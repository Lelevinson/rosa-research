"""Fresh FULL arm map (definitions: FULL_ARM_MAP_DEFINITIONS.md, fixed before any number was computed on the ablation's FULL arm). Offline, from saved traces.
  uv run python full_arm_map.py ablation   -> FULL_ARM_MAP.json, FULL_ARM_MAP_TABLES.md   (the fresh FULL arm of the ablation, phase full)
  uv run python full_arm_map.py round1     -> a test run on round 1's control traces (output only printed)"""
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
REPO = HERE.parents[2]
sys.path.insert(0, str(STUDIES / "offline_replay_20261116"))
import episodes as E  # noqa: E402

ag = E.ag
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
LIST_TOOLS = {"ros2_node_list", "ros2_topic_list", "ros2_service_list"}
NO_INFO_TOOLS = {"wait", "set_debugging", "set_verbosity"}
CLASSES = ["FIN", "ERR", "REC", "RED", "NAME", "BATCH", "OTHER"]
tasks = E.load_tasks()


# ------------------------------------------------------------------ (a) input split
def token_split(row):
    """Per-request exact split (fixed / history / new) and the characters of the fixed part from request 1's model_start event."""
    events = [json.loads(l) for l in (REPO / row["trace_path"]).read_text().splitlines()]
    inputs = [(e.get("usage") or {}).get("input_tokens", 0) for e in events if e["kind"] == "model_end"]
    outputs = [(e.get("usage") or {}).get("output_tokens", 0) for e in events if e["kind"] == "model_end"]
    if not inputs:  # the first request never returned (backend crash): no usage to split
        return [], dict(system=0, schemas=0, task=0), {}
    first = next(e for e in events if e["kind"] == "model_start")
    system_chars = sum(len(m["content"]) for m in first["messages"] if m.get("type") == "system")
    task_chars = sum(len(m["content"]) for m in first["messages"] if m.get("type") == "human")
    schema_chars = len(json.dumps(first["schemas"]))
    fixed = inputs[0]
    parts = []
    for k, value in enumerate(inputs):
        if k == 0:
            parts.append(dict(request=1, input=value, fixed=value, history=0, new=0, output=outputs[k]))
        else:
            parts.append(dict(request=k + 1, input=value, fixed=fixed, history=inputs[k - 1] - fixed, new=value - inputs[k - 1], output=outputs[k]))
    total_chars = system_chars + schema_chars + task_chars
    estimate = dict(system=fixed * system_chars / total_chars, schemas=fixed * schema_chars / total_chars, task=fixed * task_chars / total_chars)
    return parts, estimate, dict(system_chars=system_chars, schema_chars=schema_chars, task_chars=task_chars)


# ------------------------------------------------------------------ (b) request classes
def call_key(c):
    return (c["tool"], json.dumps(c["args"], sort_keys=True), c["entity"])


def classify(ep):
    """One class per request (first rule that applies). Returns [(request index, class)]."""
    task_names = set(ag.names_in_text(ep["task_text"]))
    known_after = {0: set(task_names)}  # names known after the results of requests <= r
    seen_names = set(task_names)
    for index, call, new in E.ledger_events(ep)[0]:
        seen_names |= new
        known_after[index] = set(seen_names)
    for r in range(1, len(ep["requests"]) + 1):
        known_after.setdefault(r, known_after[max(k for k in known_after if k < r)])
    succeeded, out, previous_failed_tools = set(), [], set()
    for request in ep["requests"]:
        k, calls = request["index"], request["calls"]
        failed_tools = {c["tool"] for c in calls if not c["ok"] and c["tool"] != "final_answer"}
        if not calls:
            label = "OTHER"
        elif any(c["tool"] == "final_answer" and str(c["output"]).startswith("Answer recorded") for c in calls):  # the parser's `ok` is false for this harness text
            label = "FIN"
        elif all(not c["ok"] for c in calls):
            label = "ERR"
        elif previous_failed_tools & {c["tool"] for c in calls}:
            label = "REC"
        elif all(c["tool"] in NO_INFO_TOOLS or (c["ok"] and call_key(c) in succeeded) for c in calls):
            label = "RED"
        elif all(c["tool"] in LIST_TOOLS and c["args"].get("pattern") for c in calls):
            label = "NAME"
        elif k >= 2 and all(c["entity"] is not None and c["entity"] in known_after[k - 2] for c in calls):
            label = "BATCH"
        else:
            label = "OTHER"
        out.append((k, label))
        for c in calls:
            if c["ok"] and c["tool"] != "final_answer":
                succeeded.add(call_key(c))
        previous_failed_tools = failed_tools
    return out


