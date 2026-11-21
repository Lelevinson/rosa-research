"""Analysis of the replication (amendment A2): applies the frozen reading rules of PROTOCOL.md section 5 and AMENDMENT_A2.md section 2. Written and hashed BEFORE the first episode of the replication.
  uv run python research/studies/thinking_escalation_20261119/analyze_replication.py
Reads RESULTS_LOG.jsonl (phase partA = part A, phase replA2 = replication) and the traces; writes results_replication.json and REPLICATION_TABLES.md. CPU only.
 R1 = ESCALATE against FULL on the replication's 18 tasks (seeds 3-4); R2 = the same on the 10 shared tasks with part A added (seeds 1-4); per model; task-clustered bootstrap intervals;
 gpt-oss rows are marked "not interpretable" and a pooled version without gpt-oss is shown; design check ESCALATE_CAPPED against ESCALATE (descriptive, no class)."""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import analyze_think as N  # noqa: E402  (the frozen part A functions: episode_metrics, aggregate, decide)

SHARED_TASKS = {"u3", "p3", "h4", "v2", "e1h_amb_1", "e1h_amb_2", "e1h_abs_1", "e1h_abs_2", "e1h_chg_1", "e1h_chg_2"}
GPT_OSS = "gpt-oss:20b"
BOOTSTRAP_DRAWS, BOOTSTRAP_SEED = 5000, 20261119
RUNAWAY_THINKING_REQUESTS = 10


def runaway(levels, done_reasons):
    """Amendment A2: an episode with at least 10 requests sent with thinking on, or a length-cut response while thinking was on."""
    on = [lv is not None for lv in levels]
    cut_while_on = any(on[i] and reason == "length" for i, reason in enumerate(done_reasons) if i < len(on))
    return sum(on) >= RUNAWAY_THINKING_REQUESTS or cut_while_on


def extra(trace):
    events = [json.loads(line) for line in (ROOT / trace).read_text().splitlines()]
    level = {e["request"]: e["level"] for e in events if e["kind"] == "handler" and e.get("event") == "think_request"}
    ends = [e for e in events if e["kind"] == "model_end"]
    levels = [level.get(i) for i in range(1, len(ends) + 1)]
    reasons = [(e.get("response_metadata") or {}).get("done_reason") for e in ends]
    return dict(runaway=runaway(levels, reasons), cap_reached=any(e["kind"] == "handler" and e.get("event") == "cap_reached" for e in events), thinking_on_requests=sum(lv is not None for lv in levels))


def episode(row):
    m = N.episode_metrics(row)
    m.update(extra(row["trace_path"]))
    first = [f["outcome"][1] for f in m["fires"] if f["outcome"][1] is not None]
    m["O2_hits"], m["O2_events"] = sum(o["O2"] for o in first), len(first)
    return m


def cluster_intervals(rows, arm_a="FULL", arm_b="ESCALATE", draws=BOOTSTRAP_DRAWS, seed=BOOTSTRAP_SEED):
    """Cluster bootstrap over TASKS for arm_b against arm_a: supported difference (points), request ratio, token ratio, O2 difference (points). A task carries all its models, seeds and episodes."""
    by = defaultdict(lambda: defaultdict(lambda: dict(n=0, sup=0, req=0, tok=0, o2=0, ev=0)))
    for r in rows:
        if r["arm"] not in (arm_a, arm_b):
            continue
        s = by[r["task"]][r["arm"]]
        s["n"] += 1; s["sup"] += r["supported"]; s["req"] += r["requests"]; s["tok"] += r["input_tokens"] + r["output_tokens"]; s["o2"] += r["O2_hits"]; s["ev"] += r["O2_events"]
    tasks = sorted(t for t in by if by[t][arm_a]["n"] and by[t][arm_b]["n"])
    if len(tasks) < 2:
        return None

    def stats(sample):
        a = {k: sum(by[t][arm_a][k] for t in sample) for k in ("n", "sup", "req", "tok", "o2", "ev")}
        b = {k: sum(by[t][arm_b][k] for t in sample) for k in ("n", "sup", "req", "tok", "o2", "ev")}
        out = dict(diff_points=100 * (b["sup"] / b["n"] - a["sup"] / a["n"]), request_ratio=b["req"] / a["req"] if a["req"] else None, token_ratio=b["tok"] / a["tok"] if a["tok"] else None,
                   o2_diff_points=100 * (b["o2"] / b["ev"] - a["o2"] / a["ev"]) if a["ev"] and b["ev"] else None)
        return out

    point = stats(tasks)
    rng = random.Random(seed)
    samples = [stats([rng.choice(tasks) for _ in tasks]) for _ in range(draws)]
    interval = {}
    for key in point:
        values = sorted(s[key] for s in samples if s[key] is not None)
        interval[key] = [round(values[int(0.025 * len(values))], 3), round(values[min(len(values) - 1, int(0.975 * len(values)))], 3)] if values else None
    return dict(tasks=len(tasks), point={k: (round(v, 3) if v is not None else None) for k, v in point.items()}, interval_95=interval)


