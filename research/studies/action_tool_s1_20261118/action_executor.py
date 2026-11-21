"""Guarded action tool, stage S1: the EXECUTOR CORE (state machine). Interface: action_interface.py. Spec: GUARDED_ACTION_TOOL_SPEC v2, sections 3, 6, 7.

One call to `ActionExecutor.execute(tool_name, arguments)` does, in this order, and returns an ActionOutcome (it never raises to the caller):
  1. refuse if a previous goal is unresolved (LOCKED)        4. readiness preflight (NOT_READY, budget unchanged)
  2. check the tool name and arguments (REJECTED, no motion)  5. send the goal once; never resend (a lost acknowledgement locks)
  3. check the per-episode goal budget (REJECTED)             6. wait for the result up to the execution deadline, then cancel and wait for settlement

Decisions that are easy to miss (each is tested in tests/test_executor.py):
  * A goal that is sent counts against the budget even if the server refuses it or never answers; a NOT_READY call does not.
  * A lost acknowledgement is never retried. The executor asks the backend once about the goal id: a running goal is tracked as usual, a finished one is reported,
    and if the backend cannot say, the executor requests a cancel and LOCKS.
  * A cancel is a request. Only a confirmed terminal status counts as "motion stopped"; otherwise the executor locks and the model is told the state is unknown.
  * The lock is never released by the executor, not even by begin_episode(): a new episode must be blocked, not silently continued (spec section 7).
  * S1 runs in the caller's process. The spec's separate long-lived supervisor (so a killed worker cannot orphan a goal) is the next stage; the backend and clock are
    injected so that this logic moves into the supervisor unchanged.
"""
import math
import uuid
from typing import Dict, List, Optional, Tuple

from action_interface import (Ack, ActionBackend, ActionOutcome, ActionSpec, Clock, DeploymentPolicy, ExecutorOptions, ExecutorState, GoalStatus, Result)

FINISHED_STATUSES = (GoalStatus.SUCCEEDED, GoalStatus.ABORTED, GoalStatus.CANCELED)


