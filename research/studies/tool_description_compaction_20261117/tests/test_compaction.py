"""Frozen tests of the compaction rule and arms (no ROS, no Ollama). From the repository root:
  uv run python -m unittest discover -s research/studies/tool_description_compaction_20261117/tests -v"""
import copy
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "steady_loop_ablation_20261117"))
import compaction  # noqa: E402
import compaction_arm  # noqa: E402
from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: E402
from rosa.tools import ROSATools  # noqa: E402
import rosa.tools.ros2 as ros2  # noqa: E402

harness = compaction_arm.ablation_arms.harness
CONTEXT = dict(env="stage3", task=dict(id="u3", floor=None), ns="/plant32")


class Recorder:
    def __init__(self):
        self.rows = []

    def add(self, kind, **values):
        self.rows.append(dict(kind=kind, **values))


class RuleTests(unittest.TestCase):
    def test_first_sentence_rules(self):
        fs = compaction.first_sentence
        self.assertEqual(fs("Get a list.  More text here.", 160), "Get a list.")
        self.assertEqual(fs("Only show lines with this level (e.g. ERROR, INFO). Second.", 160), "Only show lines with this level (e.g. ERROR, INFO).")
        self.assertEqual(fs("no end punctuation here", 160), "no end punctuation here")
        self.assertEqual(fs("one two three four five six", 12), "one two")  # cut at the last space within the cap
        self.assertEqual(fs("abcdefghijklmnop", 5), "abcde")
        self.assertEqual(fs("Is it? Yes.", 160), "Is it?")
        self.assertEqual(fs("", 160), "")

    def test_split_and_arguments(self):
        text = "Does a thing. More about it.\n\n:param a: First arg.\n  continues here. Second sentence.\n:param b: Second arg\n:return: something\n:note: ignored\n"
        out = compaction.compact_description(text, ["a", "b", "c"])
        self.assertEqual(out, "Does a thing.\na: First arg.\nb: Second arg")  # c has no field: no line; return/note dropped
        self.assertEqual(compaction.compact_description("Only a head sentence. And more.", ["x"]), "Only a head sentence.")
        self.assertEqual(compaction.compact_description(":param x: text here.", ["x"]), "x: text here.")  # empty head
        self.assertEqual(compaction.compact_description(":arg xy: A list (e.g. [(1, 2)]). Rest.", ["xy"]), "xy: A list (e.g. [(1, 2)]).")
        self.assertEqual(compaction.compact_description("Head.\n:param int n: typed.", ["n"]), "Head.\nn: typed.")  # a type word before the name is allowed

    def test_deterministic_and_does_not_mutate(self):
        schema = {"type": "function", "function": {"name": "t", "description": "Head. Tail.\n:param a: x.", "parameters": {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}}}
        before = copy.deepcopy(schema)
        first, second = compaction.compact_schema(schema), compaction.compact_schema(schema)
        self.assertEqual(first, second)
        self.assertEqual(schema, before)
        self.assertEqual(first["function"]["parameters"], schema["function"]["parameters"])


class RealToolTests(unittest.TestCase):
    def test_all_47_tools_keep_name_and_parameters_and_get_shorter_descriptions(self):
        tools = [convert_to_openai_tool(t) for t in ROSATools(2, blacklist=[]).get_tools()]
        self.assertEqual(len(tools), 47)
        shorter = 0
        for s in tools:
            c = compaction.compact_schema(s)
            self.assertEqual((c["function"]["name"], c["function"]["parameters"]), (s["function"]["name"], s["function"]["parameters"]))
            self.assertLessEqual(len(c["function"]["description"]), len(s["function"]["description"]), s["function"]["name"])
            self.assertTrue(c["function"]["description"], s["function"]["name"])  # no tool is left without a description
            for line in c["function"]["description"].split("\n")[1:]:
                self.assertIn(line.split(":")[0], s["function"]["parameters"]["properties"], s["function"]["name"])
            shorter += len(c["function"]["description"]) < len(s["function"]["description"])
        self.assertGreater(shorter, 20)

    def test_domain_tool_totals_are_the_frozen_numbers(self):
        by = {t.name: convert_to_openai_tool(t) for t in ROSATools(2, blacklist=[]).get_tools()}
        before = sum(len(by[n]["function"]["description"]) for n in harness.DOMAIN_TOOLS)
        after = sum(len(compaction.compact_schema(by[n])["function"]["description"]) for n in harness.DOMAIN_TOOLS)
        self.assertEqual((before, after), (2056, 1601))


class ArmTests(unittest.TestCase):
    def fixture(self, name):
        recorder = Recorder()
        ros2.execute_ros_command = lambda command, *a, **k: (True, "ok")
        arm = compaction_arm.make_arm(name, recorder, CONTEXT)
        tools = {t.name: t for t in arm.wrap_tools(ROSATools(2, blacklist=[]).get_tools())}
        return arm, tools, [convert_to_openai_tool(t) for t in tools.values()], recorder

    def test_only_the_descriptions_differ(self):
        full, ftools, fschemas, _ = self.fixture("FULL")
        comp, ctools, cschemas, recorder = self.fixture("COMPACT")
        self.assertEqual(full.prompt_messages, comp.prompt_messages)
        a, b = full.visible_schemas(fschemas, []), comp.visible_schemas(cschemas, [])
        self.assertEqual([s["function"]["name"] for s in a], [s["function"]["name"] for s in b])
        self.assertEqual(len(a), 13)
        for x, y in zip(a, b):
            self.assertEqual(x["function"]["parameters"], y["function"]["parameters"])
            self.assertEqual(x["type"], y["type"])
        self.assertLess(sum(len(s["function"]["description"]) for s in b), sum(len(s["function"]["description"]) for s in a))
        self.assertTrue(next(r for r in recorder.rows if r.get("event") == "description_chars")["parameters_identical"])
        # the stored (uncompacted) tool objects and the pre-check schemas are the originals
        self.assertEqual(comp.schemas, full.schemas)

    def test_execution_and_errors_are_identical(self):
        results = []
        for name in ("FULL", "COMPACT"):
            arm, tools, schemas, _ = self.fixture(name)
            arm.visible_schemas(schemas, [])
            results.append((tools["ros2_node_info"].run({"nodes": "abc"}), tools["ros2_param_get"].run({"node_name": "/a", "param_name": "g"})))
        self.assertEqual(results[0], results[1])


if __name__ == "__main__":
    unittest.main()
