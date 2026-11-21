"""Extra offline check: the answer gate on every valid pilot episode of every arm (scorer v2.0 labels from research/studies/residual_failures_20261115/rescore_v2.json).
Only the final answer of each episode is replayed (first submission). No model, no ROS."""
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "residual_failures_20261115"))
import answer_gate, precheck_gate, scorer_v2 as v2
ROOT = precheck_gate.ROOT
log = {json.loads(l)["run_id"]: json.loads(l) for l in (ROOT / "research/studies/small_model_harness_20261115/RESULTS_LOG.jsonl").read_text().splitlines()}
score = json.loads((ROOT / "research/studies/residual_failures_20261115/rescore_v2.json").read_text())
from collections import Counter
count = Counter(); false = []
for s in score:
    r = log[s["run_id"]]
    events = v2.s1.read_events(ROOT / r["trace_path"])
    answer, _ = v2.episode_answer(events)
    if not isinstance(answer, dict):
        count[("no_answer", s["new"])] += 1; continue
    ep = precheck_gate.load_episode(r["trace_path"])
    verdict = answer_gate.check_answer(answer, ep["task_text"], ep["outputs"])
    count[(s["new"], verdict["reject"])] += 1
    if s["new"] and verdict["reject"]:
        false.append((s["run_id"], s["arm"], [p["hint"] for p in verdict["problems"]]))
print("(supported, would_reject) counts:", dict(count)); print("false rejections:", len(false))
for f in false: print(f)
