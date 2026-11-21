"""Analysis of the LISTVAL live test (protocol: PROTOCOL.md, section 3). Offline: reads the results log and saved traces only.

  uv run python research/studies/listval_live_20261120/analyze_listval.py [RESULTS_LOG_PATH]      (default: research/_artifacts/exam/listval/RESULTS_LOG_all.jsonl)
Writes results.json and TABLES.md next to this file (when run on the default path) and prints the class. A different path (for example the smoke log) writes results_<name>.json instead.
"""
import ast
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDIES = ROOT / "research/studies"
sys.path.insert(0, str(STUDIES / "candidate_counts_20261118"))
sys.path.insert(0, str(STUDIES / "name_fix_applied_20261117"))
import count_candidates as CC  # noqa: E402
import namefix_rule as rule  # noqa: E402
E, ag, v2 = CC.E, CC.ag, CC.v2
DEFAULT_LOG = ROOT / "research/_artifacts/exam/listval/RESULTS_LOG_all.jsonl"
LOSSMAP_LABELS = STUDIES / "loss_map_20261120/labelled_lossmap.jsonl"
REPLICATION_LOG = ROOT / "research/_artifacts/exam/thinking_replA2/RESULTS_LOG_all.jsonl"
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
METRICS = ["param_get_calls", "requests", "input_tokens", "output_tokens", "native_ops", "wall_seconds"]


def norm(name):
    return "/" + name.lstrip("/") if isinstance(name, str) else name


def trace_calls(trace_path):
    """(inline events, param_get calls): each as dicts with the request index (1-based; a tool call belongs to the request whose model_end precedes it)."""
    index, inline, gets, lists = 0, [], [], []
    for line in (ROOT / trace_path).read_text().splitlines():
        e = json.loads(line)
        if e["kind"] == "model_end":
            index += 1
        elif e["kind"] == "handler" and e.get("event") == "listval_inline" and e.get("params"):
            inline.append(dict(request=e["request"], node=norm(e["node"]), params=e["params"], unreadable=e.get("unreadable", 0)))
        elif e["kind"] == "tool_start":
            try:
                args = ast.literal_eval(e["input"]) if isinstance(e["input"], str) else e["input"]
            except (ValueError, SyntaxError):
                args = {}
            if e["name"] == "ros2_param_get":
                gets.append(dict(request=index, node=norm(args.get("node_name")), param=args.get("param_name")))
            elif e["name"] == "ros2_param_list" and args.get("node_name"):
                lists.append(dict(request=index, node=norm(args["node_name"])))
    return inline, gets, lists


def needed_params(task):
    return {(norm(f[1]), f[2]) for f in task["support"] if f[0] == "param"}


def primary(rows_listval, tasks):
    """Per model: shown instances, fetched instances (later param_get on the same node and parameter), excluding the scripted-change parameter in e1h_chg tasks."""
    out = {m: dict(inline_lists=0, shown=0, fetched=0, needed_shown=0, needed_fetched=0, lists_with_any_fetch=0, excluded_change_instances=0, unreadable=0) for m in MODELS}
    detail = []
    for row in rows_listval:
        task = tasks[row["task"]]
        inline, gets, _lists = trace_calls(row["trace_path"])
        change = task.get("change")
        change_key = (norm(change["node"]), change["param"]) if change else None
        needed = needed_params(task)
        o = out[row["model"]]
        for item in inline:
            o["inline_lists"] += 1
            o["unreadable"] += item["unreadable"]
            any_fetch = False
            for p in item["params"]:
                key = (item["node"], p)
                if key == change_key:
                    o["excluded_change_instances"] += 1
                    continue
                fetched = any(g["request"] > item["request"] and (g["node"], g["param"]) == key for g in gets)
                o["shown"] += 1
                o["fetched"] += fetched
                any_fetch |= fetched
                if key in needed:
                    o["needed_shown"] += 1
                    o["needed_fetched"] += fetched
            o["lists_with_any_fetch"] += any_fetch
            detail.append(dict(run_id=row["run_id"], request=item["request"], node=item["node"], shown=len(item["params"]), any_fetch=any_fetch))
    for m, o in out.items():
        o["share_fetched"] = round(o["fetched"] / o["shown"], 4) if o["shown"] else None
        o["share_needed_fetched"] = round(o["needed_fetched"] / o["needed_shown"], 4) if o["needed_shown"] else None
        o["share_lists_with_fetch"] = round(o["lists_with_any_fetch"] / o["inline_lists"], 4) if o["inline_lists"] else None
    return out, detail


