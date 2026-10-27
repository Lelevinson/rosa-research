"""Exercise the actual ROSA executor through the native OAuth model adapter."""
from copy import deepcopy
import json
import socket
import subprocess
import unittest
from unittest.mock import patch

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from rosa.prompts import RobotSystemPrompts, system_prompts
from rosa_auth.oauth import SafeError
from rosa_backends import create_mock_agent, create_model
from rosa_backends.chat_siwc import ChatSiwc


@tool
def read_battery(robot_id: str) -> dict:
    """Read the fixed in-memory mock battery."""
    return {'robot_id': robot_id, 'battery_percent': 73}


def function(name='read_battery', **changes):
    return {'type': 'function_call', 'id': 'fc1', 'call_id': 'call1',
            'namespace': 'rosa_tools', 'name': name,
            'arguments': '{"robot_id":"mock-robot"}', **changes}


class FakeBackend:
    def __init__(self, outputs=None):
        self.secret = 'PRIVATE_ACCESS_TOKEN'
        self.outputs = outputs if outputs is not None else [
            [{'type': 'reasoning', 'id': 'r1', 'encrypted_content': 'PRIVATE_REASONING'}, function()],
            [{'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': 'Battery is 73%.'}]}],
        ]
        self.requests = []

    def respond(self, model, history, tools):
        self.requests.append(deepcopy({'model': model, 'input': history, 'tools': tools}))
        return {'status': 'completed', 'model': model, 'output': self.outputs.pop(0),
                'usage': {'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15}}, 0.01

    def close(self):
        self.secret = None


class Capture(BaseCallbackHandler):
    def __init__(self):
        self.public = []

    def on_chat_model_start(self, serialized, messages, **kwargs):
        self.public.append(str((serialized, messages, kwargs)))

    def on_llm_end(self, response, **kwargs):
        self.public.append(str((response, kwargs)))


class SharedBackendTests(unittest.TestCase):
    def test_actual_rosa_roundtrip_preserves_private_continuation_without_logging_it(self):
        backend = FakeBackend()
        llm = create_model('siwc', model='account-model', siwc_transport=backend)
        capture = Capture()
        # Attach callbacks to the underlying model, as the ROSA constructor binds it.
        llm.callbacks = [capture]
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('No subprocess')), \
             patch.object(socket.socket, 'connect', side_effect=AssertionError('No network')):
            agent = create_mock_agent(llm, [read_battery])
            self.assertEqual(agent.tool_names, ('read_battery',))
            self.assertEqual(agent.invoke('Read the battery for mock-robot.'), 'Battery is 73%.')
        self.assertEqual(len(backend.requests), 2)
        first, second = backend.requests
        self.assertTrue(any(item.get('role') == 'developer' for item in first['input']))
        self.assertFalse(any(item.get('role') == 'system' for item in first['input']))
        self.assertEqual(first['tools'][0]['name'], 'rosa_tools')
        self.assertEqual(first['tools'][0]['tools'][0]['name'], 'read_battery')
        self.assertTrue(any(item.get('encrypted_content') == 'PRIVATE_REASONING' for item in second['input']))
        result = next(item for item in second['input'] if item.get('type') == 'function_call_output')
        self.assertEqual(result['call_id'], 'call1')
        self.assertEqual(json.loads(result['output'])['battery_percent'], 73)
        public = str(capture.public) + str(llm) + repr(llm) + json.dumps(llm.model_dump()) + json.dumps(llm.request_records)
        self.assertNotIn('PRIVATE_ACCESS_TOKEN', public)
        self.assertNotIn('PRIVATE_REASONING', public)
        llm.close()
        self.assertFalse(llm._native_outputs)
        self.assertIsNone(backend.secret)

    def test_rejects_unregistered_names_namespaces_and_malformed_calls(self):
        invalid = [function(name='execute_motion'), function(namespace='other'),
                   function(call_id=''), function(arguments='[]'), function(arguments='bad'),
                   function(arguments='{"robot_id":"a","robot_id":"b"}')]
        for call in invalid:
            with self.subTest(call=call):
                backend = FakeBackend([[call]])
                llm = ChatSiwc(model='model', backend=backend)
                with self.assertRaises(SafeError):
                    llm.bind_tools([read_battery]).invoke('Read battery')

    def test_rejects_orphan_missing_and_unrecoverable_tool_history_before_request(self):
        backend = FakeBackend()
        llm = ChatSiwc(model='model', backend=backend)
        call = {'name': 'read_battery', 'args': {}, 'id': 'lost', 'type': 'tool_call'}
        for messages in ([ToolMessage(content='73', tool_call_id='lost')],
                         [AIMessage(content='', tool_calls=[call])]):
            with self.assertRaises(SafeError):
                llm.invoke(messages)
        self.assertFalse(backend.requests)
        result = llm.bind_tools([read_battery]).invoke([HumanMessage(content='Read battery')])
        with self.assertRaises(SafeError):
            llm.invoke([result, HumanMessage(content='Continue without the tool result')])
        self.assertEqual(len(backend.requests), 1)

    def test_selection_and_allowlist_fail_closed(self):
        for backend, options in [('unknown', {}), ('siwc', {}),
                                 ('siwc', {'model': 'm', 'siwc_transport': FakeBackend(), 'base_url': 'http://elsewhere'}),
                                 ('ollama', {'siwc_transport': FakeBackend()})]:
            with self.assertRaises(ValueError):
                create_model(backend, **options)
        llm = ChatSiwc(model='model', backend=FakeBackend())
        for tools in ([], [read_battery, read_battery]):
            with self.assertRaises(ValueError):
                create_mock_agent(llm, tools)
        with self.assertRaises(SafeError):
            llm.bind_tools([read_battery], tool_choice='required')
        with self.assertRaises(SafeError):
            llm.invoke('test', temperature=0)

    def test_multiple_agent_prompts_do_not_modify_global_roots(self):
        from rosa import ROSA
        before = list(system_prompts)
        for marker in ('first', 'second'):
            ROSA(2, ChatSiwc(model='m', backend=FakeBackend()), tools=[read_battery],
                 load_default_tools=False, streaming=False,
                 prompts=RobotSystemPrompts(mission_and_objectives=marker))
        self.assertEqual(system_prompts, before)

    def test_async_langchain_invocation_uses_the_same_adapter(self):
        import asyncio
        llm = ChatSiwc(model='model', backend=FakeBackend())
        result = asyncio.run(llm.bind_tools([read_battery]).ainvoke('Read battery'))
        self.assertEqual(result.tool_calls[0]['name'], 'read_battery')
        self.assertEqual(result.usage_metadata['total_tokens'], 15)

    def test_separate_tasks_share_model_but_do_not_inherit_tool_history(self):
        template = FakeBackend().outputs
        backend = FakeBackend(deepcopy(template) + deepcopy(template))
        llm = ChatSiwc(model='model', backend=backend)
        for query in ('first task', 'second task'):
            self.assertIn('73', create_mock_agent(llm, [read_battery]).invoke(query))
        second_task_input = backend.requests[2]['input']
        self.assertFalse(any(item.get('type') in ('function_call', 'function_call_output', 'reasoning')
                             for item in second_task_input))
        self.assertFalse(any(item.get('content') == 'first task' for item in second_task_input))

    def test_duplicate_call_ids_are_rejected_and_tool_schemas_can_be_rebound(self):
        backend = FakeBackend([[function(), function()]])
        llm = ChatSiwc(model='model', backend=backend)
        with self.assertRaisesRegex(SafeError, 'invalid_tool_call_id'):
            llm.bind_tools([read_battery]).invoke('Read')

        @tool
        def other_read() -> int:
            """Read a different fixed fixture."""
            return 1

        backend.outputs = [[function(name='read_battery')]]
        with self.assertRaisesRegex(SafeError, 'model_requested_unregistered_tool'):
            llm.bind_tools([other_read]).invoke('Read')

    def test_explicit_ollama_loading_option_preserves_other_generation_options(self):
        llm = create_model('ollama', use_mmap=True)
        params = llm._chat_params([HumanMessage(content='Read')])
        self.assertEqual(params['options']['use_mmap'], True)
        self.assertEqual(params['options']['num_ctx'], 4096)
        self.assertEqual(params['options']['num_predict'], 256)
        self.assertEqual(params['options']['temperature'], 0)
        self.assertEqual(params['options']['seed'], 42)
        self.assertFalse(llm.cache)


if __name__ == '__main__':
    unittest.main()
