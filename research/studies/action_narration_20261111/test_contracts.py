"""Focused checks for experiment safety and scoring boundaries; no inference."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json
import threading
from types import SimpleNamespace
from langchain_core.messages import AIMessage, HumanMessage

import run_study as study
import score


class Contracts(unittest.TestCase):
    def test_prompts_do_not_mutate_baseline_and_keep_final_answers(self):
        original = list(study.system_prompts)
        protocol = json.loads((study.HERE/'cases.json').read_text())
        for arm in 'ABC':
            messages = study.prompts(arm,protocol)
            self.assertFalse(any('SEQUENTIAL TOOL EXECUTION' in s for _,s in messages))
            self.assertIn('complete supported final answer', str(messages))
        self.assertEqual(original,study.system_prompts)

    def test_guard_cannot_dispatch_mutators_or_shell_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            guard = study.native_guard(study.Journal(Path(directory)/'trace.jsonl'))
            with patch.object(study.subprocess,'run') as execute:
                for command in ['ros2 param set /n foo 1', 'ros2 service call /s X {}',
                                'ros2 node info /n;id','ros2 node info /n --help']:
                    self.assertFalse(guard(command)[0])
                execute.assert_not_called()

    def test_scorer_keeps_sources_and_roles_distinct(self):
        text = '  Publishers:\n    /pose: turtlesim/msg/Pose\n  Subscribers:\n    /cmd_vel: geometry_msgs/msg/Twist\n'
        self.assertEqual(score.node_section(text,'Publishers'),{'/pose':'turtlesim/msg/Pose'})
        self.assertEqual(score.node_section(text,'Subscribers'),{'/cmd_vel':'geometry_msgs/msg/Twist'})
        actual,remainder = score.first_object('Unverified claim. {"use_sim_time":false}')
        self.assertFalse(actual['use_sim_time'])
        self.assertIn('Unverified claim',remainder)

    def test_concurrent_failed_attempts_cannot_bypass_retry_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = study.Journal(Path(directory)/'trace.jsonl')
            guard = study.native_guard(journal)
            entered = threading.Barrier(3)
            release = threading.Event()
            def native(*args,**kwargs):
                entered.wait(timeout=3)
                release.wait(timeout=3)
                return SimpleNamespace(returncode=1,stdout='',stderr='missing')
            with patch.object(study.subprocess,'run',side_effect=native) as execute:
                threads = [threading.Thread(target=guard,args=('ros2 node info /missing',)) for _ in range(2)]
                for thread in threads: thread.start()
                entered.wait(timeout=3)
                self.assertFalse(guard('ros2 node info /missing')[0])
                release.set()
                for thread in threads: thread.join(timeout=3)
                self.assertFalse(guard('ros2 node info /missing')[0])
                self.assertEqual(execute.call_count,2)

    def test_measurement_preserves_action_ids_and_complete_final(self):
        with tempfile.TemporaryDirectory() as directory:
            for answer in [AIMessage(content='Optional prose',tool_calls=[dict(name='ros2_node_list',args={},id='native-call-7')]),
                           AIMessage(content='Complete final answer including unavailable fields.')]:
                class Model:
                    def _chat_params(self,*args,**kwargs): return {'think':False,'tools':kwargs['tools']}
                    def bind_tools(self,schemas): return self
                    def invoke(self,*args,**kwargs): return answer
                model = study.MeasuredModel(underlying=Model(),journal=study.Journal(Path(directory)/'trace.jsonl'))
                observed = model._generate([HumanMessage(content='request')],tools=[]).generations[0].message
                self.assertEqual(observed.model_dump(),answer.model_dump())

    def test_diagnostic_scoring_does_not_repair_missing_enumeration(self):
        path=study.ROOT/'research/_artifacts/action_narration_20261111/primary-v1/oracle-after.json'
        if not path.exists(): self.skipTest('Postexecution raw counterexample not available')
        raw=path.read_bytes()
        snapshot=json.loads(raw)
        self.assertEqual(snapshot['nodes']['stdout'],'')
        with self.assertRaises(AssertionError): score.expected(snapshot)
        values=score.expected(snapshot,require_enumeration=False)
        self.assertEqual(values['t1']['node'],'/diag_turtle/palette')
        self.assertEqual(snapshot['nodes']['stdout'],'')
        self.assertEqual(path.read_bytes(),raw)


if __name__ == '__main__': unittest.main()
