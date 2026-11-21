"""Errors as text with a strict argument pre-check.
LABEL: REIMPLEMENTATION from Levinson's public description (METHOD_SUMMARY.md row 3: "a failed call is returned to the model as a tool message, with field, expected type
and received value"; one-page summary: the arguments are checked before the original parser). Not his code; his exact wording and strictness details are (H)."""
import json


def _expected(spec):
    if 'type' in spec:
        return spec['type']
    alternatives = [a.get('type') for a in spec.get('anyOf', []) if a.get('type') and a.get('type') != 'null']
    return ' or '.join(alternatives) if alternatives else 'any'


def _matches(value, spec):
    if 'anyOf' in spec:
        if value is None and any(a.get('type') == 'null' for a in spec['anyOf']):
            return True
        return any(_matches(value, a) for a in spec['anyOf'] if a.get('type') != 'null')
    kind = spec.get('type')
    if kind is None:
        return True
    if kind == 'string':
        return isinstance(value, str)
    if kind == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == 'number':
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == 'boolean':
        return isinstance(value, bool)
    if kind == 'object':
        return isinstance(value, dict)
    if kind == 'array':
        if not isinstance(value, list):
            return False
        item = spec.get('items') or {}
        return all(_matches(v, item) for v in value)
    return True


def precheck(tool, arguments):
    """List of problems (field, expected type, received value). Empty list = the call may go on. No coercion: a string for an integer is a problem."""
    schema = tool.args_schema.model_json_schema() if hasattr(tool.args_schema, 'model_json_schema') else tool.args_schema
    properties, required = schema.get('properties', {}), set(schema.get('required', []))
    if not isinstance(arguments, dict):
        return ['arguments must be a JSON object, received %r' % (arguments,)]
    problems = []
    for name in sorted(required - set(arguments)):
        problems.append('field "%s": required (expected %s), nothing received' % (name, _expected(properties.get(name, {}))))
    for name, value in arguments.items():
        if name not in properties:
            problems.append('field "%s": not a parameter of this tool (parameters: %s)' % (name, ', '.join(sorted(properties)) or 'none'))
        elif not _matches(value, properties[name]):
            problems.append('field "%s": expected %s, received %s (%s)' % (name, _expected(properties[name]), json.dumps(value, default=str), type(value).__name__))
    return problems


def render(output):
    return output if isinstance(output, str) else json.dumps(output, sort_keys=True, default=str)


def execute_tool(tool, arguments):
    """Returns (ok, text for the model, raw output or None). Never raises: every failure becomes a tool message."""
    problems = precheck(tool, arguments)
    if problems:
        return False, 'Error calling %s: %s. Fix the arguments and call again.' % (tool.name, '; '.join(problems)), None
    try:
        output = tool.invoke(arguments)
    except Exception as error:   # includes ToolException and ControlledStop: all returned as text, none ends the episode here
        return False, 'Error: %s raised %s: %s' % (tool.name, type(error).__name__, error), None
    return True, render(output), output
