"""Constructor/dispatch regression: custom-only ROSA must never import ROS tools."""
import builtins
import socket
import subprocess
import unittest
from collections import deque
from unittest.mock import patch

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from pydantic import PrivateAttr

from rosa import ROSA


class ScriptedModel(BaseChatModel):
    _steps: deque = PrivateAttr()

    def __init__(self):
        super().__init__()
        self._steps = deque([
            AIMessage(content='', tool_calls=[{'name': 'read_battery', 'args': {}, 'id': 'mock-1', 'type': 'tool_call'}]),
            AIMessage(content='Battery is 73%.'),
        ])

    @property
    def _llm_type(self):
        return 'offline-scripted'

    def bind_tools(self, tools, **kwargs):
        if {t.name for t in tools} != {'read_battery'}:
            raise AssertionError('Unexpected model-visible tool')
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=self._steps.popleft())])


class MockIsolationTests(unittest.TestCase):
    def test_custom_only_agent_dispatches_without_ros_shell_or_network(self):
        calls = []

        @tool
        def read_battery() -> dict:
            """Read the in-memory mock battery."""
            calls.append('read_battery')
            return {'battery_percent': 73}

        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == 'rclpy' or name.startswith('rclpy.') or name.endswith('.ros2') or name.endswith('.ros1'):
                raise AssertionError(f'Unexpected ROS import: {name}')
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=guarded_import), \
             patch.object(subprocess, 'Popen', side_effect=AssertionError('Subprocess forbidden')), \
             patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')):
            agent = ROSA(2, ScriptedModel(), tools=[read_battery], load_default_tools=False,
                         streaming=False, accumulate_chat_history=False, max_iterations=3)
            self.assertEqual(agent.tool_names, ('read_battery',))
            self.assertEqual(agent.invoke('Read battery.'), 'Battery is 73%.')
            self.assertEqual(calls, ['read_battery'])

    def test_invalid_ros_version_still_rejected(self):
        from rosa.tools import ROSATools
        with self.assertRaises(ValueError):
            ROSATools(99, load_default_tools=False)


if __name__ == '__main__':
    unittest.main()
