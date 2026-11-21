"""Action tool S2 tiny model smoke (protocol: PROTOCOL_SMOKE.md, hash in PROTOCOL_SMOKE.sha256). Stand-alone loop; not part of any harness.
  source /opt/ros/jazzy/setup.bash; ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 nohup uv run python research/studies/action_tool_s2_20261118/smoke_loop.py > smoke.log 2>&1 &
One job at a time. Each episode starts a fresh turtlesim_node (heading 0.0), runs a short tool-calling loop against Ollama, then reads the ground truth with a separate node."""
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "action_tool_s1_20261118"))
sys.path.insert(0, str(HERE / "tests"))

from action_executor import ActionExecutor  # noqa: E402
from action_interface import ExecutorOptions, render_for_model, tool_schema  # noqa: E402
from turtlesim_backend import TURTLESIM_POLICY, TurtlesimBackend  # noqa: E402
from test_turtlesim_backend import WallClock, angle_error, start_turtlesim, stop, true_heading  # noqa: E402  (same helpers as the S2 tests)

OLLAMA = os.environ.get("ROSA_OLLAMA_URL", "http://172.30.80.1:11434")  # lab container sets ROSA_OLLAMA_URL
MODEL = "qwen3.5:9b"
MAX_ITERATIONS = 12
EPISODE_SECONDS = 300
SYSTEM = ("You control a simulated turtle in ROS 2 turtlesim. Use the tools to act and to look. Headings are in radians. "
          "When you are done, call final_answer with a JSON object.")
TASKS = {
    "A1": dict(text='Turn the turtle so that it faces heading 1.5 radians, then reply with the heading it ended with as {"heading": <number>}.', final_target=1.5),
    "A2": dict(text='Turn the turtle to heading 2.0 radians and then to heading -1.0 radians (in that order), then reply with its final heading as {"heading": <number>}.', final_target=-1.0),
}
READ_SCHEMA = {"type": "function", "function": {"name": "read_turtle_pose", "description": "Read the turtle's current pose (read-only).",
                                                "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}}
FINAL_SCHEMA = {"type": "function", "function": {"name": "final_answer", "description": "Give the final answer as a JSON object and finish.",
                                                 "parameters": {"type": "object", "properties": {"answer": {"type": "object"}}, "required": ["answer"]}}}


def chat(messages, tools):
    body = json.dumps(dict(model=MODEL, messages=messages, tools=tools, stream=False, think=False,
                           options=dict(temperature=0.7, num_ctx=65536, num_predict=4096))).encode()
    request = urllib.request.Request(OLLAMA + "/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read())


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def run_episode(backend, task_id, arm, out_dir):
    task = TASKS[task_id]
    sim = start_turtlesim()
    try:
        deadline = time.monotonic() + 20
        while backend.readiness() is not None and time.monotonic() < deadline:
            time.sleep(0.3)
        if backend.readiness() is not None:
            return dict(task=task_id, arm=arm, ending="infrastructure: simulator not ready")
        executor = ActionExecutor(TURTLESIM_POLICY, backend, WallClock(), ExecutorOptions(attach_post_action_state=(arm == "ON")))
        executor.begin_episode()
        tools = [tool_schema(TURTLESIM_POLICY.actions["rotate_to_heading"]), READ_SCHEMA, FINAL_SCHEMA]
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task["text"]}]
        transcript = [dict(role="system", content=SYSTEM), dict(role="user", content=task["text"])]
        answer, ending, started, requests, tokens = None, "cap", time.monotonic(), 0, 0
        for _ in range(MAX_ITERATIONS):
            if time.monotonic() - started > EPISODE_SECONDS:
                ending = "timeout"
                break
            reply = chat(messages, tools)
            requests += 1
            tokens += reply.get("prompt_eval_count", 0) + reply.get("eval_count", 0)
            message = reply["message"]
            messages.append(message)
            transcript.append(dict(role="assistant", content=message.get("content"), tool_calls=message.get("tool_calls")))
            calls = message.get("tool_calls") or []
            if not calls:
                ending, answer = "text", message.get("content")
                break
            done = False
            for call in calls:
                name, arguments = call["function"]["name"], call["function"].get("arguments") or {}
                if name == "rotate_to_heading":
                    result = render_for_model(executor.execute(name, arguments))
                elif name == "read_turtle_pose":
                    result = backend.observe_state()
                elif name == "final_answer":
                    answer, ending, done, result = arguments.get("answer"), "final_answer", True, "Answer recorded."
                else:
                    result = f"unknown tool {name}"
                messages.append({"role": "tool", "tool_name": name, "content": result})
                transcript.append(dict(role="tool", name=name, arguments=arguments, content=result))
            if done:
                break
        # ground truth: turtle still for 1 s, then an independent read
        first = true_heading()
        time.sleep(1.0)
        second = true_heading()
        still = angle_error(first, second) < 0.01
        truth = second
        reported = None
        if isinstance(answer, str):
            try:
                answer = json.loads(answer)
            except ValueError:
                pass
        if isinstance(answer, dict) and isinstance(answer.get("heading"), (int, float)):
            reported = float(answer["heading"])
        success = reported is not None and angle_error(truth, task["final_target"]) < 0.1 and angle_error(reported, truth) < 0.1
        row = dict(task=task_id, arm=arm, ending=ending, answer=answer, requests=requests, tokens=tokens, seconds=round(time.monotonic() - started, 1),
                   true_heading=round(truth, 3), reported=reported, turtle_still=still, success_judge=success,
                   executor_final_state=executor.state.value, goals_sent=executor.goals_sent,
                   prompt_hash=sha(SYSTEM + task["text"]), tools_hash=sha(tools), executor_events=executor.events, transcript=transcript)
        return row
    finally:
        stop(sim)
        time.sleep(1.0)


def main():
    out_dir = HERE
    protocol_hash = (HERE / "PROTOCOL_SMOKE.sha256").read_text().split()[0]
    assert hashlib.sha256((HERE / "PROTOCOL_SMOKE.md").read_bytes()).hexdigest() == protocol_hash, "protocol changed after freezing"
    cells = [(t, a) for t in TASKS for a in ("OFF", "ON")]
    random.Random(20261124).shuffle(cells)
    backend = TurtlesimBackend("s2_smoke_backend")
    rows = []
    for task_id, arm in cells:
        print(time.strftime("%H:%M:%S"), "episode", task_id, arm, flush=True)
        row = run_episode(backend, task_id, arm, out_dir)
        row["protocol_sha256"] = protocol_hash
        rows.append(row)
        with open(out_dir / "SMOKE_RESULTS.jsonl", "a") as handle:
            handle.write(json.dumps(row, default=str) + "\n")
        print({k: row.get(k) for k in ("task", "arm", "ending", "requests", "seconds", "true_heading", "reported", "success_judge", "executor_final_state", "turtle_still")}, flush=True)
    backend.close()
    urllib.request.urlopen(urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps(dict(model=MODEL, keep_alive=0)).encode(), headers={"Content-Type": "application/json"}), timeout=30).read()
    print("done", flush=True)


if __name__ == "__main__":
    main()
