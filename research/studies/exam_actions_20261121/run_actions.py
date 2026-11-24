"""Runner adapter of the Stage 2 action systems (XM, XS0, XE1) for the exam queue: `run_worker`, `episode_row`, `load_env` and the `episode` command. DEVELOPMENT action tasks only (judge.TASKS of
action_dev_switch_20261118); held-out action cells need the custodian bridge (see REPORT.md section 4).

Per episode (a fresh process): start a new turtlesim_node (reset), wait for readiness, **stable-state check** (the pose is read twice one second apart through an independent node; a turtle
that moves, or is not at the start pose, is infrastructure and the episode is not run), run the system's loop with the guarded action tool, read the **ground truth** with another independent node
(`true_pose`), judge with `judge_exam` (v1.2 + form normalisation) and write the events: observation reads, dispatched goals and terminal status (`action_call`), executor receipts
(`executor_events.json`), pre/post simulator state (`ground_truth` events), the verdict (`judge` event).
  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python research/studies/exam_actions_20261121/run_actions_queue.py run --spec SPEC --run-name RUN --machine laptop --machines laptop:1
"""
import argparse
import contextlib
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDIES / "action_dev_switch_20261118"))
sys.path.insert(0, str(STUDIES / "stage23_plan_20261123"))
sys.path.insert(0, str(STUDIES / "action_tool_s2_20261118"))
sys.path.insert(0, str(STUDIES / "action_tool_s2_20261118" / "tests"))   # WallClock lives in the S2 test helpers
import action_arms  # noqa: E402  (puts the action tool, pilot and arm folders on the path)
import action_bridge  # noqa: E402  (task text and judge: the public dev bridge, or the custodian bridge named by ROSA_ACTION_BRIDGE_FILE)
import action_trace  # noqa: E402
import graph_settle  # noqa: E402  (waits for / ignores transient ros2 CLI nodes in the fixture checks)
import judge as dev_judge  # noqa: E402  (the dev task bank TASKS)
import judge_exam  # noqa: E402
import run_pilot  # noqa: E402

EPISODE_TIMEOUT_SECONDS = 900
EXPECTED_NODES = ["/turtlesim"]                      # the simulator; a missing one means the fixture is gone
ALLOWED_EXTRA_NODES = ["/exam_actions_backend"]      # this runner's own action-client node
load_env = None  # set below (a stub environment: the episode starts its own simulator)


class TurtlesimEnv:
    """Stub of the graph-fixture interface the queue's session expects (`run_pilot.session`): no fixture processes, an always-clean oracle. The simulator lives inside each episode."""
    NS = "/__turtlesim_stub__"
    GRAPH = {"nodes": []}
    TASKS = [dict(id=task_id, floor=None, request=task["text"]) for task_id, task in dev_judge.TASKS.items()]

    @staticmethod
    def commands():
        return []

    @staticmethod
    def oracle(directory, recorder):
        return []

    @staticmethod
    def cli(*argv, retries=3):
        """The graph fixtures' ros2-CLI helper, which the queue's oracle wrapper (OracleWithRetry) replaces. Never used: this fixture has no oracle reads."""
        raise RuntimeError("the turtlesim stub environment has no ros2 CLI oracle")


def _load_env(name):
    """The only environment of this runner is the turtlesim stub; the custody index names it with its own label, which is not checked here (the custody bridge owns the fixture)."""
    return TurtlesimEnv


load_env = _load_env


