"""Offline sizing of four candidate mechanisms. Protocol: PROTOCOL.md (frozen by FREEZE.json before this file existed). CPU only; no model, no ROS.

Run from the repo root (no .pyc is written, so tracked compiled files stay untouched):
  PYTHONDONTWRITEBYTECODE=1 nice uv run python research/studies/idea_search_20261120/claude_lane/size_candidates.py

Flow: load P1 (288 loss-map episodes) and P2 (1,832 episodes of candidate_counts_20261118) -> parse each trace with the existing parser ->
compute, per episode, the raw measures of candidates 1-4 (section numbers below are the protocol's) -> aggregate per population, model and task -> results.json + detail jsonl files.
"""
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STUDIES = ROOT / "research/studies"
sys.path.insert(0, str(STUDIES / "candidate_counts_20261118"))
sys.path.insert(0, str(STUDIES / "name_fix_applied_20261117"))
import count_candidates as CC  # noqa: E402  (loader and parser of the candidate counts study)
import namefix_rule as rule  # noqa: E402  (name-rewrite v2, unchanged)

E, ag, v2 = CC.E, CC.ag, CC.v2
LOSSMAP_LOG = ROOT / "research/_artifacts/exam/lossmap/RESULTS_LOG_all.jsonl"
LABELS = STUDIES / "loss_map_20261120/labelled_lossmap.jsonl"
NODE_TOOLS = {"ros2_node_info", "ros2_param_list", "ros2_param_get"}
ENUMERATION_TOOLS = {"ros2_node_list"}
CAP_REQUESTS = 40
INLINE_CAP_CHARS = 2000
TOKEN_RE = re.compile(r"""[^\s"'{}\[\],:;()=]+""")
QUOTED_TOKEN = re.compile(r"'([^']+)'")
ROLE_WORD_NAME = re.compile(r"(?:[Ss]ervice|[Tt]opic)\s+(/[A-Za-z0-9_/]+)")
VALUE_RE = re.compile(r"value is:\s*(.*)", re.S)


def norm(name):
    return "/" + name.lstrip("/") if isinstance(name, str) else name


def seg(name):
    return name.rstrip("/").rsplit("/", 1)[-1]


def text_of(call):
    text = call["text"] if isinstance(call.get("text"), str) else ""
    return text.replace("\\n", "\n")


def is_read(call):
    return call["tool"] != "final_answer"


def ok_read(call):
    return call["ok"] and not call["harness_error"] and is_read(call)


def strings_of(value):
    return CC.strings_of(value)


def needed_entities(task):
    names = {s for s in strings_of(task["answer"]) if ag.ABSOLUTE_NAME.fullmatch(s)}
    for fact in task["support"]:
        if fact[0] == "text" and ag.ABSOLUTE_NAME.fullmatch(fact[1]):
            names.add(fact[1])
        elif fact[0] in ("param", "absent"):
            names.add(fact[1])
    return names


# ------------------------------------------------------------------ ledgers (protocol section 3)
def cumulative_ledgers(ep, with_task):
    """ledger[i] = names after requests 1..i (L-res: successful results only; L-task adds the task text). Same code as the name-fix ledger."""
    base = ag.allowed_names(ep["task_text"] if with_task else "", [])
    ledgers = [base]
    for request in ep["requests"]:
        outputs = [u["output"] for u in request.get("units", [])]
        ledgers.append(ledgers[-1] | ag.allowed_names("", outputs))
    return ledgers


# ------------------------------------------------------------------ candidate 1
def contiguous_name_in_results(ep, request_limit, name):
    for request in ep["requests"][:request_limit]:
        for unit in request.get("units", []):
            for part in ag.successful_text_parts(unit["output"]):
                if name in ag.NAME_IN_TEXT.findall(part.replace("\\n", "\n")):
                    return True
    return False


