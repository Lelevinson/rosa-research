"""Focused fixtures for the finish-tool split arms (no ROS, no Ollama). From the repository root:
  uv run python -m unittest discover -s research/studies/finish_split_20261118/tests -v
Checks: serialized prompts, offered tools and schemas differ from FULL only as the protocol says; final_answer behaves as in C1 where offered; the plan."""
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import split_arms as A  # noqa: E402
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


class Fixture:
    def __init__(self, variant):
        self.recorder = Recorder()
        ros2.execute_ros_command = lambda command, *a, **k: (True, "ok")
        self.arm = A.make_arm(variant, self.recorder, CONTEXT)
        self.tools = {t.name: t for t in self.arm.wrap_tools(ROSATools(2, blacklist=[]).get_tools())}
        self.schemas = [convert_to_openai_tool(t) for t in self.tools.values()]

    def offered(self):
        return [s["function"]["name"] for s in self.arm.visible_schemas(self.schemas, [])]

    def offered_schemas(self):
        return {s["function"]["name"]: s for s in self.arm.visible_schemas(self.schemas, [])}

    def call(self, name, args):
        self.arm.visible_schemas(self.schemas, [])
        return self.tools[name].run(args)


class ArmTests(unittest.TestCase):
    def test_prompts_and_tools_differ_from_full_only_as_the_protocol_says(self):
        full, tool_only, line_json = Fixture("FULL"), Fixture("TOOL_ONLY"), Fixture("LINE_JSON")
        self.assertEqual(full.arm.prompt_messages[-1], harness.FINAL_ANSWER_LINE)
        base = full.arm.prompt_messages[:-1]
        self.assertEqual(tool_only.arm.prompt_messages, base)
        self.assertEqual(line_json.arm.prompt_messages, base + [A.JSON_ONLY_LINE])
        for messages in (tool_only.arm.prompt_messages, line_json.arm.prompt_messages):
            self.assertNotIn("final_answer", " ".join(m[1] for m in messages))
        self.assertEqual(len(full.offered()), 13)
        self.assertEqual(tool_only.offered(), full.offered())
        self.assertEqual(tool_only.offered_schemas(), full.offered_schemas())  # same schema and description for the finish tool
        self.assertNotIn("final_answer", line_json.offered())
        self.assertEqual(sorted(line_json.offered()), sorted(harness.DOMAIN_TOOLS))
        full_schemas, line_schemas = full.offered_schemas(), line_json.offered_schemas()
        for name in harness.DOMAIN_TOOLS:
            self.assertEqual(line_schemas[name], full_schemas[name], name)

    def test_frozen_line_text(self):
        self.assertEqual(A.JSON_ONLY_LINE, ("system", "When you have the answer, reply with the answer as a JSON object only, using exactly the keys the task asks for. Do not write anything else."))

    def test_final_answer_and_its_retry_as_in_c1_where_offered(self):
        for variant in ("FULL", "TOOL_ONLY"):
            f = Fixture(variant)
            self.assertTrue(str(f.call("final_answer", {"answer": {}})).startswith("final_answer needs"), variant)
            self.assertFalse(f.arm.final_done)
            f.call("final_answer", {"answer": {"node": "/a"}})
            self.assertTrue(f.arm.final_done, variant)
            self.assertEqual(f.arm.final_answer, {"node": "/a"})

    def test_line_json_cannot_call_final_answer(self):
        f = Fixture("LINE_JSON")
        self.assertIn("not available at this step", str(f.call("final_answer", {"answer": {"node": "/a"}})))
        self.assertFalse(f.arm.final_done)


class PlanTests(unittest.TestCase):
    def test_plan_is_240_cells_80_per_arm_two_seeds_deterministic(self):
        import run_split as R
        plan = R.plan_for("full")
        cells = [c for v in plan.values() for c in v]
        self.assertEqual(len(cells), 240)
        for arm in A.ARMS:
            self.assertEqual(sum(c["arm"] == arm for c in cells), 80)
        self.assertEqual({c["seed"] for c in cells}, {1, 2})
        self.assertEqual(len({(c["model"], c["task"], c["seed"], c["arm"]) for c in cells}), 240)
        self.assertEqual(R.plan_for("full"), plan)
        smoke = [c for v in R.plan_for("smoke").values() for c in v]
        self.assertEqual(sorted((c["model"], c["task"], c["seed"], c["arm"]) for c in smoke), sorted(("qwen3.5:9b", "u3", 1, a) for a in A.ARMS))


if __name__ == "__main__":
    unittest.main()
