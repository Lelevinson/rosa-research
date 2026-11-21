"""Live arms for the repeat-finish nudge study (protocol: PROTOCOL.md, hash in PROTOCOL.sha256). Read the protocol first.

FULL  = pilot arm C1 unchanged, plus silent logging of identical repeats.
NUDGE = FULL, and on an identical repeat (at most 2 per episode) the result gets one fixed line appended.

Identical repeat: a successful call whose tool name, arguments AND result equal those of an earlier successful call in the episode.
Detection is the same code in both arms; only the output differs. No LLM call, nothing hidden or rewritten.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDIES / "small_model_harness_20261115"))
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
import harness  # noqa: E402
import run_pilot  # noqa: E402

ARMS = ["FULL", "NUDGE"]
MENU_TOOLS = set(harness.DOMAIN_TOOLS)  # the 12 menu tools; final_answer never goes through execute()
NUDGE_LINE = ("Note: this call repeated an earlier call and returned the same result. "
              "If you already have what the task asks for, call final_answer now; otherwise try a different call.")
MAX_FIRES = 2


def canonical(value):
    return json.dumps(value, sort_keys=True, default=str)


def with_nudge(output):
    """The result plus the fixed line. A string gets the line after a newline; a dict gets one extra key at the end (its own keys are unchanged)."""
    if isinstance(output, dict):
        key = "note" if "note" not in output else "note_repeat"
        return {**output, key: NUDGE_LINE}
    return f"{output}\n{NUDGE_LINE}"


def strip_nudge(output):
    """Inverse of with_nudge, for the checks that recompute detection from a trace."""
    if isinstance(output, dict):
        return {k: v for k, v in output.items() if v != NUDGE_LINE}
    if isinstance(output, str) and output.endswith("\n" + NUDGE_LINE):
        return output[: -len("\n" + NUDGE_LINE)]
    return output


class NudgeArm(harness.Arm):
    def __init__(self, variant, recorder, context, prompt_messages):
        assert variant in ARMS, variant
        super().__init__("C1", recorder, context, prompt_messages)  # exactly the base arm
        self.name, self.variant = variant, variant
        self.successful_calls = set()  # (tool, arguments, result) of every earlier successful call
        self.repeats, self.fires = 0, 0

    def execute(self, tool, arguments):
        output = super().execute(tool, arguments)  # raises for errors and blocked tools: those are never successful calls
        if tool.name not in MENU_TOOLS or harness.failed_items(tool.name, arguments, output):
            return output
        key = (tool.name, canonical(arguments), canonical(output))
        if key not in self.successful_calls:
            self.successful_calls.add(key)
            return output
        self.repeats += 1
        fire = self.variant == "NUDGE" and self.fires < MAX_FIRES
        self.log("identical_repeat", request=self.request_count, tool=tool.name, args=arguments, repeat_number=self.repeats, fired=fire)
        if not fire:
            return output
        self.fires += 1
        return with_nudge(output)


def make_arm(variant, recorder, context):
    return NudgeArm(variant, recorder, context, run_pilot.prompt_for("A1"))
