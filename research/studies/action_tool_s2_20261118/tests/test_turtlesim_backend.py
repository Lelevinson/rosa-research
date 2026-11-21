"""S2 tests against REAL turtlesim (ROS 2 Jazzy). Each test starts its own turtlesim_node (offscreen) on the domain given by the environment: one ROS job at a time.
From the repository root:
  source /opt/ros/jazzy/setup.bash; ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python -m unittest discover -s research/studies/action_tool_s2_20261118/tests -v
The ground truth is read by a SEPARATE subscription in the test (not by the backend), so a test checks the robot's real pose, not the backend's own report."""
import dataclasses
import math
import os
import signal
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent / "action_tool_s1_20261118"))

import rclpy  # noqa: E402
from turtlesim.msg import Pose  # noqa: E402

from action_executor import ActionExecutor  # noqa: E402
from action_interface import ExecutorOptions, ExecutorState, Result, render_for_model  # noqa: E402
from turtlesim_backend import TURTLESIM_POLICY, TurtlesimBackend  # noqa: E402


class WallClock:
    def now(self):
        return time.monotonic()

    def sleep(self, seconds):
        time.sleep(seconds)


def start_turtlesim():
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    return subprocess.Popen(["ros2", "run", "turtlesim", "turtlesim_node"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)


def stop(process):
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass
    process.wait(timeout=10)


def true_heading():
    """Independent ground-truth read: a fresh node and subscription."""
    node = rclpy.create_node("s2_test_truth")
    seen = []
    node.create_subscription(Pose, "/turtle1/pose", seen.append, 10)
    end = time.monotonic() + 3
    while not seen and time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_node()
    if not seen:
        raise AssertionError("no pose received")
    return seen[-1].theta


def angle_error(a, b):
    return abs(math.atan2(math.sin(a - b), math.cos(a - b)))


class TurtlesimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = TurtlesimBackend("s2_test_backend")

    @classmethod
    def tearDownClass(cls):
        cls.backend.close()

    def start_sim(self):
        self.sim = start_turtlesim()
        self.addCleanup(self.stop_sim)
        deadline = time.monotonic() + 15
        while self.backend.readiness() is not None and time.monotonic() < deadline:
            time.sleep(0.3)
        self.assertIsNone(self.backend.readiness(), "turtlesim did not become ready")

    def stop_sim(self):
        stop(self.sim)
        time.sleep(1.0)

    def make(self, **changes):
        policy = dataclasses.replace(TURTLESIM_POLICY, **changes) if changes else TURTLESIM_POLICY
        return ActionExecutor(policy, self.backend, WallClock(), ExecutorOptions(attach_post_action_state=False))

    def test_not_ready_when_simulator_is_absent(self):
        executor = self.make()
        outcome = executor.execute("rotate_to_heading", {"theta": 1.0})
        self.assertEqual(outcome.result, Result.NOT_READY)
        self.assertEqual(executor.goals_sent, 0)          # nothing sent, budget untouched

    def test_rotation_succeeds_and_the_real_pose_matches(self):
        self.start_sim()
        outcome = self.make().execute("rotate_to_heading", {"theta": 1.2})
        self.assertEqual(outcome.result, Result.SUCCEEDED, outcome)
        self.assertLess(angle_error(true_heading(), 1.2), 0.05)
        self.assertEqual(render_for_model(outcome), "SUCCEEDED")       # switch off: no state line

    def test_out_of_range_is_rejected_without_motion(self):
        self.start_sim()
        executor = self.make()
        before = true_heading()
        outcome = executor.execute("rotate_to_heading", {"theta": 9.0})
        self.assertEqual(outcome.result, Result.REJECTED)
        self.assertEqual(executor.goals_sent, 0)
        self.assertLess(angle_error(true_heading(), before), 1e-3)

    def test_timeout_cancel_is_confirmed_by_the_real_server(self):
        self.start_sim()
        executor = self.make(execution_seconds=0.3)      # shorter than a long turn takes
        outcome = executor.execute("rotate_to_heading", {"theta": 3.0})
        self.assertEqual(outcome.result, Result.TIMEOUT, outcome)
        self.assertTrue(outcome.motion_confirmed_stopped)
        self.assertEqual(executor.state, ExecutorState.TERMINAL)
        stopped_at = true_heading()
        time.sleep(1.0)
        self.assertLess(angle_error(true_heading(), stopped_at), 0.02)     # really stopped
        self.assertGreater(angle_error(stopped_at, 3.0), 0.05)             # and did not reach the goal

    def test_budget_is_enforced(self):
        self.start_sim()
        executor = self.make(goal_budget=1)
        self.assertEqual(executor.execute("rotate_to_heading", {"theta": 0.5}).result, Result.SUCCEEDED)
        second = executor.execute("rotate_to_heading", {"theta": -0.5})
        self.assertEqual(second.result, Result.REJECTED)
        self.assertIn("budget", second.detail)

    def test_post_action_state_switch_changes_only_the_text(self):
        self.start_sim()
        off = self.make()
        on = ActionExecutor(TURTLESIM_POLICY, self.backend, WallClock(), ExecutorOptions(attach_post_action_state=True))
        a = off.execute("rotate_to_heading", {"theta": 0.7})
        b = on.execute("rotate_to_heading", {"theta": -0.7})
        self.assertEqual((a.result, b.result), (Result.SUCCEEDED, Result.SUCCEEDED))
        self.assertNotIn("State after action", render_for_model(a))
        text = render_for_model(b)
        self.assertTrue(text.startswith("SUCCEEDED\nState after action: heading "), text)
        self.assertLess(abs(float(text.split("heading ")[1].split(" rad")[0]) - (-0.7)), 0.05)    # the line reports the real heading
        self.assertNotIn("State after action", render_for_model(on.execute("rotate_to_heading", {"theta": 99})))   # no goal sent: no line

    def test_simulator_killed_during_motion_ends_cleanly(self):
        self.start_sim()
        executor = self.make(execution_seconds=4.0, cancel_settlement_seconds=1.0)
        threading.Timer(0.3, lambda: stop(self.sim)).start()
        outcome = executor.execute("rotate_to_heading", {"theta": 3.0})
        # The server vanished: the goal can never finish. The executor must not hang, must say the state is unknown, and must lock.
        self.assertEqual(outcome.result, Result.TIMEOUT)
        self.assertFalse(outcome.motion_confirmed_stopped)
        self.assertEqual(executor.state, ExecutorState.UNKNOWN_LOCKED)
        self.assertEqual(executor.execute("rotate_to_heading", {"theta": 0.0}).result, Result.LOCKED)


if __name__ == "__main__":
    unittest.main()
