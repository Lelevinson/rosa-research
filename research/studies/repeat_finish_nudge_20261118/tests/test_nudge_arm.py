"""Focused fixtures for the nudge arms (no ROS, no Ollama). From the repository root:
  uv run python -m unittest discover -s research/studies/repeat_finish_nudge_20261118/tests -v"""
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import nudge_arm as A  # noqa: E402
from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: E402
from rosa.tools import ROSATools  # noqa: E402
import rosa.tools.ros2 as ros2  # noqa: E402

CONTEXT = dict(env="stage3", task=dict(id="u3", floor=None), ns="/plant32")


class Recorder:
    def __init__(self):
        self.rows = []

    def add(self, kind, **values):
        self.rows.append(dict(kind=kind, **values))

    def events(self, name):
        return [r for r in self.rows if r["kind"] == "handler" and r.get("event") == name]


class Fixture:
    def __init__(self, variant, text="Node name: anvil\n"):
        self.recorder, self.text = Recorder(), text
        ros2.execute_ros_command = lambda command, *a, **k: (True, self.text)
        self.arm = A.make_arm(variant, self.recorder, CONTEXT)
        self.tools = {t.name: t for t in self.arm.wrap_tools(ROSATools(2, blacklist=[]).get_tools())}
        self.schemas = [convert_to_openai_tool(t) for t in self.tools.values()]

    def call(self, name, args):
        self.arm.visible_schemas(self.schemas, [])
        return self.tools[name].run(args)


class NudgeTests(unittest.TestCase):
    def test_prompt_and_offered_schemas_identical(self):
        full, nudge = Fixture("FULL"), Fixture("NUDGE")
        self.assertEqual(full.arm.prompt_messages, nudge.arm.prompt_messages)
        self.assertEqual(full.arm.visible_schemas(full.schemas, []), nudge.arm.visible_schemas(nudge.schemas, []))

    def test_first_call_is_never_nudged(self):
        f = Fixture("NUDGE")
        out = f.call("ros2_node_list", {})
        self.assertNotIn(A.NUDGE_LINE, json.dumps(out))
        self.assertEqual(f.recorder.events("identical_repeat"), [])

    def test_identical_repeat_gets_the_fixed_line_in_nudge_only(self):
        for variant in ("FULL", "NUDGE"):
            f = Fixture(variant)
            first = f.call("ros2_node_list", {})
            second = f.call("ros2_node_list", {})
            events = f.recorder.events("identical_repeat")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["fired"], variant == "NUDGE")
            self.assertEqual(events[0]["request"], 2)
            if variant == "FULL":
                self.assertEqual(second, first)
            else:
                self.assertEqual(A.strip_nudge(second), first)
                self.assertIn(A.NUDGE_LINE, json.dumps(second))

    def test_fires_at_most_twice_but_all_repeats_are_logged(self):
        f = Fixture("NUDGE")
        outs = [f.call("ros2_node_list", {}) for _ in range(5)]
        fired = [A.NUDGE_LINE in json.dumps(o) for o in outs]
        self.assertEqual(fired, [False, True, True, False, False])
        events = f.recorder.events("identical_repeat")
        self.assertEqual([e["fired"] for e in events], [True, True, False, False])
        self.assertEqual([e["repeat_number"] for e in events], [1, 2, 3, 4])

    def test_same_arguments_with_a_different_result_is_not_a_repeat(self):
        f = Fixture("NUDGE")
        f.call("ros2_node_list", {})
        f.text = "Node name: basalt\n"
        out = f.call("ros2_node_list", {})
        self.assertNotIn(A.NUDGE_LINE, json.dumps(out))
        self.assertEqual(f.recorder.events("identical_repeat"), [])

    def test_different_arguments_with_the_same_result_is_not_a_repeat(self):
        f = Fixture("NUDGE")
        f.call("ros2_topic_info", {"topics": ["/plant32/a"]})
        out = f.call("ros2_topic_info", {"topics": ["/plant32/b"]})
        self.assertNotIn(A.NUDGE_LINE, json.dumps(out))

    def test_a_result_containing_an_item_error_is_not_a_successful_call(self):
        f = Fixture("NUDGE", text="Error: Unable to find node\n")
        f.arm.record_step = lambda *a, **k: None
        # drive the arm directly with a per-item error dict, as list tools return for a failed item
        class T: name = "ros2_node_info"; func = staticmethod(lambda **kw: {"/x/y": {"error": "Unable to find node"}})
        f.arm.offered = {"ros2_node_info"}
        a = f.arm.execute(T, {"nodes": ["/x/y"]})
        b = f.arm.execute(T, {"nodes": ["/x/y"]})
        self.assertEqual(a, b)
        self.assertEqual(f.recorder.events("identical_repeat"), [])

    def test_dict_result_gets_one_extra_key_and_keeps_its_own(self):
        out = A.with_nudge({"nodes": ["/a"]})
        self.assertEqual(out, {"nodes": ["/a"], "note": A.NUDGE_LINE})
        self.assertEqual(A.strip_nudge(out), {"nodes": ["/a"]})
        self.assertEqual(A.strip_nudge(A.with_nudge("text")), "text")

    def test_line_is_the_owner_text(self):
        self.assertEqual(A.NUDGE_LINE, "Note: this call repeated an earlier call and returned the same result. If you already have what the task asks for, call final_answer now; otherwise try a different call.")


if __name__ == "__main__":
    unittest.main()
