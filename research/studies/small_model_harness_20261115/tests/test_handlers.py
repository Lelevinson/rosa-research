"""Unit tests for harness.py on synthetic tool histories (no ROS, no Ollama).

  uv run python -m unittest discover -s research/studies/small_model_harness_20261115/tests -v      (from the repository root)
"""
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "headroom_diagnostic_20261112"))

from langchain_core.tools import StructuredTool  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from typing import List, Optional  # noqa: E402

import harness  # noqa: E402
import pilot_score  # noqa: E402


class FakeRecorder:
    def __init__(self):
        self.rows = []

    def add(self, kind, **values):
        self.rows.append(dict(kind=kind, **values))

    def events(self, name):
        return [r for r in self.rows if r["kind"] == "handler" and r["event"] == name]


class FakeMonitor:
    def __init__(self, log):
        self.events, self.log = [], log

    def start(self):
        pass

    def changed_since(self, node_name, since):
        wanted = None if node_name is None else "/" + node_name.lstrip("/")
        return [e for e in self.events if e[0] > since and (wanted is None or e[1] == wanted)]

    def stop(self):
        pass


class NodeArgs(BaseModel):
    nodes: List[str]


class ParamArgs(BaseModel):
    node_name: str
    param_name: str


class ListArgs(BaseModel):
    pattern: Optional[str] = None
    blacklist: Optional[List[str]] = None


class World:
    """A tiny fake ROS graph behind fake tools with the real names and the real result shapes."""
    nodes = {"/a/gauge": 5, "/b/gauge": 7, "/e1h/lab/probe": 9, "/e1h/tank": 30}

    def __init__(self):
        self.calls = []

    def node_info(self, nodes):
        self.calls.append(("ros2_node_info", list(nodes)))
        return {n: (f"{n} info\n  Subscribers:\nNode name: {n.rsplit('/', 1)[1]}\nNode namespace: {n.rsplit('/', 1)[0] or '/'}\n" if n in self.nodes else dict(error=f"Unable to find node '{n}'")) for n in nodes}

    def param_get(self, node_name, param_name):
        self.calls.append(("ros2_param_get", node_name, param_name))
        if node_name not in self.nodes:
            return {"error": "Node not found"}
        return {param_name: f"Integer value is: {self.nodes[node_name]}\n"}

    def node_list(self, pattern=None, blacklist=None):
        self.calls.append(("ros2_node_list", pattern))
        return {"nodes": sorted(self.nodes)}

    def tools(self):
        make = lambda name, fn, model, desc: StructuredTool(name=name, description=desc, args_schema=model, func=fn)
        extra = [make(n, (lambda **kw: {}), ListArgs, n) for n in ["ros2_topic_list", "ros2_service_list", "ros2_param_list"]]
        hidden = [make(n, (lambda **kw: {"ok": 1}), ParamArgs, n) for n in ["ros2_param_set", "ros2_service_call", "add"]]
        return [make("ros2_node_info", self.node_info, NodeArgs, "node info"), make("ros2_param_get", self.param_get, ParamArgs, "param get"),
                make("ros2_node_list", self.node_list, ListArgs, "node list")] + extra + hidden


def make_arm(name, task_id="p3"):
    harness.ParameterEventMonitor = FakeMonitor
    recorder = FakeRecorder()
    arm = harness.Arm(name, recorder, dict(task=dict(id=task_id)), [("system", "base")])
    world = World()
    tools = {t.name: t for t in arm.wrap_tools(world.tools())}
    return arm, recorder, world, tools


def offer(arm, tools):
    schemas = [harness.convert_to_openai_tool(t) for t in tools.values()]
    return arm.visible_schemas(schemas, [])


