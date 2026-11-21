"""Compact trace viewer for round 1 episodes: prints requests, calls, results and add-on events with trace line numbers.  uv run python view_episode.py RUN_ID [width]"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[2]
rid = sys.argv[1]; width = int(sys.argv[2]) if len(sys.argv) > 2 else 230
row = next(json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines() if json.loads(l)["run_id"] == rid and json.loads(l)["phase"] == "full")
print(rid, "supported", row["supported_complete"], "requests", row["llm_requests"], "answer", json.dumps(row["answer"])[:200], "missing", row["support_missing"], row["issues"][:2])
k = 0
for n, line in enumerate((REPO / row["trace_path"]).read_text().splitlines(), 1):
    e = json.loads(line)
    if e["kind"] == "model_end":
        k += 1; m = e["message"]
        print(f"[L{n}] REQ{k} calls={[(c['name'], json.dumps(c['args'])) for c in m.get('tool_calls', [])]}"[:width + 60], ("| text: " + m['content'].strip()[:120]) if m["content"].strip() else "")
    elif e["kind"] == "tool_end":
        print(f"[L{n}]   OBS {str(e['output'])[:width]!r}")
    elif e["kind"] == "handler" and e["event"] in ("gate_reject", "gate_followup", "bare_text_nudge", "gate_accepted_after_limit", "list_call", "list_rejected"):
        print(f"[L{n}]   ** {e['event']} " + json.dumps({a: b for a, b in e.items() if a in ('hint', 'changed', 'number', 'items', 'given', 'tool', 'answer', 'now')})[:width])
    elif e["kind"] == "final_answer_accepted":
        print(f"[L{n}]   FINAL {json.dumps(e['answer'])[:width]}")
