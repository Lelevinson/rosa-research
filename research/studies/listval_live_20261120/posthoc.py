"""POST HOC (written after the measurement data were opened; labelled as such in the report). Re-scores LISTVAL episodes counting a parameter value shown INLINE by `ros2_param_list` as a read, because scorer v2.0 only
credits `ros2_param_get` rows (`scorer_v2.param_values`), so a fact the model saw inline but did not re-fetch counts as 'not read'. FULL episodes are unchanged. The frozen class and totals are NOT replaced by these numbers.
  uv run python research/studies/listval_live_20261120/posthoc.py"""
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research/studies/candidate_counts_20261118"))
import count_candidates as CC  # noqa: E402
v2 = CC.v2


def typed(value):
    if value in ("True", "False"):
        return "Boolean"
    try:
        int(value)
        return "Integer"
    except ValueError:
        pass
    try:
        float(value)
        return "Double"
    except ValueError:
        return "String"


def inline_rows(trace_path):
    events = [json.loads(l) for l in (ROOT / trace_path).read_text().splitlines()]
    starts = {e["run_id"]: e for e in events if e["kind"] == "tool_start"}
    rows = []
    for e in events:
        if e["kind"] == "tool_end" and starts[e["run_id"]]["name"] == "ros2_param_list":
            args = ast.literal_eval(starts[e["run_id"]]["input"]) if isinstance(starts[e["run_id"]]["input"], str) else starts[e["run_id"]]["input"]
            out = e["output"]
            if not args.get("node_name") or not isinstance(out, dict):
                continue
            for node, entries in out.items():
                for entry in entries if isinstance(entries, list) else []:
                    if ": " in entry and not entry.endswith("<unreadable>"):
                        name, value = entry.split(": ", 1)
                        text = f"{typed(value)} value is: {value}\n"
                        rows.append(dict(name="ros2_param_get", args=dict(node_name=node, param_name=name), given_args=dict(node_name=node, param_name=name), output={name: text}, text=json.dumps({name: text}), ok=True, line=0))
    return rows


def main():
    tasks = CC.all_tasks()
    rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
    out = defaultdict(lambda: defaultdict(int))
    flips, still = [], []
    for row in rows:
        ep = CC.parse_episode("listval", row, tasks)
        supported = bool(ep["supported"])
        if row["arm"] == "LISTVAL":
            extra = inline_rows(row["trace_path"])
            sc = v2.score_task(ep["task_def"], ep["answer"], ep["rows"] + extra)
            supported_ph = bool(sc["supported_complete"])
            if supported_ph != supported:
                flips.append(dict(run_id=row["run_id"], model=row["model"], task=row["task"], trace=row["trace_path"]))
        else:
            supported_ph = supported
        out[row["arm"]][row["model"]] += supported_ph
        out[row["arm"]]["ALL"] += supported_ph
    result = dict(label="POST HOC, counted inline values as reads", supported={a: dict(v) for a, v in out.items()}, listval_rescued_episodes=len(flips), rescued=flips)
    (HERE / "posthoc.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result[k] for k in ("supported", "listval_rescued_episodes")}, indent=1))


if __name__ == "__main__":
    main()