def full_habit(rows_full):
    """(c) FULL arm: successful param_list calls with a node followed later by a param_get of that node."""
    per_model = {m: dict(lists=0, followed=0) for m in MODELS}
    for row in rows_full:
        _inline, gets, lists = trace_calls(row["trace_path"])
        for item in lists:
            per_model[row["model"]]["lists"] += 1
            per_model[row["model"]]["followed"] += any(g["request"] > item["request"] and g["node"] == item["node"] for g in gets)
    return per_model


def episode_metrics(row):
    _inline, gets, _lists = trace_calls(row["trace_path"])
    return dict(param_get_calls=len(gets), requests=row["llm_requests"], input_tokens=row["input_tokens"], output_tokens=row["output_tokens"], native_ops=row["native_ops"], wall_seconds=row["wall_seconds"])


def rewrite_supported(ep):
    answer = ep["answer"]
    if not isinstance(answer, dict) or not answer:
        return bool(ep["supported"])
    outputs = [u["output"] for r in ep["requests"] for u in r.get("units", [])]
    allowed = ag.allowed_names(ep["task_text"], outputs)
    rewritten = rule.rewrite_answer(answer, allowed, [])
    return bool(v2.score_task(ep["task_def"], rewritten, ep["rows"])["supported_complete"])


def paired(by_key, metric_values, models=MODELS):
    """difference LISTVAL - FULL over the cells (task, seed, model) that have both arms."""
    out = {}
    groups = {m: [] for m in models}
    for (model, task, seed), arms in by_key.items():
        if "FULL" in arms and "LISTVAL" in arms:
            groups[model].append(arms)
    groups["ALL"] = [a for m in models for a in groups[m]]
    for model, cells in groups.items():
        out[model] = {}
        for metric in metric_values:
            diffs = [c["LISTVAL"][metric] - c["FULL"][metric] for c in cells]
            out[model][metric] = dict(cells=len(diffs), mean_full=round(statistics.mean(c["FULL"][metric] for c in cells), 3) if cells else None,
                                      mean_listval=round(statistics.mean(c["LISTVAL"][metric] for c in cells), 3) if cells else None,
                                      mean_diff=round(statistics.mean(diffs), 3) if diffs else None, median_diff=statistics.median(diffs) if diffs else None,
                                      lower=sum(d < 0 for d in diffs), equal=sum(d == 0 for d in diffs), higher=sum(d > 0 for d in diffs))
    return out


