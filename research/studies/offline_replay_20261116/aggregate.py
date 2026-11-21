"""Aggregate results.json into tables (printed as Markdown).  python3 aggregate.py"""
import json
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "results.json").read_text())["episodes"]
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
def slices():
    yield "all four models", R
    for m in MODELS: yield m, [e for e in R if e["model"] == m]
tot_req = sum(e["requests"] for e in R); tot_tok = sum(e["tokens"] for e in R)
print(f"Episodes {len(R)} (supported {sum(e['supported'] for e in R)}); fixed-loop requests {tot_req}, tokens {tot_tok}\n")
for v, name in (("p1_v1", "V1 (two consecutive calls)"), ("p1_v2", "V2 (one call, group of 2 to 4 names)")):
    print(f"### Proposal 1, {name}\n\n| model | episodes | episodes with a trigger | triggers | median group size | median sweep size | requests after first trigger (sum) | predicted saved requests | % of requests | saved tokens | extra tokens | extra tool runs |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for m, s in slices():
        gs = [x for e in s for x in e[v]["group_sizes"]]; ss = [x for e in s for x in e[v]["sweep_sizes"]]
        med = lambda l: sorted(l)[len(l)//2] if l else "-"
        rq = sum(e["requests"] for e in s); sv = sum(e[v]["saved_requests"] for e in s)
        print(f"| {m} | {len(s)} | {sum(e[v]['triggers']>0 for e in s)} | {sum(e[v]['triggers'] for e in s)} | {med(gs)} | {med(ss)} | {sum(e[v]['requests_after_trigger'] for e in s)} | {sv} | {100*sv/rq:.1f} | {sum(e[v]['saved_tokens'] for e in s)} | {sum(e[v]['extra_tokens'] for e in s):.0f} | {sum(e[v]['extra_executions'] for e in s):.0f} |")
    print()
print("### Proposal 2, stall breaker\n\n| model | episodes | stalls rule (a) | stalls (a') | stalls (b) | episodes with a stall (a or b) | supported episodes with a stall | requests after first stall | second stalls | hides that remove a useful call (all) | in supported episodes |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for m, s in slices():
    st = [e for e in s if e["p2"]["stalled_tools"]]
    print(f"| {m} | {len(s)} | {sum(e['p2']['stalls_a'] for e in s)} | {sum(e['p2']['stalls_a2'] for e in s)} | {sum(e['p2']['stalls_b'] for e in s)} | {len(st)} | {sum(e['supported'] for e in st)} | {sum(e['p2']['requests_after_first'] for e in s)} | {sum(e['p2']['second_stalls'] for e in s)} | {sum(e['p2']['hide_useful'] for e in s)} | {sum(e['p2']['hide_useful'] for e in s if e['supported'])} |")
print("\n### Proposal 3, answer rewrite\n\n| model | answers | unchanged | rewritten | would reject | supported before, rewritten | supported after rewrite | unsupported -> supported | supported -> unsupported | supported answers that would be rejected | rejects with a ledger next step |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for m, s in slices():
    p = [e for e in s if e["p3"]["status"] != "no_answer"]
    rw = [e for e in p if e["p3"]["status"] == "rewritten"]; rj = [e for e in p if e["p3"]["status"] == "reject"]
    print(f"| {m} | {len(p)} | {sum(e['p3']['status']=='unchanged' for e in p)} | {len(rw)} | {len(rj)} | {sum(e['supported'] for e in rw)} | {sum(e['p3']['supported_after'] for e in rw)} | {sum((not e['supported']) and e['p3']['supported_after'] for e in rw)} | {sum(e['supported'] and not e['p3']['supported_after'] for e in rw)} | {sum(e['supported'] for e in rj)} | {sum(1 for e in rj if any(x['kind']=='reject_never_seen' for x in e['p3']['rejects']) and e['p3']['has_next_step'])} of {sum(1 for e in rj if any(x['kind']=='reject_never_seen' for x in e['p3']['rejects']))} |")

print("\n### Concentration (the 400 episodes are 80 cells run up to 5 times each)\n")
for v in ("p1_v1", "p1_v2"):
    cells = defaultdict(int)
    for e in R: cells[(e["model"], e["task"], e["seed"])] += e[v]["saved_requests"]
    top = sorted(cells.items(), key=lambda kv: -kv[1])[:5]; total = sum(cells.values())
    sup = sum(e[v]["saved_requests"] for e in R if e["supported"]); uns = total - sup
    print(f"- {v}: saved requests {total} in {sum(1 for x in cells.values() if x)} distinct cells; in supported episodes {sup}, in unsupported {uns}; top 5 cells = {sum(x for _, x in top)} ({100*sum(x for _, x in top)/max(total,1):.0f}%): " + ", ".join(f"{k[0]} {k[1]} s{k[2]}={x}" for k, x in top))
    pc = defaultdict(int); [pc.__setitem__(e["task"], pc[e["task"]] + e[v]["saved_requests"]) for e in R]
    print("  by task:", dict(sorted(pc.items(), key=lambda kv: -kv[1])))
cells = {(e["model"], e["task"], e["seed"]) for e in R if e["p3"]["status"] == "rewritten"}
print(f"- proposal 3: rewritten episodes {sum(e['p3']['status']=='rewritten' for e in R)} come from {len(cells)} distinct cell(s): {sorted(cells)}; would-reject episodes come from {len({(e['model'], e['task'], e['seed']) for e in R if e['p3']['status']=='reject'})} cells")
sc = {(e["model"], e["task"], e["seed"]) for e in R if e["p2"]["hide_useful"] and e["supported"]}
print(f"- proposal 2: supported episodes where hiding removes a useful call: {sum(1 for e in R if e['p2']['hide_useful'] and e['supported'])} episodes in cells {sorted(sc)}")
