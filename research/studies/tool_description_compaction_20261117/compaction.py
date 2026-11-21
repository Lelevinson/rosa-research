"""TOOL-DESCRIPTION COMPACTION RULE (frozen 2026-11-17; generic and automatic: it reads only the text of each tool's description and the argument names of its JSON schema).

Applied to every tool schema offered to the model, in the openai tool format {"type":"function","function":{"name","description","parameters"}}:
  1. `name` and `parameters` (argument names, types, required list, defaults, enums) are copied byte for byte. Only `description` changes.
  2. The description is split into HEAD = the lines before the first line that starts with a reST field marker (`:param`, `:arg`, `:argument`, `:key`, `:keyword`, `:type`, `:return`,
     `:returns`, `:rtype`, `:raises`, `:raise`, `:note`, `:notes`, `:example`, `:examples`) and FIELDS = the marker lines with their continuation lines (every following line up to the next marker line).
  3. TOOL LINE = the first sentence of HEAD (see FIRST SENTENCE), at most 160 characters.
  4. For every argument name in `parameters.properties`, in schema order, that has a `:param <name>:` / `:arg <name>:` / `:argument <name>:` field (a type word between marker and name is allowed):
     ARGUMENT LINE = `<name>: ` + the first sentence of the field text, at most 100 characters. Arguments without such a field get no line (their name and type are still in `parameters`).
  5. New description = TOOL LINE, then one ARGUMENT LINE per line (separated by a newline). Everything else (return documentation, notes, examples, further sentences) is dropped. If HEAD is empty
     the description starts with the argument lines.
FIRST SENTENCE of a text: collapse every run of whitespace to one space; the sentence ends at the first '.', '!' or '?' that is followed by a space or by the end of the text and does not end one of
the abbreviations `e.g.`, `i.e.`, `etc.`, `vs.`, `cf.`; if there is no such end the whole text is the sentence. If the sentence is longer than the cap, it is cut at the last space at or before the cap
(at the cap if there is no space) and nothing is appended.
The rule is deterministic (applied once to the original description; it is not meant to be applied to its own output), has no list of tool names, no per-tool or per-task edit and no knowledge of the task.
"""
import copy
import re

MARKERS = r"(?:param|arg|argument|key|keyword|type|return|returns|rtype|raises|raise|note|notes|example|examples)"
MARKER_LINE = re.compile(r"^\s*:" + MARKERS + r"\b")
PARAM_FIELD = re.compile(r"^\s*:(?:param|arg|argument)\s+(?:[^\s:]+\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "cf.")
TOOL_LINE_CAP, ARGUMENT_LINE_CAP = 160, 100


def first_sentence(text, cap):
    s = " ".join((text or "").split())
    end = None
    for i, ch in enumerate(s):
        if ch in ".!?" and (i + 1 == len(s) or s[i + 1] == " ") and not s[: i + 1].lower().endswith(ABBREVIATIONS):
            end = i + 1
            break
    s = s if end is None else s[:end]
    if len(s) > cap:
        cut = s.rfind(" ", 0, cap + 1)
        s = s[:cut] if cut > 0 else s[:cap]
    return s


def split_description(description):
    head, fields, current = [], [], None
    for line in (description or "").split("\n"):
        if MARKER_LINE.match(line):
            current = [line]
            fields.append(current)
        elif current is not None:
            current.append(line)
        else:
            head.append(line)
    return "\n".join(head), ["\n".join(f) for f in fields]


def compact_description(description, argument_names):
    head, fields = split_description(description)
    documented = {}
    for field in fields:
        m = PARAM_FIELD.match(field.split("\n")[0])
        if m:
            documented.setdefault(m.group(1), " ".join([m.group(2)] + field.split("\n")[1:]))
    lines = []
    tool_line = first_sentence(head, TOOL_LINE_CAP)
    if tool_line:
        lines.append(tool_line)
    for name in argument_names:
        if name in documented:
            lines.append(f"{name}: {first_sentence(documented[name], ARGUMENT_LINE_CAP)}")
    return "\n".join(lines)


def compact_schema(schema):
    """A copy of one tool schema (openai format) with the compacted description; name and parameters untouched."""
    out = copy.deepcopy(schema)
    function = out["function"]
    function["description"] = compact_description(function.get("description", ""), list((function.get("parameters") or {}).get("properties", {})))
    return out
