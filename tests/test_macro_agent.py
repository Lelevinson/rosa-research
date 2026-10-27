"""Actual ROSA and both real adapter classes, with fake transports only."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage
from ollama import ChatResponse

from rosa_backends.chat_ollama import ConfiguredChatOllama
from rosa_backends.chat_siwc import ChatSiwc
from rosa_reliability.execution import ControlledStop
from rosa_reliability.macro_agent import MacroROSA, InferenceBudget, InferenceLimits
from rosa_reliability.macro_demo import MemoryTransport, demo_registry


def message(*, reason='stop', output=5, call=True):
    return AIMessage(content='', tool_calls=[{'name': 'select_skill', 'args': {'skill_id': 'station.right'},
        'id': 'call1', 'type': 'tool_call'}] if call else [],
        usage_metadata={'input_tokens': 10, 'output_tokens': output, 'total_tokens': 10 + output},
        response_metadata={'finish_reason': reason})


class ReturnModel:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.requests = result, error, []

    def invoke(self, prompt, config=None, **kwargs):
        self.requests.append(deepcopy(kwargs))
        if self.error: raise self.error
        return self.result


class AdapterScript:
    """Scripted caller uses current session evidence, not a live LLM."""

    def __init__(self, invocation, *, wrong_report=False):
        self.invocation, self.index = invocation, 0
        self.wrong_report = wrong_report
        self.requests = []

    def next_call(self):
        index = self.index
        self.index += 1
        if index == 0:
            return 'select_skill', {'skill_id': 'station.right'}
        if self.invocation.mode == 'primitives':
            steps = [('read_state', {'nodes': ['/demo_arm']}),
                     ('write_state', {'node_name': '/demo_arm', 'values': {'yaw': 0.2, 'pitch': 0.1}}),
                     ('verify_outcome', {})]
            if index <= len(steps): return steps[index - 1]
        evidence = self.invocation.session.observations[-1]
        status = 'SUCCESS'
        if self.wrong_report and index == 1: status = 'UNKNOWN'
        return 'submit_report', {'status': status, 'observation_id': evidence['observation_id']}

    def respond(self, model, history, tools):
        self.requests.append(deepcopy({'input': history, 'tools': tools}))
        name, args = self.next_call()
        return {'status': 'completed', 'model': model, 'output': [{'type': 'function_call',
            'id': 'fc' + str(self.index), 'call_id': 'call' + str(self.index),
            'namespace': 'rosa_tools', 'name': name, 'arguments': json.dumps(args)}],
            'usage': {'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15}}, 0.001

    def ollama_chat(self, **kwargs):
        self.requests.append(deepcopy(kwargs))
        name, args = self.next_call()
        response = ChatResponse(model='fake-local', done=True, done_reason='stop', prompt_eval_count=10,
            eval_count=5, message={'role': 'assistant', 'content': '',
                'tool_calls': [{'function': {'name': name, 'arguments': args}}]})
        return iter([response]) if kwargs.get('stream') else response

    def close(self): pass


class MacroAgentTests(unittest.TestCase):
    def test_real_adapters_and_executor_share_tools_terminate_and_preserve_options(self):
        for backend in ('ollama', 'siwc'):
            for mode in ('macro', 'primitives'):
                with self.subTest(backend=backend, mode=mode):
                    invocation = demo_registry().open(MemoryTransport(), mode=mode)
                    script = AdapterScript(invocation)
                    if backend == 'siwc':
                        llm = ChatSiwc(model='fake-hosted', backend=script)
                        context = patch('socket.socket.connect', side_effect=AssertionError('No network'))
                    else:
                        llm = ConfiguredChatOllama(model='fake-local', streaming=False, reasoning=False,
                            num_ctx=8192, num_predict=1024, temperature=0, seed=42, use_mmap=True)
                        context = patch.object(llm._client, 'chat', side_effect=script.ollama_chat)
                    reserved = []
                    with context:
                        agent = MacroROSA(llm, invocation, backend=backend,
                            batch_reserve=lambda: reserved.append(1))
                        answer = agent.invoke('Choose station.right.')
                    self.assertTrue(answer.startswith('{'), answer)
                    self.assertTrue(json.loads(answer)['report_accepted'])
                    expected = 2 if mode == 'macro' else 5
                    self.assertEqual(script.index, expected)
                    self.assertEqual(len(reserved), expected)
                    self.assertEqual(agent.inference_budget.calls, expected)
                    self.assertTrue(agent.inference_budget.snapshot()['usage_complete'])
                    self.assertTrue(any(e['type'] == 'terminal' for e in invocation.session.events))
                    with self.assertRaises(ControlledStop): agent.invoke('Again.')
                    if backend == 'ollama':
                        for request in script.requests:
                            self.assertEqual(request['options']['num_ctx'], 8192)
                            self.assertEqual(request['options']['temperature'], 0)
                            self.assertEqual(request['options']['seed'], 42)
                            self.assertEqual(request['options']['num_predict'], 1024)
                            self.assertTrue(request['options']['use_mmap'])
                    else:
                        llm.close()

    def test_rejected_report_is_correctable_without_an_extra_terminal_ack(self):
        invocation = demo_registry().open(MemoryTransport())
        script = AdapterScript(invocation, wrong_report=True)
        llm = ChatSiwc(model='fake-hosted', backend=script)
        agent = MacroROSA(llm, invocation, backend='siwc')
        self.assertTrue(json.loads(agent.invoke('Choose station.right.'))['report_accepted'])
        self.assertEqual(script.index, 3)
        self.assertEqual(invocation.session.validation_errors, 1)
        self.assertEqual(invocation.session.write_count, 1)
        llm.close()

    def test_truncation_withholds_parseable_tool_calls_before_dispatch(self):
        invocation = demo_registry().open(MemoryTransport())
        gate = InferenceBudget(invocation, backend='ollama')
        model = ReturnModel(message(reason='length'))
        with self.assertRaisesRegex(ControlledStop, 'truncated_response'):
            gate.invoke(model, [])
        self.assertFalse(invocation.session.budget.events)
        self.assertEqual(gate.calls, 1)
        self.assertEqual(gate.events[0]['tool_calls_withheld'], 1)

    def test_unreturned_calls_remain_reserved_and_usage_is_unknown(self):
        for backend, upper in (('siwc', None), ('ollama', 1024)):
            gate = InferenceBudget(demo_registry().open(MemoryTransport()), backend=backend)
            with self.assertRaises(TimeoutError): gate.invoke(ReturnModel(error=TimeoutError()), [])
            result = gate.snapshot()
            self.assertEqual(result['calls'], 1)
            self.assertFalse(result['usage_complete'])
            self.assertEqual(result['output_upper_bound'], upper)

    def test_invalid_usage_has_no_finite_output_bound(self):
        gate = InferenceBudget(demo_registry().open(MemoryTransport()), backend='ollama')
        invalid = AIMessage(content='unmetered')
        with self.assertRaises(ControlledStop): gate.invoke(ReturnModel(invalid), [])
        self.assertFalse(gate.snapshot()['usage_complete'])
        self.assertIsNone(gate.snapshot()['output_upper_bound'])

    def test_late_return_is_metered_but_withheld_before_tool_dispatch(self):
        invocation = demo_registry().open(MemoryTransport())
        gate = InferenceBudget(invocation, backend='scripted')
        started = invocation.session.budget.started
        with patch('rosa_reliability.macro_agent.time.monotonic', side_effect=[started, started + 181]):
            with self.assertRaisesRegex(ControlledStop, 'returned_after_deadline'):
                gate.invoke(ReturnModel(message()), [])
        self.assertEqual(gate.snapshot()['known_output_tokens'], 5)
        self.assertFalse(invocation.session.budget.events)

    def test_request_output_and_batch_caps_do_not_reset(self):
        invocation = demo_registry().open(MemoryTransport())
        for limits in (0, False, {}):
            with self.assertRaises(TypeError): InferenceBudget(invocation, backend='siwc', limits=limits)
        gate = InferenceBudget(invocation, backend='siwc', limits=InferenceLimits(calls=1))
        model = ReturnModel(message(call=False))
        gate.invoke(model, [])
        with self.assertRaises(ControlledStop): gate.invoke(model, [])
        self.assertEqual(len(model.requests), 1)
        gate = InferenceBudget(invocation, backend='siwc', limits=InferenceLimits(output_tokens=4))
        with self.assertRaisesRegex(ControlledStop, 'threshold_exceeded'): gate.invoke(model, [])
        self.assertEqual(gate.output_tokens, 5)
        def reject(): raise ControlledStop('batch_exhausted')
        gate = InferenceBudget(invocation, backend='siwc', batch_reserve=reject)
        with self.assertRaisesRegex(ControlledStop, 'batch_exhausted'): gate.invoke(model, [])
        self.assertEqual(gate.calls, 0)


if __name__ == '__main__': unittest.main()