class StrictValidation(unittest.TestCase):
    def test_error_text_names_field_expected_type_and_received_value(self):
        schema = {"type": "object", "properties": {"nodes": {"type": "array", "items": {"type": "string"}}}, "required": ["nodes"]}
        text = harness.strict_error("ros2_node_info", schema, {"nodes": "/a/gauge"})
        self.assertEqual(text, "Invalid arguments for ros2_node_info: field 'nodes': expected array, received string \"/a/gauge\". Fix the arguments and call the tool again.")
        self.assertIn("required field, received missing", harness.strict_error("t", schema, {}))

    def test_no_value_repair_string_is_not_coerced_to_integer(self):
        schema = {"type": "object", "properties": {"count": {"type": "integer"}}}
        self.assertIn("expected integer, received string", harness.strict_error("t", schema, {"count": "5"}))
        self.assertIsNone(harness.strict_error("t", schema, {"count": 5}))

    def test_optional_list_given_an_object_is_rejected_and_reaches_the_model_as_text(self):
        arm, rec, world, tools = make_arm("C1")
        offer(arm, tools)
        result = tools["ros2_node_list"].run({"blacklist": {}})
        self.assertIn("field 'blacklist': expected array or null, received object", result)
        self.assertEqual(world.calls, [])  # the tool was not run


class C1Control(unittest.TestCase):
    def test_write_tool_is_hidden_and_blocked_at_execution(self):
        arm, rec, world, tools = make_arm("C1")
        names = [s["function"]["name"] for s in offer(arm, tools)]
        self.assertNotIn("ros2_param_set", names)
        self.assertNotIn("add", names)
        self.assertIn("final_answer", names)
        result = tools["ros2_param_set"].run({"node_name": "/a/gauge", "param_name": "x"})  # a model calling it anyway
        self.assertIn("not available", result)
        self.assertEqual(len(rec.events("blocked_write_tool")), 1)
        self.assertEqual(world.calls, [])

    def test_tool_exception_becomes_an_observation(self):
        harness.ParameterEventMonitor = FakeMonitor
        rec = FakeRecorder()
        arm = harness.Arm("C1", rec, dict(task=dict(id="p3")), [("system", "base")])

        def explode(**kw):
            raise ValueError("bad regex")
        inner = StructuredTool(name="ros2_node_list", description="d", args_schema=ListArgs, func=explode)
        tools = {t.name: t for t in arm.wrap_tools([inner])}
        arm.offered = {"ros2_node_list"}
        self.assertIn("failed: ValueError: bad regex", tools["ros2_node_list"].run({}))  # returned as text, not raised
        self.assertEqual(len(rec.events("tool_exception")), 1)

    def test_final_answer_accepts_object_and_retries_once_on_invalid(self):
        arm, rec, world, tools = make_arm("C1")
        offer(arm, tools)
        self.assertIn("field 'answer': expected object", tools["final_answer"].run({"answer": "text"}))  # strict check, first invalid
        self.assertFalse(arm.final_done)
        tools["final_answer"].run({"answer": {"a": 1}})
        self.assertTrue(arm.final_done)
        self.assertEqual(arm.final_answer, {"a": 1})

    def test_second_invalid_final_answer_is_accepted_as_is(self):
        arm, rec, world, tools = make_arm("C1")
        offer(arm, tools)
        tools["final_answer"].run({"answer": {}})
        self.assertFalse(arm.final_done)
        tools["final_answer"].run({"answer": {}})
        self.assertTrue(arm.final_done)
        self.assertEqual([r for r in rec.rows if r["kind"] == "final_answer_accepted"][0]["invalid"], True)


class M0Control(unittest.TestCase):
    def test_supertool_returns_the_sequence_unchanged_and_prompt_has_the_sentence(self):
        arm, rec, world, tools = make_arm("M0")
        self.assertIn("supertool", [s["function"]["name"] for s in offer(arm, tools)])
        self.assertEqual(tools["supertool"].run({"input_str": "x", "generated_instruction_sequence": "1. node_list 2. param_get"}), "1. node_list 2. param_get")
        self.assertIn(harness.M0_LINE, arm.prompt_messages)
        arm2, _, _, tools2 = make_arm("C1")
        self.assertNotIn("supertool", [s["function"]["name"] for s in offer(arm2, tools2)])


