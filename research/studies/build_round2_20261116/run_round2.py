"""Round 2 runner: plans, sessions, worker and the append-only RESULTS_LOG.jsonl. Reuses the pilot's session/fixture/oracle code (run_pilot.py) unchanged.

  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python run_round2.py plan  smoke|full|addon
  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python run_round2.py run   smoke|full|addon OUTDIR [session names...]
  uv run python run_round2.py collect OUTDIR PHASE
  uv run python run_round2.py episode ...        (internal) one episode in its own process

Design (PROTOCOL.md section 6): arms CONTROL and SWEEP; enriched tasks (h4, u3, v2) seeds 1..10, other development tasks seeds 1,2, four models; one fixture session per
(model, environment) with both arms shuffled together (master seed 20261118). Settings are the pilot's/round 1's (think false, temperature 0.7, num_ctx 65536,
num_predict 4096, 40-iteration cap). Phases: smoke (4 episodes, never in totals), full (352), addon (seeds 11..15 on the enriched tasks, only if V-c fails).
"""
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROUND1 = HERE.parent / "build_round1_20261115"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROUND1))
import round2_harness as r2  # noqa: E402  (also puts the pilot study on sys.path)
import run_pilot  # noqa: E402
import score_round2  # noqa: E402
import run_round1 as R1  # noqa: E402  (task table, handler_events helper)

REPO = HERE.parents[2]
LOG = HERE / "RESULTS_LOG.jsonl"
RUNS = REPO / "research/_artifacts/runs/build_round2_20261116"
MASTER_SEED = 20261118
MODELS = R1.MODELS
ENRICHED = ["h4", "u3", "v2"]  # PROTOCOL.md section 3
STAGE3_OTHER = ["p3"]
E1H_TASKS = R1.E1H_TASKS
TEMPERATURE = 0.7
TASKS = R1.TASKS
SWEEP_EVENTS = {"sweep_fire", "sweep_shadow", "sweep_empty_after_limit"}


def plan_for(phase):
    """{session name: [cells]}. full = 352 cells; smoke = 4; addon = 120."""
    sessions = {}
    for model in MODELS:
        for env, tasks in (("stage3", ENRICHED + STAGE3_OTHER), ("e1h", E1H_TASKS)):
            cells = []
            for task in tasks:
                if phase == "smoke":
                    chosen = {("bonsai-2:4b", "v2"): [2], ("qwen3.5:9b", "h4"): [1]}.get((model, task), [])
                elif phase == "addon":
                    chosen = [11, 12, 13, 14, 15] if task in ENRICHED else []
                else:
                    chosen = list(range(1, 11)) if task in ENRICHED else [1, 2]
                cells += [dict(env=env, task=task, arm=arm, model=model, seed=seed, temperature=TEMPERATURE) for seed in chosen for arm in r2.ARMS]
            if cells:
                random.Random(f"{MASTER_SEED}-{phase}-{model}-{env}").shuffle(cells)
                sessions[f"{model.replace(':', '_')}-{env}"] = cells
    return sessions


