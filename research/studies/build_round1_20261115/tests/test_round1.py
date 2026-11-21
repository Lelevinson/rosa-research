"""Unit tests for answer_gate.py, list_args.py, round1_harness.py, score_round1.py (no ROS, no Ollama).

  uv run python -m unittest discover -s research/studies/build_round1_20261115/tests -v      (from the repository root)
"""
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import answer_gate as ag  # noqa: E402
import list_args  # noqa: E402
import round1_harness as r1  # noqa: E402
import score_round1  # noqa: E402
import harness  # noqa: E402
from rosa.tools import ros2  # noqa: E402

TASKS = {t["id"]: t for t in json.loads((ROOT / "research/studies/headroom_diagnostic_20261112/stage3_tasks.json").read_text())}
TASKS.update({t["id"]: t for t in json.loads((ROOT / "research/studies/small_model_harness_20261115/e1h_tasks.json").read_text())})
KEYS = {"v2": [{"node", "type"}], "u3": [{"publisher", "input_topic", "upstream"}], "h4": [{"node", "publishers", "gains"}],
        "p3": [{"first", "second", "setpoint"}], "e1h_chg_1": [{"first_level", "pump_setpoint", "final_level"}],
        "e1h_amb_1": [{"node", "limit"}], "e1h_amb_2": [{"node", "gain"}], "e1h_chg_2": [{"first_mode", "meter_flow", "final_mode"}],
        "e1h_abs_1": [{"node", "running", "limit"}, {"node", "running"}], "e1h_abs_2": [{"node", "running", "rate"}, {"node", "running"}]}


class FakeRecorder:
    def __init__(self):
        self.rows = []

    def add(self, kind, **values):
        self.rows.append(dict(kind=kind, **values))

    def events(self, name):
        return [r for r in self.rows if r.get("event") == name]


class GateTests(unittest.TestCase):
    TASK = "Find the node that provides /plant32/cedar_reset. Return JSON with keys node (the full node name) and type."
    OUT = [{"nodes": ["/plant32/wharf", "/e1h/ember/mistral"]}, "Node name: quill\nNode namespace: /plant32\n"]

    def check(self, answer, outputs=None, task=None):
        return ag.check_answer(answer, task or self.TASK, self.OUT if outputs is None else outputs)

    def test_exact_name_passes(self):
        self.assertFalse(self.check({"node": "/plant32/wharf", "type": "std_srvs/srv/Trigger"})["reject"])

    def test_name_in_task_text_passes_without_tool_result(self):
        self.assertFalse(self.check({"node": "/plant32/cedar_reset", "type": "x"})["reject"])

    def test_unique_suffix_gets_did_you_mean(self):
        v = self.check({"node": "/wharf", "type": "x"})
        self.assertTrue(v["reject"])
        self.assertIn("did you mean '/plant32/wharf'", v["problems"][0]["hint"])

    def test_bare_name_with_unique_suffix_rejected_but_plain_strings_pass(self):
        self.assertTrue(self.check({"node": "wharf", "type": "x"})["reject"])
        self.assertFalse(self.check({"node": "/plant32/wharf", "type": "fast"})["reject"])
        self.assertFalse(self.check({"node": "/plant32/wharf", "type": "std_srvs/srv/Trigger"})["reject"])

    def test_never_seen_name_rejected(self):
        v = self.check({"node": "/plant32/cedar", "type": "x"})
        self.assertEqual(v["problems"][0]["rule"], "never_seen")

    def test_node_name_from_topic_info_block_is_allowed(self):
        self.assertFalse(self.check({"node": "/plant32/quill", "type": "x"})["reject"])

    def test_failed_call_does_not_make_a_name_seen(self):
        outputs = [{"/plant32/ghost": {"error": "Unable to find node '/plant32/ghost'"}}, {"error": "Node not found /plant32/ghost2"}]
        self.assertTrue(self.check({"node": "/plant32/ghost", "type": "x"}, outputs)["reject"])
        self.assertTrue(self.check({"node": "/plant32/ghost2", "type": "x"}, outputs)["reject"])

    def test_successful_item_of_a_mixed_list_result_counts(self):
        outputs = [{"/a/x": "Node name: x\nNode namespace: /a\n", "/a/y": {"error": "no such"}}]
        self.assertFalse(self.check({"node": "/a/x", "type": "t"}, outputs)["reject"])
        self.assertTrue(self.check({"node": "/a/y", "type": "t"}, outputs)["reject"])

    def test_nested_keys_are_checked(self):
        task = "Return JSON with keys gains (an object mapping each publisher's full name to its gain)."
        outputs = [{"nodes": ["/p/zephyr"]}]
        self.assertFalse(ag.check_answer({"gains": {"/p/zephyr": 74}}, task, outputs)["reject"])
        self.assertTrue(ag.check_answer({"gains": {"zephyr": 74}}, task, outputs)["reject"])

    def test_missing_key_rejected_extra_key_not(self):
        self.assertTrue(self.check({"/plant32/cedar_reset": "x"})["reject"])
        self.assertFalse(self.check({"node": "/plant32/wharf", "type": "t", "extra": 1})["reject"])

    def test_numbers_are_logged_never_rejected(self):
        v = self.check({"node": "/plant32/wharf", "type": "t", "gain": 999})
        self.assertFalse(v["reject"])
        self.assertEqual(v["numbers_unseen"], [dict(path="gain", value=999)])
        self.assertEqual(self.check({"node": "/plant32/wharf", "type": "t", "gain": 74}, self.OUT + [{"gain": "Integer value is: 74"}])["numbers_unseen"], [])

    def test_key_rule_parses_every_pilot_task(self):
        for task_id, expected in KEYS.items():
            self.assertEqual(sorted(map(sorted, ag.parse_required_key_sets(TASKS[task_id]["request"]))), sorted(map(sorted, expected)), task_id)

    def test_key_rule_has_no_clause_without_keys_word(self):
        self.assertEqual(ag.parse_required_key_sets("Tell me which node is running."), [])


