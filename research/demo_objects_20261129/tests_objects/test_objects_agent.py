"""Objects tools and agent integration, fake model and fake arm: ZERO model calls, no Gazebo, no MoveIt. Demonstration only, not for the paper.
Run in WSL with ROS sourced: python -m unittest discover -s tests_objects -v   (from research/demo_objects_20261129)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'demo_merged_20261122'))
from merged_demo import his_m  # noqa: E402
from merged_demo.events import EventLog  # noqa: E402
from merged_demo.fakes import FakeArm, FakeReadiness  # noqa: E402
from merged_demo.skill_tool import SkillRunner, ur5e_registry  # noqa: E402

import objects_lib as ol  # noqa: E402
import objects_skills as sk  # noqa: E402
from fakes_objects import FakeObjectsArm  # noqa: E402
from objects_agent import ObjectTools, make_objects_arm_class, OBJECT_RULES  # noqa: E402

try:
    H = his_m.load()
    SKIP = None
except his_m.HisFilesMissing as error:
    H, SKIP = None, str(error)


class SkillTests(unittest.TestCase):
    def test_where(self):
        out = sk.Skills(FakeObjectsArm()).where('red_block')
        self.assertTrue(out['ok'])
        self.assertEqual(out['evidence']['position'], [0.45, 0.1, 0.0225])
        self.assertFalse(sk.Skills(FakeObjectsArm()).where('green_cube')['ok'])

    def test_pick_and_place_succeed(self):
        arm = FakeObjectsArm(); s = sk.Skills(arm)
        p = s.pick(); self.assertTrue(p['ok'], p)
        self.assertTrue(s.is_held())
        q = s.place(); self.assertTrue(q['ok'], q)
        self.assertTrue(s.block_on_tray())
        self.assertFalse(arm.attached)

    def test_pick_refuses_unknown_object_without_moving(self):
        arm = FakeObjectsArm(); out = sk.Skills(arm).pick('green_cube')
        self.assertFalse(out['ok']); self.assertEqual(out['step'], 'precondition'); self.assertEqual(arm.moves, [])

    def test_pick_refuses_out_of_reach_without_moving(self):
        arm = FakeObjectsArm(block=(1.2, 0.0, 0.0225)); out = sk.Skills(arm).pick()
        self.assertEqual(out['step'], 'precondition'); self.assertEqual(arm.moves, [])

    def test_place_refuses_when_nothing_is_held(self):
        arm = FakeObjectsArm(); out = sk.Skills(arm).place()
        self.assertEqual(out['step'], 'precondition'); self.assertIn('not holding', out['detail']); self.assertEqual(arm.moves, [])

    def test_place_refuses_unknown_target(self):
        arm = FakeObjectsArm(); s = sk.Skills(arm); s.pick()
        n = len(arm.moves); out = s.place('red_block', 'shelf')
        self.assertFalse(out['ok']); self.assertEqual(len(arm.moves), n)

    def test_pick_planning_failure_stops_opens_gripper_and_does_not_retry(self):
        arm = FakeObjectsArm(fail={'move_to_pose'}); out = sk.Skills(arm).pick()
        self.assertFalse(out['ok']); self.assertEqual(out['step'], 'plan_pre_grasp')
        self.assertEqual(len([m for m in arm.moves if m[0] == 'pose']), 1)           # one attempt only
        self.assertEqual(arm.fingers, [0.0, 0.0]); self.assertFalse(arm.attached)

    def test_pick_fails_safe_when_fingers_close_on_nothing(self):
        arm = FakeObjectsArm(fail={'close_no_block'}); out = sk.Skills(arm).pick()
        self.assertEqual(out['step'], 'close'); self.assertFalse(arm.attached); self.assertEqual(arm.fingers, [0.0, 0.0])

    def test_pick_refuses_when_already_held(self):
        arm = FakeObjectsArm(); s = sk.Skills(arm); s.pick()
        out = s.pick(); self.assertEqual(out['step'], 'precondition'); self.assertIn('already held', out['detail'])

    def test_place_failure_does_not_claim_success(self):
        arm = FakeObjectsArm(); s = sk.Skills(arm); s.pick(); arm.fail.add('move_to_pose')
        out = s.place(); self.assertFalse(out['ok']); self.assertEqual(out['step'], 'plan_above_target')

    def test_grasp_yaw_reduction(self):
        import math
        self.assertAlmostEqual(sk.yaw_for_grasp(math.radians(100)), math.radians(10), places=6)
        self.assertAlmostEqual(sk.yaw_for_grasp(math.radians(-80)), math.radians(10), places=6)


class ToolTests(unittest.TestCase):
    def tools(self, **kw):
        arm = FakeObjectsArm(**kw); log = EventLog()
        return ObjectTools(sk.Skills(arm), log), arm, log

    def test_three_tools_named(self):
        t, *_ = self.tools()
        self.assertEqual([x.name for x in t.tools()], ['get_object_pose', 'pick', 'place'])

    def test_second_pick_is_refused_by_the_limit(self):
        t, arm, log = self.tools(); t.pick('red_block')
        out = json.loads(t.pick('red_block')); self.assertEqual(out['code'], 'pick_limit_reached')

    def test_one_object_tool_per_response(self):
        t, arm, log = self.tools(); n = [1]; t.request_of = lambda: n[0]
        self.assertTrue(json.loads(t.get_object_pose('red_block'))['ok'])
        self.assertEqual(json.loads(t.get_object_pose('tray'))['code'], 'one_object_tool_per_response')
        n[0] = 2; self.assertTrue(json.loads(t.get_object_pose('tray'))['ok'])

    def test_events_are_logged_with_evidence(self):
        t, arm, log = self.tools(); t.pick('red_block')
        end = log.of('object_call_end')[-1]; self.assertTrue(end['ok']); self.assertIn('block_after_lift', end['evidence'])


def episode(task, steps, fake_arm=None):
    from merged_demo.his_m import FakeToolModel
    path = Path(tempfile.mkdtemp()) / 'trace.jsonl'
    recorder = H['Recorder'](path); log = EventLog(sink=recorder)
    arm_fake = fake_arm or FakeObjectsArm()
    runner = SkillRunner(ur5e_registry(), {'state': FakeArm(), 'inspection': FakeReadiness()}, log)
    tools = ObjectTools(sk.Skills(arm_fake), log)
    arm = make_objects_arm_class(H)(recorder, dict(env='objects_demo', task={'id': 't', 'request': task, 'floor': 0}, ns=''), runner, tools)
    H['ros2'].execute_ros_command = lambda c: (False, 'canned')
    answer = error = None
    try:
        model = H['run_pilot'].ArmTracedModel(holder={'model': FakeToolModel(steps=steps)}, recorder=recorder, options={}, arm=arm)
        agent = H['run_pilot'].PilotROSA(model, arm)
        answer = agent._ROSA__executor.invoke({'input': task, 'chat_history': []}, config={'callbacks': [H['ToolRecorder'](recorder)]})['output']
    except Exception as failure:
        error = repr(failure)
    finally:
        arm.close()
    return answer, error, arm, arm_fake, tools, log, recorder


@unittest.skipIf(SKIP, SKIP)
class AgentTests(unittest.TestCase):
    def test_tool_set_has_his_menu_run_skill_and_the_three_object_tools(self):
        answer, error, arm, fake, tools, log, rec = episode('x', [[('final_answer', {'answer': {'x': 1}})]])
        offered = arm.base_menu()
        self.assertEqual(offered[-4:], ['run_skill', 'get_object_pose', 'pick', 'place'])
        self.assertIn('final_answer', ' '.join(str(m) for m in arm.prompt_messages) + 'final_answer')
        self.assertIn(OBJECT_RULES, [m[1] if isinstance(m, tuple) else m.get('content') for m in arm.prompt_messages])

    def test_where_is_the_red_block(self):
        answer, error, arm, fake, tools, log, rec = episode('Where is the red block?', [[('get_object_pose', {'name': 'red_block'})],
                                                          [('final_answer', {'answer': {'red_block': [0.45, 0.1, 0.0225]}})]])
        self.assertIsNone(error); self.assertEqual(fake.moves, []); self.assertEqual(json.loads(answer)['red_block'][0], 0.45)

    def test_put_the_red_block_on_the_tray(self):
        answer, error, arm, fake, tools, log, rec = episode('Put the red block on the tray.', [
            [('get_object_pose', {'name': 'red_block'})], [('pick', {'object': 'red_block'})], [('place', {'object': 'red_block', 'target': 'tray'})],
            [('final_answer', {'answer': {'done': True}})]])
        self.assertIsNone(error)
        self.assertEqual([e['tool'] for e in log.of('object_call_end')], ['get_object_pose', 'pick', 'place'])
        self.assertTrue(all(e['ok'] for e in log.of('object_call_end')))

    def test_two_object_tools_in_one_response_second_refused(self):
        answer, error, arm, fake, tools, log, rec = episode('x', [[('pick', {'object': 'red_block'}), ('place', {'object': 'red_block', 'target': 'tray'})],
                                                          [('final_answer', {'answer': {'x': 1}})]])
        self.assertEqual(tools.counts, {'pick': 1, 'place': 0})
        self.assertFalse(any(e['tool'] == 'place' for e in log.of('object_call_end')))

    def test_place_without_pick_is_refused_and_arm_does_not_move(self):
        answer, error, arm, fake, tools, log, rec = episode('x', [[('place', {'object': 'red_block', 'target': 'tray'})], [('final_answer', {'answer': {'x': 1}})]])
        self.assertEqual(fake.moves, []); self.assertFalse(log.of('object_call_end')[0]['ok'])

    def test_unknown_object_pick_is_refused(self):
        answer, error, arm, fake, tools, log, rec = episode('x', [[('pick', {'object': 'green_cube'})], [('final_answer', {'answer': {'x': 1}})]])
        self.assertEqual(fake.moves, []); self.assertEqual(log.of('object_call_end')[0]['step'], 'precondition')


if __name__ == '__main__':
    unittest.main()
