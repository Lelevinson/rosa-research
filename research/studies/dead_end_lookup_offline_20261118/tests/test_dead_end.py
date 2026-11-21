"""Tests on a synthetic graph. uv run python -m unittest discover -s research/studies/dead_end_lookup_offline_20261118/tests"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dead_end_lookup as D  # noqa: E402

ITEMS = [dict(kind="node", name="/e1h/alder/pewter", relation=None, node=None), dict(kind="node", name="/e1h/basalt/sorrel", relation=None, node=None),
         dict(kind="topic", name="/e1h/pewter_t", relation="published by node", node="/e1h/alder/pewter"),
         dict(kind="service", name="/e1h/reset", relation="provided by node", node="/e1h/basalt/sorrel"), dict(kind="parameter", name="mode", relation="of node", node="/e1h/basalt/sorrel")]


def call(tool, entity, text, output=None, harness=False):
    return dict(tool=tool, entity=entity, text=text, output=output if output is not None else text, harness_error=harness)


class SearchTests(unittest.TestCase):
    def test_root_namespace_is_not_a_segment(self):
        self.assertEqual(D.segments_of("/e1h/alder/pewter", "e1h"), ["alder", "pewter"])

    def test_whole_segment_match_not_substring(self):
        lines, _ = D.build_lines("/e1h/pew", "e1h", ITEMS)
        self.assertEqual(lines, [])
        lines, _ = D.build_lines("/e1h/sorrel", "e1h", ITEMS)
        self.assertEqual(lines, ["sorrel appears in: node /e1h/basalt/sorrel"])

    def test_relations_and_order_follow_graph_order(self):
        lines, _ = D.build_lines("/alder/pewter", "e1h", ITEMS)
        self.assertEqual(lines, ["alder appears in: node /e1h/alder/pewter", "pewter appears in: node /e1h/alder/pewter"])
        lines, _ = D.build_lines("/e1h/reset", "e1h", ITEMS)
        self.assertEqual(lines, ["reset appears in: service /e1h/reset (provided by node /e1h/basalt/sorrel)"])

    def test_parameter_key_matches_by_equality(self):
        lines, _ = D.build_lines("/mode", "e1h", ITEMS)
        self.assertEqual(lines, ["mode appears in: parameter mode (of node /e1h/basalt/sorrel)"])

    def test_line_cap_and_character_cap(self):
        items = [dict(kind="node", name=f"/e1h/x{i}/same", relation=None, node=None) for i in range(30)]
        lines, truncated = D.build_lines("/e1h/same", "e1h", items)
        self.assertEqual(len(lines), 10); self.assertTrue(truncated)
        long = [dict(kind="node", name="/e1h/" + "a" * 200 + f"/{i}/same", relation=None, node=None) for i in range(10)]
        lines, truncated = D.build_lines("/e1h/same", "e1h", long)
        self.assertTrue(truncated); self.assertLessEqual(sum(len(l) + 1 for l in lines), 600)

    def test_lookalike_rule(self):
        lines, _ = D.build_lines("/alder/pewter", "e1h", ITEMS)
        self.assertTrue(D.lookalike_lines("/alder/pewter", lines, ITEMS))
        self.assertFalse(D.lookalike_lines("/e1h/alder/pewter", lines, ITEMS))

    def test_dead_end_classes(self):
        self.assertEqual(D.dead_end_class(call("ros2_node_info", "/a", '{"error": "Unable to find node \'/a\'"}')), "a")
        self.assertEqual(D.dead_end_class(call("ros2_service_info", "/a", '{"error": ""}', {"error": ""})), "b")
        self.assertEqual(D.dead_end_class(call("ros2_topic_info", "/a", "")), "c")
        self.assertIsNone(D.dead_end_class(call("ros2_node_info", "/a", "Node name: a")))
        self.assertIsNone(D.dead_end_class(call("ros2_node_list", None, "not found")))
        self.assertIsNone(D.dead_end_class(call("ros2_node_info", "/a", "Tool failed: not found", harness=True)))

    def test_graph_has_it_and_needed(self):
        self.assertTrue(D.graph_has("/e1h/alder/pewter", "node", ITEMS)); self.assertFalse(D.graph_has("/e1h/alder/pewter", "topic", ITEMS))
        self.assertEqual(D.needed_entities(dict(support=[["text", "/a/b"], ["text", "std_srvs/srv/Trigger"], ["param", "/c/d", "m", 1], ["absent", "/z"]])), ["/a/b", "/c/d"])


if __name__ == "__main__":
    unittest.main()
