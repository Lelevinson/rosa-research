"""Focused tests of boundary isolation and the two substantive rule revisions."""
import json
from pathlib import Path
import tempfile
import unittest

import replay


def h1(version, public):
    if public['error']:
        return 'ABSTAIN'
    if version >= 1 and (public['stop_competes'] or public['schema_changed']):
        return 'ABSTAIN'
    if version >= 2 and public['needed'] is not True:
        return 'ABSTAIN'
    return 'PROPOSE_READ'


def h2(version, public):
    if not public['origins']:
        return 'ABSTAIN'
    if version >= 1 and (len(public['origins']) != 1 or public['schema_changed']):
        return 'ABSTAIN'
    if version >= 2 and not (public['current'] and public['permitted_flow']):
        return 'ABSTAIN'
    return 'PROPOSE_BIND'


def scenarios():
    ordinary = dict(error=False, stop_competes=False, schema_changed=False,
                    needed=None, origins=['receipt0/nodes/0'], current=True,
                    permitted_flow=False)
    # needed/permitted_flow/current are STIPULATED fixture-contract assumptions,
    # not inferred from ROSA outputs. Truth labels remain test-only.
    return [
        ('goal_STOP', dict(ordinary), False, True),
        ('goal_more_inspection', dict(ordinary), True, True),
        ('error_repair', dict(ordinary, error=True), False, True),
        ('equal_value_distinct_identity', dict(ordinary, origins=['receipt0/config/frame', 'receipt0/observed/frame']), True, False),
        ('stale_or_text_only', dict(ordinary, current=False), True, False),
        ('same_path_list_composite', dict(ordinary, needed=True, permitted_flow=True), True, True),
        ('new_application_schema', dict(ordinary, schema_changed=True), True, False),
        ('observed_STOP_competitor', dict(ordinary, stop_competes=True), False, True),
    ]


