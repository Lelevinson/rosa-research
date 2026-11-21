import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import view
rows = {r["run_id"]: r for r in (json.loads(l) for l in (view.PILOT / "RESULTS_LOG.jsonl").read_text().splitlines())}
def brief(key):
    rid = [k for k in rows if key in k]
    assert len(rid) == 1, (key, rid); r = rows[rid[0]]; t = view.TASKS[r["task"]]
    print("=" * 90); print(r["run_id"], r["arm"], r["task"], "req", r["llm_requests"], "floor", t["floor"], "in_tok", r["input_tokens"])
    k = 0
    for n, line in enumerate((view.REPO / r["trace_path"]).read_text().splitlines(), 1):
        e = json.loads(line)
        if e["kind"] == "model_end":
            k += 1; m = e["message"]
            print(f"L{n} R{k}", [(c["name"], json.dumps(c["args"])[:90]) for c in m.get("tool_calls", [])], ("TEXT:" + m["content"].strip()[:70].replace("\n", " ")) if m["content"].strip() and not m.get("tool_calls") else "")
        elif e["kind"] == "tool_end": print(f"   L{n} ->", str(e["output"])[:90].replace("\n", " "))
        elif e["kind"] == "handler" and e["event"] not in ("tools_offered",): print(f"   L{n} H:", e["event"], str(e.get("error") or e.get("args") or "")[:80])
for k in sys.argv[1:]: brief(k)
