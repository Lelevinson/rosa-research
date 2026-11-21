"""SCORER v2.0 (frozen 2026-11-15; see research/decisions/2026-11-15-scorer-v2.md). Same support/exactness rules as pilot_score.py (scorer v1) plus exactly two fixes.

Fix 1, leading slash (decided by slash_check.py on the real fixture):
  - `ros2 param get` / `ros2 param list` resolve a relative node name (`plant32/anvil`) to the same node as `/plant32/anvil`, so a parameter read
    made with the relative form supports a task fact about the absolute node: node names of param reads are normalised to '/' + name.lstrip('/').
  - `ros2 node info plant32/anvil` does NOT resolve (it fails for a node that exists), so a failed relative-name node_info is NOT evidence that the
    node is absent (unchanged from v1: it never counted). Absence is shown by a successful node listing without the name, or by a failed read that
    names the exact absolute name, or by a failed param read of the relative form of that name (param tools resolve it).
Fix 2, wrapper: if the answer is the last JSON object of the final free text and that object has exactly one key, `answer`, whose value is an object,
  the inner object is scored. (A `final_answer` tool object is never unwrapped.)
Everything else (answer = final_answer object else last complete JSON object; exact match by vendored baseline_audit; strict support) is as in v1.

Interface for other harnesses (for example Forge runs): score_task(task, answer_object, rows) with rows = list of dict(name, args, given_args, output, text, ok);
and last_json_object / unwrap_answer to get answer_object from a final text.
"""
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
STAGE3 = HERE.parent / "headroom_diagnostic_20261112"
sys.path.insert(0, str(STAGE3 / "vendor")); sys.path.insert(0, str(STAGE3))
import baseline_audit as audit  # noqa: E402  (vendored, unchanged)
import score_stage1 as s1  # noqa: E402  (unchanged Stage 1 helpers: assembled(), tool_results(), ERROR)

SCORER_VERSION = "scorer-v2.0"
ABSENT_TEXT = re.compile(r"not found|Unable to find|does not exist|no such node", re.I)
PARAM_TOOLS = ("ros2_param_get", "ros2_param_list")  # these resolve relative node names in ROS 2 Jazzy (checked in slash_check.json)


def absolute(name):
    return "/" + name.lstrip("/") if isinstance(name, str) else name


def last_json_object(text):
    decoder, found, end_of_last = json.JSONDecoder(), None, -1
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


def unwrap_answer(obj):
    """Fix 2: {"answer": {...}} and nothing else -> the inner object."""
    if isinstance(obj, dict) and list(obj) == ["answer"] and isinstance(obj["answer"], dict):
        return obj["answer"]
    return obj


def param_values(rows):
    values = {}
    for r in rows:
        if r["name"] == "ros2_param_get" and r["ok"] and isinstance(r["output"], dict):
            for param, raw in r["output"].items():
                m = re.search(r"(Boolean|Integer|String|Double) value is:\s*(.*)", str(raw))
                if m:
                    text = m[2].strip()
                    value = (text == "True") if m[1] == "Boolean" else int(text) if m[1] == "Integer" else float(text) if m[1] == "Double" else text
                    values[(absolute(r["args"].get("node_name")), r["args"].get("param_name", param))] = value  # Fix 1
    return values


def absence_shown(name, rows):
    for r in rows:
        if r["name"] == "ros2_node_list" and r["ok"]:
            nodes = r["output"].get("nodes", []) if isinstance(r["output"], dict) else []
            if name not in nodes and f'"{name}"' not in r["text"] and name not in r["text"].replace("\\n", "\n").split():
                return True
        if (not r["ok"]) and ABSENT_TEXT.search(r["text"]):
            given = r["given_args"]
            exact = name in json.dumps(given)  # v1 rule: the exact absolute name appears in the failed call
            resolved = r["name"] in PARAM_TOOLS and absolute(given.get("node_name")) == name  # Fix 1: param tools resolve the relative form
            if exact or resolved:
                return True
    return False


def support_missing(task, rows):
    good = [r for r in rows if r["ok"]]
    text = "\n".join(r["text"].replace("\\n", "\n") for r in good)
    known = s1.assembled(text)
    params = param_values(rows)
    missing = []
    for req in task["support"]:
        if req[0] == "param":
            if params.get((absolute(req[1]), req[2])) != req[3]:
                missing.append(f"param {req[1]} {req[2]}={req[3]!r} not read")
        elif req[0] == "absent":
            if not absence_shown(req[1], rows):
                missing.append(f"absence of {req[1]} not shown")
        elif req[1] not in text and req[1] not in known and req[1] not in task["request"]:
            missing.append(f"text {req[1]!r} not seen in a tool result")
    return missing


def score_task(task, answer_object, rows):
    issues = audit.differences(audit.canonical(answer_object), audit.canonical(task["answer"])) if answer_object is not None else ["no answer object"]
    missing = support_missing(task, rows)
    return dict(exact=not issues, issues=issues, support_missing=missing, supported_complete=(not issues and not missing), scorer=SCORER_VERSION)


# ---- adapter for pilot traces (same trace format as pilot_score.py) ----
def tool_rows(events):
    effective = {e["tool_run_id"]: e["args"] for e in events if e["kind"] == "effective_call" and e.get("tool_run_id")}
    rows = s1.tool_results(events)
    starts = [e for e in events if e["kind"] == "tool_start"]
    ends = {e.get("run_id") for e in events if e["kind"] == "tool_end"}
    for row, start in zip(rows, [s for s in starts if s.get("run_id") in ends]):
        row["given_args"] = row["args"]
        if start.get("run_id") in effective:
            row["args"] = effective[start["run_id"]]
    return rows


def episode_answer(events):
    accepted = [e for e in events if e["kind"] == "final_answer_accepted"]
    if accepted:
        return accepted[-1]["answer"], "final_answer"
    end = [e for e in events if e["kind"] == "episode_end"]
    return unwrap_answer(last_json_object(end[-1].get("answer") if end else None)), "free_text"


def score_events(task, events):
    answer, source = episode_answer(events)
    out = score_task(task, answer, tool_rows(events))
    out.update(answer_object=answer, answer_source=source)
    return out
