"""Tests of the Forge queue adapter row builder on a saved gate episode (no Forge, no ROS, no Ollama). From the repository root:
  uv run python -m unittest discover -s research/studies/exam_arms_20261121/tests -p "test_run_forge.py" -v
Fixture: the lfm3:1.7b u3 episode of the 2026-11-21 Forge smoke gate: one HTTP non-200 response (no usage) among 11 requests."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import run_forge as F  # noqa: E402

DIRECTORY = HERE / "forge_fixture" / "007-u3-Forge-s1"
ATTEMPT = dict(directory=DIRECTORY.name, returncode=0, error=None, seconds=41.0, cell=dict(env="stage3", task="u3", arm="F", model="lfm3:1.7b", seed=1, temperature=0.7))


class ForgeRowTests(unittest.TestCase):
    def setUp(self):
        self.row = F.episode_row("exam", "block_0001", DIRECTORY, ATTEMPT)

    def test_row_has_the_queue_fields_and_names_the_arm_f(self):
        for key in ("run_id", "task", "arm", "model", "seed", "supported_complete", "llm_requests", "input_tokens", "output_tokens", "native_ops", "wall_seconds", "aborts", "answer", "trace_hash"):
            self.assertIn(key, self.row)
        self.assertEqual((self.row["arm"], self.row["task"], self.row["model"]), ("F", "u3", "lfm3:1.7b"))
        self.assertTrue(self.row["supported_complete"])  # scorer v2.0 on the saved episode (supported in the gate)

    def test_missing_usage_stays_null_is_counted_and_marks_a_lower_bound(self):
        self.assertEqual(self.row["llm_requests"], 11)
        self.assertEqual(len(self.row["usage_per_request"]), 11)
        self.assertEqual(self.row["usage_per_request"].count(None), 1)
        self.assertEqual(self.row["usage_missing_requests"], 1)
        self.assertTrue(self.row["token_totals_lower_bound"])
        known = [u for u in self.row["usage_per_request"] if u]
        self.assertEqual(self.row["input_tokens"], sum(u["input"] for u in known))
        self.assertEqual(self.row["exposure"]["non_200_responses"], 1)

    def test_no_write_tool_in_the_episode(self):
        self.assertEqual(self.row["exposure"]["write_tool_calls"], 0)

    def test_missing_interpreter_stops_with_a_clear_message(self):
        old = os.environ.get("ROSA_FORGE_PYTHON")
        os.environ["ROSA_FORGE_PYTHON"] = "/nonexistent/forge/bin/python"
        try:
            with self.assertRaises(RuntimeError) as caught:
                F.forge_python()
            self.assertIn("forge-guardrails==0.10.1", str(caught.exception))
        finally:
            if old is None:
                del os.environ["ROSA_FORGE_PYTHON"]
            else:
                os.environ["ROSA_FORGE_PYTHON"] = old

    def test_iteration_limit_error_maps_to_the_phrase_the_queue_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / DIRECTORY.name
            directory.mkdir()
            lines = (DIRECTORY / "trace.jsonl").read_text().splitlines()
            events = [json.loads(l) for l in lines]
            for e in events:
                if e["kind"] == "episode_end":
                    e["error"] = "MaxIterationsError('Workflow exceeded max_iterations')"
                    e["answer"] = None
            (directory / "trace.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
            row = F.episode_row("exam", "b", directory, ATTEMPT)
            self.assertIn("iteration limit", row["aborts"])
            sys.path.insert(0, str(HERE.parents[1] / "final_exam_draft_20261118" / "exam_queue"))
            import queue_core
            self.assertEqual(queue_core.ending_class(row), "iteration_cap")


if __name__ == "__main__":
    unittest.main()
