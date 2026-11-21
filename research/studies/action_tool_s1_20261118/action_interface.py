"""Guarded action tool, stage S1: the INTERFACE (spec: "Claude outputs/2026-11-17_GUARDED_ACTION_TOOL_SPEC.md", v2). Read DESIGN.md first.

This file only defines the shapes that everything else agrees on: the deployment policy (fixed per robot, identical for every method), the executor options (the
method switches), the backend contract (what the real Nav2 / turtlesim code must provide later), the result states, and the text the model sees.
It contains no motion logic. The logic is in action_executor.py; a scripted fake robot for tests is in fake_backend.py.

Everything here is a prototype for development; nothing is registered in ROSA or in any harness (framework integration needs the owner's authorization).
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Protocol, Tuple


# ---------------------------------------------------------------- deployment policy (written once per robot, before any task is seen)
@dataclass(frozen=True)
class FieldRange:
    """One numeric argument of a typed action: a finite number inside [minimum, maximum] (the units go into the description)."""
    name: str
    minimum: float
    maximum: float
    unit: str


@dataclass(frozen=True)
class ActionSpec:
    """One typed action tool, for example navigate_to_pose(x, y, yaw). `ros_action_name` is what the backend sends the goal to."""
    tool_name: str
    ros_action_name: str
    description: str
    fields: Tuple[FieldRange, ...]


@dataclass(frozen=True)
class DeploymentPolicy:
    """Fixed per robot and identical in every method (the fairness requirement of spec section 9). Deadlines are wall-clock seconds on a monotonic clock."""
    actions: Dict[str, ActionSpec]          # tool_name -> spec; only these actions can ever be sent
    goal_budget: int                         # goals that may be SENT per episode (a NOT_READY call does not consume it)
    acknowledgement_seconds: float           # how long the server may take to accept or reject a goal
    execution_seconds: float                 # how long an accepted goal may run before the executor cancels it
    cancel_settlement_seconds: float         # how long a cancel request may take to be confirmed
    poll_seconds: float = 0.5


@dataclass(frozen=True)
class ExecutorOptions:
    """Method switches. Separate from the policy on purpose: the policy must be the same for all methods, a switch here may become a method component.

    attach_post_action_state: if True, a line `State after action: ...` (from backend.observe_state()) is appended to the model-visible result of any call that
    sent a goal. Default False. It is NOT the evaluator's ground truth (spec section 8); it is whatever the robot's own sensors report to the executor.
    """
    attach_post_action_state: bool = False


# ---------------------------------------------------------------- states and results
class ExecutorState(Enum):
    IDLE = "IDLE"
    PENDING = "PENDING"                      # goal sent, not yet acknowledged
    ACTIVE = "ACTIVE"                        # goal accepted, running
    TERMINAL = "TERMINAL"                    # last goal ended in a known way; a new goal may be sent
    UNKNOWN_LOCKED = "UNKNOWN_LOCKED"        # motion state unknown (lost acknowledgement, unresolved timeout, failed cancel): no new motion, never auto-unlocked


class Result(Enum):
    REJECTED = "REJECTED"                    # failed a check before any goal was sent (or the server refused it); no motion
    NOT_READY = "NOT_READY"                  # preflight failed; no goal sent, budget unchanged
    SUCCEEDED = "SUCCEEDED"
    ABORTED = "ABORTED"
    CANCELED = "CANCELED"
    TIMEOUT = "TIMEOUT"
    LOCKED = "LOCKED"                        # a previous goal is unresolved; nothing was sent


@dataclass
class ActionOutcome:
    """Structured internal record (for the experiment log). The model only sees render_for_model(outcome)."""
    result: Result
    detail: str = ""                         # short reason, e.g. the failed check and field
    goal_id: Optional[str] = None
    error_code: Optional[int] = None
    motion_confirmed_stopped: Optional[bool] = None   # None = not applicable or not known
    seconds: float = 0.0
    post_action_state: Optional[str] = None  # filled only when the option is on
    state_after: ExecutorState = ExecutorState.IDLE


def render_for_model(outcome: ActionOutcome) -> str:
    """Compact text for the model (spec section 3). Never an exception. The post-action line is present only if the executor filled it."""
    names = {
        Result.REJECTED: "REJECTED",
        Result.NOT_READY: "NOT_READY",
        Result.SUCCEEDED: "SUCCEEDED",
        Result.ABORTED: "ABORTED",
        Result.CANCELED: "CANCELED",
        Result.TIMEOUT: "TIMEOUT",
        Result.LOCKED: "LOCKED",
    }
    text = names[outcome.result]
    if outcome.result == Result.ABORTED and outcome.error_code is not None:
        text += f" (error code {outcome.error_code})"
    if outcome.result == Result.TIMEOUT:
        # The cancel is only a request: if it was not confirmed, the model must not believe the robot has stopped.
        text += ": cancel confirmed, robot stopped" if outcome.motion_confirmed_stopped else ": cancel requested, motion state unknown"
    elif outcome.result == Result.LOCKED:
        text += ": previous goal unresolved"
    elif outcome.detail:
        text += f" {outcome.detail}"
    if outcome.post_action_state is not None:
        text += f"\nState after action: {outcome.post_action_state}"
    return text


def tool_schema(spec: ActionSpec) -> dict:
    """OpenAI-style function schema of one typed action tool, generated from the policy (units and limits in the description, never per task)."""
    properties = {f.name: {"type": "number", "description": f"{f.name} in {f.unit}, from {f.minimum} to {f.maximum}"} for f in spec.fields}
    return {"type": "function", "function": {"name": spec.tool_name, "description": spec.description,
                                             "parameters": {"type": "object", "properties": properties, "required": [f.name for f in spec.fields], "additionalProperties": False}}}


# ---------------------------------------------------------------- what the real robot side must provide
class GoalStatus(Enum):
    ACTIVE = "ACTIVE"
    SUCCEEDED = "SUCCEEDED"
    ABORTED = "ABORTED"
    CANCELED = "CANCELED"
    UNKNOWN = "UNKNOWN"                      # the backend cannot say (goal id not found, connection lost)


class Ack(Enum):
    ACCEPTED = "ACCEPTED"
    REFUSED = "REFUSED"                      # the action server answered and said no
    NO_ANSWER = "NO_ANSWER"                  # nothing arrived within the acknowledgement deadline: the goal may or may not exist


class Clock(Protocol):
    def now(self) -> float: ...              # monotonic seconds
    def sleep(self, seconds: float) -> None: ...


class ActionBackend(Protocol):
    """The contract a real backend (turtlesim action client, Nav2 Simple Commander) must satisfy. All methods may raise; the executor treats an exception as an
    unknown outcome and locks (after a goal was sent) or reports NOT_READY (before)."""
    def readiness(self) -> Optional[str]: ...           # None if ready, else a short reason (server missing, lifecycle inactive, stale TF, sim clock stalled)
    def send_goal(self, action_name: str, fields: Dict[str, float], goal_id: str, ack_deadline_seconds: float) -> Ack: ...
    def poll(self, goal_id: str) -> Tuple[GoalStatus, Optional[int]]: ...   # (status, error code if aborted)
    def cancel(self, goal_id: str) -> None: ...         # a request only; it does not promise a stop
    def observe_state(self) -> str: ...                 # one compact line from the robot's own sensors (not the evaluator's ground truth)
