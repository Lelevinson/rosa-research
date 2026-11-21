"""Tests of the frozen decision rule with synthetic aggregates (no traces). uv run python -m unittest discover -s research/studies/repeat_finish_nudge_20261118/tests"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analyze_nudge as N  # noqa: E402


def agg(supported=60, R=100):
    return dict(supported=supported, R_sum=R)


MODELS = ["a", "b", "c", "d"]


def decide(full_R, nudge_R, full_sup=60, nudge_sup=60, early_full=0, early_nudge=0):
    full_by = {m: agg(R=r) for m, r in zip(MODELS, full_R)}
    nudge_by = {m: agg(R=r) for m, r in zip(MODELS, nudge_R)}
    return N.decide(agg(full_sup, sum(full_R)), agg(nudge_sup, sum(nudge_R)), full_by, nudge_by, early_full, early_nudge)


class DecisionTests(unittest.TestCase):
    def test_class_a_when_bar_met_and_no_harm(self):
        d = decide([100, 100, 5, 5], [60, 60, 5, 5])
        self.assertTrue(d["event_bar_met"]); self.assertEqual(d["klass"], "A")
        self.assertEqual(d["evaluable_models"], 2)

    def test_not_met_when_only_one_model_drops(self):
        d = decide([100, 100, 5, 5], [50, 100, 5, 5])
        self.assertFalse(d["event_bar_met"]); self.assertEqual(d["klass"], "B")

    def test_models_below_20_requests_cannot_count(self):
        d = decide([100, 19, 19, 19], [40, 0, 0, 0])
        self.assertEqual(d["models_with_drop_ge_30"], 1); self.assertFalse(d["event_bar_met"])

    def test_supported_loss_of_4_is_a_harm_flag_but_3_is_not(self):
        self.assertEqual(decide([100, 100, 5, 5], [100, 100, 5, 5], 60, 57)["klass"], "B")
        self.assertEqual(decide([100, 100, 5, 5], [100, 100, 5, 5], 60, 56)["klass"], "C")

    def test_early_answers_flag_and_class_d(self):
        d = decide([100, 100, 5, 5], [50, 50, 5, 5], early_full=0, early_nudge=1)
        self.assertEqual(d["klass"], "D"); self.assertIn("CHG early answers higher in NUDGE", d["harm_flags"])

    def test_threshold_is_exactly_30_percent(self):
        self.assertTrue(decide([100] * 4, [70] * 4)["event_bar_met"])
        self.assertFalse(decide([100] * 4, [71] * 4)["event_bar_met"])


if __name__ == "__main__":
    unittest.main()
