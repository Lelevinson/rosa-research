"""Print the Stage 1 queue's STATUS COUNTS only (state, done/total/skipped, per-tier counts, tier:system:model of the current cell, contended count, heartbeat age). Reads status_<machine>.json of the
custodian queue folder and prints a fixed whitelist of fields: no trace, no row, no task id, no log. Not part of the frozen file list (read-only helper).
  python3 status_stage1.py [RUN] [MACHINE]"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import monitor_stage1  # noqa: E402

run = sys.argv[1] if len(sys.argv) > 1 else "stage1_laptop_20261122"
machine = sys.argv[2] if len(sys.argv) > 2 else "laptop"
path = monitor_stage1.custody_queue_dir() / run / f"status_{machine}.json"
if not path.exists():
    print("no status file yet")
    sys.exit(0)
status = json.loads(path.read_text())
keep = ("state", "done", "total", "skipped", "tiers", "active_tier", "current_cell", "block", "contended_episodes", "quarantined_groups", "ollama_ok", "disk_free_gb", "gpu_used_mib", "gpu_total_mib")
out = {k: status.get(k) for k in keep if k in status}
out["heartbeat_age_s"] = round(time.time() - status["heartbeat_at"], 1) if "heartbeat_at" in status else None
out["started_at"] = time.strftime("%F %T", time.localtime(status["started_at"])) if status.get("started_at") else None
print(json.dumps(out))
