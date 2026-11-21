"""STEP 5 analysis of build round 2 (definitions: PROTOCOL.md section 8; nothing here may be changed after the first full-run episode).

  uv run python analyze_round2.py [PHASES]     PHASES = comma list of RESULTS_LOG phases to include (default: full; use full,addon after the add-on)
Writes ANALYSIS.json (all numbers, event list, bar verdicts that can be computed) and TABLES.md. P4 (hand reading) is not computed: the script lists the
SWEEP episodes that fired and ended unsupported, to be read by hand (view_episode.py of round 1 prints a trace).
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "offline_replay_20261116"))
sys.path.insert(0, str(HERE))
import episodes as E  # noqa: E402
import sweep_logic  # noqa: E402

LOG = HERE / "RESULTS_LOG.jsonl"
tasks = E.load_tasks()
rtoks = lambda r: r["input_tokens"] + r["output_tokens"]


def load_rows(phases):
    rows = [json.loads(line) for line in LOG.read_text().splitlines()]
    excluded_file = HERE / "INFRA_EXCLUDED.json"  # episodes of sessions stopped by an oracle failure (PROTOCOL amendment 2); kept in the log, never analysed
    excluded = set(json.loads(excluded_file.read_text())["run_ids"]) if excluded_file.exists() else set()
    return [r for r in rows if r["phase"] in phases and r["run_id"] not in excluded]


def other_key(call):
    return json.dumps(call["args"], sort_keys=True)


def first_event(row, parsed):
    """The first firing (live or shadow) of an episode, with the per-event measures of PROTOCOL.md section 8, or None."""
    fires = [e for e in row["sweep"] if e["event"] in ("sweep_fire", "sweep_shadow")]
    if not fires:
        return None
    first = min(fires, key=lambda e: e["request"])
    k, tool = first["request"], first["tool"]
    requests = parsed["requests"]
    already_read = set(first["sweep"])
    for r in requests:
        if r["index"] <= k:
            already_read |= {c["entity"] for c in r["calls"] if c["tool"] == tool and c["entity"] is not None}
    reask = []
    for r in requests:
        if r["index"] > k and r["calls"] and all(c["tool"] == tool and c["entity"] is not None and c["entity"] in already_read for c in r["calls"]):
            reask.append(r["index"])
    after = [r for r in requests if r["index"] > k]
    return dict(run_id=row["run_id"], arm=row["arm"], model=row["model"], task=row["task"], seed=row["seed"], kind=first["event"], request=k, tool=tool,
                sweep_size=len(first["sweep"]), cut=len(first.get("cut") or []), extra_tool_runs=first.get("extra_tool_runs"), extra_tokens_est=first.get("extra_result_tokens_est"),
                reask=bool(reask), reask_requests=reask, requests_after=len(after), tokens_after=sum(rtoks(r) for r in after), supported=row["supported_complete"],
                hit_cap="iteration limit" in row["aborts"], later_firings=len(fires) - 1, trace_path=row["trace_path"])


def summarize(events):
    if not events:
        return dict(n=0)
    after, tokens = [e["requests_after"] for e in events], [e["tokens_after"] for e in events]
    return dict(n=len(events), models=len({e["model"] for e in events}), reask_rate=sum(e["reask"] for e in events) / len(events),
                mean_requests_after=statistics.mean(after), median_requests_after=statistics.median(after), mean_tokens_after=statistics.mean(tokens),
                median_tokens_after=statistics.median(tokens), supported=sum(e["supported"] for e in events), hit_cap=sum(e["hit_cap"] for e in events),
                extra_tool_runs=sum(e["extra_tool_runs"] or 0 for e in events if e["kind"] == "sweep_fire"),
                extra_tokens_est=sum(e["extra_tokens_est"] or 0 for e in events if e["kind"] == "sweep_fire"))


def rewrite_summary(rows):
    out = dict(answers=0, changed=0, supported_to_unsupported=[], unsupported_to_supported=[], would_reject_ambiguous=0, would_reject_never_seen=0, would_reject_supported=0,
               would_reject_with_unread=0)
    for r in rows:
        shadow = r["rewrite_shadow"]
        if not shadow:
            continue
        s = shadow[-1]
        out["answers"] += 1
        amb, never = len(s["would_reject_ambiguous"]), len(s["would_reject_never_seen"])
        out["would_reject_ambiguous"] += amb
        out["would_reject_never_seen"] += never
        if amb or never:
            out["would_reject_supported"] += bool(r["supported_complete"])
            out["would_reject_with_unread"] += bool(s.get("listed_but_unread"))
        if s["changed"] and r["rewritten"] is not None:
            out["changed"] += 1
            after = r["rewritten"]["supported_complete"]
            cell = dict(run_id=r["run_id"], model=r["model"], task=r["task"], seed=r["seed"], arm=r["arm"], rewrites=s["rewrites"])
            if r["supported_complete"] and not after:
                out["supported_to_unsupported"].append(cell)
            if not r["supported_complete"] and after:
                out["unsupported_to_supported"].append(cell)
    cells = {(c["task"], c["model"], c["seed"]) for c in out["unsupported_to_supported"]}
    out["unsupported_to_supported_cells"] = len(cells)
    out["unsupported_to_supported_models"] = sorted({c["model"] for c in out["unsupported_to_supported"]})
    return out


def main(phases):
    rows = load_rows(phases)
    events, parsed_rows = [], {}
    for row in rows:
        parsed = E.parse("round 2", row, tasks)
        parsed_rows[row["run_id"]] = parsed
        event = first_event(row, parsed)
        if event:
            events.append(event)
    arms = {a: [e for e in events if e["arm"] == a] for a in ("CONTROL", "SWEEP")}
    episodes_per_arm = {a: sum(r["arm"] == a for r in rows) for a in arms}
    summary = {a: summarize(v) for a, v in arms.items()}
    by_model = {a: {m: summarize([e for e in v if e["model"] == m]) for m in sorted({e["model"] for e in events})} for a, v in arms.items()}
    by_task = {a: {t: summarize([e for e in v if e["task"] == t]) for t in sorted({e["task"] for e in events})} for a, v in arms.items()}
    largest_task_share = {a: (max(((t, sum(e["task"] == t for e in v)) for t in {e["task"] for e in v}), key=lambda x: x[1]) if v else None, len(v)) for a, v in arms.items()}
    c, s = summary["CONTROL"], summary["SWEEP"]
    verdict = {}
    nc, ns = c.get("n", 0), s.get("n", 0)
    verdict["V-b first-fire episode counts differ by < factor 2"] = bool(nc and ns and max(nc, ns) / min(nc, ns) < 2)
    verdict["V-c >= 15 first-fire events per arm from >= 3 models"] = bool(nc >= 15 and ns >= 15 and c["models"] >= 3 and s["models"] >= 3)
    if nc and ns:
        drop = [e for e in arms["CONTROL"]]
        biggest = max(drop, key=lambda e: e["requests_after"])
        without = statistics.mean(e["requests_after"] for e in drop if e is not biggest) if len(drop) > 1 else None
        verdict["P1 re-ask rate in SWEEP <= 25%"] = s["reask_rate"] <= 0.25
        verdict["FAIL if re-ask rate >= 50%"] = s["reask_rate"] >= 0.5
        verdict["P2 mean requests after fire lower in SWEEP by >= 1.0"] = c["mean_requests_after"] - s["mean_requests_after"] >= 1.0
        verdict["P2 median not higher"] = s["median_requests_after"] <= c["median_requests_after"]
        verdict["P2 direction holds without the largest CONTROL event"] = without is not None and s["mean_requests_after"] < without
        verdict["FAIL if mean requests after fire not lower"] = not (s["mean_requests_after"] < c["mean_requests_after"])
        verdict["P3 mean tokens after fire lower in SWEEP"] = s["mean_tokens_after"] < c["mean_tokens_after"]
    p4 = [dict(run_id=e["run_id"], model=e["model"], task=e["task"], seed=e["seed"], request=e["request"], trace=e["trace_path"]) for e in arms["SWEEP"] if not e["supported"]]
    # paired by cell (descriptive): the two arms of a cell share task, model and seed
    cells = defaultdict(dict)
    for e in events:
        cells[(e["task"], e["model"], e["seed"])][e["arm"]] = e
    paired = [dict(cell=list(k), control=v["CONTROL"]["requests_after"], sweep=v["SWEEP"]["requests_after"]) for k, v in cells.items() if len(v) == 2]
    result = dict(phases=sorted(phases), episodes=len(rows), episodes_per_arm=episodes_per_arm, first_fire_events=dict(CONTROL=nc, SWEEP=ns), summary=summary,
                  by_model=by_model, by_task=by_task, largest_task_share=largest_task_share, verdict=verdict, p4_episodes_to_hand_read=p4, paired_cells_both_fired=paired,
                  rewrite=rewrite_summary(rows), later_firings=dict(CONTROL=sum(e["later_firings"] for e in arms["CONTROL"]), SWEEP=sum(e["later_firings"] for e in arms["SWEEP"])),
                  whole_arm_totals_for_the_record_only={a: dict(requests=sum(r["llm_requests"] for r in rows if r["arm"] == a), tokens=sum(r["input_tokens"] + r["output_tokens"] for r in rows if r["arm"] == a),
                                                                supported=sum(r["supported_complete"] for r in rows if r["arm"] == a), episodes=episodes_per_arm[a]) for a in arms},
                  aborts={a: sum(bool([x for x in r["aborts"] if x != "iteration limit"]) for r in rows if r["arm"] == a) for a in arms}, events=events)
    (HERE / "ANALYSIS.json").write_text(json.dumps(result, indent=1, default=str))
    lines = ["# Round 2 tables (generated by analyze_round2.py; phases: " + ", ".join(sorted(phases)) + ")", "", f"Episodes {len(rows)}: {episodes_per_arm}. First-fire events: CONTROL {nc}, SWEEP {ns}.", "",
             "## Per arm (unit = first firing of an episode)", "| arm | events | models | re-ask rate | mean requests after | median | mean tokens after | supported | hit cap | extra tool runs | extra tokens (est) |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for a, v in summary.items():
        if v["n"]:
            lines.append(f"| {a} | {v['n']} | {v['models']} | {v['reask_rate']:.2f} | {v['mean_requests_after']:.2f} | {v['median_requests_after']} | {v['mean_tokens_after']:.0f} | {v['supported']} | {v['hit_cap']} | {v['extra_tool_runs']} | {v['extra_tokens_est']} |")
    for title, table in (("model", by_model), ("task", by_task)):
        lines += ["", f"## Per {title}", f"| {title} | arm | events | re-ask rate | mean requests after | mean tokens after | supported |", "|---|---|---:|---:|---:|---:|---:|"]
        for a in table:
            for key, v in table[a].items():
                if v["n"]:
                    lines.append(f"| {key} | {a} | {v['n']} | {v['reask_rate']:.2f} | {v['mean_requests_after']:.2f} | {v['mean_tokens_after']:.0f} | {v['supported']} |")
    lines += ["", "## Bars computable by script", *[f"- {k}: {'yes' if v else 'NO'}" for k, v in verdict.items()], "", "## Rewrite (shadow)", json.dumps(result["rewrite"], default=str)[:3000]]
    (HERE / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(dict(first_fire_events=result["first_fire_events"], verdict=verdict, summary=summary), indent=1, default=str))


if __name__ == "__main__":
    main(set((sys.argv[1] if len(sys.argv) > 1 else "full").split(",")))
