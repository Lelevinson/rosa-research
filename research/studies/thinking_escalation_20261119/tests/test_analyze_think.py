"""Tests of the frozen decision rule with synthetic aggregates. uv run python -m unittest discover -s research/studies/thinking_escalation_20261119/tests"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analyze_think as N  # noqa: E402


def agg(episodes=80, supported=60, requests=500, o2=0.5, events=20, wall=1000, tokens=1000, bad=0, cuts=0):
    return dict(episodes=episodes, supported=supported, requests=requests, O2_rate=o2, events_with_next=events, wall_seconds=wall, input_tokens=tokens, output_tokens=0, timeouts=bad, capped=0, no_answer=0, length_cuts=cuts)


MODELS = ["a", "b", "c", "d"]


def decide(full=None, esc=None, alw=None, full_m=None, esc_m=None):
    full, esc, alw = full or agg(), esc or agg(o2=0.65), alw or agg(supported=66)
    fm = {m: (full_m or {}).get(m, agg()) for m in MODELS}
    em = {m: (esc_m or {}).get(m, agg(o2=0.65)) for m in MODELS}
    return N.decide(dict(FULL=full, ESCALATE=esc, ALWAYS=alw), dict(FULL=fm, ESCALATE=em, ALWAYS=fm))


class DecisionTests(unittest.TestCase):
    def test_class_a(self):
        d = decide(); self.assertTrue(d["mechanism_met"]); self.assertEqual(d["klass"], "A"); self.assertTrue(d["C0_headroom"])

    def test_pooled_gain_threshold_is_ten_points(self):
        self.assertTrue(decide(esc=agg(o2=0.60))["mechanism_met"]); self.assertFalse(decide(esc=agg(o2=0.59))["mechanism_met"])

    def test_models_below_15_events_cannot_count(self):
        few = {m: agg(events=14) for m in MODELS}
        d = decide(full_m=few); self.assertEqual(d["evaluable_models"], 0); self.assertFalse(d["mechanism_met"])

    def test_needs_two_models_higher(self):
        em = {"a": agg(o2=0.7), "b": agg(o2=0.4), "c": agg(o2=0.4), "d": agg(o2=0.4)}
        self.assertFalse(decide(esc_m=em)["mechanism_met"])

    def test_harm_flags_and_classes(self):
        self.assertEqual(decide(esc=agg(o2=0.5, supported=56))["klass"], "C")
        self.assertEqual(decide(esc=agg(o2=0.5, supported=57))["klass"], "B")
        d = decide(esc=agg(o2=0.7, requests=575)); self.assertEqual(d["klass"], "D")
        self.assertIn("timeouts + cap endings + no-answer endings up by 5 or more", decide(esc=agg(o2=0.5, bad=5))["harm_flags"])
        self.assertIn("length-cut responses up by 10 or more", decide(esc=agg(o2=0.5, cuts=10))["harm_flags"])

    def test_cost_flags_do_not_change_the_class(self):
        d = decide(esc=agg(o2=0.7, tokens=1500, wall=1500)); self.assertEqual(d["klass"], "A"); self.assertEqual(len(d["cost_flags"]), 2)

    def test_no_headroom_is_reported_separately(self):
        d = decide(alw=agg(supported=63)); self.assertFalse(d["C0_headroom"]); self.assertEqual(d["klass"], "A")


class PartAOnlyTests(unittest.TestCase):
    def test_no_always_arm_means_c0_is_not_evaluated_and_the_class_still_comes_from_escalate_vs_full(self):
        empty = dict(supported=0, requests=0, O2_rate=None, events_with_next=0, wall_seconds=0, input_tokens=0, output_tokens=0, timeouts=0, capped=0, no_answer=0, length_cuts=0, episodes=0)
        fm = {m: agg() for m in MODELS}; em = {m: agg(o2=0.65) for m in MODELS}
        d = N.decide(dict(FULL=dict(agg(), episodes=80), ESCALATE=dict(agg(o2=0.65), episodes=80), ALWAYS=empty), dict(FULL=fm, ESCALATE=em, ALWAYS={}))
        self.assertIsNone(d["C0_headroom"]); self.assertIsNone(d["always_minus_full_supported"]); self.assertEqual(d["klass"], "A")


class EstimateTests(unittest.TestCase):
    def test_thinking_estimate(self):
        end = dict(usage=dict(output_tokens=100), message=dict(content="x" * 40, tool_calls=[]))
        self.assertEqual(N.thinking_estimate(end), 100 - 11)  # 40 chars + "[]" = 42 chars -> ceil(42/4) = 11
        self.assertEqual(N.thinking_estimate(dict(usage=dict(output_tokens=3), message=dict(content="x" * 400, tool_calls=[]))), 0)


if __name__ == "__main__":
    unittest.main()
