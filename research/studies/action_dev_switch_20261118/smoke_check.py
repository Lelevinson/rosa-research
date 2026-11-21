"""Clean criteria of PROTOCOL.md section 5 for the smoke (phase 'smoke' rows of RESULTS_LOG.jsonl). Prints PASS/FAIL per check and the judge reasons for hand checking."""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
rows = [r for r in rows if r["phase"] == "smoke"][-6:]
checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


check("6 smoke rows", len(rows) == 6, str(len(rows)))
check("every episode has an ending, ran the judge, none over 300 s, no infrastructure", all(r["ending"] and "success" in r and r["seconds"] <= 300 and not r["infrastructure"] for r in rows))
for task in ("S3", "R1", "R2"):
    pair = [r for r in rows if r["task"] == task]
    check(f"{task}: prompt and tool hashes identical across arms", len({r["prompt_hash"] for r in pair}) == 1 and len({r["tools_hash"] for r in pair}) == 1)
state_ok = True
for r in rows:
    events = [json.loads(l) for l in (ROOT / r["trace_path"]).read_text().splitlines()]
    tool_msgs = [e for e in events if e["kind"] == "tool" and e["name"] == "rotate_to_heading"]
    for e in tool_msgs:
        has = "State after action:" in e["content"]
        sent_goal = not (e["content"].startswith(("REJECTED", "NOT_READY", "LOCKED")))
        if (r["arm"] == "OFF" and has) or (r["arm"] == "ON" and has != sent_goal):
            state_ok = False
    others = [e for e in events if e["kind"] == "tool" and e["name"] != "rotate_to_heading" and "State after action:" in e["content"]]
    if others:
        state_ok = False
check("the 'State after action:' line only in ON and only after a goal-sending call", state_ok)
check("executor not PENDING/ACTIVE/UNKNOWN_LOCKED and turtle still at the end", all(r["executor_final_state"] in ("IDLE", "TERMINAL") and r["turtle_still"] for r in rows), str([r["executor_final_state"] for r in rows]))
r1_params = []
for r in rows:
    if r["task"] == "R1":
        events = [json.loads(l) for l in (ROOT / r["trace_path"]).read_text().splitlines()]
        r1_params += [e["content"] for e in events if e["kind"] == "tool" and e["name"] == "get_parameter"]
check("get_parameter returned the real background_r in at least one R1 episode", any("69" in c for c in r1_params), str(r1_params[:3]))
left = subprocess.run(["pgrep", "-x", "turtlesim_node"], capture_output=True, text=True).stdout.split()
check("no turtlesim_node left", not left)
with urllib.request.urlopen(os.environ.get("ROSA_OLLAMA_URL", "http://172.30.80.1:11434") + "/api/ps", timeout=30) as response:
    loaded = [m["name"] for m in json.loads(response.read())["models"]]
check("Ollama has no model loaded afterwards", not loaded, str(loaded))
print("\nFor the hand check of the judge:")
for r in rows:
    print(r["task"], r["arm"], "| answer", r["answer"], "| true", r["true_heading"], r["true_x"], r["true_y"], "| success", r["success"], r["judge_reasons"], "| rotate", r["rotate_results"], "| calls", r["tool_calls"], "| verification", r["verification_calls"], "| ending", r["ending"])
print("\nCLEAN" if all(checks) else "\nNOT CLEAN")
sys.exit(0 if all(checks) else 1)
