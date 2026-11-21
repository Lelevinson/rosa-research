from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from judge_v1_2 import Completion, Dispatch, Read, Step, judge, judge_contract

PASS = {"success": True, "reasons": []}
SOURCE = ("parameter", "/fixture", "bearing")
STEP1 = Step("rotate", (0.5,), (.01,), (0,))
STEP2 = Step("rotate", (-1.2,), (.01,), (0,))
DYNAMIC = Step("navigate", None, (.01, .01, .01), (2,), SOURCE,
               lambda read: (read["x"], read["y"], read["theta"]))


class SequenceTests(unittest.TestCase):
    def test_both_actions_required_even_with_correct_final_state(self):
        first = Dispatch("1", "rotate", (.5,))
        second = Dispatch("2", "rotate", (-1.2,))
        done1, done2 = Completion("1", True), Completion("2", True)
        cases = [
            ([first, done1, second, done2], True),
            ([second, done2], False),
            ([second, done2, first, done1], False),
            ([first, second, done1, done2], False),
            ([first, Completion("1", False), second, done2], False),
            ([first, done1, Dispatch("1", "rotate", (-1.2,)), done2], False),
            ([first, done1, second], False),
            ([first, done1, second, done2, first, done1], False),
        ]
        for events, success in cases:
            with self.subTest(events=events):
                self.assertEqual(judge_contract(PASS, [STEP1, STEP2], events)["success"], success)

    def test_read_must_precede_and_match_dispatched_goal(self):
        read = Read(SOURCE, {"x": 1, "y": 2, "theta": -0.1}, 1)
        dispatch = Dispatch("1", "navigate", (1, 2, -.1), 2)
        done = Completion("1", True)
        newer = Read(SOURCE, {"x": 5, "y": 2, "theta": -0.1}, 1)
        cases = [
            ([read, dispatch, done], True),
            ([dispatch, done], False),
            ([dispatch, read, done], False),
            ([read, newer, dispatch, done], False),
            ([Read(("wrong",), read.value, 1), dispatch, done], False),
            ([Read(SOURCE, read.value, 2), dispatch, done], False),
            ([Read(SOURCE, {"x": 1}, 1), dispatch, done], False),
            ([read, Dispatch("1", "navigate", (1, 2, float("nan")), 2), done], False),
        ]
        for events, success in cases:
            with self.subTest(events=events):
                self.assertEqual(judge_contract(PASS, [DYNAMIC], events)["success"], success)

    def test_terminal_verdict_still_required(self):
        self.assertFalse(judge_contract({"success": False, "reasons": ["false answer"]}, [], [])["success"])

    def test_no_goal_requires_proven_empty_capture(self):
        self.assertTrue(judge_contract(PASS, [], [])["success"])
        self.assertFalse(judge_contract(PASS, [], None)["success"])
        self.assertFalse(judge_contract(PASS, [], [Dispatch("1", "rotate", (.5,))])["success"])


class ArchivedTraceFormatTests(unittest.TestCase):
    def setUp(self):
        args = {"theta": .69}
        self.trace = [
            {"kind": "assistant"},
            {"kind": "tool", "name": "get_parameter",
             "arguments": {"node_name": "/turtlesim", "parameter_name": "background_r"},
             "content": "Integer value is: 69"},
            {"kind": "assistant"},
            {"kind": "tool", "name": "rotate_to_heading", "arguments": args, "content": "SUCCEEDED"},
            {"kind": "executor_events", "events": [
                {"kind": "state", "goal_id": "a", "state": state}
                for state in ("PENDING", "ACTIVE", "TERMINAL")
            ] + [{"kind": "call", "tool": "rotate_to_heading", "arguments": args,
                  "goal_id": "a", "result": "SUCCEEDED"}]},
        ]

    def score(self, trace):
        return judge("R1", {"background_r": 69, "heading": .69}, .69, 5., 5., True,
                     ending="final_answer", trace=trace)

    def test_public_dev_trace_shape(self):
        self.assertTrue(self.score(self.trace)["success"])
        self.assertFalse(self.score(self.trace[:-1])["success"])
        self.assertFalse(self.score(self.trace[:2] + self.trace[3:])["success"])

    def test_claimed_success_without_terminal_event_is_rejected(self):
        broken = deepcopy(self.trace)
        del broken[-1]["events"][2]
        self.assertFalse(self.score(broken)["success"])

    def test_read_value_is_used_even_when_answer_repeats_expected_constant(self):
        broken = deepcopy(self.trace)
        broken[1]["content"] = "Integer value is: 68"
        self.assertFalse(self.score(broken)["success"])


if __name__ == "__main__":
    unittest.main()
