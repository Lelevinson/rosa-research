"""Thinking-escalation runner (protocol: PROTOCOL.md in this folder, hash in PROTOCOL.sha256). Derived from repeat_finish_nudge_20261118/run_nudge.py.

  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python run_think.py plan  smoke|partA|partB   (amendment A1; "full" = all three arms together, no longer used)
  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python run_think.py run   smoke|full OUTDIR [session names...]
  uv run python run_think.py collect OUTDIR PHASE
Design: 10 dev tasks x 4 models x seeds 1-2 x 3 arms (FULL, ESCALATE, ALWAYS) = 240 episodes; one fixture session per (model, environment), arms and seeds of a session shuffled together (master seed 20261125).
Smoke: qwen3.5:9b and gpt-oss:20b, tasks u3 / e1h_abs_1, seed 1, three arms (12 episodes, not in totals). Pilot settings except HTTP timeout 240 s and episode timeout 1800 s (protocol section 3).
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
import think_arm  # noqa: E402  (also puts the pilot study on sys.path)
harness = think_arm.harness
import run_pilot  # noqa: E402
import scorer_v2 as v2  # noqa: E402
import run_round2  # noqa: E402  (OracleWithRetry only)

ORIGINAL_LOAD_ENV = run_pilot.load_env


def load_env(name):
    """stage3 and e1h as in the pilot; the name-fix fixture (graph /nf) for the amendment-A2 tasks, as in the rendering live run."""
    if name == "namefix":
        sys.path.insert(0, str(STUDIES / "name_fix_applied_20261117"))
        import namefix_fixture
        return namefix_fixture
    return ORIGINAL_LOAD_ENV(name)

REPO = HERE.parents[2]
LOG = HERE / "RESULTS_LOG.jsonl"
MASTER_SEED = 20261125
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
STAGE3_TASKS = ["u3", "p3", "h4", "v2"]
E1H_TASKS = ["e1h_amb_1", "e1h_amb_2", "e1h_abs_1", "e1h_abs_2", "e1h_chg_1", "e1h_chg_2"]
TASKS = {t["id"]: t for t in json.loads((STUDIES / "headroom_diagnostic_20261112/stage3_tasks.json").read_text())}
TASKS.update({t["id"]: t for t in json.loads((STUDIES / "small_model_harness_20261115/e1h_tasks.json").read_text())})
TASKS.update({t["id"]: t for t in json.loads((STUDIES / "name_fix_applied_20261117/namefix_tasks.json").read_text())})  # amendment A2: the 8 name-fix tasks
NAMEFIX_TASKS = ["nf_single_1", "nf_single_2", "nf_multi_1", "nf_multi_2", "nf_amb_1", "nf_amb_2", "nf_exact", "nf_absent"]


PARTS = {"partA": ["FULL", "ESCALATE"], "partB": ["ALWAYS"], "replA2": ["FULL", "ESCALATE", "ESCALATE_CAPPED"]}  # replA2: amendment A2 (seeds 3-4, 18 tasks)
SEEDS = {"replA2": [3, 4]}  # amendment A1: part A = FULL vs ESCALATE; part B = ALWAYS, run later in separate sessions


def plan_for(phase):
    sessions = {}
    smoke_tasks = {"stage3": ["u3"], "e1h": ["e1h_abs_1"]}
    full_tasks = {"stage3": STAGE3_TASKS, "e1h": E1H_TASKS}
    if phase in ("replA2", "smokeA2"):
        full_tasks["namefix"] = NAMEFIX_TASKS
    if phase == "smokeA2":  # amendment A2 smoke: qwen3.5 only, u3 and nf_single_1, seed 3, three arms
        smoke_tasks = {"stage3": ["u3"], "namefix": ["nf_single_1"]}
    for model in ([MODELS[1], MODELS[2]] if phase == "smoke" else [MODELS[1]] if phase == "smokeA2" else MODELS):
        for env, tasks in (smoke_tasks if phase in ("smoke", "smokeA2") else full_tasks).items():
            seeds = [1] if phase == "smoke" else [3] if phase == "smokeA2" else SEEDS.get(phase, [1, 2])
            cells = [dict(env=env, task=t, arm=a, model=model, seed=seed, temperature=0.7) for t in tasks for seed in seeds
                     for a in (think_arm.ARMS_ORIGINAL if phase in ("smoke", "full") else PARTS["replA2"] if phase == "smokeA2" else PARTS[phase])]
            random.Random(f"{MASTER_SEED}-{phase}-{model}-{env}").shuffle(cells)
            sessions[f"{model.replace(':', '_')}-{env}"] = cells
    return sessions


EPISODE_TIMEOUT_SECONDS = 1800  # protocol section 3 (the pilot session passes 900, which is ignored here for all three arms)


def run_worker(out, directory, cell, timeout, recorder):
    timeout = EPISODE_TIMEOUT_SECONDS
    command = [sys.executable, str(HERE / "run_think.py"), "episode", "--output", str(directory), "--env", cell["env"], "--task", cell["task"],
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
    think_arm.CURRENT_MODEL["name"] = args.model
    run_pilot.make_arm = think_arm.make_arm
    run_pilot.ArmTracedModel = think_arm.ThinkTracedModel
    run_pilot.build_chat_model = think_arm.build_chat_model
    run_pilot.load_env = load_env
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
    fires = [e for e in handler if e["event"] == "trigger_fire"]
    think_requests = [e for e in handler if e["event"] == "think_request"]
    exposure = dict(trigger_fires=len(fires), requests_with_thinking_on=sum(e["level"] is not None for e in think_requests), precheck_rejections=count("validation_error"), stock_validation_errors=count("stock_validation_error"), coercions=count("coercion"),
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
    run_pilot.load_env = lambda name: run_round2.OracleWithRetry(load_env(name))
    try:
        for name, cells in plan.items():
            path = out / f"plan_{name}.json"
            path.write_text(json.dumps(cells, indent=1))
            print(json.dumps(dict(event="session_start", session=name, cells=len(cells))), flush=True)
            run_pilot.session(out / name, path, wall_limit_hours=8.0)
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