# ------------------------------------------------------------------ driver
def load(source):
    if source == "ablation":
        log = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
        return [r for r in log if r["phase"] == "full" and r["arm"] == "FULL"]
    return [r for g, r in E.run_rows() if g == "round 1 control"]


def main(source):
    rows = load(source)
    eps, splits = [], {}
    for r in rows:
        ep = E.parse("round 2", r, tasks)
        ep["row"] = r
        eps.append(ep)
        splits[r["run_id"]] = token_split(r)
    result = dict(source=source, episodes=len(eps), growth={}, totals={}, classes={}, floor={}, unsupported=[])
    # (a) growth and totals
    for key in ["all"] + MODELS:
        sub = [e for e in eps if key == "all" or e["model"] == key]
        by_k = defaultdict(list)
        total = Counter()
        est = Counter()
        for e in sub:
            parts, estimate, chars = splits[e["run_id"]]
            for p in parts:
                by_k[p["request"]].append(p)
                for f in ("input", "fixed", "history", "new", "output"):
                    total[f] += p[f]
            for name, value in estimate.items():
                est[name] += value * len(parts)  # the fixed part is sent with every request
        result["growth"][key] = {str(k): dict(n=len(v), input=statistics.mean(p["input"] for p in v), fixed=statistics.mean(p["fixed"] for p in v), history=statistics.mean(p["history"] for p in v),
                                              new=statistics.mean(p["new"] for p in v), output=statistics.mean(p["output"] for p in v)) for k, v in sorted(by_k.items())}
        result["totals"][key] = dict(episodes=len(sub), requests=sum(len(e["requests"]) for e in sub), **dict(total), fixed_estimated_split={k: round(v) for k, v in est.items()})
    # (b) classes
    for key in ["all"] + MODELS:
        sub = [e for e in eps if key == "all" or e["model"] == key]
        count, tokens = Counter(), Counter()
        floors = excess = requests = 0
        for e in sub:
            floor = e["task_def"]["floor"]
            labels = classify(e)
            requests += len(e["requests"])
            floors += floor
            excess += len(e["requests"]) - floor
            for (k, label), request in zip(labels, e["requests"]):
                count[label] += 1
                tokens[label] += request["input_tokens"] + request["output_tokens"]
        avoidable = sum(count[c] for c in ("ERR", "REC", "RED", "NAME", "BATCH"))
        result["classes"][key] = dict(requests=requests, floor=floors, excess=excess, counts=dict(count), tokens=dict(tokens), avoidable_classes=avoidable)
    by_task = {}
    for t in sorted({e["task"] for e in eps}):
        sub = [e for e in eps if e["task"] == t]
        count = Counter(label for e in sub for _, label in classify(e))
        by_task[t] = dict(episodes=len(sub), requests=sum(len(e["requests"]) for e in sub), floor=sum(e["task_def"]["floor"] for e in sub), counts=dict(count))
    result["classes_by_task"] = by_task
    # (c) unsupported cells
    for e in eps:
        r = e["row"]
        if not r["supported_complete"]:
            result["unsupported"].append(dict(run_id=r["run_id"], model=r["model"], task=r["task"], seed=r["seed"], requests=len(e["requests"]), floor=e["task_def"]["floor"], issues=r["issues"],
                                              support_missing=r["support_missing"], aborts=r["aborts"], answer=r["answer"], trace=r["trace_path"], labels=[l for _, l in classify(e)]))
    return result


