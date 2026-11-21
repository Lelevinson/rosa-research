"""Answer gate (build round 1, 2026-11-15): deterministic checks when the model tries to finish. No LLM call of its own.

Pure functions only, so the same code is used live (round1_harness.py) and in the offline replay (precheck_gate.py).

Checks (all inputs are things the model itself can see: the task text, tool results of this episode, the submitted answer):
  1. Bare-text finish nudge (adopted from Forge's bare-text nudge; see round1_harness.Round1Model): handled in the harness.
  2. Name check on final_answer. A string value, or a key of a nested object, "looks like a ROS graph name" when it is a valid
     absolute ROS name: '/' followed by one or more [A-Za-z0-9_]+ tokens separated by '/'. (ROS name syntax only; nothing task specific.)
       allowed set = names found in SUCCESSFUL tool results of this episode  U  names written in the task text
       exact member            -> pass
       trailing part of exactly one allowed full name -> reject, "did you mean <full name>?"
       otherwise               -> reject, "never appeared in a tool result or the task"
     A value WITHOUT a leading '/' (for example 'zephyr' or 'plant32/zephyr') is only rejected when it is the trailing part of exactly one allowed
     full name; otherwise it is an ordinary string (modes, types, ...) and passes.
  3. Key check: required keys are read from the task text by one rule (see parse_required_key_sets); no clause found -> no key check.
  4. Numbers: LOG ONLY (is the integer found as a token in some tool result or the task?).
  5. At most 2 rejections per episode (counted by the caller), then the answer is accepted.
"""
import json
import re

ABSOLUTE_NAME = re.compile(r"/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+")
RELATIVE_NAME = re.compile(r"(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+")
# a full name inside free text: starts with '/', not preceded by a word character, '/', '.', ':' or '-' (so 'std_srvs/srv/Trigger' is not a name)
NAME_IN_TEXT = re.compile(r"(?<![\w/.:-])/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+")
NODE_BLOCK = re.compile(r"Node name:\s*(\S+)\s+Node namespace:\s*(\S+)")
ERROR_ENTRY = re.compile(r"^\s*(error|Error)")


# ------------------------------------------------------------------ allowed names
def names_in_text(text):
    text = text.replace("\\n", "\n")
    found = set(NAME_IN_TEXT.findall(text))
    found.update(f"{ns.rstrip('/')}/{name}" for name, ns in NODE_BLOCK.findall(text))  # 'ros2 topic info --verbose' prints name and namespace separately
    return found


def successful_text_parts(output):
    """Texts of a tool result that carry information. A failed call contributes nothing. In a list-tool result (one entry per item) failed
    items are skipped one by one, so a failed item neither hides the successful ones nor makes its echoed (possibly wrong) name count as seen."""
    if isinstance(output, dict):
        if "error" in output:
            return []
        if any(isinstance(v, dict) and "error" in v for v in output.values()):
            return [json.dumps({k: v}) for k, v in output.items() if not (isinstance(v, dict) and "error" in v)]
    return [output if isinstance(output, str) else json.dumps(output)]


def allowed_names(task_text, tool_outputs):
    """tool_outputs: the raw output of every tool call of the episode, in order."""
    allowed = names_in_text(task_text)
    for output in tool_outputs:
        for part in successful_text_parts(output):
            allowed |= names_in_text(part)
            if isinstance(output, dict) and isinstance(output.get("nodes"), list):
                allowed.update(n for n in output["nodes"] if isinstance(n, str) and ABSOLUTE_NAME.fullmatch(n))
    return allowed


