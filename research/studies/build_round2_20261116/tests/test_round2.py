"""Tests for build round 2 (no ROS, no Ollama).  From the repository root:
  uv run python -m unittest discover -s research/studies/build_round2_20261116/tests -v
Groups: A payload identity (V-a), B sweep mechanics on fake tools, C trigger equivalence with the offline replay on the 400 recorded episodes,
D scoring adapter = scorer v2.0 on recorded traces without sweeps, E answer rewrite = replay rewrite, F frozen fixed line.
"""
import json
from pathlib import Path
import sys
import unittest

from langchain_core.tools import StructuredTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, Field
from typing import List, Optional

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import round2_harness as r2  # noqa: E402
import score_round2  # noqa: E402
import sweep_logic  # noqa: E402

NODES = [f"/plant/n{i}" for i in range(1, 26)]  # 25 names: more than the 20-name limit


class FakeRecorder:
    def __init__(self):
        self.rows = []

    def add(self, kind, **values):
        self.rows.append(dict(kind=kind, **values))

    def events(self, name):
        return [r for r in self.rows if r.get("event") == name]


class NodeInfoArgs(BaseModel):
    nodes: List[str] = Field(description=":param nodes: names of nodes")


class ParamGetArgs(BaseModel):
    node_name: str = Field(description="name of node")
    param_name: str = Field(description="name of parameter")


class ParamListArgs(BaseModel):
    node_name: Optional[str] = Field(None, description="name of node")
    pattern: Optional[str] = Field(None, description="filter")


class NoArgs(BaseModel):
    pass


def make_tools(sizes=None, failing=()):
    sizes = sizes or {}

    def node_list():
        return {"nodes": list(NODES)}

    def node_info(nodes):
        return {n: ({"error": f"Node not found: {n}"} if n in failing else "Node name: x " + "y" * sizes.get(n, 40)) for n in nodes}

    def param_get(node_name, param_name):
        return {param_name: f"Integer value is: 5 ({node_name})"}

    def param_list(node_name=None, pattern=None):
        return {node_name or "all": ["a", "b"]}
    return [StructuredTool(name="ros2_node_list", description="list nodes", args_schema=NoArgs, func=node_list),
            StructuredTool(name="ros2_node_info", description="info", args_schema=NodeInfoArgs, func=node_info),
            StructuredTool(name="ros2_param_get", description="get", args_schema=ParamGetArgs, func=param_get),
            StructuredTool(name="ros2_param_list", description="plist", args_schema=ParamListArgs, func=param_list)]


class Session:
    """Drives one arm like the executor does: per request visible_schemas, the model's calls registered, then the calls through the wrapped tools."""
    def __init__(self, arm_name, **tool_options):
        self.recorder = FakeRecorder()
        self.arm = r2.make_arm(arm_name, self.recorder, dict(task=dict(request="Which node? Look at /plant/n1."), ns="/"))
        self.tools = {t.name: t for t in self.arm.wrap_tools(make_tools(**tool_options))}
        self.schemas = [convert_to_openai_tool(t) for t in self.tools.values()]
        self.offered_log, self.outputs = [], []

    def request(self, calls):
        offered = self.arm.visible_schemas(self.schemas, [])
        self.offered_log.append([s["function"]["name"] for s in offered])
        self.arm.tracker.register_model_calls(self.arm.request_count, [dict(name=n, args=a) for n, a in calls])
        results = [self.tools[name].func(**args) for name, args in calls]
        self.outputs.append(results)
        return results


NO_TRIGGER = [[("ros2_node_list", {})], [("ros2_node_info", {"nodes": ["/plant/n1"]})], [("ros2_param_get", {"node_name": "/plant/n1", "param_name": "gain"})],
              [("ros2_param_list", {"node_name": "/plant/n1"})]]
TWO_CALLS = [[("ros2_node_list", {})], [("ros2_node_info", {"nodes": ["/plant/n1"]})], [("ros2_node_info", {"nodes": ["/plant/n2"]})]]


