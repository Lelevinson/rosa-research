"""Analysis of the live rendering run, applying the frozen reading rule of PROTOCOL_LIVE.md section 5. Written and hashed BEFORE the full run starts.
  uv run python research/studies/canonical_render_20261118/analyze_live.py [full|smoke]
Reads RESULTS_LOG_LIVE.jsonl and the traces; writes results_live.json (phase 'full') or results_live_smoke.json. CPU only."""
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "research/studies/candidate_counts_20261118"))
import render_core as R  # noqa: E402
import count_candidates as C  # noqa: E402
import offline_check as O  # noqa: E402

S1 = {"h4", "u3", "v2"}
S2 = {"nf_single_1", "nf_single_2", "nf_multi_1", "nf_multi_2", "nf_amb_1", "nf_amb_2", "nf_exact", "nf_absent"}


def stratum(task):
    return "S1" if task in S1 else ("S2" if task in S2 else "S3")


def tasks_all():
    tasks = C.all_tasks()
    return tasks


def events_with_raw_results(events):
    """For a RENDER trace: put the raw result back in place of the rendered one (matched by re-rendering), so that the frozen fire analysis sees what the harness saw."""
    events = [dict(e) for e in events]
    raws = [e["raw"] for e in events if e["kind"] == "handler" and e.get("event") == "render_applied"]
    for e in events:
        if e["kind"] == "tool_end":
            for index, raw in enumerate(raws):
                if R.render_result(raw) == e.get("output"):
                    e["output"] = raw
                    raws.pop(index)
                    break
    return events


def episode_metrics(row, tasks):
    read = C.v2.s1.read_events
    C.v2.s1.read_events = lambda path: events_with_raw_results(read(path))  # parse_episode reads the trace through this function
    try:
        ep = C.parse_episode("live", row, tasks)
    finally:
        C.v2.s1.read_events = read
    fires = [dict(f, **O.classify_fire(f, ep)) for f in C.fires_a(ep)]
    calls = [c for r in ep["requests"] for c in r["calls"] if c["tool"] != "final_answer"]
    not_found = sum(1 for c in calls if not c["ok"] and not c["harness_error"] and c["entity"] is not None and C.E.NOT_FOUND.search(c["text"] if isinstance(c["text"], str) else ""))
    return dict(arm=row["arm"], model=row["model"], task=row["task"], seed=row["seed"], stratum=stratum(row["task"]), supported=bool(row["supported_complete"]),
                requests=row["llm_requests"], tokens=row["input_tokens"] + row["output_tokens"], ending=ep["ending"], tool_calls=len(calls), failed_calls=sum(1 for c in calls if not c["ok"]),
                not_found_entity_calls=not_found, fires_split_only=sum(1 for f in fires if f["kind"] == "split_only"), fires_other=sum(1 for f in fires if f["kind"] != "split_only"),
                fire_distances=[f["request_distance"] for f in fires if f["request_distance"] is not None], infra=row["llm_requests"] == 0)


def aggregate(rows):
    n = len(rows)
    return dict(episodes=n, supported=sum(r["supported"] for r in rows), requests=sum(r["requests"] for r in rows), tokens=sum(r["tokens"] for r in rows),
                capped_or_no_answer=sum(r["ending"] == "none" for r in rows), tool_calls=sum(r["tool_calls"] for r in rows), failed_calls=sum(r["failed_calls"] for r in rows),
                not_found_entity_calls=sum(r["not_found_entity_calls"] for r in rows), fires_split_only=sum(r["fires_split_only"] for r in rows), fires_other=sum(r["fires_other"] for r in rows),
                infra_failed=sum(r["infra"] for r in rows))


