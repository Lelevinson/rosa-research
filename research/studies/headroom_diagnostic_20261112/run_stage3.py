"""Stage 3 harness (frozen by PROTOCOL_STAGE3.md). Run with: uv run python run_stage3.py <command> ...

  run OUTDIR [--providers ollama openai]   pilot (4 Qwen) then the 48-episode main run, one fixture session
  episode ...                              one worker episode (spawned by run)
Domain 214, localhost only, must be set by the caller.
"""
import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_stage1 as S1  # noqa: E402  (prompt override, traced model, fixture helpers)
import stage3_fixture as FX  # noqa: E402
from menu_run_study import Recorder, ToolRecorder, guarded_native, save  # noqa: E402
from rosa.tools import ros2  # noqa: E402

TASKS = {t["id"]: t for t in FX.TASKS}
PILOT = ["u2", "p3", "v4", "h3"]
SEED = 20261114
CAP = 52


def build_model(provider, recorder, stack):
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=S1.QWEN, base_url=S1.OLLAMA, temperature=0, seed=42, reasoning=False, num_predict=4096,
                          num_ctx=65536, client_kwargs={"timeout": 90}), {}
    from dataclasses import replace
    from rosa_llm import Config, create_client
    from rosa_llm.langchain import ChatRosaLLM
    config = replace(Config.load(), provider="openai", openai_model=S1.LUNA, require_explicit_model=True, timeout=90)
    client = stack.enter_context(create_client(config, observer=lambda record: recorder.add("provider_record", record=record)))
    return ChatRosaLLM(client=client, allowed_tools=None, cache=False), {"parallel_tool_calls": True}


def episode(args):
    out = Path(args.output)
    out.mkdir(exist_ok=False)
    recorder = Recorder(out / "trace.jsonl")
    task = TASKS[args.task]
    recorder.add("episode_start", task=dict(id=task["id"], depth=task["depth"], floor=task["floor"]), arm="A0", repeat=args.repeat,
                 provider=args.provider, stage="3", prompt_sha256=S1.prompt_hash("A0"), prompts=S1.prompt_messages("A0"))
    ros2.execute_ros_command = guarded_native(recorder)
    answer = error = None
    started = time.perf_counter()
    with contextlib.ExitStack() as stack:
        try:
            base, options = build_model(args.provider, recorder, stack)
            model = S1.TracedModel(holder={"model": base}, recorder=recorder, options=options)
            agent = S1.StageROSA(model, "A0", 40)
            recorder.add("effective_request", request=task["request"])
            result = agent._ROSA__executor.invoke({"input": task["request"], "chat_history": []}, config={"callbacks": [ToolRecorder(recorder)]})
            answer = result["output"]
        except Exception as failure:
            error = repr(failure)
    recorder.add("episode_end", answer=answer, error=error, seconds=time.perf_counter() - started)
    save(out / "answer.json", dict(task=task["id"], provider=args.provider, repeat=args.repeat, answer=answer, error=error))


def run_worker(out, directory, extra, timeout, recorder):
    command = [sys.executable, str(HERE / "run_stage3.py"), "episode", "--output", str(directory)] + extra
    recorder.add("worker_start", command=command)
    started = time.perf_counter()
    error = None
    with (out / (directory.name + ".worker.log")).open("w") as log:
        worker = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = worker.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            import signal
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
    source = out / "source"
    names = ["run_stage3.py", "run_stage1.py", "stage3_build.py", "stage3_node.py", "stage3_fixture.py", "stage3_graph.json", "stage3_tasks.json",
             "score_stage3.py", "score_stage1.py", "PROTOCOL_STAGE3.md", "CODEBOOK.md", "STAGE3_USE_CASES.md"]
    for name in names:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HERE / name, target)
    shutil.copytree(HERE / "vendor", source / "vendor", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(S1.ROOT / "src/rosa", source / "src/rosa", ignore=shutil.ignore_patterns("__pycache__"))
    for name in ["pyproject.toml", "uv.lock"]:
        shutil.copy2(S1.ROOT / name, source / name)
    hashes = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob("*") if p.is_file()}
    git = lambda *a: subprocess.check_output(["git", *a], cwd=S1.ROOT, text=True).strip()
    packages = {n: importlib.metadata.version(n) for n in ["jpl-rosa", "rosa-llm", "langchain", "langchain-core", "langchain-ollama", "ollama"] if S1._installed(n)}
    save(out / "identity.json", dict(utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), head=git("rev-parse", "HEAD"), branch=git("branch", "--show-current"),
         status=git("status", "--short"), python=sys.version, packages=packages, source_sha256=hashes, prompt_sha256={"A0": S1.prompt_hash("A0")},
         prompts={"A0": S1.prompt_messages("A0")}, seeds=dict(graph=20261113, schedule=SEED, ollama=42),
         environment={k: os.environ.get(k) for k in ["ROS_DISTRO", "ROS_DOMAIN_ID", "ROS_LOCALHOST_ONLY", "RMW_IMPLEMENTATION"]}))


