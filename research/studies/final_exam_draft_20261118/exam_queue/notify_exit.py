"""Called by the tmux wrapper when the runner process exits. If the exit code is not 0 and the status file still says running/starting, mark the status `crashed`
so the monitor (the single sender of notifications) reports it at once instead of waiting for a stale heartbeat.
  python notify_exit.py RUN_NAME MACHINE EXIT_CODE"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import queue_core  # noqa: E402

run_name, machine, code = sys.argv[1], sys.argv[2], int(sys.argv[3])
path = queue_core.ARTIFACTS / run_name / f"status_{machine}.json"
if code != 0 and not path.exists():
    # The runner stopped before it wrote any status (for example the zero-cell guard, a bad spec or a missing task file): without a status file the monitor would stay silent all night.
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    path.write_text(json.dumps(dict(machine=machine, state="crashed", exit_code=code, done=0, total=0, skipped=0, heartbeat_at=now, last_progress_at=now, disk_free_gb=None, active_tier=None)))
elif code != 0:
    status = json.loads(path.read_text())
    if status.get("state") in ("running", "starting", "waiting_for_ollama", "waiting_for_gpu"):
        status["state"], status["exit_code"] = "crashed", code
        path.write_text(json.dumps(status))
print(f"runner exited with code {code}")
