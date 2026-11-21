"""Recount saved development traces under the adjacent frozen protocol; CPU only."""
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
STUDIES = ROOT / "research/studies"
sys.path.insert(0, str(STUDIES / "offline_replay_20261116"))
import episodes as E
import answer_gate as ag

OUT = ROOT / "research/decisions"
sources = {
    "pilot": STUDIES / "small_model_harness_20261115/RESULTS_LOG.jsonl",
    "round1": STUDIES / "build_round1_20261115/RESULTS_LOG.jsonl",
    "round2": STUDIES / "build_round2_20261116/RESULTS_LOG.jsonl",
}
pilot_excluded = json.loads((STUDIES / "small_model_harness_20261115/INFRA_EXCLUDED.json").read_text())
pilot_excluded = {run for group in pilot_excluded.values() for run in group["run_ids"]}
round2_excluded = set(json.loads((STUDIES / "build_round2_20261116/INFRA_EXCLUDED.json").read_text())["run_ids"])
pilot_scores = {r["run_id"]: r["new"] for r in json.loads((STUDIES / "residual_failures_20261115/rescore_v2.json").read_text())}
tasks = E.load_tasks()


def empty_or_missing(out, text):
    if out is None:
        return False
    if out == "" or out == [] or out == {}:
        return True
    if isinstance(out, dict) and all(value in ([], {}, None, "") for value in out.values()):
        return True
    return bool(E.NOT_FOUND.search(text))


def summarize(rows):
    result = {"episodes": len(rows)}
    for field in ("requests", "stall_calls", "repeat_calls", "same_arguments_repeats", "empty_stalls", "missing_results", "first_after_requests", "first_after_known_tokens", "first_after_missing_usage", "second_after_requests", "second_after_known_tokens", "second_after_missing_usage"):
        result[field] = sum(row[field] for row in rows)
    for name, pred in {
        "with_stall": lambda x: x["stall_calls"] > 0,
        "supported": lambda x: x["supported"] is True,
        "supported_with_stall": lambda x: x["supported"] is True and x["stall_calls"] > 0,
        "with_second_stall": lambda x: x["second_request"] is not None,
        "supported_with_useful_next_hide": lambda x: x["supported"] is True and x["useful_next_hide"] > 0,
        "at_least_40_requests": lambda x: x["requests"] >= 40,
        "cap_termination": lambda x: x["cap_termination"],
    }.items():
        result[name] = sum(bool(pred(row)) for row in rows)
    result["stalls_in_supported_episodes"] = sum(r["stall_calls"] for r in rows if r["supported"] is True)
    result["useful_next_hide_events"] = sum(r["useful_next_hide"] for r in rows)
    return result


