"""Parse recorded fixed-loop traces into requests, calls and a name ledger (offline replay, 2026-11-16). No model, no ROS.

Parsed episode = dict(run_id, model, arm, task, seed, supported, task_text, requests=[Request], answer, rows)
Request = dict(index, input_tokens, output_tokens, calls=[Call])
Call    = dict(tool, args, entity_arg, entity, output, ok, request, is_harness_error, item_of_list)
"""
import ast
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
REPO = HERE.parents[2]
sys.path.insert(0, str(STUDIES / "build_round1_20261115"))
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
import answer_gate as ag  # noqa: E402
import scorer_v2 as v2  # noqa: E402
import score_round1  # noqa: E402

NOT_FOUND = re.compile(r"not found|Unable to find|does not exist|no such", re.I)
HARNESS_TEXT = re.compile(r"^(Invalid arguments|Tool \S+ (is not available|failed)|final_answer needs|Answer recorded|Answer not accepted|The list of names|Too many names)")
ENTITY_STEMS = {"node", "topic", "service"}


def entity_argument(name):
    """Schema-based: property name minus a trailing '_name' and a plural 's' is node/topic/service."""
    stem = re.sub(r"_name$", "", name)
    stem = stem[:-1] if stem.endswith("s") else stem
    return stem in ENTITY_STEMS


def load_tasks():
    tasks = {t["id"]: t for t in json.loads((STUDIES / "headroom_diagnostic_20261112/stage3_tasks.json").read_text())}
    tasks.update({t["id"]: t for t in json.loads((STUDIES / "small_model_harness_20261115/e1h_tasks.json").read_text())})
    return tasks


def run_rows():
    """(set name, log row) for the pilot fixed loop and the four round-1 arms."""
    excluded = set()
    for group in json.loads((STUDIES / "small_model_harness_20261115/INFRA_EXCLUDED.json").read_text()).values():
        excluded |= set(group["run_ids"])
    out = []
    for line in (STUDIES / "small_model_harness_20261115/RESULTS_LOG.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["arm"] == "C1" and r["run_id"] not in excluded:
            out.append(("pilot fixed loop", r))
    for line in (STUDIES / "build_round1_20261115/RESULTS_LOG.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["phase"] == "full":
            out.append(("round 1 control" if r["arm"] == "C1" else "round 1 add-on arms", r))
    return out


def parse(group, row, tasks):
    events = v2.s1.read_events(REPO / row["trace_path"])
    task = tasks[row["task"]]
    task_text = next(e["request"] for e in events if e["kind"] == "effective_request")
    scored = score_round1.score_events(task, events)
    rows_for_score = score_round1.expanded_rows(events)
    tool_ends = {e.get("run_id"): e for e in events if e["kind"] == "tool_end"}
    requests, current = [], None
    for e in events:
        if e["kind"] == "model_end":
            usage = e.get("usage") or {}
            current = dict(index=len(requests) + 1, input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0), calls=[], units=[])
            requests.append(current)
        elif e["kind"] == "tool_start" and current is not None:
            end = tool_ends.get(e.get("run_id"))
            try:
                args = ast.literal_eval(e["input"]) if isinstance(e["input"], str) else e["input"]
            except (ValueError, SyntaxError):
                args = {}
            output = end.get("output") if end else None
            text = output if isinstance(output, str) else json.dumps(output)
            harness_error = isinstance(output, str) and bool(HARNESS_TEXT.match(output))
            items = expand_call(e["name"], args, output, text, harness_error, current["index"])
            current["calls"].extend(items)
            current.setdefault("units", []).append(dict(tool=e["name"], args=args, output=output, text=text, harness_error=harness_error, items=items,
                                                     ok=not is_failure(output, text, harness_error) and not any(not i["ok"] for i in items if i["entity"] is not None and isinstance(output, dict) and "error" in output)))
    return dict(run_id=row["run_id"], group=group, model=row["model"], arm=row["arm"], task=row["task"], seed=row["seed"], supported=scored["supported_complete"],
                task_text=task_text, requests=requests, answer=scored["answer_object"], rows=rows_for_score, task_def=task, scored=scored)


def is_failure(output, text, harness_error):
    if harness_error:
        return True
    if isinstance(output, dict) and "error" in output:
        return True
    return bool(NOT_FOUND.search(text)) and not isinstance(output, dict)


def expand_call(tool, args, output, text, harness_error, request):
    """One Call per entity of a list argument; calls without an entity argument give one Call with entity None."""
    entity_args = [k for k in args if entity_argument(k)]
    if tool == "final_answer":
        return [dict(tool=tool, args=args, entity_arg=None, entity=None, output=output, text=text, ok=not harness_error, request=request, harness_error=harness_error)]
    if not entity_args:
        return [dict(tool=tool, args=args, entity_arg=None, entity=None, output=output, text=text, ok=not is_failure(output, text, harness_error), request=request, harness_error=harness_error)]
    key = entity_args[0]
    value = args[key]
    values = value if isinstance(value, list) else [value]
    calls = []
    for entity in values:
        if isinstance(output, dict) and not harness_error and isinstance(value, list) and entity in output:
            part = output[entity]  # list tools and list-argument calls: one entry per item
        else:
            part = output
        ptext = part if isinstance(part, str) else json.dumps(part)
        calls.append(dict(tool=tool, args={k: v for k, v in args.items() if k != key}, entity_arg=key, entity=entity, output=part, text=ptext,
                          ok=not is_failure(part, ptext, harness_error), request=request, harness_error=harness_error))
    return calls


# ------------------------------------------------------------------ groups (sibling sets) and ledger
HEADING = re.compile(r"^\s*([A-Za-z][A-Za-z ]*):\s*$")


def groups_of(output, text):
    """Lists of full names that belong together: one JSON list value or one heading section of a text result; a lone name is its own group."""
    found = []
    if isinstance(output, dict):
        for value in output.values():
            if isinstance(value, list):
                names = [n for n in value if isinstance(n, str) and ag.ABSOLUTE_NAME.fullmatch(n)]
                if names:
                    found.append(names)
    sections, current = [], []
    for line in text.replace("\\n", "\n").split("\n"):
        if HEADING.match(line):
            if current:
                sections.append(current)
            current = []
            continue
        first = ag.NAME_IN_TEXT.findall(line)
        if first and re.match(r"^\s*/", line):
            current.append(first[0])
    if current:
        sections.append(current)
    found.extend(s for s in sections if s)
    unique = []
    for g in found:
        g = list(dict.fromkeys(g))
        if g and g not in unique:
            unique.append(g)
    return unique


def ledger_events(ep):
    """Per call, in order: (request index, call, names newly added to the ledger by this call's successful result)."""
    seen = set(ag.names_in_text(ep["task_text"]))
    out = []
    for r in ep["requests"]:
        for c in r["calls"]:
            new = set()
            if c["ok"] and not c["harness_error"] and c["tool"] != "final_answer":
                names = ag.names_in_text(c["text"] if isinstance(c["text"], str) else "")
                if isinstance(c["output"], dict) and isinstance(c["output"].get("nodes"), list):
                    names |= {n for n in c["output"]["nodes"] if isinstance(n, str) and ag.ABSOLUTE_NAME.fullmatch(n)}
                new = names - seen
                seen |= names
            out.append((r["index"], c, new))
    return out, seen