def study(out, providers):
    out = Path(out)
    out.mkdir(exist_ok=False)
    for key, value in {"ROS_DOMAIN_ID": "214", "ROS_LOCALHOST_ONLY": "1"}.items():
        assert os.environ.get(key) == value, f"set {key}={value} before running"
    freeze(out)
    recorder = Recorder(out / "setup.jsonl")
    save(out / "protocol_reference.json", dict(protocol="PROTOCOL_STAGE3.md", providers=providers, ollama=S1.OLLAMA, strong_model=S1.LUNA))
    if "ollama" in providers:
        with urllib.request.urlopen(S1.OLLAMA + "/api/tags", timeout=15) as response:
            save(out / "ollama-tags.json", json.load(response))
    rng = random.Random(SEED)
    schedule = []
    for repeat in range(2):
        block = [(repeat, t, p) for t in TASKS for p in providers]
        rng.shuffle(block)
        schedule += block
    pilot = [("pilot", t, "ollama") for t in PILOT] if "ollama" in providers else []
    save(out / "schedule.json", dict(pilot=pilot, main=schedule))
    active = list(providers)
    count = 0
    processes = handles = None
    try:
        S1.assert_domain_empty((FX.NS,), recorder)
        processes, handles = S1.start_processes(FX.commands(), out, "fx", recorder)
        time.sleep(6)
        listed = S1.wait_for([n["fqn"] for n in FX.GRAPH["nodes"]], recorder, attempts=10)
        recorder.add("readiness_summary", fully_listed=listed)

        def check(label):
            (out / f"oracle-{label}").mkdir()
            bad = FX.oracle(out / f"oracle-{label}", recorder)
            if bad:
                raise RuntimeError(f"oracle mismatch at {label}: {bad[:3]}")

        check("before")
        def one(index, label, task, provider):
            nonlocal count
            if count >= CAP:
                raise RuntimeError("cap reached")
            if any(p.poll() is not None for p in processes):
                raise RuntimeError("Fixture process exited during study")
            destination = out / (f"pilot-{task}-{provider}" if label == "pilot" else f"{index:02d}-{task}-{provider}-r{label}")
            timeout = 900 if provider == "ollama" else 600
            run_worker(out, destination, ["--provider", provider, "--task", task, "--repeat", str(label)], timeout, recorder)
            count += 1
            if provider == "ollama" and count == 1 and not S1.check_context(out, "ollama-active-context.json", recorder):
                raise RuntimeError("Active Ollama context is not 65536; stopping")
            if provider == "openai":
                text = (destination / "trace.jsonl").read_text() if (destination / "trace.jsonl").exists() else ""
                if "model_error" in text and '"answer": null' in text.split('"kind": "episode_end"')[-1][:400]:
                    recorder.add("provider_stop", directory=destination.name)
                    active.remove("openai")
                    print(f"STOP strong-model part after {destination.name}", flush=True)
        for index, (label, task, provider) in enumerate(pilot):
            one(index, label, task, provider)
        check("after-pilot")
        for index, (repeat, task, provider) in enumerate(schedule):
            if provider not in active:
                recorder.add("skipped_after_provider_stop", task=task, provider=provider, repeat=repeat)
                continue
            one(index, repeat, task, provider)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run"); r.add_argument("output"); r.add_argument("--providers", nargs="+", default=["ollama", "openai"])
    e = sub.add_parser("episode"); e.add_argument("--output", required=True); e.add_argument("--provider", choices=["ollama", "openai"], required=True)
    e.add_argument("--task", required=True); e.add_argument("--repeat", default="0")
    a = parser.parse_args()
    study(a.output, a.providers) if a.command == "run" else episode(a)
