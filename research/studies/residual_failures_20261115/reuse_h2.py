"""Parts 2 and 3 of WASTE_BY_CAUSE: reuse (H1e/H1n) and name fixer (H2), measured from handler events in the traces. No model, no ROS."""
import json, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); import view, scorer_v2 as v2
resc = {x["run_id"]: x for x in json.loads((HERE / "rescore_v2.json").read_text())}
rows = [json.loads(l) for l in (view.PILOT / "RESULTS_LOG.jsonl").read_text().splitlines()]
rows = [r for r in rows if r["run_id"] not in view.EXC]
cell = {(r["model"], r["task"], r["seed"], r["arm"]): r for r in rows}

def events(r): return [json.loads(l) for l in (view.REPO / r["trace_path"]).read_text().splitlines()]

def per_request(ev):
    """request index (1-based) -> dict(calls=[...], reuse=count, h2=...)"""
    k, reqs = 0, {}
    for e in ev:
        if e["kind"] == "model_start": pass
        if e["kind"] == "model_end":
            k += 1; reqs[k] = dict(ncalls=len(e["message"].get("tool_calls", [])), reuse=0, repair=0, line=None)
        elif e["kind"] == "handler" and k:
            if e["event"] == "reuse": reqs[k]["reuse"] += 1
            if e["event"] == "h2_repair": reqs[k]["repair"] += 1
    return reqs

print("## PART 2: reuse")
tot = defaultdict(int); table = []
for r in rows:
    if r["arm"] not in ("C1+H1e", "C1+H1n"): continue
    ev = events(r); rq = per_request(ev); n = sum(q["reuse"] for q in rq.values())
    c1 = cell.get((r["model"], r["task"], r["seed"], "C1"))
    whole = sum(1 for q in rq.values() if q["reuse"] and q["reuse"] == q["ncalls"])
    partial = sum(1 for q in rq.values() if q["reuse"] and q["reuse"] < q["ncalls"])
    consecutive = 0; best = 0
    for k in sorted(rq):
        consecutive = consecutive + 1 if rq[k]["reuse"] else 0; best = max(best, consecutive)
    blocked = sum(1 for e in ev if e["kind"] == "handler" and e["event"] == "reuse_blocked")
    key = r["arm"]; tot[key + "_episodes"] += 1; tot[key + "_fired_ep"] += n > 0; tot[key + "_events"] += n; tot[key + "_whole"] += whole; tot[key + "_partial"] += partial; tot[key + "_blocked"] += blocked
    tot[key + "_native_saved"] += n   # each reuse replaced exactly one native ros2 call
    if n: table.append((r["run_id"], r["arm"], r["task"], r["seed"], n, whole, partial, best, r["llm_requests"], c1["llm_requests"] if c1 else None, r["native_ops"], c1["native_ops"] if c1 else None))
for k, v in sorted(tot.items()): print(" ", k, v)
print("\nepisodes with reuse (run, arm, task, seed, reuse events, requests that were ONLY reused calls, requests with reused + other calls, longest run of consecutive reuse requests, LLM requests, C1 same cell requests, native ops, C1 same cell native ops):")
for t in table: print(" ", t)

print("\n## PART 3: H2")
fired = []; norep = 0; repairs = []
for r in rows:
    if r["arm"] != "C1+H2": continue
    ev = events(r); rq = per_request(ev)
    for e in ev:
        if e["kind"] == "handler" and e["event"] == "h2_no_repair": norep += 1
    n = sum(q["repair"] for q in rq.values())
    # repair results: effective_call event, then the tool_end that follows
    k = 0
    for i, e in enumerate(ev):
        if e["kind"] == "handler" and e["event"] == "h2_repair":
            j = i
            while j < len(ev) and ev[j]["kind"] != "tool_end": j += 1
            out = ev[j]["output"] if j < len(ev) else None
            ok = not (isinstance(out, dict) and ("error" in out or any(isinstance(v, dict) and "error" in v for v in out.values())))
            repairs.append(dict(run=r["run_id"], task=r["task"], seed=r["seed"], given=e["given"], resolved=e["resolved"], tool=e["tool"], result_ok=ok, supported=resc[r["run_id"]]["new"]))
    if n:
        c1 = cell.get((r["model"], r["task"], r["seed"], "C1"))
        fired.append(dict(run=r["run_id"], model=r["model"], task=r["task"], seed=r["seed"], repairs=n, req_requests=sum(1 for q in rq.values() if q["repair"]), h2_requests=r["llm_requests"],
                          c1_requests=c1["llm_requests"] if c1 else None, h2_supported=resc[r["run_id"]]["new"], c1_supported=resc[c1["run_id"]]["new"] if c1 else None))
print("repair events", len(repairs), "no-repair decisions", norep, "episodes with a repair", len(fired), "of", sum(1 for r in rows if r["arm"] == "C1+H2"))
print("repairs whose re-run result was not an error:", sum(x["result_ok"] for x in repairs), "of", len(repairs))
for x in repairs: print(" ", x)
print("\nepisodes with at least one repair, same-cell comparison with C1:")
for f in fired: print(" ", f)
