"""Memory and failure check: headless Gazebo TurtleBot3 + Nav2 together with each of the 4 Ollama models loaded (owner's request of 2026-11-19, task 2).
DIAGNOSTIC, no bars, no model quality is measured, one stack at a time, GPU used by nothing else. Plan, frozen in this docstring before the first run:
  For each model in the order lfm3:1.7b, bonsai-2:4b, qwen3.5:9b, gpt-oss:20b:
   A. (no stack) load the model at num_ctx 65536 (the dev setting), record /api/ps size and size_vram and nvidia-smi used MiB; run one fixed ~4k-token prompt, 200 new tokens, temperature 0,
      seed 1; record tokens/s and the peak GPU memory (1 Hz polling).
   B. start the owned Gazebo + Nav2 stack (turtlebot3_nav2_smoke_20261116/stack.py start, domain 219), wait until the navigation script can run; record GPU memory with stack + model.
   C. run the same prompt again while navigate_once.py sends one bounded goal at the same time; record tokens/s, peak GPU memory, whether the goal succeeded and how long it took.
   D. stop the stack (stack.py stop) and check that no owned process remains; unload the model; record GPU memory after.
  Also: RAM (free -m) and load average at each step. Any exception, non-zero exit, timeout, goal failure or cleanup failure is recorded as a failure with its text; nothing is retried.
Run:  uv run --no-project --python /usr/bin/python3 python research/studies/gazebo_nav2_model_memory_20261119/check.py   (ROS Jazzy installed; no Python packages needed)"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
OLLAMA = os.environ.get("ROSA_OLLAMA_URL", "http://172.30.80.1:11434")  # lab container sets ROSA_OLLAMA_URL
STACK = STUDIES / "turtlebot3_nav2_smoke_20261116/stack.py"
NAV = STUDIES / "turtlebot3_nav2_smoke_20261116/navigate_once.py"
MODELS = ["lfm3:1.7b", "bonsai-2:4b", "qwen3.5:9b", "gpt-oss:20b"]
PROMPT = ("List the ROS 2 nodes, topics and services in this graph and say which node provides the service. " + "The node anvil publishes the topic harbor_t and subscribes to quarry_t. " * 330 + "Answer in two sentences.")


def api(path, body=None, timeout=300):
    request = urllib.request.Request(OLLAMA + path, json.dumps(body).encode() if body is not None else None, {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(request, timeout=timeout))


OUT = Path(os.environ.get("ROSA_CHECK_OUT", HERE))  # where results.json goes (the lab run writes outside the checked-in repo files, 2026-11-20)


def gpu():
    """(used, total) MiB. The lab container has no nvidia-smi: then the newest sample of the HOST sampler is used (start it with `gpu_state.py sample --seconds 1 --log $ROSA_GPU_STATE_LOG`;
    added 2026-11-20 after the lab run showed the container cannot call nvidia-smi). Fails loudly if there is no sample from the last 15 s."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.strip().split(",")
        return int(out[0]), int(out[1])
    except FileNotFoundError:
        sys.path.insert(0, str(STUDIES / "final_exam_draft_20261118/exam_queue"))
        import gpu_state
        samples = [s for s in gpu_state.read_window(time.time() - 15, time.time()) if s.get("used_mib") is not None]
        if not samples:
            raise RuntimeError("nvidia-smi is not available here and the host GPU sampler wrote no sample in the last 15 s")
        return samples[-1]["used_mib"], samples[-1]["total_mib"]


