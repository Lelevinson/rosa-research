"""Guarded action tool, stage S2: the REAL backend for turtlesim (ROS 2 Jazzy). Implements the `ActionBackend` contract of ../action_tool_s1_20261118/action_interface.py.

It knows how to talk to ONE action server (`/turtle1/rotate_absolute`, goal field `theta`) and how to read the turtle's own pose topic. It contains no
decision logic: checks, budget, sending once, cancelling and locking all stay in the S1 executor (action_executor.py), unchanged.

A rclpy node is spun in a background thread so that `poll()` and `readiness()` can be called from the (blocking) executor.
Turtlesim is a workbench only (spec section 3); nothing here is registered in ROSA or in any harness.
"""
import math
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "action_tool_s1_20261118"))

import rclpy  # noqa: E402
from action_msgs.msg import GoalStatus as RosGoalStatus  # noqa: E402
from rclpy.action import ActionClient  # noqa: E402
from rclpy.executors import SingleThreadedExecutor  # noqa: E402
from turtlesim.action import RotateAbsolute  # noqa: E402
from turtlesim.msg import Pose  # noqa: E402

from action_interface import (Ack, ActionSpec, DeploymentPolicy, FieldRange, GoalStatus)  # noqa: E402

POSE_TOPIC = "/turtle1/pose"
ACTION_NAME = "/turtle1/rotate_absolute"
POSE_MAX_AGE_SECONDS = 2.0           # readiness: the pose topic must have published this recently (the simulator is alive and its clock moves)

# The turtlesim deployment policy: one typed action. The numbers are workbench placeholders, not a robot's limits.
TURTLESIM_POLICY = DeploymentPolicy(
    actions={"rotate_to_heading": ActionSpec(
        tool_name="rotate_to_heading", ros_action_name=ACTION_NAME,
        description="Rotate the turtle in place to an absolute heading. Returns SUCCEEDED, ABORTED, CANCELED, TIMEOUT, REJECTED or NOT_READY.",
        fields=(FieldRange("theta", -math.pi, math.pi, "radians"),))},
    goal_budget=3, acknowledgement_seconds=2.0, execution_seconds=15.0, cancel_settlement_seconds=3.0, poll_seconds=0.1)


class TurtlesimBackend:
    def __init__(self, node_name: str = "action_tool_s2_backend"):
        if not rclpy.ok():
            rclpy.init()
        self.node = rclpy.create_node(node_name)
        self.client = ActionClient(self.node, RotateAbsolute, ACTION_NAME)
        self._pose: Optional[Pose] = None
        self._pose_time = 0.0
        self.node.create_subscription(Pose, POSE_TOPIC, self._on_pose, 10)
        self._send_futures: Dict[str, object] = {}     # goal_id -> future of send_goal_async (kept so a late acknowledgement can be reconciled)
        self._handles: Dict[str, object] = {}          # goal_id -> ClientGoalHandle once accepted
        self._result_futures: Dict[str, object] = {}
        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self.node)
        self._thread = threading.Thread(target=self._executor.spin, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._executor.shutdown()
        self.node.destroy_node()

    def _on_pose(self, message: Pose) -> None:
        self._pose, self._pose_time = message, time.monotonic()

    # ---------------------------------------------------------------- ActionBackend contract
    def readiness(self) -> Optional[str]:
        if not self.client.wait_for_server(timeout_sec=1.0):
            return f"action server {ACTION_NAME} not available"
        deadline = time.monotonic() + 1.0
        while self._pose is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if self._pose is None or time.monotonic() - self._pose_time > POSE_MAX_AGE_SECONDS:
            return f"no recent pose on {POSE_TOPIC}"
        return None

    def send_goal(self, action_name: str, fields: Dict[str, float], goal_id: str, ack_deadline_seconds: float) -> Ack:
        if action_name != ACTION_NAME:
            raise ValueError(f"this backend only serves {ACTION_NAME}")
        goal = RotateAbsolute.Goal()
        goal.theta = float(fields["theta"])
        future = self.client.send_goal_async(goal)
        self._send_futures[goal_id] = future
        deadline = time.monotonic() + ack_deadline_seconds
        while not future.done() and time.monotonic() < deadline:
            time.sleep(0.02)
        if not future.done():
            return Ack.NO_ANSWER        # the goal may exist; poll() reconciles it if the answer arrives later
        handle = future.result()
        if not handle.accepted:
            return Ack.REFUSED
        self._adopt(goal_id, handle)
        return Ack.ACCEPTED

    def poll(self, goal_id: str) -> Tuple[GoalStatus, Optional[int]]:
        if goal_id not in self._handles:
            future = self._send_futures.get(goal_id)
            if future is None or not future.done():
                return GoalStatus.UNKNOWN, None
            handle = future.result()
            if not handle.accepted:
                return GoalStatus.UNKNOWN, None     # refused after the deadline: nothing is running
            self._adopt(goal_id, handle)
        result_future = self._result_futures[goal_id]
        if not result_future.done():
            return GoalStatus.ACTIVE, None
        status = result_future.result().status
        mapping = {RosGoalStatus.STATUS_SUCCEEDED: GoalStatus.SUCCEEDED, RosGoalStatus.STATUS_ABORTED: GoalStatus.ABORTED, RosGoalStatus.STATUS_CANCELED: GoalStatus.CANCELED}
        return mapping.get(status, GoalStatus.UNKNOWN), None     # turtlesim reports no error code

    def cancel(self, goal_id: str) -> None:
        handle = self._handles.get(goal_id)
        if handle is not None:
            handle.cancel_goal_async()          # a request only; poll() decides whether the goal really ended

    def observe_state(self) -> str:
        """One line from the turtle's own pose topic (what the robot reports, not the evaluator's ground truth)."""
        if self._pose is None or time.monotonic() - self._pose_time > POSE_MAX_AGE_SECONDS:
            return "pose unavailable"
        p = self._pose
        return f"heading {p.theta:.3f} rad, position ({p.x:.2f}, {p.y:.2f})"

    def _adopt(self, goal_id: str, handle) -> None:
        self._handles[goal_id] = handle
        self._result_futures[goal_id] = handle.get_result_async()
