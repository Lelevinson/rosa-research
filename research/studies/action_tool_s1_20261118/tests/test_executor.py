"""Deterministic tests of the S1 executor core against the fake robot (no ROS, no model). From the repository root:
  uv run python -m unittest discover -s research/studies/action_tool_s1_20261118/tests -v
Covers the spec section 10 items that apply to the core. NOT covered (next stage): worker killed mid-motion with a separate supervisor, Nav2 preflight on real
lifecycle nodes, ground-truth reader, same tool exposed identically in four systems, central write authorization."""
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from action_executor import ActionExecutor  # noqa: E402
from action_interface import Ack, ActionSpec, DeploymentPolicy, ExecutorOptions, ExecutorState, FieldRange, GoalStatus, Result, render_for_model, tool_schema  # noqa: E402
from fake_backend import FakeBackend, FakeClock  # noqa: E402

# Test-only numbers (not a real robot's limits).
NAVIGATE = ActionSpec("navigate_to_pose", "navigate_to_pose", "Drive the robot to a pose on the map.",
                      (FieldRange("x", -5.0, 5.0, "meters"), FieldRange("y", -5.0, 5.0, "meters"), FieldRange("yaw", -math.pi, math.pi, "radians")))
POLICY = DeploymentPolicy(actions={"navigate_to_pose": NAVIGATE}, goal_budget=2, acknowledgement_seconds=2.0, execution_seconds=10.0, cancel_settlement_seconds=4.0)
GOOD = {"x": 1.0, "y": 2.0, "yaw": 0.5}


def build(options=None, make_goal_id=None):
    clock = FakeClock()
    backend = FakeBackend(clock)
    return ActionExecutor(POLICY, backend, clock, options, make_goal_id), backend, clock


class RejectionTests(unittest.TestCase):
    def test_bad_arguments_are_rejected_and_nothing_is_sent_or_counted(self):
        cases = {
            "out of range": {"x": 9.0, "y": 0.0, "yaw": 0.0},
            "nan": {"x": float("nan"), "y": 0.0, "yaw": 0.0},
            "infinite": {"x": 0.0, "y": float("inf"), "yaw": 0.0},
            "outside the yaw range": {"x": 0.0, "y": 0.0, "yaw": 7.0},
            "missing field": {"x": 0.0, "y": 0.0},
            "unknown field": {"x": 0.0, "y": 0.0, "yaw": 0.0, "speed": 1.0},
            "string number": {"x": "1.0", "y": 0.0, "yaw": 0.0},
            "boolean": {"x": True, "y": 0.0, "yaw": 0.0},
            "behavior tree": {"x": 0.0, "y": 0.0, "yaw": 0.0, "behavior_tree": "custom.xml"},
        }
        for name, arguments in cases.items():
            executor, backend, _ = build()
            outcome = executor.execute("navigate_to_pose", arguments)
            self.assertEqual(outcome.result, Result.REJECTED, name)
            self.assertEqual(backend.sent, [], name)
            self.assertEqual(executor.goals_sent, 0, name)
            self.assertTrue(render_for_model(outcome).startswith("REJECTED "), name)

    def test_empty_behavior_tree_is_accepted_and_unknown_tool_is_rejected(self):
        executor, backend, _ = build()
        self.assertEqual(executor.execute("navigate_to_pose", dict(GOOD, behavior_tree="")).result, Result.SUCCEEDED)
        self.assertEqual(build()[0].execute("ros2_service_call", {}).result, Result.REJECTED)

    def test_rejection_text_names_the_field(self):
        text = render_for_model(build()[0].execute("navigate_to_pose", {"x": 9.0, "y": 0.0, "yaw": 0.0}))
        self.assertIn("field x", text)


class ReadinessTests(unittest.TestCase):
    def test_not_ready_sends_nothing_and_keeps_the_budget(self):
        for reason in ("action server missing", "lifecycle node inactive", "stale transform", "sim clock stalled"):
            executor, backend, _ = build()
            backend.not_ready_reason = reason
            outcome = executor.execute("navigate_to_pose", GOOD)
            self.assertEqual((outcome.result, outcome.detail), (Result.NOT_READY, reason))
            self.assertEqual((backend.sent, executor.goals_sent), ([], 0), reason)
            backend.not_ready_reason = None   # becomes ready: the same call now works and the budget was not used up
            self.assertEqual(executor.execute("navigate_to_pose", GOOD).result, Result.SUCCEEDED)

    def test_a_readiness_check_that_raises_is_not_ready_not_a_crash(self):
        executor, backend, _ = build()
        backend.readiness = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        self.assertEqual(executor.execute("navigate_to_pose", GOOD).result, Result.NOT_READY)
        self.assertEqual(backend.sent, [])


