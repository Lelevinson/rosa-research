"""Focused fixtures for the live rendering arms (no ROS, no Ollama). From the repository root:
  uv run python -m unittest discover -s research/studies/canonical_render_20261118/tests -v"""
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import render_arm as A  # noqa: E402
import render_core  # noqa: E402
from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: E402
from rosa.tools import ROSATools  # noqa: E402
import rosa.tools.ros2 as ros2  # noqa: E402

CONTEXT = dict(env="stage3", task=dict(id="u3", floor=None), ns="/plant32")
TOPIC_INFO = ("Type: std_msgs/msg/String\n\nPublisher count: 1\n\nNode name: anvil\nNode namespace: /plant32\nEndpoint type: PUBLISHER\nQoS profile:\n  Reliability: RELIABLE\n\n"
              "Subscription count: 0\n\n")


class Recorder:
    def __init__(self):
        self.rows = []

    def add(self, kind, **values):
        self.rows.append(dict(kind=kind, **values))

    def events(self, name):
        return [r for r in self.rows if r["kind"] == "handler" and r.get("event") == name]


class Fixture:
    def __init__(self, variant, ros_text=TOPIC_INFO, ok=True):
        self.recorder = Recorder()
        ros2.execute_ros_command = lambda command, *a, **k: (ok, ros_text)
        self.arm = A.make_arm(variant, self.recorder, CONTEXT)
        self.tools = {t.name: t for t in self.arm.wrap_tools(ROSATools(2, blacklist=[]).get_tools())}
        self.schemas = [convert_to_openai_tool(t) for t in self.tools.values()]

    def call(self, name, args):
        self.arm.visible_schemas(self.schemas, [])
        return self.tools[name].run(args)


class ArmTests(unittest.TestCase):
    def test_prompt_and_offered_schemas_are_identical(self):
        full, render = Fixture("FULL"), Fixture("RENDER")
        self.assertEqual(full.arm.prompt_messages, render.arm.prompt_messages)
        self.assertEqual(full.arm.visible_schemas(full.schemas, []), render.arm.visible_schemas(render.schemas, []))

    def test_full_returns_the_raw_result_and_render_returns_the_rendering_of_the_same_raw_result(self):
        raw = Fixture("FULL").call("ros2_topic_info", {"topics": ["/plant32/reef_t"]})
        out = Fixture("RENDER").call("ros2_topic_info", {"topics": ["/plant32/reef_t"]})
        self.assertNotIn("full name", json.dumps(raw))
        self.assertEqual(out, render_core.render_result(raw))
        self.assertIn("Node full name: /plant32/anvil", out["/plant32/reef_t"])

    def test_render_applied_event_keeps_the_raw_result_only_when_changed(self):
        f = Fixture("RENDER")
        raw = Fixture("FULL").call("ros2_topic_info", {"topics": ["/plant32/reef_t"]})
        f.call("ros2_topic_info", {"topics": ["/plant32/reef_t"]})
        events = f.recorder.events("render_applied")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["raw"], raw)
        g = Fixture("RENDER", ros_text="Integer value is: 5\n")
        g.call("ros2_param_get", {"node_name": "/plant32/a", "param_name": "gain"})
        self.assertEqual(g.recorder.events("render_applied"), [])   # unchanged result: no event

    def test_failed_results_and_blocked_tools_are_not_rendered(self):
        failing = Fixture("RENDER", ros_text="Unable to find node 'x'\n", ok=False)
        text = str(failing.call("ros2_node_info", {"nodes": ["/plant32/x"]}))
        self.assertIn("Unable to find", text)
        self.assertEqual(failing.recorder.events("render_applied"), [])
        blocked = Fixture("RENDER")
        message = blocked.call("ros2_param_set", {"node_name": "/plant32/a", "param_name": "gain", "param_value": "1"})  # C1 hands the block back as a tool message
        self.assertIn("not available", str(message))
        self.assertEqual(blocked.recorder.events("render_applied"), [])

    def test_the_harness_bookkeeping_sees_the_raw_result(self):
        f = Fixture("RENDER")
        f.call("ros2_topic_info", {"topics": ["/plant32/reef_t"]})
        step = f.arm.steps[-1]
        self.assertNotIn("full name", json.dumps(step.output))


class PlanTests(unittest.TestCase):
    def test_plan_is_288_cells_144_per_arm_two_seeds_three_environments_deterministic(self):
        import run_render as R
        plan = R.plan_for("full")
        cells = [c for v in plan.values() for c in v]
        self.assertEqual(len(cells), 288)
        self.assertEqual(sorted(plan), sorted(f"{m.replace(':', '_')}-{e}" for m in R.MODELS for e in ("stage3", "e1h", "namefix")))
        for arm in A.ARMS:
            self.assertEqual(sum(c["arm"] == arm for c in cells), 144)
        self.assertEqual({c["seed"] for c in cells}, {1, 2})
        self.assertEqual({c["task"] for c in cells}, set(R.STAGE3_TASKS + R.E1H_TASKS + R.NAMEFIX_TASKS))
        self.assertEqual(len({(c["model"], c["task"], c["seed"], c["arm"]) for c in cells}), 288)
        self.assertEqual(R.plan_for("full"), plan)
        smoke = [c for v in R.plan_for("smoke").values() for c in v]
        self.assertEqual(sorted((c["task"], c["arm"]) for c in smoke), sorted((t, a) for t in ("u3", "e1h_amb_1", "nf_single_1") for a in A.ARMS))
        self.assertTrue(all(t in R.TASKS for t in {c["task"] for c in cells}))


if __name__ == "__main__":
    unittest.main()
