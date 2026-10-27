"""Ordinary bounded macro reference, sharing permissions and report validation.

This is deliberately the same acquisition policy as WorkflowSession. It is a
strong packaging reference, not a new selection algorithm or general planner.
"""
from copy import deepcopy

from .reference import ReferenceWorkflowSession
from .terminal import coordination_span


class MacroSession(ReferenceWorkflowSession):
    """Straight-line read / conditional write / fresh verify with no FSM dispatch."""

    def run_workflow(self):
        with self.owner('program'), coordination_span(self, 'macro.bounded_execution'):
            try:
                observed = self.tools_by_name['read_state'].invoke({'nodes': sorted(self.targets)})
                if not isinstance(observed, dict):
                    return self.escalate('read_rejected', observed)
                values = observed['observed_values']
                if any(v is None for group in values.values() for v in group.values()):
                    return self.escalate('observation_unavailable_no_write', observed)
                if any(abs(values[n][k] - v) > self.tolerance
                       for n, group in self.targets.items() for k, v in group.items()):
                    node = next(iter(self.targets))
                    receipt = self.tools_by_name['write_state'].invoke(
                        {'node_name': node, 'values': deepcopy(self.targets[node])})
                    if not isinstance(receipt, dict):
                        return self.escalate('prerequisite_rejected_no_automatic_retry', receipt)
                verified = self.tools_by_name['verify_outcome'].invoke({})
                if not isinstance(verified, dict):
                    return self.escalate('verification_rejected', verified)
                if verified['goal_reached'] is not True:
                    return self.escalate('outcome_not_confirmed_no_command_replay', verified)
                self.workflow_state = 'AWAITING_REPORT'
                return {'selected_skill': self.selected_skill, 'workflow_state': self.workflow_state,
                        'verification': verified, 'next_step_owner': 'model'}
            except BaseException:
                self.transition('STOPPED', 'exception_no_automatic_retry_or_replay')
                raise