def decide(full, render, per_model_supported_diff):
    """The reading rule of PROTOCOL_LIVE.md section 5. `full` and `render` are aggregate() dicts over S1 + S2 for the mechanism and over all cells for the harm flags
    (passed as dict(name=..., sn=<S1+S2 aggregate>, all=<overall aggregate>)). per_model_supported_diff: model -> (RENDER supported - FULL supported)."""
    def drop(a, b):  # relative drop of b against a (positive = b lower)
        return None if not a else (a - b) / a
    sn_split_drop = drop(full["sn"]["fires_split_only"] / max(full["sn"]["episodes"], 1), render["sn"]["fires_split_only"] / max(render["sn"]["episodes"], 1))
    sn_other_drop = drop(full["sn"]["fires_other"] / max(full["sn"]["episodes"], 1), render["sn"]["fires_other"] / max(render["sn"]["episodes"], 1))
    mechanism = sn_split_drop is not None and sn_split_drop >= 0.30 and (sn_other_drop is None or sn_other_drop < 0.30)
    a, b = full["all"], render["all"]
    flags = []
    if b["supported"] - a["supported"] <= -10:
        flags.append("supported lower by 10 or more cells")
    if a["requests"] and (b["requests"] - a["requests"]) / a["requests"] >= 0.15:
        flags.append("requests up by 15% or more")
    if a["tokens"] and (b["tokens"] - a["tokens"]) / a["tokens"] >= 0.10:
        flags.append("tokens up by 10% or more")
    if b["capped_or_no_answer"] - a["capped_or_no_answer"] >= 5:
        flags.append("capped or no-answer endings up by 5 or more")
    if sum(1 for diff in per_model_supported_diff.values() if diff <= -4) >= 3:
        flags.append("supported lower by 4 or more cells in 3 or more models")
    klass = "A" if mechanism and not flags else ("B" if not mechanism and not flags else ("D" if mechanism else "C"))
    return dict(split_only_drop=sn_split_drop, other_drop=sn_other_drop, mechanism_signal=mechanism, harm_flags=flags, klass=klass)


def main(phase="full"):
    tasks = tasks_all()
    rows = [json.loads(l) for l in (HERE / "RESULTS_LOG_LIVE.jsonl").read_text().splitlines()]
    rows = [r for r in rows if r.get("phase") == phase]
    metrics = [episode_metrics(r, tasks) for r in rows]
    by = lambda key, arm: [m for m in metrics if m["arm"] == arm and key(m)]
    out = dict(protocol_sha256=(HERE / "PROTOCOL_LIVE.sha256").read_text().split()[0], phase=phase, episodes=len(metrics), tables={})
    for arm in ("FULL", "RENDER"):
        out["tables"][arm] = dict(overall=aggregate(by(lambda m: True, arm)), S1=aggregate(by(lambda m: m["stratum"] == "S1", arm)), S2=aggregate(by(lambda m: m["stratum"] == "S2", arm)),
                                  S3=aggregate(by(lambda m: m["stratum"] == "S3", arm)), S1_S2=aggregate(by(lambda m: m["stratum"] in ("S1", "S2"), arm)),
                                  by_model={model: aggregate(by(lambda m, model=model: m["model"] == model, arm)) for model in sorted({m["model"] for m in metrics})})
    cells = defaultdict(dict)
    for m in metrics:
        cells[(m["task"], m["model"], m["seed"])][m["arm"]] = m["supported"]
    out["paired"] = dict(Counter(("both" if c["FULL"] and c["RENDER"] else "FULL_only" if c["FULL"] else "RENDER_only" if c["RENDER"] else "neither") for c in cells.values() if len(c) == 2))
    distances = {arm: [d for m in metrics if m["arm"] == arm for d in m["fire_distances"]] for arm in ("FULL", "RENDER")}
    out["fire_request_distance"] = {arm: (dict(n=len(v), median=statistics.median(v), mean=round(statistics.mean(v), 2)) if v else dict(n=0)) for arm, v in distances.items()}
    diffs = {model: out["tables"]["RENDER"]["by_model"][model]["supported"] - out["tables"]["FULL"]["by_model"][model]["supported"] for model in out["tables"]["FULL"]["by_model"]}
    out["supported_difference_by_model"] = diffs
    wrap = lambda arm: dict(sn=out["tables"][arm]["S1_S2"], all=out["tables"][arm]["overall"])
    out["decision"] = decide(wrap("FULL"), wrap("RENDER"), diffs)
    name = "results_live.json" if phase == "full" else f"results_live_{phase}.json"
    (HERE / name).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(dict(episodes=len(metrics), paired=out["paired"], decision=out["decision"], overall={a: out["tables"][a]["overall"] for a in out["tables"]}), indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "full")
