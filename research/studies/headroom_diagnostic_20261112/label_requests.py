"""Stage 0 labeling of ROSA model requests (offline; no inference, no ROS).

For every model request after the first in each preserved trace this script
computes objective features and proposes a reason label. Proposed labels are
a FIRST PASS: `manual_labels.json` overrides them after human review, and the
override reason is kept in the output so every label is traceable.

Labels (brief section 4): JUDG, DEP, REC, ORD, FIN, RED, UNCLEAR.
Extra column `batchable` (not a label): True when every call of the request
had all string arguments verbatim available one or more requests earlier, so a
perfect batching policy could have issued it earlier (see ready_request).
This is a bound on batching headroom, not proof the earlier call was wise.

Usage: python3 label_requests.py <repo_root> <out_dir>
"""
import ast
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_requests import FROZEN, extract_episode  # noqa: E402

TOKEN = re.compile(r"[/\w][/\w.~-]*[/\w]")  # names, topics, params; no trailing punctuation
NOISE_TOOLS = {"set_debugging", "set_verbosity", "wait", "ros2_doctor"}
FETCH_TOOLS = {"ros2_param_get", "ros2_node_info", "ros2_topic_info", "ros2_service_info",
               "ros2_param_list", "ros2_topic_echo"}
LIST_TOOLS = {"ros2_node_list", "ros2_topic_list", "ros2_service_list"}

# Dependency floors (model requests = observation stages + 1 final answer).
# `strict` assumes no guessed names; `alt` allows the stated shortcut.
# Derivations are written out in PROTOCOL_STAGE0.md section 3.
FLOORS = {
    "t1": {"strict": 4, "alt": 3},   # node_list+topic_list | param_list+topic_info | param_get x3
    "t2": {"strict": 3, "alt": 3},   # node_list+service_list | service_info+param_get
    "t3": {"strict": 3, "alt": 3},   # node_list | node_info
    "d1": {"strict": 3, "alt": 3},   # topic_info (verbose names FQN-assemblable) | param_get x endpoints
    "d2": {"strict": 4, "alt": 3},   # node_list | node_info (servers) | param_get ; alt = over-fetch param_get
    "x1": {"strict": 3, "alt": 3},   # node_list+topic_list | param_get x4 + topic_info x2
    "d1_recovery": {"strict": 4, "alt": 4},  # retired-node check alone | topic_info | param_get | final
}

BATCHING_PERMITTED = {  # from the prompts actually sent (checked in PROTOCOL_STAGE0.md section 2)
    "baseline": "conflicted",    # original 'NEVER call multiple tools' text kept in A, B and C
    "narration": "deconflicted",
    "coverage": "deconflicted",
}


def parse_args(raw):
    if isinstance(raw, dict):
        return raw
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return {"_unparsed": str(raw)}


