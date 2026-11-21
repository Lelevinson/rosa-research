"""Loss-map classifier (protocol: PROTOCOL.md, section 3). Offline: reads saved traces and result rows only; no model, no ROS, no GPU.

  uv run python research/studies/loss_map_20261120/classify.py dev        # development set: FULL arms of part A and the replication (seeds 1-4); used to debug the rules
  uv run python research/studies/loss_map_20261120/classify.py lossmap    # the measurement (seeds 5-8); run only after FREEZE_ANALYSIS.json holds this file's hash

Every request of an episode gets ONE primary type (precedence order below) from its tool calls and results; requests above the floor and unsupported episodes are then attributed to types.

Request types, in precedence order (definitions: PROTOCOL.md section 3):
  format       every call was rejected by the harness (invalid arguments, tool not offered, finish-tool format, answer not accepted), or the request made no tool call at all
  repeat       every call repeats an earlier SUCCESSFUL call (same tool, entity and other arguments); `loop` (a flag, not a type) = a request containing a call whose signature (tool, entity, arguments; successful or failed) occurs for the third time or more in the episode
  name_guess   a call names an entity that is not in the episode's name ledger (task text and earlier results) and the call failed
  name_recovery the request right after a name_guess request that is neither format, repeat nor a new guess
  serial_batchable  a non-final, non-first request whose calls all succeeded and are INDEPENDENT of the previous request, so they could have been sent in the previous request. A call is
               independent if it has no entity argument (a list tool), or its entity is named in the task text, or the entity was already in the name ledger before the previous request
               AND the previous request's results do not mention it (if they mention it, the model probably picked it because of that result: a necessary serial step)
  productive   everything else (including the final answer): the request looks necessary
Above the floor: excess = requests - task floor. It is attributed to waste types in precedence order (format, repeat, name_guess, name_recovery, serial_batchable); what the waste requests do not
explain is `unexplained_longer_route` (the model took more steps than the floor without a waste type). If the waste requests outnumber the excess, the rest is `waste_within_floor`.
Failure types of an unsupported episode, in order: no_answer_<cap|timeout|backend|other>; wrong_conclusion_facts_present (answer exists, scorer's support_missing is empty);
facts_missing_<loop|name_guess|format|stopped_early|other> (answer exists, a support fact was never read).
"""
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STUDIES = ROOT / "research/studies"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIES / "offline_replay_20261116"))
import episodes as E  # noqa: E402
import answer_gate as ag  # noqa: E402

WASTE = ["format", "repeat", "name_guess", "name_recovery", "serial_batchable"]   # precedence order
TYPES = WASTE + ["productive"]
LONG_RESULT_CHARS = 8000
MAX_ITERATIONS = 40   # the episode iteration cap of the thinking runner
WRITE_TOOLS = {"ros2_service_call", "ros2_param_set"}


def all_tasks():
    tasks = E.load_tasks()
    tasks.update({t["id"]: t for t in json.loads((STUDIES / "name_fix_applied_20261117/namefix_tasks.json").read_text())})
    return tasks


def signature(call):
    return (call["tool"], str(call["entity"]), json.dumps(call["args"], sort_keys=True, default=str))


def known(name, ledger):
    return name in ledger or (isinstance(name, str) and (("/" + name) in ledger or name.lstrip("/") in {n.lstrip("/") for n in ledger}))


def is_rejected(call):
    """A call the harness rejected. The accepted finish call is not: the parser's HARNESS_TEXT also matches the success text "Answer recorded", so the final answer is judged by its own text."""
    if call["tool"] == "final_answer":
        text = call["text"] if isinstance(call.get("text"), str) else ""
        return text.startswith(("Answer not accepted", "final_answer needs", "Invalid arguments"))
    return bool(call["harness_error"])


def mentioned_in_results(request):
    names = set()
    for c in request["calls"]:
        if c["tool"] != "final_answer" and isinstance(c.get("text"), str):
            names |= set(ag.names_in_text(c["text"]))
    return names


def independent(call, task_names, before_previous, previous_mentions):
    if call["entity"] is None:
        return True
    if known(call["entity"], task_names):
        return True
    return known(call["entity"], before_previous) and not known(call["entity"], previous_mentions)