def run_worker(out, directory, cell, timeout, recorder):
    command = [sys.executable, str(HERE / "run_actions.py"), "episode", "--output", str(directory), "--env", cell["env"], "--task", cell["task"], "--arm", cell["arm"],
               "--model", cell["model"], "--seed", str(cell["seed"]), "--temperature", str(cell["temperature"])]
    recorder.add("worker_start", command=command)
    started, error = time.perf_counter(), None
    with (out / (directory.name + ".worker.log")).open("w") as log:
        worker = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = worker.wait(timeout=EPISODE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(worker.pid, signal.SIGTERM)
            try:
                worker.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(worker.pid, signal.SIGKILL)
                worker.wait()
            code, error = worker.returncode, f"{EPISODE_TIMEOUT_SECONDS}-second episode timeout"
    record = dict(directory=directory.name, returncode=code, error=error, seconds=time.perf_counter() - started, cell=cell)
    with (out / "attempts.jsonl").open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    print(json.dumps(record), flush=True)
    return record


def fixture_check(phase, recorder):
    """Graph check before (class (a) on failure) and after (class (c) on failure) the system runs: waits for transient ros2 CLI nodes to go, retries empty discovery, ignores CLI helper
    nodes but never a real extra node, and records what was waited for and ignored. A command error is a failed check, never a pass."""
    try:
        result = graph_settle.check_fixture_graph(graph_settle.real_run_command, EXPECTED_NODES, ALLOWED_EXTRA_NODES)
    except Exception as failure:  # noqa: BLE001
        result = dict(ok=False, error=repr(failure), missing=[], unexpected=[], ignored=[], settle=None)
    recorder.add("fixture_check", phase=phase, **result)
    return result


CUSTODY_DIR_ENV = "ROSA_ACTION_CUSTODY_DIR"


def run_agent(args, arm, recorder, request):
    """Runs the system's loop on the request. Returns (answer, ending, error). A separate function so that tests can replace the model."""
    try:
        base = run_pilot.build_chat_model(args.model, args.temperature, args.seed)
        traced = run_pilot.ArmTracedModel(holder={"model": base}, recorder=recorder, options={}, arm=arm)
        agent = run_pilot.PilotROSA(traced, arm)
        result = agent._ROSA__executor.invoke({"input": request, "chat_history": []}, config={"callbacks": [run_pilot.ToolRecorder(recorder)]})
        done = getattr(arm, "final_done", False)
        return (getattr(arm, "final_answer", None) if done else result["output"]), ("final_answer" if done else "text"), None
    except Exception as failure:  # noqa: BLE001
        return None, "no_answer", repr(failure)


def private_directory(path):
    path = Path(path)
    os.mkdir(path, 0o700)
    os.chmod(path, 0o700)   # the umask must not widen it
    return path


def episode_custody(args, bridge):
    """One held-out episode through the custody bridge. Order matters (Codex contract): open the custody episode BEFORE any model; request, simulator, backend, recorder and evidence all come
    from custody; score INSIDE the context, before teardown. Trace, evidence and ROS files stay in a mode-0700 directory under ROSA_ACTION_CUSTODY_DIR; the queue folder gets only
    `custody_result.json` (opaque fields, counts, ending class, trace hash): no request text, no trace. A FixtureError on entry is class (a): a pre-start failure, zero requests, the queue retries."""
    from action_executor import ActionExecutor
    from action_interface import ExecutorOptions
    from test_turtlesim_backend import WallClock
    from turtlesim_backend import TURTLESIM_POLICY

    if (os.environ.get("ROS_DOMAIN_ID") in (None, "", "219") or os.environ.get("ROS_LOCALHOST_ONLY") != "1"
            or os.environ.get("ROS_AUTOMATIC_DISCOVERY_RANGE") != "LOCALHOST"):
        raise RuntimeError("a custody episode needs an isolated ROS domain (not 219), ROS_LOCALHOST_ONLY=1 and ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; start it through run_actions_queue.py")
    root = os.environ.get(CUSTODY_DIR_ENV)
    if not root or not Path(root).is_dir() or Path(root).stat().st_mode & 0o077:
        raise RuntimeError(f"{CUSTODY_DIR_ENV} must name an existing mode-0700 directory for a custody run")
    queue_dir = Path(args.output)
    queue_dir.mkdir(exist_ok=False)
    episode_dir = private_directory(Path(root) / f"{queue_dir.parent.name}__{queue_dir.name}")
    ros_dir, trace_path = private_directory(episode_dir / "ros"), episode_dir / "trace.jsonl"
    identity = dict(env=args.env, task=args.task, arm=args.arm, model=args.model, seed=args.seed, temperature=args.temperature)
    started = time.perf_counter()
    stack = contextlib.ExitStack()
    try:
        active = stack.enter_context(bridge.episode(args.task, args.seed, ros_dir))
    except bridge.FixtureError:
        stack.close()
        (queue_dir / "custody_result.json").write_text(json.dumps(dict(identity, ending_class="pre_start_fixture_failure", requests=0, input_tokens=0, output_tokens=0, native_ops=0, aborts=[],
                                                                      seconds=time.perf_counter() - started, score=None, trace_path=None, trace_sha256=None)))
        return
    with stack:
        recorder = bridge.recorder(trace_path, active)       # the single recorder for model, guard, action kit and tool callbacks
        recorder.add("episode_start", task=dict(id=args.task, floor=None), env=args.env, arm=args.arm, model=args.model, seed=args.seed, temperature=args.temperature, bridge=bridge.name)
        run_pilot.ros2.execute_ros_command = run_pilot.guarded_native(recorder)   # stock write paths stay blocked; only the typed tool can move the robot
        executor = ActionExecutor(TURTLESIM_POLICY, active.backend, WallClock(), ExecutorOptions(attach_post_action_state=False))   # same options for every system
        executor.begin_episode()
        kit = action_arms.ActionToolKit(TURTLESIM_POLICY, executor, active.backend, recorder)
        arm = action_arms.make_arm(args.arm, recorder, dict(env=args.env, task=dict(id=args.task, floor=None, request=active.request), ns="/"), kit)
        recorder.add("tools_policy", policy=dict(goal_budget=TURTLESIM_POLICY.goal_budget, acknowledgement_seconds=TURTLESIM_POLICY.acknowledgement_seconds,
                                                 execution_seconds=TURTLESIM_POLICY.execution_seconds, cancel_settlement_seconds=TURTLESIM_POLICY.cancel_settlement_seconds))
        try:
            answer, ending, error = run_agent(args, arm, recorder, active.request)
        finally:
            arm.close()
        events = [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
        started_requests = sum(e["kind"] == "model_start" for e in events)
        score = bridge.judge(active, answer, executor, started_requests, evidence_path=episode_dir / "evidence.json")   # before teardown
        recorder.add("judge", ending_class=score.get("ending_class"), success=score.get("success"), judge_version=score.get("judge_version"))
        recorder.add("episode_end", answer="in_custody" if answer else None, error=error, seconds=time.perf_counter() - started)
    events = [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
    usage = [e.get("usage") or {} for e in events if e["kind"] == "model_end"]
    (queue_dir / "custody_result.json").write_text(json.dumps(dict(
        identity, ending_class=score["ending_class"], requests=sum(e["kind"] == "model_end" for e in events), input_tokens=sum(u.get("input_tokens", 0) for u in usage),
        output_tokens=sum(u.get("output_tokens", 0) for u in usage), native_ops=sum(e["kind"] == "ros_start" for e in events), aborts=[error] if error else [], seconds=time.perf_counter() - started,
        answer_given=bool(answer), score={k: score.get(k) for k in ("ending_class", "supported_complete", "scored", "goals_sent", "executor_final_state", "arrived", "arrival_claim", "claim_audit", "judge_version")},
        trace_path=str(trace_path), trace_sha256=hashlib.sha256(trace_path.read_bytes()).hexdigest())))


def episode(args):
    """The worker process: one episode of one system on one task. A custody bridge (held-out) takes the custody path; the default is the public dev path."""
    bridge = action_bridge.load_bridge()
    if bridge.kind == "custody":
        return episode_custody(args, bridge)
    import rclpy  # noqa: F401  (imported here so that the queue process itself never needs it)
    from action_executor import ActionExecutor
    from action_interface import ExecutorOptions
    from run_action_study import true_pose  # the dev study's independent ground-truth read
    from test_turtlesim_backend import WallClock, start_turtlesim, stop
    from turtlesim_backend import TURTLESIM_POLICY, TurtlesimBackend

    out = Path(args.output)
    out.mkdir(exist_ok=False)
    recorder = run_pilot.Recorder(out / "trace.jsonl")
    bridge = action_bridge.load_bridge()   # a missing or broken custodian bridge stops the episode here, before any request
    request = bridge.request_text(args.task)
    recorder.add("episode_start", task=dict(id=args.task, floor=None), env=args.env, arm=args.arm, model=args.model, seed=args.seed, temperature=args.temperature, text=request, bridge=bridge.name)
    run_pilot.ros2.execute_ros_command = run_pilot.guarded_native(recorder)  # the stock tools' write paths stay blocked; only the typed tool can move the robot
    simulator, backend = start_turtlesim(), None
    answer, error, ending, started = None, None, "no_answer", time.perf_counter()
    try:
        backend = TurtlesimBackend("exam_actions_backend")
        deadline = time.monotonic() + 20
        while backend.readiness() is not None and time.monotonic() < deadline:
            time.sleep(0.3)
        pre, before_check = None, None
        if backend.readiness() is None:
            before_check = fixture_check("before", recorder)
            if before_check["ok"]:
                heading, x, y, still = true_pose()  # stable-state check before the episode
                pre = dict(heading=heading, x=x, y=y, still=still)
        recorder.add("ground_truth", phase="before", **(pre or {}))
        if pre is None or not bridge.start_state_ok(pre):
            recorder.add("infrastructure", infrastructure_class="a", reason="simulator not ready, fixture graph check failed, or not in a stable start state")
            recorder.add("episode_end", answer=None, error="infrastructure: stable-state check failed", seconds=0.0)
            return
        executor = ActionExecutor(TURTLESIM_POLICY, backend, WallClock(), ExecutorOptions(attach_post_action_state=False))  # the same options for every system
        executor.begin_episode()
        kit = action_arms.ActionToolKit(TURTLESIM_POLICY, executor, backend, recorder)
        context = dict(env=args.env, task=dict(id=args.task, floor=None, request=request), ns="/")
        arm = action_arms.make_arm(args.arm, recorder, context, kit)
        recorder.add("tools_policy", policy=dict(goal_budget=TURTLESIM_POLICY.goal_budget, acknowledgement_seconds=TURTLESIM_POLICY.acknowledgement_seconds,
                                                 execution_seconds=TURTLESIM_POLICY.execution_seconds, cancel_settlement_seconds=TURTLESIM_POLICY.cancel_settlement_seconds))
        try:
            base = run_pilot.build_chat_model(args.model, args.temperature, args.seed)
            traced = run_pilot.ArmTracedModel(holder={"model": base}, recorder=recorder, options={}, arm=arm)
            agent = run_pilot.PilotROSA(traced, arm)
            result = agent._ROSA__executor.invoke({"input": request, "chat_history": []}, config={"callbacks": [run_pilot.ToolRecorder(recorder)]})
            answer = getattr(arm, "final_answer", None) if getattr(arm, "final_done", False) else result["output"]
            ending = "final_answer" if getattr(arm, "final_done", False) else "text"
        except Exception as failure:  # noqa: BLE001
            error = repr(failure)
        finally:
            arm.close()
        after_check = fixture_check("after", recorder)
        true_state = None
        if after_check["ok"]:
            try:
                heading, x, y, still = true_pose()  # independent ground truth after the episode
                true_state = dict(heading=heading, x=x, y=y, still=still)
            except Exception as failure:  # noqa: BLE001
                error = error or f"truth read failed: {failure!r}"
        recorder.add("ground_truth", phase="after", **(true_state or {}))
        (out / "executor_events.json").write_text(json.dumps(executor.events, default=str))
        if true_state is None:
            # Class (c) of the protocol: the simulator or the independent reader was lost AFTER a request. The cell cannot be re-run and cannot be scored; it stays as `unscored`.
            recorder.add("infrastructure", infrastructure_class="c", reason="post-start fixture check or independent state read failed")
            recorder.add("episode_end", answer=answer if isinstance(answer, str) else json.dumps(answer), error=error, seconds=time.perf_counter() - started)
            return
        rows = [json.loads(line) for line in (out / "trace.jsonl").read_text().splitlines()]
        trace = action_trace.dev_trace(rows, executor.events)
        verdict = bridge.judge(args.task, answer, true_state, ending=ending, trace=trace)
        # Class (b): motion caused by the agent that is unresolved at the end (state LOCKED after an unknown goal, or the robot still moving). An agent outcome, never re-run.
        unresolved = executor.state.value == "UNKNOWN_LOCKED" or not true_state["still"]
        recorder.add("judge", version=verdict.get("judge_version"), success=verdict["success"], reasons=verdict["reasons"], claim_audit=verdict.get("claim_audit"),
                     unresolved_motion=unresolved, executor_final_state=executor.state.value, goals_sent=executor.goals_sent, answer=answer, ending=ending)
        recorder.add("episode_end", answer=answer if isinstance(answer, str) else json.dumps(answer), error=error, seconds=time.perf_counter() - started)
    finally:
        if backend is not None:
            backend.close()
        stop(simulator)
        time.sleep(1.0)
        subprocess.run(["pkill", "-9", "-x", "turtlesim_node"], capture_output=True)


def custody_row(phase, session, directory, attempt):
    """Row of a custody episode from `custody_result.json` only (opaque fields; the trace and the answer stay in custody). Ending classes of the custody scorer map to the queue's:
    pre_start_fixture_failure -> infrastructure (zero requests, the queue retries); post_start_oracle_loss -> unscored; agent_unresolved_motion -> unresolved_motion."""
    result = json.loads((directory / "custody_result.json").read_text())
    score, ending_class = result.get("score") or {}, result["ending_class"]
    override = {"post_start_oracle_loss": "unscored", "agent_unresolved_motion": "unresolved_motion"}.get(ending_class)
    supported = bool(score.get("supported_complete")) and ending_class == "scored"
    exposure = dict(custody_ending_class=ending_class, goals_sent=score.get("goals_sent"), executor_final_state=score.get("executor_final_state"), arrived=score.get("arrived"),
                    arrival_claim=score.get("arrival_claim"), claim_audit=score.get("claim_audit"), claimed_but_not_arrived=bool((score.get("claim_audit") or {}).get("claimed_but_not_arrived")),
                    judge_version=score.get("judge_version"))
    return dict(run_id=f"{session}/{directory.name}", phase=phase, env=result["env"], task=result["task"], arm=result["arm"], model=result["model"], seed=result["seed"],
                temperature=attempt["cell"]["temperature"], supported_complete=supported, ending_override=override, exact=None, issues=[], support_missing=[],
                answer="in_custody" if result.get("answer_given") else None, answer_source=None, llm_requests=result["requests"], input_tokens=result["input_tokens"],
                output_tokens=result["output_tokens"], native_ops=result["native_ops"], wall_seconds=round(attempt["seconds"], 2), aborts=[a for a in [attempt.get("error")] + result["aborts"] if a],
                exposure=exposure, trace_path=result["trace_path"], trace_hash=result["trace_sha256"])


def episode_row(phase, session, directory, attempt):
    if (directory / "custody_result.json").exists():
        return custody_row(phase, session, directory, attempt)
    trace = directory / "trace.jsonl"
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    start = next(e for e in events if e["kind"] == "episode_start")
    judged = [e for e in events if e["kind"] == "judge"]
    ends = [e for e in events if e["kind"] == "episode_end"]
    infra_events = [e for e in events if e["kind"] == "infrastructure"]
    infra_class = infra_events[-1].get("infrastructure_class") if infra_events else None
    infra = infra_class == "a"          # class (a): before the first request; the queue's frozen rule then treats the row as infrastructure
    checks = [e for e in events if e["kind"] == "fixture_check"]
    verdict = judged[-1] if judged else None
    model_ends = [e for e in events if e["kind"] == "model_end"]
    usage = [e.get("usage") or {} for e in model_ends]
    error = ends[-1].get("error") if ends else "no episode_end"
    aborts = [x for x in [attempt.get("error"), error] if x]
    calls = [e for e in events if e["kind"] == "action_call"]
    audit = (verdict or {}).get("claim_audit")
    # Ending override: the queue's frozen ending_class has no class for (b) or (c); run_actions_queue.py patches ending_class to read this field (no frozen file is edited).
    ending_override = "unscored" if infra_class == "c" else ("unresolved_motion" if verdict and verdict.get("unresolved_motion") else None)
    exposure = dict(infrastructure_class=infra_class, claim_audit=audit, claimed_but_not_arrived=bool(audit and audit["claimed_but_not_arrived"]),
                    fixture_checks=[dict(phase=c["phase"], ok=c["ok"], missing=c.get("missing"), unexpected=c.get("unexpected"), ignored_cli_nodes=len(c.get("ignored") or []),
                                         settled=(c.get("settle") or {}).get("settled"), waited_s=(c.get("settle") or {}).get("waited_s"),
                                         discovery_misses=(c.get("settle") or {}).get("discovery_misses"), error=c.get("error")) for c in checks],
                    goals_sent=verdict["goals_sent"] if verdict else 0, executor_final_state=verdict["executor_final_state"] if verdict else None,
                    action_calls=len(calls), action_results=[c["result"] for c in calls], pose_reads=sum(e["kind"] == "pose_read" for e in events),
                    verification_reads=sum(e["kind"] == "pose_read" and e.get("after_goal") for e in events), judge_version=verdict["version"] if verdict else None)
    return dict(run_id=f"{session}/{directory.name}", phase=phase, env=start["env"], task=start["task"]["id"], arm=start["arm"], model=start["model"], seed=start["seed"],
                temperature=attempt["cell"]["temperature"], supported_complete=bool(verdict and verdict["success"] and infra_class is None), ending_override=ending_override, exact=None, issues=(verdict or {}).get("reasons", []), support_missing=[],
                answer=(verdict or {}).get("answer"), answer_source=(verdict or {}).get("ending"), llm_requests=0 if infra else len(model_ends),
                input_tokens=sum(u.get("input_tokens", 0) for u in usage), output_tokens=sum(u.get("output_tokens", 0) for u in usage), native_ops=sum(e["kind"] == "ros_start" for e in events),
                wall_seconds=round(attempt["seconds"], 2), aborts=aborts, exposure=exposure, trace_path=str(trace.relative_to(REPO)) if trace.is_relative_to(REPO) else str(trace),
                trace_hash=hashlib.sha256(trace.read_bytes()).hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    e = sub.add_parser("episode")
    for flag in ("--output", "--env", "--task", "--arm", "--model", "--temperature"):
        e.add_argument(flag, required=True)
    e.add_argument("--seed", type=int, required=True)
    a = parser.parse_args()
    a.temperature = float(a.temperature)
    episode(a)
