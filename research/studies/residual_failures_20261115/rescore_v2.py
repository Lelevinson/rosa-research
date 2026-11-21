"""Rescore every valid pilot episode (all arms, all models) with scorer v2 and compare with the stored v1 flag. No model, no ROS. Writes rescore_v2.json."""
import json, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "small_model_harness_20261115"; REPO = HERE.parents[2]
sys.path.insert(0, str(HERE)); import scorer_v2 as v2
import view
rows = [json.loads(l) for l in (PILOT / "RESULTS_LOG.jsonl").read_text().splitlines()]
rows = [r for r in rows if r["run_id"] not in view.EXC]
out = []
for r in rows:
    task = view.TASKS[r["task"]]
    ev = v2.s1.read_events(REPO / r["trace_path"])
    new = v2.score_events(task, ev)
    out.append(dict(run_id=r["run_id"], model=r["model"], arm=r["arm"], task=r["task"], seed=r["seed"], old=r["supported_complete"], new=new["supported_complete"],
                    new_exact=new["exact"], new_missing=new["support_missing"], source=new["answer_source"]))
(HERE / "rescore_v2.json").write_text(json.dumps(out, indent=1))
ARMS = ["A1", "C1", "M0", "C1+FN", "C1+H2", "C1+H1e", "C1+H1n", "C1+H7"]
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
print("| model | arm | n | supported v1 (old) | supported v2 (new) |"); print("|---|---|---:|---:|---:|")
for m in MODELS:
    for a in ARMS:
        s = [x for x in out if x["model"] == m and x["arm"] == a]
        if s: print(f"| {m} | {a} | {len(s)} | {sum(x['old'] for x in s)} | {sum(x['new'] for x in s)} |")
flips = [x for x in out if x["old"] != x["new"]]
print("\nflips:", len(flips), "up:", sum(x["new"] and not x["old"] for x in flips), "down:", sum(x["old"] and not x["new"] for x in flips))
for x in flips: print(" ", x["run_id"], "old", x["old"], "new", x["new"])
print("totals old", sum(x["old"] for x in out), "new", sum(x["new"] for x in out), "of", len(out))
