"""Action judge v1.2 for dev replay and prospective action pools.

Custodians provide a task contract and the independent final-state/answer
verdict. Pass trusted events in chronological order, with dispatch and
completion recorded by the transport, not extracted from model text.
"""
from dataclasses import dataclass
from math import isfinite
import re
from typing import Callable

from judge import TASKS, TOLERANCE, angle_error
from judge_v1_1 import judge as judge_v1_1

JUDGE_VERSION = "action-judge-v1.2"


@dataclass(frozen=True)
class Read:
    source: tuple[str, ...]
    value: object
    decision: int | None = None


@dataclass(frozen=True)
class Dispatch:
    goal_id: str
    action: str
    target: tuple[float, ...]
    decision: int | None = None


@dataclass(frozen=True)
class Completion:
    goal_id: str
    succeeded: bool


@dataclass(frozen=True)
class Step:
    action: str
    target: tuple[float, ...] | None
    tolerance: tuple[float, ...]
    angular: tuple[int, ...] = ()
    read_source: tuple[str, ...] | None = None
    target_from_read: Callable[[object], tuple[float, ...]] | None = None


def finite_number(value):
    return type(value) in (int, float) and isfinite(value)


def matches(observed, expected, tolerance, angular):
    if not len(observed) == len(expected) == len(tolerance):
        return False
    for index, (actual, goal, limit) in enumerate(zip(observed, expected, tolerance)):
        if not all(finite_number(x) for x in (actual, goal, limit)) or limit <= 0:
            return False
        difference = angle_error(actual, goal) if index in angular else abs(actual - goal)
        if difference > limit:
            return False
    return True


def verify_sequence(steps, events):
    """Require each declared action to be dispatched and completed in order.

    Supply decision indices on both events if tool calls were preselected as
    a batch. A result from that same decision cannot inform a preselected
    goal. For goals dynamically bound from observations, record the actual
    dispatch, after the binding has completed.
    """
    if events is None:
        return ["missing action event evidence"]
    seen = set()
    reads = {}
    pending = None
    completed = 0
    for event in events:
        if isinstance(event, Read):
            reads.setdefault(event.source, []).append(event)
        elif isinstance(event, Dispatch):
            if pending is not None:
                return ["goal dispatched before the previous goal completed"]
            if not event.goal_id or event.goal_id in seen:
                return ["missing or duplicate dispatched goal ID"]
            if completed == len(steps):
                return ["unexpected dispatched goal"]
            step = steps[completed]
            if event.action != step.action or (
                step.target is not None
                and not matches(event.target, step.target, step.tolerance, step.angular)
            ):
                return ["dispatched goal differs from the ordered task step"]
            if step.target is None and step.read_source is None:
                return ["missing expected goal contract"]
            if step.read_source is not None:
                available = [
                    read for read in reads.get(step.read_source, ())
                    if event.decision is None
                    or (read.decision is not None and read.decision < event.decision)
                ]
                if not available:
                    return ["required read unavailable before goal dispatch"]
                if step.target_from_read is None:
                    return ["missing read-to-goal contract"]
                try:
                    target = step.target_from_read(available[-1].value)
                    agrees = matches(event.target, target, step.tolerance, step.angular)
                except (ArithmeticError, TypeError, ValueError, KeyError, IndexError):
                    agrees = False
                if not agrees:
                    return ["dispatched goal does not match the preceding read"]
            seen.add(event.goal_id)
            pending = event.goal_id
        elif isinstance(event, Completion):
            if pending is None or event.goal_id != pending or event.succeeded is not True:
                return ["missing or unsuccessful goal completion"]
            pending = None
            completed += 1
        else:
            return ["unrecognized action evidence event"]
    if pending is not None or completed != len(steps):
        return ["incomplete ordered action sequence"]
    return []


def judge_contract(base_verdict, steps, events):
    """Combine a pool's answer-time oracle and the common sequence checks."""
    reasons = list(base_verdict["reasons"]) + verify_sequence(steps, events)
    return {"success": base_verdict["success"] and not reasons, "reasons": reasons}


