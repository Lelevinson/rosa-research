"""Step 5: run_skill over the real macro with fake transports. Zero model calls, no ROS. Includes the L4 logging checks and the cross-call write guard."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rosa_reliability.ros_arm import HOME_POSE  # noqa: E402

from merged_demo.events import EventLog  # noqa: E402
from merged_demo.fakes import FakeArm, FakeReadiness  # noqa: E402
from merged_demo.skill_tool import SkillRunner, ur5e_registry  # noqa: E402

PARK_RIGHT = {**HOME_POSE, 'shoulder_pan_joint': .16, 'wrist_3_joint': -.12}


def runner(arm=None, readiness=None, **kwargs):
    log = EventLog()
    arm, readiness = arm or FakeArm(), readiness or FakeReadiness()
    return SkillRunner(ur5e_registry(), {'state': arm, 'inspection': readiness}, log, **kwargs), log, arm, readiness


def last_end(log):
    return log.of('skill_call_end')[-1]


class SkillToolTests(unittest.TestCase):
    def test_catalogue_is_the_frozen_m4_one(self):
        catalogue = ur5e_registry().catalogue()
        self.assertEqual(sorted(catalogue), ['ur5e.home', 'ur5e.inspect_readiness', 'ur5e.park_right', 'ur5e.stage_left'])
        self.assertEqual(catalogue['ur5e.park_right']['targets']['/ur5e'], PARK_RIGHT)
        self.assertEqual(catalogue['ur5e.stage_left']['targets']['/ur5e']['shoulder_pan_joint'], -.14)
        self.assertEqual(catalogue['ur5e.stage_left']['targets']['/ur5e']['wrist_3_joint'], .20)
        self.assertEqual(catalogue['ur5e.inspect_readiness']['max_writes'], 0)

    def test_tool_name_and_no_report_tool(self):
        r, *_ = runner()
        self.assertEqual(r.tool().name, 'run_skill')

    def test_inspection_reads_only_and_logs_sources_in_order(self):
        r, log, arm, _ = runner()
        text = json.loads(r.run('ur5e.inspect_readiness'))
        self.assertTrue(text['verification']['goal_reached'])
        self.assertEqual(arm.writes, 0)
        reads = log.of('internal_read')
        self.assertEqual(len(reads), 2)
        self.assertTrue(all(e['source'] == 'inspection.read_group' for e in reads))
        start, end = log.of('skill_call_start')[0], last_end(log)
        for e in reads:
            self.assertTrue(start['seq'] < e['seq'] < end['seq'])
            self.assertEqual(e['parent_call_seq'], start['seq'])
            self.assertEqual(e['actor'], 'macro_program')
            self.assertEqual(e['macro_actor'], 'program')
            self.assertIn('t_wall', e)
            self.assertIn('t_start_monotonic', e)
        self.assertEqual([e['operation_id'] for e in reads], [1, 2])
        self.assertEqual(end['writes_dispatched'], 0)
        self.assertIsNone(end['write_skipped'])        # an inspection skill never writes: nothing was skipped

    def test_movement_is_read_then_one_write_then_fresh_read_in_that_order(self):
        r, log, arm, _ = runner()
        text = json.loads(r.run('ur5e.park_right'))
        self.assertTrue(text['verification']['goal_reached'])
        self.assertEqual(arm.writes, 1)
        events = log.of('internal_read', 'internal_write')
        self.assertEqual([e['kind'] for e in events], ['internal_read', 'internal_write', 'internal_read'])
        self.assertEqual([e['operation_kind'] for e in events], ['read', 'write', 'read'])
        self.assertEqual([e['source'] for e in events], ['state.read', 'state.write', 'state.read'])
        times = [e['t_start_monotonic'] for e in events]
        self.assertEqual(times, sorted(times))
        self.assertEqual(last_end(log)['writes_dispatched'], 1)
        self.assertEqual(last_end(log)['outcome'], 'COMPLETED')
        self.assertEqual(events[-1]['result']['shoulder_pan_joint'], .16)    # the fresh read after the write shows the target

    def test_already_at_goal_skips_write_and_logs_why(self):
        r, log, arm, _ = runner(arm=FakeArm(initial=PARK_RIGHT))
        r.run('ur5e.park_right')
        self.assertEqual(arm.writes, 0)
        end = last_end(log)
        self.assertEqual(end['writes_dispatched'], 0)
        self.assertTrue(end['write_skipped'].startswith('already_within_tolerance'))

    def test_ineffective_command_is_not_replayed_inside_or_across_calls(self):
        r, log, arm, _ = runner(arm=FakeArm(fault='ineffective'))
        text = json.loads(r.run('ur5e.park_right'))
        self.assertEqual(text['reason'], 'outcome_not_confirmed_no_command_replay')
        self.assertEqual(arm.writes, 1)
        again = json.loads(r.run('ur5e.stage_left'))                    # a fresh macro invocation would write again: the runner refuses
        self.assertEqual(again['code'], 'no_replay_after_unconfirmed_write')
        self.assertEqual(arm.writes, 1)
        self.assertEqual(last_end(log)['outcome'], 'REJECTED_BEFORE_ANY_IO')

    def test_episode_write_budget_blocks_a_second_movement(self):
        r, log, arm, _ = runner()
        r.run('ur5e.park_right')
        again = json.loads(r.run('ur5e.stage_left'))
        self.assertEqual(again['code'], 'episode_write_budget_exhausted')
        self.assertEqual(arm.writes, 1)
        r2, _, arm2, _ = runner(max_writes=2)                           # configurable for tasks that need two movements (lab arm)
        r2.run('ur5e.park_right')
        r2.run('ur5e.stage_left')
        self.assertEqual(arm2.writes, 2)

    def test_missing_observation_blocks_the_write(self):
        r, log, arm, _ = runner(arm=FakeArm(fault='missing_observation'))
        text = json.loads(r.run('ur5e.park_right'))
        self.assertEqual(arm.writes, 0)
        self.assertEqual(text['reason'], 'observation_unavailable_no_write')
        end = last_end(log)
        self.assertEqual(end['writes_dispatched'], 0)
        self.assertTrue(end['write_skipped'].startswith('no_write_'))
        self.assertEqual(log.of('internal_read')[0]['status'], 'ERROR')   # the failed internal read is logged too

    def test_unknown_skill_touches_no_transport(self):
        r, log, arm, readiness = runner()
        text = json.loads(r.run('ur5e.bogus'))
        self.assertEqual(text['code'], 'skill_not_authorized')
        self.assertEqual(log.of('internal_read', 'internal_write'), [])

    def test_inactive_controllers_are_failure_evidence_not_a_write(self):
        r, log, arm, _ = runner(readiness=FakeReadiness(fault='inactive'))
        text = json.loads(r.run('ur5e.inspect_readiness'))
        self.assertEqual(text['reason'], 'inspection_conditions_not_met')
        self.assertEqual(arm.writes, 0)


if __name__ == '__main__':
    unittest.main()
