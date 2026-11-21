"""Aggregate results.json into REPORT.md against the frozen bar (PROTOCOL.md). No reinterpretation."""
import json, statistics
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
eps = json.loads((HERE / "results.json").read_text())
MODELS = ["lfm3:1.7b", "bonsai-2:4b", "gpt-oss:20b", "qwen3.5:9b"]
BAR_MODELS = MODELS[:3]
lines = []
P = lines.append


def agg(sel, v):
    req = sum(e["requests"] for e in sel); rem = sum(e[v]["removable"] for e in sel); nf = sum(e["nonfinal_requests"] for e in sel)
    nets = [e[v]["net_tokens"] for e in sel]
    return dict(n=len(sel), req=req, rem=rem, pct=100 * rem / req if req else 0, pct_nf=100 * rem / nf if nf else 0, saved=sum(e[v]["saved_tokens"] for e in sel),
                added=sum(e[v]["added_tokens"] for e in sel), net_mean=statistics.mean(nets), net_median=statistics.median(nets))


verdicts = {}
P("# REPORT: structure-snapshot offline replay\n")
P("Protocol and bar frozen before any number (`PROTOCOL.md`, `FREEZE.json`). Offline replay of 80 pilot C1 episodes (20 per model); development evidence on a synthetic fixture; no model, no GPU. The snapshot text was captured with the real ROSA read tools on the two fixtures (`snapshots.json`): Stage 3 fixture 19 nodes, E1h fixture 14 nodes.\n")
for v, label in (("A", "Variant A (node_list, topic_list, service_list, node_info of every node)"), ("B", "Variant B (A plus param_list names per node)")):
    snaptok = {e: round(json.loads((HERE / 'snapshots.json').read_text())[e][v] and len(json.dumps(json.loads((HERE / 'snapshots.json').read_text())[e][v])) / 4) for e in ("stage3", "e1h")}
    P(f"## {label}\nSnapshot size: {snaptok['stage3']} tokens (Stage 3 fixture), {snaptok['e1h']} tokens (E1h fixture), chars/4.\n")
    P("| model | episodes | requests | removable | removable % of all requests | % of non-final requests | input tokens of removed requests (sum) | snapshot tokens charged (sum) | net per episode, mean | net per episode, median |")
    P("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    res = {}
    for m in MODELS:
        a = agg([e for e in eps if e["model"] == m], v); res[m] = a
        P(f"| {m} | {a['n']} | {a['req']} | {a['rem']} | {a['pct']:.1f}% | {a['pct_nf']:.1f}% | {a['saved']:.0f} | {a['added']:.0f} | {a['net_mean']:+.0f} | {a['net_median']:+.0f} |")
    meets = [m for m in BAR_MODELS if res[m]["pct"] >= 25]
    cond1 = len(meets) >= 2
    cond2 = cond1 and all(res[m]["net_mean"] <= 0 for m in meets)
    verdicts[v] = cond1 and cond2
    P(f"\n**Bar for variant {v}:** (1) removable >= 25% for at least 2 of lfm3, bonsai, gpt-oss: models meeting it = {meets or 'none'} -> {'met' if cond1 else 'NOT met'}. "
      f"(2) mean net input tokens per episode <= 0 for each such model: " + (", ".join(f"{m} {res[m]['net_mean']:+.0f}" for m in meets) if meets else "not evaluable (no model meets (1)); for reference the three bar models have " + ", ".join(f"{m} {res[m]['net_mean']:+.0f}" for m in BAR_MODELS)) + f" -> {'met' if cond2 else 'NOT met'}. **Variant {v}: {'PASS' if verdicts[v] else 'FAIL'}.**\n")
    P(f"Per task (removable requests / all requests, over the models' episodes, then net tokens per episode mean over the four models):\n")
    P("| task | " + " | ".join(MODELS) + " | net tokens per episode (mean, 4 models) |"); P("|---|" + "---:|" * (len(MODELS) + 1))
    for t in sorted({e["task"] for e in eps}):
        cells = []
        for m in MODELS:
            sel = [e for e in eps if e["model"] == m and e["task"] == t]; a = agg(sel, v)
            cells.append(f"{a['rem']}/{a['req']} ({a['pct']:.0f}%)")
        allsel = [e for e in eps if e["task"] == t]
        P(f"| {t} | " + " | ".join(cells) + f" | {statistics.mean(e[v]['net_tokens'] for e in allsel):+.0f} |")
    P("")
d = "A_topicinfo_derivable"
P("## Exploratory only (not used for the bar): ros2_topic_info counted as derivable from the snapshot\n")
P("| model | removable % of all requests | net per episode, mean |\n|---|---:|---:|")
for m in MODELS:
    a = agg([e for e in eps if e["model"] == m], d)
    P(f"| {m} | {a['pct']:.1f}% | {a['net_mean']:+.0f} |")
P("")
P("## Verdict against the frozen bar\n")
P(f"- Variant A: **{'PASS' if verdicts['A'] else 'FAIL'}**\n- Variant B: **{'PASS' if verdicts['B'] else 'FAIL'}**\n")
P("## What makes the numbers optimistic or pessimistic\n- Pessimistic: removed requests are credited only with their own recorded input tokens; the shorter inputs of later requests (they would no longer carry the removed tool results) are not credited. Not modeled: the model's behaviour with the snapshot in context (a different model run).\n- Optimistic: requests judged independently, so a request that would only exist because an earlier removed request's result was needed is still counted as removable; calls that returned not-found errors for bare names count as answered by the snapshot's absence proof; the fixtures are small (19 and 14 nodes) and the snapshot grows with graph size; Stage 3 tasks are discovery-heavy by design.\n- One analyst; chars/4 token estimate; C1 episodes only (20 per model, 2 seeds), whose request counts are noisy (pilot noise floor).\n")
(HERE / "REPORT.md").write_text("\n".join(lines))
print("\n".join(lines))