class PayloadIdentity(unittest.TestCase):  # V-a
    def test_no_trigger_payloads_identical(self):
        control, sweep = Session("CONTROL"), Session("SWEEP")
        for calls in NO_TRIGGER:
            control.request(calls)
            sweep.request(calls)
        self.assertEqual(control.arm.prompt_messages, sweep.arm.prompt_messages)
        self.assertEqual(control.offered_log, sweep.offered_log)
        self.assertEqual(control.schemas, sweep.schemas)
        self.assertEqual(control.outputs, sweep.outputs)
        self.assertFalse(sweep.recorder.events("sweep_fire") or control.recorder.events("sweep_shadow"))

    def test_same_up_to_the_firing_request_and_shadow_changes_nothing(self):
        control, sweep = Session("CONTROL"), Session("SWEEP")
        for calls in TWO_CALLS:
            control.request(calls)
            sweep.request(calls)
        self.assertEqual(control.outputs[:2], sweep.outputs[:2])
        self.assertEqual(len(control.recorder.events("sweep_shadow")), 1)
        self.assertEqual(len(sweep.recorder.events("sweep_fire")), 1)
        self.assertEqual(control.outputs[2], [{"/plant/n2": "Node name: x " + "y" * 40}])  # shadow: result untouched
        self.assertNotEqual(control.outputs[2], sweep.outputs[2])


class SweepMechanics(unittest.TestCase):
    def test_fire_content_and_fixed_line(self):
        sweep = Session("SWEEP")
        for calls in TWO_CALLS:
            sweep.request(calls)
        result = sweep.outputs[2][0]
        fire = sweep.recorder.events("sweep_fire")[0]
        self.assertEqual(fire["request"], 3)
        self.assertEqual(fire["tool"], "ros2_node_info")
        self.assertEqual(fire["group_source"], dict(request=1, tool="ros2_node_list"))
        self.assertEqual(fire["sweep"], NODES[2:22])  # group order, minus n1 (earlier call) and n2 (this call), first 20
        self.assertEqual(fire["cut"], NODES[22:])  # cut by the 20-name limit
        self.assertEqual(fire["extra_tool_runs"], 20)
        self.assertEqual(result["also_read_note"], "Also read with the same arguments, for other names from the same list (results keyed by full name): "
                         + ", ".join(NODES[2:22]) + ". Not read (limit reached): " + ", ".join(NODES[22:]) + ".")
        self.assertEqual(list(result["also_read"]), NODES[2:22])
        self.assertIn("/plant/n2", result)  # the original result is untouched
        self.assertEqual(fire["original_output"], {"/plant/n2": "Node name: x " + "y" * 40})
        self.assertTrue(all(i["output"] for i in fire["items"]))

    def test_no_second_firing_for_covered_names_and_one_firing_per_request(self):
        sweep = Session("SWEEP")
        for calls in TWO_CALLS:
            sweep.request(calls)
        sweep.request([("ros2_node_info", {"nodes": ["/plant/n3"]})])  # covered by the sweep: no firing, no tool run
        sweep.request([("ros2_node_info", {"nodes": ["/plant/n23"]}), ("ros2_node_info", {"nodes": ["/plant/n24"]})])  # one firing at most for the request
        self.assertEqual(len(sweep.recorder.events("sweep_fire")), 2)
        self.assertEqual(sweep.recorder.events("sweep_fire")[1]["sweep"], ["/plant/n25"])  # remaining group names after n23 n24 (being called)
        self.assertNotIn("also_read", sweep.outputs[4][1])

    def test_token_limit_item_failure_and_empty_set(self):
        big = {n: 6000 for n in NODES[2:6]}  # each ~1500 tokens: two fit under 3000, the third passes the limit
        sweep = Session("SWEEP", sizes=big, failing=("/plant/n3",))
        for calls in TWO_CALLS:
            sweep.request(calls)
        fire = sweep.recorder.events("sweep_fire")[0]
        self.assertEqual(fire["sweep"], ["/plant/n3", "/plant/n4"])
        self.assertEqual(fire["cut"][:2], ["/plant/n5", "/plant/n6"])
        self.assertEqual(fire["extra_tool_runs"], 3)  # the item that passed the limit was run but not appended
        result = sweep.outputs[2][0]
        self.assertIn("error", result["also_read"]["/plant/n3"])  # an item failure stays in its own entry
        self.assertIn("Not read (limit reached): /plant/n5", result["also_read_note"])
        # first result alone above the limit: nothing appended, no firing
        huge = Session("SWEEP", sizes={n: 20000 for n in NODES})
        for calls in TWO_CALLS:
            huge.request(calls)
        self.assertEqual(huge.recorder.events("sweep_fire"), [])
        self.assertEqual(len(huge.recorder.events("sweep_empty_after_limit")), 1)

    def test_param_tools_other_arguments_must_match_and_defaults_count_as_missing(self):
        sweep = Session("SWEEP")
        sweep.request([("ros2_node_list", {})])
        sweep.request([("ros2_param_get", {"node_name": "/plant/n1", "param_name": "gain"})])
        sweep.request([("ros2_param_get", {"node_name": "/plant/n2", "param_name": "other"})])  # other argument differs: no trigger
        self.assertEqual(sweep.recorder.events("sweep_fire"), [])
        sweep.request([("ros2_param_get", {"node_name": "/plant/n3", "param_name": "other"})])  # same as previous request: trigger
        fire = sweep.recorder.events("sweep_fire")[0]
        self.assertEqual(fire["tool"], "ros2_param_get")
        self.assertEqual(fire["extra_tool_runs"], 20)
        self.assertIsInstance(sweep.outputs[3][0], dict)
        # a default passed explicitly equals a missing argument
        s2 = Session("SWEEP")
        s2.request([("ros2_node_list", {})])
        s2.request([("ros2_param_list", {"node_name": "/plant/n1"})])
        s2.request([("ros2_param_list", {"node_name": "/plant/n2", "pattern": None})])
        self.assertEqual(len(s2.recorder.events("sweep_fire")), 1)

    def test_topic_echo_and_non_eligible_tools_never_fire(self):
        self.assertNotIn("ros2_topic_echo", sweep_logic.ELIGIBLE_TOOLS)
        tracker = sweep_logic.SweepTracker()
        tracker.register_model_calls(1, [dict(name="ros2_topic_echo", args={"topic": "/a"})])
        tracker.register_model_calls(2, [dict(name="ros2_topic_echo", args={"topic": "/b"})])
        self.assertIsNone(tracker.evaluate(2, "ros2_topic_echo", {"topic": "/b"}))


