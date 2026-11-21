"""Tables for REPORT.md from RESULTS_LOG.jsonl (phase 'full' only). No model, no ROS.   uv run python report_round1.py > REPORT_TABLES.md"""
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
rows = [r for r in rows if r["phase"] == "full"]
ARMS = ["C1", "C1+AG", "C1+LA", "C1+AG+LA"]
NAME = {"C1": "fixed loop (fresh control)", "C1+AG": "+ answer gate", "C1+LA": "+ list arguments", "C1+AG+LA": "+ both"}
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
cell = lambda r: (r["model"], r["task"], r["seed"])
by = defaultdict(dict)
for r in rows:
    by[r["arm"]][cell(r)] = r
tok = lambda r: r["input_tokens"] + r["output_tokens"]
crash = lambda r: bool(r["aborts"])
print(f"Episodes logged (full): {len(rows)} of 320; per arm: " + ", ".join(f"{a} {len(by[a])}" for a in ARMS) + "\n")
print("## Per model and arm\n\n| model | arm | episodes | supported-complete | LLM requests | tokens (in+out) | episodes with an abort/error |\n|---|---|---:|---:|---:|---:|---:|")
for m in MODELS + ["all four"]:
    for a in ARMS:
        s = [r for r in by[a].values() if m == "all four" or r["model"] == m]
        print(f"| {m} | {NAME[a]} | {len(s)} | {sum(r['supported_complete'] for r in s)} | {sum(r['llm_requests'] for r in s)} | {sum(map(tok, s))} | {sum(map(crash, s))} |")
print("\n## Same-cell comparison with the fresh control (supported-complete)\n\n| arm | both supported | only arm | only control | neither | requests arm-control | tokens arm-control |\n|---|---:|---:|---:|---:|---:|---:|")
for a in ARMS[1:]:
    common = [c for c in by[a] if c in by["C1"]]
    b = sum(by[a][c]["supported_complete"] and by["C1"][c]["supported_complete"] for c in common)
    o = sum(by[a][c]["supported_complete"] and not by["C1"][c]["supported_complete"] for c in common)
    k = sum(not by[a][c]["supported_complete"] and by["C1"][c]["supported_complete"] for c in common)
    n = len(common) - b - o - k
    print(f"| {NAME[a]} | {b} | {o} | {k} | {n} | {sum(by[a][c]['llm_requests'] - by['C1'][c]['llm_requests'] for c in common):+d} | {sum(tok(by[a][c]) - tok(by['C1'][c]) for c in common):+d} |")
print("\n## Answer gate firings (arms with the gate)\n")
for a in ("C1+AG", "C1+AG+LA"):
    ev = [(r, g) for r in by[a].values() for g in r["gate"]]
    rej = [(r, g) for r, g in ev if g["event"] == "gate_reject"]
    nud = [(r, g) for r, g in ev if g["event"] == "bare_text_nudge"]
    fol = [(r, g) for r, g in ev if g["event"] == "gate_followup"]
    lim = [(r, g) for r, g in ev if g["event"] == "gate_accepted_after_limit"]
    print(f"- {NAME[a]}: rejections {len(rej)} in {len({r['run_id'] for r, _ in rej})} episodes; nudges {len(nud)} in {len({r['run_id'] for r, _ in nud})} episodes; accepted after limit {len(lim)}; answer changed after a rejection {sum(g['changed'] for _, g in fol)} of {len(fol)}")
    for r, g in rej:
        ctrl = by["C1"].get(cell(r))
        print(f"  - {r['model']} {r['task']} s{r['seed']}: rejected {json.dumps(g['answer'])[:140]} rules {[p['rule'] for p in g['problems']]}; final supported {r['supported_complete']}; control supported {ctrl['supported_complete'] if ctrl else None}; {r['run_id']}")
    for r, g in nud:
        ctrl = by["C1"].get(cell(r))
        print(f"  - nudge {g['number']}: {r['model']} {r['task']} s{r['seed']}; final supported {r['supported_complete']}; control supported {ctrl['supported_complete'] if ctrl else None}; {r['run_id']}")
print("\nShadow gate in arms without it (would it have rejected?):")
for a in ("C1", "C1+LA"):
    sh = [(r, g) for r in by[a].values() for g in r["gate"] if g["event"] == "gate_shadow"]
    wr = [(r, g) for r, g in sh if g["would_reject"]]
    print(f"- {NAME[a]}: {len(sh)} final answers checked, would reject {len(wr)}; of those supported-complete (= false rejections) {sum(r['supported_complete'] for r, _ in wr)}")
    for r, g in wr:
        print(f"  - {r['model']} {r['task']} s{r['seed']} supported {r['supported_complete']} rules {[p['rule'] for p in g['problems']]} {json.dumps(g['answer'])[:120]}")
unseen = [(r["arm"], r["run_id"], r["supported_complete"], g["numbers_unseen"]) for a in ARMS for r in by[a].values() for g in r["gate"] if g.get("numbers_unseen")]
print(f"\nNumbers log-only: {len(unseen)} final answers contained an integer not seen in a tool result or the task: " + json.dumps(unseen)[:600])
print("\n## List-argument adoption\n\n| arm | episodes | episodes with a list call | tool calls | list calls | items per list call | requests/episode | tokens/episode |\n|---|---:|---:|---:|---:|---:|---:|---:|")
for a in ARMS:
    s = list(by[a].values())
    lc, li, tc = sum(r["list_calls"] for r in s), sum(r["list_items"] for r in s), sum(r["tool_calls"] for r in s)
    print(f"| {NAME[a]} | {len(s)} | {sum(r['list_calls'] > 0 for r in s)} | {tc} | {lc} | {li / lc:.2f} | {sum(r['llm_requests'] for r in s) / max(len(s), 1):.2f} | {sum(map(tok, s)) / max(len(s), 1):.0f} |" if lc else
          f"| {NAME[a]} | {len(s)} | {sum(r['list_calls'] > 0 for r in s)} | {tc} | 0 | - | {sum(r['llm_requests'] for r in s) / max(len(s), 1):.2f} | {sum(map(tok, s)) / max(len(s), 1):.0f} |")
print("\n## Per-cell table (supported / requests): control, gate, lists, both\n\n| model | task | seed | " + " | ".join(ARMS) + " |\n|---|---|---:|---|---|---|---|")
for c in sorted(by["C1"], key=lambda c: (MODELS.index(c[0]), c[1], c[2])):
    print(f"| {c[0]} | {c[1]} | {c[2]} | " + " | ".join((f"{'Y' if by[a][c]['supported_complete'] else 'n'} / {by[a][c]['llm_requests']}" if c in by[a] else "-") for a in ARMS) + " |")
