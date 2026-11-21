"""Stall hint v2, Step 1 (offline replay). Protocol: PROTOCOL_STEP1.md (hash in PROTOCOL_STEP1.sha256). CPU only; no model, no ROS.

Run from the repo root:  uv run python research/studies/stall_hint_v2_20261118/step1_offline.py

Flow per recorded episode: parse the trace into requests/units (episodes.py), replay the recount's stall rule unit by unit
(copied from decisions/2026-11-17-stall-recount.py so that B0 can compare), and at each stall build the hint from the ledger *before* that unit.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STUDIES = ROOT / "research/studies"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIES / "offline_replay_20261116"))
import episodes as E  # noqa: E402
import answer_gate as ag  # noqa: E402

# ---------------------------------------------------------------- frozen constants (protocol section 1)
MAX_SHOWN = 5
MIN_Q = 3
REGEX_CHARS = re.compile(r"[\^\$\.\*\+\?\(\)\[\]\{\}\|\\]")
ENTITY_ARGS = {"nodes": "node", "topics": "topic", "services": "service", "node_name": "node", "topic": "topic"}
LIST_TOOL_KIND = {"ros2_node_list": "node", "ros2_topic_list": "topic", "ros2_service_list": "service"}
TOOLS_BY_KIND = {"node": ["ros2_node_info", "ros2_param_list", "ros2_param_get"],
                 "topic": ["ros2_topic_info", "ros2_topic_echo"],
                 "service": ["ros2_service_info"]}
INFO_TOOL_KIND = {"ros2_node_info": "node", "ros2_topic_info": "topic", "ros2_service_info": "service"}
HEADING_KIND = {"subscribers": "topic", "publishers": "topic", "service servers": "service", "service clients": "service"}


# ---------------------------------------------------------------- selection (copied from the recount)
def load_population():
    sources = {"pilot": STUDIES / "small_model_harness_20261115/RESULTS_LOG.jsonl",
               "round1": STUDIES / "build_round1_20261115/RESULTS_LOG.jsonl",
               "round2": STUDIES / "build_round2_20261116/RESULTS_LOG.jsonl"}
    pilot_excluded = json.loads((STUDIES / "small_model_harness_20261115/INFRA_EXCLUDED.json").read_text())
    pilot_excluded = {run for group in pilot_excluded.values() for run in group["run_ids"]}
    round2_excluded = set(json.loads((STUDIES / "build_round2_20261116/INFRA_EXCLUDED.json").read_text())["run_ids"])
    pilot_scores = {r["run_id"]: r["new"] for r in json.loads((STUDIES / "residual_failures_20261115/rescore_v2.json").read_text())}
    selected, seen_paths = [], set()
    for group, path in sources.items():
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if group != "pilot" and row.get("phase") != "full":
                continue
            if group == "pilot" and row["run_id"] in pilot_excluded:
                continue
            trace = row["trace_path"]
            if group == "round2":
                rel = trace.split("/build_round2_20261116/", 1)[-1].removesuffix("/trace.jsonl")
                if rel in round2_excluded or (rel.startswith("full_20261116T003046Z/") and row["run_id"] in round2_excluded):
                    continue
            if trace in seen_paths:
                continue
            seen_paths.add(trace)
            supported = pilot_scores.get(row["run_id"]) if group == "pilot" else row.get("supported_complete")
            selected.append((group, row, supported))
    return selected


def empty_or_missing(out, text):
    if out is None:
        return False
    if out == "" or out == [] or out == {}:
        return True
    if isinstance(out, dict) and all(value in ([], {}, None, "") for value in out.values()):
        return True
    return bool(E.NOT_FOUND.search(text))


# ---------------------------------------------------------------- ledger kinds (protocol: kind sets from provenance)
def add_kinds(kinds, unit):
    """Record the kind of every full name that a successful unit result shows. Names with no rule stay unknown (absent from `kinds`)."""
    tool, out, text = unit["tool"], unit["output"], unit["text"]
    for name, namespace in ag.NODE_BLOCK.findall(text.replace("\\n", "\n")):
        kinds[f"{namespace.rstrip('/')}/{name}"].add("node")
    if tool in LIST_TOOL_KIND and isinstance(out, dict):
        for value in out.values():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and ag.ABSOLUTE_NAME.fullmatch(item):
                        kinds[item].add(LIST_TOOL_KIND[tool])
    if tool in INFO_TOOL_KIND and isinstance(out, dict):
        for key, value in out.items():
            if ag.ABSOLUTE_NAME.fullmatch(str(key)) and not (isinstance(value, dict) and "error" in value):
                kinds[key].add(INFO_TOOL_KIND[tool])
                if tool == "ros2_node_info" and isinstance(value, str):
                    heading_kind = None
                    for line in value.replace("\\n", "\n").split("\n"):
                        stripped = line.strip().rstrip(":").lower()
                        if line.strip().endswith(":") and stripped in HEADING_KIND:
                            heading_kind = HEADING_KIND[stripped]
                        elif line.strip().endswith(":") and not line.startswith("    "):
                            heading_kind = None
                        elif heading_kind and line.startswith("    "):
                            for found in ag.NAME_IN_TEXT.findall(line):
                                kinds[found].add(heading_kind)


# ---------------------------------------------------------------- hint content
def typed_strings(unit):
    """(kind of the argument or None, typed string) for every entity or pattern string of a call."""
    found = []
    for key, value in (unit["args"] or {}).items():
        values = value if isinstance(value, list) else [value]
        for item in values:
            if not isinstance(item, str) or not item:
                continue
            if key in ENTITY_ARGS:
                found.append((ENTITY_ARGS[key], item, "entity"))
            elif key == "pattern":
                found.append((LIST_TOOL_KIND.get(unit["tool"]), item, "pattern"))
    return found


def query_of(typed):
    cleaned = REGEX_CHARS.sub(" ", typed)
    segments = [s for s in re.split(r"[/\s]+", cleaned) if s]
    q = segments[-1] if segments else ""
    return q if len(q) >= MIN_Q else ""


def build_hint(unit, ledger, kinds):
    """Return dict(tiers, shown, suggested_tools, kind_mismatch, type, text). Uses only the ledger and kinds before this unit."""
    tiers = {"T1": [], "T2": [], "T3": []}
    argument_kinds = set()
    for arg_kind, typed, how in typed_strings(unit):
        if arg_kind:
            argument_kinds.add(arg_kind)
        q = query_of(typed)
        if typed in ledger:
            tiers["T1"].append(typed)
        if how == "entity":
            suffix = typed if typed.startswith("/") else "/" + typed
            for name in sorted(ledger):
                if name != typed and name.endswith(suffix):
                    tiers["T2"].append(name)
        if q:
            for name in sorted(ledger):
                last = name.rsplit("/", 1)[-1]
                if name in tiers["T1"] or name in tiers["T2"] or name == typed:
                    continue
                if q in last or (len(last) >= MIN_Q and last in q):
                    tiers["T3"].append(name)
    ordered = []
    for tier in ("T1", "T2", "T3"):
        for name in tiers[tier]:
            if name not in ordered:
                ordered.append(name)
    shown = ordered[:MAX_SHOWN]
    shown_kinds = {name: sorted(kinds.get(name, ())) for name in shown}
    suggested = []
    for name in shown:
        for kind in shown_kinds[name]:
            for tool in TOOLS_BY_KIND.get(kind, []):
                if tool not in suggested:
                    suggested.append(tool)
    informative = bool(tiers["T2"] or tiers["T3"])
    if informative:
        kind_type = "informative"
    elif tiers["T1"]:
        kind_type = "t1_only"
    else:
        kind_type = "empty"
    known_kinds = {k for name in shown for k in shown_kinds[name]}
    kind_mismatch = bool(informative and argument_kinds and known_kinds and not (known_kinds & argument_kinds))
    if shown:
        parts = [f"{name} ({'/'.join(shown_kinds[name]) or 'kind unknown'})" for name in shown]
        text = ("Hint from this session's own results: the same result came back again. Full names already seen that match what you typed: "
                + "; ".join(parts) + ".")
        if suggested:
            text += " Tools that take those kinds of names: " + ", ".join(suggested) + "."
    else:
        text = "Hint from this session's own results: the same result came back again. No seen full name matches what you typed."
    return dict(tiers={k: list(dict.fromkeys(v)) for k, v in tiers.items()}, shown=shown, kinds=shown_kinds, suggested=suggested,
                kind_mismatch=kind_mismatch, type=kind_type, text=text)


# ---------------------------------------------------------------- per-episode replay
def replay(group, row, supported, tasks, clean_ledger_for_hint=False):
    ep = E.parse(group, row, tasks)
    ledger = set(ag.names_in_text(ep["task_text"]))
    clean = set(ledger)  # name-fix style ledger: failed list items are skipped (used for hint content only in the post-hoc sensitivity run)
    kinds = defaultdict(set)
    prior, empty_count = set(), defaultdict(int)
    returned_by_tool = defaultdict(set)
    stalls, fires, later_units = 0, [], []
    for req in ep["requests"]:
        for unit in req["units"]:
            tool, out, text = unit["tool"], unit["output"], unit["text"]
            if tool == "final_answer" or out is None:
                continue
            key = (tool, text)
            repeat = key in prior
            empty = empty_or_missing(out, text)
            if empty:
                empty_count[tool] += 1
            is_empty_stall = empty and empty_count[tool] >= 2
            is_new_result = text not in returned_by_tool[tool]
            if repeat or is_empty_stall:
                stalls += 1
                hint = build_hint(unit, clean if clean_ledger_for_hint else ledger, kinds)
                hint["shown_not_in_clean_ledger"] = [n for n in hint["shown"] if n not in clean]
                hint.update(request=req["index"], tool=tool, args=unit["args"], rule=("a" if repeat else "b") if not (repeat and is_empty_stall) else "a+b")
                fires.append(hint)
            later_units.append(dict(request=req["index"], tool=tool, args=unit["args"], ok=bool(unit["ok"]), empty=empty, new_result=is_new_result,
                                    entities=[t for _k, t, how in typed_strings(unit) if how == "entity"]))
            returned_by_tool[tool].add(text)
            prior.add(key)
            if unit["ok"]:
                names = set(ag.names_in_text(text))
                if isinstance(out, dict) and isinstance(out.get("nodes"), list):
                    names |= {n for n in out["nodes"] if isinstance(n, str) and ag.ABSOLUTE_NAME.fullmatch(n)}
                add_kinds(kinds, unit)
                if not unit.get("harness_error"):
                    for part in ag.successful_text_parts(out):
                        clean |= ag.names_in_text(part)
                    if isinstance(out, dict) and isinstance(out.get("nodes"), list):
                        clean |= {n for n in out["nodes"] if isinstance(n, str) and ag.ABSOLUTE_NAME.fullmatch(n)}
                new = names - ledger
                if new:
                    empty_count.clear()
                    ledger |= new
    return dict(group=group, arm=row["arm"], model=row["model"], task=row["task"], seed=row["seed"], supported=supported,
                trace_path=row["trace_path"], stall_calls=stalls, fires=fires, units=later_units)


def next_progress_call(episode, fire):
    """P: first call in a later request that is ok, has an entity argument, and returns a nonempty result never returned before by that tool."""
    for unit in episode["units"]:
        if unit["request"] > fire["request"] and unit["ok"] and not unit["empty"] and unit["new_result"] and unit["entities"]:
            return unit
    return None


def classify_p(fire, p):
    if p is None:
        return "no_p"
    in_names = any(entity in fire["shown"] for entity in p["entities"])
    in_tools = p["tool"] in fire["suggested"]
    delayed = p["request"] >= fire["request"] + 2
    if in_names and in_tools:
        return "pointed_delayed" if delayed else "pointed_immediate"
    if fire["shown"] and fire["suggested"] and not in_names and not in_tools:
        return "contradicted"
    return "indeterminate"


def pct(a, b):
    return f"{a}/{b} = {100 * a / b:.1f}%" if b else f"{a}/0"


def summarize(label, eps):
    fires = [f for e in eps for f in e["fires"]]
    informative = [f for f in fires if f["type"] == "informative"]
    with_info = sum(any(f["type"] == "informative" for f in e["fires"]) for e in eps)
    b2_rows = []
    for e in eps:
        if e["supported"] is not True:
            continue
        first = next((f for f in e["fires"] if f["type"] == "informative"), None)
        if first is None:
            continue
        p = next_progress_call(e, first)
        if p is None:
            continue
        b2_rows.append((e, first, p, classify_p(first, p)))
    counts = Counter(c for *_, c in b2_rows)
    pointed = counts["pointed_immediate"] + counts["pointed_delayed"]
    out = dict(label=label, episodes=len(eps), episodes_with_stall=sum(e["stall_calls"] > 0 for e in eps), fires=len(fires),
               fire_types=dict(Counter(f["type"] for f in fires)), kind_mismatch_fires=sum(f["kind_mismatch"] for f in informative),
               episodes_with_informative_fire=with_info, informative_fire_episode_rate=pct(with_info, len(eps)),
               informative_share_of_fires=pct(len(informative), len(fires)),
               b2_denominator=len(b2_rows), b2_classes=dict(counts), b2_pointed=pct(pointed, len(b2_rows)),
               b3_delayed_share_of_pointed=pct(counts["pointed_delayed"], pointed), b4_contradicted=pct(counts["contradicted"], len(b2_rows)),
               hint_chars_mean=round(sum(len(f["text"]) for f in fires) / len(fires), 1) if fires else None)
    return out, b2_rows


def main():
    clean_mode = "--clean-ledger" in sys.argv
    suffix = "_clean" if clean_mode else ""
    tasks = E.load_tasks()
    selected = load_population()
    episodes_ = []
    errors = []
    for group, row, supported in selected:
        try:
            episodes_.append(replay(group, row, supported, tasks, clean_mode))
        except Exception as exc:  # report, never hide
            errors.append(dict(trace_path=row["trace_path"], error=repr(exc)))
    # B0: compare with the recount, per episode
    recount = {json.loads(l)["trace_path"]: json.loads(l) for l in (ROOT / "research/decisions/2026-11-17-stall-episodes.jsonl").read_text().splitlines()}
    mismatches = [(e["trace_path"], e["stall_calls"], recount[e["trace_path"]]["stall_calls"]) for e in episodes_
                  if e["trace_path"] not in recount or recount[e["trace_path"]]["stall_calls"] != e["stall_calls"]]
    missing = [p for p in recount if p not in {e["trace_path"] for e in episodes_}]
    b0 = dict(episodes_replayed=len(episodes_), recount_episodes=len(recount), mismatched=len(mismatches), missing_from_replay=len(missing), errors=len(errors),
              pass_=(len(mismatches) == 0 and not missing and not errors and len(episodes_) == 1248))

    def c1_type(e):
        return (e["group"] in ("pilot", "round1") and e["arm"] == "C1") or (e["group"] == "round2" and e["arm"] == "CONTROL")
    weak = {"bonsai-2:4b", "lfm3:1.7b"}
    populations = {
        "PRIMARY: C1-type, bonsai+lfm3": [e for e in episodes_ if c1_type(e) and e["model"] in weak],
        "C1-type, all four models": [e for e in episodes_ if c1_type(e)],
        "all arms, all models": episodes_,
        "PRIMARY, round-2 CONTROL seeds 1-2 only": [e for e in episodes_ if c1_type(e) and e["model"] in weak and e["group"] == "round2" and e["seed"] in (1, 2)],
        "PRIMARY, round-2 CONTROL extra seeds only": [e for e in episodes_ if c1_type(e) and e["model"] in weak and e["group"] == "round2" and e["seed"] not in (1, 2)],
    }
    results, primary_rows = {}, None
    for label, eps in populations.items():
        results[label], rows = summarize(label, eps)
        if label.startswith("PRIMARY: "):
            primary_rows = rows
    primary = results["PRIMARY: C1-type, bonsai+lfm3"]
    # bar evaluation (thresholds fixed in PROTOCOL_STEP1.md)
    n = primary["b2_denominator"]
    counts = primary["b2_classes"]
    pointed = counts.get("pointed_immediate", 0) + counts.get("pointed_delayed", 0)
    fires_n = primary["fires"]
    informative_n = primary["fire_types"].get("informative", 0)
    bars = {
        "B0 reproduction": b0["pass_"],
        "B1 >=10% episodes with informative fire": primary["episodes_with_informative_fire"] / primary["episodes"] >= 0.10,
        "B2 >=50% pointed (strict)": n >= 15 and pointed / n >= 0.50,
        "B3 >=30% of pointed are delayed": pointed > 0 and counts.get("pointed_delayed", 0) / pointed >= 0.30,
        "B4 <=25% contradicted": n >= 15 and counts.get("contradicted", 0) / n <= 0.25,
        "B5 >=50% of fires informative": fires_n > 0 and informative_n / fires_n >= 0.50,
    }
    inconclusive = n < 15
    verdict = "INCONCLUSIVE (treated as FAIL)" if inconclusive else ("PASS" if all(bars.values()) else "FAIL")
    # samples: first fire of each type per (type, kind_mismatch) in fixed episode order
    samples, seen = [], set()
    for e in populations["all arms, all models"]:
        for f in e["fires"]:
            key = (f["type"], f["kind_mismatch"], bool(f["suggested"]))
            if key not in seen and len(samples) < 20:
                seen.add(key)
                samples.append(dict(trace_path=e["trace_path"], request=f["request"], tool=f["tool"], args=f["args"], type=f["type"], kind_mismatch=f["kind_mismatch"], text=f["text"]))
    contradicted = [dict(trace_path=e["trace_path"], model=e["model"], task=e["task"], seed=e["seed"], fire_request=f["request"], hint_names=f["shown"], hint_tools=f["suggested"],
                         p_request=p["request"], p_tool=p["tool"], p_entities=p["entities"]) for e, f, p, c in primary_rows if c == "contradicted"]
    report = dict(mode="POST-HOC SENSITIVITY: hint content from clean ledger; not the frozen verdict" if clean_mode else "frozen protocol", protocol_sha256=(HERE / "PROTOCOL_STEP1.sha256").read_text().split()[0], B0=b0, mismatches=mismatches[:20], errors=errors[:10],
                  results=results, bars=bars, verdict=verdict, samples=samples, contradicted_primary=contradicted)
    (HERE / f"step1_results{suffix}.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    (HERE / f"step1_fires{suffix}.jsonl").write_text("".join(json.dumps(dict(trace_path=e["trace_path"], group=e["group"], arm=e["arm"], model=e["model"], task=e["task"], seed=e["seed"],
                                                                   supported=e["supported"], fires=e["fires"]), default=str) + "\n" for e in episodes_ if e["fires"]))
    print(json.dumps(dict(B0=b0, bars=bars, verdict=verdict, primary=primary), indent=2, default=str))


if __name__ == "__main__":
    main()
