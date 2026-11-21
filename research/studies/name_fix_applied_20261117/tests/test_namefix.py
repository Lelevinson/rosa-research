"""Frozen tests of the name-fix test (rule v2, strict adapter, lenient scorer, arm). No ROS, no Ollama. From the repository root:
  uv run python -m unittest discover -s research/studies/name_fix_applied_20261117/tests -v"""
import copy
import json
from pathlib import Path
import random
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "build_round2_20261116"))
import namefix_rule as rule  # noqa: E402
import namefix_scoring as scoring  # noqa: E402
import namefix_fixture as fixture  # noqa: E402
import round2_harness as r2  # noqa: E402

ALLOWED = {"/plant32/quill", "/plant32/anvil", "/plant32/dune"}
TASKS = {t["id"]: t for t in fixture.TASKS}
GRAPH = fixture.GRAPH
FIX = HERE / "tests" / "fixtures"


def run(answer, allowed=ALLOWED):
    events = []
    return rule.rewrite_answer(copy.deepcopy(answer), allowed, events), events


def leaves(value):
    if isinstance(value, dict):
        return [leaf for v in value.values() for leaf in leaves(v)]
    if isinstance(value, list):
        return [leaf for v in value for leaf in leaves(v)]
    return [value]


class RuleTests(unittest.TestCase):
    def test_same_as_round2_rewrite_when_there_is_no_collision(self):
        cases = [{"node": "quill"}, {"node": "/plant32/quill", "n": 3}, {"a": {"quill": 1, "dune": 2}}, {"a": ["anvil", "dune"]}, {"x": "unseen"}, {"x": "/never/seen"},
                 {"quill": 1}, {"nested": {"deep": {"anvil": "quill"}}}, {"ok": True, "v": None, "f": 1.5}]
        for answer in cases:
            old_events = []
            old = r2.rewrite(copy.deepcopy(answer), ALLOWED, old_events)
            new, new_events = run(answer)
            self.assertEqual(new, old, answer)
            self.assertEqual([e["kind"] for e in new_events], [e["kind"] for e in old_events], answer)

    def test_collision_of_nested_keys_keeps_every_key_and_value(self):
        for answer in ({"gains": {"quill": 1, "/plant32/quill": 2}}, {"gains": {"/plant32/quill": 2, "quill": 1}}):
            out, events = run(answer)
            self.assertEqual(out, answer)  # nothing changed, nothing lost
            self.assertEqual([e["kind"] for e in events], ["collision"])
        out, events = run({"gains": {"anvil": 5, "/anvil": 6}})
        self.assertEqual(out, {"gains": {"anvil": 5, "/anvil": 6}})
        self.assertEqual(sum(e["kind"] == "collision" for e in events), 2)
        out, events = run({"gains": {"quill": 1, "/plant32/anvil": 2}})  # no collision: rewritten as before
        self.assertEqual(out, {"gains": {"/plant32/quill": 1, "/plant32/anvil": 2}})
        self.assertFalse(any(e["kind"] == "collision" for e in events))

    def test_collision_of_list_items(self):
        out, events = run({"nodes": ["quill", "/plant32/quill"]})
        self.assertEqual(out, {"nodes": ["quill", "/plant32/quill"]})
        self.assertEqual([e["kind"] for e in events], ["collision"])
        out, events = run({"nodes": ["quill", "quill"]})  # two identical short items: both would become the same item
        self.assertEqual(out, {"nodes": ["quill", "quill"]})
        self.assertTrue(all(e["kind"] == "collision" for e in events) and len(events) == 2)
        out, events = run({"nodes": ["quill", "anvil", "dune"]})
        self.assertEqual(out, {"nodes": ["/plant32/quill", "/plant32/anvil", "/plant32/dune"]})

    def test_ambiguous_unseen_and_top_level_keys(self):
        allowed = ALLOWED | {"/other/quill"}
        out, events = run({"node": "quill"}, allowed)
        self.assertEqual(out, {"node": "quill"})
        self.assertEqual([e["kind"] for e in events], ["reject_ambiguous"])
        out, events = run({"node": "/ghost/node"})
        self.assertEqual((out, [e["kind"] for e in events]), ({"node": "/ghost/node"}, ["reject_never_seen"]))
        self.assertEqual(run({"quill": 1})[0], {"quill": 1})  # top-level keys are never rewritten

    def test_property_nothing_is_lost_and_result_is_idempotent(self):
        rng = random.Random(7)
        pool = ["quill", "anvil", "dune", "/plant32/quill", "/plant32/anvil", "/x/y", "zzz", "12", "mode"]
        def make(depth):
            roll = rng.random()
            if depth == 0 or roll < 0.35:
                return rng.choice(pool + [1, 2.5, True, None])
            if roll < 0.7:
                return {rng.choice(pool): make(depth - 1) for _ in range(rng.randint(1, 4))}
            return [make(depth - 1) for _ in range(rng.randint(1, 4))]
        for _ in range(500):
            answer = {"top": make(3), "other": make(2)}
            out, _events = run(answer)
            self.assertEqual(len(leaves(out)), len(leaves(answer)))  # no value dropped or merged
            again, again_events = run(out)
            self.assertEqual(again, out)


def minimal(task_id):
    d = json.loads((FIX / f"minimal_{task_id}.json").read_text())
    return d["answer"], scoring_rows(d["log"])


def scoring_rows(log):
    return fixture.rows_of(log)


