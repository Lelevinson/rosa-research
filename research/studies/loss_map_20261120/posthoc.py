"""Post-hoc checks written AFTER the measurement data were opened and the frozen classifier had run (labelled as such in the report; they do not change any frozen number).
  uv run python research/studies/loss_map_20261120/posthoc.py
(1) serial_batchable requests that are only a retry of the tool of an immediately preceding harness-rejected (format) request: found by hand reading 14 random serial_batchable requests (4 of 14).
(2) how the 'serial_batchable' and 'repeat' counts split by model after removing those retries."""
import json, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import classify as C
rows = {r["trace_path"]: r for r in C.load_rows("lossmap")}
eps = [json.loads(l) for l in (HERE / "labelled_lossmap.jsonl").read_text().splitlines()]
tasks = C.all_tasks()
retry, total = collections.Counter(), collections.Counter()
examples = collections.defaultdict(list)
for e in eps:
    ep = C.E.parse("l", rows[e["trace_path"]], tasks)
    for i, kind in enumerate(e["request_types"]):
        if kind != "serial_batchable":
            continue
        total[e["model"]] += 1
        prev = ep["requests"][i - 1]
        if e["request_types"][i - 1] == "format" and {c["tool"] for c in ep["requests"][i]["calls"]} <= {c["tool"] for c in prev["calls"]}:
            retry[e["model"]] += 1
            if len(examples[e["model"]]) < 3:
                examples[e["model"]].append(e["trace_path"])
out = dict(serial_batchable_total=dict(total), of_which_retry_of_rejected_call=dict(retry), examples=dict(examples))
(HERE / "posthoc.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))

# ---------------------------------------------------------------- further post-hoc counts for the report's open search (also written after the data were opened)
extra = {}
excess_total = sum(e["excess"] for e in eps)
extra["excess_in_supported_episodes"] = sum(e["excess"] for e in eps if e["supported"])
extra["excess_in_unsupported_episodes"] = sum(e["excess"] for e in eps if not e["supported"])
extra["episodes_with_excess_supported"] = sum(1 for e in eps if e["supported"] and e["excess"] > 0)
extra["episodes_supported"] = sum(1 for e in eps if e["supported"])
ranked = sorted(eps, key=lambda e: -e["excess"])
extra["top_10_percent_episodes_share_of_excess"] = round(sum(e["excess"] for e in ranked[:len(ranked) // 10]) / excess_total, 3)
extra["episodes_with_30plus_requests"] = [(e["model"], e["task"], e["seed"], e["requests"], e["supported"]) for e in eps if e["requests"] >= 30]
extra["excess_of_those_episodes"] = sum(e["excess"] for e in eps if e["requests"] >= 30)
by_task = collections.Counter()
for e in eps:
    by_task[e["task"]] += e["excess"]
extra["excess_by_task_top5"] = by_task.most_common(5)
cell = collections.Counter()
for e in eps:
    cell[(e["model"], e["task"])] += e["excess"]
extra["excess_by_model_task_top6"] = [(f"{m}|{t}", n) for (m, t), n in cell.most_common(6)]
extra["wall_seconds_by_model"] = {m: round(sum(e["wall_seconds"] or 0 for e in eps if e["model"] == m)) for m in sorted({e["model"] for e in eps})}
extra["input_tokens_by_model"] = {m: sum(e["input_tokens"] or 0 for e in eps if e["model"] == m) for m in sorted({e["model"] for e in eps})}
extra["input_tokens_in_episodes_with_30plus_requests"] = sum(e["input_tokens"] or 0 for e in eps if e["requests"] >= 30)
extra["input_tokens_total"] = sum(e["input_tokens"] or 0 for e in eps)
# param_list followed by param_get on the same node (an extra step if the floor assumes a direct get)
list_then_get = collections.Counter(); lists = collections.Counter()
for e in eps:
    ep = C.E.parse("l", rows[e["trace_path"]], tasks)
    gets = set()
    seen_lists = []
    for r in ep["requests"]:
        for c in r["calls"]:
            if c["tool"] == "ros2_param_list" and c["ok"]:
                seen_lists.append((r["index"], c["entity"]))
                lists[e["model"]] += 1
            if c["tool"] == "ros2_param_get" and c["ok"]:
                gets.add((r["index"], c["entity"]))
    for idx, ent in seen_lists:
        if any(g_ent == ent and g_idx > idx for g_idx, g_ent in gets):
            list_then_get[e["model"]] += 1
extra["param_list_calls_by_model"] = dict(lists)
extra["param_list_followed_later_by_param_get_same_node"] = dict(list_then_get)
extra["requests_that_batch_two_or_more_calls_by_model"] = {m: sum(e["batched_requests"] for e in eps if e["model"] == m) for m in sorted({e["model"] for e in eps})}
out["extra"] = extra
(HERE / "posthoc.json").write_text(json.dumps(out, indent=1))
print(json.dumps(extra, indent=1))