class FixedLine(unittest.TestCase):
    def test_wording_is_frozen(self):
        self.assertEqual(r2.fixed_line(["/a", "/b"], []), "Also read with the same arguments, for other names from the same list (results keyed by full name): /a, /b.")
        self.assertEqual(r2.fixed_line(["/a"], ["/c"]), "Also read with the same arguments, for other names from the same list (results keyed by full name): /a. Not read (limit reached): /c.")
        self.assertEqual(r2.attach("text", "L", {"/a": 1}), 'text\nL\n{"/a": 1}')
        self.assertEqual(r2.attach({"k": 1}, "L", {"/a": 1}), {"k": 1, "also_read_note": "L", "also_read": {"/a": 1}})


# ------------------------------------------------------------------ tests on the recorded episodes (parsed once)
_cache = {}


def replay_module():
    if "replay" not in _cache:
        sys.path.insert(0, str(HERE.parent / "offline_replay_20261116"))
        import replay
        _cache["replay"] = replay
    return _cache["replay"]


class TriggerEquivalence(unittest.TestCase):
    @staticmethod
    def feed(ep, replay_mode, replay_sweep_sizes=()):
        """Feed one recorded episode through the tracker. replay_mode=True mimics the replay's information exactly (one name at a time, names of the same call
        count as unread until processed); False is the protocol's rule (the model's whole response is known: names called in request k are excluded)."""
        tracker, firings = sweep_logic.SweepTracker(), []
        for r in ep["requests"]:
            calls = [dict(name=u["tool"], args=u["args"]) for u in r["units"]]
            if not replay_mode:
                tracker.register_model_calls(r["index"], calls)
            for call, u in zip(calls, r["units"]):
                if u["harness_error"]:
                    if replay_mode:
                        tracker.register_model_calls(r["index"], [call])
                    continue  # a call that raised in the live loop never reaches the trigger check
                pieces = [call]
                key, names = sweep_logic.entity_names(u["args"])
                if replay_mode and key is not None and isinstance(u["args"][key], list):
                    pieces = [dict(name=u["tool"], args={**u["args"], key: [n]}) for n in names]
                for piece in pieces:
                    if replay_mode:
                        tracker.register_model_calls(r["index"], [piece])
                    fire = tracker.evaluate(r["index"], piece["name"], piece["args"])
                    if fire:
                        if replay_mode and len(firings) < len(replay_sweep_sizes):
                            fire["sweep"] = fire["sweep"][:replay_sweep_sizes[len(firings)]]  # the replay cut by an estimated token budget; the live arm cuts by real sizes
                        tracker.mark_covered(fire, fire["sweep"])
                        firings.append(fire)
                        if replay_mode:
                            tracker.fired_requests.discard(r["index"])  # the replay allows several firings per request; the protocol allows one
                tracker.add_result(r["index"], u["tool"], u["output"], u["text"], u["ok"])
        return firings

    def test_tracker_in_replay_mode_matches_replay_v1_on_recorded_episodes(self):
        replay = replay_module()
        differing, total_tracker, total_replay, size_differs = [], 0, 0, 0
        for ep in replay.eps:
            expected = replay.proposal1(ep, "V1")
            firings = self.feed(ep, replay_mode=True, replay_sweep_sizes=expected["sweep_sizes"])
            total_tracker += len(firings)
            total_replay += expected["triggers"]
            if [f["group_size"] for f in firings] != expected["group_sizes"]:
                differing.append((ep["run_id"], [f["group_size"] for f in firings], expected["group_sizes"]))
            elif [len(f["sweep"]) for f in firings] != expected["sweep_sizes"]:
                size_differs += 1
        print(f"\nreplay mode: tracker firings {total_tracker}, replay triggers {total_replay}, episodes differing in group sizes {len(differing)}, "
              f"episodes with different sweep sizes {size_differs}")
        self.assertEqual(size_differs, 0)
        self.assertEqual(total_replay, 31)
        self.assertEqual(differing, [], "the tracker must reproduce the replay's V1 triggers when given the replay's information")

    def test_protocol_rule_fires_less_often_than_the_replay_and_never_in_new_places(self):
        replay = replay_module()
        firings, episodes = 0, 0
        for ep in replay.eps:
            mine = self.feed(ep, replay_mode=False)
            expected = replay.proposal1(ep, "V1")
            firings += len(mine)
            episodes += bool(mine)
            self.assertLessEqual(len(mine), expected["triggers"] + 0, ep["run_id"])
            if expected["triggers"] == 0:
                self.assertEqual(mine, [], ep["run_id"])
        print(f"\nprotocol rule (names called in request k excluded): {firings} firings in {episodes} of 400 recorded episodes (replay: 31 in 22)")


