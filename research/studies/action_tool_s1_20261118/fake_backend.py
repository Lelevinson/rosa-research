"""A scripted fake robot and a fake clock for testing the executor without ROS, Gazebo or a model. Development tool only.

FakeClock.sleep() advances time instantly, so a 60-second deadline costs no real time. FakeBackend is driven by plain settings; each test sets exactly one behaviour.
It records every call the executor makes, so tests can assert "no goal was sent" or "the goal was sent exactly once".
"""
from typing import Dict, List, Optional, Tuple

from action_interface import Ack, GoalStatus


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


class FakeBackend:
    """Behaviour settings (all defaults give a robot that is ready, accepts the goal and succeeds after `run_seconds`)."""

    def __init__(self, clock: FakeClock):
        self.clock = clock
        self.not_ready_reason: Optional[str] = None
        self.ack = Ack.ACCEPTED
        self.run_seconds = 3.0                      # how long an accepted goal runs; use a huge value for "never finishes"
        self.final_status = GoalStatus.SUCCEEDED
        self.error_code: Optional[int] = None
        self.cancel_works = True                    # False: cancel is requested but the goal keeps running
        self.goal_exists_after_lost_ack = False     # with Ack.NO_ANSWER: does the goal actually exist on the server?
        self.poll_raises = False
        self.state_text = "pose x=1.00 y=2.00 yaw=0.00"
        self.sent: List[Tuple[str, Dict[str, float], str]] = []
        self.cancels: List[str] = []
        self.observed = 0
        self._started_at: Optional[float] = None
        self._goal_id: Optional[str] = None
        self._canceled = False

    def readiness(self) -> Optional[str]:
        return self.not_ready_reason

    def send_goal(self, action_name, fields, goal_id, ack_deadline_seconds) -> Ack:
        self.sent.append((action_name, dict(fields), goal_id))
        self._canceled = False                      # a new goal starts un-canceled (the flag belongs to one goal)
        if self.ack == Ack.NO_ANSWER:
            self.clock.sleep(ack_deadline_seconds)   # the executor waited the whole deadline
            if self.goal_exists_after_lost_ack:
                self._goal_id, self._started_at = goal_id, self.clock.now()
            return Ack.NO_ANSWER
        if self.ack == Ack.ACCEPTED:
            self._goal_id, self._started_at = goal_id, self.clock.now()
        return self.ack

    def poll(self, goal_id) -> Tuple[GoalStatus, Optional[int]]:
        if self.poll_raises:
            raise ConnectionError("lost connection")
        if goal_id != self._goal_id or self._started_at is None:
            return GoalStatus.UNKNOWN, None
        if self._canceled:
            return GoalStatus.CANCELED, None
        if self.clock.now() - self._started_at >= self.run_seconds:
            return self.final_status, (self.error_code if self.final_status == GoalStatus.ABORTED else None)
        return GoalStatus.ACTIVE, None

    def cancel(self, goal_id) -> None:
        self.cancels.append(goal_id)
        if self.cancel_works and goal_id == self._goal_id:
            self._canceled = True

    def observe_state(self) -> str:
        self.observed += 1
        return self.state_text
