"""Tables for WASTE_ANALYSIS.md from waste.json (measured part). No model, no ROS."""
import json, statistics
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
e = json.loads((HERE / "waste.json").read_text())
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
ARMS = ["A1", "C1", "M0", "C1+FN", "C1+H2", "C1+H1e", "C1+H7"]
def line(m, a, s):
    n = len(s); fl = sum(x["floor"] for x in s); ex = sum(x["excess"] for x in s)
    return (f"| {m} | {a} | {n} | {sum(x['requests'] for x in s) / n:.1f} | {ex / n:+.2f} | {100 * ex / fl:.0f}% | {sum(x['input_tokens'] for x in s) / n:.0f} | {sum(x['output_tokens'] for x in s) / n:.0f} | "
            f"{sum(x['n_repeat'] for x in s)} / {sum(x['n_failed'] for x in s)} / {sum(x['n_offroute'] for x in s)} |")
print("### All supported-complete episodes (scorer v2.0)\n| model | arm | supported episodes | mean requests | mean requests above floor | excess as % of floor | mean input tokens | mean output tokens | flagged requests: repeat / failed / off-route (sums) |\n|---|---|---:|---:|---:|---:|---:|---:|---:|")
for m in MODELS:
    for a in ARMS:
        s = [x for x in e if x["model"] == m and x["arm"] == a]
        if s: print(line(m, a, s))
print("\n### Matched pairs: same model, task, seed, supported under both C1 and A1\n| model | pairs | A1 requests above floor (sum) | C1 requests above floor (sum) | A1 input tokens (sum) | C1 input tokens (sum) |\n|---|---:|---:|---:|---:|---:|")
idx = {(x["model"], x["task"], x["seed"], x["arm"]): x for x in e}
tot = [0] * 5
for m in MODELS:
    pairs = [(idx[(m, t, s, "A1")], idx[(m, t, s, "C1")]) for (mm, t, s, a) in idx if mm == m and a == "A1" and (m, t, s, "C1") in idx]
    if pairs:
        r = [len(pairs), sum(a["excess"] for a, c in pairs), sum(c["excess"] for a, c in pairs), sum(a["input_tokens"] for a, c in pairs), sum(c["input_tokens"] for a, c in pairs)]
        tot = [x + y for x, y in zip(tot, r)]; print(f"| {m} | " + " | ".join(map(str, r)) + " |")
print("| all four | " + " | ".join(map(str, tot)) + " |")
print("\n### Requests flagged by rule in C1 supported episodes (flags are per request and can overlap the floor route; not a decomposition of the excess)\n| model | C1 excess requests (sum) | repeat of an earlier successful call | contains a failed call | uses a tool outside the minimal route |\n|---|---:|---:|---:|---:|")
for m in MODELS:
    s_ = [x for x in e if x["model"] == m and x["arm"] == "C1"]
    print(f"| {m} | {sum(x['excess'] for x in s_)} | {sum(x['n_repeat'] for x in s_)} | {sum(x['n_failed'] for x in s_)} | {sum(x['n_offroute'] for x in s_)} |")
