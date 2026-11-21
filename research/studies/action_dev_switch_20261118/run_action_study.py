"""Turtlesim dev action study: post-action-state switch OFF vs ON. Protocol: PROTOCOL.md (hash in PROTOCOL.sha256). Stand-alone loop (not part of any harness).
  source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1
  uv run python research/studies/action_dev_switch_20261118/run_action_study.py smoke
  nohup uv run python research/studies/action_dev_switch_20261118/run_action_study.py full > run.log 2>&1 &
One job at a time. Each episode starts a fresh turtlesim_node, runs a short tool-calling loop against Ollama, then reads the ground truth with a separate node."""
import hashlib
import json
import os
import random
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "action_tool_s2_20261118"))
sys.path.insert(0, str(HERE.parent / "action_tool_s2_20261118/tests"))
sys.path.insert(0, str(HERE.parent / "action_tool_s1_20261118"))

import rclpy  # noqa: E402
from turtlesim.msg import Pose  # noqa: E402

from action_executor import ActionExecutor  # noqa: E402
from action_interface import ExecutorOptions, render_for_model, tool_schema  # noqa: E402
from judge import TASKS, judge  # noqa: E402
from test_turtlesim_backend import WallClock, angle_error, start_turtlesim, stop  # noqa: E402  (the S2 test helpers)
from turtlesim_backend import TURTLESIM_POLICY, TurtlesimBackend  # noqa: E402

OLLAMA = os.environ.get("ROSA_OLLAMA_URL", "http://172.30.80.1:11434")  # lab container sets ROSA_OLLAMA_URL
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
MAX_ITERATIONS = 15
EPISODE_SECONDS = 300
MASTER_SEED = 20261125
RUNS = ROOT / "research/_artifacts/runs/action_dev_switch_20261118"
SYSTEM = ("You control a simulated turtle in ROS 2 turtlesim. Use the tools to act and to look. Headings are in radians. "
          "When you are done, call final_answer with a JSON object.")
