"""Finish-tool split arms (protocol: PROTOCOL.md in this folder, hash in PROTOCOL.sha256). Read the protocol first.

Base = pilot arm C1 (`small_model_harness_20261115/harness.py`), unchanged: 12 domain tools + final_answer, errors returned as tool messages, strict schema pre-check,
observation-only guard. Arms differ only in how the episode is told to finish:
  FULL       C1 itself: final_answer tool offered AND the line FINAL_ANSWER_LINE in the prompt.
  TOOL_ONLY  final_answer tool offered (same schema, description and one-retry behaviour); the finish line is absent (prompt = base A1 prompt only).
  LINE_JSON  no final_answer tool; a new system line asks for a JSON object only. Same position in the prompt as FINAL_ANSWER_LINE. The episode ends on the first response without
             a tool call and is scored by scorer v2.0 free-text extraction (no retry).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(STUDIES / "small_model_harness_20261115"))
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
import harness  # noqa: E402
import run_pilot  # noqa: E402

ARMS = ["FULL", "TOOL_ONLY", "LINE_JSON"]
JSON_ONLY_LINE = ("system", "When you have the answer, reply with the answer as a JSON object only, using exactly the keys the task asks for. Do not write anything else.")


class SplitArm(harness.Arm):
    def __init__(self, variant, recorder, context, prompt_messages):
        assert variant in ARMS, variant
        super().__init__("C1", recorder, context, prompt_messages)  # exactly the base arm (its prompt ends with FINAL_ANSWER_LINE)
        self.name, self.variant = variant, variant
        assert self.prompt_messages[-1] == harness.FINAL_ANSWER_LINE
        if variant == "TOOL_ONLY":
            self.prompt_messages = list(prompt_messages)  # base prompt without the finish line
        elif variant == "LINE_JSON":
            self.prompt_messages = list(prompt_messages) + [JSON_ONLY_LINE]

    def base_menu(self):
        if self.variant == "LINE_JSON":
            return list(harness.DOMAIN_TOOLS)  # no final_answer
        return super().base_menu()


def make_arm(variant, recorder, context):
    return SplitArm(variant, recorder, context, run_pilot.prompt_for("A1"))
