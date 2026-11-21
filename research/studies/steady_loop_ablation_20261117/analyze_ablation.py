"""Analysis of the steady-loop ablation (protocol: research/decisions/2026-11-17-steady-loop-ablation-protocol.md, 'Frozen reading rules and numbers'). uv run python analyze_ablation.py
Writes TABLES.md, results.json, DISCORDANT_CELLS.json (cells where fresh FULL and a removal differ, for the blind hand audit; no aggregates inside).
Mechanical parts only: the 'important benefit/harm' and 'efficiency' verdicts need the hand audit (>= 2 trace-supported attributable disagreements / exposure cases) and are left to REPORT.md."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
REPO = HERE.parents[2]
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
import scorer_v2 as v2  # noqa: E402

MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
REMOVALS = ["NO_SOFT_ERRORS", "NO_PRECHECK", "NO_MENU", "NO_FINISH"]
ARMS = ["FULL"] + REMOVALS
rows = lambda p: [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]
tok = lambda r: r["input_tokens"] + r["output_tokens"]
cell = lambda r: (r["task"], r["model"], r["seed"])


def error_observations(r):
    e = r["exposure"]
    return e["precheck_rejections"] + e["stock_validation_errors"] + e["tool_exceptions"] + e["tool_not_offered"] + e["blocked_write_attempts"]


def summarize(rs):
    n, sup = len(rs), sum(r["supported_complete"] for r in rs)
    req, tokens = sum(r["llm_requests"] for r in rs), sum(tok(r) for r in rs)
    both = [r for r in rs if r["supported_complete"]]
    return dict(episodes=n, supported=sup, aborts=sum(bool([a for a in r["aborts"] if a != "iteration limit"]) for r in rs), no_answer=sum(r["answer"] is None for r in rs),
                cap_hits=sum("iteration limit" in r["aborts"] for r in rs), error_observations=sum(error_observations(r) for r in rs), requests=req,
                input_tokens=sum(r["input_tokens"] for r in rs), output_tokens=sum(r["output_tokens"] for r in rs), tokens=tokens, native_ops=sum(r["native_ops"] for r in rs),
                blocked_write_attempts=sum(r["exposure"]["blocked_write_attempts"] for r in rs), wall_seconds=sum(r["wall_seconds"] for r in rs),
                requests_per_episode=req / n if n else None, tokens_per_episode=tokens / n if n else None, requests_per_supported=req / sup if sup else None, tokens_per_supported=tokens / sup if sup else None,
                missing_usage=sum(r["input_tokens"] == 0 and r["output_tokens"] == 0 for r in rs))


def historical():
    """Pilot C1 seed 1 (the 40 matching cells) re-scored with scorer v2.0; round-1 C1 seed 1 as supplemental context (log labels)."""
    tasks = {t["id"]: t for t in json.loads((STUDIES / "headroom_diagnostic_20261112/stage3_tasks.json").read_text())}
    tasks.update({t["id"]: t for t in json.loads((STUDIES / "small_model_harness_20261115/e1h_tasks.json").read_text())})
    excluded = {x for g in json.loads((STUDIES / "small_model_harness_20261115/INFRA_EXCLUDED.json").read_text()).values() for x in g["run_ids"]}
    pilot = {}
    for r in rows(STUDIES / "small_model_harness_20261115/RESULTS_LOG.jsonl"):
        if r["arm"] == "C1" and r["seed"] == 1 and r["run_id"] not in excluded and r.get("phase") != "smoke":
            scored = v2.score_events(tasks[r["task"]], v2.s1.read_events(REPO / r["trace_path"]))
            pilot[cell(r)] = dict(supported=scored["supported_complete"], requests=r["llm_requests"], tokens=r["input_tokens"] + r["output_tokens"], model=r["model"])
    round1 = {cell(r): dict(supported=r["supported_complete"], requests=r["llm_requests"], tokens=r["input_tokens"] + r["output_tokens"], model=r["model"])
              for r in rows(STUDIES / "build_round1_20261115/RESULTS_LOG.jsonl") if r["phase"] == "full" and r["arm"] == "C1" and r["seed"] == 1}
    return pilot, round1


def main():
    allrows = [r for r in rows(HERE / "RESULTS_LOG.jsonl") if r["phase"] == "full"]
    excluded = set(json.loads((HERE / "INFRA_EXCLUDED.json").read_text())["run_ids"]) if (HERE / "INFRA_EXCLUDED.json").exists() else set()
    data = [r for r in allrows if r["run_id"] not in excluded]
    by_arm = {a: [r for r in data if r["arm"] == a] for a in ARMS}
    cells = {a: {cell(r): r for r in by_arm[a]} for a in ARMS}
    result = dict(episodes={a: len(by_arm[a]) for a in ARMS}, arms={a: dict(total=summarize(by_arm[a]), per_model={m: summarize([r for r in by_arm[a] if r["model"] == m]) for m in MODELS}) for a in ARMS}, paired={}, exposure={}, historical={})
    discordant = {}
    for a in REMOVALS:
        common = sorted(set(cells["FULL"]) & set(cells[a]))
        f, g = cells["FULL"], cells[a]
        pair = dict(cells=len(common), both=sum(f[c]["supported_complete"] and g[c]["supported_complete"] for c in common), full_only=sum(f[c]["supported_complete"] and not g[c]["supported_complete"] for c in common),
                    removal_only=sum(g[c]["supported_complete"] and not f[c]["supported_complete"] for c in common), neither=sum(not f[c]["supported_complete"] and not g[c]["supported_complete"] for c in common))
        pair["full_minus_removal_supported"] = pair["full_only"] - pair["removal_only"]
        both = [c for c in common if f[c]["supported_complete"] and g[c]["supported_complete"]]
        pair["matched_both_supported"] = dict(cells=len(both), full_requests=sum(f[c]["llm_requests"] for c in both), removal_requests=sum(g[c]["llm_requests"] for c in both),
                                              full_tokens=sum(tok(f[c]) for c in both), removal_tokens=sum(tok(g[c]) for c in both))
        pair["total_requests_change"] = (sum(r["llm_requests"] for r in by_arm[a]) - sum(r["llm_requests"] for r in by_arm["FULL"])) / max(1, sum(r["llm_requests"] for r in by_arm["FULL"]))
        pair["total_tokens_change"] = (sum(tok(r) for r in by_arm[a]) - sum(tok(r) for r in by_arm["FULL"])) / max(1, sum(tok(r) for r in by_arm["FULL"]))
        pair["efficiency_flag_10pct"] = abs(pair["total_requests_change"]) >= 0.10 or abs(pair["total_tokens_change"]) >= 0.10
        pair["per_model_full_minus_removal"] = {m: sum(f[c]["supported_complete"] for c in common if c[1] == m) - sum(g[c]["supported_complete"] for c in common if c[1] == m) for m in MODELS}
        result["paired"][a] = pair
        discordant[a] = [dict(task=c[0], model=c[1], seed=c[2], full_supported=f[c]["supported_complete"], removal_supported=g[c]["supported_complete"], full_trace=f[c]["trace_path"], removal_trace=g[c]["trace_path"],
                              full_run_id=f[c]["run_id"], removal_run_id=g[c]["run_id"]) for c in common if f[c]["supported_complete"] != g[c]["supported_complete"]]
    for a in ARMS:
        ex = Counter()
        for r in by_arm[a]:
            for k, v in r["exposure"].items():
                ex[k] += v
            ex["episodes_with_any_error_observation"] += error_observations(r) > 0
            ex["episodes_ended_by_error"] += r["exposure"]["ended_by_error"] > 0
            ex["answers_by_final_answer"] += r["answer_source"] == "final_answer"
            ex["answers_free_text"] += r["answer_source"] == "free_text"
            ex["episodes_with_extra_tool_calls"] += r["exposure"]["extra_tool_calls"] > 0
        result["exposure"][a] = dict(ex)
    pilot, round1 = historical()
    for a in REMOVALS:
        common = sorted(set(cells[a]) & set(pilot))
        result["historical"][a] = dict(cells=len(common), pilot_c1_supported=sum(pilot[c]["supported"] for c in common), removal_supported=sum(cells[a][c]["supported_complete"] for c in common),
                                       pilot_minus_removal=sum(pilot[c]["supported"] for c in common) - sum(cells[a][c]["supported_complete"] for c in common))
    result["historical"]["FULL_vs_pilot_c1"] = dict(cells=len(set(cells["FULL"]) & set(pilot)), pilot_c1_supported=sum(pilot[c]["supported"] for c in set(cells["FULL"]) & set(pilot)),
                                                    fresh_c1_supported=sum(cells["FULL"][c]["supported_complete"] for c in set(cells["FULL"]) & set(pilot)),
                                                    pilot_requests=sum(pilot[c]["requests"] for c in set(cells["FULL"]) & set(pilot)), pilot_tokens=sum(pilot[c]["tokens"] for c in set(cells["FULL"]) & set(pilot)))
    result["historical"]["round1_c1_seed1_supplemental"] = dict(cells=len(round1), supported=sum(v["supported"] for v in round1.values()), requests=sum(v["requests"] for v in round1.values()), tokens=sum(v["tokens"] for v in round1.values()))
    (HERE / "results.json").write_text(json.dumps(result, indent=1, default=str))
    (HERE / "DISCORDANT_CELLS.json").write_text(json.dumps(discordant, indent=1))
    L = ["# Steady-loop ablation tables (generated by analyze_ablation.py)", "", f"Episodes: {result['episodes']}", "",
         "## Per arm: tokens and requests first", "| arm | episodes | requests | tokens (in+out) | input | output | requests/episode | tokens/episode | supported | requests per supported | tokens per supported |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for a in ARMS:
        t = result["arms"][a]["total"]
        L.append(f"| {a} | {t['episodes']} | {t['requests']} | {t['tokens']:,} | {t['input_tokens']:,} | {t['output_tokens']:,} | {t['requests_per_episode']:.1f} | {t['tokens_per_episode']:,.0f} | {t['supported']} | "
                 f"{(t['requests_per_supported'] or 0):.1f} | {(t['tokens_per_supported'] or 0):,.0f} |")
    L += ["", "## Per arm: other measures", "| arm | aborts | no answer | cap hits | error observations | native ROS ops | blocked write attempts | wall seconds | missing usage |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for a in ARMS:
        t = result["arms"][a]["total"]
        L.append(f"| {a} | {t['aborts']} | {t['no_answer']} | {t['cap_hits']} | {t['error_observations']} | {t['native_ops']} | {t['blocked_write_attempts']} | {t['wall_seconds']:.0f} | {t['missing_usage']} |")
    L += ["", "## Per model: supported/10 (requests, tokens)", "| model | " + " | ".join(ARMS) + " |", "|---|" + "---|" * len(ARMS)]
    for m in MODELS:
        L.append(f"| {m} | " + " | ".join(f"{result['arms'][a]['per_model'][m]['supported']}/10 ({result['arms'][a]['per_model'][m]['requests']}, {result['arms'][a]['per_model'][m]['tokens']:,})" for a in ARMS) + " |")
    L += ["", "## Paired against fresh FULL (C1)", "| removal | cells | both | FULL only | removal only | neither | FULL minus removal | requests change | tokens change | >=10% flag |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for a in REMOVALS:
        p = result["paired"][a]
        L.append(f"| {a} | {p['cells']} | {p['both']} | {p['full_only']} | {p['removal_only']} | {p['neither']} | {p['full_minus_removal_supported']:+d} | {p['total_requests_change']:+.1%} | {p['total_tokens_change']:+.1%} | {p['efficiency_flag_10pct']} |")
    L += ["", "Matched both-supported cost (cells, requests FULL/removal, tokens FULL/removal):"]
    for a in REMOVALS:
        m = result["paired"][a]["matched_both_supported"]
        L.append(f"- {a}: {m['cells']} cells, requests {m['full_requests']}/{m['removal_requests']}, tokens {m['full_tokens']:,}/{m['removal_tokens']:,}")
    L += ["", "## Exposure (events)", "| arm | " + " | ".join(["tool_calls", "precheck_rejections", "stock_validation_errors", "coercions", "tool_exceptions", "blocked_write_attempts", "tool_not_offered", "ended_by_error", "episodes_with_any_error_observation", "episodes_with_extra_tool_calls", "answers_by_final_answer", "answers_free_text"]) + " |", "|---|" + "---:|" * 12]
    for a in ARMS:
        e = result["exposure"][a]
        L.append(f"| {a} | " + " | ".join(str(e.get(k, 0)) for k in ["tool_calls", "precheck_rejections", "stock_validation_errors", "coercions", "tool_exceptions", "blocked_write_attempts", "tool_not_offered", "ended_by_error", "episodes_with_any_error_observation", "episodes_with_extra_tool_calls", "answers_by_final_answer", "answers_free_text"]) + " |")
    L += ["", "## Historical sensitivity (pilot C1 seed 1, scorer v2.0; not a replacement for the primary comparison)", json.dumps(result["historical"], indent=1)]
    (HERE / "TABLES.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
