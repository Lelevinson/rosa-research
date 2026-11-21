"""Steps 2 and 3a: the 12-tool menu and errors-as-text. No ROS execution, no model."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from langchain_core.tools import StructuredTool  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from merged_demo import menu, soft_errors  # noqa: E402

EXPECTED = ['ros2_node_list', 'ros2_topic_list', 'ros2_topic_echo', 'ros2_service_list', 'ros2_node_info', 'ros2_topic_info',
            'ros2_param_list', 'ros2_param_get', 'ros2_service_info', 'ros2_doctor', 'roslog_list', 'read_log']


class Args(BaseModel):
    node_name: str
    count: int = 1
    names: list[str] | None = None


def make_tool(func=None):
    return StructuredTool(name='probe', description='probe', args_schema=Args, func=func or (lambda **kw: {'ok': kw}))


class MenuTests(unittest.TestCase):
    def test_menu_names_and_no_write_tools(self):
        tools = menu.stock_menu()
        self.assertEqual([t.name for t in tools], EXPECTED)   # his 12 names (menu-coverage-and-rule.md:24)
        menu.assert_menu(tools)
        names = {t.name for t in tools}
        self.assertFalse(names & {'ros2_param_set', 'ros2_service_call'})

    def test_menu_digest_is_stable_and_has_schemas(self):
        a, b = menu.digest(menu.stock_menu()), menu.digest(menu.stock_menu())
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)
        for t in menu.stock_menu():
            self.assertIn('properties', menu.tool_json(t)['schema'])


class ErrorTextTests(unittest.TestCase):
    def test_valid_call_passes(self):
        ok, text, raw = soft_errors.execute_tool(make_tool(), {'node_name': '/a', 'count': 2})
        self.assertTrue(ok)
        self.assertEqual(raw, {'ok': {'node_name': '/a', 'count': 2}})

    def test_missing_field_names_field_and_type(self):
        ok, text, _ = soft_errors.execute_tool(make_tool(), {})
        self.assertFalse(ok)
        self.assertIn('field "node_name": required (expected string)', text)

    def test_wrong_type_is_not_coerced_and_shows_received_value(self):
        ok, text, _ = soft_errors.execute_tool(make_tool(), {'node_name': '/a', 'count': '2'})
        self.assertFalse(ok)
        self.assertIn('field "count": expected integer, received "2" (str)', text)

    def test_bool_is_not_an_integer_and_extra_field_is_rejected(self):
        ok, text, _ = soft_errors.execute_tool(make_tool(), {'node_name': '/a', 'count': True, 'bogus': 1})
        self.assertFalse(ok)
        self.assertIn('received true (bool)', text)
        self.assertIn('field "bogus": not a parameter', text)

    def test_array_item_type_and_nullable(self):
        ok, text, _ = soft_errors.execute_tool(make_tool(), {'node_name': '/a', 'names': ['x', 3]})
        self.assertFalse(ok)
        self.assertTrue(soft_errors.execute_tool(make_tool(), {'node_name': '/a', 'names': None})[0])
        self.assertTrue(soft_errors.execute_tool(make_tool(), {'node_name': '/a', 'names': ['x']})[0])

    def test_tool_exception_becomes_text_and_does_not_raise(self):
        def boom(**kw):
            raise RuntimeError('subprocess failed')
        ok, text, raw = soft_errors.execute_tool(make_tool(boom), {'node_name': '/a'})
        self.assertFalse(ok)
        self.assertIsNone(raw)
        self.assertIn('RuntimeError: subprocess failed', text)


if __name__ == '__main__':
    unittest.main()
