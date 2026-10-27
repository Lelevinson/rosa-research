"""Zero-model public API example, including non-success outcomes.

Run: python -m rosa_reliability.macro_demo --fault none
This is deterministic demonstration code, not independent evaluation.
"""
import argparse
from copy import deepcopy
import json

from .bounded_macro import SkillRegistry, StateSkill


class MemoryTransport:
    """Small bounded in-memory adapter; faults are demo/test inputs only."""

    def __init__(self, initial=None, *, fault='none'):
        self.values = deepcopy(initial or {'yaw': 0.0, 'pitch': 0.0})
        self.fault, self.writes = fault, 0
        self.records = []

    def read(self, node, fields):
        if self.fault == 'missing_before' or (self.fault == 'missing_after' and self.writes):
            self.records.append({'kind': 'read', 'available': False})
            raise TimeoutError('demo_observation_unavailable')
        values = {name: self.values[name] for name in fields}
        self.records.append({'kind': 'read', 'values': deepcopy(values)})
        return values

    def write(self, node, values):
        self.writes += 1
        if self.fault != 'ineffective':
            self.values.update(values)
        if self.fault == 'partial':
            self.values['pitch'] = 0.0
        self.records.append({'kind': 'write', 'values': deepcopy(values)})
        if self.fault == 'uncertain':
            raise TimeoutError('demo_receipt_unknown_after_effect')
        return {'accepted_locally': True}


def demo_registry():
    return (SkillRegistry()
        .register(StateSkill(skill_id='station.left', targets={'/demo_arm': {'yaw': -0.2, 'pitch': 0.1}}))
        .register(StateSkill(skill_id='station.right', targets={'/demo_arm': {'yaw': 0.2, 'pitch': 0.1}})))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fault', choices=('none', 'missing_before', 'missing_after', 'partial', 'ineffective'), default='none')
    args = parser.parse_args()
    transport = MemoryTransport(fault=args.fault)
    invocation = demo_registry().open(transport)
    bundle = invocation.execute('station.right')
    evidence = invocation.session.observations[-1]
    values = evidence['observed_values']['/demo_arm']
    target = invocation.catalogue['station.right']['/demo_arm']
    # The deterministic demo caller classifies. This is not credited to an LLM.
    status = ('UNKNOWN' if any(v is None for v in values.values()) else
              'SUCCESS' if all(abs(values[k] - v) <= invocation.limits.tolerance for k, v in target.items()) else 'FAILURE')
    report = invocation.submit_report(status, evidence['observation_id'])
    print(json.dumps({'decision_actor': 'deterministic_demo', 'live_model_requests': 0,
        'bundle': bundle, 'report': report, 'writes': transport.writes,
        'snapshot': invocation.snapshot()}, indent=2))


if __name__ == '__main__':
    main()