class ScoringAdapter(unittest.TestCase):
    def test_equals_scorer_v2_on_recorded_traces_without_sweeps(self):
        replay = replay_module()
        E = replay.E
        checked = 0
        tasks = E.load_tasks()
        for group, row in E.run_rows():
            events = score_round2.v2.s1.read_events(replay.E.REPO / row["trace_path"])
            if any(e["kind"] == "handler" and e.get("event") == "list_item" for e in events):
                continue  # round 1 list-argument arms are scored by round 1's adapter; round 2 arms have no list arguments
            task = tasks[row["task"]]
            direct = score_round2.v2.score_events(task, events)
            adapted = score_round2.score_events(task, events)
            for key in ("exact", "issues", "support_missing", "supported_complete"):
                self.assertEqual(direct[key], adapted[key], (row["run_id"], key))
            checked += 1
        self.assertGreater(checked, 300)
        print(f"\nadapter equals scorer v2.0 on {checked} recorded traces without list calls or sweeps")

    def test_sweep_rows_expand_to_single_rows_and_trigger_row_is_original(self):
        events = [dict(kind="tool_start", run_id="r1", name="ros2_node_info", input="{'nodes': ['/a']}", line=1),
                  dict(kind="tool_end", run_id="r1", output={"/a": "ok", "also_read_note": "L", "also_read": {"/b": "ok b"}}),
                  dict(kind="handler", event="sweep_fire", tool_run_id="r1", tool="ros2_node_info", original_output={"/a": "ok"},
                       items=[dict(name="/b", args={"nodes": ["/b"]}, output={"/b": "ok b"})])]
        rows = score_round2.expanded_rows(events)
        self.assertEqual([r["args"] for r in rows], [{"nodes": ["/a"]}, {"nodes": ["/b"]}])
        self.assertEqual(rows[0]["output"], {"/a": "ok"})
        self.assertEqual(rows[1]["output"], {"/b": "ok b"})


