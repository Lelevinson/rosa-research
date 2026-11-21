"""Pilot runner: one episode worker, one fixture session, shared by Step A (model check), Step D (pilot) and the harm fixture check.

  uv run python run_pilot.py episode --output DIR --env stage3|e1h --task ID --arm ARM --model NAME --seed N --temperature T
  uv run python run_pilot.py session OUT PLAN.json     run a list of cells in one fixture session (ROS domain 220)

A cell is {"env","task","arm","model","seed","temperature"}. Arms S0 and A1 need no handlers (stock tools); every other arm
is built by harness.py. src/rosa is not edited: prompts and tools are replaced inside this study's ROSA subclass.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
STAGE3 = HERE.parent / "headroom_diagnostic_20261112"
sys.path.insert(0, str(STAGE3))
sys.path.insert(0, str(HERE))
import run_stage1 as S1  # noqa: E402  (TracedModel, ROSA, prompts, fixture helpers; unchanged Stage 1-3 code)
import run_stage3b as S3B  # noqa: E402  (A1 prompt)
from menu_run_study import Recorder, ToolRecorder, guarded_native, save  # noqa: E402
from rosa.tools import ros2  # noqa: E402

DOMAIN = "220"
MAX_ITERATIONS = 40
NUM_CTX = 65536
NUM_PREDICT = 4096


def prompt_for(arm):
    """S0 = stock ROSA prompt unchanged; A1 = Stage 3b prompt; engineered arms add their lines in harness.py."""
    if arm == "S0":
        return S1.prompt_messages("A_orig")
    return S3B.prompt_messages_a1()


def prompt_hash(messages):
    return hashlib.sha256(json.dumps(messages).encode()).hexdigest()


def build_chat_model(model, temperature, seed):
    from langchain_ollama import ChatOllama
    return ChatOllama(model=model, base_url=S1.OLLAMA, temperature=temperature, seed=seed, reasoning=False,
                      num_predict=NUM_PREDICT, num_ctx=NUM_CTX, client_kwargs={"timeout": 90})


def load_env(name):
    if name == "stage3":
        import stage3_fixture as env
    else:
        import e1h_fixture as env
    return env


class PilotROSA(S1.ROSA):
    """Stock ROSA whose prompt list and tool list come from an arm object (runtime override; src/rosa untouched)."""
    def __init__(self, llm, arm, max_iterations=MAX_ITERATIONS):
        self.pilot_arm = arm
        super().__init__(ros_version=2, llm=llm, streaming=False, verbose=False, max_iterations=max_iterations, accumulate_chat_history=False)

    def _get_prompts(self, robot_prompts=None):
        return S1.ChatPromptTemplate.from_messages(self.pilot_arm.prompt_messages + [
            S1.MessagesPlaceholder("chat_history"), ("human", "{input}"), S1.MessagesPlaceholder("agent_scratchpad")])

    def _get_agent(self):
        from langchain.agents import create_tool_calling_agent
        self.pilot_tools = self.pilot_arm.wrap_tools(self._ROSA__tools.get_tools())
        return create_tool_calling_agent(llm=self._ROSA__llm, tools=self.pilot_tools, prompt=self._ROSA__prompts)

    def _get_executor(self, verbose):
        return self.pilot_arm.make_executor(agent=self._ROSA__agent, tools=self.pilot_tools, max_iterations=MAX_ITERATIONS)


class StockArm:
    """S0 and A1: stock tools, stock executor, no handlers."""
    def __init__(self, name, recorder):
        self.name, self.recorder = name, recorder
        self.prompt_messages = prompt_for(name)

    def wrap_tools(self, tools):
        return tools

    def visible_schemas(self, schemas, messages):
        return schemas

    def make_executor(self, agent, tools, max_iterations):
        from langchain.agents import AgentExecutor
        return AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=max_iterations, handle_parsing_errors=True)

    def close(self):
        pass


def make_arm(name, recorder, context):
    if name in ("S0", "A1"):
        return StockArm(name, recorder)
    import harness
    return harness.make_arm(name, recorder, context, prompt_for('A1'))


class ArmTracedModel(S1.TracedModel):
    """TracedModel whose tool list is decided per request by the arm (this is where per-request binding happens)."""
    arm: object

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        kwargs["tools"] = self.arm.visible_schemas(kwargs.get("tools", []), messages)
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def episode(args):
    out = Path(args.output)
    out.mkdir(exist_ok=False)
    recorder = Recorder(out / "trace.jsonl")
    env = load_env(args.env)
    task = next(t for t in env.TASKS if t["id"] == args.task)
    context = dict(env=args.env, task=task, ns=env.NS)
    arm = make_arm(args.arm, recorder, context)
    recorder.add("episode_start", task=dict(id=task["id"], floor=task["floor"], depth=task.get("depth")), env=args.env, arm=args.arm,
                 model=args.model, seed=args.seed, temperature=args.temperature, prompt_sha256=prompt_hash(arm.prompt_messages),
                 prompts=arm.prompt_messages, num_ctx=NUM_CTX, num_predict=NUM_PREDICT, max_iterations=MAX_ITERATIONS)
    ros2.execute_ros_command = guarded_native(recorder)
    hook = env.EpisodeHook(recorder) if hasattr(env, "EpisodeHook") else None
    answer = error = None
    started = time.perf_counter()
    try:
        if hook:
            hook.start()
        base = build_chat_model(args.model, args.temperature, args.seed)
        model = ArmTracedModel(holder={"model": base}, recorder=recorder, options={}, arm=arm)
        agent = PilotROSA(model, arm)
        recorder.add("effective_request", request=task["request"])
        result = agent._ROSA__executor.invoke({"input": task["request"], "chat_history": []}, config={"callbacks": [ToolRecorder(recorder)]})
        answer = result["output"]
    except Exception as failure:
        error = repr(failure)
    finally:
        arm.close()
        if hook:
            hook.stop()
    recorder.add("episode_end", answer=answer, error=error, seconds=time.perf_counter() - started)
    save(out / "answer.json", dict(task=task["id"], arm=args.arm, model=args.model, seed=args.seed, answer=answer, error=error))


def run_worker(out, directory, cell, timeout, recorder):
    command = [sys.executable, str(HERE / "run_pilot.py"), "episode", "--output", str(directory), "--env", cell["env"], "--task", cell["task"],
               "--arm", cell["arm"], "--model", cell["model"], "--seed", str(cell["seed"]), "--temperature", str(cell["temperature"])]
    recorder.add("worker_start", command=command)
    started = time.perf_counter()
    error = None
    with (out / (directory.name + ".worker.log")).open("w") as log:
        import signal
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


def write_reached_ros(directory):
    """Native commands that were actually started (ros_start) and are not observation-only. The study guard should make this impossible."""
    trace = directory / "trace.jsonl"
    if not trace.exists():
        return []
    found = []
    for line in trace.read_text().splitlines():
        event = json.loads(line)
        if event["kind"] == "ros_start" and tuple(event["command"][1:3]) in {("param", "set"), ("service", "call"), ("topic", "pub")}:
            found.append(event["command"])
    return found


def check_ollama_context(out, model, recorder):
    with urllib.request.urlopen(S1.OLLAMA + "/api/ps", timeout=10) as response:
        active = json.load(response)
    save(out / f"active-context-{model.replace(':', '_')}.json", active)
    ok = any(m["name"] == model and m.get("context_length") == NUM_CTX for m in active.get("models", []))
    recorder.add("context_check", model=model, ok=ok, models=active.get("models"))
    return ok


def session(out, plan_path, wall_limit_hours=10.0):
    """Run cells in order in one fixture session per environment. Stop rules: Ollama unreachable, oracle mismatch, cleanup failure, wall limit."""
    out = Path(out)
    out.mkdir(exist_ok=False)
    for key, value in {"ROS_DOMAIN_ID": DOMAIN, "ROS_LOCALHOST_ONLY": "1"}.items():
        assert os.environ.get(key) == value, f"set {key}={value} before running"
    plan = json.loads(Path(plan_path).read_text())
    save(out / "plan.json", plan)
    recorder = Recorder(out / "setup.jsonl")
    envs = sorted({c["env"] for c in plan})
    assert len(envs) == 1, "one environment per session"
    env = load_env(envs[0])
    deadline = time.time() + wall_limit_hours * 3600
    processes = handles = None
    seen_models = set()
    try:
        S1.assert_domain_empty((env.NS,), recorder)
        processes, handles = S1.start_processes(env.commands(), out, "fx", recorder)
        time.sleep(6)
        recorder.add("readiness_summary", fully_listed=S1.wait_for([n["fqn"] for n in env.GRAPH["nodes"]], recorder, attempts=10))

        def oracle(label):
            """A CLI timeout while reading the oracle is retried (logged); a mismatch is never retried and stops the session."""
            (out / f"oracle-{label}").mkdir()
            for attempt in range(3):
                try:
                    bad = env.oracle(out / f"oracle-{label}", recorder)
                    break
                except subprocess.TimeoutExpired as failure:
                    recorder.add("oracle_cli_timeout", label=label, attempt=attempt, command=failure.cmd)
                    time.sleep(5)
            else:
                raise RuntimeError(f"oracle could not be read at {label} (3 CLI timeouts)")
            if bad:
                raise RuntimeError(f"oracle mismatch at {label}: {bad[:3]}")
        oracle("before")
        for index, cell in enumerate(plan):
            if time.time() > deadline:
                raise RuntimeError("wall-time limit reached")
            if any(p.poll() is not None for p in processes):
                raise RuntimeError("fixture process exited during session")
            try:
                urllib.request.urlopen(S1.OLLAMA + "/api/tags", timeout=15).read()
            except Exception as failure:
                raise RuntimeError(f"Ollama unreachable: {failure!r}")
            directory = out / f"{index:03d}-{cell['task']}-{cell['arm']}-{cell['model'].replace(':', '_')}-s{cell['seed']}"
            run_worker(out, directory, cell, 900, recorder)
            reached = write_reached_ros(directory)
            if reached:  # stop rule: any write tool reaching ROS
                raise RuntimeError(f"write command reached ROS in {directory.name}: {reached[:2]}")
            if cell["model"] not in seen_models:
                seen_models.add(cell["model"])
                if not check_ollama_context(out, cell["model"], recorder):
                    recorder.add("context_not_65536", model=cell["model"])
            if (index + 1) % 12 == 0 and index + 1 < len(plan):
                oracle(f"after-{index + 1:03d}")
        oracle("after")
    except Exception as failure:
        recorder.add("session_error", error=repr(failure))
        print("SESSION STOPPED:", repr(failure), flush=True)
        raise
    finally:
        if processes is not None:
            S1.stop_processes(processes, handles, recorder)
            recorder.add("cleanup_ok", ok=S1.verify_empty((env.NS,), recorder))
        S1.stop_daemon(recorder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    e = sub.add_parser("episode")
    for flag in ["--output", "--env", "--task", "--arm", "--model", "--temperature"]:
        e.add_argument(flag, required=True)
    e.add_argument("--seed", type=int, required=True)
    s = sub.add_parser("session")
    s.add_argument("output")
    s.add_argument("plan")
    a = parser.parse_args()
    if a.command == "episode":
        a.temperature = float(a.temperature)
        episode(a)
    else:
        session(a.output, a.plan)
