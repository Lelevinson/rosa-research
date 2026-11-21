"""Tables for REPORT.md: stock ROSA verbatim prompt (S0) vs fixed-loop rerun (build round 1 control) vs A1 (pilot, scorer v2.0 labels). No model.  python3 report_s0.py"""
import json
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent; ST = HERE.parent
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
s0 = [r for r in map(json.loads, (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()) if r["phase"] == "full"]
c1 = [r for r in map(json.loads, (ST / "build_round1_20261115/RESULTS_LOG.jsonl").read_text().splitlines()) if r["phase"] == "full" and r["arm"] == "C1"]
cmp_ = json.loads((ST / "forge_baseline_20261115/SAME_CELL_COMPARISON.json").read_text())
a1 = [dict(c["A1"], model=c["cell"]["model"], task=c["cell"]["task"], seed=c["cell"]["seed"]) for c in cmp_]
cell = lambda r: (r["model"], r["task"], r["seed"])
tok = lambda r: r["input_tokens"] + r["output_tokens"]
arms = {"stock ROSA, verbatim prompt (S0, this run)": s0, "fixed loop (build round 1 control)": c1, "stock executor, deconflicted prompt (A1, pilot)": a1}
print(f"S0 episodes logged: {len(s0)} of 80\n\n| model | arm | episodes | supported-complete | LLM requests | tokens (in+out) | episodes with an abort/error |\n|---|---|---:|---:|---:|---:|---:|")
for m in MODELS + ["all four"]:
    for name, rows in arms.items():
        s = [r for r in rows if m == "all four" or r["model"] == m]
        print(f"| {m} | {name} | {len(s)} | {sum(r['supported_complete'] for r in s)} | {sum(r['llm_requests'] for r in s)} | {sum(map(tok, s))} | {sum(bool(r['aborts']) for r in s)} |")
S0 = {cell(r): r for r in s0}
for name, rows in list(arms.items())[1:]:
    other = {cell(r): r for r in rows}
    common = [c for c in S0 if c in other]
    b = sum(S0[c]["supported_complete"] and other[c]["supported_complete"] for c in common)
    o = sum(S0[c]["supported_complete"] and not other[c]["supported_complete"] for c in common)
    k = sum(not S0[c]["supported_complete"] and other[c]["supported_complete"] for c in common)
    print(f"\nSame-cell, S0 vs {name}: both supported {b}, only S0 {o}, only comparator {k}, neither {len(common) - b - o - k} (cells {len(common)})")
ab = defaultdict(int)
for r in s0:
    for a in r["aborts"]:
        ab[a.split("(")[0][:60] if not a.startswith("1 validation") else "validation error: " + a.split("\n")[1][:40]] += 1
print("\nS0 abort/error kinds:", dict(ab))
print("\nPer-cell (supported / requests): S0, fixed loop, A1\n\n| model | task | seed | S0 | fixed loop | A1 |\n|---|---|---:|---|---|---|")
C1 = {cell(r): r for r in c1}; A1 = {cell(r): r for r in a1}
for c in sorted(S0, key=lambda c: (MODELS.index(c[0]), c[1], c[2])):
    f = lambda d: f"{'Y' if d[c]['supported_complete'] else 'n'} / {d[c]['llm_requests']}" if c in d else "-"
    print(f"| {c[0]} | {c[1]} | {c[2]} | {f(S0)} | {f(C1)} | {f(A1)} |")
