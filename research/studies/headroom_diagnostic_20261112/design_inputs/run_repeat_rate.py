"""Repeat-rate measurement (addendum ROSA_repeat_rate_three_models_addendum.md): gpt-oss:20b, lfm3:1.7b, ornith-1.5:9b on the 12 Stage 3 tasks x 2 repeats, arm A1.
Same harness as run_smoke.py and Stage 3b (temperature 0, seed 42, num_ctx 65536, num_predict 4096, 40 iterations, reasoning=False, observation-only guard).
No per-model changes. Ollama only; no API key. Uses only stage3_tasks.json (never the held-out task file).

  uv run python run_repeat_rate.py check          offline: A1 hash equals Stage 3b; client builds for each model
  uv run python run_repeat_rate.py run OUT        3 models x 24 episodes, one fixture session, ROS domain 218, 3 hour cap
  uv run python run_repeat_rate.py episode ...    one worker episode
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY))
import run_stage1 as S1  # noqa: E402
import run_stage3 as S3  # noqa: E402
import run_stage3b as S3B  # noqa: E402
import stage3_fixture as FX  # noqa: E402
from menu_run_study import Recorder, ToolRecorder, guarded_native, save  # noqa: E402
from rosa.tools import ros2  # noqa: E402

MODELS = ["gpt-oss:20b", "lfm3:1.7b", "ornith-1.5:9b"]
SEED = 20261118
CAP_SECONDS = 3 * 3600
STAGE3B_A1_SHA = "7acbb0555cba9f406f4915e6d96da1d69bfdf7360d48c2d37c40e4232954a209"


def build_model(model_name):
    from langchain_ollama import ChatOllama
    # Identical to the Stage 3b Qwen settings (run_stage3.build_model); only the model name is different.
    return ChatOllama(model=model_name, base_url=S1.OLLAMA, temperature=0, seed=42, reasoning=False, num_predict=4096,
                      num_ctx=65536, client_kwargs={"timeout": 90})


def tag(model_name):
    return model_name.replace(":", "_").replace("/", "_")


def episode(args):
    out = Path(args.output)
    out.mkdir(exist_ok=False)
    recorder = Recorder(out / "trace.jsonl")
    task = S3.TASKS[args.task]
    recorder.add("episode_start", task=dict(id=task["id"], depth=task["depth"], floor=task["floor"]), arm="A1", repeat=args.repeat, provider="ollama",
                 model=args.model, stage="repeat-rate", prompt_sha256=S3B.prompt_hash_a1(), prompts=S3B.prompt_messages_a1())
    ros2.execute_ros_command = guarded_native(recorder)
    answer = error = None
    started = time.perf_counter()
    try:
        model = S1.TracedModel(holder={"model": build_model(args.model)}, recorder=recorder, options={})
        agent = S3B.A1ROSA(model, 40)
        recorder.add("effective_request", request=task["request"])
        result = agent._ROSA__executor.invoke({"input": task["request"], "chat_history": []}, config={"callbacks": [ToolRecorder(recorder)]})
        answer = result["output"]
    except Exception as failure:
        error = repr(failure)
    recorder.add("episode_end", answer=answer, error=error, seconds=time.perf_counter() - started)
    save(out / "answer.json", dict(task=task["id"], model=args.model, repeat=args.repeat, answer=answer, error=error))


def run_worker(out, directory, extra, timeout, recorder, attempts_file):
    import subprocess, signal
    command = [sys.executable, str(HERE / "run_repeat_rate.py"), "episode", "--output", str(directory)] + extra
    recorder.add("worker_start", command=command)
    started = time.perf_counter()
    error = None
    with (out / (directory.name + ".worker.log")).open("w") as log:
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
    with attempts_file.open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    print(json.dumps(record), flush=True)
    return record


def active_models():
    with urllib.request.urlopen(S1.OLLAMA + "/api/ps", timeout=15) as response:
        return json.load(response)


def study(out):
    import random
    out = Path(out)
    out.mkdir(exist_ok=False)
    for key, value in {"ROS_DOMAIN_ID": "218", "ROS_LOCALHOST_ONLY": "1"}.items():
        assert os.environ.get(key) == value, f"set {key}={value} before running"
    S3.freeze(out)
    source = out / "source"
    for name in ["design_inputs/run_repeat_rate.py", "run_stage3b.py", "stage3_labels.py", "stage3_review.py"]:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STUDY / name, target)
    recorder = Recorder(out / "setup.jsonl")
    shown = {}
    for name in MODELS:
        request = urllib.request.Request(S1.OLLAMA + "/api/show", data=json.dumps({"model": name}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=30) as response:
            d = json.load(response)
        shown[name] = dict(capabilities=d.get("capabilities"), details=d.get("details"), parameters=d.get("parameters"),
                           context_length={k: v for k, v in d.get("model_info", {}).items() if "context_length" in k}, modified_at=d.get("modified_at"))
    save(out / "model_show.json", shown)
    with urllib.request.urlopen(S1.OLLAMA + "/api/tags", timeout=15) as response:
        save(out / "ollama-tags.json", json.load(response))
    rng = random.Random(SEED)
    schedule = []
    for repeat in range(2):
        block = [(repeat, t) for t in S3.TASKS]
        rng.shuffle(block)
        schedule += block
    save(out / "schedule.json", dict(seed=SEED, models=MODELS, main=schedule))
    started = time.monotonic()
    processes = handles = None
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
        for model_name in MODELS:
            mdir = out / tag(model_name)
            mdir.mkdir()
            for index, (repeat, task) in enumerate(schedule):
                if time.monotonic() - started > CAP_SECONDS:
                    recorder.add("time_cap_reached", model=model_name, next_index=index)
                    print(f"TIME CAP reached before {model_name} episode {index}", flush=True)
                    break
                if any(p.poll() is not None for p in processes):
                    raise RuntimeError("Fixture process exited during study")
                destination = mdir / f"{index:02d}-{task}-ollama-r{repeat}"
                run_worker(mdir, destination, ["--model", model_name, "--task", task, "--repeat", str(repeat)], 900, recorder, mdir / "attempts.jsonl")
                if index == 0:
                    save(mdir / "ollama-ps.json", active_models())
            check(f"after-{tag(model_name)}")
    except Exception as failure:
        recorder.add("study_error", error=repr(failure))
        raise
    finally:
        if processes is not None:
            S1.stop_processes(processes, handles, recorder)
            recorder.add("cleanup_ok", ok=S1.verify_empty((FX.NS,), recorder))
        S1.stop_daemon(recorder)


def offline_check():
    assert S3B.prompt_hash_a1() == STAGE3B_A1_SHA, "A1 prompt hash differs from Stage 3b"
    print("A1 hash equals Stage 3b:", STAGE3B_A1_SHA)

    class Dummy(S1.BaseChatModel):
        @property
        def _llm_type(self):
            return "dummy"
        def bind_tools(self, tools, **kwargs):
            return self
        def _generate(self, *args, **kwargs):
            raise RuntimeError("no inference in offline check")
    S3B.A1ROSA(Dummy(), 3)
    for name in MODELS:
        m = build_model(name)  # constructing the client does not call the server
        print(name, "client settings:", dict(model=m.model, temperature=m.temperature, seed=m.seed, num_ctx=m.num_ctx, num_predict=m.num_predict, reasoning=m.reasoning))
    print("OFFLINE CHECK OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    r = sub.add_parser("run"); r.add_argument("output")
    e = sub.add_parser("episode"); e.add_argument("--output", required=True); e.add_argument("--model", required=True, choices=MODELS); e.add_argument("--task", required=True); e.add_argument("--repeat", default="0")
    a = parser.parse_args()
    {"check": lambda: offline_check(), "run": lambda: study(a.output), "episode": lambda: episode(a)}[a.command]()
