"""Focused tests of the exam arms (no ROS, no Ollama). From the repository root:
  uv run python -m unittest discover -s research/studies/exam_arms_20261121/tests -v"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import exam_arms as X  # noqa: E402
from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: E402
from rosa.tools import ROSATools  # noqa: E402
import rosa.tools.ros2 as ros2  # noqa: E402

harness, ablation_arms, v2 = X.harness, X.ablation_arms, X.v2
TRACE = HERE / "nf_single_2_lfm3_trace.jsonl"  # saved dev episode (name_fix_applied_20261117, lfm3, nf_single_2): the rewrite turns an unsupported answer into a supported one
TASKS = {t["id"]: t for t in json.loads((X.STUDIES / "name_fix_applied_20261117/namefix_tasks.json").read_text())}


class Recorder:
    def __init__(self):
        self.rows = []

    def add(self, kind, **values):
        self.rows.append(dict(kind=kind, **values))

    def events(self, name):
        return [r for r in self.rows if r["kind"] == "handler" and r["event"] == name]


class Fixture:
    """One exam arm with the 47 stock tools; ROS commands are replaced so nothing reaches ROS."""
    def __init__(self, variant, request="Find the node."):
        self.recorder = Recorder()
        self.ros_calls = []
        ros2.execute_ros_command = lambda command, *a, **k: (self.ros_calls.append(command) or (True, "ok"))
        self.arm = X.make_arm(variant, self.recorder, dict(env="stage3", task=dict(id="u3", floor=None, request=request), ns="/plant32"))
        self.tools = {t.name: t for t in self.arm.wrap_tools(ROSATools(2, blacklist=[]).get_tools())}
        self.schemas = [convert_to_openai_tool(t) for t in self.tools.values()]

    def offered(self):
        return [s["function"]["name"] for s in self.arm.visible_schemas(self.schemas, [])]

    def call(self, name, args):
        self.arm.visible_schemas(self.schemas, [])
        return self.tools[name].run(args)


class PayloadTests(unittest.TestCase):
    def test_m_is_the_dev_full_arm_and_ablations_change_one_component(self):
        full = Fixture("M")
        dev = ablation_arms.AblationArm("FULL", Recorder(), dict(env="stage3", task=dict(id="u3", floor=None), ns="/plant32"), X.run_pilot.prompt_for("A1"))
        self.assertEqual(full.arm.prompt_messages, dev.prompt_messages)
        self.assertEqual(full.arm.name, "M")
        base = full.offered()
        self.assertEqual(len(base), 13)
        self.assertEqual(Fixture("NO_ERRORTEXT").offered(), base)  # the menu, prompt and schemas are those of M
        self.assertEqual(Fixture("NO_ERRORTEXT").arm.prompt_messages, full.arm.prompt_messages)
        self.assertEqual(len(Fixture("NO_MENU").offered()), 48)
        self.assertEqual(sorted(Fixture("NO_FINISH").offered()), sorted(harness.DOMAIN_TOOLS))


class NoErrortextTests(unittest.TestCase):
    def test_invalid_arguments_end_the_episode_and_there_is_no_precheck(self):
        arm = Fixture("NO_ERRORTEXT")
        with self.assertRaises(ablation_arms.HardToolError):
            arm.call("ros2_node_info", {"nodes": "abc"})
        self.assertEqual(len(arm.recorder.events("validation_error")), 0)  # the strict pre-check is off
        self.assertEqual(len(arm.recorder.events("episode_ended_by_error")), 1)
        self.assertEqual(arm.ros_calls, [])

    def test_pydantic_coercion_is_logged_and_the_coerced_call_runs(self):
        arm = Fixture("NO_ERRORTEXT")
        arm.call("ros2_topic_echo", {"topic": "/a", "count": "2"})
        self.assertEqual([(c["field"], c["given"], c["parsed"]) for c in arm.recorder.events("coercion")], [("count", "2", 2)])
        self.assertGreaterEqual(len(arm.ros_calls), 1)

    def test_tool_exception_ends_the_episode_but_m_returns_it_as_text(self):
        boom = lambda command, *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        hard = Fixture("NO_ERRORTEXT")
        ros2.execute_ros_command = boom  # set after the fixture: its constructor installs a recording stub
        with self.assertRaises(ablation_arms.HardToolError):
            hard.call("ros2_node_list", {})
        soft = Fixture("M")
        ros2.execute_ros_command = boom
        self.assertIn("boom", str(soft.call("ros2_node_list", {})))

    def test_m_still_rejects_with_text(self):
        arm = Fixture("M")
        self.assertTrue(arm.call("ros2_node_info", {"nodes": "abc"}).startswith("Invalid arguments for ros2_node_info"))

    def test_write_tools_are_still_blocked(self):
        arm = Fixture("NO_ERRORTEXT")
        with self.assertRaises(ablation_arms.HardToolError):  # a blocked write is an exception in the hard arm, as in dev NO_SOFT_ERRORS
            arm.call("ros2_param_set", {"node_name": "/a", "param_name": "gain", "param_value": "1"})
        self.assertEqual(arm.ros_calls, [])


class NameFixShadowTests(unittest.TestCase):
    def setUp(self):
        self.events = v2.s1.read_events(TRACE)
        self.start = next(e for e in self.events if e["kind"] == "episode_start")
        self.task = TASKS[self.start["task"]["id"]]

    def test_saved_trace_scores_differently_raw_and_rewritten(self):
        both = X.score_both(self.task, self.events)
        self.assertTrue(both["rewritten"]["supported_complete"])
        self.assertFalse(both["raw"]["supported_complete"])
        original = [e for e in self.events if e["kind"] == "final_answer_original"][-1]["answer"]
        self.assertEqual(both["raw"]["answer_object"], original)
        self.assertNotEqual(both["rewritten"]["answer_object"], original)

    def test_without_an_original_both_scores_are_the_same(self):
        events = [e for e in self.events if e["kind"] != "final_answer_original"]
        both = X.score_both(self.task, events)
        self.assertEqual(both["raw"], both["rewritten"])

    def test_arm_logs_the_raw_answer_before_the_rewrite_and_records_the_rewritten_one(self):
        rows = v2.tool_rows(self.events)
        raw = [e for e in self.events if e["kind"] == "final_answer_original"][-1]["answer"]
        arm = Fixture("M", request=self.task["request"]).arm
        arm.tool_outputs = [r["output"] for r in rows]
        arm.final_answer_tool({"answer": raw})
        original = [r for r in arm.recorder.rows if r["kind"] == "final_answer_original"]
        accepted = [r for r in arm.recorder.rows if r["kind"] == "final_answer_accepted"]
        self.assertEqual(original[0]["answer"], raw)
        self.assertNotEqual(accepted[0]["answer"], raw)
        self.assertTrue(arm.recorder.events("namefix")[0]["changed"])
        self.assertLess(arm.recorder.rows.index(original[0]), arm.recorder.rows.index(accepted[0]))  # raw logged first


class MetaToolPortTests(unittest.TestCase):
    def setUp(self):
        self.recorder = Recorder()
        self.arm = X.make_arm("MT", self.recorder, dict(env="stage3", task=dict(id="u3", floor=None, request="x"), ns="/plant32"))
        self.tools = self.arm.wrap_tools(ROSATools(2, blacklist=[]).get_tools())

    def test_is_the_stock_arm_plus_one_line_and_one_tool(self):
        stock = X.run_pilot.StockArm("S0", Recorder())
        self.assertEqual(self.arm.prompt_messages, stock.prompt_messages + [X.MT_LINE])
        self.assertEqual(X.MT_LINE[1], "Always use supertool() to think and generate a plan for the sequence of tool execution, then use that plan to execute the tools in proper order.")
        names = [t.name for t in self.tools]
        self.assertEqual(len(names), 48)
        self.assertEqual(names[-1], "supertool")
        self.assertEqual(names[:-1], [t.name for t in ROSATools(2, blacklist=[]).get_tools()])  # the 47 stock tools, unchanged and in order
        self.assertEqual(self.arm.visible_schemas([1, 2], []), [1, 2])  # no per-request menu change
        self.assertEqual(self.arm.name, "MT")

    def test_supertool_echoes_its_plan_unchanged_and_is_counted(self):
        tool = self.tools[-1]
        plan = "1. ros2_node_list\n2. ros2_node_info for each node"
        self.assertEqual(tool.run({"input_str": "task", "generated_instruction_sequence": plan}), plan)
        self.assertEqual(self.arm.supertool_calls, 1)
        self.assertEqual(self.recorder.events("supertool_call")[0]["plan_chars"], len(plan))

    def test_stock_executor_is_used(self):
        self.assertIs(type(self.arm).make_executor, X.run_pilot.StockArm.make_executor)  # the stock AgentExecutor with handle_parsing_errors, as arm S0
        self.assertIs(type(self.arm).__mro__[1], X.run_pilot.StockArm)


if __name__ == "__main__":
    unittest.main()
