"""Tool-description compaction runner (PROTOCOL.md of this folder). Derived from run_compaction.py: same sessions, oracle, scoring and episode rows; only arms and plan differ.

  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python run_compaction.py plan  smoke|full
  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python run_compaction.py run   smoke|full OUTDIR [session names...]
  uv run python run_compaction.py collect OUTDIR PHASE
Design: 10 dev tasks x 4 models x seed 1 = 40 cells per arm x 2 arms (FULL, COMPACT) = 80 episodes; one fixture session per (model, environment) with all five arms of that session shuffled together
(master seed 20261121). Smoke: qwen3.5:9b, task u3 seed 1, both arms (2 episodes, not in totals). Pilot settings, round 2's amended oracle (daemon read, 5 s retry, raw log).
"""
import hashlib
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDIES / "build_round2_20261116"))
sys.path.insert(0, str(STUDIES / "steady_loop_ablation_20261117"))
import compaction_arm as ablation_arms  # noqa: E402  (arms FULL and COMPACT; also puts the pilot study on sys.path)
import ablation_arms as base_arms  # noqa: E402
harness = base_arms.harness
import run_pilot  # noqa: E402
import scorer_v2 as v2  # noqa: E402
import run_round2  # noqa: E402  (OracleWithRetry only)

REPO = HERE.parents[2]
LOG = HERE / "RESULTS_LOG.jsonl"
MASTER_SEED = 20261125
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
STAGE3_TASKS = ["u3", "p3", "h4", "v2"]
E1H_TASKS = ["e1h_amb_1", "e1h_amb_2", "e1h_abs_1", "e1h_abs_2", "e1h_chg_1", "e1h_chg_2"]
TASKS = {t["id"]: t for t in json.loads((STUDIES / "headroom_diagnostic_20261112/stage3_tasks.json").read_text())}
TASKS.update({t["id"]: t for t in json.loads((STUDIES / "small_model_harness_20261115/e1h_tasks.json").read_text())})


def plan_for(phase):
    sessions = {}
    for model in ([MODELS[1]] if phase == "smoke" else MODELS):
        for env, tasks in (("stage3", STAGE3_TASKS), ("e1h", E1H_TASKS)):
            if phase == "smoke":
                if env == "e1h":
                    continue
                tasks = ["u3"]
            cells = [dict(env=env, task=t, arm=a, model=model, seed=1, temperature=0.7) for t in tasks for a in ablation_arms.ARMS]
            random.Random(f"{MASTER_SEED}-{phase}-{model}-{env}").shuffle(cells)
            sessions[f"{model.replace(':', '_')}-{env}"] = cells
    return sessions


def run_worker(out, directory, cell, timeout, recorder):
    command = [sys.executable, str(HERE / "run_compaction.py"), "episode", "--output", str(directory), "--env", cell["env"], "--task", cell["task"],
               "--arm", cell["arm"], "--model", cell["model"], "--seed", str(cell["seed"]), "--temperature", str(cell["temperature"])]
    recorder.add("worker_start", command=command)
    import os, signal, subprocess, time
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
    run_pilot.make_arm = ablation_arms.make_arm
    run_pilot.episode(args)


def episode_row(phase, session, directory, attempt):
    trace = directory / "trace.jsonl"
    events = v2.s1.read_events(trace)
    start = next(e for e in events if e["kind"] == "episode_start")
    task = TASKS[start["task"]["id"]]
    scored = v2.score_events(task, events)
    metrics = v2.s1.episode_metrics(events)
    end = [e for e in events if e["kind"] == "episode_end"]
    aborts = [x for x in [attempt.get("error"), end[-1].get("error") if end else "no episode_end"] if x]
    if metrics.get("iteration_cap"):
        aborts.append("iteration limit")
    handler = [e for e in events if e["kind"] == "handler"]
    count = lambda name: sum(e["event"] == name for e in handler)
    tools_called = [e["name"] for e in events if e["kind"] == "tool_start"]
    exposure = dict(precheck_rejections=count("validation_error"), stock_validation_errors=count("stock_validation_error"), coercions=count("coercion"),
                    tool_exceptions=count("tool_exception"), blocked_write_attempts=count("blocked_write_tool"), tool_not_offered=count("tool_not_offered"),
                    ended_by_error=count("episode_ended_by_error"), final_answer_invalid=count("final_answer_invalid"),
                    final_answer_accepted=sum(e["kind"] == "final_answer_accepted" for e in events),
                    extra_tool_calls=sum(t not in harness.DOMAIN_TOOLS and t != "final_answer" for t in tools_called), tool_calls=len(tools_called))
    return dict(run_id=f"{session}/{directory.name}", phase=phase, env=start["env"], task=task["id"], arm=start["arm"], model=start["model"], seed=start["seed"],
                temperature=start["temperature"], prompt_sha256=start["prompt_sha256"], scorer=scored["scorer"], supported_complete=scored["supported_complete"],
                exact=scored["exact"], issues=scored["issues"], support_missing=scored["support_missing"], answer=scored["answer_object"], answer_source=scored["answer_source"],
                llm_requests=metrics["requests"], input_tokens=metrics["input_tokens"], output_tokens=metrics["output_tokens"], native_ops=metrics["native_ops"],
                wall_seconds=round(attempt["seconds"], 2), aborts=aborts, exposure=exposure, trace_path=str(trace.relative_to(REPO)), trace_hash=hashlib.sha256(trace.read_bytes()).hexdigest())


def collect(run, phase):
    run = Path(run).resolve()
    prefix = run.name + "/"  # episode directory names repeat between runs, so ids carry the run folder
    have = {json.loads(l)["run_id"] for l in LOG.read_text().splitlines()} if LOG.exists() else set()
    added = 0
    with LOG.open("a") as handle:
        for session in sorted(p for p in run.iterdir() if p.is_dir() and (p / "attempts.jsonl").exists()):
            for line in (session / "attempts.jsonl").read_text().splitlines():
                attempt = json.loads(line)
                run_id = f"{prefix}{session.name}/{attempt['directory']}"
                directory = session / attempt["directory"]
                if run_id in have or not (directory / "trace.jsonl").exists():
                    continue
                handle.write(json.dumps(episode_row(phase, prefix + session.name, directory, attempt), default=str) + "\n")
                added += 1
    print(f"added {added} episodes to {LOG.name}", flush=True)


def run(phase, out, only=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    plan = {k: v for k, v in plan_for(phase).items() if only is None or k in only}
    (out / "plan_all.json").write_text(json.dumps(plan, indent=1))
    run_pilot.run_worker = run_worker
    original_load_env = run_pilot.load_env
    run_pilot.load_env = lambda name: run_round2.OracleWithRetry(original_load_env(name))
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
