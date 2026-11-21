"""Arms of the Stage 1 exam (protocol: final_exam_draft_20261118/PROTOCOL_DRAFT.md section 9c). New file; no frozen dev file is edited.

  M             the steady loop = ablation FULL (12-tool menu + final_answer, soft errors with the strict pre-check) + the answer name fix.
  NO_MENU       M with the 47 stock tools + final_answer offered (ablation NO_MENU).
  NO_FINISH     M without the final_answer tool and its prompt line (ablation NO_FINISH).
  NO_ERRORTEXT  M with soft errors AND the strict pre-check both off: stock pydantic validation (coercions logged) and any validation/tool exception ends the episode
                (the union of the dev arms NO_PRECHECK and NO_SOFT_ERRORS; the combined arm is new and has no dev result).

Name fix (name-rewrite v2, adopted 2026-11-20): at the final_answer call the submitted answer is passed through namefix_rule. Both answers stay in the trace:
  event `final_answer_original`  the answer exactly as the model submitted it (raw)
  handler event `namefix`         whether the rule changed it, its events
  event `final_answer_accepted`   the REWRITTEN answer, which scorer v2.0 reads as the episode's answer
`score_both(task, events)` scores the same episode both ways, so "M" and "M without the name fix" come from the same requests; there is no separate run for the second.
The rewrite is applied in every arm that has a final_answer tool, so each ablation differs from M in one component only (NO_FINISH has no final_answer call: no rewrite).
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(STUDIES / "steady_loop_ablation_20261117"))
sys.path.insert(0, str(STUDIES / "name_fix_applied_20261117"))
sys.path.insert(0, str(STUDIES / "build_round1_20261115"))
import ablation_arms  # noqa: E402  (also puts the pilot and residual-failures studies on sys.path)
import answer_gate as ag  # noqa: E402
import namefix_rule as rule  # noqa: E402
import scorer_v2 as v2  # noqa: E402

harness = ablation_arms.harness
run_pilot = ablation_arms.run_pilot
ARMS = ["M", "NO_MENU", "NO_FINISH", "NO_ERRORTEXT"]
ABLATION_BASE = {"M": "FULL", "NO_MENU": "NO_MENU", "NO_FINISH": "NO_FINISH", "NO_ERRORTEXT": "FULL"}  # the dev arm each exam arm is built on


class ExamArm(ablation_arms.AblationArm):
    def __init__(self, variant, recorder, context, prompt_messages):
        assert variant in ARMS, variant
        super().__init__(ABLATION_BASE[variant], recorder, context, prompt_messages)
        self.name = self.variant = variant  # logged under the exam name; menu / finish switches key on NO_MENU / NO_FINISH, which keep their names
        self.task_text = context["task"]["request"]
        self.tool_outputs = []  # genuine tool results of this episode: the rewrite may only use names the model has seen

    def wrap_tools(self, tools):
        wrapped = super().wrap_tools(tools)
        if self.variant == "NO_ERRORTEXT":
            wrapped = [ablation_arms.NoPrecheckTool(name=t.name, description=t.description, args_schema=t.args_schema, arm=self, func=t.func, handle_tool_error=True,
                                                    handle_validation_error=self._stock_validation_text) for t in wrapped]
            for tool in wrapped:  # soft errors off: every exception ends the episode (same handlers as the dev arm NO_SOFT_ERRORS)
                tool.handle_validation_error = self._hard_validation(tool.name)
                tool.handle_tool_error = self._hard_tool_error(tool.name)
        return wrapped

    def execute(self, tool, arguments):
        output = super().execute(tool, arguments)
        self.tool_outputs.append(output)
        return output

    def final_answer_tool(self, arguments):
        answer = arguments.get("answer")
        if isinstance(answer, dict) and answer:
            started = time.perf_counter()
            allowed = ag.allowed_names(self.task_text, self.tool_outputs)
            events = []
            rewritten = rule.rewrite_answer(answer, allowed, events)
            self.recorder.add("final_answer_original", answer=answer)
            self.log("namefix", rule=rule.RULE_NAME, changed=rewritten != answer, events=events, ledger_size=len(allowed), cpu_seconds=round(time.perf_counter() - started, 5))
            arguments = {**arguments, "answer": rewritten}
        return super().final_answer_tool(arguments)


def score_both(task, events):
    """Scorer v2.0 on the accepted (rewritten) answer and on the answer as the model submitted it. Same episode, same tool results.
    Returns {"rewritten": score, "raw": score}; raw equals rewritten when no final_answer_original event exists (no rewrite happened or no finish call)."""
    rewritten = v2.score_events(task, events)
    originals = [e for e in events if e["kind"] == "final_answer_original"]
    if not originals:
        return {"rewritten": rewritten, "raw": rewritten}
    raw_events = [dict(e, answer=originals[-1]["answer"]) if e["kind"] == "final_answer_accepted" else e for e in events]
    return {"rewritten": rewritten, "raw": v2.score_events(task, raw_events)}


# ------------------------------------------------------------------ MT: the MetaTool mechanism, ported from the released source
# Label everywhere: "MetaTool mechanism ported from the released source (echo planning tool + prompt), not the original package."
# Source (read 2026-11-14, anonymized release anonymous.4open.science/r/uh_bot_v1_sim-BDB1, files MetaTool_prompts.py and MetaTool_robot_brain_tools.py; recorded in
# Claude outputs/ROSA_small_model_harness_pilot_build.md, row M0): a LangChain tool `supertool(input_str, generated_instruction_sequence)` that returns generated_instruction_sequence
# unchanged, plus the prompt instruction below, on a standard ROSA AgentExecutor with the stock tools. This arm is exactly that on top of the stock arm S0 (stock prompt, stock executor, 47 tools).
# Differences from the release, all deliberate and recorded: (1) the release's task-specific movement/navigation prompt lines are for its own robot and are left out; (2) the tool's
# description text is the pilot's wording (harness.EXTRA_TOOLS["supertool"]): the released description text was not available verbatim in this repository; (3) the code itself was not
# downloaded or run (unvetted code, owner decision), so the port rests on the recorded description; (4) the release used its own LLM backends, here the same local models as every arm.
MT_LINE = ("system", harness.M0_LINE[1])  # "Always use supertool() to think and generate a plan for the sequence of tool execution, then use that plan to execute the tools in proper order."


class MTArm(run_pilot.StockArm):
    """S0 (stock prompt, stock executor, stock tools) + the echo planning tool and the MetaTool prompt line. Nothing else changes; the plan is not executed or enforced."""
    def __init__(self, recorder):
        super().__init__("S0", recorder)
        self.name = "MT"
        self.prompt_messages = list(self.prompt_messages) + [MT_LINE]
        self.supertool_calls = 0

    def wrap_tools(self, tools):
        from langchain_core.tools import StructuredTool
        description, args_model = harness.EXTRA_TOOLS["supertool"]
        def supertool(input_str: str, generated_instruction_sequence: str) -> str:
            self.supertool_calls += 1
            self.recorder.add("handler", handler="MT", event="supertool_call", number=self.supertool_calls, plan_chars=len(generated_instruction_sequence))
            return generated_instruction_sequence  # the released tool returns its plan argument unchanged
        return list(tools) + [StructuredTool(name="supertool", description=description, args_schema=args_model, func=supertool)]


def make_arm(variant, recorder, context):
    if variant == "MT":
        return MTArm(recorder)
    return ExamArm(variant, recorder, context, run_pilot.prompt_for("A1"))
