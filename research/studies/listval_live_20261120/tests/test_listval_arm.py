"""Tests of the LISTVAL rendering and the switch. uv run python -m unittest discover -s research/studies/listval_live_20261120/tests"""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import listval_arm as L  # noqa: E402

LISTED = {"/e1h/willow": ["  mode", "  start_type_description_service", "  use_sim_time"]}
VALUES = {"mode": "String value is: idle\n", "start_type_description_service": "Boolean value is: True\n", "use_sim_time": "Boolean value is: False\n"}


def reader(node, name):
    return {name: VALUES[name]}


class RenderTests(unittest.TestCase):
    def test_renders_name_value_per_parameter_in_order(self):
        out, info = L.render_inline(LISTED, reader)
        self.assertEqual(out, {"/e1h/willow": ["mode: idle", "start_type_description_service: True", "use_sim_time: False"]})
        self.assertTrue(info["rendered"])
        self.assertEqual(info["params"], ["mode", "start_type_description_service", "use_sim_time"])

    def test_failed_value_read_is_shown_not_dropped(self):
        def flaky(node, name):
            return {"error": "Parameter not set"} if name == "mode" else reader(node, name)
        out, info = L.render_inline(LISTED, flaky)
        self.assertEqual(out["/e1h/willow"][0], "mode: <unreadable>")
        self.assertEqual(len(out["/e1h/willow"]), 3)
        self.assertEqual(info["unreadable"], 1)

    def test_exception_in_read_is_shown_as_unreadable(self):
        def boom(node, name):
            raise RuntimeError("x")
        out, info = L.render_inline(LISTED, boom)
        self.assertEqual(out["/e1h/willow"], [f"{n}: <unreadable>" for n in ("mode", "start_type_description_service", "use_sim_time")])

    def test_cap_fallback_returns_the_original_object(self):
        big = {"/n": [f"  p{i}" for i in range(200)]}
        out, info = L.render_inline(big, lambda node, name: {name: "Integer value is: 123456\n"})
        self.assertIs(out, big)
        self.assertEqual(info["reason"], "over_cap")
        self.assertGreater(info["chars"], 2000)

    def test_cap_boundary(self):
        out, info = L.render_inline({"/n": ["  a"]}, lambda n, p: {p: "String value is: x\n"}, cap=len('{"/n": ["a: x"]}'))
        self.assertTrue(info["rendered"])
        out, info = L.render_inline({"/n": ["  a"]}, lambda n, p: {p: "String value is: x\n"}, cap=len('{"/n": ["a: x"]}') - 1)
        self.assertFalse(info["rendered"])

    def test_error_and_odd_shapes_untouched(self):
        for odd in ({"error": "Node not found\n"}, {"/a": ["  x"], "/b": ["  y"]}, "text", {"/a": "notalist"}):
            out, info = L.render_inline(odd, reader)
            self.assertIs(out, odd)
            self.assertFalse(info["rendered"])

    def test_string_value_with_spaces_kept(self):
        out, _ = L.render_inline({"/n": ["  m"]}, lambda n, p: {p: "String value is: fast and loose\n"})
        self.assertEqual(out["/n"], ["m: fast and loose"])


class FakeTool:
    name = "ros2_param_list"
    def __init__(self, result): self.result = result
    def func(self, **kw): return copy.deepcopy(self.result)


class FakeRecorder:
    def __init__(self): self.events = []
    def add(self, kind, **values): self.events.append((kind, values))


class SwitchTests(unittest.TestCase):
    def arm(self, variant, **kw):
        recorder = FakeRecorder()
        arm = L.ListValArm(variant, recorder, dict(env="e1h", task={"id": "x"}, ns="/e1h"), [], **kw)
        arm.read_param = reader
        return arm, recorder

    def test_default_switch_off_for_full_and_on_for_listval(self):
        self.assertFalse(self.arm("FULL")[0].inline_param_values)
        self.assertTrue(self.arm("LISTVAL")[0].inline_param_values)

    def test_switch_off_output_is_identical_and_untouched(self):
        arm, rec = self.arm("FULL")
        tool = FakeTool(LISTED)
        self.assertEqual(arm.call_inner(tool, {"node_name": "/e1h/willow"}), LISTED)
        self.assertEqual([e for e in rec.events if e[1].get("event") == "listval_inline"], [])

    def test_switch_on_renders_only_param_list_with_node_name(self):
        arm, rec = self.arm("LISTVAL")
        out = arm.call_inner(FakeTool(LISTED), {"node_name": "/e1h/willow"})
        self.assertEqual(out["/e1h/willow"][0], "mode: idle")
        self.assertTrue(any(e[1].get("event") == "listval_inline" for e in rec.events))
        self.assertEqual(arm.call_inner(FakeTool(LISTED), {}), LISTED)            # whole-system listing untouched
        other = FakeTool({"x": 1}); other.name = "ros2_param_get"
        self.assertEqual(arm.call_inner(other, {"node_name": "/e1h/willow", "param_name": "mode"}), {"x": 1})

    def test_explicit_option_overrides_variant(self):
        self.assertTrue(self.arm("FULL", inline_param_values=True)[0].inline_param_values)


if __name__ == "__main__":
    unittest.main()