def arm_tables(rows, arms):
    models = sorted({r["model"] for r in rows})
    tables = {}
    for arm in arms:
        sel = [r for r in rows if r["arm"] == arm]
        tables[arm] = dict(overall=N.aggregate(sel), by_model={m: N.aggregate([r for r in sel if r["model"] == m]) for m in models})
    return tables


def reading(rows, label):
    """ESCALATE against FULL with the unchanged frozen rule (decide), pooled, per model, and pooled without gpt-oss."""
    out = {}
    for variant, sel in (("all_models", rows), ("without_gpt_oss", [r for r in rows if r["model"] != GPT_OSS])):
        tables = arm_tables(sel, ("FULL", "ESCALATE"))
        empty = N.aggregate([])
        decision = N.decide(dict(FULL=tables["FULL"]["overall"], ESCALATE=tables["ESCALATE"]["overall"], ALWAYS=empty),
                            dict(FULL=tables["FULL"]["by_model"], ESCALATE=tables["ESCALATE"]["by_model"], ALWAYS={}))
        pairs = defaultdict(dict)
        for r in sel:
            if r["arm"] in ("FULL", "ESCALATE"):
                pairs[(r["task"], r["model"], r["seed"])][r["arm"]] = r["supported"]
        paired = defaultdict(int)
        for p in pairs.values():
            if len(p) == 2:
                paired["both" if p["FULL"] and p["ESCALATE"] else "FULL_only" if p["FULL"] else "ESCALATE_only" if p["ESCALATE"] else "neither"] += 1
        out[variant] = dict(label=label, tables=tables, decision=decision, paired=dict(paired), clustered=cluster_intervals(sel))
    out["per_model_clustered"] = {m: cluster_intervals([r for r in rows if r["model"] == m]) for m in sorted({r["model"] for r in rows})}
    out["gpt_oss_note"] = "gpt-oss contrasts are NOT INTERPRETABLE (request 1 differed between arms in 16 of 20 part A cells with identical prompt and settings; its false level is medium-like and not recorded)"
    return out


def design_check(rows):
    models = sorted({r["model"] for r in rows})
    arms = ("ESCALATE", "ESCALATE_CAPPED")

    def block(sel):
        a = N.aggregate(sel)
        a.update(runaway_episodes=sum(r["runaway"] for r in sel), cap_reached_episodes=sum(r["cap_reached"] for r in sel), thinking_on_requests_total=sum(r["thinking_on_requests"] for r in sel),
                 tokens_in_out=a["input_tokens"] + a["output_tokens"],
                 thinking_est_per_escalated_request=(a["escalated_output_tokens"] / a["thinking_requests"]) if a["thinking_requests"] else None)
        return a
    return {arm: dict(overall=block([r for r in rows if r["arm"] == arm]), by_model={m: block([r for r in rows if r["arm"] == arm and r["model"] == m]) for m in models}) for arm in arms}


