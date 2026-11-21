"""Counts of PROTOCOL.md (hash in PROTOCOL.sha256): write-tool attempts (item 1), tail cost (item 2), repeat loops (item 3). Offline, CPU only.
  uv run python research/studies/write_tail_repeat_20261118/count_wtr.py
Reuses candidate_counts_20261118/count_candidates.py (population and parser) unchanged."""
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "candidate_counts_20261118"))
import count_candidates as C  # noqa: E402

assert hashlib.sha256((HERE / "PROTOCOL.md").read_bytes()).hexdigest() == (HERE / "PROTOCOL.sha256").read_text().split()[0], "protocol changed after freezing"
WRITE = C.WRITE_TOOLS
STATE_CHANGING = ("/set_parameters", "/set_parameters_atomically")
READ_ONLY = ("/describe_parameters", "/get_parameter_types", "/get_parameters", "/list_parameters")
VALIDATION = re.compile(r"^\d+ validation errors? for ")
GUARD = "Observation-only study: command rejected"


def env_of(task):
    return "e1h" if task.startswith("e1h_") else "namefix" if task.startswith("nf_") else "stage3"


def norm(name):
    return "/" + str(name).strip().rstrip(":").lstrip("/")


def percentile90(values):
    s = sorted(values)
    return s[math.ceil(0.9 * len(s)) - 1]


def summary(values):
    if not values:
        return None
    return dict(n=len(values), median=statistics.median(values), p90=percentile90(values), max=max(values), mean=round(statistics.mean(values), 1), total=sum(values))


