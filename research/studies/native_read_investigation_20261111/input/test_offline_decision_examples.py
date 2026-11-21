"""Tests of the stated deterministic toy model only."""
import unittest
from offline_decision_examples import Transport, costs_per_episode, batch_runtime_ms

class TestIllustrativePolicies(unittest.TestCase):
    def setUp(self):
        self.t = Transport(100,450,25)

    def test_short_calls_no_switch(self):
        r = costs_per_episode(2, self.t)
        self.assertEqual(r['online_rent_then_buy'], 200)
        self.assertEqual(r['offline_oracle'], 200)

    def test_long_calls_switch_with_regret(self):
        r = costs_per_episode(20, self.t)
        self.assertEqual(r['online_rent_then_buy'], 1400)
        self.assertEqual(r['offline_oracle'], 950)
        self.assertLess(r['online_rent_then_buy'],r['always_cli'])
        self.assertGreater(r['online_rent_then_buy'],r['always_persistent_cold'])

    def test_premium_competitive_under_fixed_cost_assumptions(self):
        # Exact finite enumeration checks algebra for n=0..300; not an ROSA claim.
        delta=self.t.cli_per_read-self.t.persistent_per_read
        for n in range(301):
            r=costs_per_episode(n,self.t)
            premium=r['online_rent_then_buy']-n*self.t.persistent_per_read
            offline_premium=min(n*delta,self.t.persistent_setup)
            self.assertLessEqual(premium,2*offline_premium+1e-9)

    def test_concurrency_action_contrasts(self):
        self.assertLess(batch_runtime_ms(8,4,80,4,0.8),batch_runtime_ms(8,2,80,4,0.8))
        self.assertLess(batch_runtime_ms(8,2,80,2,0.8),batch_runtime_ms(8,4,80,2,0.8))

if __name__ == '__main__':
    unittest.main()
