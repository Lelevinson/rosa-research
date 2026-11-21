"""Stage 3 request labels from the verified minimal stage plans (offline).

For each task the minimal-sequence log (stage3_floorcheck run) gives, per stage, the calls a perfect agent makes.
Each actual request after the first and before the final answer gets one label:
  RED      only repeats/subsets of earlier successful calls, or param_list when the task names the parameter (unneeded)
  REC      follows a request with an error
  NEEDED   first request that carries the NEXT dependency stage (stage s>=2 while stage s-1 has been started) -> JUDG or DEP-dependent
  LATE     carries only calls of a stage already started (serialised continuation) or stage-1 calls issued after the first request
           (their arguments came from the task text) -> DEP, args available earlier: avoidable
  EXPLORE  only calls outside the plan whose arguments come from earlier results (unneeded route needing a choice): codebook JUDG
  NOARG    only calls outside the plan whose arguments are in the task text or absent: DEP available earlier: avoidable
Avoidable under the frozen definition = RED + REC + LATE + NOARG. EXPLORE is reported separately.
"""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from label_requests import string_leaves, parse_args

TASKS = {t["id"]: t for t in json.loads((HERE / "stage3_tasks.json").read_text())}
FLOORCHECK = sorted((HERE.parents[1] / "_artifacts/runs/headroom_diagnostic_20261112").glob("stage3_floorcheck_*"))[-1]


def plan(task_id):
    elems = {}
    for e in json.loads((FLOORCHECK / f"minimal_{task_id}.json").read_text())["log"]:
        t, a, s = e["tool"], e["args"], e["stage"]
        if t == "ros2_node_list":
            elems[("node_list",)] = s
        elif t == "ros2_node_info":
            for n in a["nodes"]:
                elems[("node_info", n)] = s
        elif t == "ros2_topic_info":
            for n in a["topics"]:
                elems[("topic_info", n)] = s
        elif t == "ros2_param_get":
            elems[("param_get", a["node_name"], a["param_name"])] = s
    return elems


def call_elements(c):
    n, a = c["name"], c["args"]
    if n == "ros2_node_list":
        return [("node_list",)]
    if n == "ros2_node_info":
        return [("node_info", x) for x in a.get("nodes", [])]
    if n == "ros2_topic_info":
        return [("topic_info", x) for x in a.get("topics", [])]
    if n == "ros2_param_get":
        return [("param_get", a.get("node_name"), a.get("param_name"))]
    return []


def stage_of(c, elems):
    """(stage or None, short_name_mapped, all_elements_in_plan)"""
    found, mapped, total = [], False, 0
    for el in call_elements(c):
        total += 1
        if el in elems:
            found.append(elems[el])
        else:  # short name such as 'anvil' for '/plant32/anvil'
            alt = [k for k in elems if k[0] == el[0] and len(k) == len(el) and k[1].endswith("/" + el[1]) and k[2:] == el[2:]]
            if alt:
                found.append(elems[alt[0]]); mapped = True
    return (min(found) if found else None), mapped, (len(found) == total and total > 0)


def label_episode(task_id, requests):
    """requests: list of dicts with calls (name,args,text,ok). Returns list of (request_index, label, note)."""
    elems = plan(task_id)
    task_text = TASKS[task_id]["request"]
    started, done_calls, done_keys, failed_stages = set(), set(), set(), set()
    prev_error, out = False, []
    for r in requests:
        k = r["index"]
        calls = r["calls"]
        errs = [not c["ok"] for c in calls]
        stages = [stage_of(c, elems) for c in calls]
        key = lambda c: (c["name"], json.dumps(c["args"], sort_keys=True))
        label = None
        if k > 1 and calls:
            repeats = all((json.dumps([c["name"], c["args"]], sort_keys=True) in done_keys) or (call_elements(c) and all(el in done_calls for el in call_elements(c))) for c in calls)
            names_param = all(c["name"] == "ros2_param_list" and "gain" in task_text or c["name"] == "ros2_param_list" and "setpoint" in task_text for c in calls)
            if repeats:
                label = "RED"
            elif prev_error:
                label = "REC"
            elif names_param:
                label = "RED"
            else:
                needed = any(s is not None and s >= 2 and (s - 1) in started and s not in started for s, _, _ in stages)
                matched_late = any(s is not None and (s == 1 or s in started) for s, _, _ in stages)
                unmatched = [c for c, (s, _, _) in zip(calls, stages) if s is None]
                redo = any(s is not None and s in failed_stages for s, _, _ in stages)
                if needed and redo:
                    label = "REC"  # re-issue of a stage whose earlier attempt failed (e.g. short node name)
                elif needed:
                    label = "NEEDED"
                elif matched_late:
                    label = "LATE"
                elif unmatched:
                    arg_strings = [x for c in unmatched for x in string_leaves(c["args"])]
                    label = "NOARG" if all(x in task_text for x in arg_strings) else "EXPLORE"
                else:
                    label = "UNCLEAR"
        elif k > 1:
            label = "FIN"
        out.append((k, label))
        for c, (s, mapped, _), err in zip(calls, stages, errs):
            if not err:
                for el in call_elements(c):
                    done_calls.add(el)
                if s is not None and not mapped:
                    started.add(s)
                done_keys.add(json.dumps([c["name"], c["args"]], sort_keys=True))
            elif s is not None:
                failed_stages.add(s)
        prev_error = any(errs)
    return out