class ActionExecutor:
    def __init__(self, policy: DeploymentPolicy, backend: ActionBackend, clock: Clock, options: Optional[ExecutorOptions] = None, make_goal_id=None):
        self.policy = policy
        self.backend = backend
        self.clock = clock
        self.options = options or ExecutorOptions()
        self.make_goal_id = make_goal_id or (lambda: uuid.uuid4().hex)
        self.state = ExecutorState.IDLE
        self.goals_sent = 0
        self.events: List[dict] = []        # experiment log: one row per call and per state change, with monotonic times

    # ------------------------------------------------------------ episode contract (spec section 7)
    def begin_episode(self) -> Tuple[bool, str]:
        """Start a new episode. Returns (False, reason) and changes nothing if a goal is unresolved: the episode must then be recorded as invalid, not as an agent failure."""
        if self.state in (ExecutorState.PENDING, ExecutorState.ACTIVE, ExecutorState.UNKNOWN_LOCKED):
            self._log("episode_blocked", state=self.state.value)
            return False, f"executor state is {self.state.value}"
        self.goals_sent = 0
        self.state = ExecutorState.IDLE
        self._log("episode_begin")
        return True, ""

    # ------------------------------------------------------------ the one entry point
    def execute(self, tool_name: str, arguments: Dict[str, float]) -> ActionOutcome:
        started = self.clock.now()
        outcome = self._execute(tool_name, arguments, started)
        outcome.seconds = round(self.clock.now() - started, 3)
        outcome.state_after = self.state
        if self.options.attach_post_action_state and outcome.goal_id is not None:
            outcome.post_action_state = self._observe()
        self._log("call", tool=tool_name, arguments=arguments, result=outcome.result.value, detail=outcome.detail, goal_id=outcome.goal_id, state=self.state.value)
        return outcome

    def _execute(self, tool_name: str, arguments: Dict[str, float], started: float) -> ActionOutcome:
        if self.state == ExecutorState.UNKNOWN_LOCKED:
            return ActionOutcome(Result.LOCKED, state_after=self.state)
        if self.state in (ExecutorState.PENDING, ExecutorState.ACTIVE):
            return ActionOutcome(Result.REJECTED, "concurrency: another goal is running")   # unreachable while execute() blocks; kept for the supervisor stage
        spec, problem = self._check(tool_name, arguments)
        if problem:
            return ActionOutcome(Result.REJECTED, problem)
        if self.goals_sent >= self.policy.goal_budget:
            return ActionOutcome(Result.REJECTED, f"budget: {self.policy.goal_budget} goals already sent in this episode")
        try:
            reason = self.backend.readiness()
        except Exception as error:  # the preflight itself failed: not ready, nothing was sent
            reason = f"readiness check failed ({type(error).__name__})"
        if reason:
            return ActionOutcome(Result.NOT_READY, reason)
        return self._send_and_wait(spec, arguments)

    # ------------------------------------------------------------ checks before any motion
    def _check(self, tool_name: str, arguments: Dict[str, float]) -> Tuple[Optional[ActionSpec], str]:
        spec = self.policy.actions.get(tool_name)
        if spec is None:
            return None, f"tool: {tool_name} is not an allowed action"
        if not isinstance(arguments, dict):
            return None, "arguments: expected an object"
        if "behavior_tree" in arguments and arguments["behavior_tree"] not in ("", None):
            return None, "behavior_tree: custom behavior trees are not allowed"   # spec section 4: always empty
        allowed = {f.name for f in spec.fields} | {"behavior_tree"}
        for name in arguments:
            if name not in allowed:
                return None, f"field {name}: unknown field"
        for f in spec.fields:
            if f.name not in arguments:
                return None, f"field {f.name}: missing"
            value = arguments[f.name]
            if isinstance(value, bool) or not isinstance(value, (int, float)):   # bool is an int in Python; a model sending true is a mistake, not a number
                return None, f"field {f.name}: must be a number"
            if not math.isfinite(value):
                return None, f"field {f.name}: must be finite"
            if not f.minimum <= value <= f.maximum:
                return None, f"field {f.name}: {value} is outside {f.minimum} to {f.maximum} {f.unit}"
        return spec, ""

    # ------------------------------------------------------------ send once, wait, cancel on timeout
    def _send_and_wait(self, spec: ActionSpec, arguments: Dict[str, float]) -> ActionOutcome:
        fields = {f.name: float(arguments[f.name]) for f in spec.fields}
        goal_id = self.make_goal_id()
        self.goals_sent += 1                 # counted when sent, whatever the answer
        self._set_state(ExecutorState.PENDING, goal_id)
        try:
            ack = self.backend.send_goal(spec.ros_action_name, fields, goal_id, self.policy.acknowledgement_seconds)
        except Exception as error:           # the goal may or may not exist
            return self._lock_after_lost_ack(goal_id, f"send failed ({type(error).__name__})")
        if ack == Ack.REFUSED:
            self._set_state(ExecutorState.TERMINAL, goal_id)
            return ActionOutcome(Result.REJECTED, "action_server: goal refused", goal_id=goal_id)
        if ack == Ack.NO_ANSWER:
            return self._lock_after_lost_ack(goal_id, "no acknowledgement")
        self._set_state(ExecutorState.ACTIVE, goal_id)
        return self._wait_for_result(goal_id)

    def _wait_for_result(self, goal_id: str) -> ActionOutcome:
        """Poll until the goal ends or the execution deadline passes; then cancel and wait for settlement."""
        deadline = self.clock.now() + self.policy.execution_seconds
        while True:
            status, code = self._poll(goal_id)
            if status in FINISHED_STATUSES:
                return self._finished(goal_id, status, code)
            if self.clock.now() >= deadline:
                break
            self.clock.sleep(self.policy.poll_seconds)
        return self._cancel_and_settle(goal_id)

    def _poll(self, goal_id: str) -> Tuple[GoalStatus, Optional[int]]:
        try:
            return self.backend.poll(goal_id)
        except Exception:
            return GoalStatus.UNKNOWN, None   # treated as "still running"; the deadline still ends the wait

    def _finished(self, goal_id: str, status: GoalStatus, code: Optional[int]) -> ActionOutcome:
        self._set_state(ExecutorState.TERMINAL, goal_id)
        result = {GoalStatus.SUCCEEDED: Result.SUCCEEDED, GoalStatus.ABORTED: Result.ABORTED, GoalStatus.CANCELED: Result.CANCELED}[status]
        return ActionOutcome(result, goal_id=goal_id, error_code=code if status == GoalStatus.ABORTED else None, motion_confirmed_stopped=True)

    def _lock_after_lost_ack(self, goal_id: str, why: str) -> ActionOutcome:
        """Never resend. Ask once whether the goal exists (reconcile by goal id): if it is running, track it as usual; if it already ended, report that;
        if the backend cannot say, request a cancel and lock."""
        status, code = self._poll(goal_id)
        if status == GoalStatus.ACTIVE:
            self._set_state(ExecutorState.ACTIVE, goal_id)
            return self._wait_for_result(goal_id)
        if status in FINISHED_STATUSES:
            return self._finished(goal_id, status, code)
        return self._cancel_and_settle(goal_id, detail=why)

    def _cancel_and_settle(self, goal_id: str, detail: str = "execution deadline") -> ActionOutcome:
        try:
            self.backend.cancel(goal_id)
        except Exception:
            pass                              # a failed cancel request is handled by the settlement wait below: it will not confirm
        settle_deadline = self.clock.now() + self.policy.cancel_settlement_seconds
        while True:
            status, code = self._poll(goal_id)
            if status in FINISHED_STATUSES:
                self._set_state(ExecutorState.TERMINAL, goal_id)
                if status == GoalStatus.SUCCEEDED:   # it finished before the cancel took effect: report the truth
                    return ActionOutcome(Result.SUCCEEDED, "finished during the cancel request", goal_id=goal_id, motion_confirmed_stopped=True)
                return ActionOutcome(Result.TIMEOUT, detail, goal_id=goal_id, error_code=code if status == GoalStatus.ABORTED else None, motion_confirmed_stopped=True)
            if self.clock.now() >= settle_deadline:
                break
            self.clock.sleep(self.policy.poll_seconds)
        self._set_state(ExecutorState.UNKNOWN_LOCKED, goal_id)
        return ActionOutcome(Result.TIMEOUT, detail, goal_id=goal_id, motion_confirmed_stopped=False)

    # ------------------------------------------------------------ small helpers
    def _observe(self) -> str:
        try:
            return self.backend.observe_state()
        except Exception as error:
            return f"unavailable ({type(error).__name__})"

    def _set_state(self, state: ExecutorState, goal_id: Optional[str]) -> None:
        self.state = state
        self._log("state", state=state.value, goal_id=goal_id)

    def _log(self, kind: str, **values) -> None:
        self.events.append(dict(kind=kind, monotonic=self.clock.now(), **values))