# ------------------------------------------------------------------ worker (one episode, own process)
def run_worker(out, directory, cell, timeout, recorder):
    command = [sys.executable, str(HERE / "run_round2.py"), "episode", "--output", str(directory), "--env", cell["env"], "--task", cell["task"],
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


class OracleWithRetry:
    """Amendments 1, 2 and 4 (PROTOCOL.md, 2026-11-16): stands in for the fixture module inside the session process. Everything else is delegated unchanged; run_pilot.py is not edited.
    Amendments 1+2: EVERY oracle read (before, periodic, end of session) is retried ONCE after a 5-second wait before it counts as a failure. Every oracle read that reports a mismatch
    (first try and retry, any label) is appended to oracle_failures.jsonl in the run folder with the session, the label, the attempt and the arms of the episodes run since the previous oracle read.
    Amendment 4 (root cause of the node-discovery flakes, DISCOVERY_FLAKES.md): the oracle's one call `ros2 node list --no-daemon --spin-time 4` is replaced by `ros2 node list` read through a
    daemon restarted once at the start of the session (the command the agent's own tool runs), and the RAW node list of every such read is written to node_list_raw.jsonl in the oracle folder
    (both attempts). The parameter, topic and node-info reads, the expected values and the cleanup checks are untouched."""
    DAEMON_SETTLE_SECONDS = 10

    def __init__(self, env):
        self._env, self._seen, self._directory, self._daemon_restarted = env, 0, None, False
        if not hasattr(env, "_round2_original_cli"):  # load_env may hand back a module that an earlier session already wrapped
            env._round2_original_cli = env.cli
        env.cli = self.cli

    def __getattr__(self, name):
        return getattr(self._env, name)

    def restart_daemon(self):
        subprocess.run(["ros2", "daemon", "stop"], capture_output=True, text=True, timeout=60)
        subprocess.run(["ros2", "daemon", "start"], capture_output=True, text=True, timeout=60)
        time.sleep(self.DAEMON_SETTLE_SECONDS)  # a just-started daemon needs a moment to hear the running nodes
        self._daemon_restarted = True

    def cli(self, *argv, retries=3):
        """The fixture's own cli(), except that the oracle's one no-daemon node list becomes a daemon read, and its raw output is logged."""
        original = self._env._round2_original_cli
        if tuple(argv[:3]) != ("node", "list", "--no-daemon"):
            return original(*argv, retries=retries)
        began = time.time()
        text, tries = original("node", "list", retries=retries)
        declared = {n["fqn"] for n in self._env.GRAPH["nodes"]}
        with (self._directory / "node_list_raw.jsonl").open("a") as handle:
            handle.write(json.dumps(dict(command="ros2 node list", via_daemon=True, time=began, seconds=round(time.time() - began, 2), cli_tries=tries, raw=text,
                                         listed_fixture_nodes=len(declared & set((text or "").split())), declared_fixture_nodes=len(declared))) + "\n")
        return text, tries

    def oracle(self, directory, recorder):
        directory = Path(directory)
        self._directory = directory
        if not self._daemon_restarted:  # once per session, before the first oracle read (the fixture nodes are already running)
            self.restart_daemon()
        session_dir, label = directory.parent, directory.name.replace("oracle-", "")
        attempts_file = session_dir / "attempts.jsonl"
        attempts = [json.loads(l) for l in attempts_file.read_text().splitlines()] if attempts_file.exists() else []
        arms = sorted({a["cell"]["arm"] for a in attempts[self._seen:]})
        self._seen = len(attempts)
        for attempt in (1, 2):
            bad = self._env.oracle(directory, recorder)
            if bad:
                with (session_dir.parent / "oracle_failures.jsonl").open("a") as handle:
                    handle.write(json.dumps(dict(session=session_dir.name, label=label, attempt=attempt, mismatches=bad[:5], arms_since_last_oracle=arms,
                                                 episodes_in_session_so_far=len(attempts))) + "\n")
                recorder.add("oracle_failure_logged", label=label, attempt=attempt, mismatches=bad[:5], arms=arms)
            if not bad or attempt == 2:
                return bad
            time.sleep(5)


def episode(args):
    run_pilot.make_arm = r2.make_arm
    run_pilot.ArmTracedModel = r2.Round2Model
    run_pilot.episode(args)


# ------------------------------------------------------------------ results log
def episode_row(phase, session, directory, attempt):
    trace = directory / "trace.jsonl"
    events = score_round2.v2.s1.read_events(trace)
    start = next(e for e in events if e["kind"] == "episode_start")
    task = TASKS[start["task"]["id"]]
    scored = score_round2.score_events(task, events)
    metrics = scored["metrics"]
    end = [e for e in events if e["kind"] == "episode_end"]
    aborts = [x for x in [attempt.get("error"), end[-1].get("error") if end else "no episode_end"] if x]
    if metrics.get("iteration_cap"):
        aborts.append("iteration limit")
    sweep_events = [{k: v for k, v in e.items() if k not in ("kind", "monotonic", "handler", "original_output", "items")}
                    for e in events if e["kind"] == "handler" and e.get("event") in SWEEP_EVENTS]
    rewrite = [{k: v for k, v in e.items() if k not in ("kind", "monotonic", "tool_run_id", "handler")}
               for e in events if e["kind"] == "handler" and e.get("event") == "rewrite_shadow"]
    return dict(run_id=f"{session}/{directory.name}", phase=phase, env=start["env"], task=task["id"], arm=start["arm"], model=start["model"], seed=start["seed"],
                temperature=start["temperature"], scorer=scored["scorer"], supported_complete=scored["supported_complete"], exact=scored["exact"],
                issues=scored["issues"], support_missing=scored["support_missing"], answer=scored["answer_object"], answer_source=scored["answer_source"],
                rewritten=scored.get("rewritten"), rewrite_shadow=rewrite, sweep=sweep_events,
                llm_requests=metrics["requests"], input_tokens=metrics["input_tokens"], output_tokens=metrics["output_tokens"], native_ops=metrics["native_ops"],
                wall_seconds=round(attempt["seconds"], 2), aborts=aborts, tool_calls=len([e for e in events if e["kind"] == "tool_start"]),
                trace_path=str(trace.relative_to(REPO)), trace_hash=hashlib.sha256(trace.read_bytes()).hexdigest())


ORIGINAL_FULL_FOLDER = "full_20261116T003046Z"  # rows of this folder keep the plain run id; rows of later resume folders get "<folder>/" in front


def collect(run, phase):
    run = Path(run).resolve()
    prefix = "" if run.name in (ORIGINAL_FULL_FOLDER,) or run.name.startswith("smoke_") else run.name + "/"
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
    print(f"added {added} episodes to {LOG.name}")


def run(phase, out, only=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    plan = {k: v for k, v in plan_for(phase).items() if only is None or k in only}
    (out / "plan_all.json").write_text(json.dumps(plan, indent=1))
    run_pilot.run_worker = run_worker
    original_load_env = run_pilot.load_env
    run_pilot.load_env = lambda name: OracleWithRetry(original_load_env(name))
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
