"""The offline lossless checker must be able to FAIL: deliberately broken renderings are flagged. From the repository root:
  uv run python -m unittest discover -s research/studies/canonical_render_20261118/tests -v"""
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "candidate_counts_20261118"))
import offline_check as O  # noqa: E402
import render_core as R  # noqa: E402

TEXT = "Type: t\n\nNode name: alpha\nNode namespace: /ns1\nEndpoint type: PUBLISHER\n"


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.good = R.render_result({"k": TEXT})

    def test_good_rendering_passes(self):
        self.assertEqual(O.lossless_violations({"k": TEXT}, self.good), [])

    def test_each_mutation_is_flagged(self):
        mutations = {
            "dropped line": {"k": self.good["k"].replace("Endpoint type: PUBLISHER\n", "")},
            "wrong full name": {"k": self.good["k"].replace("/ns1/alpha", "/ns1/beta")},
            "changed value": {"k": self.good["k"].replace("alpha", "alpho", 1)},
            "reordered lines": {"k": "Node namespace: /ns1\nNode name: alpha\nType: t\nEndpoint type: PUBLISHER\n"},
            "shape change": {"k": [1]},
        }
        for name, rendered in mutations.items():
            original = {"k": [1, 2]} if name == "shape change" else {"k": TEXT}
            self.assertTrue(O.lossless_violations(original, rendered), name)


if __name__ == "__main__":
    unittest.main()