def label_requests(ep):
    """List of dicts, one per request: type, flags, and the facts the classifier used."""
    events, _final = E.ledger_events(ep)
    added = defaultdict(set)                      # request index -> names that its calls added to the ledger
    for index, _call, new in events:
        added[index] |= new
    ledger_after = {0: set(ag.names_in_text(ep["task_text"]))}
    for r in ep["requests"]:
        ledger_after[r["index"]] = ledger_after[r["index"] - 1] | added[r["index"]]
    task_names = set(ag.names_in_text(ep["task_text"]))
    succeeded, labels, previous_guess = set(), [], False
    for r in ep["requests"]:
        i = r["index"]
        calls = r["calls"]
        reads = [c for c in calls if c["tool"] != "final_answer"]
        finals = [c for c in calls if c["tool"] == "final_answer"]
        before, before_previous = ledger_after[i - 1], ledger_after[max(i - 2, 0)]
        previous_mentions = mentioned_in_results(ep["requests"][i - 2]) if i > 1 else set()
        info = dict(index=i, calls=len(calls), tools=[c["tool"] for c in calls], flags=[])
        rejected = [c for c in calls if is_rejected(c)]
        guesses = [c for c in reads if c["entity"] is not None and not known(c["entity"], before) and not c["ok"]]
        lucky = [c for c in reads if c["entity"] is not None and not known(c["entity"], before) and c["ok"]]
        repeats = [c for c in reads if c["ok"] is not None and signature(c) in succeeded]
        if not calls or (rejected and len(rejected) == len(calls)):
            kind = "format"
        elif reads and len(repeats) == len(reads) and not finals:
            kind = "repeat"
        elif guesses:
            kind = "name_guess"
        elif previous_guess:
            kind = "name_recovery"
        elif reads and not finals and i > 1 and all(c["ok"] and not c["harness_error"] for c in reads) and all(independent(c, task_names, before_previous, previous_mentions) for c in reads):
            kind = "serial_batchable"
        else:
            kind = "productive"
        if lucky:
            info["flags"].append("lucky_guess")
        if any(c["tool"] in WRITE_TOOLS for c in calls):
            info["flags"].append("write_attempt")
        if any(len(c["text"]) >= LONG_RESULT_CHARS for c in calls if isinstance(c.get("text"), str)):
            info["flags"].append("long_result")
        if reads and [c for c in reads if not c["ok"] and signature(c) in {s for s, _ in info.get("failed_before", [])}]:
            info["flags"].append("repeat_of_failed")
        info["type"] = kind
        info["new_names"] = len(added[i])
        labels.append(info)
        previous_guess = kind == "name_guess"
        for c in reads:
            if c["ok"] and not c["harness_error"]:
                succeeded.add(signature(c))
    seen = Counter()                              # a loop: a call signature (successful or failed) that occurs for the third time or more; the request is flagged, its primary type stays
    for r, info in zip(ep["requests"], labels):
        for c in r["calls"]:
            if c["tool"] != "final_answer":
                seen[signature(c)] += 1
                if seen[signature(c)] >= 3 and "loop" not in info["flags"]:
                    info["flags"].append("loop")
    return labels


def attribute_excess(labels, floor):
    """Split requests - floor over the waste types in precedence order. Returns (dict type -> requests, unexplained, waste_within_floor)."""
    excess = max(0, len(labels) - floor)
    counts = Counter(l["type"] for l in labels if l["type"] in WASTE)
    attributed, left = {}, excess
    for kind in WASTE:
        take = min(counts.get(kind, 0), left)
        attributed[kind] = take
        left -= take
    waste_total = sum(counts.values())
    return attributed, left, max(0, waste_total - excess), excess


def failure_type(row, labels, floor):
    if row.get("supported_complete"):
        return None
    aborts = " ".join(str(a) for a in row.get("aborts", []))
    answer_missing = row.get("answer") in (None, {}, "")
    if answer_missing or aborts.strip():
        if "timeout" in aborts:
            return "no_answer_timeout"
        if "iteration limit" in aborts or len(labels) >= MAX_ITERATIONS:   # older rows do not carry the cap in `aborts`; 40 requests is the cap
            return "no_answer_cap"
        if "Error" in aborts or "error" in aborts or "backend" in aborts:
            return "no_answer_backend"
        if labels and labels[-1]["type"] == "format":
            return "no_answer_format"                                       # the last request was rejected by the harness and nothing followed
        return "no_answer_other"
    if not row.get("support_missing"):
        return "wrong_conclusion_facts_present"
    kinds = Counter(l["type"] for l in labels)
    if any("loop" in l["flags"] for l in labels):
        return "facts_missing_loop"
    if kinds["name_guess"]:
        return "facts_missing_name_guess"
    if kinds["format"]:
        return "facts_missing_format"
    if len(labels) < floor:
        return "facts_missing_stopped_early"
    return "facts_missing_other"


