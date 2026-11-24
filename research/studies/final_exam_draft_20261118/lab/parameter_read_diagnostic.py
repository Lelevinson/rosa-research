"""Exercise the frozen parameter read path with one public node and one stream."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from threading import Thread
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock

from rosa.tools import ros2

STUDIES = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STUDIES / "headroom_diagnostic_20261112/vendor"))
from menu_run_study import Recorder, guarded_native  # noqa: E402


def run(output, require_clock):
    recorder = Recorder(output / "native.jsonl")
    ros2.execute_ros_command = guarded_native(recorder)
    rclpy.init()
    node = Node("rosa_lab_parameter_diagnostic")
    node.declare_parameter("diagnostic_value", 42)
    clock = [None]

    def note_clock(message):
        clock[0] = message.clock.sec * 1_000_000_000 + message.clock.nanosec

    node.create_subscription(Clock, "/clock", note_clock, qos_profile_sensor_data)
    thread = Thread(target=rclpy.spin, args=(node,), daemon=True)
    thread.start()
    name = "/" + node.get_name()
    counts = Counter()
    try:
        for _ in range(3):
            discovered, _ = ros2.execute_ros_command(f"ros2 node info {name}")
            if discovered and (not require_clock or clock[0] is not None):
                break
            time.sleep(1)
        else:
            raise RuntimeError("Public node or required simulator clock was not ready")
        start_clock = clock[0]
        if not require_clock and start_clock is not None:
            raise RuntimeError("A simulator clock was active in the control condition")
        checks = (
            (
                "list",
                lambda: ros2.ros2_param_list.func(name),
                lambda result: "diagnostic_value" in {item.strip() for item in result.get(name, [])},
            ),
            (
                "get",
                lambda: ros2.ros2_param_get.func(name, "diagnostic_value"),
                lambda result: result.get("diagnostic_value", "").strip() == "Integer value is: 42",
            ),
        )
        with (output / "attempts.jsonl").open("x", buffering=1) as log:
            for pair in range(1, 201):
                for tool, read, valid in checks:
                    before = len(recorder.rows)
                    try:
                        reply_valid = valid(read())
                    except Exception:
                        reply_valid = False
                    events = recorder.rows[before:]
                    start = [event for event in events if event["kind"] == "ros_start"]
                    end = [event for event in events if event["kind"] in {"ros_end", "ros_error"}]
                    if len(start) != 1 or len(end) != 1:
                        raise RuntimeError(f"Pair {pair} {tool} did not record one native attempt")
                    terminal = end[0]
                    timeout = terminal.get("error") == "15-second native command timeout"
                    label = "timeout" if timeout else "valid" if reply_valid else "other_failure"
                    counts[tool, label] += 1
                    log.write(json.dumps({"pair": pair, "tool": tool, "outcome": label}) + "\n")
        end_clock = clock[0]
        if require_clock and (end_clock is None or end_clock <= start_clock):
            raise RuntimeError("Simulator clock did not advance during the read series")
        if not require_clock and end_clock is not None:
            raise RuntimeError("Simulator clock appeared in the control condition")
        summary = {
            tool: {label: counts[tool, label] for label in ("valid", "timeout", "other_failure")}
            for tool, _, _ in checks
        }
        summary["simulator_clock"] = [start_clock, end_clock]
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary), flush=True)
    finally:
        rclpy.try_shutdown()
        thread.join(timeout=5)
        node.destroy_node()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--require-clock", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    run(args.output, args.require_clock)
