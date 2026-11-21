"""Step 6: scripted end-to-end dry run of D1-D3 with a FAKE model (no model call, no GPU, no ROS, no Gazebo) plus the loop's negative cases."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from merged_demo import menu, prompts  # noqa: E402
from merged_demo.events import EventLog  # noqa: E402
from merged_demo.fakes import FakeArm, FakeReadiness, ScriptedModel, canned_menu  # noqa: E402
from merged_demo.loop import run_episode  # noqa: E402
from merged_demo.namefix import NameFixer  # noqa: E402
from merged_demo.skill_tool import SkillRunner, ur5e_registry  # noqa: E402

TOPIC_INFO = {'/joint_states': {'info': 'Type: sensor_msgs/msg/JointState\n\nPublisher count: 1\n\nNode name: joint_state_broadcaster\nNode namespace: /\n'}}
ECHO = {'/joint_states': {'name': ['shoulder_pan_joint', 'wrist_3_joint'], 'position': [0.0, 0.0]}}
TASKS = {t['id']: t for t in prompts.load_tasks()['tasks']}


def build(steps, arm=None, max_writes=1):
    log, registry = EventLog(), ur5e_registry()
    arm = arm or FakeArm()
    runner = SkillRunner(registry, {'state': arm, 'inspection': FakeReadiness()}, log, max_writes=max_writes)
    real = menu.stock_menu()
    tools = canned_menu(real, {n: {'info': 'canned'} for n in menu.MENU_NAMES} | {'ros2_topic_info': TOPIC_INFO, 'ros2_topic_echo': ECHO}) + [runner.tool()]
    system, _ = prompts.load_prompt()
    return log, registry, runner, tools, system, ScriptedModel(steps), arm


def go(task_id, steps, **kw):
    log, registry, runner, tools, system, model, arm = build(steps, **kw)
    result = run_episode(TASKS[task_id]['text'], model, tools, system, log, registry=registry, name_fixer=NameFixer(), skill_runner=runner)
    return result, log, arm


class DryRunTests(unittest.TestCase):
    def test_tasks_file_matches_the_plan(self):
        self.assertEqual(sorted(TASKS), ['D1', 'D2', 'D3'])

    def test_D1_question_menu_finish_and_name_fix(self):
        result, log, arm = go('D1', [[('ros2_topic_info', {'topics': ['/joint_states']})],
                                     [('ros2_topic_echo', {'topic': '/joint_states', 'count': 1, 'return_echoes': True})],
                                     [('final_answer', {'answer': {'publisher': 'joint_state_broadcaster', 'shoulder_pan_joint': 0.0, 'wrist_3_joint': 0.0}})]])
        self.assertEqual(result['ending'], 'final_answer')
        self.assertEqual(result['requests'], 3)
        self.assertEqual([n for n, _ in result['tool_calls']], TASKS['D1']['expected_path'][:-1])
        self.assertEqual(result['answer_raw']['publisher'], 'joint_state_broadcaster')            # raw answer kept
        self.assertEqual(result['answer_accepted']['publisher'], '/joint_state_broadcaster')       # rewritten answer
        self.assertEqual(arm.writes, 0)
        self.assertEqual(log.of('internal_read', 'internal_write'), [])

    def test_D2_inspect_then_move_with_one_terminal(self):
        result, log, arm = go('D2', [[('run_skill', {'skill_id': 'ur5e.inspect_readiness'})],
                                     [('run_skill', {'skill_id': 'ur5e.park_right'})],
                                     [('final_answer', {'answer': {'ready': True, 'shoulder_pan_joint': 0.16}})]])
        self.assertEqual(result['ending'], 'final_answer')
        self.assertEqual(result['requests'], 3)
        self.assertEqual(arm.writes, 1)
        kinds = [e['kind'] for e in log.events if e['kind'] in ('skill_call_start', 'internal_read', 'internal_write', 'skill_call_end', 'final_answer_accepted')]
        self.assertEqual(kinds, ['skill_call_start', 'internal_read', 'internal_read', 'skill_call_end',
                                 'skill_call_start', 'internal_read', 'internal_write', 'internal_read', 'skill_call_end', 'final_answer_accepted'])
        seqs = [e['seq'] for e in log.events]
        self.assertEqual(seqs, sorted(seqs))                                                          # one global sequence
        self.assertEqual(len(log.of('final_answer_accepted')), 1)

    def test_D3_move_then_menu_read_then_finish(self):
        result, log, arm = go('D3', [[('run_skill', {'skill_id': 'ur5e.stage_left'})],
                                     [('ros2_topic_echo', {'topic': '/joint_states', 'count': 1, 'return_echoes': True})],
                                     [('final_answer', {'answer': {'wrist_3_joint': 0.2}})]])
        self.assertEqual(result['ending'], 'final_answer')
        self.assertEqual([n for n, _ in result['tool_calls']], ['run_skill', 'ros2_topic_echo'])
        self.assertEqual(arm.writes, 1)

    def test_tool_set_has_one_terminal_and_no_report_tool(self):
        log, registry, runner, tools, system, model, arm = build([[('final_answer', {'answer': {'a': 1}})]])
        names = [t.name for t in tools]
        self.assertEqual(names, list(menu.MENU_NAMES) + ['run_skill'])        # final_answer is added by the loop as the one terminal
        for forbidden in ('submit_report', 'select_skill', 'read_state', 'write_state', 'verify_outcome', 'ros2_param_set', 'ros2_service_call'):
            self.assertNotIn(forbidden, names)

    def test_submit_report_is_an_unknown_tool_and_the_episode_goes_on(self):
        result, log, _ = go('D3', [[('submit_report', {'status': 'SUCCESS', 'observation_id': 'x'})], [('final_answer', {'answer': {'wrist_3_joint': 0.2}})]])
        self.assertEqual(result['ending'], 'final_answer')
        self.assertIn('unknown tool "submit_report"', log.of('tool_call')[0]['result'])

    def test_bad_arguments_come_back_as_text(self):
        result, log, _ = go('D1', [[('ros2_topic_info', {'topics': '/joint_states'})], [('final_answer', {'answer': {}})], [('final_answer', {'answer': {'ok': 1}})]])
        calls = log.of('tool_call')
        self.assertIn('field "topics": expected array', calls[0]['result'])
        self.assertIn('non-empty JSON object', calls[1]['result'])
        self.assertEqual(result['ending'], 'final_answer')

    def test_text_without_final_answer_is_its_own_ending(self):
        result, _, _ = go('D1', ['I think it is the broadcaster.'])
        self.assertEqual(result['ending'], 'text_without_final_answer')

    def test_request_cap(self):
        result, _, _ = go('D1', [[('nope', {})]] * 8)
        self.assertEqual(result['ending'], 'request_cap')
        self.assertEqual(result['requests'], 8)

    def test_third_skill_call_and_double_call_in_one_response_are_refused(self):
        result, log, arm = go('D2', [[('run_skill', {'skill_id': 'ur5e.inspect_readiness'}), ('run_skill', {'skill_id': 'ur5e.park_right'})],
                                     [('run_skill', {'skill_id': 'ur5e.park_right'})],
                                     [('run_skill', {'skill_id': 'ur5e.inspect_readiness'})],
                                     [('final_answer', {'answer': {'done': True}})]])
        results = [e['result'] for e in log.of('tool_call')]
        self.assertIn('one run_skill per response', results[1])
        self.assertIn('run_skill limit reached', results[3])
        self.assertEqual(arm.writes, 1)

    def test_logs_are_json_serialisable_and_carry_the_l4_fields(self):
        import json
        result, log, _ = go('D2', [[('run_skill', {'skill_id': 'ur5e.park_right'})], [('final_answer', {'answer': {'a': 1}})]])
        json.dumps(log.events, default=str)
        for e in log.of('internal_read', 'internal_write'):
            for key in ('source', 'actor', 'seq', 'parent_call_seq', 't_monotonic', 't_start_monotonic', 't_wall', 'operation_id', 'skill_id', 'status'):
                self.assertIn(key, e)


if __name__ == '__main__':
    unittest.main()
