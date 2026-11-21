"""Focused fixtures for the steady-loop ablation arms (no ROS, no Ollama). From the repository root:
  uv run python -m unittest discover -s research/studies/steady_loop_ablation_20261117/tests -v
Checks (protocol 'before inference verify...'): serialized prompts and offered schemas, safe-block behaviour, exception / validation paths, final-answer extraction,
payload equality outside the intended change."""
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import ablation_arms as A  # noqa: E402
from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: E402
from rosa.tools import ROSATools  # noqa: E402
import rosa.tools.ros2 as ros2  # noqa: E402

harness = A.harness
CONTEXT = dict(env="stage3", task=dict(id="u3", floor=None), ns="/plant32")


class Recorder:
    def __init__(self):
        self.rows = []

    def add(self, kind, **values):
        self.rows.append(dict(kind=kind, **values))

    def events(self, name):
        return [r for r in self.rows if r["kind"] == "handler" and r["event"] == name]


class Fixture:
    """One arm with the real 47 stock tools; ROS commands are replaced by a recorder so nothing reaches ROS."""
    def __init__(self, variant):
        self.recorder = Recorder()
        self.ros_calls = []
        ros2.execute_ros_command = lambda command, *a, **k: (self.ros_calls.append(command) or (True, "ok"))
        self.arm = A.make_arm(variant, self.recorder, CONTEXT)
        self.tools = {t.name: t for t in self.arm.wrap_tools(ROSATools(2, blacklist=[]).get_tools())}
        self.schemas = [convert_to_openai_tool(t) for t in self.tools.values()]

    def offered(self):
        return [s["function"]["name"] for s in self.arm.visible_schemas(self.schemas, [])]

    def call(self, name, args):
        self.arm.visible_schemas(self.schemas, [])  # the request that offered the tools
        return self.tools[name].run(args)


class PayloadTests(unittest.TestCase):
    def test_prompt_and_offered_schemas_outside_the_intended_change(self):
        full = Fixture("FULL")
        base_offered = full.offered()
        self.assertEqual(len(base_offered), 13)
        self.assertEqual(base_offered[-1], "final_answer")
        base_schemas = {s["function"]["name"]: s for s in full.arm.visible_schemas(full.schemas, [])}
        for variant in ("NO_SOFT_ERRORS", "NO_PRECHECK"):
            f = Fixture(variant)
            self.assertEqual(f.arm.prompt_messages, full.arm.prompt_messages, variant)
            self.assertEqual(f.offered(), base_offered, variant)
            self.assertEqual({s["function"]["name"]: s for s in f.arm.visible_schemas(f.schemas, [])}, base_schemas, variant)
        menu = Fixture("NO_MENU")
        self.assertEqual(menu.arm.prompt_messages, full.arm.prompt_messages)
        names = menu.offered()
        self.assertEqual(len(names), 48)
        self.assertEqual(len(set(names)), 48)
        self.assertIn("final_answer", names)
        self.assertTrue(set(base_offered) <= set(names))
        self.assertTrue({"ros2_param_set", "ros2_service_call", "add"} <= set(names))  # the write tools are advertised in this arm
        offered_schemas = {s["function"]["name"]: s for s in menu.arm.visible_schemas(menu.schemas, [])}
        for name in base_offered:
            self.assertEqual(offered_schemas[name], base_schemas[name], name)  # same schema and description for the 13 tools of C1
        finish = Fixture("NO_FINISH")
        self.assertEqual(finish.arm.prompt_messages, full.arm.prompt_messages[:-1])  # only the final_answer line is gone
        self.assertEqual(full.arm.prompt_messages[-1], harness.FINAL_ANSWER_LINE)
        self.assertEqual(sorted(finish.offered()), sorted(harness.DOMAIN_TOOLS))
        finish_schemas = {s["function"]["name"]: s for s in finish.arm.visible_schemas(finish.schemas, [])}
        for name in harness.DOMAIN_TOOLS:
            self.assertEqual(finish_schemas[name], base_schemas[name], name)


