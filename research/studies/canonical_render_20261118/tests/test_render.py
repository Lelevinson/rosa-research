"""Tests of the canonical renderer on small invented texts (no ROS, no model). From the repository root:
  uv run python -m unittest discover -s research/studies/canonical_render_20261118/tests -v
The texts imitate common ROS 2 CLI shapes but the tests do not depend on any tool name."""
from collections import Counter
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import render_core as R  # noqa: E402

ENDPOINTS = ("Type: t/msg/String\n\nPublisher count: 2\n\nNode name: alpha\nNode namespace: /ns1\nEndpoint type: PUBLISHER\nQoS profile:\n  Reliability: RELIABLE\n\n"
             "Node name: beta\nNode namespace: /\nEndpoint type: PUBLISHER\n\nSubscription count: 0\n\n")


def lines(text):
    return [" ".join(line.split()) for line in text.split("\n") if line.strip()]


class ParserTests(unittest.TestCase):
    def test_line_classes(self):
        self.assertEqual(R.classify("  Reliability: RELIABLE")[0], R.KEY_VALUE)
        self.assertEqual(R.classify("Subscribers:")[0], R.HEADER)
        self.assertEqual(R.classify("/ns/topic: std_msgs/msg/String")[:2], (R.KEY_VALUE, "/ns/topic"))
        self.assertEqual(R.classify("/plant32/anvil")[0], R.BARE)
        self.assertEqual(R.classify("http://host/x")[0], R.BARE)          # ":/" is not ": "
        self.assertEqual(R.classify("\tKey: v")[0], R.BARE)               # a tab in the indentation: not read
        self.assertEqual(R.classify("Integer value is: 74")[1:], ("Integer value is", "74"))

    def test_depths_follow_indentation(self):
        self.assertEqual(R.depths([0, 2, 2, 4, 2, 0, 3]), [0, 1, 1, 2, 1, 0, 1])


class RenderTests(unittest.TestCase):
    def test_two_blocks_each_get_their_own_full_name_and_root_namespace_works(self):
        out = R.render_text(ENDPOINTS, Counter())
        self.assertIn("Node full name: /ns1/alpha", out)
        self.assertIn("Node full name: /beta", out)
        self.assertEqual(out.count("full name"), 2)

    def test_lossless_line_level_and_only_derived_lines_added(self):
        out = R.render_text(ENDPOINTS, Counter())
        original, rendered = lines(ENDPOINTS), lines(out)
        position = 0
        for line in original:                       # subsequence check
            position = rendered.index(line, position) + 1
        extra = [line for line in rendered if line not in original]
        self.assertEqual(extra, ["Node full name: /ns1/alpha", "Node full name: /beta"])

    def test_blank_lines_dropped_indentation_normalised_trailing_newline_kept(self):
        out = R.render_text("A: 1\n\n\n   B:\n        C: 2\n", Counter())
        self.assertEqual(out, "A: 1\n  B:\n    C: 2\n")   # R3: a deeper indentation is a deeper level, whatever the width

    def test_idempotent(self):
        once = R.render_text(ENDPOINTS, Counter())
        self.assertEqual(R.render_text(once, Counter()), once)

    def test_pass_through_is_byte_identical(self):
        for text in ["/plant32/anvil", "  next_node", "2.04 KB", "", "Unable to find node 'x'\n", "plain words only\n\n\n"]:
            self.assertIs(R.render_text(text, Counter()), text, text)

    def test_no_pair_means_no_added_line(self):
        for text in ["Node name: a\nOther: b\n", "Node namespace: /x\nOther: b\n",
                     "Node name: a\nNode namespace: relative\n", "Node name: /abs\nNode namespace: /x\n",
                     "Node name: a\nNode name: b\nNode namespace: /x\n"]:
            self.assertNotIn("full name", R.render_text(text, Counter()), text)

    def test_generic_prefix_and_case_variants_without_naming_a_tool(self):
        self.assertIn("Full name: /a/b", R.render_text("Name: b\nNamespace: /a\n", Counter()))
        self.assertIn("Action full name: /a/b", R.render_text("Action name: b\nAction namespace: /a\n", Counter()))
        self.assertIn("full name: /a/b", R.render_text("name: b\nnamespace: /a\n", Counter()).replace("Full name", "full name"))

    def test_blank_line_separates_blocks_so_two_pairs_are_not_ambiguous(self):
        out = R.render_text("name: a\nnamespace: /x\n\nname: b\nnamespace: /y\n", Counter())
        self.assertIn("Full name: /x/a", out)   # R6: an empty prefix gives the key `Full name`
        self.assertIn("Full name: /y/b", out)

    def test_existing_full_name_line_is_not_duplicated(self):
        text = "Node name: a\nNode namespace: /x\nNode full name: /x/a\n"
        self.assertEqual(R.render_text(text, Counter()).count("full name"), 1)


class ContainerTests(unittest.TestCase):
    def test_containers_keys_and_non_strings_are_unchanged(self):
        value = {"/ns/topic": ENDPOINTS, "nodes": ["/a/b", "/a/c"], "total": 3, "ok": True, "none": None, "error": "Unable to find node 'x'\n"}
        out = R.render_result(value)
        self.assertEqual(list(out), list(value))
        self.assertEqual((out["nodes"], out["total"], out["ok"], out["none"], out["error"]), (value["nodes"], 3, True, None, value["error"]))
        self.assertNotEqual(out["/ns/topic"], ENDPOINTS)

    def test_stats_count_rendered_and_passed_leaves(self):
        stats = Counter()
        R.render_result({"a": ENDPOINTS, "b": "/x/y", "c": ["z"]}, stats)
        self.assertEqual((stats["leaves_rendered"], stats["leaves_passed_through"], stats["derived_lines"]), (1, 2, 2))


if __name__ == "__main__":
    unittest.main()
