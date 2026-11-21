"""Ending class of a stock-executor validation abort (freeze prep 9d-4). No ROS, no Ollama."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import exam_tables  # noqa: E402
import queue_core as Q  # noqa: E402

PYDANTIC_ABORT = "1 validation error for ros2_node_list\nblacklist\n  Input should be a valid list [type=list_type, input_value={}, input_type=dict]"


class EndingClassTests(unittest.TestCase):
    def test_stock_validation_abort_has_its_own_class(self):
        row = dict(llm_requests=1, aborts=[PYDANTIC_ABORT], answer=None, supported_complete=False)
        self.assertEqual(Q.ending_class(row), "validation_abort")

    def test_hard_tool_error_of_the_no_errortext_arm_is_the_same_class(self):
        row = dict(llm_requests=3, aborts=["HardToolError: Invalid arguments"], answer=None)
        self.assertEqual(Q.ending_class(row), "validation_abort")

    def test_other_aborts_stay_backend_error_and_timeout_wins(self):
        self.assertEqual(Q.ending_class(dict(llm_requests=2, aborts=["ResponseError: 500"], answer=None)), "backend_error")
        self.assertEqual(Q.ending_class(dict(llm_requests=2, aborts=["900-second episode timeout", PYDANTIC_ABORT], answer=None)), "timeout")

    def test_counted_with_the_capped_totals_and_shown_as_a_row(self):
        self.assertIn("validation_abort", exam_tables.CAPPED)
        self.assertIn("validation_abort", exam_tables.CLASSES)


if __name__ == "__main__":
    unittest.main()
