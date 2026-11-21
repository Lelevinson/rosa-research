"""Step 4: the name fix = his public namefix_rule.py + the labelled answer_gate reconstruction. Zero model calls."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from merged_demo.namefix import NameFixer  # noqa: E402

TOPIC_INFO = {'/joint_states': {'info': 'Type: sensor_msgs/msg/JointState\n\nPublisher count: 1\n\nNode name: joint_state_broadcaster\nNode namespace: /\nTopic type: sensor_msgs/msg/JointState\n'}}


class NameFixTests(unittest.TestCase):
    def setUp(self):
        self.fixer = NameFixer()

    def test_provenance_says_reconstruction(self):
        self.assertIn('RECONSTRUCTION', self.fixer.provenance['answer_gate_source'])
        self.assertEqual(len(self.fixer.provenance['namefix_rule_sha256']), 64)
        self.assertIn('name-rewrite-v2', self.fixer.rule.RULE_NAME)

    def test_short_name_becomes_the_one_full_name_seen(self):
        answer, events, size = self.fixer.apply('Which node publishes /joint_states?', [TOPIC_INFO], {'publisher': 'joint_state_broadcaster', 'x': 0.5})
        self.assertEqual(answer, {'publisher': '/joint_state_broadcaster', 'x': 0.5})
        self.assertEqual([e['kind'] for e in events], ['rewrite'])
        self.assertIn('/joint_state_broadcaster', self.fixer.gate.allowed_names('', [TOPIC_INFO]))    # the joined name (Node name + Node namespace)

    def test_full_name_and_numbers_are_untouched(self):
        answer, events, _ = self.fixer.apply('t', [TOPIC_INFO], {'publisher': '/joint_state_broadcaster', 'shoulder_pan_joint': 0.16})
        self.assertEqual(answer, {'publisher': '/joint_state_broadcaster', 'shoulder_pan_joint': 0.16})
        self.assertEqual(events, [])

    def test_two_candidates_is_left_alone_and_logged(self):
        outputs = [{'nodes': ['/a/probe', '/b/probe']}]
        answer, events, _ = self.fixer.apply('t', outputs, {'node': 'probe'})
        self.assertEqual(answer, {'node': 'probe'})
        self.assertEqual(events[0]['kind'], 'reject_ambiguous')

    def test_failed_results_do_not_enter_the_ledger(self):
        allowed = self.fixer.gate.allowed_names('', [{'error': 'no such node /ghost/probe'}, {'/x': {'error': 'bad /ghost2/y'}, '/z': {'ok': '/real/node'}}])
        self.assertNotIn('/ghost/probe', allowed)
        self.assertNotIn('/ghost2/y', allowed)
        self.assertIn('/real/node', allowed)


if __name__ == '__main__':
    unittest.main()