records, excluded, errors, seen_paths = [], Counter(), [], set()
for group, path in sources.items():
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if group != "pilot" and row.get("phase") != "full":
            excluded[group + ":smoke"] += 1
            continue
        if group == "pilot" and row["run_id"] in pilot_excluded:
            excluded[group + ":infra_or_superseded"] += 1
            continue
        trace = row["trace_path"]
        if group == "round2":
            rel = trace.split("/build_round2_20261116/", 1)[-1].removesuffix("/trace.jsonl")
            # The first excluded session is recorded without its full-run directory.
            if rel in round2_excluded or (rel.startswith("full_20261116T003046Z/") and row["run_id"] in round2_excluded):
                excluded[group + ":infra"] += 1
                continue
        if trace in seen_paths:
            excluded[group + ":duplicate_path"] += 1
            continue
        seen_paths.add(trace)
        try:
            ep = E.parse(group, row, tasks)
            events = [json.loads(line) for line in (ROOT / trace).read_text().splitlines()]
            model_events = [e for e in events if e.get("kind") == "model_end"]
            token_usage = []
            for event in model_events:
                usage = event.get("usage") or {}
                a, b = usage.get("input_tokens"), usage.get("output_tokens")
                token_usage.append(a + b if isinstance(a, int) and isinstance(b, int) else None)
            ledger = set(ag.names_in_text(ep["task_text"]))
            prior, prior_args, empty_count = set(), set(), defaultdict(int)
            stalls, by_tool, observed = [], defaultdict(list), []
            repeat_count = exact_count = empty_stall_count = missing = 0
            for req in ep["requests"]:
                for unit in req["units"]:
                    tool, out, text = unit["tool"], unit["output"], unit["text"]
                    if tool == "final_answer":
                        continue
                    if out is None:
                        missing += 1
                        continue
                    key = (tool, text)
                    arg_key = (tool, json.dumps(unit["args"], sort_keys=True, default=str), text)
                    repeat, exact = key in prior, arg_key in prior_args
                    repeat_count += repeat
                    exact_count += exact
                    empty = empty_or_missing(out, text)
                    if empty:
                        empty_count[tool] += 1
                    is_empty_stall = empty and empty_count[tool] >= 2
                    empty_stall_count += is_empty_stall
                    if repeat or is_empty_stall:
                        stalls.append(req["index"])
                        by_tool[tool].append(req["index"])
                    observed.append((req["index"], tool, text, bool(unit["ok"]), empty))
                    prior.add(key)
                    prior_args.add(arg_key)
                    if unit["ok"]:
                        names = set(ag.names_in_text(text))
                        if isinstance(out, dict) and isinstance(out.get("nodes"), list):
                            names |= {n for n in out["nodes"] if isinstance(n, str) and ag.ABSOLUTE_NAME.fullmatch(n)}
                        new = names - ledger
                        if new:
                            empty_count.clear()
                            ledger |= new
            useful = 0
            for tool, indices in by_tool.items():
                if len(indices) < 2:
                    continue
                trigger = indices[1]
                old = {text for q, t, text, _, _ in observed if t == tool and q <= trigger}
                useful += any(q == trigger + 1 and t == tool and ok and not empty and text not in old for q, t, text, ok, empty in observed)
            def after(index):
                if index is None:
                    return 0, 0, 0
                remaining = token_usage[index:]
                return len(remaining), sum(t for t in remaining if t is not None), sum(t is None for t in remaining)
            first = stalls[0] if stalls else None
            second = stalls[1] if len(stalls) > 1 else None
            f_req, f_tok, f_missing = after(first)
            s_req, s_tok, s_missing = after(second)
            end = next((e for e in reversed(events) if e.get("kind") == "episode_end"), {})
            cap = "max iterations" in str(end.get("answer", "")).lower() or "iteration limit" in str(end.get("error", "")).lower()
            records.append(dict(group=group, arm=row["arm"], model=row["model"], task=row["task"], seed=row["seed"], trace_path=trace,
                supported=pilot_scores.get(row["run_id"]) if group == "pilot" else row.get("supported_complete"),
                requests=len(model_events), stall_calls=len(stalls), repeat_calls=repeat_count, same_arguments_repeats=exact_count,
                empty_stalls=empty_stall_count, missing_results=missing, first_request=first, second_request=second,
                first_after_requests=f_req, first_after_known_tokens=f_tok, first_after_missing_usage=f_missing,
                second_after_requests=s_req, second_after_known_tokens=s_tok, second_after_missing_usage=s_missing,
                useful_next_hide=useful, cap_termination=cap))
        except Exception as exc:
            errors.append(dict(group=group, trace_path=trace, error=repr(exc)))

groups = {group: summarize([r for r in records if r["group"] == group]) for group in sources}
models = {model: summarize([r for r in records if r["model"] == model]) for model in sorted({r["model"] for r in records})}
c1 = [r for r in records if (r["group"] in ("pilot", "round1") and r["arm"] == "C1") or (r["group"] == "round2" and r["arm"] == "CONTROL")]
summary = dict(total=summarize(records), groups=groups, models=models, c1_type=summarize(c1),
    c1_round2_seed_1_2=summarize([r for r in c1 if r["group"] == "round2" and r["seed"] in (1, 2)]),
    c1_round2_extra=summarize([r for r in c1 if r["group"] == "round2" and r["seed"] not in (1, 2)]),
    excluded=dict(excluded), errors=errors, fairness="not included: full run not yet documented as completed")
(OUT / "2026-11-17-stall-episodes.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
(OUT / "2026-11-17-stall-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(json.dumps(summary, indent=2))