class OutcomeTests(unittest.TestCase):
    def test_success_abort_and_server_refusal(self):
        executor, backend, _ = build()
        outcome = executor.execute("navigate_to_pose", GOOD)
        self.assertEqual((outcome.result, outcome.state_after, outcome.motion_confirmed_stopped), (Result.SUCCEEDED, ExecutorState.TERMINAL, True))
        self.assertEqual(render_for_model(outcome), "SUCCEEDED")
        self.assertEqual(backend.sent[0][0:2], ("navigate_to_pose", {"x": 1.0, "y": 2.0, "yaw": 0.5}))
        executor, backend, _ = build()
        backend.final_status, backend.error_code = GoalStatus.ABORTED, 104
        self.assertEqual(render_for_model(executor.execute("navigate_to_pose", GOOD)), "ABORTED (error code 104)")
        executor, backend, _ = build()
        backend.ack = Ack.REFUSED
        outcome = executor.execute("navigate_to_pose", GOOD)
        self.assertEqual(outcome.result, Result.REJECTED)
        self.assertEqual(executor.goals_sent, 1)   # a goal that was sent counts, even if refused

    def test_budget_is_enforced_per_episode_and_reset_by_begin_episode(self):
        executor, backend, _ = build()
        self.assertEqual(executor.execute("navigate_to_pose", GOOD).result, Result.SUCCEEDED)
        self.assertEqual(executor.execute("navigate_to_pose", GOOD).result, Result.SUCCEEDED)
        third = executor.execute("navigate_to_pose", GOOD)
        self.assertEqual(third.result, Result.REJECTED)
        self.assertIn("budget", third.detail)
        self.assertEqual(len(backend.sent), 2)
        self.assertEqual(executor.begin_episode(), (True, ""))
        self.assertEqual(executor.execute("navigate_to_pose", GOOD).result, Result.SUCCEEDED)


class TimeoutAndLockTests(unittest.TestCase):
    def test_timeout_with_a_working_cancel_stops_the_robot_and_does_not_lock(self):
        executor, backend, _ = build()
        backend.run_seconds = 1e9
        outcome = executor.execute("navigate_to_pose", GOOD)
        self.assertEqual((outcome.result, outcome.motion_confirmed_stopped, outcome.state_after), (Result.TIMEOUT, True, ExecutorState.TERMINAL))
        self.assertEqual(render_for_model(outcome), "TIMEOUT: cancel confirmed, robot stopped")
        self.assertEqual(len(backend.cancels), 1)
        self.assertGreaterEqual(outcome.seconds, POLICY.execution_seconds)
        backend.run_seconds = 1.0
        self.assertEqual(executor.execute("navigate_to_pose", GOOD).result, Result.SUCCEEDED)

    def test_timeout_with_a_failed_cancel_locks_and_never_auto_unlocks(self):
        executor, backend, _ = build()
        backend.run_seconds, backend.cancel_works = 1e9, False
        outcome = executor.execute("navigate_to_pose", GOOD)
        self.assertEqual((outcome.result, outcome.motion_confirmed_stopped, outcome.state_after), (Result.TIMEOUT, False, ExecutorState.UNKNOWN_LOCKED))
        self.assertEqual(render_for_model(outcome), "TIMEOUT: cancel requested, motion state unknown")
        sent_before = len(backend.sent)
        locked = executor.execute("navigate_to_pose", GOOD)
        self.assertEqual(render_for_model(locked), "LOCKED: previous goal unresolved")
        self.assertEqual(len(backend.sent), sent_before)       # nothing sent while locked
        self.assertEqual(executor.begin_episode()[0], False)   # a new episode is blocked, the lock is not released
        self.assertEqual(executor.state, ExecutorState.UNKNOWN_LOCKED)

    def test_lost_acknowledgement_is_never_resent(self):
        executor, backend, _ = build()
        backend.ack = Ack.NO_ANSWER   # the goal does not exist on the server, or the backend cannot say
        outcome = executor.execute("navigate_to_pose", GOOD)
        self.assertEqual((outcome.result, outcome.state_after), (Result.TIMEOUT, ExecutorState.UNKNOWN_LOCKED))
        self.assertEqual(len(backend.sent), 1)
        self.assertEqual(len(backend.cancels), 1)
        self.assertEqual(executor.execute("navigate_to_pose", GOOD).result, Result.LOCKED)
        self.assertEqual(len(backend.sent), 1)

    def test_lost_acknowledgement_reconciled_by_goal_id_when_the_goal_exists(self):
        executor, backend, _ = build()
        backend.ack, backend.goal_exists_after_lost_ack = Ack.NO_ANSWER, True
        outcome = executor.execute("navigate_to_pose", GOOD)
        self.assertEqual(outcome.result, Result.SUCCEEDED)   # tracked as a normal goal, not resent
        self.assertEqual(len(backend.sent), 1)

    def test_a_backend_that_raises_after_sending_locks_instead_of_crashing(self):
        executor, backend, _ = build()
        backend.send_goal = lambda *a, **k: (_ for _ in ()).throw(ConnectionError("gone"))
        backend.poll_raises = True
        outcome = executor.execute("navigate_to_pose", GOOD)
        self.assertEqual(outcome.state_after, ExecutorState.UNKNOWN_LOCKED)
        self.assertEqual(executor.execute("navigate_to_pose", GOOD).result, Result.LOCKED)