class ScoringTests(unittest.TestCase):
    def strict(self, task_id, answer, rows):
        return scoring.score(TASKS[task_id], answer, rows)["strict"]["supported_complete"]

    def both(self, task_id, answer, rows):
        s = scoring.score(TASKS[task_id], answer, rows, GRAPH)
        return s["strict"]["supported_complete"], s["lenient"]["supported_complete"]

    def test_strict_positive_and_negative_fixtures_for_every_task(self):
        for task in fixture.TASKS:
            truth, rows = minimal(task["id"])
            self.assertTrue(self.strict(task["id"], truth, rows), task["id"])
            wrong = copy.deepcopy(truth)
            wrong["EXTRA"] = 1
            self.assertFalse(self.strict(task["id"], wrong, rows), task["id"] + " extra key")
            missing = {k: v for k, v in list(truth.items())[1:]} or {}
            self.assertFalse(self.strict(task["id"], missing, rows), task["id"] + " missing key")
            self.assertFalse(self.strict(task["id"], None, rows), task["id"] + " no answer")
            self.assertFalse(self.strict(task["id"], truth, []), task["id"] + " no evidence in the trace")  # support requirement cannot be passed without tool results

    def test_strict_rejects_short_and_wrong_names(self):
        truth, rows = minimal("nf_single_1")
        short = {"node": truth["node"].rsplit("/", 1)[1]}
        self.assertFalse(self.strict("nf_single_1", short, rows))
        self.assertFalse(self.strict("nf_single_1", {"node": "/nf/other/node"}, rows))

    def test_lenient_positive_cases(self):
        for tid in ("nf_single_1", "nf_single_2"):
            truth, rows = minimal(tid)
            full = truth["node"]
            for short in (full.rsplit("/", 1)[1], "/".join(full.split("/")[-2:])):
                self.assertEqual(self.both(tid, {"node": short}, rows), (False, True), (tid, short))
        truth, rows = minimal("nf_multi_1")  # nested keys
        short_keys = {"gains": {k.rsplit("/", 1)[1]: v for k, v in truth["gains"].items()}}
        self.assertEqual(self.both("nf_multi_1", short_keys, rows), (False, True))
        truth, rows = minimal("nf_multi_2")  # nested keys (topics) and values (nodes)
        short = {"upstream": {k.rsplit("/", 1)[1]: v.rsplit("/", 1)[1] for k, v in truth["upstream"].items()}}
        self.assertEqual(self.both("nf_multi_2", short, rows), (False, True))
        self.assertEqual(self.both("nf_single_1", minimal("nf_single_1")[0], minimal("nf_single_1")[1]), (True, True))  # a correct full name is supported in both

    def test_lenient_negative_cases(self):
        truth, rows = minimal("nf_amb_1")
        base = truth["node"].rsplit("/", 1)[1]
        self.assertEqual(self.both("nf_amb_1", {"node": base, "limit": truth["limit"]}, rows), (False, False))  # the short name is shared by two nodes: no leniency
        self.assertEqual(self.both("nf_amb_1", {"node": truth["node"], "limit": truth["limit"] + 1}, rows), (False, False))  # wrong value
        truth, rows = minimal("nf_single_1")
        self.assertEqual(self.both("nf_single_1", {"node": "/" + "/".join(truth["node"].split("/")[2:])}, rows), (False, False))  # absolute partial name: not relative
        other = minimal("nf_single_2")[0]["node"].rsplit("/", 1)[1]
        self.assertEqual(self.both("nf_single_1", {"node": other}, rows), (False, False))  # a different entity
        self.assertEqual(self.both("nf_single_1", {"node": truth["node"].rsplit("/", 1)[1], "extra": 1}, rows), (False, False))  # extra key
        truth, rows = minimal("nf_absent")
        short = truth["node"].rsplit("/", 1)[1]
        self.assertEqual(self.both("nf_absent", {"node": short, "running": False}, rows), (False, False))  # the required name is not in the graph: no leniency
        truth, rows = minimal("nf_multi_1")
        broken = {"gains": {k.rsplit("/", 1)[1]: v + 1 for k, v in truth["gains"].items()}}
        self.assertEqual(self.both("nf_multi_1", broken, rows), (False, False))  # short keys but wrong values
        self.assertEqual(self.both("nf_multi_1", truth, []), (False, False))  # no evidence

    def test_graph_has_unique_and_colliding_suffixes(self):
        from collections import Counter
        count = Counter(n["name"] for n in GRAPH["nodes"])
        self.assertTrue(any(v == 2 for v in count.values()) and any(v == 1 for v in count.values()))


class ArmTests(unittest.TestCase):
    def test_applied_answer_is_the_rewritten_one_and_the_original_is_kept(self):
        import namefix_arm

        class Recorder:
            def __init__(self):
                self.rows = []

            def add(self, kind, **values):
                self.rows.append(dict(kind=kind, **values))

        recorder = Recorder()
        task = TASKS["nf_multi_1"]
        arm = namefix_arm.make_arm(recorder, dict(env="namefix", task=task, ns="/nf"))
        names = list(task["answer"]["gains"])
        arm.tool_outputs.append({names[0]: "x", "nodes": names})
        arm.offered = {"final_answer"}
        short = {"gains": {n.rsplit("/", 1)[1]: 1 for n in names}}
        arm.execute_extra("final_answer", {"answer": short})
        original = next(r for r in recorder.rows if r["kind"] == "final_answer_original")["answer"]
        accepted = next(r for r in recorder.rows if r["kind"] == "final_answer_accepted")["answer"]
        self.assertEqual(original, short)
        self.assertEqual(accepted, {"gains": {n: 1 for n in names}})
        self.assertTrue(next(r for r in recorder.rows if r.get("event") == "namefix")["changed"])


if __name__ == "__main__":
    unittest.main()
