"""Offline check of the canonical renderer (protocol: PROTOCOL_OFFLINE.md, hash in PROTOCOL_OFFLINE.sha256). CPU only; no model, no ROS, no GPU.

Run from the repo root:  uv run python research/studies/canonical_render_20261118/offline_check.py

Flow: select the episodes of candidate_counts_20261118 -> for every menu-tool result render it, check it is lossless (item 1), measure size (3) and parsed share (4)
-> re-score every episode with the rendered results substituted (item 2) -> classify the name fires (item 5) -> results.json, violations.jsonl.
"""
import copy
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STUDIES = ROOT / "research/studies"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDIES / "candidate_counts_20261118"))
import render_core as R  # noqa: E402
import count_candidates as C  # noqa: E402  (selection, parsing, fires_a: the frozen candidate-count code)
import answer_gate as ag  # noqa: E402
import scorer_v2 as v2  # noqa: E402
import score_round1  # noqa: E402

MENU_TOOLS = {"ros2_node_list", "ros2_topic_list", "ros2_topic_echo", "ros2_service_list", "ros2_node_info", "ros2_topic_info", "ros2_param_list",
              "ros2_param_get", "ros2_service_info", "ros2_doctor", "roslog_list", "read_log"}
CHARS_PER_TOKEN = 4  # protocol item 3: an estimate, not a tokenizer count