def conclusion_subtype(issues):
    """Sub-split of wrong_conclusion_facts_present from the scorer's issue strings ("/key: 'given' != 'expected'", "/key: missing", "/key: extra field"). A heuristic, checked by hand on development traces:
    name_form = the given value is the expected name with the slash, namespace or a letter changed or cut (short name, missing leading slash, typo); wrong_entity = another full name;
    answer_shape = a missing or extra field; wrong_value = anything else (numbers, booleans, types)."""
    kinds = set()
    for issue in issues or []:
        match = re.match(r"^(\S+): '(.*)' != '(.*)'$", issue)
        if match:
            given, expected = match.group(2), match.group(3)
            a, b = given.strip("/"), expected.strip("/")
            if given.startswith("/") is False and "/" not in given and expected.startswith("/"):
                kinds.add("name_form")           # a short name such as 'bobbin'
            elif a == b or a.endswith(b) or b.endswith(a) or abs(len(a) - len(b)) <= 2 and sum(x != y for x, y in zip(a, b)) <= 2:
                kinds.add("name_form")
            elif expected.startswith("/") and given.startswith("/"):
                kinds.add("wrong_entity")
            else:
                kinds.add("wrong_value")
        elif issue.endswith("missing") or issue.endswith("extra field"):
            kinds.add("answer_shape")
        else:
            kinds.add("wrong_value")
    return "+".join(sorted(kinds)) or "unspecified"


def analyse(rows):
    tasks = all_tasks()
    out = []
    for row in rows:
        ep = E.parse("loss", dict(row, run_id=row["run_id"], arm=row["arm"]), tasks)
        floor = tasks[row["task"]]["floor"]
        labels = label_requests(ep)
        attributed, unexplained, within_floor, excess = attribute_excess(labels, floor)
        failure = failure_type(row, labels, floor)
        out.append(dict(run_id=row["run_id"], model=row["model"], task=row["task"], env=row["env"], seed=row["seed"], supported=bool(row["supported_complete"]), exact=row.get("exact"), requests=len(labels),
                        floor=floor, excess=excess, attributed=attributed, unexplained_longer_route=unexplained, waste_within_floor=within_floor, below_floor=len(labels) < floor,
                        failure=failure, support_missing=row.get("support_missing"), issues=row.get("issues"), conclusion_subtype=conclusion_subtype(row.get("issues")) if failure == "wrong_conclusion_facts_present" else None, aborts=row.get("aborts"), trace_path=row["trace_path"],
                        request_types=[l["type"] for l in labels], flags={f: sum(f in l["flags"] for l in labels) for f in ("lucky_guess", "write_attempt", "long_result", "loop")},
                        batched_requests=sum(l["calls"] >= 2 for l in labels), input_tokens=row.get("input_tokens"), output_tokens=row.get("output_tokens"), wall_seconds=row.get("wall_seconds")))
    return out


def load_rows(source):
    if source == "dev":
        rows = []
        for path, phase_filter in ((ROOT / "research/_artifacts/exam/thinking_replA2/RESULTS_LOG_all.jsonl", None), (STUDIES / "thinking_escalation_20261119/RESULTS_LOG.jsonl", "partA")):
            for line in path.read_text().splitlines():
                r = json.loads(line)
                if r["arm"] == "FULL" and r.get("trace_path") and (phase_filter is None or r.get("phase") == phase_filter or True):
                    rows.append(r)
        seen, unique = set(), []
        for r in rows:
            if r["trace_path"] not in seen:
                seen.add(r["trace_path"])
                unique.append(r)
        return unique
    return [json.loads(l) for l in (ROOT / "research/_artifacts/exam/lossmap/RESULTS_LOG_all.jsonl").read_text().splitlines() if l.strip()]