class ListArgumentTests(unittest.TestCase):
    TOOLS = [ros2.ros2_param_get, ros2.ros2_param_list, ros2.ros2_topic_echo, ros2.ros2_node_info, ros2.ros2_topic_info, ros2.ros2_service_info,
             ros2.ros2_node_list, ros2.ros2_topic_list, ros2.ros2_service_list, ros2.ros2_doctor, ros2.roslog_list]

    def test_rule_selects_exactly_the_documented_tools(self):
        chosen = list_args.applicable_tools(self.TOOLS, harness.DOMAIN_TOOLS)
        self.assertEqual(chosen, {"ros2_param_get": "node_name", "ros2_param_list": "node_name", "ros2_topic_echo": "topic"})

    def test_schema_and_description_change_only_for_the_argument(self):
        schema, description = list_args.with_list_schema(ros2.ros2_param_get, "node_name")
        properties = schema.model_json_schema()["properties"]
        self.assertIn("anyOf", properties["node_name"])
        self.assertEqual(properties["param_name"]["type"], "string")
        self.assertEqual(description.count(list_args.LIST_SENTENCE), 1)
        self.assertIn(":param param_name: The name of the parameter.", description)

    def test_strict_validator_accepts_both_forms_and_rejects_bad_items(self):
        schema, _ = list_args.with_list_schema(ros2.ros2_param_get, "node_name")
        from langchain_core.tools import StructuredTool
        from langchain_core.utils.function_calling import convert_to_openai_tool
        tool = StructuredTool(name="ros2_param_get", description="d", args_schema=schema, func=lambda **k: k)
        json_schema = convert_to_openai_tool(tool)["function"]["parameters"]
        self.assertIsNone(harness.strict_error("t", json_schema, {"node_name": "/a/b", "param_name": "gain"}))
        self.assertIsNone(harness.strict_error("t", json_schema, {"node_name": ["/a/b", "/c/d"], "param_name": "gain"}))
        self.assertIsNotNone(harness.strict_error("t", json_schema, {"node_name": [1, 2], "param_name": "gain"}))

    def test_wrapper_equals_single_calls_on_recorded_ros_output(self):
        """Replay real recorded `ros2 param get` results from pilot traces and compare a list call with the single calls."""
        recorded = {}
        for trace in (ROOT / "research/_artifacts/runs/small_model_harness_20261115/pilot").glob("*/*C1-*/trace.jsonl"):
            for line in trace.read_text().splitlines():
                e = json.loads(line)
                if e["kind"] == "ros_end" and e["command"][1:3] == ["param", "get"]:
                    recorded[" ".join(e["command"])] = (e["returncode"] == 0, e["stdout"] if e["returncode"] == 0 else e["stderr"])
        self.assertGreater(len(recorded), 10)
        commands = [c for c in recorded if recorded[c][0]][:3] + [c for c in recorded if not recorded[c][0]][:1]
        nodes_params = [tuple(c.split()[3:5]) for c in commands]
        original = ros2.execute_ros_command
        ros2.execute_ros_command = lambda command: recorded[command]
        try:
            for param in {p for _, p in nodes_params}:
                names = [n for n, p in nodes_params if p == param]
                single = {n: ros2.ros2_param_get.func(node_name=n, param_name=param) for n in names}
                combined, items = list_args.run_per_item(lambda a: ros2.ros2_param_get.func(**a), {"node_name": names + names[:1], "param_name": param}, "node_name")
                self.assertEqual(combined, single)
                self.assertEqual(items, names)  # duplicates dropped, order kept
        finally:
            ros2.execute_ros_command = original

    def test_limits(self):
        self.assertIsNone(list_args.list_problem("a"))
        self.assertIsNotNone(list_args.list_problem([]))
        self.assertIsNone(list_args.list_problem(["a"] * 20))
        self.assertIsNotNone(list_args.list_problem(["a"] * 21))

    def test_item_error_stays_in_its_item(self):
        def run_one(args):
            if args["node_name"] == "bad":
                raise ValueError("boom")
            return {"gain": "Integer value is: 1"}
        combined, _ = list_args.run_per_item(run_one, {"node_name": ["ok", "bad"], "param_name": "gain"}, "node_name")
        self.assertEqual(combined["ok"], {"gain": "Integer value is: 1"})
        self.assertIn("boom", combined["bad"]["error"])


