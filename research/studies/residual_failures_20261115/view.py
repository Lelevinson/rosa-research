"""Read-only trace viewer: prints one episode as requests/calls/results with trace line numbers (no model, no ROS)."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "small_model_harness_20261115"
REPO = HERE.parents[2]
TASKS = {t["id"]: t for t in json.loads((HERE.parent / "headroom_diagnostic_20261112/stage3_tasks.json").read_text())}
TASKS.update({t["id"]: t for t in json.loads((PILOT / "e1h_tasks.json").read_text())})
EXC = set()
for g in json.loads((PILOT / "INFRA_EXCLUDED.json").read_text()).values():
    EXC |= set(g["run_ids"])

def failed():
    rows = [json.loads(l) for l in (PILOT / "RESULTS_LOG.jsonl").read_text().splitlines()]
    return [r for r in rows if r["arm"] == "C1" and r["run_id"] not in EXC and not r["supported_complete"]]

def show(r, width=260):
    t = TASKS[r["task"]]
    print("=" * 100); print(r["run_id"], "| model", r["model"], "| task", r["task"], "seed", r["seed"], "| requests", r["llm_requests"], "floor", t["floor"], "| aborts", r["aborts"])
    print("TASK:", t["request"]); print("TRUTH:", json.dumps(t["answer"])); print("ANSWER OBJ:", json.dumps(r["answer"]))
    lines = (REPO / r["trace_path"]).read_text().splitlines(); k = 0
    for n, line in enumerate(lines, 1):
        e = json.loads(line)
        if e["kind"] == "model_end":
            k += 1; m = e["message"]
            calls = [(c["name"], json.dumps(c["args"])) for c in m.get("tool_calls", [])]
            print(f"[L{n}] REQ{k} calls={calls}"[:width + 80]); 
            if m["content"].strip(): print(f"       text: {m['content'].strip()[:width]!r}")
        elif e["kind"] == "tool_end":
            print(f"[L{n}]   OBS {str(e['output'])[:width]!r}")
        elif e["kind"] in ("final_answer_accepted", "scripted_change", "handler") and not (e["kind"] == "handler" and e["event"] == "tools_offered"):
            print(f"[L{n}]   {e['kind']} {json.dumps({a: b for a, b in e.items() if a not in ('kind','monotonic','tool_run_id')})[:width]}")
        elif e["kind"] == "episode_end":
            print(f"[L{n}] END answer={str(e.get('answer'))[:width]!r} error={e.get('error')}")

if __name__ == "__main__":
    rs = failed()
    if len(sys.argv) == 1:
        for i, r in enumerate(rs): print(i, r["model"], r["task"], r["seed"], r["run_id"])
    else:
        show(rs[int(sys.argv[1])])