def summarize(episodes):
    """Aggregates per model and per task: counts and shares; examples (up to 3 trace paths) per type and model."""
    by_model = defaultdict(list)
    for e in episodes:
        by_model[e["model"]].append(e)
    result = dict(episodes=len(episodes), by_model={}, by_task={}, examples=defaultdict(list), failures=Counter(), failure_examples=defaultdict(list))
    groups = dict(by_model)
    groups["ALL"] = episodes

    def block(eps):
        n = len(eps)
        excess = sum(e["excess"] for e in eps)
        attributed = Counter()
        for e in eps:
            attributed.update(e["attributed"])
        return dict(episodes=n, supported=sum(e["supported"] for e in eps), requests=sum(e["requests"] for e in eps), floor_requests=sum(e["floor"] for e in eps), excess=excess,
                    attributed=dict(attributed), unexplained=sum(e["unexplained_longer_route"] for e in eps), waste_within_floor=sum(e["waste_within_floor"] for e in eps),
                    below_floor=sum(e["below_floor"] for e in eps), loops=sum(e["flags"]["loop"] > 0 for e in eps), lucky_guesses=sum(e["flags"]["lucky_guess"] for e in eps),
                    batched_requests=sum(e["batched_requests"] for e in eps), failures=dict(Counter(e["failure"] for e in eps if e["failure"])),
                    request_types=dict(Counter(t for e in eps for t in e["request_types"])), input_tokens=sum(e["input_tokens"] or 0 for e in eps), output_tokens=sum(e["output_tokens"] or 0 for e in eps))
    result["by_model"] = {m: block(eps) for m, eps in groups.items()}
    tasks = defaultdict(list)
    for e in episodes:
        tasks[e["task"]].append(e)
    result["by_task"] = {t: block(eps) for t, eps in sorted(tasks.items())}
    cells = defaultdict(list)
    for e in episodes:
        cells[(e["model"], e["task"])].append(e)
    result["by_model_task"] = {f"{m}|{t}": block(eps) for (m, t), eps in sorted(cells.items())}
    for e in episodes:
        for kind in WASTE:
            if e["attributed"].get(kind) and len(result["examples"][f"{e['model']}|{kind}"]) < 3:
                result["examples"][f"{e['model']}|{kind}"].append(e["trace_path"])
        if e["failure"] and len(result["failure_examples"][f"{e['model']}|{e['failure']}"]) < 3:
            result["failure_examples"][f"{e['model']}|{e['failure']}"].append(e["trace_path"])
    return result


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "n/a"


