"""Part B (measured part): requests above the floor and tokens in supported-complete episodes (scorer v2.0), plus rule-based flags per request.
No model, no ROS. Writes waste.json. Floors are the pilot's verified floors (analysis only; never used by any method)."""
import json, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "small_model_harness_20261115"))
import scorer_v2 as v2, view, harness
resc = {x["run_id"]: x for x in json.loads((HERE / "rescore_v2.json").read_text())}
rows = [json.loads(l) for l in (view.PILOT / "RESULTS_LOG.jsonl").read_text().splitlines()]
rows = [r for r in rows if r["run_id"] not in view.EXC and resc[r["run_id"]]["new"]]   # supported-complete under scorer v2.0

def request_flags(events, task):
    """Per request: repeat (every call repeats an earlier SUCCESSFUL call with identical args), failed (some call returned an error), offroute (some call uses a tool outside the
    task's verified minimal route), final (a final_answer call or the closing text request)."""
    route = harness.route_tools(task) | {"final_answer"}
    seen_ok, out, k, cur = set(), [], 0, None
    ends = [e for e in events if e["kind"] in ("model_end", "tool_start", "tool_end")]
    reqs = []
    for e in ends:
        if e["kind"] == "model_end":
            cur = dict(calls=[(c["name"], json.dumps(c["args"], sort_keys=True)) for c in e["message"].get("tool_calls", [])], results=[]); reqs.append(cur)
        elif e["kind"] == "tool_end" and cur is not None:
            cur["results"].append(str(e["output"]))
    for q in reqs:
        res_failed = [bool(v2.s1.ERROR.search(t)) for t in q["results"]]
        flags = dict(final=(not q["calls"]) or any(n == "final_answer" for n, _ in q["calls"]),
                     repeat=bool(q["calls"]) and all(c in seen_ok for c in q["calls"]),
                     failed=any(res_failed), offroute=any(n not in route for n, _ in q["calls"]))
        for c, f in zip(q["calls"], res_failed + [False] * len(q["calls"])):
            if not f: seen_ok.add(c)
        out.append(flags)
    return out

eps = []
for r in rows:
    task = view.TASKS[r["task"]]; ev = v2.s1.read_events(view.REPO / r["trace_path"])
    fl = request_flags(ev, task)
    eps.append(dict(run_id=r["run_id"], model=r["model"], arm=r["arm"], task=r["task"], seed=r["seed"], floor=task["floor"], requests=r["llm_requests"], excess=r["llm_requests"] - task["floor"],
                    input_tokens=r["input_tokens"], output_tokens=r["output_tokens"], wall=r["wall_seconds"],
                    n_repeat=sum(f["repeat"] for f in fl), n_failed=sum(f["failed"] and not f["repeat"] for f in fl), n_offroute=sum(f["offroute"] and not f["repeat"] and not f["failed"] for f in fl)))
(HERE / "waste.json").write_text(json.dumps(eps, indent=1))
print(len(eps), "supported-complete episodes (scorer v2.0)")