def main():
    tasks = C.all_tasks()
    population = C.load_population()
    episodes = []
    for study, row in population:
        ep = C.parse_episode(study, row, tasks)
        ep["env_name"] = env_of(row["task"])
        episodes.append(ep)
    print("episodes", len(episodes), flush=True)

    # ---- fixture knowledge per environment (names appearing in successful results)
    nodes, services, params = defaultdict(set), defaultdict(set), defaultdict(set)
    for ep in episodes:
        env = ep["env_name"]
        for request in ep["requests"]:
            for unit in request.get("units", []):
                if not unit["ok"] or unit["harness_error"] or not isinstance(unit["output"], dict):
                    continue
                if unit["tool"] == "ros2_node_list":
                    nodes[env].update(norm(n) for n in unit["output"].get("nodes", []))
                elif unit["tool"] == "ros2_service_list":
                    services[env].update(norm(n) for n in unit["output"].get("services", []))
                elif unit["tool"] == "ros2_param_list":
                    for key, listed in unit["output"].items():
                        if isinstance(listed, list):
                            params[env].update((norm(key), str(p).strip()) for p in listed)

    # ---- item 1
    attempts, method_rows = [], defaultdict(lambda: dict(episodes=0, attempts=0, not_offered_events=0))
    arm_episodes = Counter()
    for ep in episodes:
        study, arm, model = ep["study"], ep["arm"], ep["model"]
        arm_episodes[(study, arm)] += 1
        tool_errors = [e for e in ep["events"] if e["kind"] == "tool_error"]
        has_validation_error = any(VALIDATION.match(str(e.get("error", ""))) for e in tool_errors)
        n_units = 0
        for request in ep["requests"]:
            for unit in request.get("units", []):
                if unit["tool"] not in WRITE:
                    continue
                n_units += 1
                out = unit["output"]
                text = out if isinstance(out, str) else json.dumps(out) if out is not None else ""
                if out is None and has_validation_error:
                    status = "no_result_validation"
                elif isinstance(out, str) and VALIDATION.match(out):
                    status = "validation_text"
                elif GUARD in text:
                    status = "guard_rejected"
                elif isinstance(out, str) and "is not available" in out:
                    status = "not_available"
                else:
                    status = "executed"
                args = unit["args"] or {}
                env = ep["env_name"]
                if unit["tool"] == "ros2_param_set":
                    node, param = norm(args.get("node_name", "")), str(args.get("param_name", ""))
                    would = ("existing node, existing parameter" if (node, param) in params[env] else "existing node, parameter not seen" if node in nodes[env] else "no such node")
                else:
                    service = norm(args.get("service_name", ""))
                    would = ("no such service" if service not in services[env] else "existing state-changing service" if service.endswith(STATE_CHANGING)
                             else "existing read-only service" if service.endswith(READ_ONLY) else "existing other service")
                attempts.append(dict(study=study, arm=arm, model=model, task=ep["task"], seed=ep["seed"], tool=unit["tool"], status=status, would_change=would,
                                     args=json.dumps(args, default=str)[:200], output=text[:120], trace=ep["row"]["trace_path"]))
        for event in ep["events"]:
            if event["kind"] == "handler" and event.get("event") in ("tool_not_offered", "blocked_write_tool") and (event.get("tool") in WRITE or event.get("event") == "blocked_write_tool"):
                method_rows[(study, arm)]["not_offered_events"] += 1
        if n_units:
            method_rows[(study, arm)]["episodes"] += 1
            method_rows[(study, arm)]["attempts"] += n_units
    by_arm = defaultdict(lambda: Counter())
    for a in attempts:
        by_arm[(a["study"], a["arm"])][a["status"]] += 1
    table1 = {f"{k[0]}/{k[1]}": dict(v, episodes_in_arm=arm_episodes[k], episodes_with_attempt=method_rows[k]["episodes"]) for k, v in sorted(by_arm.items())}
    per_model = {f"{s}/{a}": dict(Counter(x["model"] for x in attempts if (x["study"], x["arm"]) == (s, a))) for (s, a) in sorted(by_arm)}
    would_table = {f"{s}/{a}": dict(Counter(x["would_change"] for x in attempts if (x["study"], x["arm"]) == (s, a))) for (s, a) in sorted(by_arm)}
    status_total = dict(Counter(a["status"] for a in attempts))
    method_arm_zero = {f"{s}/{a}": dict(episodes=n, attempts=by_arm.get((s, a), Counter()).total(), not_offered_events_naming_write=method_rows[(s, a)]["not_offered_events"])
                       for (s, a), n in sorted(arm_episodes.items()) if (s, a) not in by_arm}
    item1 = dict(total_attempts=len(attempts), fairness_attempts=sum(1 for a in attempts if a["study"] == "fairness"), status_total=status_total,
                 by_arm=table1, per_model_by_arm=per_model, would_change_by_arm=would_table, arms_with_no_attempt=method_arm_zero,
                 executed=[a for a in attempts if a["status"] == "executed"])

    # ---- item 2
    def is_cap(ep):
        ends = [e for e in ep["events"] if e["kind"] == "episode_end"]
        blob = " ".join([str(ep["end_text"] or ""), json.dumps(ep["row"].get("aborts", [])), str(ends[-1].get("error")) if ends else ""])
        return "max iterations" in blob

    groups = {"ORIG (s0 S0)": ("s0", "S0"), "E0": ("fairness", "E0"), "E1": ("fairness", "E1"), "A1 (extra)": ("pilot", "A1"), "FULL (pilot C1)": ("pilot", "C1"),
              "FULL (round1 C1)": ("round1", "C1"), "FULL (ablation)": ("ablation", "FULL"), "FULL (compaction)": ("compaction", "FULL")}
    item2 = {}
    for label, key in groups.items():
        eps = [e for e in episodes if (e["study"], e["arm"]) == key]
        entry = dict(episodes=len(eps), pooled=dict(requests=summary([e["row"]["llm_requests"] for e in eps]), tokens=summary([e["row"]["input_tokens"] + e["row"]["output_tokens"] for e in eps]),
                     cap_endings=sum(is_cap(e) for e in eps), requests_ge_40=sum(e["row"]["llm_requests"] >= 40 for e in eps)), per_model={})
        top = sorted((e["row"]["llm_requests"] for e in eps), reverse=True)[:math.ceil(0.1 * len(eps))]
        entry["top_decile_share_of_requests"] = round(sum(top) / sum(e["row"]["llm_requests"] for e in eps), 3)
        for model in sorted({e["model"] for e in eps}):
            me = [e for e in eps if e["model"] == model]
            entry["per_model"][model] = dict(episodes=len(me), requests=summary([e["row"]["llm_requests"] for e in me]), tokens=summary([e["row"]["input_tokens"] + e["row"]["output_tokens"] for e in me]),
                                              cap_endings=sum(is_cap(e) for e in me))
        entry["cap_models"] = sum(1 for m in entry["per_model"].values() if m["cap_endings"] > 0)
        item2[label] = entry

    # ---- item 3
    def rebuild(calls):
        rows = []
        for c in calls:
            args = dict(c["args"] or {})
            if c.get("entity_arg"):
                args[c["entity_arg"]] = c["entity"]
            rows.append(dict(name=c["tool"], args=args, given_args=args, output=c["output"], text=c["text"] if isinstance(c["text"], str) else json.dumps(c["text"]), ok=c["ok"], line=None))
        return rows

    agree = total = 0
    repeats = []
    for ep in episodes:
        all_calls = [c for r in ep["requests"] for c in r["calls"]]
        try:
            mine = C.v2.support_missing(ep["task_def"], rebuild(all_calls))
        except Exception:
            mine = None
        total += 1
        agree += (mine is not None and sorted(mine) == sorted(ep["scored"]["support_missing"]))
        seen, repeat_list = set(), []
        for request in ep["requests"]:
            for unit in request.get("units", []):
                if unit["harness_error"] or not unit["ok"]:
                    continue
                key = (unit["tool"], json.dumps(unit["args"], sort_keys=True, default=str))
                if key in seen:
                    repeat_list.append(request["index"])
                seen.add(key)
        if len(repeat_list) < 2:
            continue
        first = repeat_list[0]
        before = [c for r in ep["requests"] if r["index"] < first for c in r["calls"]]
        try:
            missing = C.v2.support_missing(ep["task_def"], rebuild(before))
        except Exception:
            missing = ["error"]
        last = len(ep["requests"])
        repeats.append(dict(study=ep["study"], arm=ep["arm"], model=ep["model"], task=ep["task"], seed=ep["seed"], repeats=len(repeat_list), first_repeat_request=first,
                            klass="facts_present" if not missing else "facts_not_yet", missing=missing[:3], supported=bool(ep["supported"]), no_answer=ep["answer"] is None,
                            requests_after_first_repeat=last - first, trace=ep["row"]["trace_path"]))
    stock = {("s0", "S0"), ("pilot", "A1"), ("fairness", "E0"), ("fairness", "E1")}

    def tally(rows):
        out = {}
        for klass in ("facts_present", "facts_not_yet"):
            r = [x for x in rows if x["klass"] == klass]
            out[klass] = dict(episodes=len(r), unsupported=sum(not x["supported"] for x in r), no_answer=sum(x["no_answer"] for x in r), unsupported_or_no_answer=sum((not x["supported"]) or x["no_answer"] for x in r),
                              requests_after_first_repeat_sum=sum(x["requests_after_first_repeat"] for x in r),
                              requests_after_first_repeat_median=statistics.median([x["requests_after_first_repeat"] for x in r]) if r else None)
        return out
    models = sorted({x["model"] for x in repeats})
    item3 = dict(b3a_rebuild_agreement=dict(agree=agree, total=total, share=round(agree / total, 4)), episodes_of_interest=len(repeats), pooled=tally(repeats),
                 per_model={m: tally([x for x in repeats if x["model"] == m]) for m in models},
                 stock_arms=tally([x for x in repeats if (x["study"], x["arm"]) in stock]), menu_arms=tally([x for x in repeats if (x["study"], x["arm"]) not in stock]))
    fp = [x for x in repeats if x["klass"] == "facts_present"]
    item3["bar_B3"] = dict(facts_present_episodes=len(fp), models=len({x["model"] for x in fp}), unsupported_or_no_answer=sum((not x["supported"]) or x["no_answer"] for x in fp))
    results = dict(protocol_sha256=(HERE / "PROTOCOL.sha256").read_text().split()[0], episodes=len(episodes), item1=item1, item2=item2, item3=item3)
    (HERE / "results.json").write_text(json.dumps(results, indent=1, default=str))
    (HERE / "attempts.jsonl").write_text("".join(json.dumps(a) + "\n" for a in attempts))
    (HERE / "repeats.jsonl").write_text("".join(json.dumps(r) + "\n" for r in repeats))
    print("done", len(attempts), "attempts;", len(repeats), "repeat episodes; B3a", item3["b3a_rebuild_agreement"])


if __name__ == "__main__":
    main()
