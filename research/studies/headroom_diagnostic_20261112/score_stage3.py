"""Offline scoring for Stage 3 (no inference, no ROS).

  uv run python score_stage3.py selftest         check scorer on the minimal-sequence transcripts
  uv run python score_stage3.py run RUNDIR       score a Stage 3 run directory -> RUNDIR/scores_3.json
"""
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor"))
sys.path.insert(0, str(HERE))
import baseline_audit as audit  # noqa: E402  (vendored, unchanged)
import score_stage1 as s1  # noqa: E402

TASKS = {t["id"]: t for t in json.loads((HERE / "stage3_tasks.json").read_text())}


def param_values(results):
    values = {}
    for r in results:
        if r["name"] == "ros2_param_get" and r["ok"] and isinstance(r["output"], dict):
            for param, raw in r["output"].items():
                m = re.search(r"(Boolean|Integer|String|Double) value is:\s*(.*)", str(raw))
                if m:
                    text = m[2].strip()
                    value = (text == "True") if m[1] == "Boolean" else int(text) if m[1] == "Integer" else float(text) if m[1] == "Double" else text
                    values[(r["args"].get("node_name"), r["args"].get("param_name", param))] = value
    return values


def support_missing(task, results):
    good = [r for r in results if r["ok"]]
    text = "\n".join(r["text"].replace("\\n", "\n") for r in good)
    known = s1.assembled(text)
    params = param_values(results)
    missing = []
    for req in task["support"]:
        if req[0] == "param":
            if params.get((req[1], req[2])) != req[3]:
                missing.append(f"param {req[1]} {req[2]}={req[3]!r} not read")
        elif req[1] not in text and req[1] not in known and req[1] not in task["request"]:
            missing.append(f"text {req[1]!r} not seen in a tool result")
    return missing


def score_answer(task, answer, results):
    parsed, _ = audit.first_object(answer)
    issues = audit.differences(audit.canonical(parsed), audit.canonical(task["answer"]))
    missing = support_missing(task, results)
    return dict(exact=not issues, issues=issues, support_missing=missing, supported_complete=(not issues and not missing))


def score_run(run):
    run = Path(run)
    rows = []
    for line in (run / "attempts.jsonl").read_text().splitlines():
        attempt = json.loads(line)
        directory = run / attempt["directory"]
        if not (directory / "trace.jsonl").exists():
            rows.append(dict(episode=attempt["directory"], status="no trace", returncode=attempt["returncode"], error=attempt["error"]))
            continue
        events = s1.read_events(directory / "trace.jsonl")
        start = next(e for e in events if e["kind"] == "episode_start")
        task = TASKS[start["task"]["id"]]
        metrics = s1.episode_metrics(events)
        graded = score_answer(task, metrics["answer"], s1.tool_results(events))
        rows.append(dict(episode=attempt["directory"], task=task["id"], template=task["template"], depth=task["depth"], floor=task["floor"],
                         provider=start["provider"], repeat=start["repeat"], pilot=attempt["directory"].startswith("pilot"),
                         excess=metrics["requests"] - task["floor"], timeout=bool(attempt["error"]), **graded, **metrics))
    return rows


def selftest():
    base = sorted((HERE.parents[1] / "_artifacts/runs/headroom_diagnostic_20261112").glob("stage3_floorcheck_*"))[-1]
    ok = True
    for task in TASKS.values():
        d = json.loads((base / f"minimal_{task['id']}.json").read_text())
        results = [dict(name=e["tool"], args=e["args"], output=e["result"], text=json.dumps(e["result"]), ok=True) for e in d["log"]]
        g = score_answer(task, json.dumps(d["answer"]), results)
        wrong = dict(d["answer"]); k = next(iter(wrong)); wrong[k] = "WRONG" if isinstance(wrong[k], str) else -1
        bad = score_answer(task, json.dumps(wrong), results)
        nosupport = score_answer(task, json.dumps(d["answer"]), [])
        ok &= g["supported_complete"] and not bad["exact"] and not nosupport["supported_complete"]
        print(task["id"], "minimal passes:", g["supported_complete"], "| wrong answer fails:", not bad["exact"], "| no trace fails support:", not nosupport["supported_complete"])
    print("SELFTEST OK" if ok else "SELFTEST FAILED")


if __name__ == "__main__":
    if sys.argv[1] == "selftest":
        selftest()
    else:
        rows = score_run(sys.argv[2])
        (Path(sys.argv[2]) / "scores_3.json").write_text(json.dumps(rows, indent=1, default=str))
        print("wrote", len(rows), "episode scores")
