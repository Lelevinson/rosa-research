"""Scoring and labelling for pilot episodes (offline, no inference, no ROS).

Rules, identical for every arm:
- Answer: the `final_answer` submission when the arm accepted one (event `final_answer_accepted`); otherwise the LAST complete
  top-level JSON object in the free-text answer (one documented legacy rule; Stage 1-3 used the first object, which penalised
  models that quote a tool result before answering).
- Exactness: vendored baseline_audit.canonical / differences against the task's declared answer (unchanged).
- Support: the strict Stage 3 rule (every declared fact must be backed by a successful tool result), extended with one
  requirement type, ['absent', node], for the absent-target tasks (see support_missing).
- A tool result's arguments are the arguments EXECUTED: when a handler repaired a call (H2) the trace holds an
  `effective_call` event and that event's arguments are used, otherwise the harm tasks would be scored against the wrong node.
"""
import ast
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
STAGE3 = HERE.parent / "headroom_diagnostic_20261112"
sys.path.insert(0, str(STAGE3 / "vendor"))
sys.path.insert(0, str(STAGE3))
import baseline_audit as audit  # noqa: E402
import score_stage1 as s1  # noqa: E402

ABSENT_TEXT = re.compile(r"not found|Unable to find|does not exist|no such node", re.I)


def last_json_object(text):
    """The last complete top-level JSON object in text (an object nested inside an earlier one does not count)."""
    decoder = json.JSONDecoder()
    found, end_of_last = None, -1
    for match in re.finditer(r"\{", text or ""):
        if match.start() < end_of_last:
            continue
        try:
            value, length = decoder.raw_decode(text[match.start():])
        except ValueError:
            continue
        if isinstance(value, dict):
            found, end_of_last = value, match.start() + length
    return found


def tool_rows(events):
    """s1.tool_results with executed arguments substituted where a handler changed the call."""
    effective = {e["tool_run_id"]: e["args"] for e in events if e["kind"] == "effective_call" and e.get("tool_run_id")}
    rows = s1.tool_results(events)
    run_ids = [e.get("run_id") for e in events if e["kind"] == "tool_start"]
    starts = [e for e in events if e["kind"] == "tool_start"]
    ends = {e.get("run_id"): e for e in events if e["kind"] == "tool_end"}
    paired = [s for s in starts if s.get("run_id") in ends]
    for row, start in zip(rows, paired):
        row["run_id"] = start.get("run_id")
        row["given_args"] = row["args"]
        if start.get("run_id") in effective:
            row["args"] = effective[start["run_id"]]
    return rows


def param_values(rows):
    values = {}
    for r in rows:
        if r["name"] == "ros2_param_get" and r["ok"] and isinstance(r["output"], dict):
            for param, raw in r["output"].items():
                m = re.search(r"(Boolean|Integer|String|Double) value is:\s*(.*)", str(raw))
                if m:
                    text = m[2].strip()
                    value = (text == "True") if m[1] == "Boolean" else int(text) if m[1] == "Integer" else float(text) if m[1] == "Double" else text
                    values[(r["args"].get("node_name"), r["args"].get("param_name", param))] = value
    return values


def support_missing(task, rows):
    good = [r for r in rows if r["ok"]]
    text = "\n".join(r["text"].replace("\\n", "\n") for r in good)
    known = s1.assembled(text)
    params = param_values(rows)
    missing = []
    for req in task["support"]:
        if req[0] == "param":
            if params.get((req[1], req[2])) != req[3]:
                missing.append(f"param {req[1]} {req[2]}={req[3]!r} not read")
        elif req[0] == "absent":
            # Supported only by a successful node listing without the node, or by a failed read of the node that says it was not found.
            listing = any(r["name"] == "ros2_node_list" and r["ok"] and req[1] not in r["text"].replace("\\n", "\n").split() and f'"{req[1]}"' not in r["text"] for r in rows)
            failed = any((not r["ok"]) and ABSENT_TEXT.search(r["text"]) and req[1] in json.dumps(r["given_args"]) for r in rows)
            if not (listing or failed):
                missing.append(f"absence of {req[1]} not shown")
        elif req[1] not in text and req[1] not in known and req[1] not in task["request"]:
            missing.append(f"text {req[1]!r} not seen in a tool result")
    return missing


def episode_answer(events):
    accepted = [e for e in events if e["kind"] == "final_answer_accepted"]
    if accepted:
        return accepted[-1]["answer"], "final_answer"
    end = [e for e in events if e["kind"] == "episode_end"]
    return last_json_object(end[-1].get("answer") if end else None), "free_text"


def score_events(task, events):
    rows = tool_rows(events)
    answer, source = episode_answer(events)
    issues = audit.differences(audit.canonical(answer), audit.canonical(task["answer"])) if answer is not None else ["no answer object"]
    missing = support_missing(task, rows)
    metrics = s1.episode_metrics(events)
    return dict(answer_object=answer, answer_source=source, exact=not issues, issues=issues, support_missing=missing,
                supported_complete=(not issues and not missing), rows=rows, metrics=metrics)


# ------------------------------------------------------------------ automatic failure-row labels (taxonomy rows of FAILURE_CATEGORIZATION.md)
def failure_rows(task, events, scored):
    """Descriptive heuristics, not a measurement: rows 1-14 where a simple trace rule exists; row 9 and row 15 are not labelled."""
    rows, labels = scored["rows"], set()
    seen_ok, seen_failed = set(), set()
    for r in rows:
        key = (r["name"], json.dumps(r["args"], sort_keys=True))
        if key in seen_ok and r["ok"]:
            labels.add(1)
        if key in seen_failed:
            labels.add(8)
        (seen_ok if r["ok"] else seen_failed).add(key)
        if not r["ok"] and re.search(r"not found|Unable to find|no such", r["text"], re.I):
            labels.add(2)
        if re.search(r"is not valid under any|is not of type|should be a valid|Input should be|type_error|expected type", r["text"]):
            labels.add(3)
        if re.search(r"Field required|missing required|Missing required", r["text"]):
            labels.add(4)
        if re.search(r"is not a valid tool", r["text"]):
            labels.add(5)
        if r["name"] in ("add", "subtract", "multiply", "divide", "wait", "set_debugging", "set_verbosity", "ros2_param_set", "ros2_service_call"):
            labels.add(6)
    end = [e for e in events if e["kind"] == "episode_end"]
    error = end[-1].get("error") if end else "no episode_end"
    tool_calls = sum(len(e["message"].get("tool_calls", [])) for e in events if e["kind"] == "model_end")
    if error or any(e["kind"] == "model_error" for e in events):
        labels.add(7)
    if scored["answer_object"] is None and not error:
        labels.add(12)
    if not scored["exact"] and scored["answer_object"] is not None:
        labels.add(13)
    if scored["exact"] and scored["support_missing"]:
        labels.add(11)
    if scored["support_missing"] and not scored["exact"]:
        labels.add(10)
    if tool_calls == 0:
        labels.add(14)
    return sorted(labels)
