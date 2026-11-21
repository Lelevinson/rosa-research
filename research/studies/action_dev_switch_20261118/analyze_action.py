"""Analysis of PROTOCOL.md section 3-4, applied by frozen code. Offline: reads RESULTS_LOG.jsonl.
  uv run python research/studies/action_dev_switch_20261118/analyze_action.py [full|smoke]
Writes results.json (full) or results_smoke.json."""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
CAPPED = ("cap", "timeout", "timeout_http")


def capped(row):
    return row["ending"] in CAPPED or row["ending"].startswith("backend_error") or row["ending"] == "text" and False


def agg(rows):
    n = len(rows)
    if not n:
        return dict(episodes=0)
    return dict(episodes=n, success=sum(bool(r["success"]) for r in rows), requests=sum(r["requests"] for r in rows), tokens=sum(r["tokens"] for r in rows),
                verification_calls=sum(r["verification_calls"] for r in rows), verification_per_episode=round(sum(r["verification_calls"] for r in rows) / n, 3),
                pose_reads=sum(r["pose_reads"] for r in rows), rotate_calls=sum(r["tool_calls"].get("rotate_to_heading", 0) for r in rows), goals_sent=sum(r["goals_sent"] for r in rows),
                requests_per_episode=round(sum(r["requests"] for r in rows) / n, 2), tokens_per_episode=round(sum(r["tokens"] for r in rows) / n),
                capped_or_error=sum(capped(r) for r in rows), locked=sum(r["executor_final_state"] == "UNKNOWN_LOCKED" for r in rows),
                not_still=sum(not r["turtle_still"] for r in rows), infrastructure=sum(bool(r.get("infrastructure")) for r in rows),
                endings={e: sum(r["ending"] == e for r in rows) for e in sorted({r["ending"] for r in rows})})


def decide(by_arm, by_model_arm):
    off, on = by_arm["OFF"], by_arm["ON"]
    models_v = [m for m in MODELS if by_model_arm[m]["ON"]["verification_calls"] < by_model_arm[m]["OFF"]["verification_calls"]]
    models_e = [m for m in MODELS if by_model_arm[m]["ON"]["requests"] < by_model_arm[m]["OFF"]["requests"]]
    models_success_lower = [m for m in MODELS if by_model_arm[m]["OFF"]["success"] - by_model_arm[m]["ON"]["success"] >= 2]
    rel = lambda a, b: (a - b) / a if a else 0.0           # relative drop of b against a
    v = rel(off["verification_calls"], on["verification_calls"]) >= 0.25 and len(models_v) >= 3
    e = rel(off["requests"], on["requests"]) >= 0.10 and len(models_e) >= 3
    harm = []
    if off["success"] - on["success"] >= 6:
        harm.append(f"ON success lower by {off['success'] - on['success']} cells")
    if on["tokens"] >= 1.10 * off["tokens"]:
        harm.append("tokens up 10% or more")
    if on["capped_or_error"] - off["capped_or_error"] >= 3:
        harm.append("capped/error endings up 3 or more")
    if on["locked"] + on["not_still"] > off["locked"] + off["not_still"]:
        harm.append("more locked or moving episodes in ON")
    if len(models_success_lower) >= 3:
        harm.append("ON success lower by 2+ cells in 3+ models")
    klass = "D" if (v or e) and harm else "C" if harm else "A" if (v or e) else "B"
    return dict(signal_V=v, signal_E=e, verification_drop=round(rel(off["verification_calls"], on["verification_calls"]), 3), requests_drop=round(rel(off["requests"], on["requests"]), 3),
                models_lower_verification=models_v, models_lower_requests=models_e, harm_flags=harm, klass=klass)


def main(phase="full"):
    rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
    rows = [r for r in rows if r.get("phase") == phase]
    out = dict(protocol_sha256=(HERE / "PROTOCOL.sha256").read_text().split()[0], phase=phase, episodes=len(rows))
    by_arm = {a: agg([r for r in rows if r["arm"] == a]) for a in ("OFF", "ON")}
    by_model_arm = {m: {a: agg([r for r in rows if r["arm"] == a and r["model"] == m]) for a in ("OFF", "ON")} for m in MODELS}
    kinds = sorted({r["kind"] for r in rows})
    out.update(by_arm=by_arm, by_model_arm=by_model_arm,
               by_kind_arm={k: {a: agg([r for r in rows if r["arm"] == a and r["kind"] == k]) for a in ("OFF", "ON")} for k in kinds},
               by_task_arm={t: {a: agg([r for r in rows if r["arm"] == a and r["task"] == t]) for a in ("OFF", "ON")} for t in sorted({r["task"] for r in rows})})
    heading_only = [r for r in rows if r["task"] in ("S1", "S2", "S3", "M1", "M2", "M3")]
    out["verification_on_heading_only_tasks"] = {a: agg([r for r in heading_only if r["arm"] == a]).get("verification_per_episode") for a in ("OFF", "ON")}
    cells = defaultdict(dict)
    for r in rows:
        cells[(r["task"], r["model"], r["seed"])][r["arm"]] = bool(r["success"])
    paired = defaultdict(int)
    for c in cells.values():
        if len(c) == 2:
            paired["both" if c["OFF"] and c["ON"] else "OFF_only" if c["OFF"] else "ON_only" if c["ON"] else "neither"] += 1
    out["paired"] = dict(paired)
    out["rotate_results"] = {a: dict(sorted(__import__("collections").Counter(x for r in rows if r["arm"] == a for x in r["rotate_results"]).items())) for a in ("OFF", "ON")}
    if phase == "full":
        out["decision"] = decide(by_arm, by_model_arm)
    (HERE / ("results.json" if phase == "full" else f"results_{phase}.json")).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(dict(episodes=len(rows), by_arm=by_arm, paired=out["paired"], decision=out.get("decision")), indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "full")
