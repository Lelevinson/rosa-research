"""Movement versus a genuinely read-only inspection contract; zero providers."""
from copy import deepcopy
import unittest

from pydantic import ValidationError
from rosa_reliability.bounded_macro import MacroLimits, StateSkill
from rosa_reliability.capabilities import CapabilityRegistry, InspectionSkill
from rosa_reliability.execution import ControlledStop
from rosa_reliability.macro_demo import MemoryTransport


CHECKS = {'controllers': ['controller_active'], 'joint_state': ['joint_sample_fresh']}


class MemoryReadiness:
    def __init__(self, fault=None): self.fault, self.records = fault, []
    def read_group(self, source, names):
        self.records.append(source)
        if source == self.fault: raise TimeoutError('synthetic_source_unavailable')
        return {name: False if self.fault == 'unready' and source == 'controllers' else True for name in names}


def registry():
    return (CapabilityRegistry()
        .register(StateSkill(skill_id='arm.move', targets={'/demo_arm': {'yaw': 0.2, 'pitch': 0.1}}))
        .register(InspectionSkill(skill_id='arm.inspect', subject='/arm_readiness', checks=deepcopy(CHECKS))))


class CapabilityTests(unittest.TestCase):
    def setup_case(self, fault=None, mode='macro', **kwargs):
        movement, inspection = MemoryTransport(), MemoryReadiness(fault)
        inv = registry().open({'state': movement, 'inspection': inspection}, mode=mode, **kwargs)
        return inv, movement, inspection, {t.name: t for t in inv.tools}

    def test_catalogue_distinguishes_capability_and_permission(self):
        catalog = registry().catalogue()
        self.assertEqual(catalog['arm.move']['kind'], 'state_change')
        self.assertEqual(catalog['arm.inspect']['kind'], 'read_only_inspection')
        self.assertEqual(catalog['arm.inspect']['max_writes'], 0)
        self.assertNotIn('targets', catalog['arm.inspect'])

    def test_ready_inspection_uses_two_metered_sources_and_no_movement_io(self):
        inv, movement, inspection, _ = self.setup_case()
        inv.execute('arm.inspect')
        evidence = inv.session.observations[-1]
        self.assertTrue(inv.submit_report('SUCCESS', evidence['observation_id'])['report_accepted'])
        self.assertEqual(inspection.records, ['controllers', 'joint_state'])
        self.assertEqual(len(evidence['evidence']), 2)
        self.assertEqual({e['operation_id'] for e in evidence['evidence']}, {1, 2})
        self.assertEqual([e['actor'] for e in inv.session.budget.events], ['program', 'program'])
        self.assertFalse(movement.records)
        self.assertEqual(inv.snapshot()['selected_max_writes'], 0)

    def test_unready_is_failure_and_unavailable_is_unknown(self):
        for fault, status in [('unready', 'FAILURE'), ('controllers', 'UNKNOWN'), ('joint_state', 'UNKNOWN')]:
            inv, movement, _, _ = self.setup_case(fault)
            inv.execute('arm.inspect')
            identifier = inv.session.observations[-1]['observation_id']
            self.assertIn('unsupported_success', inv.submit_report('SUCCESS', identifier))
            self.assertEqual(inv.submit_report(status, identifier)['status'], status)
            self.assertEqual(movement.writes, 0)

    def test_primitive_inspection_can_never_write_and_cannot_reselect_to_move(self):
        inv, movement, _, tools = self.setup_case(mode='primitives')
        inv.execute('arm.inspect')
        self.assertIn('read_only_skill_forbids_write', tools['write_state'].invoke(
            {'node_name': '/arm_readiness', 'values': {'controller_active': 1, 'joint_sample_fresh': 1}}))
        self.assertIn('skill_already_selected', inv.execute('arm.move'))
        self.assertFalse(movement.records)
        self.assertFalse(inv.session.budget.events)

    def test_inspection_requires_correct_source_scope_and_boolean_observations(self):
        inv, _, transport, tools = self.setup_case(mode='primitives')
        inv.execute('arm.inspect')
        self.assertIn('invalid_node_scope', tools['read_state'].invoke({'nodes': ['/demo_arm']}))
        transport.read_group = lambda source, names: {name: 1 for name in names}
        with self.assertRaisesRegex(RuntimeError, 'invalid_boolean'):
            tools['read_state'].invoke({'nodes': ['/arm_readiness']})
        self.assertFalse(inv.session.observations)

    def test_each_source_reserves_budget_before_acquisition(self):
        inv, movement, inspection, _ = self.setup_case(limits=MacroLimits(native_operations=1))
        with self.assertRaises(ControlledStop): inv.execute('arm.inspect')
        self.assertEqual(inspection.records, ['controllers'])
        self.assertFalse(inv.session.observations)
        self.assertEqual(movement.writes, 0)

    def test_inspection_evidence_is_latest_and_task_scoped(self):
        inv, _, _, tools = self.setup_case(mode='primitives')
        inv.execute('arm.inspect')
        old = tools['read_state'].invoke({'nodes': ['/arm_readiness']})['observation_id']
        latest = tools['verify_outcome'].invoke({})['observation_id']
        self.assertIn('stale_observation_reference', inv.submit_report('SUCCESS', old))
        other, _, _, _ = self.setup_case()
        other.execute('arm.inspect')
        self.assertIn('unknown_observation_reference', other.submit_report('SUCCESS', latest))
        self.assertTrue(inv.submit_report('SUCCESS', latest)['report_accepted'])

    def test_movement_still_uses_original_guarded_policy(self):
        inv, movement, inspection, _ = self.setup_case()
        inv.execute('arm.move')
        self.assertEqual(movement.writes, 1)
        self.assertEqual(movement.values, {'yaw': 0.2, 'pitch': 0.1})
        self.assertFalse(inspection.records)
        self.assertEqual(inv.snapshot()['selected_max_writes'], 1)

    def test_unauthorized_skill_never_queries_a_source(self):
        inv, movement, inspection, _ = self.setup_case(allowed_skills=['arm.inspect'])
        self.assertIn('skill_not_authorized', inv.execute('arm.move'))
        self.assertFalse(movement.records)
        self.assertFalse(inspection.records)

    def test_malformed_inspection_and_duplicate_fields_are_rejected(self):
        for checks in ({}, {'controllers': []}, {'controllers': ['x'], 'joint_state': ['x']}):
            with self.assertRaises(ValidationError):
                InspectionSkill(skill_id='arm.inspect', subject='/arm_readiness', checks=checks)
        with self.assertRaises(ValidationError):
            InspectionSkill(skill_id='arm.inspect', subject='missing_slash', checks=CHECKS)

    def test_terminal_inspection_blocks_further_acquisitions(self):
        inv, _, inspection, tools = self.setup_case()
        inv.execute('arm.inspect')
        inv.submit_report('SUCCESS', inv.session.observations[-1]['observation_id'])
        with self.assertRaises(ControlledStop): tools['verify_outcome'].invoke({})
        self.assertEqual(len(inspection.records), 2)


if __name__ == '__main__': unittest.main()