def candidate1_fires(ep, with_task):
    ledgers = cumulative_ledgers(ep, with_task)
    needed = needed_entities(ep["task_def"])
    absent_names = [f[1] for f in ep["task_def"]["support"] if f[0] == "absent"]
    fires = []
    for request in ep["requests"]:
        r = request["index"]
        for call in request["calls"]:
            entity = call["entity"]
            if not is_read(call) or call["ok"] or call["harness_error"] or not isinstance(entity, str):
                continue
            if not E.NOT_FOUND.search(call["text"] if isinstance(call["text"], str) else ""):
                continue
            if entity.startswith("/") or not ag.RELATIVE_NAME.fullmatch(entity):
                continue
            matches = ag.trailing_matches(entity, ledgers[r - 1])
            if len(matches) != 1:
                continue
            resolution = matches[0]
            # first later request with an ok call of the same tool on the resolution (saved-max, protocol 4.3)
            k = None
            for later in ep["requests"][r:]:
                if any(c["tool"] == call["tool"] and ok_read(c) and norm(c["entity"]) == resolution for c in later["calls"] if isinstance(c["entity"], str)):
                    k = later["index"]
                    break
            # what the model itself used later for the typed string (agree / differ, as in candidate_counts (a))
            later_used = None
            for later in ep["requests"][r:]:
                for c in later["calls"]:
                    if ok_read(c) and isinstance(c["entity"], str) and (norm(c["entity"]) == norm(entity) or norm(c["entity"]).endswith("/" + entity)):
                        later_used = norm(c["entity"])
                        break
                if later_used:
                    break
            is_absent_task = ep["task_def"]["template"] == "absent"
            if is_absent_task and any(a.endswith("/" + entity) or a == norm(entity) for a in absent_names):
                truth = "absent_made_present"
            elif resolution in needed:
                truth = "needed"
            elif any(n.endswith("/" + entity) for n in needed):
                truth = "wrong"
            else:
                truth = "not_needed"
            fires.append(dict(run_id=ep["run_id"], model=ep["model"], task=ep["task"], arm=ep["arm"], study=ep["study"], trace=ep["row"]["trace_path"], request=r, tool=call["tool"],
                              typed=entity, resolution=resolution, truth=truth, absent_task=is_absent_task, slash_only=(norm(entity) == resolution),
                              joined_only=not contiguous_name_in_results(ep, r - 1, resolution), later_request=k, saved_max=(k - r) if k else 0,
                              later_used=later_used, differ=(later_used is not None and later_used != resolution), supported=ep["supported"]))
    return fires


def candidate1_out(ep):
    answer = ep["answer"]
    if not isinstance(answer, dict) or not answer:
        return dict(applicable=False)
    outputs = [u["output"] for request in ep["requests"] for u in request.get("units", [])]
    allowed = ag.allowed_names(ep["task_text"], outputs)
    events = []
    rewritten = rule.rewrite_answer(answer, allowed, events)
    new = v2.score_task(ep["task_def"], rewritten, ep["rows"])
    old = v2.score_task(ep["task_def"], answer, ep["rows"])
    return dict(applicable=True, changed=rewritten != answer, rewrites=[e for e in events if e["kind"] == "rewrite"], old_supported=old["supported_complete"], new_supported=new["supported_complete"],
                old_exact=old["exact"], new_exact=new["exact"], new_issues=new["issues"][:4], answer_source=ep["answer_source_rederived"])


# ------------------------------------------------------------------ candidate 2
def task_gate(task_text):
    return bool(re.search(r"/[A-Za-z0-9_]", task_text) or QUOTED_TOKEN.search(task_text))


