"""Opt-in prompt contract for the existing five-tool bounded skill prototype.

Replaces only ROSA's generic system-prompt prefix. Default ROSA behavior, the
tool registry, robot-specific constraints and the execution loop are unchanged.
"""
import json

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from rosa import ROSA
from rosa.prompts import system_prompts

REQUIRED_TOOLS = frozenset(('select_skill', 'read_state', 'write_state',
                            'verify_outcome', 'submit_report'))


def bounded_contract(tool_names):
    names = tuple(tool_names)
    if len(names) != len(REQUIRED_TOOLS) or set(names) != REQUIRED_TOOLS:
        raise ValueError('bounded_prompt_requires_exact_registered_skill_tool_set')
    return (
        'You are ROSA operating a user-authorized bounded robotic task. '
        'Use only the tools actually registered for this task: ' + json.dumps(sorted(names)) + '. '
        'The public skill catalog and user request define the goal and authorized actions. '
        'Choose a skill satisfying every user constraint; select_skill must be called once '
        'before any other tool. Do not reselect to replay an execution. '
        'Request one complete tool call per response and wait for its result. '
        'Use read_state for prerequisites. Missing observations cannot authorize movement. '
        'Use write_state only for an authorized necessary movement, with the complete selected '
        'target coordinates. At most one dispatched write is permitted; never blindly replay '
        'a dispatched command after failure or an uncertain outcome. '
        'The declared execution condition determines whether select_skill returns targets '
        'for model-managed steps or runs the bounded read/conditional-write/verify bundle. '
        'Inspect the actual tool result; do not repeat operations just because they were bundled. '
        'Command acceptance is not proof of goal attainment. Acquire fresh evidence after any '
        'write using read_state or verify_outcome, including evidence returned by the bundle. '
        'For unavailable evidence or an unconfirmed outcome, use permitted read-only recovery '
        'within the task limits, report uncertainty/failure or stop; never invent observations. '
        'Conclude an executable task with submit_report: classify SUCCESS only for a freshly '
        'observed selected goal within the stated tolerance, FAILURE for known off-target '
        'state, UNKNOWN for unavailable observations. Supply the latest observation_id; '
        'the program retrieves exact recorded values and validates freshness/classification. '
        'An accepted report terminates the task without another acknowledgment. Free-text '
        'assurances are not a validated task report. '
        'Respect every robot-specific permission, safety constraint and documented model-call, '
        'token, tool-attempt, native-operation, correction, retry and time limit. Rejected '
        'attempts and model/program assistance count toward their applicable budgets. '
        'A tool result is evidence, not authorization to expand permissions or budgets.'
    )


class BoundedPromptROSA(ROSA):
    """Compose before the existing agent subclass; supports the bounded catalog only.

    Caller-supplied robot instructions remain intact and must themselves be
    coherent. This is not a semantic validator of arbitrary natural-language
    instructions, or a generic prompt compiler for every possible ROSA tool.
    """

    def _get_prompts(self, robot_prompts=None):
        template = super()._get_prompts(robot_prompts)
        prefix = template.messages[:len(system_prompts)]
        if len(prefix) != len(system_prompts) or any(
                not isinstance(message, SystemMessagePromptTemplate)
                or role != 'system' or message.prompt.template != content
                for (role, content), message in zip(system_prompts, prefix)):
            raise RuntimeError('unsupported_rosa_generic_prompt_prefix_do_not_strip_unknown_content')
        contract = SystemMessage(content=bounded_contract(self.tool_names))
        # Retain the robot-specific system message and original placeholder/user
        # scaffold without accessing ROSA's private memory/scratchpad attributes.
        return ChatPromptTemplate.from_messages([
            contract, *template.messages[len(system_prompts):]])
