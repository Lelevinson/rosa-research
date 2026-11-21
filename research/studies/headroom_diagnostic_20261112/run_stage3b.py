"""Stage 3b harness (frozen by PROTOCOL_STAGE3B.md): arm A1 on the Stage 3 tasks. New file; Stage 0-3 files are untouched.

  uv run python run_stage3b.py check            offline: prompt lists, hashes, offline agent construction (no inference)
  uv run python run_stage3b.py run OUT          48 A1 episodes (Qwen and Luna), one fixture session, ROS domain 215
  uv run python run_stage3b.py episode ...      one worker episode
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
import run_stage3 as S3  # noqa: E402  (build_model, TASKS; unchanged)
import stage3_fixture as FX  # noqa: E402
from menu_run_study import Recorder, ToolRecorder, guarded_native, save  # noqa: E402
from rosa.tools import ros2  # noqa: E402

SEED = 20261115
CAP = 48
NEUTRAL = ("system", "Use the task text and earlier tool results to decide which tool to call next; list entities only when you do not already know their names.")
DISCOVERY = ("CRITICAL - TOOL USAGE REQUIREMENT:", "WORKFLOW FOR ACTION REQUESTS:", "When asked to provide names of topics or nodes, first retrieve")


def prompt_messages_a1():
    """A0's list with the three discovery-first stock messages replaced by one neutral line (at the first one's position)."""
    base = S1.prompt_messages("A0")
    hits = [i for i, (_, t) in enumerate(base) if any(m in t for m in DISCOVERY)]
    assert len(hits) == 3, f"expected 3 discovery-first messages, found {len(hits)}"
    out = []
    for i, msg in enumerate(base):
        if i == hits[0]:
            out.append(NEUTRAL)
        elif i not in hits:
            out.append(msg)
    text = " ".join(t for _, t in out)
    assert "rosnode_list" not in text and "check what is available" not in text and "first retrieve a list" not in text
    assert "Do not batch tool calls" not in text and "Independent tool calls whose arguments are already known" in text
    return out


def prompt_hash_a1():
    return hashlib.sha256(json.dumps(prompt_messages_a1()).encode()).hexdigest()


class A1ROSA(S1.ROSA):
    """Stock ROSA with only the system-prompt list replaced (runtime override; src/rosa untouched)."""
    def __init__(self, llm, max_iterations):
        super().__init__(ros_version=2, llm=llm, streaming=False, verbose=False, max_iterations=max_iterations, accumulate_chat_history=False)

    def _get_prompts(self, robot_prompts=None):
        return S1.ChatPromptTemplate.from_messages(prompt_messages_a1() + [
            S1.MessagesPlaceholder("chat_history"), ("human", "{input}"), S1.MessagesPlaceholder("agent_scratchpad")])


def episode(args):
    out = Path(args.output)
    out.mkdir(exist_ok=False)
    recorder = Recorder(out / "trace.jsonl")
    task = S3.TASKS[args.task]
    recorder.add("episode_start", task=dict(id=task["id"], depth=task["depth"], floor=task["floor"]), arm="A1", repeat=args.repeat,
                 provider=args.provider, stage="3b", prompt_sha256=prompt_hash_a1(), prompts=prompt_messages_a1())
    ros2.execute_ros_command = guarded_native(recorder)
    answer = error = None
    started = time.perf_counter()
    with contextlib.ExitStack() as stack:
        try:
            base, options = S3.build_model(args.provider, recorder, stack)
            model = S1.TracedModel(holder={"model": base}, recorder=recorder, options=options)
            agent = A1ROSA(model, 40)
            recorder.add("effective_request", request=task["request"])
            result = agent._ROSA__executor.invoke({"input": task["request"], "chat_history": []}, config={"callbacks": [ToolRecorder(recorder)]})
            answer = result["output"]
        except Exception as failure:
            error = repr(failure)
    recorder.add("episode_end", answer=answer, error=error, seconds=time.perf_counter() - started)
    save(out / "answer.json", dict(task=task["id"], provider=args.provider, repeat=args.repeat, answer=answer, error=error))


def run_worker(out, directory, extra, timeout, recorder):
    command = [sys.executable, str(HERE / "run_stage3b.py"), "episode", "--output", str(directory)] + extra
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
    for name in ["run_stage3b.py", "PROTOCOL_STAGE3B.md", "stage3_labels.py", "stage3_review.py", "summarize_stage3.py"]:
        shutil.copy2(HERE / name, source / name)
    identity = json.loads((out / "identity.json").read_text())
    identity["source_sha256"] = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob("*") if p.is_file()}
    identity["prompt_sha256"]["A1"] = prompt_hash_a1()
    identity["prompts"]["A1"] = prompt_messages_a1()
    identity["seeds"]["schedule"] = SEED
    save(out / "identity.json", identity)


def study(out, providers):
    out = Path(out)
    out.mkdir(exist_ok=False)
    for key, value in {"ROS_DOMAIN_ID": "215", "ROS_LOCALHOST_ONLY": "1"}.items():
        assert os.environ.get(key) == value, f"set {key}={value} before running"
    freeze(out)
    recorder = Recorder(out / "setup.jsonl")
    save(out / "protocol_reference.json", dict(protocol="PROTOCOL_STAGE3B.md", arm="A1", providers=providers, ollama=S1.OLLAMA, strong_model=S1.LUNA))
    if "ollama" in providers:
        with urllib.request.urlopen(S1.OLLAMA + "/api/tags", timeout=15) as response:
            save(out / "ollama-tags.json", json.load(response))
    rng = random.Random(SEED)
    schedule = []
    for repeat in range(2):
        block = [(repeat, t, p) for t in S3.TASKS for p in providers]
        rng.shuffle(block)
        schedule += block
    save(out / "schedule.json", dict(main=schedule))
    active, count, processes, handles = list(providers), 0, None, None
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
            if provider not in active:
                recorder.add("skipped_after_provider_stop", task=task, provider=provider, repeat=repeat)
                continue
            if count >= CAP:
                raise RuntimeError("cap reached")
            if any(p.poll() is not None for p in processes):
                raise RuntimeError("Fixture process exited during study")
            destination = out / f"{index:02d}-{task}-{provider}-r{repeat}"
            run_worker(out, destination, ["--provider", provider, "--task", task, "--repeat", str(repeat)], 900 if provider == "ollama" else 600, recorder)
            count += 1
            if provider == "ollama" and count == 1 or (provider == "ollama" and not (out / "ollama-active-context.json").exists()):
                if not S1.check_context(out, "ollama-active-context.json", recorder):
                    raise RuntimeError("Active Ollama context is not 65536; stopping")
            if provider == "openai":
                text = (destination / "trace.jsonl").read_text() if (destination / "trace.jsonl").exists() else ""
                if "model_error" in text and '"answer": null' in text.split('"kind": "episode_end"')[-1][:400]:
                    recorder.add("provider_stop", directory=destination.name)
                    active.remove("openai")
                    print(f"STOP strong-model part after {destination.name}", flush=True)
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
    a0, a1 = S1.prompt_messages("A0"), prompt_messages_a1()
    removed = [t for _, t in a0 if t not in [x for _, x in a1]]
    print("A0 messages:", len(a0), "| A1 messages:", len(a1), "| removed:", len(removed), "| added:", [t for _, t in a1 if t not in [x for _, x in a0]])
    for t in removed:
        print("REMOVED:", t[:100].replace("\n", " "), "...")
    print("A0 sha256", S1.prompt_hash("A0")); print("A1 sha256", prompt_hash_a1())
    class Dummy(S1.BaseChatModel):
        @property
        def _llm_type(self):
            return "dummy"
        def bind_tools(self, tools, **kwargs):
            return self
        def _generate(self, *args, **kwargs):
            raise RuntimeError("no inference in offline check")
    agent = A1ROSA(Dummy(), 3)
    texts = "\n".join(m.content for m in agent._ROSA__prompts.format_messages(chat_history=[], input="x", agent_scratchpad=[]))
    assert NEUTRAL[1] in texts and "rosnode_list" not in texts and "Do not batch tool calls" not in texts
    print("tools:", len(agent._ROSA__tools.get_tools()), "| OFFLINE CHECK OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    r = sub.add_parser("run"); r.add_argument("output"); r.add_argument("--providers", nargs="+", default=["ollama", "openai"])
    e = sub.add_parser("episode"); e.add_argument("--output", required=True); e.add_argument("--provider", choices=["ollama", "openai"], required=True)
    e.add_argument("--task", required=True); e.add_argument("--repeat", default="0")
    a = parser.parse_args()
    {"check": lambda: offline_check(), "run": lambda: study(a.output, a.providers) if a.command == "run" else None, "episode": lambda: episode(a)}[a.command]()
