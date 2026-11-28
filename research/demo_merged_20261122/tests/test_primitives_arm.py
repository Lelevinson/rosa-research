"""Arm (b) "M + primitives" scripted tests. Fake model, fake transports, canned ROS output: ZERO model calls, no ROS graph, no Gazebo.
LABEL: merged-method demo, arm (b), demonstration only, not evaluated, not for the paper. Run location is recorded in the run log (laptop dry check vs lab run)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rosa_reliability.bounded_macro import MacroLimits  # noqa: E402
from rosa_reliability.ros_arm import HOME_POSE  # noqa: E402

from merged_demo import his_m, prompts  # noqa: E402
from merged_demo.events import EventLog  # noqa: E402
from merged_demo.fakes import FakeArm, FakeReadiness  # noqa: E402
from merged_demo.primitive_prompts import MACRO_RULES, PRIMITIVE_LINE, PRIMITIVE_RULES  # noqa: E402
from merged_demo.primitives_tool import PrimitiveRunner, TOOL_NAMES  # noqa: E402
from merged_demo.skill_tool import ur5e_registry  # noqa: E402

try:
    H = his_m.load()
    SKIP = None
except his_m.HisFilesMissing as error:
    H, SKIP = None, str(error)

PARK_RIGHT = {**HOME_POSE, 'shoulder_pan_joint': .16, 'wrist_3_joint': -.12}


def runner(arm=None, readiness=None, **kwargs):
    log = EventLog()
    arm, readiness = arm or FakeArm(), readiness or FakeReadiness()
    return PrimitiveRunner(ur5e_registry(), {'state': arm, 'inspection': readiness}, log, **kwargs), log, arm


def code(text):
    return json.loads(text).get('code')


class PrimitiveToolTests(unittest.TestCase):
    def test_four_tools_and_no_run_skill(self):
        r, *_ = runner()
        self.assertEqual([t.name for t in r.tools()], ['read_pose', 'read_readiness', 'write_pose', 'verify_pose'])
        self.assertEqual(TOOL_NAMES, ('read_pose', 'read_readiness', 'write_pose', 'verify_pose'))

    def test_same_catalogue_and_targets_as_arm_a(self):
        r, *_ = runner()
        self.assertEqual(r.registry.catalogue()['ur5e.park_right']['targets']['/ur5e'], PARK_RIGHT)
        self.assertIn('ur5e.park_right: ', r.tools()[2].description)

    def test_read_readiness_reads_same_two_groups_as_the_macro(self):
        r, log, arm = runner()
        out = json.loads(r.read_readiness())
        self.assertTrue(out['all_true'])
        reads = log.of('internal_read')
        self.assertEqual([e['arguments'][0] for e in reads], ['controllers', 'joint_state'])
        self.assertTrue(all(e['actor'] == 'model_primitive' and e['source'] == 'inspection.read_group' for e in reads))
        self.assertEqual(arm.writes, 0)

    def test_read_write_verify_sequence_by_the_model(self):
        r, log, arm = runner()
        self.assertIn('observed_values', json.loads(r.read_pose()))
        w = json.loads(r.write_pose('ur5e.park_right'))
        self.assertTrue(w['write_dispatched'])
        self.assertFalse(w['verified'])
        self.assertTrue(r.unconfirmed_write)
        v = json.loads(r.verify_pose('ur5e.park_right'))
        self.assertTrue(v['goal_reached'])
        self.assertFalse(r.unconfirmed_write)
        self.assertEqual((arm.writes, r.writes_total, r.calls), (1, 1, 3))
        kinds = [e['kind'] for e in log.events if e['kind'].startswith('internal')]
        self.assertEqual(kinds, ['internal_read', 'internal_write', 'internal_read'])
        write = log.of('internal_write')[0]
        self.assertEqual(write['arguments'][1], PARK_RIGHT)
        self.assertTrue(all(e['t_wall'] and 't_start_monotonic' in e for e in log.of('internal_read', 'internal_write')))

    def test_write_needs_a_prior_read(self):
        r, log, arm = runner()
        self.assertEqual(code(r.write_pose('ur5e.park_right')), 'read_required_before_write')
        self.assertEqual(arm.writes, 0)

    def test_one_write_per_task(self):
        r, log, arm = runner()
        r.read_pose(); r.write_pose('ur5e.park_right'); r.verify_pose('ur5e.park_right')
        self.assertEqual(code(r.write_pose('ur5e.stage_left')), 'episode_write_budget_exhausted')
        self.assertEqual(arm.writes, 1)

    def test_no_replay_after_unconfirmed_write(self):
        arm = FakeArm(fault='ineffective')          # the write is accepted but the arm does not move
        r, log, _ = runner(arm=arm, max_writes=2)
        r.read_pose(); r.write_pose('ur5e.park_right')
        v = json.loads(r.verify_pose('ur5e.park_right'))
        self.assertFalse(v['goal_reached'])
        self.assertTrue(r.unconfirmed_write)
        self.assertEqual(code(r.write_pose('ur5e.park_right')), 'no_replay_after_unconfirmed_write')
        self.assertEqual(arm.writes, 1)

    def test_unknown_id_refused_without_counting_and_inspection_id_is_not_a_movement(self):
        r, log, arm = runner()
        r.read_pose()
        before = r.attempts
        self.assertEqual(code(r.write_pose('ur5e.nowhere')), 'skill_not_authorized')
        self.assertEqual(r.attempts, before)
        self.assertEqual(code(r.write_pose('ur5e.inspect_readiness')), 'not_a_movement_skill')
        self.assertEqual(arm.writes, 0)

    def test_target_outside_bound_is_rejected_by_the_transports_own_check(self):
        r, log, arm = runner()
        r.read_pose()
        arm.validate_write = lambda node, values: 'target outside the bounded range'
        self.assertEqual(code(r.write_pose('ur5e.park_right')), 'target_rejected')
        self.assertEqual(arm.writes, 0)

    def test_one_primitive_per_response(self):
        r, log, arm = runner()
        n = [1]
        r.request_of = lambda: n[0]
        self.assertIn('observed_values', json.loads(r.read_pose()))
        self.assertEqual(code(r.read_pose()), 'one_primitive_per_response')
        n[0] = 2
        self.assertIn('observed_values', json.loads(r.read_pose()))

    def test_native_operation_budget_of_ten(self):
        r, log, arm = runner(limits=MacroLimits(tool_attempts=40))
        outcomes = [code(r.read_pose()) for _ in range(12)]
        self.assertEqual(outcomes[:10], [None] * 10)
        self.assertEqual(outcomes[10:], ['native_operation_budget_exhausted'] * 2)

    def test_tool_attempt_budget_of_sixteen(self):
        r, log, arm = runner(limits=MacroLimits(native_operations=40))
        outcomes = [code(r.read_pose()) for _ in range(18)]
        self.assertEqual(outcomes[:16], [None] * 16)
        self.assertEqual(outcomes[16:], ['tool_attempt_budget_exhausted'] * 2)

    def test_missing_observation_is_returned_as_text_not_raised(self):
        r, log, arm = runner(arm=FakeArm(fault='missing_observation'))
        out = json.loads(r.read_pose())
        self.assertTrue(out['stopped'])
        self.assertFalse(r.read_done)

    def test_readiness_source_unavailable_is_returned_as_text(self):
        r, log, arm = runner(readiness=FakeReadiness(fault='joint_state'))
        out = json.loads(r.read_readiness())
        self.assertTrue(out['stopped'])
        self.assertEqual(r.writes_total, 0)

    def test_prompt_differs_from_arm_a_only_in_the_run_skill_wording(self):
        self.assertNotIn('run_skill', PRIMITIVE_RULES + PRIMITIVE_LINE)
        a, b = MACRO_RULES.split('. '), PRIMITIVE_RULES.split('. ')
        self.assertEqual(len(a), len(b))
        self.assertEqual([i for i, (x, y) in enumerate(zip(a, b)) if x != y], [0])      # only the first sentence changes
        self.assertEqual(prompts.MACRO_RULES, MACRO_RULES)                              # arm (a) prompt module untouched


def canned(command):
    if command.startswith('ros2 topic info'):
        return True, 'Type: sensor_msgs/msg/JointState\n\nPublisher count: 1\n\nNode name: joint_state_broadcaster\nNode namespace: /\n'
    return False, 'canned: not available for ' + command


def episode(task, steps, arm=None, **kwargs):
    from merged_demo.his_m import FakeToolModel
    from merged_demo.his_m_primitives import make_primitive_arm_class
    holder = {}
    path = Path(tempfile.mkdtemp()) / 'trace.jsonl'
    recorder = H['Recorder'](path)
    log = EventLog(sink=recorder)
    holder['arm'] = arm or FakeArm()
    runner_obj = PrimitiveRunner(ur5e_registry(), {'state': holder['arm'], 'inspection': FakeReadiness()}, log, **kwargs)
    arm_obj = make_primitive_arm_class(H)(recorder, dict(env='merged_demo_b', task={'id': 'demo', 'request': task, 'floor': 0}, ns=''), runner_obj)
    H['ros2'].execute_ros_command = canned
    answer = error = None
    try:
        model = H['run_pilot'].ArmTracedModel(holder={'model': FakeToolModel(steps=steps)}, recorder=recorder, options={}, arm=arm_obj)
        agent = H['run_pilot'].PilotROSA(model, arm_obj)
        result = agent._ROSA__executor.invoke({'input': task, 'chat_history': []}, config={'callbacks': [H['ToolRecorder'](recorder)]})
        answer = result['output']
    except Exception as failure:
        error = repr(failure)
    finally:
        arm_obj.close()
    return answer, error, arm_obj, recorder, runner_obj, holder['arm']


@unittest.skipIf(SKIP, SKIP)
class ArmBThroughHisMachineryTests(unittest.TestCase):
    D2 = 'Check that the arm is ready to move. If it is ready, move it to park_right. Report readiness and the final shoulder_pan_joint position as a JSON object.'
    D3 = 'Move the arm to stage_left, then confirm with a fresh joint sample. Report the confirmed shoulder_pan_joint and wrist_3_joint as a JSON object.'

    def test_offered_tools_are_his_menu_plus_four_primitives_and_no_run_skill(self):
        answer, error, arm, rec, run, fake = episode(self.D2, [[('final_answer', {'answer': {'x': 1}})]])
        self.assertIsNone(error)
        offered = arm.base_menu()
        self.assertEqual(offered[-4:], list(TOOL_NAMES))
        self.assertNotIn('run_skill', offered)
        self.assertEqual(sum(1 for n in offered if n in TOOL_NAMES), 4)

    def test_D2_model_sequences_readiness_read_write_verify(self):
        answer, error, arm, rec, run, fake = episode(self.D2, [
            [('read_readiness', {})],
            [('read_pose', {})],
            [('write_pose', {'skill_id': 'ur5e.park_right'})],
            [('verify_pose', {'skill_id': 'ur5e.park_right'})],
            [('final_answer', {'answer': {'ready': True, 'shoulder_pan_joint': 0.16}})]])
        self.assertIsNone(error)
        self.assertEqual(json.loads(answer)['shoulder_pan_joint'], 0.16)
        self.assertEqual((fake.writes, run.writes_total, run.calls), (1, 1, 4))
        self.assertEqual([r['tool'] for r in rec.rows if r['kind'] == 'macro_primitive_call_end'], ['read_readiness', 'read_pose', 'write_pose', 'verify_pose'])
        self.assertTrue(all(e['outcome'] == 'COMPLETED' for e in run.log.of('primitive_call_end')))

    def test_D3_move_then_verify(self):
        answer, error, arm, rec, run, fake = episode(self.D3, [
            [('read_pose', {})], [('write_pose', {'skill_id': 'ur5e.stage_left'})], [('verify_pose', {'skill_id': 'ur5e.stage_left'})],
            [('final_answer', {'answer': {'shoulder_pan_joint': -0.14, 'wrist_3_joint': 0.2}})]])
        self.assertIsNone(error)
        self.assertEqual(fake.writes, 1)
        self.assertEqual(len(run.log.of('internal_write')), 1)

    def test_two_primitives_in_one_response_second_is_refused(self):
        answer, error, arm, rec, run, fake = episode(self.D2, [
            [('read_pose', {}), ('write_pose', {'skill_id': 'ur5e.park_right'})],
            [('final_answer', {'answer': {'x': 1}})]])
        self.assertIsNone(error)
        self.assertEqual(fake.writes, 0)
        self.assertIn('one_primitive_per_response', [e.get('code') for e in run.log.of('primitive_call_end')])

    def test_write_without_read_cannot_move_the_arm_through_his_machinery(self):
        answer, error, arm, rec, run, fake = episode(self.D2, [
            [('write_pose', {'skill_id': 'ur5e.park_right'})], [('final_answer', {'answer': {'x': 1}})]])
        self.assertEqual(fake.writes, 0)
        self.assertIn('read_required_before_write', [e.get('code') for e in run.log.of('primitive_call_end')])


if __name__ == '__main__':
    unittest.main()
