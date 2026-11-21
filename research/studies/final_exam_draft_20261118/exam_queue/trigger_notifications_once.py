"""Trigger every notification kind exactly once through the REAL monitor code path (real sends, throwaway status files, machine name `notiftest`).
  python trigger_notifications_once.py
Used for the runbook's notification test. Each case writes a crafted status file and runs `monitor.py --once` against it."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import queue_core  # noqa: E402

RUN = "notif_test"
MACHINE = "notiftest"
run_dir = queue_core.ARTIFACTS / RUN
run_dir.mkdir(parents=True, exist_ok=True)
status_path, state_path = run_dir / f"status_{MACHINE}.json", run_dir / f"monitor_state_{MACHINE}.json"


def case(name, status_changes, extra_args=(), state=None):
    now = time.time()
    status = dict(machine=MACHINE, state="running", heartbeat_at=now, last_progress_at=now, done=3, total=8, skipped=0, disk_free_gb=500.0, active_tier="tier1")
    status.update(status_changes)
    status_path.write_text(json.dumps(status))
    # fresh state so that no cool-down suppresses the event under test; today's daily summary is marked as already sent unless the case is the daily one
    fresh = {"last_commit": now, "daily_sent_for": None if "--force-daily" in extra_args else time.strftime("%F")}
    state_path.write_text(json.dumps({**fresh, **(state or {})}))
    result = subprocess.run([sys.executable, str(HERE / "monitor.py"), "--run-name", RUN, "--machine", MACHINE, "--once", "--commit-every-hours", "999", *extra_args], capture_output=True, text=True, timeout=120)
    print(f"{name}: monitor exit {result.returncode} {result.stderr.strip()[:120]}")


now = time.time()
case("finished", dict(state="finished", skipped=0))
case("crash (heartbeat 10 minutes old)", dict(heartbeat_at=now - 600, last_progress_at=now - 600))
case("no_progress (16 minutes)", dict(last_progress_at=now - 16 * 60))
case("ollama_down (down since 5 minutes, simulated)", {}, ["--simulate-ollama-down"], state={"last_commit": now, "ollama_down_since": now - 300})
case("low_disk (5 GB)", dict(disk_free_gb=5.0))
case("daily (forced)", {}, ["--force-daily"])
# study_failing is sent by the runner itself; send it through the same function the runner uses
import notify  # noqa: E402
print("study_failing:", notify.send("study_failing", machine=MACHINE, tries=3, done=3, total=8))
print("sent messages are listed in", notify.LOG_FILE)
