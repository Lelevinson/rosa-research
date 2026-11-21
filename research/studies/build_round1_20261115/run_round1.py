"""Round 1 runner: plans, sessions, worker, and the append-only RESULTS_LOG.jsonl. Reuses the pilot's session/fixture/oracle code (run_pilot.py) unchanged.

  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python run_round1.py plan  smoke|full            write the plan (all cells, shuffled per model and environment)
  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python run_round1.py run   smoke|full OUTDIR      run every session of the plan, then collect
  uv run python run_round1.py collect OUTDIR PHASE                                                  append episodes of OUTDIR that are not in the log yet
  uv run python run_round1.py episode ...                                                           (internal) one episode in its own process

Same settings as the pilot: think false for all models (the pilot SDK default, reasoning=False), temperature 0.7, num_ctx 65536, num_predict 4096,
seeds 1 and 2, 40-iteration cap, one fixture session per (model, environment), ROS domain 220. All four arms of a model/environment are shuffled into
the same session, so they share fixture, daemon and model residency.
"""
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import round1_harness as r1  # noqa: E402  (also puts the pilot study on sys.path)
import run_pilot  # noqa: E402
import score_round1  # noqa: E402

REPO = HERE.parents[2]
LOG = HERE / "RESULTS_LOG.jsonl"
RUNS = REPO / "research/_artifacts/runs/build_round1_20261115"
MASTER_SEED = 20261117
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
STAGE3_TASKS = ["u3", "p3", "h4", "v2"]
E1H_TASKS = ["e1h_amb_1", "e1h_amb_2", "e1h_abs_1", "e1h_abs_2", "e1h_chg_1", "e1h_chg_2"]
SEEDS = [1, 2]
TEMPERATURE = 0.7
SMOKE_MODEL, SMOKE_TASKS = "qwen3.5:9b", {"stage3": ["h4"], "e1h": ["e1h_amb_1"]}
TASKS = {t["id"]: t for t in json.loads((HERE.parent / "headroom_diagnostic_20261112/stage3_tasks.json").read_text())}
TASKS.update({t["id"]: t for t in json.loads((HERE.parent / "small_model_harness_20261115/e1h_tasks.json").read_text())})


def plan_for(phase):
    """{session name: [cells]}; full = 10 tasks x 2 seeds x 4 models x 4 arms = 320 cells; smoke = 2 tasks x 1 model x 4 arms, seed 1."""
    sessions = {}
    for model in ([SMOKE_MODEL] if phase == "smoke" else MODELS):
        for env, tasks in (("stage3", STAGE3_TASKS), ("e1h", E1H_TASKS)):
            if phase == "smoke":
                tasks = SMOKE_TASKS[env]
            cells = [dict(env=env, task=t, arm=a, model=model, seed=s, temperature=TEMPERATURE)
                     for t in tasks for a in r1.ARMS for s in ([1] if phase == "smoke" else SEEDS)]
            random.Random(f"{MASTER_SEED}-{phase}-{model}-{env}").shuffle(cells)
            sessions[f"{model.replace(':', '_')}-{env}"] = cells
    return sessions


# ------------------------------------------------------------------ worker (one episode, own process)
def run_worker(out, directory, cell, timeout, recorder):
    command = [sys.executable, str(HERE / "run_round1.py"), "episode", "--output", str(directory), "--env", cell["env"], "--task", cell["task"],
               "--arm", cell["arm"], "--model", cell["model"], "--seed", str(cell["seed"]), "--temperature", str(cell["temperature"])]
    recorder.add("worker_start", command=command)
    started, error = time.perf_counter(), None
    with (out / (directory.name + ".worker.log")).open("w") as log:
        import os, signal
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
    run_pilot.make_arm = r1.make_arm
    run_pilot.ArmTracedModel = r1.Round1Model
    run_pilot.episode(args)


# ------------------------------------------------------------------ results log
def handler_events(events, names):
    return [{k: v for k, v in e.items() if k not in ("kind", "monotonic", "tool_run_id", "handler")} for e in events if e["kind"] == "handler" and e.get("event") in names]


