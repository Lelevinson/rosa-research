"""Opt-in reporting by reference to an existing task-local observation.

No extra sensor acquisition, value repairs, database or new evidence ledger.
The model supplies the classification; the existing validator checks it.
"""
from copy import deepcopy
from typing import Literal
from uuid import uuid4

from pydantic import StrictStr
from .tools import StrictArgs
from .workflow import WorkflowSession, make_workflow_tools


class ReferenceReportArgs(StrictArgs):
    status: Literal['SUCCESS', 'FAILURE', 'UNKNOWN']
    observation_id: StrictStr


class ReferenceWorkflowSession(WorkflowSession):
    def __init__(self, *args, **kwargs):
        self._observation_namespace = uuid4().hex[:12]
        super().__init__(*args, **kwargs)

    def read(self, nodes, actor='model'):
        result = super().read(nodes, actor)
        identifier = f'obs-{self._observation_namespace}-{len(self.observations)}'
        result['observation_id'] = identifier
        self.observations[-1]['observation_id'] = identifier
        return result

    def report_reference(self, status, observation_id):
        event = {'type': 'report_reference', 'actor': 'model', 'status': status,
                 'observation_id': observation_id, 'accepted': False,
                 'values_supplied_by': 'program_from_existing_observation'}
        self.events.append(event)
        if self.selected_skill is None:
            return self.feedback('skill_selection_required', {'available_skills': sorted(self.skills)})
        found = next(((i, o) for i, o in enumerate(self.observations)
                      if o.get('observation_id') == observation_id), None)
        if found is None:
            return self.feedback('unknown_observation_reference',
                                 {'requirement': 'Use an observation_id returned in this task.'})
        index, observed = found
        if (index < self._read_floor or index != len(self.observations) - 1
                or any(e['after_write'] != self.last_write for e in observed['evidence'])):
            return self.feedback('stale_observation_reference',
                                 {'requirement': 'Use the latest observation after any write.'})
        values = observed['observed_values']
        if set(values) != set(self.targets) or any(set(values[n]) != set(self.targets[n]) for n in self.targets):
            return self.feedback('incomplete_observation_reference',
                                 {'requirement': 'Read all selected skill fields.'})
        before = len(self.reports)
        try:
            result = super().report(status, deepcopy(values))
        finally:
            if len(self.reports) > before:
                self.reports[-1].update(observation_id=observation_id,
                    values_supplied_by='program_from_existing_observation')
        event['accepted'] = True
        return {**result, 'observation_id': observation_id,
                'values_supplied_by': 'program_from_existing_observation'}


def make_reference_tools(session):
    tools = make_workflow_tools(session)
    report = next(t for t in tools if t.name == 'submit_report')
    report.args_schema = ReferenceReportArgs
    report.func = session.report_reference
    report.description = ('Classify SUCCESS, FAILURE or UNKNOWN and cite the latest observation_id '
        'returned by read_state or verify_outcome, including nested workflow evidence. '
        'ROSA retrieves exact values and checks freshness and classification; unavailable values '
        'support UNKNOWN, never SUCCESS. Do not reconstruct node names or sensor values.')
    return tools
