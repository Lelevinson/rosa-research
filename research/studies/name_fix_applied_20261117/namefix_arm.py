"""Applied name-fix arm: C1 (round 1's control arm, gate/nudge/list OFF) whose accepted final answer is the output of name-rewrite rule v2 (namefix_rule.py).
The model, prompt, tools, requests and evidence are unchanged; the rewrite is post-model, at the final_answer call. Both answers stay in the trace:
  `final_answer_original`  the answer exactly as the model submitted it
  handler event `namefix`  the rule's events (rewrite / reject_ambiguous / reject_never_seen / collision), whether the answer changed, the CPU time of the rule
  `final_answer_accepted`  the SUBMITTED answer (the rewritten one), which scorer v2.0 reads as the episode's answer
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDIES / "build_round1_20261115"))
import answer_gate as ag  # noqa: E402
import namefix_rule as rule  # noqa: E402
import round1_harness as r1  # noqa: E402  (also puts the pilot study on sys.path)


class NameFixArm(r1.Round1Arm):
    def __init__(self, recorder, context, prompt_messages):
        super().__init__("C1", recorder, context, prompt_messages)  # exactly round 1's control
        self.name = "NAMEFIX"

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


def make_arm(recorder, context):
    return NameFixArm(recorder, context, r1.run_pilot.prompt_for("A1"))
