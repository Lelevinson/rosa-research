"""Tests of the Stage 2 wiring (no ROS node is started, no model): fake robot + the real executor. From the repository root:
  uv run python -m unittest discover -s research/studies/exam_actions_20261121/tests -v"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import action_arms as A  # noqa: E402
import action_trace  # noqa: E402
import judge_exam  # noqa: E402
import run_actions as R  # noqa: E402
from action_executor import ActionExecutor  # noqa: E402
from action_interface import ExecutorOptions  # noqa: E402
from fake_backend import FakeBackend, FakeClock  # noqa: E402
from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: E402
from rosa.tools import ROSATools  # noqa: E402
from turtlesim_backend import TURTLESIM_POLICY  # noqa: E402


class Recorder:
    def __init__(self):
        self.rows = []

    def add(self, kind, **values):
        self.rows.append(dict(kind=kind, **values))

    def of(self, kind):
        return [r for r in self.rows if r["kind"] == kind]


def make_kit():
    clock = FakeClock()
    backend = FakeBackend(clock)
    backend.observe_state = lambda: "pose: x=5.54 y=5.54 theta=0.0"
    executor = ActionExecutor(TURTLESIM_POLICY, backend, clock, ExecutorOptions(attach_post_action_state=False))
    executor.begin_episode()
    recorder = Recorder()
    return A.ActionToolKit(TURTLESIM_POLICY, executor, backend, recorder), executor, recorder


CONTEXT = dict(env="turtlesim", task=dict(id="S1", floor=None, request="Turn the turtle."), ns="/")


class SameToolTests(unittest.TestCase):
    def systems(self):
        built = {}
        for system in A.SYSTEMS:
            kit, executor, recorder = make_kit()
            arm = A.make_arm(system, recorder, CONTEXT, kit)
            built[system] = (arm, arm.wrap_tools(ROSATools(2, blacklist=[]).get_tools()), kit, recorder)
        return built

    def test_every_system_gets_the_identical_typed_tool_and_pose_tool(self):
        schemas = {}
        for system, (arm, tools, kit, recorder) in self.systems().items():
            by_name = {t.name: t for t in tools}
            self.assertIn(A.ACTION_TOOL, by_name, system)
            self.assertIn(A.POSE_TOOL, by_name, system)
            schemas[system] = (convert_to_openai_tool(by_name[A.ACTION_TOOL]), convert_to_openai_tool(by_name[A.POSE_TOOL]))
        self.assertEqual(schemas["XM"], schemas["XS0"])
        self.assertEqual(schemas["XM"], schemas["XE1"])
        function = schemas["XM"][0]["function"]
        self.assertEqual(function["description"], TURTLESIM_POLICY.actions[A.ACTION_TOOL].description)
        self.assertIn("-3.14", function["parameters"]["properties"]["theta"]["description"])
        self.assertEqual(function["parameters"]["properties"]["theta"]["type"], "number")  # as the dev study's tool_schema: the model sees a number, not an untyped field

    def test_policy_and_options_are_the_same_object_for_all_systems(self):
        kits = [make_kit()[0] for _ in A.SYSTEMS]
        self.assertTrue(all(k.policy is TURTLESIM_POLICY for k in kits))
        self.assertEqual((TURTLESIM_POLICY.goal_budget, TURTLESIM_POLICY.acknowledgement_seconds, TURTLESIM_POLICY.execution_seconds, TURTLESIM_POLICY.cancel_settlement_seconds), (3, 2.0, 15.0, 3.0))

    def test_menus_differ_only_in_the_systems_own_loop(self):
        built = self.systems()
        m_arm = built["XM"][0]
        self.assertTrue({A.ACTION_TOOL, A.POSE_TOOL, "final_answer"} <= set(m_arm.base_menu()))
        self.assertEqual(len(m_arm.base_menu()), 12 + 1 + 2)  # the 12 read tools, the finish tool, the two action-side tools
        self.assertEqual(len(built["XS0"][1]), 47 + 2)         # the 47 stock tools + two
        self.assertEqual(len(built["XE1"][1]), 47 + 2)
        self.assertEqual(built["XS0"][0].name, "XS0")
        self.assertEqual(built["XE1"][0].name, "XE1")

    def test_a_call_runs_the_executor_and_is_captured(self):
        kit, executor, recorder = make_kit()
        text = kit._rotate(1.0)
        self.assertTrue(text.startswith("SUCCEEDED"), text)
        call = recorder.of("action_call")[0]
        self.assertEqual((call["tool"], call["arguments"], call["result"]), (A.ACTION_TOOL, {"theta": 1.0}, "SUCCEEDED"))
        self.assertIsNotNone(call["goal_id"])
        self.assertEqual(executor.goals_sent, 1)
        self.assertTrue(kit._rotate(99.0).startswith("REJECTED"))  # out of range: the executor's own check, returned as text, no goal
        self.assertEqual(executor.goals_sent, 1)
        self.assertIn("theta", kit._pose())
        self.assertEqual(kit.reads_after_goal, 1)

    def test_goal_budget_is_the_same_for_every_system(self):
        kit, executor, recorder = make_kit()
        results = [kit._rotate(0.1 * i).split()[0] for i in range(1, 5)]
        self.assertEqual(results, ["SUCCEEDED"] * 3 + ["REJECTED"])  # budget 3


class JudgeWiringTests(unittest.TestCase):
    def test_event_capture_feeds_judge_v12_and_form_normalisation(self):
        kit, executor, recorder = make_kit()
        recorder.add("model_end", message=dict(content="", tool_calls=[{"name": "rotate_to_heading"}]))
        recorder.add("tool_start", name=A.ACTION_TOOL, input="{'theta': 1.0}", run_id="r1")
        text = kit._rotate(1.0)
        recorder.add("tool_end", output=text, run_id="r1")
        recorder.add("model_end", message=dict(content="done", tool_calls=[]))
        trace = action_trace.dev_trace(recorder.rows, executor.events)
        for form in ({"heading": 1.0}, {"answer": {"heading": 1.0}}, json.dumps({"heading": 1.0}), "Done. " + json.dumps({"answer": {"heading": 1.0}})):
            verdict = judge_exam.judge("S1", form, 1.0, 5.5, 5.5, True, ending="final_answer", trace=trace)
            self.assertTrue(verdict["success"], (form, verdict))
        wrong = judge_exam.judge("S1", {"heading": 1.0}, 0.2, 5.5, 5.5, True, ending="final_answer", trace=trace)  # the true heading is not the target
        self.assertFalse(wrong["success"])

    def test_parameter_read_of_a_stock_tool_is_mapped_for_the_read_before_dispatch_rule(self):
        # the stock tool's real argument name is param_name and its result a dict {param: "Integer value is: N\n"} (seen in the 2026-11-21 smoke)
        events = [dict(kind="tool_start", name="ros2_param_get", input="{'node_name': '/turtlesim', 'param_name': 'background_r'}", run_id="a"),
                  dict(kind="tool_end", output={"background_r": "Integer value is: 69\n"}, run_id="a")]
        trace = action_trace.dev_trace(events, [])
        self.assertEqual(trace[0]["name"], "get_parameter")
        self.assertEqual(trace[0]["content"], "Integer value is: 69")
        self.assertEqual(trace[0]["arguments"], {"node_name": "/turtlesim", "parameter_name": "background_r"})

    def test_read_then_act_episode_scores_with_the_mapped_read(self):
        kit, executor, recorder = make_kit()
        recorder.add("model_end", message=dict(content="", tool_calls=[]))
        recorder.add("tool_start", name="ros2_param_get", input="{'node_name': '/turtlesim', 'param_name': 'background_r'}", run_id="r0")
        recorder.add("tool_end", output={"background_r": "Integer value is: 69\n"}, run_id="r0")
        recorder.add("model_end", message=dict(content="", tool_calls=[]))
        recorder.add("tool_start", name=A.ACTION_TOOL, input="{'theta': 0.69}", run_id="r1")
        recorder.add("tool_end", output=kit._rotate(0.69), run_id="r1")
        trace = action_trace.dev_trace(recorder.rows, executor.events)
        verdict = judge_exam.judge("R1", {"background_r": 69, "heading": 0.69}, 0.69, 5.5, 5.5, True, ending="final_answer", trace=trace)
        self.assertTrue(verdict["success"], verdict)


class QueueWiringTests(unittest.TestCase):
    def test_launcher_registers_the_systems_without_editing_the_queue(self):
        import run_actions_queue  # noqa: F401
        import systems
        for system in ("XM", "XS0", "XE1"):
            self.assertIn(system, systems.SYSTEMS)
            self.assertEqual(systems.arm_of(system), system)
        source = Path(systems.__file__).read_text()
        self.assertNotIn("XM", source)  # systems.py itself is untouched

    def test_stub_environment_has_what_the_session_needs_and_the_dev_task_bank(self):
        env = R.load_env("turtlesim")
        self.assertEqual((env.commands(), env.GRAPH["nodes"]), ([], []))
        self.assertEqual(env.oracle(Path("."), None), [])
        self.assertEqual({t["id"] for t in env.TASKS}, {"S1", "S2", "S3", "R1", "R2", "M1", "M2", "M3"})


if __name__ == "__main__":
    unittest.main()