def ram():
    mem = {line.split(":")[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines()[:3]}
    return dict(ram_used_mib=(mem["MemTotal"] - mem["MemAvailable"]) // 1024, ram_total_mib=mem["MemTotal"] // 1024, load1=os.getloadavg()[0])


class Peak:
    def __enter__(self):
        self.peak, self.stop = 0, False
        def loop():
            while not self.stop:
                self.peak = max(self.peak, gpu()[0]); time.sleep(1)
        self.thread = threading.Thread(target=loop, daemon=True); self.thread.start()
        return self

    def __exit__(self, *a):
        self.stop = True; self.thread.join()


def infer(model):
    body = dict(model=model, stream=False, messages=[{"role": "user", "content": PROMPT}], think=False, options=dict(num_ctx=65536, num_predict=200, temperature=0, seed=1), keep_alive="10m")
    started = time.time()
    try:
        r = api("/api/chat", body)
    except Exception as error:  # noqa: BLE001
        return dict(error=f"{type(error).__name__}: {error}"[:200], seconds=round(time.time() - started, 1))
    return dict(prompt_tokens=r.get("prompt_eval_count"), new_tokens=r.get("eval_count"), tokens_per_second=round(r["eval_count"] / (r["eval_duration"] / 1e9), 1) if r.get("eval_duration") else None,
                prompt_tokens_per_second=round(r["prompt_eval_count"] / (r["prompt_eval_duration"] / 1e9), 1) if r.get("prompt_eval_duration") else None, seconds=round(time.time() - started, 1))


def loaded(model):
    for m in api("/api/ps", timeout=15).get("models", []):
        if m["name"] == model:
            return dict(size_mib=m["size"] // 2**20, size_vram_mib=m["size_vram"] // 2**20, context_length=m.get("context_length"))
    return None


def run(command, timeout):
    started = time.time()
    p = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    return dict(returncode=p.returncode, seconds=round(time.time() - started, 1), tail=(p.stdout + p.stderr).strip().splitlines()[-4:])


def ros_command(script, *args):
    return ["/bin/bash", "-c", f"source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=219 ROS_LOCALHOST_ONLY=1 && exec {sys.executable} {script} {' '.join(args)}"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert not api("/api/ps", timeout=15).get("models"), "a model is loaded: the GPU must be idle"
    results = dict(started=time.strftime("%FT%T%z"), gpu_total_mib=gpu()[1], nproc=os.cpu_count(), baseline=dict(gpu_used_mib=gpu()[0], **ram()), models={})
    for model in MODELS:
        entry, failures = {}, []
        results["models"][model] = entry
        try:
            # A. model alone
            infer_a_warm = infer(model)  # first call loads the model (load time is part of `seconds`)
            entry["A_loaded"] = dict(loaded(model) or {}, gpu_used_mib=gpu()[0], **ram())
            with Peak() as peak:
                entry["A_inference_no_stack"] = infer(model)
            entry["A_inference_no_stack"]["peak_gpu_used_mib"] = peak.peak
            entry["A_first_call_including_load"] = infer_a_warm
            # B. stack up
            entry["B_stack_start"] = run([sys.executable, str(STACK), "start"], 120)
            time.sleep(float(os.environ.get("ROSA_STACK_WAIT", 60)))  # the supervisor returns before Nav2 is ready; navigate_once waits for readiness itself. Lab: 35 (the Nav2 lifecycle manager there gave up after about 60 s without the initial pose; lab log step 9)
            entry["B_with_stack"] = dict(gpu_used_mib=gpu()[0], **ram())
            # C. inference with stack, navigation at the same time
            nav_result = {}
            def navigate():
                nav_result.update(run(ros_command(NAV), 240))
            thread = threading.Thread(target=navigate); thread.start()
            with Peak() as peak:
                entry["C_inference_with_stack"] = infer(model)
                thread.join(timeout=300)
            entry["C_inference_with_stack"]["peak_gpu_used_mib"] = peak.peak
            entry["C_navigation"] = nav_result
            entry["C_navigation_passed"] = "NAVIGATION PASS" in " ".join(nav_result.get("tail", []))
            if not entry["C_navigation_passed"]:
                failures.append("navigation goal did not pass: " + " | ".join(nav_result.get("tail", []))[:300])
            if "error" in entry["C_inference_with_stack"]:
                failures.append("inference with stack failed: " + entry["C_inference_with_stack"]["error"])
        except Exception as error:  # noqa: BLE001
            failures.append(f"{type(error).__name__}: {error}"[:300])
        finally:
            stop = run([sys.executable, str(STACK), "stop"], 120)
            entry["D_stack_stop"] = stop
            if stop["returncode"] != 0 or "PASS" not in " ".join(stop["tail"]):
                failures.append("stack stop did not report PASS: " + " | ".join(stop["tail"])[:300])
            try:
                api("/api/generate", dict(model=model, keep_alive=0), timeout=60)
            except Exception as error:  # noqa: BLE001
                failures.append(f"unload failed: {error}"[:200])
            time.sleep(5)
            entry["D_after"] = dict(gpu_used_mib=gpu()[0], **ram(), still_loaded=[m["name"] for m in api("/api/ps", timeout=15).get("models", [])])
            entry["failures"] = failures
        (OUT / "results.json").write_text(json.dumps(results, indent=1))
        print(model, "failures:", failures, flush=True)
    results["finished"] = time.strftime("%FT%T%z")
    (OUT / "results.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
