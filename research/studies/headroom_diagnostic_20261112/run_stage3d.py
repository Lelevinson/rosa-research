"""Stage 3d harness (frozen by PROTOCOL_STAGE3D.md): arm A2 on the Stage 3 tasks, Qwen only. New file; Stage 0-3c files are untouched.

A2 = A1 (Stage 3b) plus ONE extra system message with six fixed sentences, placed directly after A1's neutral line.

  uv run python run_stage3d.py check            offline: A2 equals A1 plus the new message and nothing else; hashes; agent construction
  uv run python run_stage3d.py run OUT          24 A2 Qwen episodes, one fixture session, ROS domain 216
  uv run python run_stage3d.py episode ...      one worker episode
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_stage1 as S1  # noqa: E402
import run_stage3 as S3  # noqa: E402  (build_model, TASKS, freeze; unchanged)
import run_stage3b as S3B  # noqa: E402  (prompt_messages_a1, NEUTRAL; unchanged)
import stage3_fixture as FX  # noqa: E402
from menu_run_study import Recorder, ToolRecorder, guarded_native, save  # noqa: E402
from rosa.tools import ros2  # noqa: E402

SEED = 20261117
CAP = 24
PROVIDERS = ["ollama"]

# The six sentences are frozen verbatim and in this order (PROTOCOL_STAGE3D.md). Never edit them after the first inference.
A2_SENTENCES = [
    "Build full node names as namespace plus name from earlier results; never pass a bare name.",
    "Do not repeat a call whose successful result is already in the conversation.",
    "Issue every call whose arguments you already know in the same response.",
    "Make lookups that need no arguments in the same response as your first lookup.",
    "Stop and answer as soon as every requested field has a value from a tool result.",
    "When you must inspect many known entities, request them all in one response.",
]
A2_MESSAGE = ("system", " ".join(A2_SENTENCES))


def prompt_messages_a2():
    """A1's list with exactly one message inserted directly after A1's neutral line."""
    base = S3B.prompt_messages_a1()
    positions = [i for i, msg in enumerate(base) if msg == S3B.NEUTRAL]
    assert len(positions) == 1, "A1's neutral line must appear exactly once"
    return base[:positions[0] + 1] + [A2_MESSAGE] + base[positions[0] + 1:]


def prompt_hash_a2():
    return hashlib.sha256(json.dumps(prompt_messages_a2()).encode()).hexdigest()


class A2ROSA(S1.ROSA):
    """Stock ROSA with only the system-prompt list replaced (runtime override; src/rosa untouched)."""
    def __init__(self, llm, max_iterations):
        super().__init__(ros_version=2, llm=llm, streaming=False, verbose=False, max_iterations=max_iterations, accumulate_chat_history=False)

    def _get_prompts(self, robot_prompts=None):
        return S1.ChatPromptTemplate.from_messages(prompt_messages_a2() + [
            S1.MessagesPlaceholder("chat_history"), ("human", "{input}"), S1.MessagesPlaceholder("agent_scratchpad")])


def episode(args):
    out = Path(args.output)
    out.mkdir(exist_ok=False)
    recorder = Recorder(out / "trace.jsonl")
    task = S3.TASKS[args.task]
    recorder.add("episode_start", task=dict(id=task["id"], depth=task["depth"], floor=task["floor"]), arm="A2", repeat=args.repeat,
                 provider=args.provider, stage="3d", prompt_sha256=prompt_hash_a2(), prompts=prompt_messages_a2())
    ros2.execute_ros_command = guarded_native(recorder)
    answer = error = None
    started = time.perf_counter()
    with contextlib.ExitStack() as stack:
        try:
            base, options = S3.build_model(args.provider, recorder, stack)
            model = S1.TracedModel(holder={"model": base}, recorder=recorder, options=options)
            agent = A2ROSA(model, 40)
            recorder.add("effective_request", request=task["request"])
            result = agent._ROSA__executor.invoke({"input": task["request"], "chat_history": []}, config={"callbacks": [ToolRecorder(recorder)]})
            answer = result["output"]
        except Exception as failure:
            error = repr(failure)
    recorder.add("episode_end", answer=answer, error=error, seconds=time.perf_counter() - started)
    save(out / "answer.json", dict(task=task["id"], provider=args.provider, repeat=args.repeat, answer=answer, error=error))


def run_worker(out, directory, extra, timeout, recorder):
    command = [sys.executable, str(HERE / "run_stage3d.py"), "episode", "--output", str(directory)] + extra
    recorder.add("worker_start", command=command)
    started = time.perf_counter()
    error = None
    with (out / (directory.name + ".worker.log")).open("w") as log:
        import subprocess, signal
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
    record = dict(directory=directory.name, returncode=code, error=error, seconds=time.perf_counter() - started, args=extra)
    with (out / "attempts.jsonl").open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    print(json.dumps(record), flush=True)
    return record


def freeze(out):
    S3.freeze(out)  # Stage 3 sources, vendor, src/rosa, identity
    source = out / "source"
    for name in ["run_stage3d.py", "run_stage3b.py", "PROTOCOL_STAGE3D.md", "stage3_labels.py", "stage3_review.py", "summarize_stage3.py"]:
        shutil.copy2(HERE / name, source / name)
    identity = json.loads((out / "identity.json").read_text())
    identity["source_sha256"] = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob("*") if p.is_file()}
    identity["prompt_sha256"]["A1"] = S3B.prompt_hash_a1()
    identity["prompt_sha256"]["A2"] = prompt_hash_a2()
    identity["prompts"]["A1"] = S3B.prompt_messages_a1()
    identity["prompts"]["A2"] = prompt_messages_a2()
    identity["seeds"]["schedule"] = SEED
    save(out / "identity.json", identity)


def study(out):
    out = Path(out)
    out.mkdir(exist_ok=False)
    for key, value in {"ROS_DOMAIN_ID": "216", "ROS_LOCALHOST_ONLY": "1"}.items():
        assert os.environ.get(key) == value, f"set {key}={value} before running"
    freeze(out)
    recorder = Recorder(out / "setup.jsonl")
    save(out / "protocol_reference.json", dict(protocol="PROTOCOL_STAGE3D.md", arm="A2", providers=PROVIDERS, ollama=S1.OLLAMA))
    with urllib.request.urlopen(S1.OLLAMA + "/api/tags", timeout=15) as response:
        save(out / "ollama-tags.json", json.load(response))
    rng = random.Random(SEED)
    schedule = []
    for repeat in range(2):
        block = [(repeat, t, "ollama") for t in S3.TASKS]
        rng.shuffle(block)
        schedule += block
    save(out / "schedule.json", dict(main=schedule))
    count, processes, handles = 0, None, None
    try:
        S1.assert_domain_empty((FX.NS,), recorder)
        processes, handles = S1.start_processes(FX.commands(), out, "fx", recorder)
        time.sleep(6)
        recorder.add("readiness_summary", fully_listed=S1.wait_for([n["fqn"] for n in FX.GRAPH["nodes"]], recorder, attempts=10))

        def check(label):
            (out / f"oracle-{label}").mkdir()
            bad = FX.oracle(out / f"oracle-{label}", recorder)
            if bad:
                raise RuntimeError(f"oracle mismatch at {label}: {bad[:3]}")

        check("before")
        for index, (repeat, task, provider) in enumerate(schedule):
            if count >= CAP:
                raise RuntimeError("cap reached")
            if any(p.poll() is not None for p in processes):
                raise RuntimeError("Fixture process exited during study")
            destination = out / f"{index:02d}-{task}-{provider}-r{repeat}"
            run_worker(out, destination, ["--provider", provider, "--task", task, "--repeat", str(repeat)], 900, recorder)
            count += 1
            if count == 1 or not (out / "ollama-active-context.json").exists():
                if not S1.check_context(out, "ollama-active-context.json", recorder):
                    raise RuntimeError("Active Ollama context is not 65536; stopping")
            if (index + 1) % 12 == 0 and index + 1 < len(schedule):
                check(f"after-{index + 1:02d}")
        check("after")
    except Exception as failure:
        recorder.add("study_error", error=repr(failure))
        raise
    finally:
        if processes is not None:
            S1.stop_processes(processes, handles, recorder)
            recorder.add("cleanup_ok", ok=S1.verify_empty((FX.NS,), recorder))
        S1.stop_daemon(recorder)


def offline_check():
    a1, a2 = S3B.prompt_messages_a1(), prompt_messages_a2()
    assert len(a2) == len(a1) + 1, "A2 must have exactly one more message than A1"
    added = [m for m in a2 if m not in a1]
    assert added == [A2_MESSAGE], "the only new message must be the six-sentence message"
    assert [m for m in a2 if m != A2_MESSAGE] == a1, "removing the new message must give A1 exactly (same order, same text)"
    index = a2.index(A2_MESSAGE)
    assert a2[index - 1] == S3B.NEUTRAL, "the new message must sit directly after A1's neutral line"
    assert A2_MESSAGE[1].split(". ")[0].startswith("Build full node names") and len(A2_SENTENCES) == 6
    print("A1 messages:", len(a1), "| A2 messages:", len(a2), "| new message at position", index)
    print("A1 sha256", S3B.prompt_hash_a1()); print("A2 sha256", prompt_hash_a2())
    print("A2 message:", A2_MESSAGE[1])

    class Dummy(S1.BaseChatModel):
        @property
        def _llm_type(self):
            return "dummy"
        def bind_tools(self, tools, **kwargs):
            return self
        def _generate(self, *args, **kwargs):
            raise RuntimeError("no inference in offline check")
    agent = A2ROSA(Dummy(), 3)
    texts = "\n".join(m.content for m in agent._ROSA__prompts.format_messages(chat_history=[], input="x", agent_scratchpad=[]))
    assert all(sentence in texts for sentence in A2_SENTENCES) and S3B.NEUTRAL[1] in texts and "Do not batch tool calls" not in texts
    print("tools:", len(agent._ROSA__tools.get_tools()), "| OFFLINE CHECK OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    r = sub.add_parser("run"); r.add_argument("output")
    e = sub.add_parser("episode"); e.add_argument("--output", required=True); e.add_argument("--provider", choices=["ollama"], required=True)
    e.add_argument("--task", required=True); e.add_argument("--repeat", default="0")
    a = parser.parse_args()
    {"check": lambda: offline_check(), "run": lambda: study(a.output), "episode": lambda: episode(a)}[a.command]()