# ------------------------------------------------------------------ name check
def answer_strings(answer):
    """(path, kind, text) for every string value and every key of a nested object. kind is 'value' or 'key'."""
    found = []

    def walk(value, path):
        if isinstance(value, str):
            found.append((path, "value", value))
        elif isinstance(value, dict):
            for key, child in value.items():
                found.append((f"{path}.{key}" if path else str(key), "key", str(key)))
                walk(child, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(answer, "")
    # top-level keys are the task's own answer keys, not graph names; the key check handles them
    return [(p, k, t) for p, k, t in found if not (k == "key" and "." not in p and "[" not in p)]


def trailing_matches(text, allowed):
    """Allowed full names that end with text at a '/' boundary (and are not equal to text)."""
    tail = "/" + text.lstrip("/")
    return sorted(n for n in allowed if n != text and n.endswith(tail))


def name_problems(answer, allowed):
    """List of dict(path, value, kind, rule, hint). Empty list = pass."""
    problems = []
    for path, kind, text in answer_strings(answer):
        if ABSOLUTE_NAME.fullmatch(text):
            if text in allowed:
                continue
            matches = trailing_matches(text, allowed)
            if len(matches) == 1:
                problems.append(dict(path=path, value=text, kind=kind, rule="unique_suffix", hint=f"'{text}' is not a full name seen in a tool result; did you mean '{matches[0]}'?"))
            else:
                problems.append(dict(path=path, value=text, kind=kind, rule="never_seen", hint=f"'{text}': this name never appeared in a tool result or the task; look it up or check spelling."))
        elif RELATIVE_NAME.fullmatch(text):
            matches = trailing_matches(text, allowed)
            if len(matches) == 1:
                problems.append(dict(path=path, value=text, kind=kind, rule="unique_suffix_bare", hint=f"'{text}' is not a full name; did you mean '{matches[0]}'?"))
    return problems


# ------------------------------------------------------------------ key check
def parse_required_key_sets(task_text):
    """One general rule on the task text: every sentence containing 'keys' lists the keys after that word, separated by commas and 'and'
    (parenthesised explanations are dropped). A clause is used only if every listed item is a single identifier.
    Returns a list of key sets (alternatives: a conditional task has one per branch); [] means 'could not parse, no key check'."""
    sets = []
    for sentence in re.split(r"(?<=[.?!])\s+", task_text):
        match = re.search(r"\bkeys?\s+(.*)", sentence)
        if not match:
            continue
        tail = match.group(1)
        while True:  # drop parentheses, innermost first
            reduced = re.sub(r"\([^()]*\)", "", tail)
            if reduced == tail:
                break
            tail = reduced
        tail = tail.strip().rstrip(".")
        items = [i.strip() for i in re.split(r",\s*(?:and\s+)?|\s+and\s+", tail) if i.strip()]
        if items and all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", i) for i in items):
            sets.append(set(items))
    return sets


def key_problem(answer, key_sets):
    """None when the answer has at least one clause's keys (extra keys are the scorer's business), else a hint."""
    if not key_sets or not isinstance(answer, dict):
        return None
    if any(keys <= set(answer) for keys in key_sets):
        return None
    best = min(key_sets, key=lambda keys: len(keys - set(answer)))
    missing = sorted(best - set(answer))
    return dict(rule="missing_keys", missing=missing, hint=f"The task asks for the keys {sorted(best)}; your answer lacks {missing}.")


# ------------------------------------------------------------------ numbers (log only)
def numbers_unseen(answer, task_text, tool_outputs):
    """Integers in the answer that appear as a token neither in a successful tool result nor in the task text. Logged, never used to reject."""
    texts = [task_text] + [p for o in tool_outputs for p in successful_text_parts(o)]
    corpus = "\n".join(texts).replace("\\n", "\n")
    unseen = []

    def walk(value, path):
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)) and not re.search(rf"(?<![\w.]){re.escape(str(value))}(?![\w])", corpus):
            unseen.append(dict(path=path, value=value))
        elif isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(answer, "")
    return unseen


# ------------------------------------------------------------------ the gate
def check_answer(answer, task_text, tool_outputs):
    """Returns dict(reject: bool, hint: str|None, problems: [...], numbers_unseen: [...]). Does not count rejections; the caller does."""
    allowed = allowed_names(task_text, tool_outputs)
    problems = name_problems(answer, allowed)
    key = key_problem(answer, parse_required_key_sets(task_text))
    if key:
        problems.append(key)
    unseen = numbers_unseen(answer, task_text, tool_outputs)
    hint = None
    if problems:
        hint = "Answer not accepted yet. " + " ".join(p["hint"] for p in problems) + " Call final_answer again with the corrected answer."
    return dict(reject=bool(problems), hint=hint, problems=problems, numbers_unseen=unseen)
