"""Analysis of the repeat-finish nudge run, applying the frozen reading rule of PROTOCOL.md section 5. Written and hashed BEFORE the full run starts.
  uv run python research/studies/repeat_finish_nudge_20261118/analyze_nudge.py [full|smoke]
Reads RESULTS_LOG.jsonl and the traces; writes results.json (phase 'full') or results_smoke.json. CPU only.
The first identical repeat is located from the `identical_repeat` events the arm logs in BOTH arms (same detection code)."""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "research/studies/candidate_counts_20261118"))
import count_candidates as C  # noqa: E402

CHG = {"e1h_chg_1", "e1h_chg_2"}
ARMS = ("FULL", "NUDGE")


def stratum(task):
    return "CHG" if task in CHG else "NONCHG"


def rebuild(calls):
    """Rows for scorer v2.0's support_missing, as in write_tail_repeat_20261118/count_wtr.py."""
    rows = []
    for c in calls:
        args = dict(c["args"] or {})
        if c.get("entity_arg"):
            args[c["entity_arg"]] = c["entity"]
        rows.append(dict(name=c["tool"], args=args, given_args=args, output=c["output"], text=c["text"] if isinstance(c["text"], str) else json.dumps(c["text"]), ok=c["ok"], line=None))
    return rows


def episode_metrics(row, tasks):
    ep = C.parse_episode("live", row, tasks)
    events = ep["events"]
    repeats = [e for e in events if e["kind"] == "handler" and e.get("event") == "identical_repeat"]
    total = row["llm_requests"]
    first = repeats[0]["request"] if repeats else None
    after_first = (total - first) if first is not None else 0
    next_final = None
    klass = None
    if first is not None:
        nxt = [r for r in ep["requests"] if r["index"] == first + 1]
        next_final = bool(nxt) and any(c["tool"] == "final_answer" for c in nxt[0]["calls"])
        before = [c for r in ep["requests"] if r["index"] < first for c in r["calls"]]
        try:
            missing = C.v2.support_missing(ep["task_def"], rebuild(before))
        except Exception:
            missing = ["error"]
        klass = "facts_present" if not missing else "facts_not_yet"
    end = [e for e in events if e["kind"] == "episode_end"]
    end_text = end[-1].get("answer") if end else None
    capped = isinstance(end_text, str) and "max iterations" in end_text
    return dict(arm=row["arm"], model=row["model"], task=row["task"], seed=row["seed"], stratum=stratum(row["task"]), supported=bool(row["supported_complete"]),
                requests=total, tokens=row["input_tokens"] + row["output_tokens"], capped=capped, no_answer=ep["answer"] is None, tool_calls=row["exposure"]["tool_calls"],
                repeats=len(repeats), fires=sum(bool(e["fired"]) for e in repeats), first_repeat_request=first, requests_after_first_repeat=after_first,
                next_request_final=next_final, klass=klass, infra=total == 0, trace=row["trace_path"])


def aggregate(rows):
    with_repeat = [r for r in rows if r["first_repeat_request"] is not None]
    return dict(episodes=len(rows), supported=sum(r["supported"] for r in rows), requests=sum(r["requests"] for r in rows), tokens=sum(r["tokens"] for r in rows),
                capped=sum(r["capped"] for r in rows), no_answer=sum(r["no_answer"] for r in rows), tool_calls=sum(r["tool_calls"] for r in rows),
                episodes_with_repeat=len(with_repeat), repeats=sum(r["repeats"] for r in rows), fired_episodes=sum(r["fires"] > 0 for r in rows), fires=sum(r["fires"] for r in rows),
                R_sum=sum(r["requests_after_first_repeat"] for r in rows), infra_failed=sum(r["infra"] for r in rows),
                next_request_final=sum(bool(r["next_request_final"]) for r in with_repeat))


def chg_early_answers(rows):
    """CHG episodes with a first repeat whose next request calls final_answer and whose episode is unsupported."""
    return [r for r in rows if r["stratum"] == "CHG" and r["first_repeat_request"] is not None and r["next_request_final"] and not r["supported"]]


def facts_split(rows):
    out = {}
    for klass in ("facts_present", "facts_not_yet"):
        sel = [r for r in rows if r["klass"] == klass]
        out[klass] = dict(episodes=len(sel), supported=sum(r["supported"] for r in sel), unsupported=sum(not r["supported"] for r in sel), no_answer=sum(r["no_answer"] for r in sel),
                          next_request_final=sum(bool(r["next_request_final"]) for r in sel), R_sum=sum(r["requests_after_first_repeat"] for r in sel))
    return out


