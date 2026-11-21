"""Step 4 (real files): his method-M code, byte for byte at e233cf5, plus run_skill. Fake model, canned ROS output: zero model calls, no ROS graph, no Gazebo.
Skipped with an instruction if his files were not extracted (extract_his_files.sh)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from merged_demo import his_m  # noqa: E402

try:
    H = his_m.load()
    SKIP = None
except his_m.HisFilesMissing as error:
    H, SKIP = None, str(error)

from merged_demo.events import EventLog  # noqa: E402
from merged_demo.fakes import FakeArm, FakeReadiness  # noqa: E402
from merged_demo.skill_tool import SkillRunner, ur5e_registry  # noqa: E402

TOPIC_INFO = ('Type: sensor_msgs/msg/JointState\n\nPublisher count: 1\n\nNode name: joint_state_broadcaster\nNode namespace: /\nTopic type: sensor_msgs/msg/JointState\n\n'
              'Subscription count: 0\n')
ECHO = 'name:\n- shoulder_pan_joint\n- wrist_3_joint\nposition:\n- 0.0\n- 0.0\n'


def canned(command):
    if command.startswith('ros2 topic info'):
        return True, TOPIC_INFO
    if command.startswith('ros2 topic echo'):
        return True, ECHO
    return False, 'canned: not available for ' + command


def episode(task, steps, arm=None, **runner_kwargs):
    holder = {}

    def factory(recorder):
        holder['arm'] = arm or FakeArm()
        log = EventLog(sink=recorder)
        holder['log'] = log
        holder['runner'] = SkillRunner(ur5e_registry(), {'state': holder['arm'], 'inspection': FakeReadiness()}, log, **runner_kwargs)
        return holder['runner']
    path = Path(tempfile.mkdtemp()) / 'trace.jsonl'
    answer, error, arm_obj, recorder = his_m.run_dry(H, task, steps, factory, path, canned)
    return answer, error, arm_obj, recorder, holder


@unittest.skipIf(SKIP, SKIP)
class HisFilesTests(unittest.TestCase):
    def test_all_26_rows_verified_byte_for_byte(self):
        self.assertEqual(len(his_m.verify()), 26)

    def test_his_modules_come_from_his_files_not_our_reconstruction(self):
        self.assertTrue(str(Path(H['answer_gate'].__file__).resolve()).startswith(str(his_m.HIS_ROOT.resolve())))
        self.assertTrue(hasattr(H['exam_arms'], 'ExamArm'))
        self.assertEqual(H['run_pilot'].NUM_CTX, 65536)
        self.assertEqual(H['run_pilot'].MAX_ITERATIONS, 40)


@unittest.skipIf(SKIP, SKIP)
class MergedRunTests(unittest.TestCase):
    D1 = 'Which node publishes /joint_states, and what are the current shoulder_pan_joint and wrist_3_joint positions? Answer as a JSON object.'
    D2 = 'Check that the arm is ready to move. If it is ready, move it to park_right. Report readiness and the final shoulder_pan_joint position as a JSON object.'

    def rows(self, recorder, *kinds):
        return [r for r in recorder.rows if r['kind'] in kinds]

    def test_D1_his_menu_finish_and_name_fix_with_his_real_ledger(self):
        answer, error, arm, rec, h = episode(self.D1, [
            [('ros2_topic_info', {'topics': ['/joint_states']})],
            [('ros2_topic_echo', {'topic': '/joint_states', 'count': 1, 'return_echoes': True})],
            [('final_answer', {'answer': {'publisher': 'joint_state_broadcaster', 'shoulder_pan_joint': 0.0, 'wrist_3_joint': 0.0}})]])
        self.assertIsNone(error)
        self.assertEqual(json.loads(answer)['publisher'], '/joint_state_broadcaster')       # his name fix, his ledger
        original = self.rows(rec, 'final_answer_original')[0]
        self.assertEqual(original['answer']['publisher'], 'joint_state_broadcaster')         # raw answer kept
        self.assertTrue(self.rows(rec, 'handler'))
        self.assertEqual(h['arm'].writes, 0)

    def test_offered_tools_are_his_12_plus_final_answer_plus_run_skill(self):
        _, _, arm, rec, _ = episode(self.D1, [[('final_answer', {'answer': {'a': 1}})]])
        offered = [r for r in self.rows(rec, 'handler') if r.get('event') == 'tools_offered'][0]['names']
        self.assertEqual(sorted(offered), sorted(list(H['harness'].DOMAIN_TOOLS) + ['final_answer', 'run_skill']))   # order is the order the ROSA registry binds them
        for forbidden in ('ros2_param_set', 'ros2_service_call', 'submit_report'):
            self.assertNotIn(forbidden, offered)

    def test_D2_inspect_then_move_and_internal_reads_sit_in_his_trace(self):
        answer, error, arm, rec, h = episode(self.D2, [
            [('run_skill', {'skill_id': 'ur5e.inspect_readiness'})],
            [('run_skill', {'skill_id': 'ur5e.park_right'})],
            [('final_answer', {'answer': {'ready': True, 'shoulder_pan_joint': 0.16}})]])
        self.assertIsNone(error)
        self.assertEqual(json.loads(answer), {'ready': True, 'shoulder_pan_joint': 0.16})
        self.assertEqual(h['arm'].writes, 1)
        macro = [r for r in rec.rows if r['kind'].startswith('macro_internal_')]
        self.assertEqual([r['kind'] for r in macro], ['macro_internal_read'] * 2 + ['macro_internal_read', 'macro_internal_write', 'macro_internal_read'])
        for r in macro:                                           # L4: source, time and sequence position
            for key in ('source', 'actor', 'seq', 'trace_row', 't_wall', 't_start_monotonic', 'parent_call_seq'):
                self.assertIn(key, r)
        links = [r for r in rec.rows if r['kind'] == 'macro_operation_link']
        self.assertEqual(sorted(l['linked_seq'] for l in links), sorted(r['seq'] for r in macro))     # every internal call is linked to the macro's own operation id
        self.assertTrue(all(l['macro_actor'] == 'program' for l in links))
        index = {id(r): i for i, r in enumerate(rec.rows)}
        positions = [index[id(r)] for r in macro]
        self.assertEqual(positions, sorted(positions))
        tool_starts = [i for i, r in enumerate(rec.rows) if r['kind'] == 'tool_start' and r.get('name') == 'run_skill']
        self.assertEqual(len(tool_starts), 2)
        self.assertTrue(tool_starts[0] < positions[0] < positions[1] < tool_starts[1] < positions[2])   # reads sit between their tool_start and the next call

    def test_strict_precheck_text_for_run_skill_and_no_transport_touch(self):
        answer, error, arm, rec, h = episode(self.D2, [[('run_skill', {'skill_id': 5})], [('final_answer', {'answer': {'a': 1}})]])
        self.assertIsNone(error)
        events = [r for r in rec.rows if r['kind'] == 'handler' and r.get('event') == 'validation_error']
        self.assertTrue(events and "field 'skill_id'" in events[0]['message'])
        self.assertEqual([r for r in rec.rows if r['kind'].startswith('macro_internal_')], [])

    def test_two_run_skill_in_one_response_second_is_refused(self):
        answer, error, arm, rec, h = episode(self.D2, [
            [('run_skill', {'skill_id': 'ur5e.inspect_readiness'}), ('run_skill', {'skill_id': 'ur5e.park_right'})],
            [('final_answer', {'answer': {'a': 1}})]])
        self.assertIsNone(error)
        self.assertEqual(h['arm'].writes, 0)
        ends = h['log'].of('skill_call_end')
        self.assertEqual([e.get('code') for e in ends if e['outcome'] == 'REJECTED_BEFORE_ANY_IO'], ['one_run_skill_per_response'])

    def test_write_tool_is_not_available(self):
        answer, error, arm, rec, h = episode(self.D1, [[('ros2_param_set', {'node_name': '/x', 'param_name': 'a', 'param_value': '1'})], [('final_answer', {'answer': {'a': 1}})]])
        self.assertIsNone(error)
        self.assertTrue([r for r in rec.rows if r['kind'] == 'handler' and r.get('event') in ('tool_not_offered', 'blocked_write_tool')])

    def test_merged_arm_differs_from_his_M_only_by_the_tool_and_two_prompt_lines(self):
        rec = H['Recorder'](Path(tempfile.mkdtemp()) / 't.jsonl')
        ctx = dict(env='x', task={'id': 'd', 'request': 'x', 'floor': 0}, ns='')
        base = H['exam_arms'].make_arm('M', rec, ctx)
        merged = his_m.make_arm_class(H)(rec, ctx, SkillRunner(ur5e_registry(), {'state': FakeArm(), 'inspection': FakeReadiness()}, EventLog()))
        self.assertEqual(merged.base_menu(), base.base_menu() + ['run_skill'])
        extra = [m for m in merged.prompt_messages if m not in base.prompt_messages]
        self.assertEqual(len(extra), 2)
        self.assertEqual([m for m in merged.prompt_messages if m in base.prompt_messages], base.prompt_messages)   # his lines unchanged and in his order


if __name__ == '__main__':
    unittest.main()
