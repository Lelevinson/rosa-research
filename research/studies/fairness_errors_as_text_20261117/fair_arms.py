"""Fairness test arms (2026-11-17): the ORIGINAL ROSA executor and all 47 stock tools, with ONE change: a failed tool call is returned to the model as a tool message.

  E0  verbatim stock ROSA prompt (pilot arm S0's prompt, Stage 1 'A_orig')            + errors as text
  E1  the deconflicted prompt (pilot arm A1's prompt, Stage 3b)                        + errors as text

"Errors as text" (frozen in PROTOCOL.md): a tool call that fails by (a) argument validation (pydantic ValidationError of the tool's own stock schema) or (b) an
exception raised by the tool is not allowed to end the episode; the model receives the message as the tool result and the loop continues.
  validation error -> the text of the error exactly as pydantic prints it
  tool exception   -> "<ExceptionType>: <message>"
Nothing else changes: no argument pre-check, no short menu, no finish tool, no extra argument rules, same schemas and descriptions, same AgentExecutor
(handle_parsing_errors=True as in S0/A1, 40 iterations). Errors that are not tool calls (Ollama backend errors, a malformed tool-call from the model's output) are not tool
errors and still end the episode exactly as before.
"""
import sys
from pathlib import Path

from langchain_core.tools import ToolException

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(STUDIES / "small_model_harness_20261115"))
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
import run_pilot  # noqa: E402

ARMS = {"E0": "S0", "E1": "A1"}  # arm -> the pilot arm whose prompt it uses


def make_returning_errors(tool, recorder=None):
    """Same tool object, with its failures turned into a returned message (and one `tool_error_returned` trace event per failure). Schema, name and description are untouched."""
    original = tool.func
    if original is not None and not getattr(original, "_errors_as_text", False):
        def guarded(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            except ToolException:
                raise
            except Exception as error:  # a tool that raises must not end the episode
                raise ToolException(f"{type(error).__name__}: {error}") from error
        guarded._errors_as_text = True
        tool.func = guarded

    def returned(kind, text):
        if recorder is not None:
            recorder.add("tool_error_returned", tool=tool.name, error_kind=kind, text=text[:2000])
        return text
    tool.handle_validation_error = lambda error: returned("validation", str(error))
    tool.handle_tool_error = lambda error: returned("tool_exception", str(error))
    return tool


class ErrorsAsTextArm(run_pilot.StockArm):
    """Stock arm (stock tools, stock AgentExecutor) whose tools return their failures as text."""
    def __init__(self, name, recorder):
        assert name in ARMS, name
        super().__init__(ARMS[name], recorder)  # prompt of S0 or A1, nothing else from the pilot arm
        self.name = name

    def wrap_tools(self, tools):
        return [make_returning_errors(t, self.recorder) for t in tools]


def make_arm(name, recorder, context):
    return ErrorsAsTextArm(name, recorder)
