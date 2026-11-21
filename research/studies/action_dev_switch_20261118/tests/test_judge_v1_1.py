from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from judge_v1_1 import judge


class WrappedTextTests(unittest.TestCase):
    def score(self, answer, *, ending="text", true_heading=1.0):
        return judge("S1", answer, true_heading, 5.0, 5.0, True, ending=ending)

    def test_last_complete_object_in_text(self):
        answer = 'Draft {"heading": 0.0}. Final: {"answer": {"heading": 1.0}} {'
        self.assertTrue(self.score(answer)["success"])

    def test_plain_object_remains_valid(self):
        self.assertTrue(self.score('{"heading": 1.0}')["success"])
        self.assertTrue(self.score({"heading": 1.0}, ending="final_answer")["success"])

    def test_only_singleton_object_wrappers_are_unwrapped_once(self):
        for answer in (
            '{"answer": {"heading": 1.0}, "extra": 0}',
            '{"answer": 1.0}',
            '{"answer": {"answer": {"heading": 1.0}}}',
        ):
            with self.subTest(answer=answer):
                self.assertFalse(self.score(answer)["success"])

    def test_tool_answer_does_not_use_text_wrapper_rule(self):
        self.assertFalse(self.score({"answer": {"heading": 1.0}}, ending="final_answer")["success"])
        self.assertFalse(self.score('{"answer": {"heading": 1.0}}', ending="final_answer")["success"])

    def test_unwrapped_answer_still_requires_true_pose_and_numeric_value(self):
        self.assertFalse(self.score('{"answer": {"heading": 1.0}}', true_heading=0.0)["success"])
        self.assertFalse(self.score('{"answer": {"heading": true}}')["success"])
