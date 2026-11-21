"""Staleness check for the proposed oracle fix (no model, CPU/ROS only): after a fixture node dies, how long does the DAEMON still list it?

  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python discovery_staleness.py OUTDIR TRIALS

Starts the stage 3 fixture (19 nodes), restarts the daemon, then per trial: kill one node (alternating SIGKILL = crash and SIGINT = clean shutdown), poll
`ros2 node list` (daemon) every 0.5 s until the node is gone (max 180 s), also run one `ros2 param get` on the dead node while it is still listed (what the
oracle's next read would see), then restart the node and wait until the daemon lists it again. Output: OUTDIR/staleness.jsonl.
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import discovery_repro as R  # noqa: E402

F = R.F


def daemon_list():
    p = subprocess.run(["ros2", "node", "list"], capture_output=True, text=True, timeout=40)
    return set(p.stdout.split()) if p.returncode == 0 else None


def main(out, trials):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    assert os.environ.get("ROS_DOMAIN_ID") == "220" and os.environ.get("ROS_LOCALHOST_ONLY") == "1"
    rec = R.Recorder(out / "setup.jsonl")
    log = R.Recorder(out / "staleness.jsonl")
    commands = F.commands()
    nodes = F.GRAPH["nodes"]
    F.common.assert_domain_empty((F.NS,), rec)
    processes, handles = F.common.start_processes(commands, out, "fx", rec)
    try:
        time.sleep(6)
        expected = sorted(n["fqn"] for n in nodes)
        rec.add("ready", ok=F.common.wait_for(expected, rec, attempts=10))
        subprocess.run(["ros2", "daemon", "stop"], capture_output=True, timeout=60)
        subprocess.run(["ros2", "daemon", "start"], capture_output=True, timeout=60)
        time.sleep(8)
        for trial in range(trials):
            index = (trial * 5 + 3) % len(nodes)
            node = nodes[index]
            how = "SIGKILL" if trial % 2 == 0 else "SIGINT"
            assert node["fqn"] in (daemon_list() or set()), "node not listed before the kill"
            began = time.time()
            processes[index].send_signal(signal.SIGKILL if how == "SIGKILL" else signal.SIGINT)
            processes[index].wait(timeout=30)
            exited = time.time() - began
            param_name = next(iter(node["params"]), None)
            param_result = None
            gone_after, polls, listed_polls = None, 0, 0
            while time.time() - began < 180:
                listed = daemon_list()
                polls += 1
                if listed is not None and node["fqn"] in listed:
                    listed_polls += 1
                    if param_name and param_result is None:  # what the oracle's next read of this node would see while the node is stale
                        p = subprocess.run(["ros2", "param", "get", node["fqn"], param_name], capture_output=True, text=True, timeout=40)
                        param_result = dict(returncode=p.returncode, stdout=p.stdout[-80:], stderr=p.stderr[-120:])
                if listed is not None and node["fqn"] not in listed:
                    gone_after = time.time() - began
                    break
                time.sleep(0.5)
            nodaemon = subprocess.run(["ros2", "node", "list", "--no-daemon", "--spin-time", "4"], capture_output=True, text=True, timeout=60)
            log.add("trial", trial=trial, node=node["fqn"], signal=how, seconds_until_process_exited=round(exited, 2),
                    seconds_until_daemon_stopped_listing=None if gone_after is None else round(gone_after, 2), daemon_polls=polls, polls_still_listing=listed_polls,
                    param_get_while_stale=param_result, nodaemon_lists_it=node["fqn"] in set(nodaemon.stdout.split()))
            # restart the node (same command) and wait until the daemon lists it again
            processes[index] = subprocess.Popen(commands[index], stdout=handles[index], stderr=subprocess.STDOUT, start_new_session=True,
                                                 env=dict(os.environ, QT_QPA_PLATFORM="offscreen"))
            back = time.time()
            while time.time() - back < 90 and node["fqn"] not in (daemon_list() or set()):
                time.sleep(0.5)
            log.add("restarted", trial=trial, node=node["fqn"], seconds_until_listed=round(time.time() - back, 2))
            time.sleep(5)
    finally:
        F.common.stop_processes(processes, handles, rec)
        rec.add("cleanup_ok", ok=F.common.verify_empty((F.NS,), rec))
        F.common.stop_daemon(rec)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
