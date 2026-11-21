"""Tests of the replication analysis helpers (synthetic data). uv run python -m unittest discover -s research/studies/thinking_escalation_20261119/tests"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analyze_replication as R  # noqa: E402


def ep(arm, task, sup, req=5, tok=1000, o2=0, ev=0, model="m"):
    return dict(arm=arm, task=task, model=model, supported=sup, requests=req, input_tokens=tok, output_tokens=0, O2_hits=o2, O2_events=ev)


class HelperTests(unittest.TestCase):
    def test_runaway_rule(self):
        self.assertTrue(R.runaway([True] * 10 + [None], ["stop"] * 11))                      # 10 requests with thinking on
        self.assertFalse(R.runaway([True] * 9 + [None], ["stop"] * 10))
        self.assertTrue(R.runaway([None, True], ["stop", "length"]))                          # length cut while thinking was on
        self.assertFalse(R.runaway([None, None], ["stop", "length"]))                         # length cut with thinking off is not a thinking runaway

    def test_cluster_bootstrap_point_estimates_and_degenerate_case(self):
        rows = []
        for t in range(6):
            rows += [ep("FULL", f"t{t}", 1, req=10, o2=1, ev=4), ep("ESCALATE", f"t{t}", 1, req=5, o2=3, ev=4)]
        out = R.cluster_intervals(rows, draws=200)
        self.assertEqual(out["tasks"], 6)
        self.assertEqual(out["point"]["diff_points"], 0.0)
        self.assertEqual(out["point"]["request_ratio"], 0.5)
        self.assertEqual(out["point"]["o2_diff_points"], 50.0)
        self.assertEqual(out["interval_95"]["request_ratio"], [0.5, 0.5])                    # identical tasks: no spread
        self.assertIsNone(R.cluster_intervals([ep("FULL", "a", 1), ep("ESCALATE", "a", 0)], draws=10))   # one task cannot be bootstrapped

    def test_cluster_bootstrap_resamples_tasks_not_episodes(self):
        rows = []
        for t in range(10):
            good = t < 5
            rows += [ep("FULL", f"t{t}", 1), ep("FULL", f"t{t}", 1), ep("ESCALATE", f"t{t}", 1 if good else 0), ep("ESCALATE", f"t{t}", 1 if good else 0)]
        out = R.cluster_intervals(rows, draws=1000)
        self.assertEqual(out["point"]["diff_points"], -50.0)
        lo, hi = out["interval_95"]["diff_points"]
        self.assertTrue(lo < -50.0 < hi)                                                     # a real interval from between-task spread

    def test_shared_tasks_are_the_ten_standard_dev_tasks(self):
        self.assertEqual(len(R.SHARED_TASKS), 10)
        self.assertTrue(all(not t.startswith("nf_") for t in R.SHARED_TASKS))


if __name__ == "__main__":
    unittest.main()