class ErrorPathTests(unittest.TestCase):
    def test_invalid_arguments(self):
        full = Fixture("FULL")
        text = full.call("ros2_node_info", {"nodes": "abc"})
        self.assertTrue(text.startswith("Invalid arguments for ros2_node_info"), text)  # strict pre-check message, returned
        self.assertEqual(len(full.recorder.events("validation_error")), 1)
        self.assertEqual(full.ros_calls, [])
        stock = Fixture("NO_PRECHECK")
        text = stock.call("ros2_node_info", {"nodes": "abc"})
        self.assertTrue(text.startswith("Invalid arguments: field 'nodes'"), text)  # stock pydantic text, still returned
        self.assertEqual(len(stock.recorder.events("stock_validation_error")), 1)
        self.assertEqual(len(stock.recorder.events("validation_error")), 0)  # no pre-check
        hard = Fixture("NO_SOFT_ERRORS")
        with self.assertRaises(A.HardToolError):
            hard.call("ros2_node_info", {"nodes": "abc"})
        self.assertEqual(len(hard.recorder.events("episode_ended_by_error")), 1)

    def test_coercion_is_logged_without_precheck_and_rejected_with_it(self):
        full = Fixture("FULL")
        text = full.call("ros2_topic_echo", {"topic": "/a", "count": "2"})
        self.assertIn("expected integer, received string", text)
        self.assertEqual(full.ros_calls, [])
        stock = Fixture("NO_PRECHECK")
        stock.call("ros2_topic_echo", {"topic": "/a", "count": "2"})
        coercions = stock.recorder.events("coercion")
        self.assertEqual([(c["field"], c["given"], c["parsed"]) for c in coercions], [("count", "2", 2)])
        self.assertGreaterEqual(len(stock.ros_calls), 1)  # the coerced call really ran

    def test_tool_exception_is_returned_or_ends_the_episode(self):
        for variant, ends in (("FULL", False), ("NO_PRECHECK", False), ("NO_MENU", False), ("NO_SOFT_ERRORS", True)):
            f = Fixture(variant)
            ros2.execute_ros_command = lambda command, *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
            if ends:
                with self.assertRaises(A.HardToolError):
                    f.call("ros2_node_list", {})
            else:
                text = f.call("ros2_node_list", {})
                self.assertIn("boom", str(text), variant)
                self.assertEqual(len(f.recorder.events("tool_exception")), 1, variant)

    def test_non_exception_failures_stay_untouched_in_the_hard_arm(self):
        f = Fixture("NO_SOFT_ERRORS")
        ros2.execute_ros_command = lambda command, *a, **k: (False, "Unable to find node")
        result = f.call("ros2_node_info", {"nodes": ["/x"]})  # a textual / dict failure is not an exception: the episode goes on
        self.assertIn("/x", json.dumps(result))


class SafetyTests(unittest.TestCase):
    def test_write_tools_never_run(self):
        for variant in ("FULL", "NO_MENU", "NO_PRECHECK", "NO_FINISH"):
            f = Fixture(variant)
            args = {"node_name": "/a", "param_name": "gain", "param_value": "1"}
            text = f.call("ros2_param_set", args)
            self.assertIn("not available", str(text), variant)
            self.assertEqual(len(f.recorder.events("blocked_write_tool")), 1, variant)
            self.assertEqual(f.ros_calls, [], variant)
        hard = Fixture("NO_SOFT_ERRORS")
        with self.assertRaises(A.HardToolError):
            hard.call("ros2_service_call", {"service_name": "/s", "srv_type": "t", "request": "{}"})
        self.assertEqual(hard.ros_calls, [])

    def test_tool_outside_the_menu_is_refused_in_c1_and_runs_in_the_wide_menu(self):
        full = Fixture("FULL")
        self.assertIn("not available at this step", str(full.call("sqrt", {"x_values": [4]})))
        wide = Fixture("NO_MENU")
        self.assertIn("2.0", str(wide.call("sqrt", {"x_values": [4]})))  # a read-only calculation tool is allowed when advertised


class FinishTests(unittest.TestCase):
    def test_final_answer_and_its_retry_behave_as_in_c1_in_every_arm_that_offers_it(self):
        for variant in ("FULL", "NO_SOFT_ERRORS", "NO_PRECHECK", "NO_MENU"):
            f = Fixture(variant)
            first = f.call("final_answer", {"answer": {}})  # empty object: C1's one retry message, returned even in the hard arm
            self.assertTrue(str(first).startswith("final_answer needs"), (variant, first))
            self.assertFalse(f.arm.final_done)
            f.call("final_answer", {"answer": {"node": "/a"}})
            self.assertTrue(f.arm.final_done, variant)
            self.assertEqual(f.arm.final_answer, {"node": "/a"})

    def test_no_finish_arm_cannot_call_final_answer_and_free_text_is_scored_by_v2(self):
        f = Fixture("NO_FINISH")
        self.assertNotIn("final_answer", f.offered())
        self.assertIn("not available at this step", str(f.call("final_answer", {"answer": {"node": "/a"}})))
        self.assertFalse(f.arm.final_done)
        import scorer_v2 as v2
        events = [dict(kind="episode_end", answer='The node is /a.\n```json\n{"node": "/plant32/anvil", "type": "std_msgs/msg/String"}\n```', error=None)]
        answer, source = v2.episode_answer(events)
        self.assertEqual((answer, source), ({"node": "/plant32/anvil", "type": "std_msgs/msg/String"}, "free_text"))
        wrapped = [dict(kind="episode_end", answer='{"answer": {"node": "/a"}}', error=None)]
        self.assertEqual(v2.episode_answer(wrapped)[0], {"node": "/a"})  # frozen v2 unwrap rule


class PlanTests(unittest.TestCase):
    def test_plan_is_forty_cells_per_arm_five_arms_and_shuffled_per_session(self):
        import run_ablation as R
        plan = R.plan_for("full")
        self.assertEqual(sum(map(len, plan.values())), 200)
        cells = [c for v in plan.values() for c in v]
        for arm in A.ARMS:
            self.assertEqual(sum(c["arm"] == arm for c in cells), 40)
        self.assertEqual({c["seed"] for c in cells}, {1})
        self.assertEqual(R.plan_for("full"), plan)  # deterministic
        self.assertEqual(sum(map(len, R.plan_for("smoke").values())), 5)


if __name__ == "__main__":
    unittest.main()