def candidate2(ep):
    task_names = {norm(n) for n in ag.names_in_text(ep["task_text"])}
    requests = ep["requests"]
    n = len(requests)
    # linked names: task-text names + names in successful results of earlier requests that are not enumerations
    linked_after = [set(task_names)]
    for request in requests:
        added = set()
        for c in request["calls"]:
            if ok_read(c) and c["tool"] not in ENUMERATION_TOOLS and not (c["tool"] == "ros2_param_list" and c["entity"] is None):
                added |= {norm(x) for x in ag.names_in_text(text_of(c))}
        linked_after.append(linked_after[-1] | added)
    probe_requests = {}
    for request in requests:
        i = request["index"]
        reads = [c for c in request["calls"] if is_read(c)]
        finals = [c for c in request["calls"] if not is_read(c)]
        if not reads or finals or not all(c["tool"] in NODE_TOOLS and isinstance(c["entity"], str) for c in reads):
            continue
        probes = [c for c in reads if norm(c["entity"]) not in linked_after[i - 1]]
        if probes and len(probes) == len(reads):
            probe_requests[i] = {norm(c["entity"]) for c in reads}
    scans, run, seen_nodes = [], [], set()

    def close_run():
        nonlocal run, seen_nodes
        if len(run) >= 2 and len(seen_nodes) >= 2:
            scans.append((list(run), set(seen_nodes)))
        run, seen_nodes = [], set()

    for request in requests:
        i = request["index"]
        if i in probe_requests:
            new_nodes = probe_requests[i] - seen_nodes
            if run and not new_nodes:
                close_run()
                run, seen_nodes = [i], set(probe_requests[i])
            else:
                run.append(i)
                seen_nodes |= probe_requests[i]
        else:
            close_run()
    close_run()
    gate = task_gate(ep["task_text"])
    task_tokens = set(ag.names_in_text(ep["task_text"])) | set(QUOTED_TOKEN.findall(ep["task_text"]))
    scan_rows = []
    for run_requests, nodes in scans:
        run_calls = [c for r in run_requests for c in requests[r - 1]["calls"]]
        matching = set()
        for c in run_calls:
            if ok_read(c) and isinstance(c["entity"], str) and any(t in text_of(c) for t in task_tokens):
                matching.add(norm(c["entity"]))
        scan_rows.append(dict(run_id=ep["run_id"], model=ep["model"], task=ep["task"], study=ep["study"], arm=ep["arm"], trace=ep["row"]["trace_path"], requests=run_requests, length=len(run_requests),
                              saved_max=len(run_requests) - 1, gate=gate, has_param_get=any(c["tool"] == "ros2_param_get" for c in run_calls), all_calls_ok=all(c["ok"] for c in run_calls), nodes=len(nodes),
                              names_chars=sum(len(m) for m in matching), est_added_tokens=round(sum(len(m) for m in matching) / 4, 1),
                              saved_request_input_tokens=sum(requests[r - 1]["input_tokens"] for r in run_requests[1:]), supported=ep["supported"],
                              in_scan_requests_saved=run_requests[1:]))
    # derived-name guesses (protocol 5)
    ledgers = cumulative_ledgers(ep, True)
    known_frozen, known_with_task = set(), set(norm(x) for x in ROLE_WORD_NAME.findall(ep["task_text"]))
    known_with_task |= set()
    guesses = []
    known_st_after = []
    st = set()
    for request in requests:
        known_st_after.append(set(st))
        for c in request["calls"]:
            if not ok_read(c):
                continue
            if c["tool"] in ("ros2_service_list", "ros2_topic_list"):
                st |= {norm(x) for x in ag.names_in_text(text_of(c))}
            if c["tool"] in ("ros2_service_info", "ros2_topic_info") and isinstance(c["entity"], str):
                st.add(norm(c["entity"]))
    for request in requests:
        i = request["index"]
        for c in request["calls"]:
            entity = c["entity"]
            if not is_read(c) or c["ok"] or c["harness_error"] or not isinstance(entity, str) or not E.entity_argument(c["entity_arg"] or ""):
                continue
            if not E.NOT_FOUND.search(c["text"] if isinstance(c["text"], str) else "") or c["entity_arg"] is None:
                continue
            if not re.sub(r"_name$", "", c["entity_arg"]).rstrip("s") == "node":
                continue
            if norm(entity) in ledgers[i - 1]:
                continue
            s = seg(entity)
            for variant, pool in (("frozen", known_st_after[i - 1]), ("with_task_roles", known_st_after[i - 1] | known_with_task)):
                if any(seg(S).startswith(s) and (len(seg(S)) == len(s) or seg(S)[len(s)] == "_") for S in pool):
                    guesses.append(dict(run_id=ep["run_id"], model=ep["model"], task=ep["task"], study=ep["study"], arm=ep["arm"], trace=ep["row"]["trace_path"], request=i, typed=entity, variant=variant,
                                        supported=ep["supported"]))
    return scan_rows, guesses


