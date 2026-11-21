"""Focused fixtures for the thinking arms (no ROS, no Ollama). From the repository root:
  uv run python -m unittest discover -s research/studies/thinking_escalation_20261119/tests -v"""
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import think_arm as A  # noqa: E402
from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: E402
from langchain_core.tools import ToolException  # noqa: E402
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
    def __init__(self, variant, model="qwen3.5:9b", text="Node name: anvil\n"):
        A.CURRENT_MODEL["name"] = model
        self.recorder, self.text = Recorder(), text
        ros2.execute_ros_command = lambda command, *a, **k: (True, self.text)
        self.arm = A.make_arm(variant, self.recorder, CONTEXT)
        self.tools = {t.name: t for t in self.arm.wrap_tools(ROSATools(2, blacklist=[]).get_tools())}
        self.schemas = [convert_to_openai_tool(t) for t in self.tools.values()]

    def request(self):
        """One model request as ThinkTracedModel does it: visible_schemas, then request_options."""
        self.arm.visible_schemas(self.schemas, [])
        return self.arm.request_options()

    def call(self, name, args):
        return self.tools[name].run(args)

    def levels(self):
        return [e["level"] for e in self.recorder.events("think_request")]


class ThinkTests(unittest.TestCase):
    def test_not_found_regex_equals_the_offline_replay_one(self):
        sys.path.insert(0, str(HERE.parent / "offline_replay_20261116"))
        import episodes
        self.assertEqual(A.NOT_FOUND.pattern, episodes.NOT_FOUND.pattern); self.assertEqual(A.NOT_FOUND.flags, episodes.NOT_FOUND.flags)

    def test_prompt_and_schemas_identical_across_arms(self):
        base = Fixture("FULL")
        for variant in ("ESCALATE", "ALWAYS"):
            other = Fixture(variant)
            self.assertEqual(base.arm.prompt_messages, other.arm.prompt_messages)
            self.assertEqual(base.arm.visible_schemas(base.schemas, []), other.arm.visible_schemas(other.schemas, []))

    def test_full_never_overrides(self):
        f = Fixture("FULL")
        self.assertEqual([f.request(), f.request()], [{}, {}])
        f.call("ros2_node_list", {}); f.call("ros2_node_list", {})  # an identical repeat is a trigger but FULL does not act
        self.assertEqual(f.request(), {})

    def test_always_overrides_every_request_with_the_right_value(self):
        self.assertEqual(Fixture("ALWAYS").request(), {"reasoning": True})
        self.assertEqual(Fixture("ALWAYS", model="gpt-oss:20b").request(), {"reasoning": "high"})
        self.assertEqual(Fixture("ALWAYS", model="bonsai-2:4b").request(), {"reasoning": True})

    def test_escalate_window_is_exactly_two_requests_after_a_trigger(self):
        f = Fixture("ESCALATE")
        self.assertEqual(f.request(), {})            # request 1
        f.text = "Error: Unable to find node '/x'"
        f.call("ros2_node_list", {})                 # not-found result -> trigger
        seq = [f.request(), f.request(), f.request()]
        self.assertEqual(seq, [{"reasoning": True}, {"reasoning": True}, {}])
        self.assertEqual(f.levels(), [None, True, True, None])

    def test_trigger_inside_the_window_resets_it(self):
        f = Fixture("ESCALATE", model="gpt-oss:20b")
        f.request(); f.text = "no such node"; f.call("ros2_node_list", {})
        self.assertEqual(f.request(), {"reasoning": "high"})      # escalated 1
        f.text = ""; f.call("ros2_node_list", {})                  # empty result inside the window -> reset to 2
        self.assertEqual([f.request(), f.request(), f.request()], [{"reasoning": "high"}, {"reasoning": "high"}, {}])

    def test_all_four_classes_are_classified_and_logged_in_every_arm(self):
        for variant in A.ARMS:
            f = Fixture(variant)
            f.request(); f.text = "ok one"; f.call("ros2_node_list", {})           # ok
            f.request(); f.call("ros2_node_list", {})                              # identical repeat
            f.request(); f.text = "Unable to find node"; f.call("ros2_node_list", {})  # not found
            f.request(); f.text = ""; f.call("ros2_node_list", {})                 # empty
            f.request()
            f.call("ros2_service_call", {"service_name": "/x", "service_type": "t", "request": {}})  # invalid arguments: strict pre-check rejects before execute()
            klasses = [e["klass"] for e in f.recorder.events("call_class")]
            self.assertEqual(klasses, ["ok", "repeat", "not_found", "empty", "error"], variant)

    def test_blocked_write_tool_with_valid_arguments_is_an_error_trigger(self):
        f = Fixture("ESCALATE"); f.request()
        schema = f.arm.schema_of("ros2_service_call")
        args = {k: ("{}" if v.get("type") == "string" and k == "request" else "/x") for k, v in schema["properties"].items() if k in schema.get("required", [])}
        f.call("ros2_service_call", args)
        self.assertEqual([e["klass"] for e in f.recorder.events("call_class")], ["error"])
        self.assertEqual(f.recorder.events("blocked_write_tool")[0]["tool"], "ros2_service_call")
        self.assertEqual(f.request(), {"reasoning": True})

    def test_capped_arm_equals_escalate_until_six_escalated_requests_then_thinking_stays_off(self):
        results = {}
        for variant in ("ESCALATE", "ESCALATE_CAPPED"):          # one fixture at a time: they share a module-level ROS stub
            f = Fixture(variant)
            f.request()
            for _ in range(8):                                    # a dead end after every request keeps re-arming the window
                f.text = "Unable to find node"
                f.call("ros2_node_list", {})
                f.request()
            results[variant] = f
        self.assertEqual(results["ESCALATE"].levels(), [None] + [True] * 8)                          # thinking on for every request after the first
        c = results["ESCALATE_CAPPED"]
        self.assertEqual(c.levels(), [None] + [True] * 6 + [None, None])                              # exactly 6 escalated requests, then off
        self.assertEqual(len(c.recorder.events("cap_reached")), 1)
        self.assertEqual(c.recorder.events("cap_reached")[0]["request"], 8)
        self.assertEqual(c.arm.escalated_sent, 6)

    def test_capped_arm_does_not_open_a_window_after_the_cap_and_logs_triggers_still(self):
        c = Fixture("ESCALATE_CAPPED")
        c.request()
        for _ in range(7):
            c.text = "no such node"; c.call("ros2_node_list", {}); c.request()
        self.assertEqual(c.levels()[-1], None)
        before = c.arm.remaining
        c.text = ""; c.call("ros2_node_list", {})                                            # a trigger after the cap
        self.assertEqual(c.arm.remaining, before)                                            # no new window
        self.assertEqual(c.recorder.events("call_class")[-1]["klass"], "empty")              # but it is logged
        self.assertEqual(c.request(), {})

    def test_capped_arm_uses_the_same_levels_and_identical_prompts(self):
        base, cap = Fixture("FULL"), Fixture("ESCALATE_CAPPED", model="gpt-oss:20b")
        self.assertEqual(base.arm.prompt_messages, cap.arm.prompt_messages)
        cap.request(); cap.text = "not found"; cap.call("ros2_node_list", {})
        self.assertEqual(cap.request(), {"reasoning": "high"})

    def test_cap_not_reached_when_fewer_than_six_requests_are_escalated(self):
        c = Fixture("ESCALATE_CAPPED")
        c.request(); c.text = "not found"; c.call("ros2_node_list", {})
        c.request(); c.request(); c.request()
        self.assertEqual(c.levels(), [None, True, True, None]); self.assertEqual(c.recorder.events("cap_reached"), [])

    def test_one_fire_per_request_even_with_two_triggers(self):
        f = Fixture("ESCALATE")
        f.request(); f.text = "not found"; f.call("ros2_node_list", {}); f.call("ros2_topic_list", {})
        self.assertEqual(len(f.recorder.events("trigger_fire")), 1); self.assertEqual(f.arm.fires, 1)

    def test_classify_result_cases(self):
        c = A.classify_result
        self.assertEqual(c({"/a/b": {"error": "Unable to find node '/a/b'\n"}}), "not_found")
        self.assertEqual(c({"error": ""}), "empty")
        self.assertEqual(c({}), "empty"); self.assertEqual(c(""), "empty"); self.assertEqual(c([]), "empty"); self.assertEqual(c(None), "empty")
        self.assertEqual(c({"nodes": []}), "empty"); self.assertEqual(c({"nodes": [], "x": ""}), "empty"); self.assertEqual(c({"nodes": [], "n": 3}), "ok")
        self.assertEqual(c({"nodes": ["/a"]}), "ok"); self.assertEqual(c("Node name: a"), "ok")

    def test_request_options_are_logged_by_the_traced_model_path(self):
        import inspect
        src = inspect.getsource(A.ThinkTracedModel._generate)
        self.assertIn("self.options = self.arm.request_options()", src)


if __name__ == "__main__":
    unittest.main()
