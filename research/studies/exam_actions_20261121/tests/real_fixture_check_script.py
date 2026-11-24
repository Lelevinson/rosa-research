"""Run by test_real_fixture_check.py in a SUBPROCESS with ROS_DOMAIN_ID=231 (never 219 or 220): real turtlesim + the runner's own backend node + a lingering `ros2 topic echo`.
Prints one JSON line: the fixture check with the echo still alive, after it ended, and with the simulator gone."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "action_tool_s2_20261118" / "tests"))
sys.path.insert(0, str(HERE.parent / "action_tool_s2_20261118"))
sys.path.insert(0, str(HERE.parent / "stage23_plan_20261123"))
assert os.environ["ROS_DOMAIN_ID"] == "231"
import graph_settle  # noqa: E402
import run_actions  # noqa: E402  (its constants EXPECTED_NODES / ALLOWED_EXTRA_NODES are what is under test)
from test_turtlesim_backend import start_turtlesim, stop  # noqa: E402
from turtlesim_backend import TurtlesimBackend  # noqa: E402


class Rec:
    def __init__(self):
        self.rows = []

    def add(self, kind, **fields):
        self.rows.append(dict(kind=kind, **fields))


def check():
    rec = Rec()
    result = run_actions.fixture_check("after", rec)
    return dict(ok=result["ok"], missing=result["missing"], unexpected=result["unexpected"], ignored=len(result["ignored"]), settled=(result["settle"] or {}).get("settled"),
                misses=(result["settle"] or {}).get("discovery_misses"))


simulator = start_turtlesim()
backend, echo, out = None, None, {}
try:
    import rclpy
    time.sleep(3)
    backend = TurtlesimBackend("exam_actions_backend")
    time.sleep(2)
    out["clean"] = check()
    echo = subprocess.Popen(["ros2", "topic", "echo", "--no-daemon", "--spin-time", "3", "/turtle1/pose"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(6)
    live = graph_settle.visible_nodes(graph_settle.real_run_command)
    out["echo_visible_before_check"] = any(graph_settle.is_transient_cli_node(n) for n in live)
    os.killpg(echo.pid, signal.SIGINT)      # the "tool call" ends; its helper node is still shutting down while the check starts
    out["right_after_echo_ends"] = check()
    backend.close()
    backend = None
    stop(simulator)
    simulator = None
    time.sleep(2)
    out["simulator_gone"] = check()
finally:
    for proc in (echo,):
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
    if backend is not None:
        backend.close()
    if simulator is not None:
        stop(simulator)
print("RESULT " + json.dumps(out))
