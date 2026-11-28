"""Merged agent plus object tools (study-local copy of the tool and prompt wiring). NEW FILE; the frozen demo files (research/demo_merged_20261122) are imported, never modified.
LABEL: merged method (Levinson M + Martin bounded macro) plus object tools; object poses read from the simulator (ground truth); simulated gripper with grasp assist;
demonstration only, not evaluated, not for the paper.

Adds three tools to the merged agent: get_object_pose(name), pick(object), place(object, target). His read menu, his final_answer, his prompt A1 and the arm macro `run_skill`
stay exactly as in the frozen demo. Limits per task: at most 1 pick and 1 place, one object tool per model response, every tool returns its result or refusal as text."""
import json
import time

from langchain_core.tools import StructuredTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, ConfigDict, StrictStr

import objects_skills as sk

OBJECT_RULES = ('For objects on the table use get_object_pose to read where an object is (position in the robot base frame, ground truth from the simulator), '
                'pick to pick one up and place to put the held object on a target. The only object is red_block and the only target is the tray. '
                'If a request is outside these skills or names an object or target that does not exist, say so with final_answer and do not move the arm. '
                'If pick or place refuses or fails, report that; do not repeat it.')
GET_DESC = ('Read where an object is: returns its position (metres) and yaw in the robot base frame. Ground truth from the simulator, read-only. Names: red_block, tray.')
PICK_DESC = ('Pick up one object with the gripper (bounded routine: read pose, move above, descend, close, lift, verify). Refuses without moving if it cannot start. '
             'Use at most once per task. Name: red_block.')
PLACE_DESC = ('Place the held object on a target (bounded routine: check held, move above, lower, open, retreat, verify it rests there). Refuses without moving if nothing is held. '
              'Use at most once per task. Arguments: object red_block, target tray.')


class GetArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: StrictStr


class PickArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    object: StrictStr


class PlaceArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    object: StrictStr
    target: StrictStr


class ObjectTools:
    def __init__(self, skills, log, request_of=None, max_pick=1, max_place=1):
        self.skills, self.log, self.request_of = skills, log, request_of
        self.counts = {'pick': 0, 'place': 0}
        self.limits = {'pick': max_pick, 'place': max_place}
        self._last = None
        self.calls = 0

    def tools(self):
        def mk(name, desc, schema, func):
            return StructuredTool(name=name, description=desc, args_schema=schema, func=func)
        return [mk('get_object_pose', GET_DESC, GetArgs, self.get_object_pose), mk('pick', PICK_DESC, PickArgs, self.pick), mk('place', PLACE_DESC, PlaceArgs, self.place)]

    def _guard(self, tool, args):
        self.calls += 1
        start = self.log.add('object_call_start', tool=tool, arguments=args)
        request = self.request_of() if self.request_of else None
        if request is not None and request == self._last:
            return start, json.dumps({'refused': True, 'code': 'one_object_tool_per_response', 'reason': 'call one object tool per response and wait for its result'})
        self._last = request
        if tool in self.limits and self.counts[tool] >= self.limits[tool]:
            return start, json.dumps({'refused': True, 'code': tool + '_limit_reached', 'reason': 'at most %d %s per task' % (self.limits[tool], tool)})
        return start, None

    def _finish(self, start, tool, outcome):
        self.log.add('object_call_end', tool=tool, parent_call_seq=start, ok=outcome['ok'], step=outcome['step'], detail=outcome['detail'], evidence=outcome['evidence'],
                     refused=outcome['step'] in ('precondition', 'read_pose'))
        return json.dumps({'ok': outcome['ok'], 'step': outcome['step'], 'detail': outcome['detail'], 'evidence': outcome['evidence']}, sort_keys=True)

    def get_object_pose(self, name):
        start, refused = self._guard('get_object_pose', {'name': name})
        if refused:
            return refused
        try:
            outcome = self.skills.where(name)
        except Exception as error:
            outcome = sk.result(False, 'read_pose', 'ground truth unavailable: %s' % error)
        return self._finish(start, 'get_object_pose', outcome)

    def pick(self, object):
        start, refused = self._guard('pick', {'object': object})
        if refused:
            return refused
        self.counts['pick'] += 1
        return self._finish(start, 'pick', self.skills.pick(object))

    def place(self, object, target):
        start, refused = self._guard('place', {'object': object, 'target': target})
        if refused:
            return refused
        self.counts['place'] += 1
        return self._finish(start, 'place', self.skills.place(object, target))


def make_objects_arm_class(h):
    """MergedObjects = his exam_arms.ExamArm ('M') + run_skill (arm macro, as in the frozen demo) + get_object_pose / pick / place."""
    from merged_demo.prompts import MACRO_RULES, SKILL_LINE
    from merged_demo.skill_tool import DESCRIPTION, RunSkillArgs

    class MergedObjects(h['exam_arms'].ExamArm):
        def __init__(self, recorder, context, runner, object_tools):
            super().__init__('M', recorder, context, list(h['run_pilot'].prompt_for('A1')) + [('system', MACRO_RULES), ('system', SKILL_LINE), ('system', OBJECT_RULES)])
            self.name = 'M+macro+objects (demo)'
            self.runner, self.object_tools = runner, object_tools
            runner.request_of = lambda: self.request_count
            object_tools.request_of = lambda: self.request_count

        def base_menu(self):
            return list(super().base_menu()) + ['run_skill', 'get_object_pose', 'pick', 'place']

        def wrap_tools(self, tools):
            wrapped = super().wrap_tools(tools)
            inner = StructuredTool(name='run_skill', description=DESCRIPTION, args_schema=RunSkillArgs, func=self.runner.run)
            self.schemas['run_skill'] = convert_to_openai_tool(inner)['function']['parameters']
            wrapped.append(h['harness'].PilotTool(name='run_skill', description=DESCRIPTION, args_schema=RunSkillArgs, arm=self, func=self._bind(inner),
                                                  handle_tool_error=True, handle_validation_error=self._pydantic_text))
            for tool in self.object_tools.tools():
                self.schemas[tool.name] = convert_to_openai_tool(tool)['function']['parameters']
                wrapped.append(h['harness'].PilotTool(name=tool.name, description=tool.description, args_schema=tool.args_schema, arm=self, func=self._bind(tool),
                                                      handle_tool_error=True, handle_validation_error=self._pydantic_text))
            return wrapped

    return MergedObjects
