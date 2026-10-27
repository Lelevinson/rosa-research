"""Public adapter behavior; no network, subprocess, ROS or live inference."""
import time
import unittest
from unittest.mock import patch

from pydantic import ValidationError
from rosa_reliability.bounded_macro import SkillRegistry, StateSkill, MacroLimits
from rosa_reliability.execution import ControlledStop
from rosa_reliability.macro_demo import MemoryTransport, demo_registry


class BoundedMacroTests(unittest.TestCase):
    def setup_invocation(self, fault='none', mode='macro', **kwargs):
        transport = MemoryTransport(fault=fault)
        invocation = demo_registry().open(transport, mode=mode, **kwargs)
        return invocation, transport, {t.name: t for t in invocation.tools}

    def test_two_registered_ids_route_without_dispatch_at_registration(self):
        for skill, yaw in (('station.left', -0.2), ('station.right', 0.2)):
            invocation, transport, _ = self.setup_invocation()
            self.assertFalse(transport.records)
            invocation.execute(skill)
            self.assertEqual(transport.values['yaw'], yaw)
            self.assertEqual(transport.writes, 1)
            self.assertEqual([e['actor'] for e in invocation.session.budget.events], ['program'] * 3)

    def test_invalid_registration_and_limits_fail_without_native_work(self):
        for targets in ({'missing_slash': {'x': 1}}, {'/a': {}}, {'/a': {'x': float('nan')}},
                        {'/a': {'x': True}}, {'/a': {'x': 1}, '/b': {'x': 1}}):
            with self.assertRaises(ValidationError):
                StateSkill(skill_id='test', targets=targets)
        for limits in ({'native_operations': True}, {'seconds': float('inf')}, {'corrections': -1}):
            with self.assertRaises(ValidationError): MacroLimits(**limits)
        for limits in (0, False, {}):
            with self.assertRaises(TypeError): demo_registry().open(MemoryTransport(), limits=limits)
        registry = demo_registry()
        with self.assertRaises(ValueError):
            registry.register(StateSkill(skill_id='station.left', targets={'/x': {'x': 1}}))

    def test_unknown_extra_and_premature_arguments_are_rejected_before_native_io(self):
        invocation, transport, tools = self.setup_invocation(limits=MacroLimits(corrections=10))
        for name, args in [('select_skill', {'skill_id': 'forbidden'}),
                           ('select_skill', {'skill_id': 'station.left', 'arguments': {'yaw': 0}}),
                           ('read_state', {'nodes': ['/demo_arm']})]:
            self.assertIsInstance(tools[name].invoke(args), str)
        self.assertFalse(transport.records)
        self.assertFalse(invocation.session.budget.events)

    def test_catalogue_and_registered_objects_cannot_mutate_existing_permissions(self):
        registry = demo_registry()
        transport = MemoryTransport()
        invocation = registry.open(transport, allowed_skills=['station.left'])
        public = invocation.catalogue
        public['station.left']['/demo_arm']['yaw'] = 100
        self.assertIn('skill_not_authorized', invocation.execute('station.right'))
        invocation.execute('station.left')
        self.assertEqual(transport.values['yaw'], -0.2)

    def test_already_at_goal_reads_and_verifies_without_write(self):
        transport = MemoryTransport({'yaw': 0.2, 'pitch': 0.1})
        invocation = demo_registry().open(transport)
        invocation.execute('station.right')
        self.assertEqual(transport.writes, 0)
        self.assertEqual(len(invocation.session.observations), 2)

    def test_missing_prerequisite_blocks_macro_and_manual_write(self):
        for mode in ('macro', 'primitives'):
            invocation, transport, tools = self.setup_invocation('missing_before', mode)
            invocation.execute('station.right')
            if mode == 'primitives': tools['read_state'].invoke({'nodes': ['/demo_arm']})
            result = tools['write_state'].invoke({'node_name': '/demo_arm', 'values': {'yaw': 0.2, 'pitch': 0.1}})
            self.assertIn('known_prerequisite_required', result)
            identifier = invocation.session.observations[-1]['observation_id']
            self.assertEqual(invocation.submit_report('UNKNOWN', identifier)['status'], 'UNKNOWN')
            self.assertEqual(transport.writes, 0)

    def test_wrong_or_incomplete_target_is_not_authorized(self):
        invocation, transport, tools = self.setup_invocation(mode='primitives')
        invocation.execute('station.right')
        tools['read_state'].invoke({'nodes': ['/demo_arm']})
        for values in ({'yaw': 0.2}, {'yaw': 0.3, 'pitch': 0.1}):
            self.assertIn('registered_target_required', tools['write_state'].invoke({'node_name': '/demo_arm', 'values': values}))
        self.assertEqual(transport.writes, 0)

    def test_partial_and_ineffective_receipts_cannot_become_success(self):
        for fault in ('partial', 'ineffective'):
            invocation, transport, _ = self.setup_invocation(fault)
            invocation.execute('station.right')
            identifier = invocation.session.observations[-1]['observation_id']
            self.assertIn('unsupported_success', invocation.submit_report('SUCCESS', identifier))
            self.assertTrue(invocation.submit_report('FAILURE', identifier)['report_accepted'])
            self.assertEqual(transport.writes, 1)

    def test_unknown_after_write_is_not_promoted_to_success_or_replayed(self):
        invocation, transport, _ = self.setup_invocation('missing_after')
        invocation.execute('station.right')
        identifier = invocation.session.observations[-1]['observation_id']
        self.assertIn('unsupported_success', invocation.submit_report('SUCCESS', identifier))
        self.assertEqual(invocation.submit_report('UNKNOWN', identifier)['status'], 'UNKNOWN')
        self.assertEqual(transport.writes, 1)

    def test_uncertain_receipt_stops_and_cannot_replay(self):
        invocation, transport, tools = self.setup_invocation('uncertain')
        with self.assertRaises(TimeoutError): invocation.execute('station.right')
        for name, args in [('select_skill', {'skill_id': 'station.right'}),
                           ('write_state', {'node_name': '/demo_arm', 'values': {'yaw': 0.2, 'pitch': 0.1}})]:
            with self.assertRaises(ControlledStop): tools[name].invoke(args)
        self.assertEqual(transport.writes, 1)
        self.assertEqual(transport.values['yaw'], 0.2)

    def test_stale_cross_task_and_post_partial_write_evidence_is_rejected(self):
        invocation, transport, tools = self.setup_invocation(mode='primitives')
        invocation.execute('station.right')
        old = tools['read_state'].invoke({'nodes': ['/demo_arm']})['observation_id']
        transport.fault = 'uncertain'
        with self.assertRaises(TimeoutError):
            tools['write_state'].invoke({'node_name': '/demo_arm', 'values': {'yaw': 0.2, 'pitch': 0.1}})
        self.assertIn('stale_observation_reference', invocation.submit_report('FAILURE', old))
        other, _, _ = self.setup_invocation()
        other.execute('station.right')
        self.assertIn('unknown_observation_reference', other.submit_report('SUCCESS', old))

    def test_operation_tool_correction_and_pre_dispatch_time_limits(self):
        invocation, transport, _ = self.setup_invocation(limits=MacroLimits(native_operations=1))
        with self.assertRaises(ControlledStop): invocation.execute('station.right')
        self.assertEqual(transport.writes, 0)
        self.assertEqual(len(invocation.session.budget.events), 1)
        invocation, _, _ = self.setup_invocation(limits=MacroLimits(tool_attempts=1))
        with self.assertRaises(ControlledStop): invocation.execute('station.right')
        invocation, _, _ = self.setup_invocation(limits=MacroLimits(corrections=0))
        with self.assertRaises(ControlledStop): invocation.execute('forbidden')
        invocation, transport, _ = self.setup_invocation()
        with patch('rosa_reliability.execution.time.monotonic', return_value=invocation.session.budget.started + 181):
            with self.assertRaises(ControlledStop): invocation.execute('station.right')
        self.assertFalse(transport.records)

    def test_terminal_blocks_further_tools_and_scope_is_per_invocation(self):
        invocation, transport, tools = self.setup_invocation()
        invocation.execute('station.right')
        identifier = invocation.session.observations[-1]['observation_id']
        self.assertTrue(invocation.submit_report('SUCCESS', identifier)['report_accepted'])
        with self.assertRaises(ControlledStop): tools['read_state'].invoke({'nodes': ['/demo_arm']})
        self.assertEqual(transport.writes, 1)

    def test_late_report_cannot_bypass_elapsed_task_limit(self):
        invocation, _, _ = self.setup_invocation()
        invocation.execute('station.right')
        identifier = invocation.session.observations[-1]['observation_id']
        with patch('rosa_reliability.bounded_macro.time.monotonic', return_value=invocation.session.budget.started + 181):
            with self.assertRaisesRegex(ControlledStop, 'task_deadline'):
                invocation.submit_report('SUCCESS', identifier)
        self.assertFalse(invocation.session.reports)


if __name__ == '__main__': unittest.main()
