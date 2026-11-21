"""Copy the thinking study's part-A (or part-B) rows from the queue's full results log into the study's own RESULTS_LOG.jsonl (phase partA / partB), the file that analyze_think.py reads.
  python export_to_thinking_log.py --run-name thinking_partA --phase partA
Rows are the unchanged output of run_think.episode_row plus the queue's fields; only `phase` is set. Dedupes by run_id, so it can be run repeatedly (also while the run is in progress)."""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import queue_core as Q  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--run-name", required=True)
parser.add_argument("--phase", required=True, choices=["partA", "partB", "replA2"])
args = parser.parse_args()
target = Q.STUDIES / "thinking_escalation_20261119/RESULTS_LOG.jsonl"
have = {json.loads(l)["run_id"] for l in target.read_text().splitlines() if l.strip()} if target.exists() else set()
added = 0
with target.open("a") as out:
    for path in sorted((Q.ARTIFACTS / args.run_name).glob("RESULTS_LOG_*.jsonl")):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            run_id = f"{args.run_name}/{row['run_id']}"
            if run_id in have:
                continue
            row["phase"], row["run_id"] = args.phase, run_id  # run ids carry the run folder, as in the other studies
            out.write(json.dumps(row, default=str) + "\n")
            added += 1
print(f"added {added} rows to {target.name}")
