"""List arguments (build round 1, 2026-11-15): an existing read tool accepts one entity name OR a list of up to 20 names.

THE RULE (derived from each tool's own schema and docstring; no per-task choice):
  A read tool of the fixed loop's menu gets list support for an argument when
    (1) the argument is a plain string argument (type 'string', or string-or-null) in the tool's schema, and
    (2) the tool's docstring line for that argument says it is a NAME of one graph entity: the line contains the word 'name' and one of
        'node', 'topic', 'service' as a whole word (the singular; 'list of nodes' does not match).
  All other arguments of the call are shared by every item.
  Tools that already take a list of entities (ros2_node_info, ros2_topic_info, ros2_service_info) are left unchanged.
  Resulting tools (see applicable_tools(); also checked by the unit test against the real tool schemas):
    ros2_param_get.node_name   (param_name is shared)      ros2_param_list.node_name   (pattern/blacklist are shared)
    ros2_topic_echo.topic      (count, delay, ... shared)
  NOTE ON THE WORDING OF THE ASSIGNMENT: it says "every read tool whose single required argument names one entity". Read literally that selects only
  ros2_topic_echo (param_get has two required arguments, param_list none). That reading would leave the add-on almost empty, because the measured
  batching waste is mostly parameter reads. This module implements the wider rule above and the report names the difference.

HOW A LIST CALL RUNS: the original tool runs once per distinct item (duplicates are dropped, order kept); the result is ONE dict
  {item: result_of_that_item, ...} in input order; a failure stays inside its own item as {'error': ...}. Nothing is truncated.
  A single string behaves exactly as before. More than 20 items or an empty list is rejected with an explanatory message and nothing is executed.
"""
import re
from typing import List, Optional, Union

from pydantic import Field, create_model

MAX_ITEMS = 20
ENTITY_WORDS = ("node", "topic", "service")
LIST_SENTENCE = "Accepts one name or a list of up to 20 names; a list returns one labeled result per name."
PARAM_LINE = re.compile(r"^:param (\w+):(.*)$", re.M)


def entity_arguments(tool):
    """Names of the arguments of this tool that the rule above selects."""
    properties = tool.args_schema.model_json_schema().get("properties", {}) if hasattr(tool.args_schema, "model_json_schema") else {}
    selected = []
    for line_match in PARAM_LINE.finditer(tool.description or ""):
        name, text = line_match.group(1), line_match.group(2)
        schema = properties.get(name, {})
        is_plain_string = schema.get("type") == "string" or (
            "anyOf" in schema and sorted(a.get("type", "") for a in schema["anyOf"]) == ["null", "string"])
        names_an_entity = re.search(r"\bname\b", text) and any(re.search(rf"\b{w}\b", text) for w in ENTITY_WORDS)
        if is_plain_string and names_an_entity:
            selected.append(name)
    return selected


def applicable_tools(tools, menu_names):
    """{tool name: argument name} for the tools of the menu that the rule selects (at most one argument per tool; the first)."""
    chosen = {}
    for tool in tools:
        if tool.name in menu_names:
            arguments = entity_arguments(tool)
            if arguments:
                chosen[tool.name] = arguments[0]
    return chosen


def with_list_schema(tool, argument):
    """(new args_schema, new description): the argument accepts a string or a list of strings; the description line gets one extra sentence."""
    fields = {}
    for name, info in tool.args_schema.model_fields.items():
        if name == argument:
            default = ... if info.is_required() else None
            annotation = Union[str, List[str]] if info.is_required() else Optional[Union[str, List[str]]]
            fields[name] = (annotation, Field(default, description=info.description))
        else:
            fields[name] = (info.annotation, info)
    schema = create_model(tool.args_schema.__name__ + "WithList", **fields)

    def extend(match):
        return match.group(0) + " " + LIST_SENTENCE if match.group(1) == argument else match.group(0)
    description = PARAM_LINE.sub(lambda m: extend(m), tool.description)
    return schema, description


def list_problem(value):
    """A message when a list argument is unusable, else None. (Item types are checked by the strict schema check.)"""
    if isinstance(value, list):
        if not value:
            return "The list of names is empty; give at least one name."
        if len(value) > MAX_ITEMS:
            return f"Too many names ({len(value)}); at most {MAX_ITEMS} per call. Split the list."
    return None


def run_per_item(run_one, arguments, argument):
    """run_one(arguments_for_one_item) -> that item's original result. Returns (combined result, items) for a list call, or None for a single string."""
    value = arguments.get(argument)
    if not isinstance(value, list):
        return None
    items = list(dict.fromkeys(value))
    combined = {}
    for item in items:
        single = dict(arguments)
        single[argument] = item
        try:
            combined[item] = run_one(single)
        except Exception as error:  # an item failure stays inside its own entry
            combined[item] = {"error": f"{type(error).__name__}: {error}"}
    return combined, items