def tables_md(result):
    lines = ["# Replication tables (amendment A2). Generated by analyze_replication.py; aggregates only.", ""]
    for key, title in (("R1", "R1: ESCALATE against FULL, replication episodes, 18 tasks, seeds 3-4"), ("R2", "R2: ESCALATE against FULL, 10 shared tasks, seeds 1-4 (part A + replication)")):
        block = result.get(key)
        if not block:
            continue
        lines += [f"## {title}", ""]
        for variant in ("all_models", "without_gpt_oss"):
            d = block[variant]
            dec, f, e = d["decision"], d["tables"]["FULL"]["overall"], d["tables"]["ESCALATE"]["overall"]
            lines += [f"### {variant}", "", f"class **{dec['klass']}**; mechanism {dec['mechanism_met']} (pooled O2 gain {dec['pooled_O2_gain']}); harm flags {dec['harm_flags']}; cost flags {dec['cost_flags']}; paired {d['paired']}", "",
                      "| | FULL | ESCALATE |", "|---|---|---|"]
            for k in ("episodes", "supported", "requests", "input_tokens", "output_tokens", "thinking_tokens_est", "wall_seconds", "capped", "no_answer", "backend_errors", "length_cuts", "fires", "events_with_next", "O2_rate", "thinking_requests"):
                lines.append(f"| {k} | {f[k]} | {e[k]} |")
            lines += ["", f"task-clustered (95%): {json.dumps(d['clustered'])}", ""]
        lines += ["per model (FULL -> ESCALATE; **gpt-oss not interpretable**):", ""]
        for m, v in block["all_models"]["decision"]["per_model"].items():
            tag = " NOT INTERPRETABLE" if m == GPT_OSS else ""
            lines.append(f"- {m}{tag}: {json.dumps(v)}; clustered {json.dumps(block['per_model_clustered'].get(m))}")
        lines.append("")
    dc = result.get("design_check")
    if dc:
        lines += ["## Design check: ESCALATE_CAPPED against ESCALATE (replication, descriptive, no class)", "", "| | ESCALATE | ESCALATE_CAPPED |", "|---|---|---|"]
        for k in ("episodes", "supported", "requests", "tokens_in_out", "output_tokens", "thinking_tokens_est", "thinking_requests", "escalated_output_tokens", "runaway_episodes", "cap_reached_episodes", "no_answer", "capped", "backend_errors", "length_cuts", "wall_seconds"):
            lines.append(f"| {k} | {dc['ESCALATE']['overall'][k]} | {dc['ESCALATE_CAPPED']['overall'][k]} |")
        lines.append("")
        for m in dc["ESCALATE"]["by_model"]:
            tag = " (gpt-oss: not interpretable)" if m == GPT_OSS else ""
            lines.append(f"- {m}{tag}: runaway {dc['ESCALATE']['by_model'][m]['runaway_episodes']} -> {dc['ESCALATE_CAPPED']['by_model'][m]['runaway_episodes']}, thinking tokens est {dc['ESCALATE']['by_model'][m]['thinking_tokens_est']} -> {dc['ESCALATE_CAPPED']['by_model'][m]['thinking_tokens_est']}, no-answer {dc['ESCALATE']['by_model'][m]['no_answer']} -> {dc['ESCALATE_CAPPED']['by_model'][m]['no_answer']}")
    return "\n".join(lines)


def main():
    raw = [json.loads(line) for line in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines() if line.strip()]
    part_a = [episode(r) for r in raw if r.get("phase") == "partA"]
    repl = [episode(r) for r in raw if r.get("phase") == "replA2"]
    result = dict(protocol="PROTOCOL.md + AMENDMENT_A1.md + AMENDMENT_A2.md", episodes=dict(partA=len(part_a), replA2=len(repl)))
    if repl:
        result["R1"] = reading([r for r in repl if r["arm"] in ("FULL", "ESCALATE")], "replication, 18 tasks, seeds 3-4")
        shared = [r for r in repl + part_a if r["task"] in SHARED_TASKS and r["arm"] in ("FULL", "ESCALATE")]
        result["R2"] = reading(shared, "10 shared tasks, seeds 1-4 (part A + replication)")
        result["design_check"] = design_check([r for r in repl if r["arm"] in ("ESCALATE", "ESCALATE_CAPPED")])
        result["episode_rows"] = [{k: v for k, v in r.items() if k != "fires"} for r in repl]
    (HERE / "results_replication.json").write_text(json.dumps(result, indent=1, default=str))
    (HERE / "REPLICATION_TABLES.md").write_text(tables_md(result))
    print(json.dumps({k: result[k] for k in result if k not in ("episode_rows",)}, default=str)[:3000])


if __name__ == "__main__":
    main()
