"""Offline, CPU only. List every failed call of the S3 episodes (p3 + e1h tasks) of the live rendering run, both arms, with trace path.
Uses the frozen analyze_live helpers; no model, no ROS. Output: failed_calls.jsonl."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import analyze_live as A
C = A.C
tasks = A.tasks_all()
rows = [json.loads(l) for l in (HERE.parent / "RESULTS_LOG_LIVE.jsonl").read_text().splitlines()]
rows = [r for r in rows if r.get("phase") == "full" and A.stratum(r["task"]) == "S3"]
out = []
for row in rows:
    read = C.v2.s1.read_events
    C.v2.s1.read_events = lambda path, read=read: A.events_with_raw_results(read(path))
    try:
        ep = C.parse_episode("live", row, tasks)
    finally:
        C.v2.s1.read_events = read
    n = 0
    for r_index, r in enumerate(ep["requests"]):
        for c in r["calls"]:
            if c["tool"] == "final_answer":
                continue
            n += 1
            if not c["ok"]:
                out.append(dict(arm=row["arm"], model=row["model"], task=row["task"], seed=row["seed"], request=r_index, call_no=n, tool=c["tool"], args=c.get("args"),
                                entity=c.get("entity"), harness_error=c["harness_error"], text=(c["text"] if isinstance(c["text"], str) else json.dumps(c["text"]))[:300],
                                supported=bool(row["supported_complete"]), trace=row["trace_path"]))
(HERE / "failed_calls.jsonl").write_text("\n".join(json.dumps(o) for o in out) + "\n")
print(len(out))
