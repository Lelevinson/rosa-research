"""Stage 2 judge entry point: `judge_exam.judge` (action judge v1.2 plus answer-form normalisation, unchanged) and the claim audit, in one call. New file; no judge file is edited.
`contract` is an `ArrivalContract` (claim_counter). For development tasks it comes from the dev task bank; for held-out tasks the custodian's bridge supplies it."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "action_dev_switch_20261118"))
import claim_counter  # noqa: E402
import judge as dev_judge  # noqa: E402
import judge_exam  # noqa: E402

JUDGE_VERSION = judge_exam.JUDGE_VERSION + "+claim-audit"


def dev_contract(task_id):
    task = dev_judge.TASKS[task_id]
    if "heading" in task["answer_keys"]:
        return claim_counter.ArrivalContract("heading", task["final_target"], dev_judge.TOLERANCE)
    return claim_counter.ArrivalContract(None)


def judge(task_id, answer, true_state, *, ending, trace, contract=None):
    """true_state = dict(heading, x, y, still) from the independent reader. Returns the v1.2 verdict plus `claim_audit` and `judge_version`."""
    verdict = judge_exam.judge(task_id, answer, true_state["heading"], true_state["x"], true_state["y"], true_state["still"], ending=ending, trace=trace)
    contract = contract or dev_contract(task_id)
    audit = claim_counter.audit(contract, judge_exam.normalise(answer), true_state["heading"], true_state["still"])
    return dict(verdict, claim_audit=audit, judge_version=JUDGE_VERSION)
