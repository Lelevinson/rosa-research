import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
import sys
V = sys.argv[1] if len(sys.argv) > 1 else "2"
d = json.loads((HERE / f"by_cause_v{V}.json").read_text())
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
ARMS = ["C1", "A1", "M0", "C1+FN", "C1+H2", "C1+H1e", "C1+H7"]
C = ["a", "b", "c", "d", "e", "f", "g"]
def row(label, s):
    ex = sum(max(0, x["excess"]) for x in s)
    att = {c: sum(x["attributed"][c] for x in s) for c in C}
    raw = {c: sum(x["raw"].get(c, 0) for x in s) for c in C[:-1]}
    pos = sum(1 for x in s if x["excess"] > 0)
    return (f"| {label} | {len(s)} | {pos} | {ex} | " + " | ".join(f"{att[c]:.1f}" for c in C) + " | " + " / ".join(str(raw[c]) for c in C[:-1]) + " |")
hdr = "| {} | episodes | with excess > 0 | above-floor requests (sum over those) | (a) batching | (b) name form | (c) re-lookup | (d) repeat | (e) bad args | (f) wrong tool/pattern | (g) other | raw tags a / b / c / d / e / f |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
for arm in ("C1", "A1"):
    print(f"### Arm {arm} (attributed above-floor requests per cause; raw tagged requests in the last column)\n" + hdr.format("model"))
    for m in MODELS:
        s = [x for x in d if x["model"] == m and x["arm"] == arm]
        if s: print(row(m, s))
    s = [x for x in d if x["arm"] == arm]; print(row("all four", s)); print()
print("### Appendix: all arms, all four models pooled\n" + hdr.format("arm"))
for arm in ARMS:
    print(row(arm, [x for x in d if x["arm"] == arm]))
