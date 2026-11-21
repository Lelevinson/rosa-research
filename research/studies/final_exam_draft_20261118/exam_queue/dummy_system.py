"""A fake system for testing the queue itself (no ROS, no Ollama): the worker sleeps, then writes a trace; the row is built from the trace.
The worker is a real subprocess started in its own session, like the real workers, so a hard kill of the runner leaves an orphan the queue must clean up on resume."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

DELAY_SECONDS = float(os.environ.get("DUMMY_DELAY_SECONDS", "3"))


def run_worker(out, directory, cell, timeout, recorder):
    if os.environ.get("DUMMY_RAISE_MODEL") == cell["model"]:  # test hook: a block group that keeps failing
        raise RuntimeError("dummy failure for the failing-group test")
    started = time.perf_counter()
    command = [sys.executable, str(Path(__file__).resolve()), "episode", "--output", str(directory), "--task", cell["task"], "--model", cell["model"], "--seed", str(cell["seed"]), "--arm", cell["arm"]]
    with (out / (directory.name + ".worker.log")).open("w") as log:
        worker = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        code = worker.wait(timeout=timeout)
    record = dict(directory=directory.name, returncode=code, error=None, seconds=time.perf_counter() - started, cell=cell)
    with (out / "attempts.jsonl").open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    return record


def episode_row(phase, session, directory, attempt):
    events = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
    start = next(e for e in events if e["kind"] == "episode_start")
    return dict(run_id=f"{session}/{directory.name}", phase=phase, env="dummy", task=start["task"], arm=start["arm"], model=start["model"], seed=start["seed"],
                supported_complete=start["supported"], llm_requests=3, input_tokens=300, output_tokens=60, native_ops=5, wall_seconds=round(attempt["seconds"], 2), aborts=[],
                answer={"x": 1}, trace_path=str(directory / "trace.jsonl"))


def episode(args):
    directory = Path(args["output"])
    directory.mkdir(parents=True)
    trace = directory / "trace.jsonl"
    supported = int(hashlib.sha256(f"{args['task']}{args['model']}{args['seed']}{args['arm']}".encode()).hexdigest(), 16) % 3 != 0
    with trace.open("w") as handle:
        handle.write(json.dumps(dict(kind="episode_start", task=args["task"], arm=args["arm"], model=args["model"], seed=int(args["seed"]), supported=supported)) + "\n")
        handle.flush()
        time.sleep(DELAY_SECONDS)
        handle.write(json.dumps(dict(kind="episode_end", answer="x", error=None)) + "\n")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "episode":
    argv = sys.argv[2:]
    episode({argv[i][2:]: argv[i + 1] for i in range(0, len(argv), 2)})