class EpisodeContractTests(unittest.TestCase):
    def test_begin_episode_is_blocked_while_a_goal_is_unresolved_and_allowed_after_a_known_end(self):
        executor, _, _ = build()
        self.assertEqual(executor.begin_episode(), (True, ""))
        executor.execute("navigate_to_pose", GOOD)
        self.assertEqual(executor.state, ExecutorState.TERMINAL)
        self.assertEqual(executor.begin_episode(), (True, ""))
        executor.state = ExecutorState.ACTIVE   # an old goal still active (set by hand: execute() blocks until the end)
        self.assertEqual(executor.begin_episode()[0], False)

    def test_event_log_has_one_call_row_per_call_with_goal_id(self):
        executor, _, _ = build(make_goal_id=iter(["g1", "g2"]).__next__)
        executor.execute("navigate_to_pose", GOOD)
        calls = [e for e in executor.events if e["kind"] == "call"]
        self.assertEqual((len(calls), calls[0]["goal_id"], calls[0]["result"]), (1, "g1", "SUCCEEDED"))


class PostActionStateSwitchTests(unittest.TestCase):
    def test_default_is_off_and_the_state_is_never_read(self):
        executor, backend, _ = build()
        outcome = executor.execute("navigate_to_pose", GOOD)
        self.assertIsNone(outcome.post_action_state)
        self.assertNotIn("State after action", render_for_model(outcome))
        self.assertEqual(backend.observed, 0)

    def test_on_appends_one_line_after_a_goal_was_sent_only(self):
        executor, backend, _ = build(ExecutorOptions(attach_post_action_state=True))
        text = render_for_model(executor.execute("navigate_to_pose", GOOD))
        self.assertEqual(text, "SUCCEEDED\nState after action: pose x=1.00 y=2.00 yaw=0.00")
        self.assertEqual(backend.observed, 1)
        rejected = executor.execute("navigate_to_pose", {"x": 99.0, "y": 0.0, "yaw": 0.0})   # no goal sent: no state line
        self.assertNotIn("State after action", render_for_model(rejected))
        self.assertEqual(backend.observed, 1)

    def test_the_switch_changes_only_the_text_not_the_decisions(self):
        results = []
        for attach in (False, True):
            executor, backend, _ = build(ExecutorOptions(attach_post_action_state=attach))
            backend.run_seconds, backend.cancel_works = 1e9, False
            outcome = executor.execute("navigate_to_pose", GOOD)
            results.append((outcome.result, outcome.state_after, len(backend.sent), len(backend.cancels)))
        self.assertEqual(results[0], results[1])

    def test_a_failing_state_read_does_not_break_the_result(self):
        executor, backend, _ = build(ExecutorOptions(attach_post_action_state=True))
        backend.observe_state = lambda: (_ for _ in ()).throw(RuntimeError("no odom"))
        text = render_for_model(executor.execute("navigate_to_pose", GOOD))
        self.assertTrue(text.startswith("SUCCEEDED\nState after action: unavailable"))


class SchemaTests(unittest.TestCase):
    def test_tool_schema_is_generated_from_the_policy(self):
        schema = tool_schema(NAVIGATE)["function"]
        self.assertEqual(schema["name"], "navigate_to_pose")
        self.assertEqual(sorted(schema["parameters"]["properties"]), ["x", "y", "yaw"])
        self.assertIn("meters", schema["parameters"]["properties"]["x"]["description"])
        self.assertEqual(schema["parameters"]["required"], ["x", "y", "yaw"])


if __name__ == "__main__":
    unittest.main()