READ_SCHEMA = {"type": "function", "function": {"name": "read_turtle_pose", "description": "Read the turtle's current pose (read-only).",
                                                "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}}
PARAM_SCHEMA = {"type": "function", "function": {"name": "get_parameter", "description": "Read one ROS 2 parameter of a node (read-only).",
                "parameters": {"type": "object", "properties": {"node_name": {"type": "string"}, "parameter_name": {"type": "string"}}, "required": ["node_name", "parameter_name"],
                               "additionalProperties": False}}}
FINAL_SCHEMA = {"type": "function", "function": {"name": "final_answer", "description": "Give the final answer as a JSON object and finish.",
                                                 "parameters": {"type": "object", "properties": {"answer": {"type": "object"}}, "required": ["answer"]}}}


class Infrastructure(Exception):
    pass


def chat(model, messages, tools, seed):
    body = json.dumps(dict(model=model, messages=messages, tools=tools, stream=False, think=False,
                           options=dict(temperature=0.7, num_ctx=65536, num_predict=4096, seed=seed))).encode()
    request = urllib.request.Request(OLLAMA + "/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read())


def unload(model):
    try:
        urllib.request.urlopen(urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps(dict(model=model, keep_alive=0)).encode(), headers={"Content-Type": "application/json"}), timeout=60).read()
    except Exception as error:
        print("unload failed", model, error, flush=True)


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def true_pose():
    """Independent ground-truth read: a fresh node and subscription; returns (heading, x, y, still)."""
    node = rclpy.create_node("action_study_truth")
    seen = []
    node.create_subscription(Pose, "/turtle1/pose", seen.append, 10)

    def latest():
        seen.clear()
        end = time.monotonic() + 3
        while not seen and time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.1)
        if not seen:
            raise RuntimeError("no pose received")
        return seen[-1]
    first = latest()
    time.sleep(1.0)
    second = latest()
    node.destroy_node()
    return second.theta, second.x, second.y, angle_error(first.theta, second.theta) < 0.01


def get_parameter(arguments):
    node_name, parameter_name = arguments.get("node_name"), arguments.get("parameter_name")
    if not isinstance(node_name, str) or not isinstance(parameter_name, str):
        return "Error: node_name and parameter_name must be strings"
    try:
        done = subprocess.run(["ros2", "param", "get", node_name, parameter_name], capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return "Error: timed out"
    lines = [l for l in (done.stdout or done.stderr).splitlines() if l.strip() and "[WARN]" not in l]
    return "\n".join(lines) if lines else "Error: no output"


def run_episode(backend, model, task_id, arm, seed, run_dir):
    task = TASKS[task_id]
    sim = start_turtlesim()
    started = time.monotonic()
    try:
        deadline = time.monotonic() + 20
        while backend.readiness() is not None and time.monotonic() < deadline:
            time.sleep(0.3)
        if backend.readiness() is not None:
            return dict(ending="infrastructure: simulator not ready", requests=0, infrastructure=True)
        executor = ActionExecutor(TURTLESIM_POLICY, backend, WallClock(), ExecutorOptions(attach_post_action_state=(arm == "ON")))
        executor.begin_episode()
        tools = [tool_schema(TURTLESIM_POLICY.actions["rotate_to_heading"]), READ_SCHEMA, PARAM_SCHEMA, FINAL_SCHEMA]
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task["text"]}]
        trace = [dict(kind="system", content=SYSTEM), dict(kind="user", content=task["text"])]
        answer, ending, requests, tokens = None, "cap", 0, 0
        calls, goal_sent, verification, rotate_results = [], False, 0, []
        ollama_seed = 1000 * seed + task["number"]
        for _ in range(MAX_ITERATIONS):
            if time.monotonic() - started > EPISODE_SECONDS:
                ending = "timeout"
                break
            try:
                reply = chat(model, messages, tools, ollama_seed)
            except urllib.error.HTTPError as error:
                ending = f"backend_error: HTTP {error.code}"
                trace.append(dict(kind="backend_error", error=str(error), body=error.read().decode(errors="replace")[:500]))
                break
            except (socket.timeout, TimeoutError):
                ending = "timeout_http"
                break
            except urllib.error.URLError as error:
                if isinstance(error.reason, (socket.timeout, TimeoutError)):
                    ending = "timeout_http"
                    break
                raise Infrastructure(str(error))
            requests += 1
            tokens += reply.get("prompt_eval_count", 0) + reply.get("eval_count", 0)
            message = reply["message"]
            messages.append(message)
            trace.append(dict(kind="assistant", content=message.get("content"), thinking=message.get("thinking"), tool_calls=message.get("tool_calls")))
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                ending, answer = "text", message.get("content")
                break
            done = False
            for call in tool_calls:
                name, arguments = call["function"]["name"], call["function"].get("arguments") or {}
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except ValueError:
                        arguments = {}
                if not isinstance(arguments, dict):
                    arguments = {}
                if name == "rotate_to_heading":
                    outcome = executor.execute(name, arguments)
                    result = render_for_model(outcome)
                    goal_sent = goal_sent or outcome.goal_id is not None
                    rotate_results.append(outcome.result.value + (f" {outcome.detail}" if outcome.detail and outcome.result.value == "REJECTED" else ""))
                elif name == "read_turtle_pose":
                    result = backend.observe_state()
                    if goal_sent:
                        verification += 1
                elif name == "get_parameter":
                    result = get_parameter(arguments)
                elif name == "final_answer":
                    answer, ending, done, result = arguments.get("answer"), "final_answer", True, "Answer recorded."
                else:
                    result = f"unknown tool {name}"
                calls.append(name)
                messages.append({"role": "tool", "tool_name": name, "content": result})
                trace.append(dict(kind="tool", name=name, arguments=arguments, content=result))
            if done:
                break
        heading, x, y, still = true_pose()
        verdict = judge(task_id, answer, heading, x, y, still)
        (run_dir).mkdir(parents=True, exist_ok=True)
        (run_dir / "trace.jsonl").write_text("".join(json.dumps(t, default=str) + "\n" for t in trace) + json.dumps(dict(kind="executor_events", events=executor.events), default=str) + "\n")
        return dict(ending=ending, answer=answer, requests=requests, tokens=tokens, seconds=round(time.monotonic() - started, 1), true_heading=round(heading, 4), true_x=round(x, 4), true_y=round(y, 4),
                    turtle_still=still, success=verdict["success"], judge_reasons=verdict["reasons"], executor_final_state=executor.state.value, goals_sent=executor.goals_sent,
                    tool_calls={n: calls.count(n) for n in set(calls)}, pose_reads=calls.count("read_turtle_pose"), verification_calls=verification, rotate_results=rotate_results,
                    prompt_hash=sha(SYSTEM + task["text"]), tools_hash=sha(tools), trace_path=str((run_dir / "trace.jsonl").relative_to(ROOT)), infrastructure=False)
    finally:
        stop(sim)
        time.sleep(1.0)
        left = subprocess.run(["pgrep", "-x", "turtlesim_node"], capture_output=True, text=True).stdout.split()
        if left:
            subprocess.run(["pkill", "-9", "-x", "turtlesim_node"])