def main():
    log_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LOG
    is_default = log_path == DEFAULT_LOG
    if is_default:
        import hashlib
        freeze = json.loads((HERE / "FREEZE_ANALYSIS.json").read_text())
        assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == freeze["analyze_listval_py_sha256"], "analyze_listval.py changed after the analysis freeze: report and re-run as a labelled revision"
    tasks = CC.all_tasks()
    rows = [json.loads(l) for l in log_path.read_text().splitlines() if l.strip()]
    eps = {}
    for row in rows:
        eps[row["run_id"]] = CC.parse_episode("listval", row, tasks)
    metrics = {r["run_id"]: episode_metrics(r) for r in rows}
    by_key = defaultdict(dict)
    for r in rows:
        m = dict(metrics[r["run_id"]], supported=int(bool(r["supported_complete"])), exact=int(bool(r["exact"])), rewrite_supported=int(rewrite_supported(eps[r["run_id"]])), no_answer=int(r["answer"] in (None, {}, "")))
        by_key[(r["model"], r["task"], r["seed"])][r["arm"]] = m
    arms = {a: [r for r in rows if r["arm"] == a] for a in ("FULL", "LISTVAL")}
    prim, detail = primary(arms["LISTVAL"], tasks)
    adoption_models = [m for m, o in prim.items() if o["inline_lists"] >= 5 and o["share_fetched"] is not None and o["share_fetched"] <= 0.5]
    adoption = len(adoption_models) >= 2
    totals = {a: dict(episodes=len(rs), supported=sum(bool(r["supported_complete"]) for r in rs), rewrite_supported=sum(by_key[(r["model"], r["task"], r["seed"])][a]["rewrite_supported"] for r in rs),
                      by_model={m: dict(episodes=sum(r["model"] == m for r in rs), supported=sum(bool(r["supported_complete"]) and r["model"] == m for r in rs),
                                        rewrite_supported=sum(by_key[(r["model"], r["task"], r["seed"])][a]["rewrite_supported"] for r in rs if r["model"] == m)) for m in MODELS}) for a, rs in arms.items()}
    pair = paired(by_key, METRICS + ["supported", "exact", "rewrite_supported", "no_answer"])
    # harm
    h1 = totals["LISTVAL"]["supported"] < totals["FULL"]["supported"] - 3
    h1_rewrite = totals["LISTVAL"]["rewrite_supported"] < totals["FULL"]["rewrite_supported"] - 3
    h2 = []
    for row in arms["LISTVAL"]:
        task = tasks[row["task"]]
        if not row["task"].startswith("e1h_chg") or not task.get("change"):
            continue
        change = task["change"]
        inline, _g, _l = trace_calls(row["trace_path"])
        shown = [i for i in inline if i["node"] == norm(change["node"]) and change["param"] in i["params"]]
        answer = row["answer"] if isinstance(row["answer"], dict) else {}
        final_keys = [k for k in answer if str(k).startswith("final_")]
        if shown and any(answer[k] == change["initial_value"] for k in final_keys):
            h2.append(dict(run_id=row["run_id"], model=row["model"], task=row["task"], trace=row["trace_path"], answer=answer, initial_value=change["initial_value"], new_value=change["new_value"]))
    # noise reference
    labels = [json.loads(l) for l in LOSSMAP_LABELS.read_text().splitlines()]
    replication = [json.loads(l) for l in REPLICATION_LOG.read_text().splitlines() if l.strip()] if REPLICATION_LOG.exists() else []
    noise = {m: dict(lossmap_requests_per_episode=round(statistics.mean(x["requests"] for x in labels if x["model"] == m), 3), lossmap_supported_rate=round(statistics.mean(x["supported"] for x in labels if x["model"] == m), 3),
                     replication_requests_per_episode=round(statistics.mean(x["llm_requests"] for x in replication if x["arm"] == "FULL" and x["model"] == m), 3) if replication else None,
                     replication_supported_rate=round(statistics.mean(bool(x["supported_complete"]) for x in replication if x["arm"] == "FULL" and x["model"] == m), 3) if replication else None,
                     this_run_full_requests_per_episode=round(statistics.mean(r["llm_requests"] for r in arms["FULL"] if r["model"] == m), 3) if any(r["model"] == m for r in arms["FULL"]) else None) for m in MODELS}
    lower_models = [m for m in MODELS if pair[m]["requests"]["mean_diff"] is not None and pair[m]["requests"]["mean_diff"] < 0]
    if h1 or h2:
        klass = "C"
    elif not adoption:
        klass = "B-"
    elif len(lower_models) >= 3:
        klass = "A"
    else:
        klass = "B"
    results = dict(log=str(log_path), episodes=len(rows), arms={a: len(rs) for a, rs in arms.items()}, cells_with_both_arms=sum(1 for v in by_key.values() if len(v) == 2),
                   primary=prim, adoption=dict(models_meeting=adoption_models, met=adoption, rule="share <= 0.5 in >= 2 models with >= 5 inline lists"), full_habit=full_habit(arms["FULL"]),
                   totals=totals, paired=pair, harm=dict(h1_supported_drop_gt3=h1, h1_rewrite_column=h1_rewrite, h2_pre_change_value_cases=h2),
                   request_lower_models=lower_models, noise_reference=noise, **{"class": klass},
                   listval_exposure=dict(inline_lists=sum(r["listval"]["inline_lists"] for r in arms["LISTVAL"]), shown_params=sum(r["listval"]["shown_params"] for r in arms["LISTVAL"]),
                                         over_cap=sum(r["listval"]["over_cap"] for r in arms["LISTVAL"]), unreadable=sum(r["listval"]["unreadable"] for r in arms["LISTVAL"]),
                                         full_arm_inline=sum(r["listval"]["inline_lists"] for r in arms["FULL"])),
                   aborts=dict(Counter(a for r in rows for a in r.get("aborts", []))))
    name = "results.json" if is_default else f"results_{log_path.parent.name}.json"
    (HERE / name).write_text(json.dumps(results, indent=1, default=str))
    print(json.dumps(dict(**{"class": klass}, adoption=results["adoption"], primary={m: (o["inline_lists"], o["share_fetched"]) for m, o in prim.items()}, totals={a: (t["supported"], t["rewrite_supported"]) for a, t in totals.items()},
                          requests_mean_diff={m: pair[m]["requests"]["mean_diff"] for m in pair}, harm=dict(h1=h1, h2=len(h2))), indent=1))


if __name__ == "__main__":
    main()
