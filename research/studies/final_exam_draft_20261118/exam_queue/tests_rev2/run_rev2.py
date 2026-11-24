"""Driver of the rev-2 crash tests: runs queue_core_rev2 in dummy mode with the test dummy system, a fake idle GPU and append-boundary faults.
  python run_rev2.py run --spec SPEC --run-name NAME --machine all --machines all:1 --dummy      (same arguments as queue_core)
Environment: ROSA_REV2_ARTIFACTS (results root), ROSA_FAULT = full_before | full_torn | full_after | compact_before | compact_torn | compact_raise | compact_raise_always | compact_after,
ROSA_FAULT_N (fire at the Nth append to that kind of log, default 3), ROSA_FAULT_DIR (marker files so that a fault fires only once across restarts).
No GPU, no model call, no ROS: ROS_DOMAIN_ID must be a domain nobody uses (the tests set 77)."""
import json
import os
import signal
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUEUE = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(QUEUE))
import dummy_system_rev2  # noqa: E402
sys.modules["dummy_system"] = dummy_system_rev2   # queue_core does `import dummy_system` in dummy mode
import importlib  # noqa: E402
Q = importlib.import_module(os.environ.get("ROSA_QUEUE_MODULE", "queue_core_rev2"))  # the negative control runs the same faults against the frozen queue_core

root = Path(os.environ["ROSA_REV2_ARTIFACTS"])
Q.ARTIFACTS = root / "artifacts"
Q.COMPACT_ROOT = root / "compact"
Q.health.gpu_memory_mib = lambda: None
Q.gpu_state.snapshot = lambda *a, **k: dict(t=__import__("time").time(), used_mib=0, total_mib=8000, util_pct=0, apps=[], our_pids=[], ours_mib=0, others_mib=0, loaded=[], load1=0.1)
Q.gpu_state.read_window = lambda *a, **k: []

if os.environ.get("ROSA_FAULT_DAEMON_SURVIVES") == "1":
    real_kill = os.kill

    def kill_except_daemons(pid, sig):
        """Test fault: every signal sent to a ROS discovery daemon is swallowed, so a run-owned daemon survives TERM and KILL."""
        try:
            command = Path(f"/proc/{pid}/cmdline").read_bytes()
        except OSError:
            command = b""
        if b"ros2cli.daemon.daemonize" in command:
            return None
        return real_kill(pid, sig)

    os.kill = kill_except_daemons

if os.environ.get("ROSA_BRIDGE_LIKE_LOG") == "1":
    original_log = Q.log_episode

    def bridge_like_log(ctx, module, out, directory, attempt, cell, gpu=None):
        """What queue_bridge.py's log wrapper does for a failed worker: nonzero exit code -> ctx.note_cell_failure(cell) (no reason), no row."""
        if attempt.get("returncode") != 0:
            ctx.note_cell_failure(cell)
            return False
        return original_log(ctx, module, out, directory, attempt, cell, gpu)

    Q.log_episode = bridge_like_log

fault = os.environ.get("ROSA_FAULT")
if fault:
    kind = "full" if fault.startswith("full") else "compact"
    mode = fault.split("_", 1)[1]
    always = mode == "raise_always"   # every compact append from the Nth on fails (a full disk): the queue must not end as finished
    nth = int(os.environ.get("ROSA_FAULT_N", "3"))
    marker = Path(os.environ["ROSA_FAULT_DIR"]) / ("fired_" + fault)
    marker.parent.mkdir(parents=True, exist_ok=True)
    counter = {"n": 0}
    real = Q.Results.append_line

    def die():
        os.kill(os.getpid(), signal.SIGKILL)

    def append_line(path, record):
        name = Path(path).name
        mine = (name.startswith("RESULTS_LOG_") and kind == "full") or (name.startswith("compact_") and "contended" not in name and kind == "compact")
        if mine and always:
            counter["n"] += 1
            if counter["n"] >= nth:
                raise OSError(28, "No space left on device (injected, persistent)")
        elif mine and not marker.exists():
            counter["n"] += 1
            if counter["n"] == nth:
                marker.write_text("x")
                line = record if isinstance(record, str) else json.dumps(record, default=str)
                if mode == "before":
                    die()
                if mode == "torn":
                    with Path(path).open("a") as handle:     # half a line, no newline, then the process dies
                        handle.write(line[: len(line) // 2])
                        handle.flush()
                        os.fsync(handle.fileno())
                    die()
                if mode == "raise":
                    raise OSError(28, "No space left on device (injected)")
                real(path, record)
                if mode == "after":
                    die()
                return
        return real(path, record)

    Q.Results.append_line = staticmethod(append_line)

sys.argv = ["queue_core_rev2.py"] + sys.argv[1:]
sys.exit(Q.main())
