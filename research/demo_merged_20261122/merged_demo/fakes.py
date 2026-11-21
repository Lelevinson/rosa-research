"""Test doubles for the scripted dry run: no ROS, no Gazebo, no real model."""
import copy

from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from rosa_reliability.ros_arm import HOME_POSE, JOINTS


class FakeArm:
    """Stands in for ArmTransport. Same contract: read(node, names) full six joints; write(node, values); validate_write bound like the real one (<= 0.4 rad from home)."""
    requires_observation = True

    def __init__(self, initial=None, fault=None):
        self.values, self.fault, self.writes = copy.deepcopy(initial or HOME_POSE), fault, 0

    def read(self, node, names):
        if node != '/ur5e' or set(names) != set(JOINTS):
            raise ValueError('ur5e_full_joint_scope_required')
        if self.fault == 'missing_observation':
            raise TimeoutError('injected_arm_observation_unavailable')
        return {n: self.values[n] for n in names}

    def validate_write(self, node, values):
        if node != '/ur5e' or set(values) != set(JOINTS):
            return 'full six-joint target required'
        if any(abs(v - HOME_POSE[n]) > .4 for n, v in values.items()):
            return 'target outside the bounded range'
        return None

    def write(self, node, values):
        self.writes += 1
        if self.fault != 'ineffective':
            self.values.update(values)
        return {'request_accepted_locally': True}


class FakeReadiness:
    def __init__(self, fault=None):
        self.fault = fault

    def read_group(self, source, names):
        if source == self.fault:
            raise TimeoutError('synthetic_source_unavailable')
        return {name: self.fault != 'inactive' for name in names}


class ScriptedModel:
    """Fake chat model: each step is a list of (tool name, arguments) for one response, or a string for a text-only response. Zero real model calls."""
    model_name = 'scripted-fake (no model call)'

    def __init__(self, steps):
        self.steps, self.index = list(steps), 0

    def __call__(self, messages):
        if self.index >= len(self.steps):
            raise AssertionError('scripted model has no step left')
        step = self.steps[self.index]
        self.index += 1
        usage = {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
        if isinstance(step, str):
            return AIMessage(content=step, usage_metadata=usage)
        calls = [{'name': n, 'args': a, 'id': 'call_%d_%d' % (self.index, i), 'type': 'tool_call'} for i, (n, a) in enumerate(step)]
        return AIMessage(content='', tool_calls=calls, usage_metadata=usage)


def canned_menu(real_tools, outputs):
    """Same names, descriptions and schemas as the real menu; execution returns canned data (no ROS). `outputs` maps tool name to the object returned."""
    def make(tool):
        return StructuredTool(name=tool.name, description=tool.description, args_schema=tool.args_schema,
                              func=lambda _name=tool.name, **kwargs: outputs[_name](kwargs) if callable(outputs.get(_name)) else outputs[_name])
    return [make(t) for t in real_tools]