def dev_steps(task_id):
    # Use the frozen dev angular tolerance. Archived dev records do not have
    # an independent intermediate pose for the relative command.
    first_targets = {"M1": 0.5, "M2": -1.5, "M3": 1.0}
    targets = [TASKS[task_id]["final_target"]]
    if task_id in first_targets:
        targets.insert(0, first_targets[task_id])
    steps = [Step("rotate_to_heading", (theta,), (TOLERANCE,), (0,)) for theta in targets]
    if task_id == "R1":
        steps[0] = Step("rotate_to_heading", (targets[0],), (1e-6,), (0,),
                        ("/turtlesim", "background_r"), lambda value: (value / 100,))
    return steps


def dev_events(trace):
    """Join archived synchronous tool rows to the executor's goal receipts.

    Every rotate tool row has one recorded executor call. PENDING is written
    just before send_goal, TERMINAL before a successful call returns. The
    runner executes tool rows serially, so their order also brackets its
    untimestamped reads.
    """
    sidecars = [row["events"] for row in trace if row["kind"] == "executor_events"]
    if len(sidecars) != 1:
        raise ValueError("expected one executor event stream")
    executor = sidecars[0]
    calls = iter(row for row in executor if row["kind"] == "call")
    states = {}
    positions = {}
    for index, row in enumerate(executor):
        if row["kind"] == "state" and row["goal_id"] is not None:
            states.setdefault(row["goal_id"], []).append(row["state"])
            positions.setdefault(row["goal_id"], []).append(index)

    events = []
    dispatched = set()
    previous_end = -1
    decision = 0
    for row in trace:
        if row["kind"] == "assistant":
            decision += 1
        if row["kind"] != "tool":
            continue
        args = row["arguments"]
        if row["name"] == "get_parameter":
            match = re.fullmatch(r"Integer value is: (-?\d+)", row["content"].strip())
            node, parameter = args.get("node_name"), args.get("parameter_name")
            if match and isinstance(node, str) and isinstance(parameter, str):
                events.append(Read((node, parameter), int(match[1]), decision))
        if row["name"] != "rotate_to_heading":
            continue
        call = next(calls, None)
        if call is None or call["tool"] != row["name"] or call["arguments"] != args:
            raise ValueError("tool/executor receipt mismatch")
        receipt = call["goal_id"]
        if receipt is None:
            if call["result"] == "SUCCEEDED":
                raise ValueError("success without a dispatched goal")
            continue
        lifecycle = states.get(receipt, [])
        if receipt in dispatched or not lifecycle or lifecycle[0] != "PENDING":
            raise ValueError("invalid dispatch lifecycle")
        if positions[receipt][0] <= previous_end:
            raise ValueError("out-of-order or overlapping executor goals")
        previous_end = positions[receipt][-1]
        succeeded = call["result"] == "SUCCEEDED"
        if succeeded and lifecycle != ["PENDING", "ACTIVE", "TERMINAL"]:
            raise ValueError("success without a terminal lifecycle")
        if row["content"].split(maxsplit=1)[0] != call["result"]:
            raise ValueError("tool/executor outcome mismatch")
        dispatched.add(receipt)
        events.append(Dispatch(receipt, row["name"], (args.get("theta"),), decision))
        events.append(Completion(receipt, succeeded))
    if next(calls, None) is not None or dispatched != set(states):
        raise ValueError("unmatched executor goal evidence")
    return events


def judge(task_id, answer, true_heading, true_x, true_y, still, *, ending, trace):
    """Public development entry point. The frozen original scorer is retained."""
    base = judge_v1_1(task_id, answer, true_heading, true_x, true_y, still, ending=ending)
    try:
        events = dev_events(trace)
    except (KeyError, IndexError, TypeError, ValueError):
        events = None
    return judge_contract(base, dev_steps(task_id), events)