def digests():
    with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=30) as response:
        return {m["name"]: m["digest"] for m in json.loads(response.read())["models"]}


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    protocol_hash = (HERE / "PROTOCOL.sha256").read_text().split()[0]
    assert hashlib.sha256((HERE / "PROTOCOL.md").read_bytes()).hexdigest() == protocol_hash, "protocol changed after freezing"
    freeze = json.loads((HERE / "FREEZE.json").read_text()) if (HERE / "FREEZE.json").exists() else None
    if freeze is not None:
        for name, expected in freeze["files"].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, f"frozen file changed: {name}"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = RUNS / f"{phase}_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    (RUNS / "CURRENT.txt").write_text(str(out.relative_to(ROOT)))
    if phase == "smoke":
        sessions = [("qwen3.5:9b", [(t, a, 1) for t in ("S3", "R1", "R2") for a in ("OFF", "ON")])]
    else:
        sessions = [(m, [(t, a, s) for t in TASKS for a in ("OFF", "ON") for s in (1, 2)]) for m in MODELS]
    rng = random.Random(MASTER_SEED)
    backend = TurtlesimBackend("action_study_backend")
    log = HERE / "RESULTS_LOG.jsonl"
    consecutive_infra = 0
    for model, cells in sessions:
        rng.shuffle(cells)
        for index, (task_id, arm, seed) in enumerate(cells):
            run_id = f"{phase}_{stamp}/{model.replace(':', '_')}/{index:03d}-{task_id}-{arm}-s{seed}"
            print(time.strftime("%H:%M:%S"), run_id, flush=True)
            try:
                row = run_episode(backend, model, task_id, arm, seed, RUNS / run_id)
            except Infrastructure as error:
                print("STOP: Ollama unreachable", error, flush=True)
                return 2
            row.update(run_id=run_id, phase=phase, model=model, task=task_id, kind=TASKS[task_id]["kind"], arm=arm, seed=seed, protocol_sha256=protocol_hash)
            with open(log, "a") as handle:
                handle.write(json.dumps(row, default=str) + "\n")
            print({k: row.get(k) for k in ("ending", "requests", "tokens", "success", "verification_calls", "executor_final_state", "seconds")}, flush=True)
            consecutive_infra = consecutive_infra + 1 if row.get("infrastructure") else 0
            if consecutive_infra >= 3:
                print("STOP: simulator not ready in 3 consecutive episodes", flush=True)
                return 3
        unload(model)
    backend.close()
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
