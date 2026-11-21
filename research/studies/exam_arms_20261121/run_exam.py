"""Runner adapter of the Stage 1 exam arms (exam_arms.py): the three hooks the exam queue needs, `run_worker`, `episode_row` and the `episode` command line.
Everything except the arm is the dev ablation runner's (run_ablation.py): pilot settings, 90 s HTTP timeout, 40 iterations, round 2's oracle with 5 s retry.
Task and environment loading reuse the thinking runner's (stage3, e1h and the name-fix fixture) and its TASKS table, i.e. DEVELOPMENT tasks only: a task id outside that table
(for example a held-out task) stops with a clear error. The custodian's held-out adapter is NOT built here (freeze-prep item 9d-1 belongs to Codex).

  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python research/studies/exam_arms_20261121/run_exam.py run smoke OUTDIR     (2 dev episodes, label: smoke, not scores)
  uv run python research/studies/exam_arms_20261121/run_exam.py plan smoke
Row additions beyond the thinking runner's row: supported_raw / exact_raw (scorer v2.0 on the answer as the model submitted it), name_fix_changed, and the raw answer.
"""
import hashlib
import json
import os
import random
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDIES / "thinking_escalation_20261119"))
import exam_arms  # noqa: E402
import run_think as T  # noqa: E402
import run_pilot  # noqa: E402
import run_round2  # noqa: E402

MASTER_SEED = 20261121
EPISODE_TIMEOUT_SECONDS = 900  # protocol section 3 (the thinking runner's 1800 s was for thinking requests)
load_env = T.load_env


def plan_for(phase):
    """Only `smoke` exists: qwen3.5:9b, one cell of NO_ERRORTEXT on u3 and one of M on nf_single_1 (the rewrite fires there in dev). The exam plan comes from the exam spec, not from here."""
    assert phase == "smoke", phase
    sessions = {}
    for env, task, arm in (("stage3", "u3", "NO_ERRORTEXT"), ("namefix", "nf_single_1", "M")):
        sessions[f"qwen3.5_9b-{env}"] = [dict(env=env, task=task, arm=arm, model="qwen3.5:9b", seed=1, temperature=0.7)]
    return sessions


def run_worker(out, directory, cell, timeout, recorder):
    timeout = EPISODE_TIMEOUT_SECONDS
    command = [sys.executable, str(HERE / "run_exam.py"), "episode", "--output", str(directory), "--env", cell["env"], "--task", cell["task"],
               "--arm", cell["arm"], "--model", cell["model"], "--seed", str(cell["seed"]), "--temperature", str(cell["temperature"])]
    recorder.add("worker_start", command=command)
    started, error = time.perf_counter(), None
    with (out / (directory.name + ".worker.log")).open("w") as log:
        worker = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = worker.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(worker.pid, signal.SIGTERM)
            try:
                worker.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(worker.pid, signal.SIGKILL)
                worker.wait()
            code, error = worker.returncode, f"{timeout}-second episode timeout"
    record = dict(directory=directory.name, returncode=code, error=error, seconds=time.perf_counter() - started, cell=cell)
    with (out / "attempts.jsonl").open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    print(json.dumps(record), flush=True)
    return record


def episode(args):
    run_pilot.make_arm = exam_arms.make_arm
    run_pilot.load_env = load_env
    run_pilot.episode(args)


def episode_row(phase, session, directory, attempt):
    """The thinking runner's row plus the raw-answer score. A task id that is not a development task raises KeyError with the id."""
    row = T.episode_row(phase, session, directory, attempt)
    events = exam_arms.v2.s1.read_events(directory / "trace.jsonl")
    both = exam_arms.score_both(T.TASKS[row["task"]], events)
    originals = [e for e in events if e["kind"] == "final_answer_original"]
    changed = [e for e in events if e["kind"] == "handler" and e.get("event") == "namefix" and e.get("changed")]
    row.update(supported_raw=both["raw"]["supported_complete"], exact_raw=both["raw"]["exact"], answer_raw=both["raw"]["answer_object"],
               name_fix_changed=bool(changed), final_answer_original_logged=bool(originals))
    return row


def collect(run, phase, log_path):
    run = Path(run).resolve()
    added = 0
    with Path(log_path).open("a") as handle:
        for session in sorted(p for p in run.iterdir() if p.is_dir() and (p / "attempts.jsonl").exists()):
            for line in (session / "attempts.jsonl").read_text().splitlines():
                attempt = json.loads(line)
                directory = session / attempt["directory"]
                if (directory / "trace.jsonl").exists():
                    handle.write(json.dumps(episode_row(phase, f"{run.name}/{session.name}", directory, attempt), default=str) + "\n")
                    added += 1
    print(f"wrote {added} rows to {log_path}", flush=True)


def run(phase, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    plan = plan_for(phase)
    (out / "plan_all.json").write_text(json.dumps(plan, indent=1))
    run_pilot.run_worker = run_worker
    original_load_env = load_env
    run_pilot.load_env = lambda name: run_round2.OracleWithRetry(original_load_env(name))
    for name, cells in plan.items():
        path = out / f"plan_{name}.json"
        path.write_text(json.dumps(cells, indent=1))
        run_pilot.session(out / name, path, wall_limit_hours=1.0)
    collect(out, phase, out / "SMOKE_ROWS.jsonl")


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "plan":
        print({k: len(v) for k, v in plan_for(sys.argv[2]).items()})
    elif command == "run":
        run(sys.argv[2], sys.argv[3])
    elif command == "episode":
        import argparse
        parser = argparse.ArgumentParser()
        for flag in ["--output", "--env", "--task", "--arm", "--model", "--temperature"]:
            parser.add_argument(flag, required=True)
        parser.add_argument("--seed", type=int, required=True)
        a = parser.parse_args(sys.argv[2:])
        a.temperature = float(a.temperature)
        episode(a)