def write_tables(source, episodes, summary):
    """TABLES_<source>.md: aggregates only (counts and shares), with example trace paths. The report is written from these by hand."""
    lines = [f"# Loss-map tables ({source}; {len(episodes)} episodes). Generated by classify.py; descriptive counts, no test.", ""]

    def table(title, header, body):
        lines.extend([f"## {title}", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(str(x) for x in row) + " |" for row in body] + [""])

    models = [m for m in summary["by_model"] if m != "ALL"] + ["ALL"]
    body = []
    for m in models:
        b = summary["by_model"][m]
        a = b["attributed"]
        body.append([m, b["episodes"], f"{b['supported']} ({pct(b['supported'], b['episodes'])})", b["requests"], b["floor_requests"], b["excess"], pct(b["excess"], b["requests"]),
                     *[f"{a.get(k, 0)} ({pct(a.get(k, 0), b['excess'])})" for k in WASTE], f"{b['unexplained']} ({pct(b['unexplained'], b['excess'])})", b["waste_within_floor"]])
    table("1. Requests above the floor, attributed to types (share of the model's excess requests; excess = requests - floor per episode)",
          ["model", "episodes", "supported", "requests", "floor requests", "excess requests", "excess / requests", *WASTE, "unexplained longer route", "waste requests inside the floor"], body)
    body = []
    for m in models:
        b = summary["by_model"][m]
        t = b["request_types"]
        body.append([m, b["requests"], *[f"{t.get(k, 0)} ({pct(t.get(k, 0), b['requests'])})" for k in TYPES]])
    table("2. All requests by primary type (not only those above the floor)", ["model", "requests", *TYPES], body)
    kinds = sorted({k for b in summary["by_model"].values() for k in b["failures"]})
    body = [[m, summary["by_model"][m]["episodes"] - summary["by_model"][m]["supported"], *[summary["by_model"][m]["failures"].get(k, 0) for k in kinds]] for m in models]
    table("3. Unsupported episodes by failure type", ["model", "unsupported", *kinds], body)
    sub = Counter((e["model"], e["conclusion_subtype"]) for e in episodes if e["failure"] == "wrong_conclusion_facts_present")
    subtypes = sorted({k for _m, k in sub})
    table("3b. wrong_conclusion_facts_present by issue subtype (heuristic on the scorer's issue strings)", ["model", *subtypes], [[m, *[sub.get((m, k), 0) for k in subtypes]] for m in models if m != "ALL"])
    body = []
    for t, b in summary["by_task"].items():
        a = b["attributed"]
        body.append([t, b["episodes"], f"{b['supported']} ({pct(b['supported'], b['episodes'])})", b["requests"], b["floor_requests"], b["excess"], *[a.get(k, 0) for k in WASTE], b["unexplained"], sum(b["failures"].values())])
    table("4. Per task", ["task", "episodes", "supported", "requests", "floor requests", "excess", *WASTE, "unexplained", "unsupported"], body)
    body = []
    for key, b in summary["by_model_task"].items():
        if b["excess"] >= 6 or sum(b["failures"].values()) >= 3:
            a = b["attributed"]
            body.append([key, b["episodes"], b["supported"], b["requests"], b["excess"], *[a.get(k, 0) for k in WASTE], b["unexplained"], sum(b["failures"].values())])
    table("4b. Model x task cells with at least 6 excess requests or 3 unsupported episodes", ["model|task", "episodes", "supported", "requests", "excess", *WASTE, "unexplained", "unsupported"], body)
    n = len(episodes)
    flags = Counter()
    for e in episodes:
        for f, v in e["flags"].items():
            flags[(e["model"], f)] += v
    body = []
    for m in models:
        eps = episodes if m == "ALL" else [e for e in episodes if e["model"] == m]
        body.append([m, len(eps), sum(e["batched_requests"] for e in eps), sum(e["requests"] for e in eps), sum(e["flags"]["loop"] > 0 for e in eps), sum(e["flags"]["lucky_guess"] for e in eps),
                     sum(e["flags"]["write_attempt"] for e in eps), sum(e["flags"]["long_result"] for e in eps), sum(e["below_floor"] for e in eps)])
    table("5. Detector counts (open search)", ["model", "episodes", "requests with 2+ calls (batching used)", "requests", "episodes with a loop", "lucky guesses (unlisted name worked)", "write-tool attempts (blocked)",
                                              "requests with a >= 8,000-character result", "episodes below the floor"], body)
    lines.extend(["## 6. Example trace paths (up to 3 per model and type; repo-relative)", ""])
    for key, paths in sorted(summary["examples"].items()):
        lines.append(f"- {key}: " + "; ".join(paths))
    lines.extend(["", "## 7. Example trace paths of unsupported episodes (up to 3 per model and failure type)", ""])
    for key, paths in sorted(summary["failure_examples"].items()):
        lines.append(f"- {key}: " + "; ".join(paths))
    (HERE / f"TABLES_{source}.md").write_text("\n".join(lines) + "\n")


def main():
    source = sys.argv[1]
    assert source in ("dev", "lossmap")
    if source == "lossmap":
        freeze = json.loads((HERE / "FREEZE_ANALYSIS.json").read_text())
        import hashlib
        assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == freeze["classify_py_sha256"], "classify.py changed after the analysis freeze: report and re-run as a labelled revision, do not edit silently"
    episodes = analyse(load_rows(source))
    summary = summarize(episodes)
    (HERE / f"labelled_{source}.jsonl").write_text("\n".join(json.dumps(e) for e in episodes) + "\n")
    (HERE / f"results_{source}.json").write_text(json.dumps(summary, indent=1, default=list))
    write_tables(source, episodes, summary)
    allm = summary["by_model"]["ALL"]
    print(json.dumps({k: allm[k] for k in ("episodes", "supported", "requests", "floor_requests", "excess", "attributed", "unexplained", "waste_within_floor", "below_floor", "loops", "failures", "request_types")}, indent=1))


if __name__ == "__main__":
    main()
