"""Small opt-in orchestration prototype over the existing bounded tools.

No planner, model-specific repairs, oracle access, caching, or command replay.
The model retains skill selection and truthful reporting in both conditions.
"""
from contextlib import contextmanager
from copy import deepcopy
import math

from pydantic import StrictStr

from .evidence import EvidenceSession, make_evidence_tools
from .execution import ControlledStop
from .tools import ReliableTool, StrictArgs
from .terminal import coordination_span


class SelectArgs(StrictArgs):
    skill_id: StrictStr


class WorkflowSession(EvidenceSession):
    """One user-authorized, single-node skill execution per fresh session.

    The supplied catalogue is a public permission boundary, not an evaluator's
    correct-answer label. Goal interpretation is scored outside this class.
    """
    def __init__(self, transport, skills, *, program_managed=False, **kwargs):
        if not skills or any(not isinstance(k, str) or not k for k in skills):
            raise ValueError('a nonempty public authorized skill catalogue is required')
        for targets in skills.values():
            if len(targets) != 1 or any(not self.canonical(n) or not values or any(
                    type(v) not in (int, float) or not math.isfinite(v)
                    for v in values.values()) for n, values in targets.items()):
                raise ValueError('prototype skills require one canonical node with finite numeric targets')
        if kwargs.get('automatic_verification', False):
            raise ValueError('automatic write verification is not part of this comparison')
        if kwargs.get('write_limit', 1) != 1:
            raise ValueError('prototype permits at most one dispatched write')
        kwargs['write_limit'] = 1
        self.skills = deepcopy(skills)
        self.program_managed = program_managed
        self.selected_skill = None
        self.workflow_state = 'AWAITING_SELECTION'
        self._actor = 'model'
        self.tools_by_name = {}
        super().__init__(transport, next(iter(self.skills.values())), **kwargs)

    @contextmanager
    def owner(self, actor):
        previous, self._actor = self._actor, actor
        try:
            yield
        finally:
            self._actor = previous

    def transition(self, state, reason):
        self.workflow_state = state
        self.events.append({'type': 'workflow_transition', 'state': state,
                            'reason': reason, 'actor': self._actor})

    @contextmanager
    def tool_call(self, name, args):
        with super().tool_call(name, args) as event:
            event['actor'] = self._actor
            if any(r.get('accepted') for r in self.reports):
                raise ControlledStop('session_already_terminal_no_further_tools')
            if self.workflow_state == 'STOPPED':
                raise ControlledStop('workflow_stopped_no_further_dispatch')
            yield event

    def native(self, kind, actor, function):
        return super().native(kind, self._actor if actor == 'model' else actor, function)

    def read(self, nodes, actor='model'):
        return super().read(nodes, self._actor if actor == 'model' else actor)

    def verify(self, actor='model'):
        return super().verify(self._actor if actor == 'model' else actor)

    def report(self, status, observed_values):
        result = super().report(status, observed_values)
        self.transition('TERMINAL', 'model_report_accepted')
        return result

    def select(self, skill_id):
        if self.selected_skill is not None:
            return self.feedback('skill_already_selected', {'selected_skill': self.selected_skill,
                'requirement': 'Do not replay a workflow; use observed feedback or stop.'})
        if skill_id not in self.skills:
            return self.feedback('skill_not_authorized', {'available_skills': sorted(self.skills)})
        self.selected_skill = skill_id
        self.targets = deepcopy(self.skills[skill_id])
        self.transition('SELECTED', 'model_selected_authorized_skill')
        if not self.program_managed:
            return {'selected_skill': skill_id, 'targets': deepcopy(self.targets),
                    'workflow_state': self.workflow_state, 'next_step_owner': 'model'}
        return self.run_workflow()

    def run_workflow(self):
        # Only select() starts a workflow. Re-selection is rejected before any
        # operation. Exceptions, including uncertain write outcomes, never retry.
        with self.owner('program'), coordination_span(self, 'workflow.bounded_execution'):
            try:
                self.transition('READING', 'fresh_prerequisite_observation')
                observation = self.tools_by_name['read_state'].invoke({'nodes': sorted(self.targets)})
                if not isinstance(observation, dict):
                    return self.escalate('read_rejected', observation)
                values = observation['observed_values']
                if any(v is None for group in values.values() for v in group.values()):
                    return self.escalate('observation_unavailable_no_write', observation)
                reached = all(abs(values[n][k] - v) <= self.tolerance
                              for n, group in self.targets.items() for k, v in group.items())
                if not reached:
                    self.transition('EXECUTING', 'known_state_requires_authorized_motion')
                    node = next(iter(self.targets))
                    receipt = self.tools_by_name['write_state'].invoke(
                        {'node_name': node, 'values': deepcopy(self.targets[node])})
                    if not isinstance(receipt, dict):
                        return self.escalate('prerequisite_rejected_no_automatic_retry', receipt)
                self.transition('VERIFYING', 'fresh_outcome_check_not_command_acceptance')
                verified = self.tools_by_name['verify_outcome'].invoke({})
                if not isinstance(verified, dict):
                    return self.escalate('verification_rejected', verified)
                if verified['goal_reached'] is not True:
                    return self.escalate('outcome_not_confirmed_no_command_replay', verified)
                self.transition('AWAITING_REPORT', 'model_must_report_observed_outcome')
                return {'selected_skill': self.selected_skill, 'workflow_state': self.workflow_state,
                        'verification': verified, 'next_step_owner': 'model'}
            except BaseException:
                self.transition('STOPPED', 'exception_no_automatic_retry_or_replay')
                raise

    def escalate(self, reason, evidence):
        self.transition('NEEDS_DECISION', reason)
        return {'selected_skill': self.selected_skill, 'workflow_state': self.workflow_state,
                'reason': reason, 'evidence': deepcopy(evidence), 'next_step_owner': 'model',
                'requirement': 'Use the same bounded tools, report uncertainty or stop; never blindly repeat a dispatched command.'}

    def snapshot(self):
        return {**super().snapshot(), 'selected_skill': self.selected_skill,
                'workflow_state': self.workflow_state, 'program_managed': self.program_managed}


def make_workflow_tools(session):
    tools = make_evidence_tools(session)
    for tool in tools:
        function = tool.func

        def selected_only(_function=function, **kwargs):
            if session.selected_skill is None:
                return session.feedback('skill_selection_required', {'available_skills': sorted(session.skills)})
            return _function(**kwargs)

        tool.func = selected_only
    session.tools_by_name = {tool.name: tool for tool in tools}
    select = ReliableTool(name='select_skill', args_schema=SelectArgs, session=session,
        func=session.select, handle_tool_error=lambda error: str(error), description=(
            'Select one user-authorized skill by exact ID. Select once per task. '
            'Depending on the declared execution condition, this either returns the targets '
            'for model-managed execution or runs bounded read/execute/verify steps. '
            'Inspect the returned observations and submit your own truthful report.'))
    return [select, *tools]
