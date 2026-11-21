"""RECONSTRUCTION of the parts of Levinson's `build_round1_20261115/answer_gate.py` that his `namefix_rule.py` uses.
LABEL: reimplemented from his public `LEDGER_DEFINITION.md` (name_fix_applied_20261117), NOT his file. Details his document does not state
(the exact regexes for relative names, how a 'one entry per requested item' result is detected) are my choices, marked (H).
Replace by his file when he sends it (see namefix.py)."""
import json
import re

NAME_IN_TEXT = re.compile(r'(?<![\w/.:-])/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+')            # from LEDGER_DEFINITION.md, item 1
ABSOLUTE_NAME = re.compile(r'/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+')                          # (H) "absolute path of letters, digits, underscores"
RELATIVE_NAME = re.compile(r'[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*')                           # (H)
NODE_BLOCK = re.compile(r'Node name:\s*(\S+)\s*Node namespace:\s*(\S+)')                  # from LEDGER_DEFINITION.md, item 2(b)


def trailing_matches(value, allowed):
    """Ledger names that end with `value` in whole path segments (value itself excluded)."""
    suffix = value if value.startswith('/') else '/' + value
    return sorted(name for name in allowed if name != value and name.endswith(suffix))


def names_in_text(text):
    text = text.replace('\\n', '\n')
    names = set(NAME_IN_TEXT.findall(text))
    for node, namespace in NODE_BLOCK.findall(text):                                      # joined names, built by the ledger
        names.add(namespace.rstrip('/') + '/' + node)
    return names


def successful_text_parts(output):
    """Failed results contribute nothing; failed items inside a per-item result are skipped one by one."""
    if isinstance(output, dict):
        if 'error' in output:
            return []
        if output and all(isinstance(v, dict) for v in output.values()) and any('error' in v for v in output.values()):   # (H) per-item shape
            return [json.dumps(v, sort_keys=True) for v in output.values() if 'error' not in v]
        return [json.dumps(output, sort_keys=True, default=str)]
    return [output if isinstance(output, str) else json.dumps(output, default=str)]


def allowed_names(task_text, outputs):
    allowed = set(names_in_text(task_text or ''))
    for output in outputs:
        for part in successful_text_parts(output):
            allowed |= names_in_text(part)
        if isinstance(output, dict) and isinstance(output.get('nodes'), list):            # item 2(c): ros2_node_list
            allowed |= {n for n in output['nodes'] if isinstance(n, str) and ABSOLUTE_NAME.fullmatch(n)}
    return allowed
