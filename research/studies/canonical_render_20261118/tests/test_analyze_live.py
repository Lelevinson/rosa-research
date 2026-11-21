"""Tests of the frozen reading rule (no model, no traces). From the repository root:
  uv run python -m unittest discover -s research/studies/canonical_render_20261118/tests -v"""
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import analyze_live as L  # noqa: E402


def agg(episodes=72, supported=60, requests=400, tokens=800000, capped=2, split=20, other=10):
    return dict(episodes=episodes, supported=supported, requests=requests, tokens=tokens, capped_or_no_answer=capped, fires_split_only=split, fires_other=other)


def arm(sn, overall):
    return dict(sn=sn, all=overall)


class DecisionTests(unittest.TestCase):
    def test_class_a_mechanism_without_harm(self):
        d = L.decide(arm(agg(), agg(episodes=144)), arm(agg(split=10, other=10), agg(episodes=144, supported=62)), {"a": 0, "b": 1, "c": 0, "d": 1})
        self.assertEqual((d["mechanism_signal"], d["harm_flags"], d["klass"]), (True, [], "A"))

    def test_class_b_no_mechanism_no_harm(self):
        d = L.decide(arm(agg(), agg(episodes=144)), arm(agg(split=18), agg(episodes=144)), {"a": 0})
        self.assertEqual((d["mechanism_signal"], d["klass"]), (False, "B"))

    def test_other_fires_falling_too_is_not_a_mechanism_signal(self):
        d = L.decide(arm(agg(), agg(episodes=144)), arm(agg(split=10, other=5), agg(episodes=144)), {"a": 0})
        self.assertFalse(d["mechanism_signal"])

    def test_each_harm_flag(self):
        base = arm(agg(), agg(episodes=144, supported=120, requests=1000, tokens=2000000, capped=3))
        cases = {"supported": agg(episodes=144, supported=110, requests=1000, tokens=2000000, capped=3),
                 "requests": agg(episodes=144, supported=120, requests=1150, tokens=2000000, capped=3),
                 "tokens": agg(episodes=144, supported=120, requests=1000, tokens=2200000, capped=3),
                 "capped": agg(episodes=144, supported=120, requests=1000, tokens=2000000, capped=8)}
        for name, overall in cases.items():
            d = L.decide(base, arm(agg(split=10), overall), {"a": 0})
            self.assertEqual(len(d["harm_flags"]), 1, name)
            self.assertEqual(d["klass"], "D", name)   # mechanism present in this fixture, so D
        d = L.decide(base, arm(agg(split=20), base["all"]), {"a": -4, "b": -4, "c": -5, "d": 0})
        self.assertEqual((d["harm_flags"], d["klass"]), (["supported lower by 4 or more cells in 3 or more models"], "C"))

    def test_boundaries_are_inclusive(self):
        base = arm(agg(), agg(episodes=144, supported=120, requests=1000, tokens=2000000))
        d = L.decide(base, arm(agg(split=14), agg(episodes=144, supported=110, requests=1000, tokens=2000000)), {"a": 0})   # exactly 30% drop and exactly -10 cells
        self.assertTrue(d["mechanism_signal"])
        self.assertIn("supported lower by 10 or more cells", d["harm_flags"])


class StratumTests(unittest.TestCase):
    def test_strata(self):
        self.assertEqual([L.stratum(t) for t in ("h4", "nf_exact", "p3", "e1h_abs_1")], ["S1", "S2", "S3", "S3"])


if __name__ == "__main__":
    unittest.main()
