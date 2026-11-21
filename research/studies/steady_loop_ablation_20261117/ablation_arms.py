"""Steady-loop ablation arms (protocol: research/decisions/2026-11-17-steady-loop-ablation-protocol.md, SHA-256 755139de...). Read that protocol first.

Base = pilot arm C1 (`small_model_harness_20261115/harness.py`, class Arm built as "C1"), unchanged:
  12 domain tools + final_answer, errors returned as tool messages, strict schema pre-check before pydantic, final_answer + its prompt line + one invalid-answer retry,
  observation-only guard (write tools hidden AND blocked at execution). Round-1 gate/nudge/list, round-2 sweep/rewrite and H2 are off in every arm.

Arms (each is C1 with exactly ONE component removed; FULL is C1 itself):
  FULL            no change (the fresh concurrent control).
  NO_SOFT_ERRORS  the episode ends on any validation/tool exception that C1 would hand back as a tool message. Which exceptions: the strict pre-check, pydantic validation,
                  a tool that raises, a blocked write, a tool that is not offered. NOT changed: results that are not exceptions (a dict with "error", textual failures), and the
                  finish behaviour: the one-retry message of final_answer for an empty answer stays a returned message (it is C1's finish logic, not a tool error).
                  No exception text is replaced: the episode simply ends (error recorded as `HardToolError: <the text C1 would have returned>`).
  NO_PRECHECK     only the custom strict pre-validation (`PilotTool._parse_input`) is removed: the stock pydantic schema of each tool validates as usual and its errors are returned
                  as tool messages exactly as in C1. Coercions done by pydantic (given value != parsed value or type) and stock validation errors are logged as handler events.
  NO_MENU         all 47 stock tools + final_answer (48 offered), original schemas and descriptions; write tools stay blocked at execution (blocked_write_tool events).
  NO_FINISH       no final_answer tool offered and no "call the final_answer tool" prompt line; C1's executor and normal termination (an answer without tool calls ends the episode);
                  the free-text answer is scored by scorer v2.0 (last complete JSON object / unwrap) with no retry and no format instruction. This bundles the tool with its prompt line.
"""
import sys
from pathlib import Path

from langchain_core.tools import ToolException

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(STUDIES / "small_model_harness_20261115"))
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
import harness  # noqa: E402
import run_pilot  # noqa: E402

ARMS = ["FULL", "NO_SOFT_ERRORS", "NO_PRECHECK", "NO_MENU", "NO_FINISH"]
FINISH_RETRY_PREFIX = "final_answer needs a non-empty JSON object"  # the message of C1's one invalid-answer retry (harness.Arm.final_answer_tool)


class HardToolError(Exception):
    """Raised instead of returning an error message to the model (arm NO_SOFT_ERRORS); it ends the episode."""


class NoPrecheckTool(harness.PilotTool):
    """PilotTool without the custom strict pre-validation: the stock pydantic schema validates; coercions are logged."""
    def _parse_input(self, tool_input, tool_call_id=None):
        parsed = super(harness.PilotTool, self)._parse_input(tool_input, tool_call_id)  # StructuredTool/BaseTool: pydantic only
        if isinstance(tool_input, dict) and isinstance(parsed, dict):
            for key, given in tool_input.items():
                if key in parsed and (type(parsed[key]) is not type(given) or parsed[key] != given):
                    self.arm.log("coercion", tool=self.name, field=key, given=given, parsed=parsed[key])
        return parsed


class AblationArm(harness.Arm):
    def __init__(self, variant, recorder, context, prompt_messages):
        assert variant in ARMS, variant
        super().__init__("C1", recorder, context, prompt_messages)  # exactly the base arm
        self.name, self.variant = variant, variant
        self.stock_tool_names = []
        if variant == "NO_FINISH":
            self.prompt_messages = list(prompt_messages)  # the base prompt without the final_answer line

    # ---------------- tools offered
    def base_menu(self):
        if self.variant == "NO_MENU":
            return list(self.stock_tool_names) + ["final_answer"]
        if self.variant == "NO_FINISH":
            return list(harness.DOMAIN_TOOLS)
        return super().base_menu()

    # ---------------- tool wrapping
    def wrap_tools(self, tools):
        self.stock_tool_names = [t.name for t in tools]
        wrapped = super().wrap_tools(tools)
        if self.variant == "NO_PRECHECK":
            wrapped = [NoPrecheckTool(name=t.name, description=t.description, args_schema=t.args_schema, arm=self, func=t.func, handle_tool_error=True,
                                      handle_validation_error=self._stock_validation_text) for t in wrapped]
        if self.variant == "NO_SOFT_ERRORS":
            for tool in wrapped:
                tool.handle_validation_error = self._hard_validation(tool.name)
                tool.handle_tool_error = self._hard_tool_error(tool.name)
        return wrapped

    def _stock_validation_text(self, error):
        text = self._pydantic_text(error)
        self.log("stock_validation_error", message=text)
        return text

    def _hard_validation(self, tool_name):
        def handler(error):
            self.log("episode_ended_by_error", tool=tool_name, error_kind="validation", message=str(error)[:500])
            raise HardToolError(self._pydantic_text(error))
        return handler

    def _hard_tool_error(self, tool_name):
        def handler(error):
            message = str(error)
            if tool_name == "final_answer" and message.startswith(FINISH_RETRY_PREFIX):
                return message  # C1's finish retry is finish behaviour, not a tool error
            self.log("episode_ended_by_error", tool=tool_name, error_kind="tool_exception", message=message[:500])
            raise HardToolError(message)
        return handler


def make_arm(variant, recorder, context):
    return AblationArm(variant, recorder, context, run_pilot.prompt_for("A1"))
