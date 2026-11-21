"""Runner adapter of the Stage 2 action systems (XM, XS0, XE1) for the exam queue: `run_worker`, `episode_row`, `load_env` and the `episode` command. DEVELOPMENT action tasks only (judge.TASKS of
action_dev_switch_20261118); held-out action cells need the custodian bridge (see REPORT.md section 4).

Per episode (a fresh process): start a new turtlesim_node (reset), wait for readiness, **stable-state check** (the pose is read twice one second apart through an independent node; a turtle
that moves, or is not at the start pose, is infrastructure and the episode is not run), run the system's loop with the guarded action tool, read the **ground truth** with another independent node
(`true_pose`), judge with `judge_exam` (v1.2 + form normalisation) and write the events: observation reads, dispatched goals and terminal status (`action_call`), executor receipts
(`executor_events.json`), pre/post simulator state (`ground_truth` events), the verdict (`judge` event).
  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python research/studies/exam_actions_20261121/run_actions_queue.py run --spec SPEC --run-name RUN --machine laptop --machines laptop:1
"""
import argparse
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
import action_arms  # noqa: E402  (puts the action tool, pilot and arm folders on the path)
import action_trace  # noqa: E402
import judge as dev_judge  # noqa: E402  (the dev task bank TASKS)
import judge_exam  # noqa: E402
import run_pilot  # noqa: E402

EPISODE_TIMEOUT_SECONDS = 900
START_POSE_TOLERANCE = 0.05
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
    assert name == "turtlesim", name
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


def episode(args):
    """The worker process: one episode of one system on one dev action task."""
    import rclpy  # noqa: F401  (imported here so that the queue process itself never needs it)
    from action_executor import ActionExecutor
    from action_interface import ExecutorOptions
    from run_action_study import true_pose  # the dev study's independent ground-truth read
    from test_turtlesim_backend import WallClock, start_turtlesim, stop
    from turtlesim_backend import TURTLESIM_POLICY, TurtlesimBackend

    out = Path(args.output)
    out.mkdir(exist_ok=False)
    recorder = run_pilot.Recorder(out / "trace.jsonl")
    task = dev_judge.TASKS[args.task]
    recorder.add("episode_start", task=dict(id=args.task, floor=None), env=args.env, arm=args.arm, model=args.model, seed=args.seed, temperature=args.temperature, text=task["text"])
    run_pilot.ros2.execute_ros_command = run_pilot.guarded_native(recorder)  # the stock tools' write paths stay blocked; only the typed tool can move the robot
    simulator, backend = start_turtlesim(), None
    answer, error, ending, started = None, None, "no_answer", time.perf_counter()
    try:
        backend = TurtlesimBackend("exam_actions_backend")
        deadline = time.monotonic() + 20
        while backend.readiness() is not None and time.monotonic() < deadline:
            time.sleep(0.3)
        pre = None
        if backend.readiness() is None:
            heading, x, y, still = true_pose()  # stable-state check before the episode
            pre = dict(heading=heading, x=x, y=y, still=still)
        recorder.add("ground_truth", phase="before", **(pre or {}))
        if pre is None or not pre["still"] or abs(pre["heading"]) > START_POSE_TOLERANCE:
            recorder.add("infrastructure", reason="simulator not ready or not in a stable start state")
            recorder.add("episode_end", answer=None, error="infrastructure: stable-state check failed", seconds=0.0)
            return
        executor = ActionExecutor(TURTLESIM_POLICY, backend, WallClock(), ExecutorOptions(attach_post_action_state=False))  # the same options for every system
        executor.begin_episode()
        kit = action_arms.ActionToolKit(TURTLESIM_POLICY, executor, backend, recorder)
        context = dict(env=args.env, task=dict(id=args.task, floor=None, request=task["text"]), ns="/")
        arm = action_arms.make_arm(args.arm, recorder, context, kit)
        recorder.add("tools_policy", policy=dict(goal_budget=TURTLESIM_POLICY.goal_budget, acknowledgement_seconds=TURTLESIM_POLICY.acknowledgement_seconds,
                                                 execution_seconds=TURTLESIM_POLICY.execution_seconds, cancel_settlement_seconds=TURTLESIM_POLICY.cancel_settlement_seconds))
        try:
            base = run_pilot.build_chat_model(args.model, args.temperature, args.seed)
            traced = run_pilot.ArmTracedModel(holder={"model": base}, recorder=recorder, options={}, arm=arm)
            agent = run_pilot.PilotROSA(traced, arm)
            result = agent._ROSA__executor.invoke({"input": task["text"], "chat_history": []}, config={"callbacks": [run_pilot.ToolRecorder(recorder)]})
            answer = getattr(arm, "final_answer", None) if getattr(arm, "final_done", False) else result["output"]
            ending = "final_answer" if getattr(arm, "final_done", False) else "text"
        except Exception as failure:  # noqa: BLE001
            error = repr(failure)
        finally:
            arm.close()
        heading, x, y, still = true_pose()  # independent ground truth after the episode
        recorder.add("ground_truth", phase="after", heading=heading, x=x, y=y, still=still)
        rows = [json.loads(line) for line in (out / "trace.jsonl").read_text().splitlines()]
        trace = action_trace.dev_trace(rows, executor.events)
        (out / "executor_events.json").write_text(json.dumps(executor.events, default=str))
        verdict = judge_exam.judge(args.task, answer, heading, x, y, still, ending=ending, trace=trace)
        recorder.add("judge", version=judge_exam.JUDGE_VERSION, success=verdict["success"], reasons=verdict["reasons"], executor_final_state=executor.state.value, goals_sent=executor.goals_sent,
                     answer=answer, ending=ending)
        recorder.add("episode_end", answer=answer if isinstance(answer, str) else json.dumps(answer), error=error, seconds=time.perf_counter() - started)
    finally:
        if backend is not None:
            backend.close()
        stop(simulator)
        time.sleep(1.0)
        subprocess.run(["pkill", "-9", "-x", "turtlesim_node"], capture_output=True)


def episode_row(phase, session, directory, attempt):
    trace = directory / "trace.jsonl"
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    start = next(e for e in events if e["kind"] == "episode_start")
    judged = [e for e in events if e["kind"] == "judge"]
    ends = [e for e in events if e["kind"] == "episode_end"]
    infra = any(e["kind"] == "infrastructure" for e in events)
    verdict = judged[-1] if judged else None
    model_ends = [e for e in events if e["kind"] == "model_end"]
    usage = [e.get("usage") or {} for e in model_ends]
    error = ends[-1].get("error") if ends else "no episode_end"
    aborts = [x for x in [attempt.get("error"), error] if x]
    calls = [e for e in events if e["kind"] == "action_call"]
    exposure = dict(goals_sent=verdict["goals_sent"] if verdict else 0, executor_final_state=verdict["executor_final_state"] if verdict else None,
                    action_calls=len(calls), action_results=[c["result"] for c in calls], pose_reads=sum(e["kind"] == "pose_read" for e in events),
                    verification_reads=sum(e["kind"] == "pose_read" and e.get("after_goal") for e in events), judge_version=verdict["version"] if verdict else None)
    return dict(run_id=f"{session}/{directory.name}", phase=phase, env=start["env"], task=start["task"]["id"], arm=start["arm"], model=start["model"], seed=start["seed"],
                temperature=attempt["cell"]["temperature"], supported_complete=bool(verdict and verdict["success"]), exact=None, issues=(verdict or {}).get("reasons", []), support_missing=[],
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