# ------------------------------------------------------------------ candidate 3 (raw part; values estimated after the population medians are known)
def param_value_text(output_text):
    match = VALUE_RE.search(output_text.replace("\\n", "\n"))
    return match.group(1).strip() if match else None


def candidate3_raw(ep):
    requests = ep["requests"]
    values = {}      # (node, param) -> inline text from this episode's successful reads
    for request in requests:
        for c in request["calls"]:
            if c["tool"] == "ros2_param_get" and ok_read(c) and isinstance(c["entity"], str):
                param = c["args"].get("param_name")
                text = param_value_text(c["text"] if isinstance(c["text"], str) else "")
                if param and text is not None:
                    values.setdefault((norm(c["entity"]), param), text)
    lists = []
    task_text = ep["task_text"]
    for request in requests:
        for unit in request.get("units", []):
            if unit["tool"] != "ros2_param_list" or unit["harness_error"] or not isinstance(unit["output"], dict) or "error" in unit["output"]:
                continue
            listed = {norm(k): [p.strip() for p in v] for k, v in unit["output"].items() if isinstance(v, list)}
            if listed:
                lists.append(dict(request=request["index"], listed=listed, original_chars=len(json.dumps(unit["output"]))))
    # list -> later get on the same node, and whether the parameter name was known before the list
    for item in lists:
        item["followed_by_get"] = False
        item["first_get_name_known_before"] = None
        known_text = task_text + "\n" + "\n".join(text_of(c) for r in requests[:item["request"] - 1] for c in r["calls"] if ok_read(c))
        for request in requests[item["request"]:]:
            for c in request["calls"]:
                if c["tool"] == "ros2_param_get" and ok_read(c) and isinstance(c["entity"], str) and norm(c["entity"]) in item["listed"]:
                    param = c["args"].get("param_name", "")
                    item["followed_by_get"] = True
                    item["first_get_name_known_before"] = bool(re.search(r"(?<![A-Za-z0-9_])" + re.escape(param) + r"(?![A-Za-z0-9_])", known_text))
                    break
            if item["followed_by_get"]:
                break
    gets = []        # per request: list of (node, param, ok) for all-param_get requests
    read_ok = set()
    for request in requests:
        reads = [c for c in request["calls"] if is_read(c)]
        finals = [c for c in request["calls"] if not is_read(c)]
        entry = dict(request=request["index"], pure=False, items=[])
        if reads and not finals and all(c["tool"] == "ros2_param_get" and c["ok"] and not c["harness_error"] and isinstance(c["entity"], str) for c in reads):
            entry["pure"] = True
            seen_here = set()
            for c in reads:
                key = (norm(c["entity"]), c["args"].get("param_name"))
                entry["items"].append(dict(key=key, first=(key not in read_ok and key not in seen_here)))
                seen_here.add(key)
        for c in reads:
            if c["tool"] == "ros2_param_get" and c["ok"] and not c["harness_error"] and isinstance(c["entity"], str):
                read_ok.add((norm(c["entity"]), c["args"].get("param_name")))
        gets.append(entry)
    return dict(values=values, lists=lists, gets=gets)


def param_get_value_lengths(ep):
    for request in ep["requests"]:
        for c in request["calls"]:
            if c["tool"] == "ros2_param_get" and ok_read(c):
                text = param_value_text(c["text"] if isinstance(c["text"], str) else "")
                if text is not None:
                    yield c["args"].get("param_name"), text