def string_leaves(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [leaf for v in value.values() for leaf in string_leaves(v)]
    if isinstance(value, list):
        return [leaf for v in value for leaf in string_leaves(v)]
    return []


def item_keys(name, args):
    """Atomic things a call fetches, for redundancy checks."""
    if name in ("ros2_node_info",):
        return [(name, n) for n in args.get("nodes", [])]
    if name == "ros2_topic_info":
        return [(name, t) for t in args.get("topics", [])]
    if name == "ros2_service_info":
        return [(name, s) for s in args.get("services", [])]
    if name == "ros2_param_get":
        return [(name, args.get("node_name"), args.get("param_name"))]
    if name == "ros2_param_list":
        return [(name, args.get("node_name"))]
    return [(name, json.dumps(args, sort_keys=True))]


def is_error(result):
    text = result or ""
    return bool(re.search(r"'error'|\"error\"|Unable to find|Node not found|not found", text))


def normalise(text):
    """Baseline traces hold real newlines; later traces hold repr strings with literal backslash-n."""
    return (text or "").replace("\\n", "\n")


def assembled_names(text):
    """Full names a model can build from verbose topic info (namespace + node name)."""
    return {f"{ns.rstrip('/')}/{name}" for name, ns in
            re.findall(r"Node name:\s*(\S+)\s+Node namespace:\s*(\S+)", text)}


def analyse_episode(info, requests, request_text):
    rows = []
    first_available = {}   # string -> first request index whose results contain it (0 = task text)
    for leaf in set(TOKEN.findall(request_text)):
        first_available[leaf] = 0
    succeeded = set()      # (tool, item...) fetched successfully so far
    failed_tools = set()
    previous_had_error = False
    for request in requests:
        k = request["request_index"]
        calls = []
        for call in request["calls"]:
            args = parse_args(call["args"])
            calls.append((call, args))
        unavailable = False
        ready = 1
        for call, args in calls:
            for leaf in string_leaves(args):
                if leaf in ("use_sim_time",):
                    continue
                avail = first_available.get(leaf)
                if avail is None:
                    unavailable = True
                else:
                    ready = max(ready, avail + 1)
        if info["task"] == "d1_recovery" and k >= 1:
            check_only = all("retired_source" in json.dumps(a) for _, a in calls)
            if not check_only:
                ready = max(ready, 2)   # ordering requirement: the stale-node check goes first
        # redundancy: every fetched item already succeeded earlier
        redundant = bool(calls) and all(
            call["name"] not in NOISE_TOOLS and all(key in succeeded for key in item_keys(call["name"], args))
            for call, args in calls)
        noise = bool(calls) and all(call["name"] in NOISE_TOOLS for call, _ in calls)
        errors_here = [is_error(call["result"]) for call, _ in calls]
        row = {
            "corpus": info["corpus"], "episode": info["episode"], "task": info["task"], "arm": info["arm"],
            "model": info["model"], "request_index": k, "trace_line": request["trace_line"],
            "n_calls": len(calls),
            "calls": "; ".join(f"{c['name']}({json.dumps(a)[:90]})" for c, a in calls),
            "ready_request": ready, "guessed_args": unavailable,
            "batchable": bool(calls) and not unavailable and ready < k,
            "redundant_items": redundant, "own_call_error": any(errors_here), "any_error": any(errors_here),
            "prev_request_error": previous_had_error,
            "input_tokens": request["input_tokens"], "output_tokens": request["output_tokens"],
            "seconds": request["seconds"],
        }
        # ---- first-pass label (kept deliberately simple and inspectable) ----
        if not calls:
            auto, why = "FIN", "no tool call: final answer"
        elif noise:
            auto, why = "RED", "tool returns no task information"
        elif redundant:
            auto, why = "RED", "all fetched items already obtained successfully earlier"
        elif (info["task"] != "t1" and all(c["name"] == "ros2_param_list" for c, _ in calls)
              and "use_sim_time" in request_text):
            auto, why = "RED", "unneeded: the parameter name is given in the task text, so listing names adds nothing required"
        elif previous_had_error or any(c["name"] in failed_tools for c, _ in calls):
            auto, why = "REC", "follows an error or re-issues a tool that failed earlier"
        elif row["batchable"]:
            auto, why = "DEP", "arguments were available earlier; serialised, not dependent on the last observation"
        elif any(c["name"] in ("ros2_node_info", "ros2_topic_info", "ros2_service_info", "ros2_topic_echo")
                 for c, _ in calls):
            auto, why = "JUDG", "chooses which observed node/topic/service to inspect, using the preceding observation"
        elif all(c["name"] in ("ros2_param_get", "ros2_param_list") for c, _ in calls):
            auto, why = "DEP", "parameter read whose node/name were copied from the preceding observation"
        else:
            auto, why = "UNCLEAR", "needs manual review"
        row["auto_label"], row["auto_reason"] = auto, why
        rows.append(row)
        # ---- update state with this request's results ----
        for call, args in calls:
            text = normalise(call["result"])
            if is_error(text):
                failed_tools.add(call["name"])
            else:
                for key in item_keys(call["name"], args):
                    succeeded.add(key)
            for leaf in set(TOKEN.findall(text)) | assembled_names(text):
                first_available.setdefault(leaf, k)
        previous_had_error = any(errors_here)
    return rows


def load_all(repo_root):
    frozen = json.loads((repo_root / FROZEN / "INPUTS_FROZEN.json").read_text())
    for entry in frozen["traces"]:
        info, requests = extract_episode(entry, repo_root)
        yield info, requests, entry["request"]


def support_judgments(repo_root):
    """Per-episode 'supported and complete' flags from the EARLIER studies (reported, not re-scored here).

    baseline : independent-judgments.json  -> strict_correct
    narration: INDEPENDENT_ANSWER_REVIEW.md table rows PASS / FAIL
    coverage : evaluation_stdout.json      -> supported_screen and procedure_satisfied
    """
    flags = {}
    previous = repo_root.parent / "rosa-research-previous-20261108" / "research" / "baseline_diagnostic"
    for item in json.loads((previous / "independent-judgments.json").read_text())["episodes"]:
        flags[item["episode"]] = bool(item["strict_correct"])
    review = (repo_root / "research/studies/action_narration_20261111/INDEPENDENT_ANSWER_REVIEW.md").read_text()
    for episode, verdict in re.findall(r"\|\s*`(\d\d-[\w]+-[ABC])`\s*\|\s*(PASS|FAIL)", review):
        flags[episode] = verdict == "PASS"
    evaluation = json.loads((repo_root / "research/_artifacts/gpt_coverage_investigation_20261111/evaluation_stdout.json").read_text())
    for item in evaluation:
        flags[item["episode"]] = bool(item["supported_screen"] and item["procedure_satisfied"])
    # The evaluator's first-start screen misses an ordering defect; the predeclared independent
    # adjudication (GPT coverage REPORT.md section 4) fails cells 04, 05 and 07 (stale check not first).
    for episode in ("04-openai-d1_recovery-B", "05-ollama-d1_recovery-B", "07-ollama-d1_recovery-V"):
        flags[episode] = False
    return flags


def main():
    repo_root, out_dir = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    manual = json.loads((Path(__file__).parent / "manual_labels.json").read_text())
    support = support_judgments(repo_root)
    all_rows = []
    for info, requests, request_text in load_all(repo_root):
        rows = analyse_episode(info, requests, request_text)
        floors = FLOORS[info["task"]]
        if info["episode"] not in support:
            raise SystemExit(f"no support judgment found for {info['episode']}")
        for row in rows:
            row["n_requests_episode"] = len(requests)
            row["floor_strict"], row["floor_alt"] = floors["strict"], floors["alt"]
            row["batching_prompt"] = BATCHING_PERMITTED[info["corpus"]]
            row["supported_complete"] = support[info["episode"]]
            row["trace_file"] = info["trace"]
            row["trace_sha256"] = info["sha256"]
            if row["request_index"] == 1:
                row["label"], row["label_source"], row["label_reason"] = "", "first request", "not labeled"
            else:
                override = manual.get(f"{info['episode']}#{row['request_index']}")
                if override:
                    row["label"], row["label_source"], row["label_reason"] = override["label"], "manual", override["reason"]
                else:
                    row["label"], row["label_source"], row["label_reason"] = row["auto_label"], "rule", row["auto_reason"]
            # The task itself plants a missing node; recovery from that planned miss is part of the floor.
            row["designed_recovery"] = (info["task"] == "d1_recovery" and row["label"] == "REC")
        all_rows.extend(rows)
    with open(out_dir / "labeled_requests.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"{len(all_rows)} request rows written")


if __name__ == "__main__":
    main()
