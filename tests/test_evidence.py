import unittest
from langchain_core.tools import ToolException
from rosa_reliability.evidence import EvidenceSession


class Transport:
    requires_observation = True
    def __init__(self):
        self.value = 0.1
        self.partial_failure = False
    def read(self, node, names):
        return {'position': self.value}
    def write(self, node, values):
        self.value = values['position']
        if self.partial_failure:
            raise RuntimeError('partial_write')
        return {'accepted': True}


class EvidenceTests(unittest.TestCase):
    def test_fresh_read_is_accepted_without_named_verifier_or_hidden_operations(self):
        transport = Transport()
        session = EvidenceSession(transport, {'/fixture': {'position': 0.1}})
        observed = session.read(['/fixture'])
        result = session.report('SUCCESS', observed['observed_values'])
        self.assertTrue(result['report_accepted'])
        self.assertEqual(len(session.budget.events), 1)

    def test_partial_failed_write_invalidates_old_read_even_without_write_receipt(self):
        transport = Transport()
        session = EvidenceSession(transport, {'/fixture': {'position': 0.1}})
        old = session.read(['/fixture'])
        transport.partial_failure = True
        with self.assertRaises(RuntimeError):
            session.write('/fixture', {'position': 0.3})
        with self.assertRaisesRegex(ToolException, 'fresh_verification_required'):
            session.report('SUCCESS', old['observed_values'])
        observed = session.read(['/fixture'])
        self.assertTrue(session.report('FAILURE', observed['observed_values'])['report_accepted'])

    def test_new_read_replaces_previous_verifier_evidence(self):
        transport = Transport()
        session = EvidenceSession(transport, {'/fixture': {'position': 0.2}})
        session.verify()
        transport.value = 0.2
        observed = session.read(['/fixture'])
        self.assertTrue(session.report('SUCCESS', observed['observed_values'])['report_accepted'])


if __name__ == '__main__':
    unittest.main()