class ArmTests(unittest.TestCase):
    def make(self, name, task_id="p3"):
        task = TASKS[task_id]
        return r1.Round1Arm(name, FakeRecorder(), dict(env="stage3", task=task, ns="plant32"), [("system", "x")])

    def test_arm_names_and_flags(self):
        for name, gate, lists in [("C1", False, False), ("C1+AG", True, False), ("C1+LA", False, True), ("C1+AG+LA", True, True)]:
            arm = self.make(name)
            self.assertEqual((arm.gate_on, arm.lists_on), (gate, lists))

    def test_gate_rejects_twice_then_accepts(self):
        arm = self.make("C1+AG", "v2")
        bad = {"answer": {"node": "/plant32/nowhere", "type": "t"}}
        from langchain_core.tools import ToolException
        for _ in range(2):
            with self.assertRaises(ToolException):
                arm.final_answer_tool(bad)
        arm.final_answer_tool(bad)
        self.assertTrue(arm.final_done)
        self.assertEqual(len(arm.recorder.events("gate_accepted_after_limit")), 1)

    def test_shadow_mode_never_rejects(self):
        arm = self.make("C1", "v2")
        arm.final_answer_tool({"answer": {"node": "/plant32/nowhere", "type": "t"}})
        self.assertTrue(arm.final_done)
        self.assertTrue(arm.recorder.events("gate_shadow")[0]["would_reject"])

    def test_followup_logged(self):
        arm = self.make("C1+AG", "v2")
        from langchain_core.tools import ToolException
        with self.assertRaises(ToolException):
            arm.final_answer_tool({"answer": {"node": "/plant32/nowhere", "type": "t"}})
        arm.tool_outputs.append({"nodes": ["/plant32/wharf"]})
        arm.final_answer_tool({"answer": {"node": "/plant32/wharf", "type": "t"}})
        self.assertTrue(arm.recorder.events("gate_followup")[0]["changed"])

    def test_nudge_only_for_gate_arms_and_only_without_tool_calls(self):
        from langchain_core.messages import AIMessage
        text, call = AIMessage(content="done"), AIMessage(content="", tool_calls=[dict(name="ros2_node_list", args={}, id="1")])
        self.assertTrue(self.make("C1+AG").wants_nudge(text))
        self.assertFalse(self.make("C1+AG").wants_nudge(call))
        self.assertFalse(self.make("C1").wants_nudge(text))
        arm = self.make("C1+AG")
        arm.nudges = 2
        self.assertFalse(arm.wants_nudge(text))

    def test_list_tool_end_to_end_with_scorer_expansion(self):
        """A list call executed through the arm is scored exactly like single calls (scorer v2.0 on expanded rows)."""
        task = TASKS["p3"]
        arm = self.make("C1+LA")
        arm.offered = {"ros2_param_get"}
        arm.wrap_tools(ros2_tools := [ros2.ros2_param_get])
        outputs = {"ros2 param get /plant32/quartz next_node": (True, "String value is: /plant32/a\n")}
        original = ros2.execute_ros_command
        ros2.execute_ros_command = lambda command: outputs.get(command, (False, "Node not found"))
        try:
            result = arm.execute(ros2_tools[0], {"node_name": ["/plant32/quartz", "/plant32/zzz"], "param_name": "next_node"})
        finally:
            ros2.execute_ros_command = original
        self.assertEqual(list(result), ["/plant32/quartz", "/plant32/zzz"])
        self.assertIn("error", result["/plant32/zzz"])
        self.assertEqual(len(arm.recorder.events("list_item")), 2)
        self.assertEqual(arm.recorder.events("list_call")[0]["items"], 2)


class ScorerAdapterTests(unittest.TestCase):
    def test_pilot_trace_scores_identically_without_list_calls(self):
        """On a recorded pilot episode (no list calls) the adapter equals scorer v2.0 itself."""
        import scorer_v2
        rows = [json.loads(l) for l in (ROOT / "research/studies/small_model_harness_20261115/RESULTS_LOG.jsonl").read_text().splitlines()]
        checked = 0
        for r in [x for x in rows if x["arm"] == "C1"][:25]:
            events = scorer_v2.s1.read_events(ROOT / r["trace_path"])
            task = TASKS[r["task"]]
            self.assertEqual(score_round1.score_events(task, events)["supported_complete"], scorer_v2.score_events(task, events)["supported_complete"])
            checked += 1
        self.assertEqual(checked, 25)


if __name__ == "__main__":
    unittest.main()
