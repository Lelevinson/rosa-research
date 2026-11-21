"""Canonical result rendering (protocol: PROTOCOL_OFFLINE.md, hash in PROTOCOL_OFFLINE.sha256). Rules R1-R8 are numbered in the protocol and in the comments below.

What it does, in one paragraph: a tool result is a dict/list/string. Every string leaf that contains `Key: value` or `Header:` lines is re-written with consistent
indentation, without blank lines, and with one added `... full name: /ns/name` line wherever a `... namespace` field and a `... name` field sit in the same block.
Nothing is removed. Everything the parser cannot read is returned unchanged. There is NO rule about any tool, field name (other than the words name / namespace),
fixture or task: if you want to add one, write it in TEMPTATIONS.md instead.

Pure Python, no ROS, no model, no I/O.
"""
from collections import Counter
from typing import Any, List, Tuple

KEY_VALUE, HEADER, BARE = "key_value", "header", "bare"


# ---------------------------------------------------------------- R2: line classes (the generic parser)
def classify(line: str) -> Tuple[str, str, str]:
    """Returns (class, key, value) for one non-blank line. The class never depends on the text of the key."""
    stripped = line.strip()
    leading = line[: len(line) - len(line.lstrip())]
    if "\t" in leading:
        return BARE, "", stripped
    if ": " in stripped:
        key, value = stripped.split(": ", 1)
        if key.strip():
            return KEY_VALUE, key.strip(), value.strip()
    if stripped.endswith(":") and len(stripped) > 1:
        return HEADER, stripped[:-1].strip(), ""
    return BARE, "", stripped


def indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


# ---------------------------------------------------------------- R3: depth from an indentation stack; blocks
def depths(indents: List[int]) -> List[int]:
    stack, result = [], []
    for indent in indents:
        while stack and stack[-1] > indent:
            stack.pop()
        if not stack or stack[-1] < indent:
            stack.append(indent)
        result.append(len(stack) - 1)
    return result


# ---------------------------------------------------------------- R6: ROS 2 name resolution inside one block
def full_name(namespace: str, name: str) -> str:
    return namespace.rstrip("/") + "/" + name  # namespace "/" gives "/name"


def derived_lines(block: List[dict], stats: Counter) -> List[Tuple[int, str]]:
    """For one block (list of dicts with index, key, value) return [(position after which to insert, key, full name)] for the one allowed namespace+name pair per prefix."""
    found = []
    for namespace_word, name_word in (("namespace", "name"), ("Namespace", "Name")):
        prefixes = {item["key"][: -len(namespace_word)] for item in block if item["key"].endswith(namespace_word)}
        for prefix in sorted(prefixes):
            namespaces = [item for item in block if item["key"] == prefix + namespace_word]
            names = [item for item in block if item["key"] == prefix + name_word]
            derived_key = prefix + "full name" if prefix else "Full name"
            if len(namespaces) != 1 or len(names) != 1:
                stats["skip_ambiguous_block"] += 1
                continue
            namespace, name = namespaces[0], names[0]
            if not namespace["value"].startswith("/"):
                stats["skip_namespace_not_absolute"] += 1
                continue
            if not name["value"] or name["value"].startswith("/"):
                stats["skip_name_empty_or_absolute"] += 1
                continue
            if any(item["key"] == derived_key for item in block):
                stats["skip_already_present"] += 1
                continue
            later = max(namespace["index"], name["index"])
            found.append((later, f"{derived_key}: {full_name(namespace['value'], name['value'])}"))
    return found


# ---------------------------------------------------------------- R4, R5: render one string leaf
def render_text(text: str, stats: Counter) -> str:
    raw_lines = text.replace("\r\n", "\n").split("\n")
    lines, after_blank = [], []  # non-blank lines, and whether a blank line came right before each (a blank line ends a block, R3)
    blank_seen = False
    for line in raw_lines:
        if not line.strip():
            blank_seen = True
            continue
        lines.append(line)
        after_blank.append(blank_seen)
        blank_seen = False
    classes = [classify(line) for line in lines]
    for kind, _key, _value in classes:
        stats["lines_" + kind] += 1
    if not any(kind in (KEY_VALUE, HEADER) for kind, _k, _v in classes):
        stats["leaves_passed_through"] += 1
        return text  # R4: nothing readable, byte-identical
    stats["leaves_rendered"] += 1
    stats["chars_in_rendered_leaves"] += len(text)
    level = depths([indentation(line) for line in lines])
    # blocks: maximal runs of key-value lines with the same indentation, no other line between (R3)
    inserts = {}
    block: List[dict] = []
    for position, ((kind, key, value), line) in enumerate(zip(classes, lines)):
        same_run = block and kind == KEY_VALUE and not after_blank[position] and indentation(lines[block[-1]["index"]]) == indentation(line)
        if kind == KEY_VALUE and (same_run or not block):
            block.append(dict(index=position, key=key, value=value))
            continue
        for later, text_line in derived_lines(block, stats) if block else []:
            inserts.setdefault(later, []).append(text_line)
        block = [dict(index=position, key=key, value=value)] if kind == KEY_VALUE else []
    for later, text_line in derived_lines(block, stats) if block else []:
        inserts.setdefault(later, []).append(text_line)
    out = []
    for position, line in enumerate(lines):
        out.append("  " * level[position] + line.strip())
        for derived in inserts.get(position, []):
            out.append("  " * level[position] + derived)
            stats["derived_lines"] += 1
    rendered = "\n".join(out)
    return rendered + "\n" if text.endswith("\n") else rendered


# ---------------------------------------------------------------- R1: containers
def render_result(value: Any, stats: Counter = None) -> Any:
    """Render one tool result. `stats` (a Counter) collects counts for the offline report; pass nothing in production."""
    stats = Counter() if stats is None else stats
    if isinstance(value, str):
        return render_text(value, stats)
    if isinstance(value, dict):
        return {key: render_result(item, stats) for key, item in value.items()}
    if isinstance(value, list):
        return [render_result(item, stats) for item in value]
    return value