def decide(full, nudge, full_by_model, nudge_by_model, early_full, early_nudge):
    """PROTOCOL.md section 5. full / nudge: overall aggregates. *_by_model: model -> aggregate. early_*: counts of CHG early answers."""
    drop = lambda a, b: None if not a else (a - b) / a
    pooled = drop(full["R_sum"], nudge["R_sum"])  # same 80 episodes per arm, so sum equals per-100 comparison
    per_model, evaluable_hits, evaluable = {}, 0, 0
    for model, f in full_by_model.items():
        n = nudge_by_model[model]
        if f["R_sum"] < 20:
            per_model[model] = dict(status="not evaluable", full_R=f["R_sum"], nudge_R=n["R_sum"])
            continue
        d = drop(f["R_sum"], n["R_sum"])
        evaluable += 1
        hit = d >= 0.30
        evaluable_hits += hit
        per_model[model] = dict(status="drop>=30%" if hit else "drop<30%", full_R=f["R_sum"], nudge_R=n["R_sum"], drop=d)
    met = pooled is not None and pooled >= 0.30 and evaluable_hits >= 2
    flags = []
    if nudge["supported"] - full["supported"] < -3:
        flags.append("supported lower by more than 3 cells")
    if early_nudge > early_full:
        flags.append("CHG early answers higher in NUDGE")
    klass = "A" if met and not flags else ("B" if not met and not flags else ("D" if met else "C"))
    return dict(pooled_R_drop=pooled, models_with_drop_ge_30=evaluable_hits, evaluable_models=evaluable, per_model=per_model, event_bar_met=met, harm_flags=flags, klass=klass)


def main(phase="full"):
    tasks = C.all_tasks()
    rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
    rows = [r for r in rows if r.get("phase") == phase]
    metrics = [episode_metrics(r, tasks) for r in rows]
    by = lambda arm, key=lambda m: True: [m for m in metrics if m["arm"] == arm and key(m)]
    models = sorted({m["model"] for m in metrics})
    out = dict(protocol_sha256=(HERE / "PROTOCOL.sha256").read_text().split()[0], phase=phase, episodes=len(metrics), tables={})
    for arm in ARMS:
        out["tables"][arm] = dict(overall=aggregate(by(arm)), CHG=aggregate(by(arm, lambda m: m["stratum"] == "CHG")), NONCHG=aggregate(by(arm, lambda m: m["stratum"] == "NONCHG")),
                                  by_model={model: aggregate(by(arm, lambda m, model=model: m["model"] == model)) for model in models}, facts_split=facts_split(by(arm)))
    cells = defaultdict(dict)
    for m in metrics:
        cells[(m["task"], m["model"], m["seed"])][m["arm"]] = m["supported"]
    paired = defaultdict(int)
    for c in cells.values():
        if len(c) == 2:
            paired["both" if c["FULL"] and c["NUDGE"] else "FULL_only" if c["FULL"] else "NUDGE_only" if c["NUDGE"] else "neither"] += 1
    out["paired"] = dict(paired)
    early = {arm: chg_early_answers(by(arm)) for arm in ARMS}
    out["chg_early_answers"] = {arm: [dict(task=r["task"], model=r["model"], seed=r["seed"], trace=r["trace"]) for r in rows_] for arm, rows_ in early.items()}
    out["after_first_fire"] = {arm: dict(episodes=out["tables"][arm]["overall"]["episodes_with_repeat"], next_request_final=out["tables"][arm]["overall"]["next_request_final"]) for arm in ARMS}
    out["decision"] = decide(out["tables"]["FULL"]["overall"], out["tables"]["NUDGE"]["overall"], out["tables"]["FULL"]["by_model"], out["tables"]["NUDGE"]["by_model"],
                             len(early["FULL"]), len(early["NUDGE"]))
    out["episode_rows"] = metrics
    name = "results.json" if phase == "full" else f"results_{phase}.json"
    (HERE / name).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(dict(episodes=len(metrics), paired=out["paired"], decision=out["decision"], overall={a: out["tables"][a]["overall"] for a in ARMS}), indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "full")
