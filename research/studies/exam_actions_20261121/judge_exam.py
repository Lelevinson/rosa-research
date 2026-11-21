"""Exam wrapper around the unchanged action judge v1.2 (action_dev_switch_20261118/judge_v1_2.py, tracked since 2026-11-21): it normalises the FORM of the final answer so that the same facts score
identically whether they arrive as an object, an object wrapped in {"answer": ...}, a JSON string, a wrapped JSON string or prose around a JSON object. v1.2 itself does not unwrap a
wrapped STRUCTURED answer (replay on the 128 dev episodes: 0 of 126 succeed in that form against 116 in every other form; see REPORT.md). The judge files are not edited; this module is new.
Not frozen. The judge's verdict rules, tolerances and sequence checks are v1.2's."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "action_dev_switch_20261118"))
import judge_v1_1 as v11  # noqa: E402
import judge_v1_2 as v12  # noqa: E402

JUDGE_VERSION = "action-judge-v1.2+form-normalisation"


def normalise(answer):
    """The answer object (dict) or None: a string is read with the read scorer's last-object rule; a singleton {"answer": dict} wrapper is removed (once)."""
    if isinstance(answer, str):
        answer = v11.parse_text_answer(answer)
    if isinstance(answer, dict) and list(answer) == ["answer"]:
        inner = answer["answer"]
        if isinstance(inner, str):
            inner = v11.parse_text_answer(inner)
        if isinstance(inner, dict):
            answer = inner
    return answer if isinstance(answer, dict) else None


def judge(task_id, answer, true_heading, true_x, true_y, still, *, ending, trace):
    """v1.2 on the normalised answer. The ending passed on is "final_answer" when an object remains, so v1.2 does not apply the text rule a second time."""
    obj = normalise(answer)
    return v12.judge(task_id, obj, true_heading, true_x, true_y, still, ending="final_answer" if obj is not None else ending, trace=trace)
