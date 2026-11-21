"""Monitor and exit hook of the Stage 1 laptop run. The custodian launcher keeps the queue's run folders in custody (queue_bridge.py sets queue_core.ARTIFACTS to <custodian bundle>/queue); the ordinary
monitor looks in research/_artifacts/exam and would see nothing. This wrapper points the unchanged monitor.py and notify_exit.py at the same folder. It reads the queue's STATUS FILE only (counts,
state, tier:system:model, heartbeat), never a trace, a row or a task id, and it never commits compact results (the commit interval is set far beyond the run).

  python3 monitor_stage1.py --run-name RUN --machine laptop            the monitor (status-only ntfy messages from fixed templates)
  python3 monitor_stage1.py exit RUN MACHINE EXIT_CODE                  the runner's exit hook (marks a crashed run so the monitor reports it)
"""
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "custodian_stage1_20261121"))


def custody_queue_dir():
    """<custodian bundle>/queue, resolved by the custodian module (a path computation; nothing in the folder is listed or read here)."""
    import bridge
    return bridge.protected(bridge.pool_path().parent / "queue")


def main():
    import queue_core
    queue_core.ARTIFACTS = custody_queue_dir()
    if len(sys.argv) > 1 and sys.argv[1] == "exit":
        sys.argv = ["notify_exit.py"] + sys.argv[2:]
        runpy.run_path(str(HERE / "notify_exit.py"), run_name="__main__")
        return
    if "--commit-every-hours" not in sys.argv:
        sys.argv += ["--commit-every-hours", "1000000"]
    import monitor
    monitor.main()


if __name__ == "__main__":
    main()
