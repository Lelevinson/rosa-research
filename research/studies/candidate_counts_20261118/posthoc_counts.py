"""POST HOC breakdowns, written after seeing the frozen counts (protocol section 4 says deviations and post-hoc items are labelled). Not part of the frozen bars.

Run from the repo root after count_candidates.py:  uv run python research/studies/candidate_counts_20261118/posthoc_counts.py
Reads the frozen outputs (needle_d.jsonl, fires_a.jsonl) and re-parses the same population for the repeated-call breakdown.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import count_candidates as C  # noqa: E402

out = {}
needles = [json.loads(l) for l in open(HERE / "needle_d.jsonl")]
d1 = [n for n in needles if n["kind"] == "D1"]
out["D1_total"] = len(d1)
out["D1_fact_located_in_a_result_text"] = sum(1 for n in d1 if n["longest_supplying_result_chars"] > 0)
out["D1_fact_not_located_by_text_search"] = sum(1 for n in d1 if n["longest_supplying_result_chars"] == 0)
located = [n for n in d1 if n["longest_supplying_result_chars"] > 0]
out["D1_located_by_model"] = dict(Counter(n["model"] for n in located))
out["D1_located_long"] = sum(1 for n in located if n["long"])
out["D1_located_chars_buckets_1000"] = dict(sorted(Counter(n["longest_supplying_result_chars"] // 1000 for n in located).items()))
out["D1_issue_kinds"] = dict(Counter(re.sub(r"[\d./_A-Za-z]+", "", (n["issues"][0] if n["issues"] else ""))[:40] or (n["issues"][0][:40] if n["issues"] else "") for n in d1).most_common(8))
out["D1_first_issue_examples"] = [n["issues"][:2] for n in d1[:6]]

fires = [json.loads(l) for l in open(HERE / "fires_a.jsonl")]
out["a_distinct_task_model_pairs"] = len({(f["task"], f["model"]) for f in fires})
out["a_distinct_task_model_pairs_by_model"] = dict(Counter(m for _, m in {(f["task"], f["model"]) for f in fires}))
agree = [f for f in fires if f["verdict"] == "agree"]
out["a_agree_sum_request_distance"] = sum(f["request_distance"] for f in agree)
out["a_agree_distance_distribution"] = dict(sorted(Counter(f["request_distance"] for f in agree).items()))
out["a_tasks_with_fires"] = dict(Counter(f["task"] for f in fires).most_common(12))
out["a_typed_examples"] = [(f["typed"], f["resolution"]) for f in fires[:6]]

tasks = C.all_tasks()
C.PILOT_SCORES = {}
requests_total = Counter()
repeat = Counter()
repeat_by_tool = Counter()
repeat_same_text = Counter()
repeat_consecutive = Counter()
repeat_examples = []
for study, row in C.load_population():
    ep = C.parse_episode(study, row, tasks)
    requests_total[ep["model"]] += len(ep["requests"])
    requests_total["ALL"] += len(ep["requests"])
    first = {}
    previous_key = None
    for request in ep["requests"]:
        for unit in request.get("units", []):
            if unit["harness_error"] or not unit["ok"] or unit["tool"] == "final_answer":
                previous_key = None
                continue
            key = (unit["tool"], json.dumps(unit["args"], sort_keys=True, default=str))
            if key in first:
                same = first[key] == unit["text"]
                for model in (ep["model"], "ALL"):
                    repeat[model] += 1
                    repeat_same_text[model] += int(same)
                    repeat_consecutive[model] += int(previous_key == key)
                repeat_by_tool[unit["tool"]] += 1
                if len(repeat_examples) < 3:
                    repeat_examples.append(ep["row"]["trace_path"])
            first.setdefault(key, unit["text"])
            previous_key = key
out["requests_total_by_model"] = dict(requests_total)
out["repeated_ok_call_by_model"] = dict(repeat)
out["repeated_ok_call_same_result_text"] = dict(repeat_same_text)
out["repeated_ok_call_in_consecutive_units"] = dict(repeat_consecutive)
out["repeated_ok_call_by_tool"] = dict(repeat_by_tool.most_common())
out["repeated_ok_call_examples"] = repeat_examples
(HERE / "posthoc.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str)[:3500])