# ---------------------------------------------------------------- item 1: lossless check (independent of the renderer's internals)
def leaves(value, path=()):
    """(path, string) for every string leaf; keys are part of the path."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, path + (index,))


def same_shape(a, b):
    if isinstance(a, dict):
        return isinstance(b, dict) and list(a) == list(b) and all(same_shape(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(same_shape(x, y) for x, y in zip(a, b))
    if isinstance(a, str):
        return isinstance(b, str)
    return a == b and type(a) is type(b)


def normalised_lines(text):
    return [" ".join(line.split()) for line in text.replace("\r\n", "\n").split("\n") if line.strip()]


def derived_is_justified(extra_line, original_text):
    """An added line must read `<P>full name: <full>` and the original must contain `<P>namespace: <ns>` and `<P>name: <nm>` with ns + '/' + nm == full (independent regexes)."""
    match = re.fullmatch(r"(.*?)[Ff]ull name: (/\S*)", extra_line)
    if not match:
        return False
    prefix, full = match.group(1), match.group(2)
    lines = normalised_lines(original_text)
    for word_ns, word_name in (("namespace", "name"), ("Namespace", "Name")):
        namespaces = [line.split(": ", 1)[1] for line in lines if line.startswith(f"{prefix}{word_ns}: ")]
        names = [line.split(": ", 1)[1] for line in lines if line.startswith(f"{prefix}{word_name}: ")]
        for namespace in namespaces:
            for name in names:
                if namespace.rstrip("/") + "/" + name == full:
                    return True
    return False


def lossless_violations(original, rendered):
    problems = []
    if not same_shape(original, rendered):
        return ["shape, keys or non-string leaves changed"]
    for (path, before), (_path, after) in zip(leaves(original), leaves(rendered)):
        left, right = normalised_lines(before), normalised_lines(after)
        position, matched = 0, [False] * len(right)
        for line in left:
            try:
                position = right.index(line, position)
            except ValueError:
                problems.append(f"original line missing at {path}: {line[:80]}")
                break
            matched[position] = True
            position += 1
        for line, was_matched in zip(right, matched):
            if not was_matched and not derived_is_justified(line, before):
                problems.append(f"unjustified added line at {path}: {line[:80]}")
    return problems


# ---------------------------------------------------------------- scoring with rendered results substituted (item 2)
def score_events(study, task, events):
    answer, _source = v2.episode_answer(events)
    if study == "namefix":
        original = [e for e in events if e["kind"] == "final_answer_original"]
        if original:
            answer = original[-1].get("answer", answer)
    rows = score_round1.expanded_rows(events)
    scored = v2.score_task(task, answer, rows)
    return dict(supported_complete=scored["supported_complete"], exact=scored["exact"], support_missing=scored["support_missing"])


def with_rendered_results(events):
    """Copy of the events in which the output of every menu-tool result (not a harness message) is replaced by its rendering."""
    events = copy.deepcopy(events)
    names = {e.get("run_id"): e["name"] for e in events if e["kind"] == "tool_start"}
    for e in events:
        if e["kind"] == "tool_end" and names.get(e.get("run_id")) in MENU_TOOLS and not harness_message(e.get("output")):
            e["output"] = R.render_result(e["output"])
        elif e["kind"] == "handler" and e.get("event") == "list_item" and e.get("tool") in MENU_TOOLS and not harness_message(e.get("output")):
            e["output"] = R.render_result(e["output"])
    return events


def harness_message(output):
    return isinstance(output, str) and bool(C.E.HARNESS_TEXT.match(output))


# ---------------------------------------------------------------- item 5: where the name of each fire lives
def contiguous_names(text):
    return set(ag.NAME_IN_TEXT.findall(text.replace("\\n", "\n")))


def classify_fire(fire, ep):
    """Returns dict(kind in task_text | contiguous_earlier | split_only, ...) for the resolution of one fire."""
    resolution, typed, request = fire["resolution"], fire["typed"], fire["request"]
    if resolution in contiguous_names(ep["task_text"]):
        return dict(kind="task_text")
    earlier = [u for r in ep["requests"] if r["index"] < request for u in r.get("units", []) if not u["harness_error"] and u["tool"] != "final_answer"]
    parts, rendered_parts, raw_blocks = [], [], []
    for unit in earlier:
        for part in ag.successful_text_parts(unit["output"]):
            parts.append(part)
        rendered_parts.extend(ag.successful_text_parts(R.render_result(unit["output"]) if unit["tool"] in MENU_TOOLS else unit["output"]))
        if isinstance(unit["output"], dict) and isinstance(unit["output"].get("nodes"), list) and resolution in unit["output"]["nodes"]:
            return dict(kind="contiguous_earlier")
    if any(resolution in contiguous_names(part) for part in parts):
        return dict(kind="contiguous_earlier")
    in_rendered = any(resolution in contiguous_names(part) for part in rendered_parts)
    joins = [(ns, nm) for part in parts for nm, ns in ag.NODE_BLOCK.findall(part.replace("\\n", "\n")) if ns.rstrip("/") + "/" + nm == resolution]
    relation = "typed_equals_name_field" if any(nm == typed for _ns, nm in joins) else "typed_differs_from_name_field"
    return dict(kind="split_only", rendered_has_full_name=in_rendered, relation=relation)


# ---------------------------------------------------------------- main
def summary(values):
    return dict(n=len(values), median=statistics.median(values), mean=round(statistics.mean(values), 2), min=min(values), max=max(values)) if values else dict(n=0)


def main():
    C.PILOT_SCORES = {}
    tasks = C.all_tasks()
    population = C.load_population()
    violations, scorer_changes, score_failures = [], [], []
    per_tool = defaultdict(lambda: Counter())
    per_tool_chars = defaultdict(lambda: Counter())
    size_rows = []                     # per result: tool, model, study, before, after
    episode_rows = []                  # per episode: study, model, delta tokens estimate, logged input tokens
    fire_rows = []
    totals = Counter()
    for study, row in population:
        ep = C.parse_episode(study, row, tasks)
        n_requests = len(ep["requests"])
        delta_chars_history = 0
        for request in ep["requests"]:
            for unit in request.get("units", []):
                if unit["tool"] not in MENU_TOOLS or unit["harness_error"]:
                    continue
                stats = Counter()
                rendered = R.render_result(unit["output"], stats)
                totals["results"] += 1
                problems = lossless_violations(unit["output"], rendered)
                if R.render_result(rendered) != rendered:
                    problems.append("not idempotent")
                    totals["not_idempotent"] += 1
                if problems:
                    if any(not p.startswith("not idempotent") for p in problems):
                        totals["lossless_violations"] += 1
                    violations.append(dict(run_id=ep["run_id"], trace=row["trace_path"], tool=unit["tool"], request=request["index"], problems=problems[:5]))
                per_tool[unit["tool"]].update(stats)
                per_tool[unit["tool"]]["results"] += 1
                changed = rendered != unit["output"]
                per_tool[unit["tool"]]["results_changed"] += int(changed)
                per_tool_chars[unit["tool"]]["string_chars"] += sum(len(t) for _p, t in leaves(unit["output"]))
                before = len(json.dumps(unit["output"], ensure_ascii=False))
                after = len(json.dumps(rendered, ensure_ascii=False))
                size_rows.append(dict(tool=unit["tool"], model=ep["model"], study=study, before=before, after=after))
                delta_chars_history += (after - before) * (n_requests - request["index"])
        episode_rows.append(dict(study=study, model=ep["model"], run_id=ep["run_id"], delta_tokens=delta_chars_history / CHARS_PER_TOKEN,
                                 input_tokens=row.get("input_tokens", 0)))
        # item 2: scorer invariance
        try:
            baseline = score_events(study, ep["task_def"], ep["events"])
            rendered_score = score_events(study, ep["task_def"], with_rendered_results(ep["events"]))
            totals["episodes_scored"] += 1
            if baseline != rendered_score:
                scorer_changes.append(dict(run_id=ep["run_id"], trace=row["trace_path"], before=baseline, after=rendered_score))
        except Exception as error:
            score_failures.append(dict(run_id=ep["run_id"], error=f"{type(error).__name__}: {error}"))
        # item 5: fires
        for fire in C.fires_a(ep):
            fire_rows.append(dict(study=study, model=ep["model"], run_id=ep["run_id"], typed=fire["typed"], resolution=fire["resolution"], **classify_fire(fire, ep)))

    tool_table = {}
    for tool, c in sorted(per_tool.items()):
        lines = c["lines_key_value"] + c["lines_header"] + c["lines_bare"]
        leaves_total = c["leaves_rendered"] + c["leaves_passed_through"]
        tool_table[tool] = dict(results=c["results"], results_changed=c["results_changed"], leaves=leaves_total, leaves_rendered=c["leaves_rendered"],
                                share_leaves_rendered=round(c["leaves_rendered"] / leaves_total, 3) if leaves_total else None,
                                lines=lines, share_key_value=round(c["lines_key_value"] / lines, 3) if lines else None, share_header=round(c["lines_header"] / lines, 3) if lines else None,
                                share_bare=round(c["lines_bare"] / lines, 3) if lines else None,
                                share_chars_in_rendered_leaves=round(c["chars_in_rendered_leaves"] / per_tool_chars[tool]["string_chars"], 3) if per_tool_chars[tool]["string_chars"] else None,
                                derived_lines=c["derived_lines"], skips={k: v for k, v in c.items() if k.startswith("skip_")})
    deltas = [r["after"] - r["before"] for r in size_rows]
    size = dict(chars_change=summary(deltas), larger=sum(d > 0 for d in deltas), equal=sum(d == 0 for d in deltas), smaller=sum(d < 0 for d in deltas),
                total_before=sum(r["before"] for r in size_rows), total_after=sum(r["after"] for r in size_rows),
                by_tool={t: dict(results=len(v), median_change=statistics.median(x["after"] - x["before"] for x in v), mean_before=round(statistics.mean(x["before"] for x in v), 1),
                                 mean_after=round(statistics.mean(x["after"] for x in v), 1)) for t in sorted({r["tool"] for r in size_rows}) for v in [[r for r in size_rows if r["tool"] == t]]},
                by_model={m: dict(results=len(v), total_change_chars=sum(x["after"] - x["before"] for x in v)) for m in sorted({r["model"] for r in size_rows}) for v in [[r for r in size_rows if r["model"] == m]]})
    percent = [100 * r["delta_tokens"] / r["input_tokens"] for r in episode_rows if r["input_tokens"]]
    history = dict(episodes=len(episode_rows), delta_tokens_est=summary([round(r["delta_tokens"], 1) for r in episode_rows]), percent_of_logged_input_tokens=summary([round(p, 2) for p in percent]),
                   total_delta_tokens_est=round(sum(r["delta_tokens"] for r in episode_rows)), total_logged_input_tokens=sum(r["input_tokens"] for r in episode_rows),
                   by_model={m: dict(episodes=len(v), total_delta_tokens_est=round(sum(x["delta_tokens"] for x in v)), total_logged_input_tokens=sum(x["input_tokens"] for x in v))
                             for m in sorted({r["model"] for r in episode_rows}) for v in [[r for r in episode_rows if r["model"] == m]]},
                   by_study={s: dict(episodes=len(v), total_delta_tokens_est=round(sum(x["delta_tokens"] for x in v)), total_logged_input_tokens=sum(x["input_tokens"] for x in v))
                             for s in sorted({r["study"] for r in episode_rows}) for v in [[r for r in episode_rows if r["study"] == s]]})
    fires = dict(total=len(fire_rows), by_kind=dict(Counter(f["kind"] for f in fire_rows)),
                 split_only_rendered_has_full_name=sum(1 for f in fire_rows if f["kind"] == "split_only" and f["rendered_has_full_name"]),
                 split_only_relation=dict(Counter(f["relation"] for f in fire_rows if f["kind"] == "split_only")),
                 by_model={m: dict(Counter(f["kind"] for f in fire_rows if f["model"] == m)) for m in sorted({f["model"] for f in fire_rows})},
                 by_study={s: dict(Counter(f["kind"] for f in fire_rows if f["study"] == s)) for s in sorted({f["study"] for f in fire_rows})})
    bars = dict(lossless_violations=totals["lossless_violations"], lossless_bar_met=totals["lossless_violations"] == 0,
                scorer_changes=len(scorer_changes), scorer_bar_met=len(scorer_changes) == 0, score_failures=len(score_failures))
    results = dict(protocol_sha256=(HERE / "PROTOCOL_OFFLINE.sha256").read_text().split()[0], episodes=len(population), results=totals["results"], not_idempotent=totals["not_idempotent"],
                   bars=bars, tool_table=tool_table, size=size, history=history, fires=fires, scorer_changes=scorer_changes[:20], score_failures=score_failures[:20])
    (HERE / "results.json").write_text(json.dumps(results, indent=1, default=str))
    (HERE / "fires_render.jsonl").write_text("".join(json.dumps(f, default=str) + "\n" for f in fire_rows))
    (HERE / "violations.jsonl").write_text("".join(json.dumps(v, default=str) + "\n" for v in violations))
    print(json.dumps(dict(episodes=len(population), results=totals["results"], bars=bars, not_idempotent=totals["not_idempotent"], size_total=[size["total_before"], size["total_after"]],
                          fires=fires["by_kind"], split_only_rendered=fires["split_only_rendered_has_full_name"], relation=fires["split_only_relation"]), indent=1))


if __name__ == "__main__":
    main()