def candidate3_finalize(ep, raw, param_median, global_median):
    requests = ep["requests"]
    n = len(requests)
    eligible = []
    list_rows = []
    for item in raw["lists"]:
        new_dict, estimated = {}, 0
        for node, params in item["listed"].items():
            entries = []
            for p in params:
                if (node, p) in raw["values"]:
                    value = raw["values"][(node, p)]
                else:
                    estimated += 1
                    value = "x" * int(param_median.get(p, global_median))
                entries.append(f"{p}: {value}")
            new_dict[node] = entries
        new_chars = len(json.dumps(new_dict))
        under_cap = new_chars <= INLINE_CAP_CHARS
        added = max(0, new_chars - item["original_chars"])
        row = dict(request=item["request"], chars_with_values=new_chars, original_chars=item["original_chars"], under_cap=under_cap, added_chars=added if under_cap else 0, estimated_params=estimated, params=sum(len(v) for v in item["listed"].values()),
                   followed_by_get=item["followed_by_get"], name_known_before=item["first_get_name_known_before"])
        list_rows.append(row)
        if under_cap:
            eligible.append((item, added))
    saved_requests, flagged = [], []
    for entry in raw["gets"]:
        if not entry["pure"]:
            continue
        covered_all = True
        for it in entry["items"]:
            node, param = it["key"]
            covered = it["first"] and any(item["request"] < entry["request"] and node in item["listed"] and param in item["listed"][node] for item, _a in eligible)
            if not covered:
                covered_all = False
                break
        if covered_all and entry["items"]:
            saved_requests.append(entry["request"])
            if ep["task"].startswith("e1h_chg"):
                flagged.append(entry["request"])
    added_tokens_carried = sum(a / 4 * (n - item["request"]) for item, a in eligible)
    saved_tokens = sum(requests[r - 1]["input_tokens"] for r in saved_requests)
    return dict(list_rows=list_rows, saved_requests=saved_requests, flagged_chg=flagged, added_tokens_carried=round(added_tokens_carried, 1), saved_tokens=saved_tokens,
                added_tokens_direct=round(sum(a for _i, a in eligible) / 4, 1))


# ------------------------------------------------------------------ candidate 4
def tokens_of(text):
    return set(TOKEN_RE.findall(text.replace("\\n", "\n")))


def novelty(ep):
    seen = tokens_of(ep["task_text"])
    flags = []
    for request in ep["requests"]:
        novel = False
        for c in request["calls"]:
            if ok_read(c) and tokens_of(c["text"] if isinstance(c["text"], str) else "") - seen:
                novel = True
        flags.append(novel)
        for c in request["calls"]:
            if is_read(c) and not c["harness_error"]:
                seen |= tokens_of(c["text"] if isinstance(c["text"], str) else "")
    return flags


def support_missing_at(ep, request_index):
    events = ep["events"]
    ends = [i for i, e in enumerate(events) if e["kind"] == "model_end"]
    start_after = ends[request_index - 1]
    cut = next((i for i in range(start_after, len(events)) if events[i]["kind"] == "model_start"), len(events))
    rows = E.score_round1.expanded_rows(events[:cut])
    return v2.support_missing(ep["task_def"], rows)


