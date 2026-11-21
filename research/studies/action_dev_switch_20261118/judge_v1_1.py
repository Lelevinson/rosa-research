"""Action judge v1.1. Use for prospective scoring or an explicit offline replay.

Pass the recorded episode ending so structured tool answers keep their original
semantics. The frozen v1 module still owns the task bank and verdict rules.
"""

import json
import re

from judge import judge as judge_v1

JUDGE_VERSION = "action-judge-v1.1"


def parse_text_answer(text):
    """Apply the read scorer v2.0 last-object and singleton-wrapper rule."""
    decoder = json.JSONDecoder()
    last_object = None
    end_of_last = -1
    for match in re.finditer(r"\{", text):
        if match.start() < end_of_last:
            continue
        try:
            value, length = decoder.raw_decode(text[match.start():])
        except ValueError:
            continue
        last_object = value
        end_of_last = match.start() + length
    if last_object is not None and list(last_object) == ["answer"]:
        inner = last_object["answer"]
        if isinstance(inner, dict):
            return inner
    return last_object


def judge(task_id, answer, true_heading, true_x, true_y, still, *, ending):
    """Judge a terminal response using its frozen runner ending value."""
    if ending == "text" and isinstance(answer, str):
        answer = parse_text_answer(answer)
    return judge_v1(task_id, answer, true_heading, true_x, true_y, still)
