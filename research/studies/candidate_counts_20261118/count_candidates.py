"""Candidate counts (offline). Protocol: PROTOCOL.md (hash in PROTOCOL.sha256). CPU only; no model, no ROS.

Run from the repo root:  uv run python research/studies/candidate_counts_20261118/count_candidates.py

Flow: select episodes (protocol section 1) -> parse each trace into requests and calls (offline_replay_20261116/episodes.py)
-> re-score with scorer v2.0 -> compute the counts (a)-(e) per episode -> aggregate per (study, model) -> results.json + jsonl detail files.
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
import scorer_v2 as v2  # noqa: E402

LONG_RESULT_CHARS = 8000  # protocol (d): about 2,000 tokens at 4 characters per token (an estimate)
FULL_TYPE = {("pilot", "C1"), ("round1", "C1"), ("round2", "CONTROL"), ("ablation", "FULL"), ("compaction", "FULL")}
NO_FINISH_ARMS = {("ablation", "NO_FINISH"), ("fairness", "E0"), ("fairness", "E1"), ("s0", "S0")}
HARNESS_PREFIXES = ["Invalid arguments", "Tool ", "final_answer needs", "Answer not accepted", "The list of names", "Too many names"]
WRITE_TOOLS = {"ros2_service_call", "ros2_param_set"}


# ------------------------------------------------------------------ selection (protocol section 1)
def load_population():
    pilot_excluded = {r for g in json.loads((STUDIES / "small_model_harness_20261115/INFRA_EXCLUDED.json").read_text()).values() for r in g["run_ids"]}
    round2_excluded = set(json.loads((STUDIES / "build_round2_20261116/INFRA_EXCLUDED.json").read_text())["run_ids"])
    pilot_scores = {r["run_id"]: r["new"] for r in json.loads((STUDIES / "residual_failures_20261115/rescore_v2.json").read_text())}
    folders = {"pilot": "small_model_harness_20261115", "round1": "build_round1_20261115", "round2": "build_round2_20261116",
               "fairness": "fairness_errors_as_text_20261117", "ablation": "steady_loop_ablation_20261117",
               "namefix": "name_fix_applied_20261117", "compaction": "tool_description_compaction_20261117", "s0": "s0_dev_20261116"}
    selected, seen = [], set()
    for study, folder in folders.items():
        for line in (STUDIES / folder / "RESULTS_LOG.jsonl").read_text().splitlines():
            row = json.loads(line)
            if not row.get("trace_path"):
                continue
            if study != "pilot" and row.get("phase") != "full":
                continue
            if study == "pilot" and row["run_id"] in pilot_excluded:
                continue
            trace = row["trace_path"]
            if study == "round2":
                rel = trace.split("/build_round2_20261116/", 1)[-1].removesuffix("/trace.jsonl")
                if rel in round2_excluded or (rel.startswith("full_20261116T003046Z/") and row["run_id"] in round2_excluded):
                    continue
            if trace in seen:
                continue
            seen.add(trace)
            selected.append((study, row))
    return selected


def all_tasks():
    tasks = E.load_tasks()
    tasks.update({t["id"]: t for t in json.loads((STUDIES / "name_fix_applied_20261117/namefix_tasks.json").read_text())})
    return tasks


# ------------------------------------------------------------------ per-episode data
def parse_episode(study, row, tasks):
    events = v2.s1.read_events(ROOT / row["trace_path"])
    ep = E.parse(study, row, tasks)
    task = tasks[row["task"]]
    accepted = [e for e in events if e["kind"] == "final_answer_accepted"]
    answer, source = v2.episode_answer(events)
    if study == "namefix":
        original = [e for e in events if e["kind"] == "final_answer_original"]
        if original:
            answer = original[-1].get("answer", answer)
        scored = v2.score_task(task, answer, ep["rows"])
    else:
        scored = ep["scored"]
    end = [e for e in events if e["kind"] == "episode_end"]
    end_text = end[-1].get("answer") if end else None
    if accepted:
        ending = "final_answer"
    elif answer is not None:
        ending = "text"
    else:
        ending = "none"
    ep.update(study=study, row=row, events=events, answer=answer, answer_source_rederived=source, scored=scored, supported=scored["supported_complete"],
              ending=ending, end_text=end_text if isinstance(end_text, str) else json.dumps(end_text), task_def=task)
    return ep


def b0_check(ep):
    """Protocol B0: re-scored support and answer source against the log. Returns a list of disagreement labels."""
    row, labels = ep["row"], []
    if ep["study"] == "pilot":
        logged = PILOT_SCORES.get(row["run_id"])
    elif ep["study"] == "namefix":
        logged = row.get("strict_original")
    else:
        logged = row.get("supported_complete")
    if logged is not None and bool(logged) != bool(ep["supported"]):
        labels.append(f"supported logged {logged} vs re-scored {ep['supported']}")
    if row.get("answer_source") and ep["study"] != "namefix":
        source = "final_answer" if ep["ending"] == "final_answer" else "free_text"
        if row["answer_source"] != source:
            labels.append(f"answer_source logged {row['answer_source']} vs {source}")
    return labels


# ------------------------------------------------------------------ (a) name binding at input
def normalised(name):
    return "/" + name.lstrip("/") if isinstance(name, str) else name


def calls_in_order(ep):
    for request in ep["requests"]:
        for call in request["calls"]:
            yield request["index"], call


def fires_a(ep):
    """Protocol (a): not-found call, entity without leading slash, unique whole-segment suffix of one clean-ledger name."""
    out = []
    outputs_by_request = []  # raw outputs of units per request, for the ledger of later requests
    for request in ep["requests"]:
        outputs_by_request.append([u["output"] for u in request.get("units", [])])
    for request in ep["requests"]:
        ledger_outputs = [o for earlier in outputs_by_request[:request["index"] - 1] for o in earlier]
        ledger = None
        for call in request["calls"]:
            entity = call["entity"]
            if call["tool"] == "final_answer" or call["ok"] or call["harness_error"] or not isinstance(entity, str):
                continue
            if not E.NOT_FOUND.search(call["text"] if isinstance(call["text"], str) else ""):
                continue
            if entity.startswith("/") or not ag.RELATIVE_NAME.fullmatch(entity):
                continue
            if ledger is None:
                ledger = ag.allowed_names(ep["task_text"], ledger_outputs)
            if entity in ledger or normalised(entity) in ledger:
                continue
            matches = ag.trailing_matches(entity, ledger)
            if len(matches) != 1:
                continue
            resolution = matches[0]
            later, later_request, resolution_used = None, None, False
            for index, other in calls_in_order(ep):
                if index <= request["index"] or not other["ok"] or other["harness_error"] or not isinstance(other["entity"], str):
                    continue
                value = normalised(other["entity"])
                if value == resolution:
                    resolution_used = True
                if later is None and (value == normalised(entity) or value.endswith("/" + entity.lstrip("/"))):
                    later, later_request = value, index
            if later is None:
                verdict = "no_later_use"
            else:
                verdict = "agree" if later == resolution else "differ"
            out.append(dict(run_id=ep["run_id"], study=ep["study"], model=ep["model"], arm=ep["arm"], task=ep["task"], seed=ep["seed"], trace=ep["row"]["trace_path"],
                            request=request["index"], tool=call["tool"], typed=entity, resolution=resolution, later_entity=later,
                            request_distance=(later_request - request["index"]) if later else None, resolution_used_later=resolution_used, verdict=verdict))
    return out


# ------------------------------------------------------------------ (b) partial-match exposure
def result_names(output, text):
    names = set(ag.names_in_text(text if isinstance(text, str) else ""))
    if isinstance(output, dict):
        for value in output.values():
            if isinstance(value, list):
                names |= {n for n in value if isinstance(n, str) and ag.ABSOLUTE_NAME.fullmatch(n)}
    return names


def strings_of(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield str(k)
            yield from strings_of(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings_of(v)


def events_b(ep):
    out = []
    answer_strings = set(strings_of(ep["answer"])) if ep["answer"] is not None else set()
    end_tokens = set(re.findall(r"[/\w]+", ep["end_text"] or ""))
    for request in ep["requests"]:
        for unit in request.get("units", []):
            pattern = (unit["args"] or {}).get("pattern")
            if unit["harness_error"] or not isinstance(pattern, str) or not ag.ABSOLUTE_NAME.fullmatch(pattern) or not unit["ok"]:
                continue
            names = result_names(unit["output"], unit["text"])
            if pattern in names:
                continue
            partial = sorted(n for n in names if n != pattern and pattern in n)
            if not partial:
                continue
            pool = answer_strings if ep["answer"] is not None else end_tokens
            named = sorted(set(partial) & pool)
            typed_named = pattern in pool
            truth = set(strings_of(ep["task_def"]["answer"]))
            out.append(dict(run_id=ep["run_id"], study=ep["study"], model=ep["model"], arm=ep["arm"], task=ep["task"], seed=ep["seed"], trace=ep["row"]["trace_path"],
                            request=request["index"], tool=unit["tool"], pattern=pattern, partial=partial, answer_names_partial=named, answer_names_typed=typed_named,
                            partial_is_truth=bool(set(partial) & truth), supported=ep["supported"]))
    return out


# ------------------------------------------------------------------ (d) needle missed
def needle_d(ep):
    scored = ep["scored"]
    if ep["supported"]:
        return None
    missing = scored["support_missing"]
    if missing:
        kind = "S" if scored["exact"] else None
        if kind is None:
            return None
        return dict(kind="S")
    if ep["answer"] is None:
        return dict(kind="D0")
    if scored["exact"]:
        return None
    # D1: longest successful result that supplies a support fact
    supplying = 0
    for request in ep["requests"]:
        for unit in request.get("units", []):
            if not unit["ok"] or unit["harness_error"]:
                continue
            text = unit["text"].replace("\\n", "\n")
            length = len(text)
            for req in ep["task_def"]["support"]:
                if req[0] == "text" and req[1] in text:
                    supplying = max(supplying, length)
                if req[0] == "param" and unit["tool"] == "ros2_param_get":
                    supplying = max(supplying, length)
    return dict(kind="D1", longest_supplying_result_chars=supplying, long=supplying >= LONG_RESULT_CHARS, issues=scored["issues"][:6])


# ------------------------------------------------------------------ (e) open-search detectors
def detectors_e(ep):
    found = defaultdict(int)
    seen_ok, seen_fail = set(), set()
    prefix_counts = Counter()
    last_index = len(ep["requests"])
    reread_seen = {}
    for request in ep["requests"]:
        units = request.get("units", [])
        if not units and request["index"] != last_index:
            found["mid_text_only_request"] += 1
        for unit in units:
            key = (unit["tool"], json.dumps(unit["args"], sort_keys=True, default=str))
            if unit["harness_error"]:
                for prefix in HARNESS_PREFIXES:
                    if str(unit["output"]).startswith(prefix):
                        prefix_counts[prefix.strip()] += 1
                        found["harness_rejected_call"] += 1
                        break
            elif unit["ok"]:
                if key in seen_ok:
                    found["identical_repeated_ok_call"] += 1
                seen_ok.add(key)
                if len(unit["text"].replace("\\n", "\n")) >= LONG_RESULT_CHARS:
                    found["long_result"] += 1
                    found["requests_after_long_result"] += max(0, last_index - request["index"])
                # same tool, same entities, entity written differently (slash added or dropped)
                alt = (unit["tool"], json.dumps({k: ([normalised(x) for x in v] if isinstance(v, list) else normalised(v)) if E.entity_argument(k) else v
                                                 for k, v in (unit["args"] or {}).items()}, sort_keys=True, default=str))
                if alt in reread_seen and reread_seen[alt] != key:
                    found["reread_slash_variant"] += 1
                reread_seen.setdefault(alt, key)
            else:
                if key in seen_fail:
                    found["identical_repeated_failed_call"] += 1
                seen_fail.add(key)
            if unit["tool"] in WRITE_TOOLS:
                found["write_tool_attempt"] += 1
    for event in ep["events"]:
        if event["kind"] == "handler" and event.get("event") == "tool_not_offered":
            found["tool_not_offered"] += 1
    endings = (ep["end_text"] or "") + " " + " ".join(str(a) for a in ep["row"].get("aborts", []))
    if "ResponseError" in endings:
        found["backend_error_ResponseError"] += 1
    if "XML syntax" in endings or "XML" in endings and "syntax" in endings:
        found["backend_error_XML_syntax"] += 1
    if "max iterations" in endings:
        found["max_iterations_ending"] += 1
    return dict(found), prefix_counts


# ------------------------------------------------------------------ aggregation helpers
def rate(num, den):
    return None if not den else round(num / den, 4)


def main():
    global PILOT_SCORES
    PILOT_SCORES = {r["run_id"]: r["new"] for r in json.loads((STUDIES / "residual_failures_20261115/rescore_v2.json").read_text())}
    tasks = all_tasks()
    population = load_population()
    parsed, parse_errors = [], []
    for study, row in population:
        try:
            parsed.append(parse_episode(study, row, tasks))
        except Exception as error:  # reported, never hidden
            parse_errors.append(dict(run_id=row["run_id"], study=study, error=f"{type(error).__name__}: {error}"))
    b0_rows = []
    for ep in parsed:
        labels = b0_check(ep)
        ep["b0"] = labels
        if labels:
            b0_rows.append(dict(run_id=ep["run_id"], study=ep["study"], model=ep["model"], arm=ep["arm"], labels=labels))
    b0_excluded = {r["run_id"] for r in b0_rows}

    fires, partial_events, needles = [], [], []
    detectors = defaultdict(lambda: defaultdict(int))
    detector_examples = defaultdict(list)
    prefix_totals = defaultdict(Counter)
    ending_table = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # (group, study/arm, model) -> ending -> [episodes, supported]
    episode_counts = defaultdict(int)
    for ep in parsed:
        cell = (ep["study"], ep["model"])
        episode_counts[cell] += 1
        episode_counts[(ep["study"], "ALL")] += 1
        fires.extend(fires_a(ep))
        partial_events.extend(events_b(ep))
        found, prefixes = detectors_e(ep)
        for name, count in found.items():
            detectors[name][cell] += count
            detectors[name][(ep["study"], "ALL")] += count
            if name not in ("requests_after_long_result",) and len(detector_examples[name]) < 3:
                detector_examples[name].append(ep["row"]["trace_path"])
        for prefix, count in prefixes.items():
            prefix_totals[prefix][cell] += count
        if ep["run_id"] in b0_excluded:
            continue
        key = (ep["study"], ep["arm"])
        group = "FULL-type" if key in FULL_TYPE else ("no finish tool" if key in NO_FINISH_ARMS else "other arms offering final_answer")
        for model in (ep["model"], "ALL"):
            slot = ending_table[(group, ep["study"], ep["arm"], model)][ep["ending"]]
            slot[0] += 1
            slot[1] += int(bool(ep["supported"]))
        need = needle_d(ep)
        if need:
            needles.append(dict(run_id=ep["run_id"], study=ep["study"], model=ep["model"], arm=ep["arm"], task=ep["task"], seed=ep["seed"], trace=ep["row"]["trace_path"], **need))

    def cell_table(rows, value):
        table = defaultdict(lambda: defaultdict(int))
        for r in rows:
            table[r["study"]][r["model"]] += 1
            table[r["study"]]["ALL"] += 1
            table["ALL STUDIES"][r["model"]] += 1
            table["ALL STUDIES"]["ALL"] += 1
        return {k: dict(v) for k, v in table.items()}

    distances = [f["request_distance"] for f in fires if f["request_distance"] is not None]
    a_summary = dict(
        fires=len(fires), episodes_with_fire=len({f["run_id"] for f in fires}), models_with_fire=sorted({f["model"] for f in fires}),
        verdicts=dict(Counter(f["verdict"] for f in fires)), by_study_model=cell_table(fires, None),
        verdict_by_study_model={s: {m: dict(Counter(f["verdict"] for f in fires if f["study"] == s and f["model"] == m)) for m in sorted({f["model"] for f in fires if f["study"] == s})} for s in sorted({f["study"] for f in fires})},
        verdict_by_model={m: dict(Counter(f["verdict"] for f in fires if f["model"] == m)) for m in sorted({f["model"] for f in fires})},
        request_distance_median=statistics.median(distances) if distances else None, request_distance_mean=round(statistics.mean(distances), 2) if distances else None,
        differ_list=[f for f in fires if f["verdict"] == "differ"],
        bar=dict(fires_ge_10=len(fires) >= 10, models_ge_2=len({f["model"] for f in fires}) >= 2, differ_zero=not any(f["verdict"] == "differ" for f in fires)))
    a_summary["bar"]["passes"] = all(a_summary["bar"].values())

    b_summary = dict(events=len(partial_events), episodes=len({e["run_id"] for e in partial_events}), by_study_model=cell_table(partial_events, None),
                     answer_names_partial=sum(1 for e in partial_events if e["answer_names_partial"]),
                     answer_names_typed_nonexistent=sum(1 for e in partial_events if e["answer_names_typed"]),
                     partial_is_truth=sum(1 for e in partial_events if e["partial_is_truth"]),
                     supported_events=sum(1 for e in partial_events if e["supported"]),
                     episodes_answer_names_partial=len({e["run_id"] for e in partial_events if e["answer_names_partial"]}))

    c_summary = {}
    for (group, study, arm, model), endings in sorted(ending_table.items()):
        c_summary.setdefault(group, {}).setdefault(f"{study}/{arm}", {})[model] = {k: dict(episodes=v[0], supported=v[1], supported_rate=rate(v[1], v[0])) for k, v in endings.items()}
    full_totals = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for (group, study, arm, model), endings in ending_table.items():
        if group == "FULL-type":
            for ending, (n, s) in endings.items():
                full_totals[model][ending][0] += n
                full_totals[model][ending][1] += s
    c_full_by_model = {m: {k: dict(episodes=v[0], supported=v[1], supported_rate=rate(v[1], v[0])) for k, v in d.items()} for m, d in full_totals.items()}

    d1 = [n for n in needles if n["kind"] == "D1"]
    d_summary = dict(
        D1_episodes=len(d1), D1_models=sorted({n["model"] for n in d1}), D1_distinct_task_model=len({(n["task"], n["model"]) for n in d1}),
        D1_long=sum(1 for n in d1 if n["long"]), D1_long_models=sorted({n["model"] for n in d1 if n["long"]}),
        D0_episodes=sum(1 for n in needles if n["kind"] == "D0"), S_episodes=sum(1 for n in needles if n["kind"] == "S"),
        D1_by_study_model=cell_table(d1, None),
        D1_by_model={m: sum(1 for n in d1 if n["model"] == m) for m in sorted({n["model"] for n in d1})},
        bar=dict(episodes_ge_5=len(d1) >= 5, models_ge_2=len({n["model"] for n in d1}) >= 2),
        long_alone_reaches_bar=(sum(1 for n in d1 if n["long"]) >= 5 and len({n["model"] for n in d1 if n["long"]}) >= 2))
    d_summary["bar"]["passes"] = all(d_summary["bar"].values())

    results = dict(
        protocol_sha256=(HERE / "PROTOCOL.sha256").read_text().split()[0], script_file="count_candidates.py",
        population=dict(episodes=len(parsed), parse_errors=parse_errors, per_study_model={f"{k[0]}|{k[1]}": v for k, v in sorted(episode_counts.items())},
                        b0_disagreements=b0_rows, b0_excluded_from_c_d=len(b0_excluded)),
        a_name_binding=a_summary, b_partial_match=b_summary, c_finish_tool=dict(by_group=c_summary, full_type_by_model=c_full_by_model),
        d_needle_missed=d_summary,
        e_detectors={name: {f"{k[0]}|{k[1]}": v for k, v in sorted(cells.items())} for name, cells in sorted(detectors.items())},
        e_examples=dict(detector_examples), e_harness_prefixes={p: {f"{k[0]}|{k[1]}": v for k, v in sorted(c.items())} for p, c in prefix_totals.items()})
    (HERE / "results.json").write_text(json.dumps(results, indent=1, default=str))
    for name, rows in (("fires_a.jsonl", fires), ("events_b.jsonl", partial_events), ("needle_d.jsonl", needles)):
        (HERE / name).write_text("".join(json.dumps(r, default=str) + "\n" for r in rows))
    print(f"episodes {len(parsed)}, parse errors {len(parse_errors)}, B0 disagreements {len(b0_rows)}")
    print(f"(a) fires {a_summary['fires']} verdicts {a_summary['verdicts']} bar {a_summary['bar']}")
    print(f"(b) events {b_summary['events']} episodes {b_summary['episodes']}")
    print(f"(d) D1 {d_summary['D1_episodes']} models {d_summary['D1_models']} bar {d_summary['bar']}")


if __name__ == "__main__":
    main()