class ReplayTests(unittest.TestCase):
    def test_group_and_stop_boundary(self):
        events = [dict(kind='model_start', schemas=[]),
                  dict(kind='model_end', message={'tool_calls': [dict(name='a', args={}), dict(name='b', args={})]}),
                  dict(kind='tool_end', name='a', output={'id': 'current'}),
                  dict(kind='model_start', schemas=[]),
                  dict(kind='model_end', message={'content': 'done'})]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'trace.jsonl'
            path.write_text('\n'.join(json.dumps(e) for e in events))
            rows, incomplete = replay.parse_trace(path, {'copy': 'test'})
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0].observed), 2)
        self.assertEqual(rows[0].state['receipts'], [])
        self.assertEqual(rows[1].state['receipts'][0]['output'], {'id': 'current'})
        self.assertEqual(rows[1].observed, replay.STOP)
        self.assertEqual(incomplete, 0)

    def test_equal_values_preserve_source_ambiguity(self):
        state = {'receipts': [dict(name='read', output={'configured': 'map', 'observed': 'map'}, error=False)]}
        template = replay.learn_template([dict(name='next', args={'frame': 'map'})], state)
        _, problems = replay.instantiate(template, state)
        self.assertIn('ambiguous_origin', problems)

    def test_current_source_uniqueness_is_rechecked(self):
        state = {'receipts': [dict(name='read', output={'source': 'x', 'other': 'y'}, error=False)]}
        template = replay.learn_template([dict(name='next', args={'id': 'x'})], state)
        state['receipts'][0]['output']['other'] = 'x'
        _, problems = replay.instantiate(template, state)
        self.assertIn('ambiguous_current_origin', problems)

    def test_schema_shift_rejected(self):
        state = {'receipts': [dict(name='read', output={'source': 'x'}, error=False)]}
        template = replay.learn_template([dict(name='next', args={'id': 'x'})], state)
        state['receipts'][0]['output'] = {'source': {'name': 'x'}}
        _, problems = replay.instantiate(template, state)
        self.assertIn('changed_schema_or_error', problems)

    def test_text_not_interpreted_as_structured(self):
        state = {'receipts': [dict(name='read', output='{"node":"x"}', error=False)]}
        self.assertEqual(replay.available_origins(state), [])

    def test_source_tool_and_identity_changes_are_rejected(self):
        state = {'receipts': [dict(name='read_a', source_arguments={'node':'a'}, output={'id':'x'}, error=False)]}
        template = replay.learn_template([dict(name='next', args={'id':'x'})], state)
        state['receipts'][0]['name'] = 'read_b'
        _, problems = replay.instantiate(template, state)
        self.assertIn('source_identity_changed', problems)
        state['receipts'][0]['name'] = 'read_a'
        state['receipts'][0]['source_arguments']['node'] = 'b'
        _, problems = replay.instantiate(template, state)
        self.assertIn('source_identity_changed', problems)

    def test_receipt_after_model_start_cannot_leak(self):
        events = [dict(kind='model_start', schemas=[]),
                  dict(kind='tool_end', name='late', output={'secret':'later'}),
                  dict(kind='model_end', message={'tool_calls':[dict(name='read', args={})]})]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'trace.jsonl'
            path.write_text('\n'.join(json.dumps(e) for e in events))
            rows,_=replay.parse_trace(path, {'copy':'late'})
        self.assertEqual(rows[0].state['receipts'], [])

    def test_lower_bound_remains_wide(self):
        self.assertLess(replay.wilson_lower(10, 10), .8)
        self.assertLess(replay.wilson_lower(3, 3), .6)
        self.assertEqual(replay.wilson_lower(0, 0), 0)

    def test_truncated_or_invalid_is_unknown_not_STOP(self):
        self.assertEqual(replay.action({'response_metadata': {'done_reason': 'length'}}), replay.UNKNOWN)
        self.assertEqual(replay.action({'invalid_tool_calls': [{}]}), replay.UNKNOWN)

    def test_semantic_indistinguishability_and_control_parity(self):
        cases = scenarios()
        self.assertEqual(cases[0][1], cases[1][1])
        self.assertNotEqual(cases[0][2], cases[1][2])
        self.assertEqual(h1(2, cases[0][1]), 'ABSTAIN')
        self.assertEqual(h2(1, cases[3][1]), 'ABSTAIN')
        self.assertEqual(h2(0, cases[3][1]), 'PROPOSE_BIND')
        self.assertEqual(h2(1, cases[4][1]), 'PROPOSE_BIND')
        self.assertEqual(h2(2, cases[4][1]), 'ABSTAIN')

    def test_backoff_control_has_full_candidate_capability(self):
        state = dict(history=['["read"]'], receipts=[], registry=[], error=False)
        rows = [replay.Boundary(state, [{'name': 'inspect', 'args': {}}], {'copy': str(i)}) for i in range(5)]
        candidate, control = replay.Predictor('candidate'), replay.Predictor('conditional_backoff')
        for policy in [candidate, control]:
            policy.fit(rows)
            policy.calibrate(rows)
        self.assertEqual(candidate.predict(state), control.predict(state))
        self.assertFalse(candidate.predict(state)['execute'])

    def test_outcome_conditioning_is_an_ordinary_count_rule(self):
        success=dict(history=['["inspect"]'], receipts=[], registry=[], error=False)
        failure=dict(success,error=True)
        rows=[]
        for i in range(4):
            rows.append(replay.Boundary(success,[dict(name='read',args={})],{'copy':f's{i}'}))
            rows.append(replay.Boundary(failure,replay.STOP,{'copy':f'f{i}'}))
        candidate,control,plain=(replay.Predictor(m) for m in ['candidate','conditional_backoff','ngram1'])
        for policy in [candidate,control,plain]:
            policy.fit(rows)
        self.assertEqual(candidate.predict(success),control.predict(success))
        self.assertEqual(candidate.predict(failure),control.predict(failure))
        self.assertNotEqual(candidate.predict(success)['prediction'],candidate.predict(failure)['prediction'])
        self.assertEqual(plain.predict(success)['prediction'],plain.predict(failure)['prediction'])

    def test_new_identity_has_no_automatic_authorized_flow(self):
        first=dict(history=['["discover"]'],registry=[],error=False,
                   receipts=[dict(name='discover',source_arguments={},output={'node':'/a'},error=False)])
        rows=[replay.Boundary(first,[dict(name='inspect',args={'node':'/a'})],{'copy':str(i)}) for i in range(4)]
        policy=replay.Predictor('candidate');policy.fit(rows)
        current=dict(first,receipts=[dict(name='discover',source_arguments={},output={'node':'/b'},error=False)])
        decision=policy.predict(current)
        self.assertEqual(decision['proposed'],[dict(name='inspect',args={'node':'/b'})])
        self.assertIn('permitted_flow_unknown',decision['reason'])
        self.assertFalse(decision['execute'])


def adversarial_report():
    result = []
    for name, public, need_truth, binding_truth in scenarios():
        versions = []
        for version in range(3):
            a, b = h1(version, public), h2(version, public)
            versions.append({'version': version, 'H1': a, 'H2': b,
                             'H1_false_continuation': a != 'ABSTAIN' and not need_truth,
                             'H2_unjustified_binding': b != 'ABSTAIN' and not binding_truth})
        result.append({'synthetic_case': name, 'public_input': public, 'versions': versions,
                       'strong_C': {'H1': h1(2, public), 'H2': h2(2, public)},
                       'parent': 'error fallback already present; domain fill unavailable; no real parent execution',
                       'B': 'same_path_list_composite matches continuation where explicitly requested'})
    (replay.ART/'results/adversarial.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    adversarial_report()
    unittest.main()