def tables(result):
    L = [f"# FULL arm map ({result['source']}, {result['episodes']} episodes; generated by full_arm_map.py)", "", "## (a) Input tokens by part (reported prompt tokens; fixed = request 1, new = increase since the previous request, history = the rest)",
         "| model | episodes | requests | input tokens | fixed (system+schemas+task) re-sent | history re-sent | new content | output tokens | fixed share | history share | new share |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for key in ["all"] + MODELS:
        t = result["totals"][key]
        L.append(f"| {key} | {t['episodes']} | {t['requests']} | {t['input']:,} | {t['fixed']:,} | {t['history']:,} | {t['new']:,} | {t['output']:,} | {t['fixed'] / t['input']:.0%} | {t['history'] / t['input']:.0%} | {t['new'] / t['input']:.0%} |")
    L += ["", "Estimated split of the fixed part (characters-proportional; ESTIMATE), tokens summed over all requests: " + json.dumps({k: v["fixed_estimated_split"] for k, v in result["totals"].items()}), "",
          "### Input tokens per request by step (all models): mean over the episodes that reached the step", "| request | episodes | input | fixed | history | new | output |", "|---:|---:|---:|---:|---:|---:|---:|"]
    for k, v in result["growth"]["all"].items():
        if int(k) <= 14:
            L.append(f"| {k} | {v['n']} | {v['input']:,.0f} | {v['fixed']:,.0f} | {v['history']:,.0f} | {v['new']:,.0f} | {v['output']:,.0f} |")
    L += ["", "### Same, per model (input tokens at request 1 / 3 / 5 / 8 / 12, n episodes reaching it)", "| model | 1 | 3 | 5 | 8 | 12 |", "|---|---|---|---|---|---|"]
    for m in MODELS:
        g = result["growth"][m]
        L.append(f"| {m} | " + " | ".join(f"{g[str(k)]['input']:,.0f} (n={g[str(k)]['n']})" if str(k) in g else "-" for k in (1, 3, 5, 8, 12)) + " |")
    L += ["", "## (b) Requests above the floor, by mechanical class", "| group | requests | floor | excess | " + " | ".join(CLASSES) + " | avoidable classes (ERR+REC+RED+NAME+BATCH) |", "|---|---:|---:|---:|" + "---:|" * len(CLASSES) + "---:|"]
    for key in ["all"] + MODELS:
        c = result["classes"][key]
        L.append(f"| {key} | {c['requests']} | {c['floor']} | {c['excess']} | " + " | ".join(str(c["counts"].get(x, 0)) for x in CLASSES) + f" | {c['avoidable_classes']} |")
    L += ["", "Tokens of the requests of each class (their own input+output, all models): " + json.dumps(result["classes"]["all"]["tokens"]), "", "| task | episodes | requests | floor | " + " | ".join(CLASSES) + " |", "|---|---:|---:|---:|" + "---:|" * len(CLASSES)]
    for t, c in result["classes_by_task"].items():
        L.append(f"| {t} | {c['episodes']} | {c['requests']} | {c['floor']} | " + " | ".join(str(c["counts"].get(x, 0)) for x in CLASSES) + " |")
    L += ["", f"## (c) Unsupported cells: {len(result['unsupported'])} (cause lines are added by hand in REPORT.md)"]
    for u in result["unsupported"]:
        L.append(f"- {u['run_id']} ({u['model']}, {u['task']}): {u['requests']} requests (floor {u['floor']}); issues {u['issues']}; missing {u['support_missing']}; aborts {u['aborts']}")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    source = sys.argv[1]
    result = main(source)
    text = tables(result)
    if source == "ablation":
        (HERE / "FULL_ARM_MAP.json").write_text(json.dumps(result, indent=1, default=str))
        (HERE / "FULL_ARM_MAP_TABLES.md").write_text(text)
    print(text)
