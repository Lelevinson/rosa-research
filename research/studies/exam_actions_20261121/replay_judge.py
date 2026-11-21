"""Replay of action judge v1.2 on the 128 development action episodes (action_dev_switch_20261118, phase full) with the final answer in several FORMS: the same facts as an object, wrapped
({"answer": object}), a JSON string, a wrapped JSON string, and prose around a JSON object. Wrapped, string and object answers of the same facts must score identically.
Read-only on the dev traces (ignored `_artifacts`); no ROS, no model. Output: replay_judge_results.json and the table printed (also in REPORT).
  uv run python research/studies/exam_actions_20261121/replay_judge.py
`ending` is the recorded ending of the episode: a structured final_answer call has ending "final_answer"; a free-text answer has ending "text" (judge v1.1 applies the read scorer's last-object and
singleton-wrapper rule only to text answers)."""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(STUDIES / "action_dev_switch_20261118"))
import judge as v1  # noqa: E402
import judge_v1_1 as v11  # noqa: E402
import judge_v1_2 as v12  # noqa: E402
import judge_exam  # noqa: E402  (the exam's form-normalising wrapper around v1.2)


def canonical(answer, ending):
    """The answer object the episode gave, with one level of {"answer": obj} wrapping removed (None if there is none)."""
    if ending == "text" and isinstance(answer, str):
        answer = v11.parse_text_answer(answer)
    elif isinstance(answer, str):
        answer = v1.parse_answer(answer)
    if isinstance(answer, dict) and list(answer) == ["answer"] and isinstance(answer["answer"], dict):
        answer = answer["answer"]
    return answer if isinstance(answer, dict) else None


def forms(obj):
    """(form name, answer value, ending) for the same facts."""
    wrapped = {"answer": obj}
    return [("object", obj, "final_answer"), ("wrapped_object", wrapped, "final_answer"), ("json_string", json.dumps(obj), "text"), ("wrapped_json_string", json.dumps(wrapped), "text"),
            ("prose_around_json", "Done. The turtle ended up here: " + json.dumps(obj) + " Thanks.", "text"), ("prose_around_wrapped_json", "Final: " + json.dumps(wrapped), "text")]


def load_rows():
    rows = [json.loads(l) for l in (STUDIES / "action_dev_switch_20261118/RESULTS_LOG.jsonl").read_text().splitlines() if l.strip()]
    return [r for r in rows if r.get("phase") == "full"]


def main():
    rows, table, table_x = load_rows(), collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    disagreements, disagreements_x, as_recorded = [], [], collections.Counter()
    for row in rows:
        trace = [json.loads(l) for l in (ROOT / row["trace_path"]).read_text().splitlines()]
        args = (row["task"], None, row["true_heading"], row["true_x"], row["true_y"], row["turtle_still"])
        recorded = v12.judge(args[0], row["answer"], *args[2:], ending=row["ending"], trace=trace)
        as_recorded["v1.0 as scored in the study"] += row["success"]
        as_recorded["v1.2 on the recorded answer"] += recorded["success"]
        obj = canonical(row["answer"], row["ending"])
        verdicts, verdicts_x = {}, {}
        for name, value, ending in (forms(obj) if obj is not None else [("no_object", row["answer"], row["ending"])]):
            verdict = v12.judge(args[0], value, *args[2:], ending=ending, trace=trace)
            verdicts[name] = verdict["success"]
            table[name]["success"] += verdict["success"]
            table[name]["episodes"] += 1
            verdict_x = judge_exam.judge(args[0], value, *args[2:], ending=ending, trace=trace)
            verdicts_x[name] = verdict_x["success"]
            table_x[name]["success"] += verdict_x["success"]
            table_x[name]["episodes"] += 1
        if len(set(verdicts.values())) > 1:
            disagreements.append(dict(run_id=row["run_id"], task=row["task"], recorded_type=type(row["answer"]).__name__, verdicts=verdicts))
        if len(set(verdicts_x.values())) > 1:
            disagreements_x.append(dict(run_id=row["run_id"], verdicts=verdicts_x))
    out = dict(episodes=len(rows), as_recorded=dict(as_recorded), v12_direct_by_form={k: dict(v) for k, v in table.items()}, v12_direct_episodes_with_form_disagreement=len(disagreements),
               exam_wrapper_by_form={k: dict(v) for k, v in table_x.items()}, exam_wrapper_episodes_with_form_disagreement=len(disagreements_x), exam_wrapper_disagreements=disagreements_x)
    (HERE / "replay_judge_results.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "exam_wrapper_disagreements"}, indent=1))


if __name__ == "__main__":
    main()