class FullNames(unittest.TestCase):
    def test_full_name_line_added_after_node_name_and_namespace(self):
        arm, rec, world, tools = make_arm("C1+FN")
        offer(arm, tools)
        out = tools["ros2_node_info"].run({"nodes": ["/a/gauge"]})
        self.assertIn("Node namespace: /a\nFull name: /a/gauge\n", out["/a/gauge"])


class H2Canonicalization(unittest.TestCase):
    def prime(self, arm, tools):
        offer(arm, tools)
        tools["ros2_node_list"].run({})  # makes the full names visible to the handler

    def test_ambiguous_suffix_two_matches_no_repair_candidate_list_shown(self):
        arm, rec, world, tools = make_arm("C1+H2")
        self.prime(arm, tools)
        out = tools["ros2_param_get"].run({"node_name": "gauge", "param_name": "x"})
        self.assertEqual(len(rec.events("h2_repair")), 0)
        self.assertEqual(rec.events("h2_no_repair")[0]["candidates"], ["/a/gauge", "/b/gauge"])
        self.assertIn("/a/gauge", out["hint"])
        self.assertNotIn("Note:", json.dumps(out))

    def test_unique_suffix_repairs_even_when_target_differs_known_harm_mode_is_logged(self):
        arm, rec, world, tools = make_arm("C1+H2")
        self.prime(arm, tools)
        out = tools["ros2_param_get"].run({"node_name": "/lab/probe", "param_name": "x"})  # asked about /lab/probe, which is NOT running
        repair = rec.events("h2_repair")[0]
        self.assertEqual((repair["given"], repair["resolved"]), ("/lab/probe", "/e1h/lab/probe"))
        self.assertEqual(out["note"], "Note: '/lab/probe' resolved to '/e1h/lab/probe'")
        effective = [r for r in rec.rows if r["kind"] == "effective_call"][0]
        self.assertEqual(effective["args"]["node_name"], "/e1h/lab/probe")
        self.assertEqual(effective["given"]["node_name"], "/lab/probe")

    def test_zero_matches_gives_the_normal_error(self):
        arm, rec, world, tools = make_arm("C1+H2")
        self.prime(arm, tools)
        out = tools["ros2_param_get"].run({"node_name": "/nowhere/xyz", "param_name": "x"})
        self.assertEqual(out, {"error": "Node not found"})
        self.assertEqual(len(rec.events("h2_repair")), 0)

    def test_list_argument_repairs_only_the_failing_item(self):
        arm, rec, world, tools = make_arm("C1+H2")
        self.prime(arm, tools)
        out = tools["ros2_node_info"].run({"nodes": ["/a/gauge", "tank"]})
        self.assertEqual(rec.events("h2_repair")[0]["resolved"], "/e1h/tank")
        self.assertIn("/e1h/tank", out)
        self.assertIn("/a/gauge", out)


