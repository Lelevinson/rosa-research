"""STEP 1 of the round 2 brief: V1 trigger counts per task, per model and per tool, read from the offline replay.

The replay's own trigger code (offline_replay_20261116/replay.py, proposal1 variant V1) is run unchanged; only `sweep_set` is wrapped to note
which tool each real firing (non-empty sweep set) belongs to. The totals are checked against offline_replay_20261116/results.json.
  uv run python v1_counts.py   -> V1_COUNTS.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPLAY = HERE.parent / "offline_replay_20261116"
sys.path.insert(0, str(REPLAY))
import replay  # noqa: E402  (parses the 400 recorded episodes)

fired_tools = []
original_sweep_set = replay.sweep_set


def noting_sweep_set(group, exclude, tool):
    names = original_sweep_set(group, exclude, tool)
    if names:
        fired_tools.append(tool)  # proposal1 appends a trigger exactly when this list is non-empty
    return names


replay.sweep_set = noting_sweep_set
recorded = json.loads((REPLAY / "results.json").read_text())["episodes"]
by_run = {e["run_id"]: e for e in recorded}

per_task, per_model, per_tool, per_task_model, per_task_tool = Counter(), Counter(), Counter(), Counter(), Counter()
episodes_with = Counter()
total = total_eps = 0
for ep in replay.eps:
    fired_tools.clear()
    result = replay.proposal1(ep, "V1")
    assert result["triggers"] == len(fired_tools), (ep["run_id"], result["triggers"], fired_tools)
    assert result["triggers"] == by_run[ep["run_id"]]["p1_v1"]["triggers"], ep["run_id"]  # same as the stored replay result
    total += result["triggers"]
    if result["triggers"]:
        total_eps += 1
        episodes_with[(ep["task"])] += 1
    for tool in fired_tools:
        per_task[ep["task"]] += 1
        per_model[ep["model"]] += 1
        per_tool[tool] += 1
        per_task_model[f'{ep["task"]}|{ep["model"]}'] += 1
        per_task_tool[f'{ep["task"]}|{tool}'] += 1
assert (total, total_eps) == (31, 22), (total, total_eps)
enriched = sorted(per_task)
out = dict(triggers=total, episodes_with_trigger=total_eps, per_task=dict(per_task), per_model=dict(per_model), per_tool=dict(per_tool),
           per_task_model=dict(per_task_model), per_task_tool=dict(per_task_tool), episodes_with_trigger_per_task=dict(episodes_with),
           enriched_tasks=enriched, ros2_topic_echo_triggers=per_tool.get("ros2_topic_echo", 0),
           all_tasks=sorted({e["task"] for e in replay.eps}), replay_protocol_sha=json.loads((REPLAY / "results.json").read_text())["protocol_sha"])
(HERE / "V1_COUNTS.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
