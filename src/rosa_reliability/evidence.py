"""Prospective v2 contract: reuse fresh trusted reads without a named-tool rule."""
from copy import deepcopy
from .execution import ExecutionSession
from .tools import make_tools


class EvidenceSession(ExecutionSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._read_floor = 0

    def native(self, kind, actor, function):
        if kind == 'write':
            # A failed dispatch can still have changed physical state.
            self._read_floor = len(self.observations)
        return super().native(kind, actor, function)

    def report(self, status, observed_values):
        if self.observations:
            values, evidence = {}, []
            for observation in reversed(self.observations[self._read_floor:]):
                for item in observation['evidence']:
                    node = item['node']
                    if node not in values and item['after_write'] == self.last_write:
                        values[node] = deepcopy(observation['observed_values'][node])
                        evidence.append(deepcopy(item))
            if set(values) == set(self.targets):
                unknown = any(v is None for group in values.values() for v in group.values())
                reached = None if unknown else all(abs(values[n][k] - v) <= self.tolerance
                    for n, group in self.targets.items() for k, v in group.items())
                ids = sorted(e['operation_id'] for e in evidence)
                previous_ids = sorted(e['operation_id'] for e in (self.verification or {}).get('evidence', []))
                if ids != previous_ids or self.verification is None:
                    self.verification = {'observed_values': values, 'evidence': evidence,
                        'after_write': self.last_write, 'goal_reached': reached, 'actor': 'shared_evidence_reuse'}
                    self.events.append({'type': 'evidence_reuse', 'actor': 'shared_contract', 'operation_ids': ids})
        return super().report(status, observed_values)


def make_evidence_tools(session):
    tools = make_tools(session)
    for tool in tools:
        if tool.name == 'submit_report':
            tool.description = ('Submit SUCCESS, FAILURE or UNKNOWN with the same node-keyed '
                'observed_values from fresh read_state or verify_outcome evidence. Never invent values.')
    return tools