class H1Reuse(unittest.TestCase):
    def call_twice(self, arm, tools, between=None):
        offer(arm, tools)
        first = tools["ros2_param_get"].run({"node_name": "/e1h/tank", "param_name": "level"})
        if between:
            between()
        second = tools["ros2_param_get"].run({"node_name": "/e1h/tank", "param_name": "level"})
        return first, second

    def test_h1e_reuses_when_no_parameter_event(self):
        arm, rec, world, tools = make_arm("C1+H1e")
        first, second = self.call_twice(arm, tools)
        self.assertEqual(len(world.calls), 1)
        self.assertEqual(second["note"], "Unchanged since step 1 (no parameter event).")
        self.assertEqual(len(rec.events("reuse")), 1)

    def test_h1e_blocked_after_a_parameter_event_for_that_node(self):
        arm, rec, world, tools = make_arm("C1+H1e")
        import time as t
        def change():
            world.nodes["/e1h/tank"] = 45
            arm.monitor.events.append((t.perf_counter() + 0.001, "/e1h/tank"))
        first, second = self.call_twice(arm, tools, change)
        self.assertEqual(len(world.calls), 2)
        self.assertIn("45", json.dumps(second))
        self.assertEqual(len(rec.events("reuse_blocked")), 1)
        World.nodes["/e1h/tank"] = 30

    def test_h1e_event_for_another_node_does_not_block(self):
        arm, rec, world, tools = make_arm("C1+H1e")
        import time as t
        first, second = self.call_twice(arm, tools, lambda: arm.monitor.events.append((t.perf_counter() + 0.001, "/other")))
        self.assertEqual(len(world.calls), 1)

    def test_h1e_is_only_for_param_calls(self):
        arm, rec, world, tools = make_arm("C1+H1e")
        offer(arm, tools)
        tools["ros2_node_list"].run({})
        tools["ros2_node_list"].run({})
        self.assertEqual(len([c for c in world.calls if c[0] == "ros2_node_list"]), 2)

    def test_h1n_reuses_despite_a_change_and_for_any_read_tool(self):
        arm, rec, world, tools = make_arm("C1+H1n")
        def change():
            world.nodes["/e1h/tank"] = 45
        first, second = self.call_twice(arm, tools, change)
        self.assertEqual(len(world.calls), 1)
        self.assertIn("30", json.dumps(second))  # stale value returned, by design of the harm probe
        tools["ros2_node_list"].run({})
        tools["ros2_node_list"].run({})
        self.assertEqual(len([c for c in world.calls if c[0] == "ros2_node_list"]), 1)
        World.nodes["/e1h/tank"] = 30

    def test_a_failed_call_is_never_reused(self):
        arm, rec, world, tools = make_arm("C1+H1n")
        offer(arm, tools)
        tools["ros2_param_get"].run({"node_name": "/nope", "param_name": "x"})
        tools["ros2_param_get"].run({"node_name": "/nope", "param_name": "x"})
        self.assertEqual(len(world.calls), 2)


class H7Plan(unittest.TestCase):
    PLAN = {"steps": [{"tools": ["ros2_node_list"], "for_each": False}, {"tools": ["ros2_param_get"], "for_each": True}]}

    def names(self, arm, tools):
        return [s["function"]["name"] for s in offer(arm, tools)]

    def test_first_request_offers_only_submit_plan(self):
        arm, rec, world, tools = make_arm("C1+H7")
        self.assertEqual(self.names(arm, tools), ["submit_plan"])

    def test_valid_plan_then_per_step_menus_and_advance(self):
        arm, rec, world, tools = make_arm("C1+H7", "v3")
        offer(arm, tools)
        tools["submit_plan"].run(self.PLAN)
        accepted = rec.events("plan_accepted")[0]
        self.assertFalse(accepted["complete_vs_floor_route"])  # v3 route also needs node_info
        self.assertEqual(accepted["missing_tools"], ["ros2_node_info"])
        self.assertEqual(sorted(self.names(arm, tools)), sorted(["ros2_node_list", "ros2_param_get", "replan", "final_answer"]))
        tools["ros2_node_list"].run({})
        tools["ros2_param_get"].run({"node_name": "/a/gauge", "param_name": "x"})  # a next-step tool advances the plan
        self.assertEqual(arm.plan.index, 1)
        self.assertEqual(sorted(self.names(arm, tools)), sorted(["ros2_param_get", "replan", "final_answer"]))

    def test_tool_outside_the_current_and_next_step_is_refused(self):
        arm, rec, world, tools = make_arm("C1+H7")
        offer(arm, tools)
        tools["submit_plan"].run(self.PLAN)
        offer(arm, tools)
        self.assertIn("not available at this step", tools["ros2_node_info"].run({"nodes": ["/a/gauge"]}))

    def test_invalid_plan_gives_a_compact_error_then_second_invalid_falls_back_to_c1(self):
        arm, rec, world, tools = make_arm("C1+H7")
        offer(arm, tools)
        bad = {"steps": [{"tools": ["fly_to_moon"], "for_each": False}]}
        self.assertIn("Invalid plan: step 1 uses unknown tools ['fly_to_moon']", tools["submit_plan"].run(bad))
        self.assertFalse(arm.plan_fallback)
        self.assertEqual(self.names(arm, tools), ["submit_plan"])
        self.assertIn("switched off", tools["submit_plan"].run(bad))
        self.assertTrue(arm.plan_fallback)
        names = self.names(arm, tools)  # C1 menu from now on
        self.assertIn("ros2_node_info", names)
        self.assertNotIn("submit_plan", names)
        self.assertEqual(len(rec.events("plan_invalid")), 2)
        self.assertEqual(len(rec.events("plan_fallback")), 1)

    def test_schema_invalid_plan_counts_as_invalid_and_second_one_falls_back(self):
        arm, rec, world, tools = make_arm("C1+H7")
        offer(arm, tools)
        first = tools["submit_plan"].run({"steps": "node_list then param_get"})
        self.assertIn("Invalid plan: arguments do not match the plan format", first)
        self.assertFalse(arm.plan_fallback)
        second = tools["submit_plan"].run({"steps": [{"tools": "ros2_node_list"}]})
        self.assertIn("switched off", second)
        self.assertTrue(arm.plan_fallback)

    def test_calling_another_tool_instead_of_planning_counts_as_invalid_plan(self):
        arm, rec, world, tools = make_arm("C1+H7")
        offer(arm, tools)
        self.assertIn("call submit_plan first", tools["ros2_node_list"].run({}))
        self.assertEqual(arm.plan_invalid, 1)
        offer(arm, tools)
        self.assertIn("switched off", tools["ros2_node_list"].run({}))
        self.assertTrue(arm.plan_fallback)
        self.assertIn("ros2_node_list", [s["function"]["name"] for s in offer(arm, tools)])

    def test_more_than_two_replans_fall_back(self):
        arm, rec, world, tools = make_arm("C1+H7")
        offer(arm, tools)
        tools["submit_plan"].run(self.PLAN)
        for _ in range(3):
            offer(arm, tools)
            tools["replan"].run(self.PLAN)
        self.assertTrue(arm.plan_fallback)
        self.assertEqual(rec.events("plan_fallback")[0]["reason"], "more than 2 replans")

    def test_final_answer_is_always_offered(self):
        arm, rec, world, tools = make_arm("C1+H7")
        offer(arm, tools)
        tools["submit_plan"].run(self.PLAN)
        self.assertIn("final_answer", self.names(arm, tools))