def episode_row(phase, session, directory, attempt):
    trace = directory / "trace.jsonl"
    events = score_round1.v2.s1.read_events(trace)
    start = next(e for e in events if e["kind"] == "episode_start")
    task = TASKS[start["task"]["id"]]
    scored = score_round1.score_events(task, events)
    metrics = scored["metrics"]
    end = [e for e in events if e["kind"] == "episode_end"]
    aborts = [x for x in [attempt.get("error"), end[-1].get("error") if end else "no episode_end"] if x]
    if metrics.get("iteration_cap"):
        aborts.append("iteration limit")
    tool_calls = [e for e in events if e["kind"] == "tool_start"]
    list_calls = handler_events(events, {"list_call"})
    return dict(run_id=f"{session}/{directory.name}", phase=phase, env=start["env"], task=task["id"], arm=start["arm"], model=start["model"], seed=start["seed"],
                temperature=start["temperature"], scorer=scored["scorer"], supported_complete=scored["supported_complete"], exact=scored["exact"],
                issues=scored["issues"], support_missing=scored["support_missing"], answer=scored["answer_object"], answer_source=scored["answer_source"],
                llm_requests=metrics["requests"], input_tokens=metrics["input_tokens"], output_tokens=metrics["output_tokens"], native_ops=metrics["native_ops"],
                wall_seconds=round(attempt["seconds"], 2), aborts=aborts, tool_calls=len(tool_calls), list_calls=len(list_calls),
                list_items=sum(c["items"] for c in list_calls),
                gate=handler_events(events, {"gate_reject", "gate_followup", "gate_accepted_after_limit", "bare_text_nudge", "gate_shadow", "gate_pass"}),
                trace_path=str(trace.relative_to(REPO)), trace_hash=hashlib.sha256(trace.read_bytes()).hexdigest())


def collect(run, phase):
    run = Path(run).resolve()
    have = {json.loads(l)["run_id"] for l in LOG.read_text().splitlines()} if LOG.exists() else set()
    added = 0
    with LOG.open("a") as handle:
        for session in sorted(p for p in run.iterdir() if p.is_dir() and (p / "attempts.jsonl").exists()):
            for line in (session / "attempts.jsonl").read_text().splitlines():
                attempt = json.loads(line)
                run_id = f"{session.name}/{attempt['directory']}"
                directory = session / attempt["directory"]
                if run_id in have or not (directory / "trace.jsonl").exists():
                    continue
                handle.write(json.dumps(episode_row(phase, session.name, directory, attempt), default=str) + "\n")
                added += 1
    print(f"added {added} episodes to {LOG.name}")


def run(phase, out, only=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    plan = {k: v for k, v in plan_for(phase).items() if only is None or k in only}  # `only` lets a stopped run continue with the sessions that did not run
    (out / "plan_all.json").write_text(json.dumps(plan, indent=1))
    run_pilot.run_worker = run_worker
    try:
        for name, cells in plan.items():
            path = out / f"plan_{name}.json"
            path.write_text(json.dumps(cells, indent=1))
            print(json.dumps(dict(event="session_start", session=name, cells=len(cells))), flush=True)
            run_pilot.session(out / name, path, wall_limit_hours=6.0)
            collect(out, phase)
    finally:
        collect(out, phase)


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "plan":
        plan = plan_for(sys.argv[2])
        print({k: len(v) for k, v in plan.items()}, "total", sum(map(len, plan.values())))
    elif command == "run":
        run(sys.argv[2], sys.argv[3], sys.argv[4:] or None)
    elif command == "collect":
        collect(sys.argv[2], sys.argv[3])
    elif command == "episode":
        import argparse
        parser = argparse.ArgumentParser()
        for flag in ["--output", "--env", "--task", "--arm", "--model", "--temperature"]:
            parser.add_argument(flag, required=True)
        parser.add_argument("--seed", type=int, required=True)
        a = parser.parse_args(sys.argv[2:])
        a.temperature = float(a.temperature)
        episode(a)