class RewriteEquivalence(unittest.TestCase):
    def test_same_as_replay_rewrite_on_recorded_answers(self):
        replay = replay_module()
        ag = replay.ag
        compared = 0
        for ep in replay.eps:
            if not isinstance(ep["answer"], dict):
                continue
            outputs = [u["output"] for r in ep["requests"] for u in r["units"] if u["tool"] != "final_answer" and not u["harness_error"]]
            allowed = ag.allowed_names(ep["task_text"], outputs)
            a, b = [], []
            self.assertEqual(r2.rewrite(ep["answer"], allowed, a), replay.rewrite(ep["answer"], allowed, b))
            self.assertEqual(a, b)
            compared += 1
        self.assertGreater(compared, 300)

    def test_shadow_does_not_change_the_submitted_answer(self):
        s = Session("CONTROL")
        s.arm.tool_outputs.append({"nodes": ["/plant/dune"]})
        s.arm.offered = {"final_answer"}
        s.arm.execute_extra("final_answer", {"answer": {"node": "dune"}})
        self.assertEqual(s.arm.final_answer, {"node": "dune"})
        shadow = s.recorder.events("rewrite_shadow")[0]
        self.assertEqual(shadow["rewritten"], {"node": "/plant/dune"})
        self.assertTrue(shadow["changed"])


class FakeFixtureModule:
    """Stands in for stage3_fixture: an oracle that makes the same cli() calls as the real one (a no-daemon node list, then other reads)."""
    GRAPH = {"nodes": [{"fqn": "/plant/a"}, {"fqn": "/plant/b"}]}

    def __init__(self):
        self.calls = []

    def cli(self, *argv, retries=3):
        self.calls.append(argv)
        return ("/plant/a\n/stale\n" if argv[:2] == ("node", "list") else "ok"), 0

    def oracle(self, out, recorder):
        listed = set(self.cli("node", "list", "--no-daemon", "--spin-time", "4")[0].splitlines())
        self.cli("param", "get", "/plant/a", "gain")
        return [f"node not listed: {n['fqn']}" for n in self.GRAPH["nodes"] if n["fqn"] not in listed]


class G_OracleAmendment4(unittest.TestCase):
    def test_node_list_goes_through_the_daemon_is_logged_and_nothing_else_changes(self):
        import tempfile
        import run_round2
        module = FakeFixtureModule()
        wrapper = run_round2.OracleWithRetry(module)
        restarts = []
        wrapper.restart_daemon = lambda: (restarts.append(1), setattr(wrapper, "_daemon_restarted", True))
        run_round2.time.sleep = lambda seconds: None  # the 5-second wait of the retry
        with tempfile.TemporaryDirectory() as tmp:
            session = Path(tmp) / "session"
            (session / "oracle-before").mkdir(parents=True)
            bad = wrapper.oracle(session / "oracle-before", FakeRecorder())
            self.assertEqual(bad, ["node not listed: /plant/b"])  # a real miss still fails, after its retry
            self.assertEqual(restarts, [1])  # the daemon is restarted once, not per read
            raw = [json.loads(l) for l in (session / "oracle-before" / "node_list_raw.jsonl").read_text().splitlines()]
            self.assertEqual(len(raw), 2)  # first try and retry are both logged
            self.assertEqual(raw[0]["raw"], "/plant/a\n/stale\n")
            self.assertEqual((raw[0]["listed_fixture_nodes"], raw[0]["declared_fixture_nodes"], raw[0]["via_daemon"]), (1, 2, True))
        self.assertEqual([c for c in module.calls if c[:2] == ("node", "list")], [("node", "list")] * 2)  # never --no-daemon any more
        self.assertEqual([c for c in module.calls if c[:2] != ("node", "list")], [("param", "get", "/plant/a", "gain")] * 2)  # other reads unchanged


if __name__ == "__main__":
    unittest.main()
