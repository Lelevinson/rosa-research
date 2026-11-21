"""Watchdog for the exam queue: reads the runner's status file and sends status-only notifications. Runs in its own tmux window; it does not touch the runner.
  python monitor.py --run-name NAME [--machine laptop] [--interval 30] [--once] [--force-daily] [--commit-every-hours 3]
Events (each de-duplicated with a cool-down, state in monitor_state_<machine>.json next to the status file):
  finished       runner state is finished / finished_with_skips
  crash          runner state is crashed/blocked, or the heartbeat is older than 3 heartbeats while the state says running (the process died)
  no_progress    no new episode row and no trace activity for 15 minutes while running
  ollama_down    Ollama unreachable for more than 2 minutes (checked here and reported by the runner)
  low_disk       free disk below the threshold (default 30 GB)
  daily          one summary per day at 08:00 local time
Also every `commit-every-hours` hours it commits the compact results (see commit_results.py)."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import health  # noqa: E402
import notify  # noqa: E402
import queue_core  # noqa: E402
import commit_results  # noqa: E402

THRESHOLDS = dict(no_progress_seconds=900, ollama_down_seconds=120, low_disk_gb=30, stale_heartbeat_seconds=None, cooldown_seconds=3600, daily_hour=8)


def evaluate(status, now, state, thr, ollama_ok_now):
    """Pure decision function: which events fire now. `state` is the monitor's memory (last sent times, when Ollama first looked down). Returns a list of (kind, values)."""
    base = dict(machine=status["machine"], done=status["done"], total=status["total"])
    events = []

    def once(kind, key=None, cooldown=None):
        key = key or kind
        last = state.get("last_sent", {}).get(key)
        if last is None or now - last >= (cooldown if cooldown is not None else thr["cooldown_seconds"]):
            state.setdefault("last_sent", {})[key] = now
            return True
        return False

    running = status["state"] in ("running", "waiting_for_ollama", "waiting_for_gpu", "starting")
    stale_after = thr["stale_heartbeat_seconds"] or 3 * 30
    if status["state"] in ("finished", "finished_with_skips"):
        if once("finished", cooldown=10 ** 9):
            events.append(("finished", dict(base, skipped=status.get("skipped", 0))))
    elif status["state"] in ("crashed", "blocked_ollama", "blocked_disk") or (running and now - status["heartbeat_at"] > stale_after):
        if once("crash", cooldown=thr["cooldown_seconds"]):
            events.append(("crash", base))
    elif status["state"] == "stopped":
        pass
    elif running and now - status["last_progress_at"] > thr["no_progress_seconds"]:
        if once("no_progress"):
            events.append(("no_progress", dict(base, minutes=int((now - status["last_progress_at"]) // 60))))
    if running or status["state"] in ("blocked_ollama",):
        if not ollama_ok_now:
            state.setdefault("ollama_down_since", now)
            if now - state["ollama_down_since"] > thr["ollama_down_seconds"] and once("ollama_down"):
                events.append(("ollama_down", dict(base, minutes=max(1, int((now - state["ollama_down_since"]) // 60)))))
        else:
            state.pop("ollama_down_since", None)
    if status.get("disk_free_gb") is not None and status["disk_free_gb"] < thr["low_disk_gb"] and once("low_disk"):
        events.append(("low_disk", dict(base, free_gb=status["disk_free_gb"])))
    return events


def daily_due(now, state, thr, force):
    local = time.localtime(now)
    key = time.strftime("%F", local)
    if force or (local.tm_hour >= thr["daily_hour"] and state.get("daily_sent_for") != key):
        state["daily_sent_for"] = key
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--machine", default=os.environ.get("ROSA_EXAM_MACHINE", "all"))
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--force-daily", action="store_true")
    parser.add_argument("--commit-every-hours", type=float, default=3.0)
    parser.add_argument("--simulate-ollama-down", action="store_true", help="test: treat Ollama as unreachable")
    for key, value in THRESHOLDS.items():
        if value is not None:
            parser.add_argument("--" + key.replace("_", "-"), type=type(value), default=value)
    parser.add_argument("--stale-heartbeat-seconds", type=int, default=None)
    args = parser.parse_args()
    thr = {k: getattr(args, k) for k in THRESHOLDS}
    run_dir = queue_core.ARTIFACTS / args.run_name
    status_path, state_path = run_dir / f"status_{args.machine}.json", run_dir / f"monitor_state_{args.machine}.json"
    run_dir.mkdir(parents=True, exist_ok=True)  # the monitor may start before the runner has created the run folder (a race that silenced the monitor during thinking part A)
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    state.setdefault("last_commit", time.time())
    while True:
        try:
            iterate(args, thr, status_path, state_path, state)
        except Exception as error:  # noqa: BLE001  a monitor that dies silently is worse than one that logs and keeps going
            notify.log(f"monitor loop error: {type(error).__name__}: {error}")
        if args.once:
            return
        time.sleep(args.interval)


def iterate(args, thr, status_path, state_path, state):
    if True:
        now = time.time()
        if status_path.exists():
            status = json.loads(status_path.read_text())
            ollama_now = False if args.simulate_ollama_down else health.ollama_ok()
            for kind, values in evaluate(status, now, state, thr, ollama_now):
                notify.send(kind, **values)
            if daily_due(now, state, thr, args.force_daily):
                notify.send("daily", machine=status["machine"], done=status["done"], total=status["total"], tier=status.get("active_tier") or "none", skipped=status.get("skipped", 0), free_gb=status["disk_free_gb"])
        if now - state["last_commit"] >= args.commit_every_hours * 3600 or (args.once and args.commit_every_hours == 0):
            try:
                commit_results.commit(args.run_name, args.machine)
            except Exception as error:  # noqa: BLE001
                notify.log(f"commit failed: {type(error).__name__}: {error}")
            state["last_commit"] = now
        state_path.write_text(json.dumps(state))


if __name__ == "__main__":
    main()
