"""Test-only dummy system for the rev-2 crash tests (no GPU, no model, no ROS). Like exam_queue/dummy_system.py, but the trace also has `model_start` events and the worker/runner can be
made to die at a chosen point. Fault control by environment (all optional):
  DUMMY_FAULT          during_episode | before_model | after_worker_before_attempt | exit_after_requests | exit_early
                       (exit_*: the worker ends with exit code 3 and the attempt line is written; exit_early = before any model request)
  DUMMY_ROS=1          the worker runs `ros2 node list` through the discovery daemon (as the agent's tools do) and the runner checks, before each worker starts, that the graph (hidden nodes
                       included) has no discovery daemon: the strict start check of the real static fixture (domain from ROS_DOMAIN_ID, a test domain, never 219)
  DUMMY_FAULT_CELL     substring of the cell id that triggers it (default: every cell)
  DUMMY_FAULT_TIMES    how many times it may fire (default 1), counted with marker files in DUMMY_FAULT_DIR
The runner process kills itself with SIGKILL (a hard kill: no cleanup, no finally block runs)."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

DELAY_SECONDS = float(os.environ.get("DUMMY_DELAY_SECONDS", "0.2"))


def fire(cell):
    fault = os.environ.get("DUMMY_FAULT")
    if not fault or os.environ.get("DUMMY_FAULT_CELL", "") not in cell["id"]:
        return None
    directory = Path(os.environ["DUMMY_FAULT_DIR"])
    directory.mkdir(parents=True, exist_ok=True)
    used = len(list(directory.glob("fired_*")))
    if used >= int(os.environ.get("DUMMY_FAULT_TIMES", "1")):
        return None
    (directory / f"fired_{used}").write_text(cell["id"])
    return fault


def graph_has_daemon():
    p = subprocess.run(["ros2", "node", "list", "-a", "--no-daemon", "--spin-time", "3"], capture_output=True, text=True, timeout=60)
    return any(line.startswith("/_ros2cli_daemon") for line in p.stdout.splitlines())


def run_worker(out, directory, cell, timeout, recorder):
    fault = fire(cell)
    started = time.perf_counter()
    if os.environ.get("DUMMY_ROS") == "1" and graph_has_daemon():          # strict start check failed: the worker never starts (no trace), the attempt line says exit code 9
        record = dict(directory=directory.name, returncode=9, error="graph not empty at fixture start", seconds=0.0, cell=cell)
        with (out / "attempts.jsonl").open("a") as handle:
            handle.write(json.dumps(record) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return record
    command = [sys.executable, str(Path(__file__).resolve()), "episode", "--output", str(directory), "--task", cell["task"], "--model", cell["model"], "--seed", str(cell["seed"]),
               "--arm", cell["arm"], "--delay", "30" if fault == "during_episode" else str(DELAY_SECONDS), "--stop-before-model", "1" if fault == "before_model" else "0", "--exit-code", "3" if fault in ("exit_after_requests", "exit_early") else "0",
               "--early", "1" if fault == "exit_early" else "0"]
    with (out / (directory.name + ".worker.log")).open("w") as log:
        worker = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        if fault in ("during_episode", "before_model"):
            deadline = time.time() + 20
            want = '"kind": "model_start"' if fault == "during_episode" else '"kind": "episode_start"'
            trace = Path(directory) / "trace.jsonl"
            while time.time() < deadline and not (trace.exists() and want in trace.read_text()):
                time.sleep(0.05)
            os.kill(os.getpid(), signal.SIGKILL)                 # the runner dies while the worker lives on (an orphan, as after a real hard kill)
        code = worker.wait(timeout=timeout)
    if fault == "after_worker_before_attempt":
        os.kill(os.getpid(), signal.SIGKILL)                      # the worker is finished (episode_end written), the attempt line is not
    record = dict(directory=directory.name, returncode=code, error=None, seconds=time.perf_counter() - started, cell=cell)
    with (out / "attempts.jsonl").open("a") as handle:
        handle.write(json.dumps(record) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def episode_row(phase, session, directory, attempt):
    events = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
    start = next(e for e in events if e["kind"] == "episode_start")
    requests = sum(e["kind"] == "model_start" for e in events)
    return dict(run_id=f"{session}/{directory.name}", phase=phase, env="dummy", task=start["task"], arm=start["arm"], model=start["model"], seed=start["seed"],
                supported_complete=start["supported"], llm_requests=requests, input_tokens=300, output_tokens=60, native_ops=5, wall_seconds=round(attempt["seconds"], 2), aborts=[],
                answer={"x": 1}, trace_path=str(directory / "trace.jsonl"))


def episode(args):
    directory = Path(args["output"])
    directory.mkdir(parents=True)
    import hashlib
    supported = int(hashlib.sha256(f"{args['task']}{args['model']}{args['seed']}{args['arm']}".encode()).hexdigest(), 16) % 3 != 0
    with (directory / "trace.jsonl").open("w") as handle:
        def add(**event):
            handle.write(json.dumps(event) + "\n")
            handle.flush()
        add(kind="episode_start", task=args["task"], arm=args["arm"], model=args["model"], seed=int(args["seed"]), supported=supported)
        if args["early"] == "1":
            sys.exit(int(args["exit-code"]))                     # the worker dies before any model request
        if args["stop-before-model"] == "1":
            time.sleep(60)                                       # killed long before this ends
        add(kind="model_start")
        add(kind="model_start")
        time.sleep(float(args["delay"]))
        if os.environ.get("DUMMY_ROS") == "1":
            subprocess.run(["ros2", "node", "list"], capture_output=True, text=True, timeout=60)   # starts the domain's discovery daemon, which outlives the worker
        add(kind="episode_end", answer="x", error=None)
        if int(args["exit-code"]):
            sys.exit(int(args["exit-code"]))


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "episode":
    argv = sys.argv[2:]
    episode({argv[i][2:]: argv[i + 1] for i in range(0, len(argv), 2)})
