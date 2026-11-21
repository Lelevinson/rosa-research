"""Name-fix applied test runner (design: research/decisions/2026-11-17-name-fix-applied-test.md; rule revision approved 2026-11-17).
  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python run_namefix.py plan  smoke|full
  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python run_namefix.py run   smoke|full OUTDIR
  uv run python run_namefix.py collect OUTDIR PHASE
64 episodes = 8 tasks x 4 models x seeds 1, 2; one fixture session per model (all 16 cells shuffled, master seed 20261122). One C1 episode gives the original and the applied answer.
Settings and oracle as the ablation (pilot settings; round 2's OracleWithRetry with amendment 4). Smoke: qwen3.5:9b, tasks nf_single_1, nf_multi_1, nf_amb_1, nf_absent, seed 1 (never in totals)."""
import hashlib
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDIES / "build_round2_20261116"))
import namefix_arm  # noqa: E402  (also puts the pilot study on sys.path)
import namefix_fixture as fixture  # noqa: E402
import namefix_scoring as scoring  # noqa: E402
import run_pilot  # noqa: E402
import scorer_v2 as v2  # noqa: E402
import run_round2  # noqa: E402  (OracleWithRetry only)

REPO = HERE.parents[2]
LOG = HERE / "RESULTS_LOG.jsonl"
MASTER_SEED = 20261122
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
TASKS = {t["id"]: t for t in fixture.TASKS}


def load_env(name):
    assert name == "namefix", name
    return fixture


def plan_for(phase):
    sessions = {}
    for model in ([MODELS[1]] if phase == "smoke" else MODELS):
        tasks = ["nf_single_1", "nf_multi_1", "nf_amb_1", "nf_absent"] if phase == "smoke" else list(TASKS)
        seeds = [1] if phase == "smoke" else [1, 2]
        cells = [dict(env="namefix", task=t, arm="NAMEFIX", model=model, seed=s, temperature=0.7) for t in tasks for s in seeds]
        random.Random(f"{MASTER_SEED}-{phase}-{model}").shuffle(cells)
        sessions[f"{model.replace(':', '_')}-namefix"] = cells
    return sessions


def run_worker(out, directory, cell, timeout, recorder):
    command = [sys.executable, str(HERE / "run_namefix.py"), "episode", "--output", str(directory), "--env", cell["env"], "--task", cell["task"],
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
    run_pilot.make_arm = lambda name, recorder, context: namefix_arm.make_arm(recorder, context)
    run_pilot.load_env = load_env
    run_pilot.episode(args)


def episode_row(phase, session, directory, attempt):
    trace = directory / "trace.jsonl"
    events = v2.s1.read_events(trace)
    start = next(e for e in events if e["kind"] == "episode_start")
    task = TASKS[start["task"]["id"]]
    scores = scoring.episode_scores(task, events, fixture.GRAPH)
    metrics = v2.s1.episode_metrics(events)
    end = [e for e in events if e["kind"] == "episode_end"]
    aborts = [x for x in [attempt.get("error"), end[-1].get("error") if end else "no episode_end"] if x]
    if metrics.get("iteration_cap"):
        aborts.append("iteration limit")
    handler = [e for e in events if e["kind"] == "handler" and e.get("event") == "namefix"]
    rule_events = [ev for h in handler for ev in h["events"]]
    kinds = {k: sum(ev["kind"] == k for ev in rule_events) for k in ("rewrite", "reject_ambiguous", "reject_never_seen", "collision")}
    strict = lambda which: scores[which]["strict"]["supported_complete"]
    lenient = lambda which: scores[which]["lenient"]["supported_complete"]
    return dict(run_id=f"{session}/{directory.name}", phase=phase, env=start["env"], task=task["id"], template=task["template"], arm=start["arm"], model=start["model"], seed=start["seed"],
                temperature=start["temperature"], prompt_sha256=start["prompt_sha256"], scorer=v2.SCORER_VERSION, strict_original=strict("original"), strict_applied=strict("applied"),
                lenient_original=lenient("original"), lenient_applied=lenient("applied"), issues_original=scores["original"]["strict"]["issues"], issues_applied=scores["applied"]["strict"]["issues"],
                support_missing_applied=scores["applied"]["strict"]["support_missing"], lenient_changes_original=scores["original"]["lenient_changes"], lenient_changes_applied=scores["applied"]["lenient_changes"],
                answer_original=scores["answer_original"], answer_submitted=scores["answer_submitted"], answer_emitted=scores["answer_original"] is not None,
                rewritten=bool(handler) and handler[-1]["changed"], rule_event_counts=kinds, rule_events=rule_events, rewrite_cpu_seconds=sum(h["cpu_seconds"] for h in handler),
                llm_requests=metrics["requests"], input_tokens=metrics["input_tokens"], output_tokens=metrics["output_tokens"], native_ops=metrics["native_ops"],
                wall_seconds=round(attempt["seconds"], 2), aborts=aborts, trace_path=str(trace.relative_to(REPO)), trace_hash=hashlib.sha256(trace.read_bytes()).hexdigest())


def collect(run, phase):
    run = Path(run).resolve()
    prefix = run.name + "/"
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
