"""Negative control: the same crash at the write boundary against the FROZEN queue_core.py (no fix). Shows that the audit of test_rev2_crash.py can fail.
  uv run --no-sync python research/studies/final_exam_draft_20261118/exam_queue/tests_rev2/negative_control.py"""
import json, os, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
for fault, label in (("full_after", "kill between the full row and the compact row"), ("compact_raise", "compact write fails in a live runner")):
    root = Path(tempfile.mkdtemp())
    env = {**os.environ, "ROSA_REV2_ARTIFACTS": str(root), "ROSA_EXAM_CONFIG_DIR": str(root / "cfg"), "ROSA_EXAM_NOTIFY_DRY": str(root / "dry.log"), "ROS_DOMAIN_ID": "77", "ROSA_QUEUE_MODULE": "queue_core",
           "ROSA_FAULT": fault, "ROSA_FAULT_N": "3", "ROSA_FAULT_DIR": str(root / "f"), "DUMMY_FAULT_DIR": str(root / "f"), "DUMMY_DELAY_SECONDS": "0.2"}
    for _ in range(3):
        p = subprocess.run([sys.executable, str(HERE / "run_rev2.py"), "run", "--spec", str(HERE / "rev2_spec.json"), "--run-name", "neg", "--machine", "all", "--machines", "all:1", "--dummy"], env=env, capture_output=True, text=True, timeout=200)
        if p.returncode == 0:
            break
    rows = lambda f: [json.loads(l) for l in f.read_text().splitlines() if l.strip()] if f.exists() else []
    full, compact = rows(root / "artifacts/neg/RESULTS_LOG_all.jsonl"), rows(root / "compact/neg/compact_all.jsonl")
    print(f"{label}: full rows {len(full)} (unique cells {len({r['cell_id'] for r in full})}), compact rows {len(compact)}, planned 12")
