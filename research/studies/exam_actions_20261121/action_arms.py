"""Stage 2 (turtlesim action cells): the three systems that can act, built from the EXISTING arms without editing any of them (new folder, no frozen file touched).

  XM    method M = the exam's M arm (exam_arms.ExamArm: short read menu, structured finish, errors as text, name fix) + the guarded action tool + a pose read tool
  XS0   extended baseline S0x = the stock arm S0 (verbatim prompt, stock executor, 47 stock tools) + the SAME action tool + the same pose read tool
  XE1   extended baseline E1x = the arm E1 (stock tools, errors returned as text, better prompt) + the SAME action tool + the same pose read tool

"Same" is literal (draft section 2): every system receives the SAME typed action tool built by `ActionToolKit` from the SAME deployment policy (TURTLESIM_POLICY: tool name, field range, goal
budget 3, acknowledgement 2 s, execution deadline 15 s, cancel settlement 3 s), the same ExecutorOptions (post-action state OFF, the dev default), and the same description and schema. Only the
system's own loop and menu differ. The ROS write paths of the stock tools stay blocked by the pilot's native guard (guarded_native), so the typed tool is the only way to move the robot.
Not integrated in the exam queue files: see action_systems.py for the registry and run_actions_queue.py for the launcher.
"""
import sys
from pathlib import Path
from typing import List

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
for folder in ("action_tool_s1_20261118", "action_tool_s2_20261118", "exam_arms_20261121", "small_model_harness_20261115", "residual_failures_20261115", "fairness_errors_as_text_20261117"):
    sys.path.insert(0, str(STUDIES / folder))
from langchain_core.tools import StructuredTool  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import exam_arms  # noqa: E402
import fair_arms  # noqa: E402
import run_pilot  # noqa: E402
from action_interface import render_for_model  # noqa: E402

ACTION_TOOL = "rotate_to_heading"
POSE_TOOL = "read_turtle_pose"
SYSTEMS = ("XM", "XS0", "XE1")


class RotateArgs(BaseModel):
    """Schema of the typed tool: a number (the model sees `type: number`, as in the dev study's tool_schema). Numeric strings are coerced by the tool layer; out-of-range and non-finite values reach
    the executor's own check and come back as REJECTED text; a non-numeric string is a validation error whose handling is the arm's own (stock arm: stock behaviour)."""
    theta: float = Field(description="theta in radians, from -3.141592653589793 to 3.141592653589793")


class NoArgs(BaseModel):
    pass


class ActionToolKit:
    """The two tools every acting system receives, bound to one executor and one backend of one episode."""
    def __init__(self, policy, executor, backend, recorder):
        self.policy, self.executor, self.backend, self.recorder = policy, executor, backend, recorder
        self.spec = policy.actions[ACTION_TOOL]
        self.goal_sent = False
        self.reads_after_goal = 0

    def _rotate(self, theta=None) -> str:
        arguments = {"theta": theta}
        outcome = self.executor.execute(ACTION_TOOL, arguments)
        self.goal_sent = self.goal_sent or outcome.goal_id is not None
        # event capture for the judge and the report: the call as the model made it, the goal id, the terminal result and the executor state
        self.recorder.add("action_call", tool=ACTION_TOOL, arguments=arguments, result=outcome.result.value, goal_id=outcome.goal_id, state_after=outcome.state_after.value, seconds=outcome.seconds)
        return render_for_model(outcome)

    def _pose(self) -> str:
        text = self.backend.observe_state()
        if self.goal_sent:
            self.reads_after_goal += 1
        self.recorder.add("pose_read", after_goal=self.goal_sent)
        return text

    def tools(self) -> List[StructuredTool]:
        return [StructuredTool(name=ACTION_TOOL, description=self.spec.description, args_schema=RotateArgs, func=self._rotate),
                StructuredTool(name=POSE_TOOL, description="Read the turtle's current pose (read-only).", args_schema=NoArgs, func=self._pose)]


class ActionM(exam_arms.ExamArm):
    """M with the action tools: offered next to the 12 read tools and the finish tool; errors of the added tools come back as text like every M error."""
    def __init__(self, recorder, context, kit):
        super().__init__("M", recorder, context, run_pilot.prompt_for("A1"))
        self.name, self.kit = "XM", kit

    def base_menu(self):
        return list(super().base_menu()) + [ACTION_TOOL, POSE_TOOL]

    def wrap_tools(self, tools):
        added = self.kit.tools()
        for tool in added:
            tool.handle_tool_error, tool.handle_validation_error = True, self._pydantic_text
        return super().wrap_tools(tools) + added


class ActionS0x(run_pilot.StockArm):
    """S0 + the same tools; stock executor: no error handler is added (a validation error is the stock behaviour of this arm)."""
    def __init__(self, recorder, kit):
        super().__init__("S0", recorder)
        self.name, self.kit = "XS0", kit

    def wrap_tools(self, tools):
        return list(tools) + self.kit.tools()


class ActionE1x(fair_arms.ErrorsAsTextArm):
    """E1 + the same tools, returned errors as in E1 (its own wrapper is applied to the added tools too)."""
    def __init__(self, recorder, kit):
        super().__init__("E1", recorder)
        self.name, self.kit = "XE1", kit

    def wrap_tools(self, tools):
        return super().wrap_tools(tools) + [fair_arms.make_returning_errors(t, self.recorder) for t in self.kit.tools()]


def make_arm(system, recorder, context, kit):
    assert system in SYSTEMS, system
    if system == "XM":
        return ActionM(recorder, context, kit)
    return {"XS0": ActionS0x, "XE1": ActionE1x}[system](recorder, kit)
