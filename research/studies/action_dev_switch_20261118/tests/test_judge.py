"""Offline tests of judge.py (no ROS). From the repo root: uv run python -m unittest discover -s research/studies/action_dev_switch_20261118/tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from judge import TASKS, judge  # noqa: E402


class JudgeTests(unittest.TestCase):
    def test_single_success_and_failures(self):
        self.assertTrue(judge("S1", {"heading": 0.99}, 0.988, 5.54, 5.54, True)["success"])
        self.assertFalse(judge("S1", {"heading": 1.0}, 0.5, 5.54, 5.54, True)["success"])          # did not turn
        self.assertFalse(judge("S1", {"heading": 0.3}, 0.988, 5.54, 5.54, True)["success"])        # turned, reported wrongly
        self.assertFalse(judge("S1", None, 0.988, 5.54, 5.54, True)["success"])                    # no answer
        self.assertFalse(judge("S1", {"heading": "0.99"}, 0.988, 5.54, 5.54, True)["success"])     # a string is not a number
        self.assertFalse(judge("S1", {"heading": 0.99}, 0.988, 5.54, 5.54, False)["success"])      # still moving

    def test_answer_may_be_a_json_string(self):
        self.assertTrue(judge("S2", '{"heading": -2.49}', -2.49, 5.5, 5.5, True)["success"])

    def test_equivalent_angle_counts_for_the_range_trap(self):
        self.assertTrue(judge("S3", {"heading": -2.28}, -2.283, 5.5, 5.5, True)["success"])         # 4.0 rad is -2.283 rad
        self.assertTrue(judge("S3", {"heading": 4.0}, -2.283, 5.5, 5.5, True)["success"])           # reporting the equivalent angle 4.0 is accepted too
        self.assertFalse(judge("S3", {"heading": -2.28}, 0.0, 5.5, 5.5, True)["success"])

    def test_r1_needs_the_parameter_value_and_the_heading(self):
        self.assertTrue(judge("R1", {"background_r": 69, "heading": 0.69}, 0.688, 5.5, 5.5, True)["success"])
        self.assertFalse(judge("R1", {"background_r": 70, "heading": 0.69}, 0.688, 5.5, 5.5, True)["success"])
        self.assertFalse(judge("R1", {"heading": 0.69}, 0.688, 5.5, 5.5, True)["success"])

    def test_r2_position_tolerance(self):
        self.assertTrue(judge("R2", {"x": 5.54, "y": 5.5}, 1.19, 5.544, 5.544, True)["success"])
        self.assertFalse(judge("R2", {"x": 5.0, "y": 5.5}, 1.19, 5.544, 5.544, True)["success"])
        self.assertFalse(judge("R2", {"x": 5.54, "y": 5.5}, 0.0, 5.544, 5.544, True)["success"])    # did not turn

    def test_two_step_targets(self):
        self.assertTrue(judge("M3", {"heading": 2.49}, 2.49, 5.5, 5.5, True)["success"])
        self.assertFalse(judge("M3", {"heading": 1.0}, 0.99, 5.5, 5.5, True)["success"])            # stopped after the first step

    def test_task_table(self):
        self.assertEqual(len(TASKS), 8)
        self.assertEqual({t["kind"] for t in TASKS.values()}, {"single", "act_read", "two_step"})


if __name__ == "__main__":
    unittest.main()
