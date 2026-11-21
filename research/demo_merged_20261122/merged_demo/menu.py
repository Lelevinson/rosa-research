"""The 12-tool read menu. LABEL: the SAME 12 names as Levinson's short menu (menu-coverage-and-rule.md:24), taken from the STOCK ROSA tool objects.
His bounded wrapper (`harness.DOMAIN_TOOLS`) is not public, so the demo menu is "same names, stock implementations", NOT his wrapper."""
import hashlib
import json

MENU_NAMES = ('ros2_node_list', 'ros2_topic_list', 'ros2_topic_echo', 'ros2_service_list', 'ros2_node_info', 'ros2_topic_info',
              'ros2_param_list', 'ros2_param_get', 'ros2_service_info', 'ros2_doctor', 'roslog_list', 'read_log')
FORBIDDEN = ('ros2_param_set', 'ros2_service_call')


def stock_menu():
    """The stock ROSA tool objects, in his order. Needs the rosa package (and ROS for execution, not for import)."""
    from rosa.tools import ros2, log
    objects = {**{n: getattr(ros2, n) for n in MENU_NAMES if hasattr(ros2, n)}, 'read_log': log.read_log}
    missing = [n for n in MENU_NAMES if n not in objects]
    if missing:
        raise RuntimeError('menu tools missing from stock ROSA: %s' % missing)
    return [objects[n] for n in MENU_NAMES]


def tool_json(tool):
    schema = tool.args_schema.model_json_schema() if hasattr(tool.args_schema, 'model_json_schema') else tool.args_schema
    return {'name': tool.name, 'description': tool.description, 'schema': schema}


def digest(tools):
    payload = json.dumps([tool_json(t) for t in tools], sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def assert_menu(tools):
    names = tuple(t.name for t in tools)
    if names != MENU_NAMES:
        raise AssertionError('menu names differ: %s' % (names,))
    if any(n in names for n in FORBIDDEN):
        raise AssertionError('write tool in menu')
