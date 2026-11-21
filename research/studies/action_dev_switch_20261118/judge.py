"""Task definitions and the success judge of PROTOCOL.md section 2. Pure Python (no ROS): the true pose is passed in by the runner, read by an independent node.
Only the true pose, the answer and (for R1) the known parameter value are used; the model's own state reports are never truth."""
import json
import math

TOLERANCE = 0.1            # radians, or position units for x and y
BACKGROUND_R = 69          # default value of /turtlesim background_r (fixed by the turtlesim package)

TASKS = {
    "S1": dict(kind="single", number=1, final_target=1.0, answer_keys=("heading",),
               text='Turn the turtle so that it faces heading 1.0 radians, then reply with the heading it ended with as {"heading": <number>}.'),
    "S2": dict(kind="single", number=2, final_target=-2.5, answer_keys=("heading",),
               text='Turn the turtle so that it faces heading -2.5 radians, then reply with the heading it ended with as {"heading": <number>}.'),
    "S3": dict(kind="single", number=3, final_target=4.0, answer_keys=("heading",),
               text='Turn the turtle so that it faces 4.0 radians, then reply with the heading it ended with as {"heading": <number>}.'),
    "R1": dict(kind="act_read", number=4, final_target=BACKGROUND_R / 100, answer_keys=("background_r", "heading"),
               text='Read the parameter background_r of the node /turtlesim, then turn the turtle to a heading equal to that value divided by 100 (in radians). '
                    'Reply with {"background_r": <number>, "heading": <number>}.'),
    "R2": dict(kind="act_read", number=5, final_target=1.2, answer_keys=("x", "y"),
               text='Turn the turtle so that it faces heading 1.2 radians, then reply with the turtle\'s position as {"x": <number>, "y": <number>}.'),
    "M1": dict(kind="two_step", number=6, final_target=2.8, answer_keys=("heading",),
               text='Turn the turtle to heading 0.5 radians, then to heading 2.8 radians (in that order). Reply with its final heading as {"heading": <number>}.'),
    "M2": dict(kind="two_step", number=7, final_target=0.8, answer_keys=("heading",),
               text='Turn the turtle to heading -1.5 radians, then to heading 0.8 radians (in that order). Reply with its final heading as {"heading": <number>}.'),
    "M3": dict(kind="two_step", number=8, final_target=2.5, answer_keys=("heading",),
               text='Turn the turtle to heading 1.0 radians. Then turn it a further 1.5 radians counter-clockwise from where it ended up (a new absolute heading). '
                    'Reply with its final heading as {"heading": <number>}.'),
}


def angle_error(a, b):
    return abs(math.atan2(math.sin(a - b), math.cos(a - b)))


def parse_answer(answer):
    """The answer object: a dict, or a JSON string of one; anything else is no answer."""
    if isinstance(answer, str):
        try:
            answer = json.loads(answer)
        except ValueError:
            return None
    return answer if isinstance(answer, dict) else None


def number(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def judge(task_id, answer, true_heading, true_x, true_y, still):
    """Returns dict(success, reasons). All conditions of the protocol's table must hold."""
    task = TASKS[task_id]
    reasons = []
    if not still:
        reasons.append("turtle not still at the end")
    if angle_error(true_heading, task["final_target"]) >= TOLERANCE:
        reasons.append(f"true heading {true_heading:.3f} not within {TOLERANCE} of target {task['final_target']}")
    obj = parse_answer(answer)
    if obj is None:
        reasons.append("no answer object")
        return dict(success=False, reasons=reasons)
    for key in task["answer_keys"]:
        if key not in obj or number(obj[key]) is None:
            reasons.append(f"answer lacks a numeric {key}")
    if reasons and any(r.startswith("answer lacks") for r in reasons):
        return dict(success=False, reasons=reasons)
    if "heading" in task["answer_keys"] and angle_error(number(obj["heading"]), true_heading) >= TOLERANCE:
        reasons.append("reported heading differs from the true heading")
    if task_id == "R1" and number(obj["background_r"]) != BACKGROUND_R:
        reasons.append("background_r is not 69")
    if task_id == "R2":
        if abs(number(obj["x"]) - true_x) >= TOLERANCE or abs(number(obj["y"]) - true_y) >= TOLERANCE:
            reasons.append("reported position differs from the true position")
    return dict(success=not reasons, reasons=reasons)