class Scoring(unittest.TestCase):
    def test_last_complete_json_object_rule(self):
        text = 'tool said {"gain": "Integer value is: 50"} so the answer is {"node": "/a/x", "gain": 50} done'
        self.assertEqual(pilot_score.last_json_object(text), {"node": "/a/x", "gain": 50})
        self.assertEqual(pilot_score.last_json_object('{"a": {"b": 1}}'), {"a": {"b": 1}})  # nested object does not count as the last one
        self.assertIsNone(pilot_score.last_json_object("no object here"))

    def test_support_uses_executed_arguments_after_a_repair(self):
        events = [dict(kind="tool_start", name="ros2_param_get", input={"node_name": "/lab/probe", "param_name": "limit"}, run_id="r1", line=1),
                  dict(kind="effective_call", args={"node_name": "/e1h/lab/probe", "param_name": "limit"}, given={}, tool_run_id="r1", line=2),
                  dict(kind="tool_end", output={"limit": "Integer value is: 9\n"}, run_id="r1", line=3)]
        rows = pilot_score.tool_rows(events)
        self.assertEqual(rows[0]["args"]["node_name"], "/e1h/lab/probe")
        self.assertEqual(rows[0]["given_args"]["node_name"], "/lab/probe")
        self.assertEqual(pilot_score.param_values(rows), {("/e1h/lab/probe", "limit"): 9})

    def test_route_tools_match_the_verified_floor_check_logs_when_present(self):
        runs = sorted((HERE.parents[1] / "_artifacts/runs/headroom_diagnostic_20261112").glob("stage3_floorcheck_*"))
        if not runs:
            self.skipTest("floor-check run not present")
        for task_id, names in harness.ROUTE_BY_ID.items():
            log = json.loads((runs[-1] / f"minimal_{task_id}.json").read_text())["log"]
            self.assertEqual(sorted({e["tool"] for e in log}), sorted(names), task_id)


if __name__ == "__main__":
    unittest.main()
