"""Runner adapter of system F (released Forge, matched transport) for the exam queue: the hooks `run_worker`, `episode_row` and the `episode` command.
System id F, arm name F (final_exam_draft_20261118/exam_queue/systems.py). Label everywhere: "Forge 0.10.1 as released, run through the pilot's unchanged episode function".

  - Episode: forge_episode.py in the isolated Forge interpreter. Its path comes from the environment variable ROSA_FORGE_PYTHON (default ~/.local/share/rosa-exam/forge-env/bin/python);
    a missing interpreter stops with an explicit message, there is no fallback to the project environment.
  - Fixtures, oracle retry (5 s, `OracleWithRetry`), GPU-state block, contention rule, resume: the queue's, identical to every other system.
  - Row: the same fields as the other runners plus Forge's token accounting. A request whose response carries no usage (a non-200 response, for example a recovered HTTP 500) keeps its usage
    NULL (`usage_per_request` has null at its position); `usage_missing_requests` counts them and `token_totals_lower_bound` is true when any exists: Forge's token totals are lower bounds.
Development tasks only (T.TASKS), like run_exam.py. Pooled dev smoke through the queue: see REPORT_BASELINE_ADAPTERS.md.
"""
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
sys.path.insert(0, str(STUDIES / "thinking_escalation_20261119"))
import run_think as T  # noqa: E402  (also puts the pilot study and scorer_v2 on the path)
import scorer_v2 as v2  # noqa: E402

EPISODE_TIMEOUT_SECONDS = 900  # same as the pilot's Forge worker and the exam protocol
DEFAULT_FORGE_PYTHON = str(Path.home() / ".local/share/rosa-exam/forge-env/bin/python")  # persistent, outside the repository; see freeze_package_20261121/FORGE_ENV.md
load_env = T.load_env
WRITE_TOOLS = {"ros2_param_set", "ros2_service_call"}


def forge_python():
    path = os.environ.get("ROSA_FORGE_PYTHON", DEFAULT_FORGE_PYTHON)
    if not Path(path).exists():
        raise RuntimeError(f"Forge interpreter not found: {path}. Create it with: uv venv ENV --python 3.12 && VIRTUAL_ENV=ENV uv pip install forge-guardrails==0.10.1, "
                           "then set ROSA_FORGE_PYTHON=ENV/bin/python")
    return path


def run_worker(out, directory, cell, timeout, recorder):
    command = [forge_python(), str(HERE / "forge_episode.py"), str(directory), cell["env"], cell["task"], cell["model"], str(cell["seed"])]
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


def relative(path):
    try:
        return str(path.relative_to(REPO))
    except ValueError:  # a trace outside the repository (tests, scratch runs): keep the absolute path
        return str(path)


def usage_per_request(events):
    """One entry per model request in order: {"input": n, "output": n} when the response carried usage, else None. Requests = wire responses (one per HTTP request)."""
    result = []
    for event in events:
        if event["kind"] == "wire_response":
            raw = event.get("response") or {}
            ok = event.get("status") == 200 and "prompt_eval_count" in raw
            result.append({"input": raw["prompt_eval_count"], "output": raw.get("eval_count", 0)} if ok else None)
    return result


def episode_row(phase, session, directory, attempt):
    trace = directory / "trace.jsonl"
    events = v2.s1.read_events(trace)
    start = next(e for e in events if e["kind"] == "episode_start")
    task = T.TASKS[start["task"]["id"]]
    scored = v2.score_events(task, events)
    ends = [e for e in events if e["kind"] == "episode_end"]
    error = ends[-1].get("error") if ends else "no episode_end"
    aborts = [x for x in [attempt.get("error"), error] if x]
    if error and "MaxIterationsError" in str(error):
        aborts.append("iteration limit")  # the exam's ending classes read this phrase
    usage = usage_per_request(events)
    missing = sum(u is None for u in usage)
    handler_tools = [e["name"] for e in events if e["kind"] == "tool_start"]
    requests = sum(e["kind"] == "model_start" for e in events)
    exposure = dict(forge_error=str(error) if error else None, usage_missing_requests=missing, non_200_responses=sum(e["kind"] == "wire_response" and e.get("status") != 200 for e in events),
                    compactions=sum(e["kind"] == "compaction" for e in events), blocked_write_attempts=sum(e["kind"] == "guard_rejection" for e in events),
                    write_tool_calls=sum(t in WRITE_TOOLS for t in handler_tools), tool_calls=len(handler_tools))
    return dict(run_id=f"{session}/{directory.name}", phase=phase, env=start["env"], task=task["id"], arm="F", model=start["model"], seed=start["seed"],
                temperature=attempt["cell"]["temperature"], prompt_sha256=hashlib.sha256(json.dumps(start["prompts"]).encode()).hexdigest(), scorer=scored["scorer"],
                supported_complete=scored["supported_complete"], exact=scored["exact"], issues=scored["issues"], support_missing=scored["support_missing"], answer=scored["answer_object"],
                answer_source=scored["answer_source"], llm_requests=requests, input_tokens=sum(u["input"] for u in usage if u), output_tokens=sum(u["output"] for u in usage if u),
                usage_per_request=usage, usage_missing_requests=missing, token_totals_lower_bound=missing > 0, native_ops=sum(e["kind"] == "ros_start" for e in events),
                wall_seconds=round(attempt["seconds"], 2), aborts=aborts, exposure=exposure, trace_path=relative(trace), trace_hash=hashlib.sha256(trace.read_bytes()).hexdigest())
