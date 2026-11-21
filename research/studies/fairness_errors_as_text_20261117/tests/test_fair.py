"""Tests for the fairness arms (no ROS, no Ollama). From the repository root:
  uv run python -m unittest discover -s research/studies/fairness_errors_as_text_20261117/tests -v
"""
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import fair_arms  # noqa: E402
from langchain_core.tools import StructuredTool  # noqa: E402
from pydantic import BaseModel  # noqa: E402


class Recorder:
    def __init__(self):
        self.rows = []

    def add(self, kind, **values):
        self.rows.append(dict(kind=kind, **values))


class Args(BaseModel):
    count: int


def make_tool(function):
    return StructuredTool.from_function(func=function, name="probe", description="probe tool", args_schema=Args)


class ErrorsAsTextTests(unittest.TestCase):
    def test_stock_tool_raises_on_bad_arguments_and_on_exception(self):
        tool = make_tool(lambda count: 1 // count)
        with self.assertRaises(Exception):
            tool.run({"count": "not a number"})
        with self.assertRaises(Exception):
            tool.run({"count": 0})

    def test_arm_returns_both_failures_as_text_and_logs_them(self):
        recorder = Recorder()
        tool = fair_arms.make_returning_errors(make_tool(lambda count: 1 // count), recorder)
        invalid = tool.run({"count": "not a number"})
        raised = tool.run({"count": 0})
        self.assertIn("count", invalid)
        self.assertIn("ZeroDivisionError", raised)
        self.assertEqual(tool.run({"count": 1}), 1)  # success path unchanged
        self.assertEqual([r["error_kind"] for r in recorder.rows], ["validation", "tool_exception"])

    def test_schema_name_and_description_are_untouched(self):
        tool = make_tool(lambda count: count)
        before = (tool.name, tool.description, tool.args_schema.model_json_schema())
        fair_arms.make_returning_errors(tool, Recorder())
        self.assertEqual(before, (tool.name, tool.description, tool.args_schema.model_json_schema()))

    def test_prompts_are_the_pilot_prompts(self):
        import run_pilot
        for arm, pilot in fair_arms.ARMS.items():
            instance = fair_arms.make_arm(arm, Recorder(), None)
            self.assertEqual(instance.prompt_messages, run_pilot.prompt_for(pilot))
        self.assertNotEqual(fair_arms.make_arm("E0", Recorder(), None).prompt_messages, fair_arms.make_arm("E1", Recorder(), None).prompt_messages)


if __name__ == "__main__":
    unittest.main()