def candidate4(ep, ks=(4, 5, 6)):
    flags = novelty(ep)
    n = len(ep["requests"])
    capped = ep["ending"] == "none" and (n >= CAP_REQUESTS or "iteration" in ((ep["end_text"] or "") + " ".join(str(a) for a in ep["row"].get("aborts", []))).lower())
    out = {}
    for k in ks:
        run, trigger = 0, None
        for i, novel in enumerate(flags, start=1):
            run = 0 if novel else run + 1
            if run >= k and i < n:
                trigger = i
                break
        if trigger is None:
            out[k] = None
            continue
        missing = support_missing_at(ep, trigger)
        unsupported_or_capped = (not ep["supported"]) or capped
        out[k] = dict(trigger=trigger, n=n, missing=missing, facts_present=not missing, supported=ep["supported"], capped=capped,
                      saved_max=max(0, n - (trigger + 1)) if unsupported_or_capped else 0, saved_loose=max(0, n - trigger) if unsupported_or_capped else 0,
                      saved_tokens=sum(r["input_tokens"] for r in ep["requests"][trigger + 1:]) if unsupported_or_capped else 0,
                      saved_requests=list(range(trigger + 2, n + 1)) if unsupported_or_capped else [],
                      harm=(ep["supported"] and bool(missing)), chg=ep["task"].startswith("e1h_chg"))
    return out, capped


# ------------------------------------------------------------------ driver
def load_p1(tasks):
    rows = [json.loads(line) for line in LOSSMAP_LOG.read_text().splitlines() if line.strip()]
    return [("lossmap", row) for row in rows]


def process(population_name, population, tasks):
    result = dict(episodes=[], fires={"res": [], "task": []}, out=[], scans=[], guesses=[], c4={}, c3raw={}, errors=[], value_lengths=defaultdict(list))
    eps = []
    for study, row in population:
        try:
            ep = CC.parse_episode(study, row, tasks)
        except Exception as error:  # reported, never hidden
            result["errors"].append(dict(run_id=row["run_id"], error=f"{type(error).__name__}: {error}"))
            continue
        eps.append(ep)
    # pass 1: raw measures and parameter value lengths
    c3 = {}
    for ep in eps:
        result["episodes"].append(dict(run_id=ep["run_id"], model=ep["model"], task=ep["task"], study=ep["study"], arm=ep["arm"], seed=ep["seed"], requests=len(ep["requests"]), supported=bool(ep["supported"]),
                                       input_tokens=sum(r["input_tokens"] for r in ep["requests"]), trace=ep["row"]["trace_path"], logged_supported=ep["row"].get("supported_complete")))
        result["fires"]["res"].extend(candidate1_fires(ep, False))
        result["fires"]["task"].extend(candidate1_fires(ep, True))
        out = candidate1_out(ep)
        out.update(run_id=ep["run_id"], model=ep["model"], task=ep["task"], study=ep["study"], arm=ep["arm"], trace=ep["row"]["trace_path"])
        result["out"].append(out)
        scans, guesses = candidate2(ep)
        result["scans"].extend(scans)
        result["guesses"].extend(guesses)
        c3[ep["run_id"] + "|" + ep["study"] + "|" + ep["arm"]] = (ep, candidate3_raw(ep))
        for param, text in param_get_value_lengths(ep):
            result["value_lengths"][param].append(len(text))
        c4, capped = candidate4(ep)
        result["c4"][ep["run_id"] + "|" + ep["study"] + "|" + ep["arm"]] = dict(per_k=c4, capped=capped)
    all_lengths = [x for v in result["value_lengths"].values() for x in v]
    global_median = statistics.median(all_lengths) if all_lengths else 5
    param_median = {p: statistics.median(v) for p, v in result["value_lengths"].items()}
    result["c3"] = {}
    for key, (ep, raw) in c3.items():
        result["c3"][key] = candidate3_finalize(ep, raw, param_median, global_median)
    result["c3_value_medians"] = dict(global_median=global_median, per_param={p: m for p, m in sorted(param_median.items())})
    result["value_lengths"] = {p: len(v) for p, v in result["value_lengths"].items()}
    return result


def main():
    tasks = CC.all_tasks()
    populations = {"P1": load_p1(tasks), "P2": CC.load_population()}
    for name, population in populations.items():
        print(name, "episodes selected", len(population), flush=True)
        result = process(name, population, tasks)
        (HERE / f"raw_{name}.json").write_text(json.dumps(result, default=str))
        print(name, "episodes parsed", len(result["episodes"]), "errors", len(result["errors"]), flush=True)


if __name__ == "__main__":
    main()
