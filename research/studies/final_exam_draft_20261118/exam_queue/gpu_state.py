"""GPU state on a shared machine: snapshots, a sampler, the per-episode summary and the contention rule.
Design and reasons: LAB_SETUP_CHECKLIST.md, section "GPU sharing and per-episode GPU-state logging". Standard library only.

  python gpu_state.py sample [--seconds 5] [--log PATH]     run on the HOST (the lab container has no nvidia-smi), e.g. in tmux session `gpusample`
  python gpu_state.py once                                   print one snapshot (a quick manual check)

What one snapshot holds: GPU memory used / total / utilisation, every compute process (pid, name, MiB) from `nvidia-smi --query-compute-apps`, our own Ollama's process ids (server plus its
runner children, so our processes can be told apart from other users' processes), Ollama's /api/ps (model, size, size_vram) and the load average.

The CONTENTION RULE (frozen design, applied to the window of one episode, never looking at the answer). An episode is `contended` if
  (a) a process that is not ours held >= OTHER_PROCESS_MIB (1024 MiB; the desktop daemon holds about 249 MiB) at any sample in the window, or
  (b) the episode's model was fully resident (size_vram == size) when first seen in the window and at the last sample is loaded only partly or not at all, or
  (c) the VRAM available to us at the first sample (total minus what others hold) was below the model's size.
A rule whose inputs are not available is simply not applied (it does not fire): on the laptop (WSL) nvidia-smi lists no processes, so (a) and (c) cannot be evaluated there; the summary then says
`process_info: false`. No samples at all = `state: "unknown"`, which is NOT contention."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import health  # noqa: E402

OTHER_PROCESS_MIB = 1024   # design choice (above the 249 MiB desktop baseline), not a measured optimum
SAMPLE_SECONDS = 5
DEFAULT_LOG = HERE.parents[2] / "_artifacts/exam/gpu_state.jsonl"  # the repo is shared between the host and the lab container, so both see this file


def log_path():
    return Path(os.environ.get("ROSA_GPU_STATE_LOG", DEFAULT_LOG))


# ------------------------------------------------------------------ one snapshot
def _run(command, timeout=10):
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return done.stdout if done.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def our_ollama_pids(url):
    """Pids of the Ollama server listening on url's port plus all its descendants (the model runner children hold the VRAM). None if it cannot be determined
    (a server on another machine, no `ss`, or no permission to see the pid)."""
    match = re.search(r":(\d+)$", url.rstrip("/"))
    if not match:
        return None
    out = _run(["ss", "-ltnpH", f"sport = :{match.group(1)}"])
    server = re.search(r"pid=(\d+)", out or "")
    if not server:
        return None
    children = {}
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                parent = int((entry / "stat").read_text().rsplit(")", 1)[1].split()[1])
            except (OSError, ValueError, IndexError):
                continue
            children.setdefault(parent, []).append(int(entry.name))
    found, queue = {int(server.group(1))}, [int(server.group(1))]
    while queue:
        for child in children.get(queue.pop(), []):
            if child not in found:
                found.add(child)
                queue.append(child)
    return sorted(found)


def ollama_ps(url, timeout=8):
    """[{name, size_mib, size_vram_mib}] of the loaded models, or None if Ollama cannot be reached."""
    try:
        models = json.load(urllib.request.urlopen(url + "/api/ps", timeout=timeout)).get("models", [])
    except Exception:  # noqa: BLE001
        return None
    return [dict(name=m["name"], size_mib=round(m.get("size", 0) / 2 ** 20), size_vram_mib=round(m.get("size_vram", 0) / 2 ** 20)) for m in models]


def snapshot(url=None, our_pids="detect"):
    """One reading of the GPU and of our Ollama. Test hook: ROSA_GPU_FAKE_SNAPSHOT=path of a JSON snapshot returned as it is (with a fresh time stamp)."""
    fake = os.environ.get("ROSA_GPU_FAKE_SNAPSHOT")
    if fake:
        return dict(json.loads(Path(fake).read_text()), t=time.time())
    url = url or health.OLLAMA_DEFAULT
    now = dict(t=time.time(), used_mib=None, total_mib=None, util_pct=None, apps=[], our_pids=None, ours_mib=None, others_mib=None, loaded=None, load1=round(os.getloadavg()[0], 2))
    gpu = _run(["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"])
    if gpu:
        try:
            now["used_mib"], now["total_mib"], now["util_pct"] = (int(x) for x in gpu.strip().split("\n")[0].split(","))
        except ValueError:
            pass
    apps = _run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader,nounits"])
    for line in (apps or "").strip().split("\n"):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 3 and parts[0].isdigit():
            now["apps"].append(dict(pid=int(parts[0]), name=parts[1], mib=int(parts[2]) if parts[2].isdigit() else 0))
    now["loaded"] = ollama_ps(url)
    ours = our_ollama_pids(url) if our_pids == "detect" else our_pids
    now["our_pids"] = ours
    if ours is not None and now["apps"]:  # process information exists only if nvidia-smi listed processes at all (it lists none under WSL)
        now["ours_mib"] = sum(a["mib"] for a in now["apps"] if a["pid"] in ours)
        now["others_mib"] = sum(a["mib"] for a in now["apps"] if a["pid"] not in ours)
    return now


# ------------------------------------------------------------------ sampler (host)
def sample_once(url, path):
    """One sample appended to the log. The pid list of our Ollama is recomputed EVERY time: Ollama starts a new runner process (a new pid) whenever it loads a model, and a cached list made
    that runner look like another user's process (found in the first lab mini exam: 'other processes held 1537 MiB' = our own lfm3 runner, which false-flagged the first episode after each load)."""
    line = json.dumps(snapshot(url))
    with path.open("a") as handle:
        handle.write(line + "\n")


def sample_forever(seconds, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    url = os.environ.get("ROSA_OLLAMA_URL", health.OLLAMA_DEFAULT)
    while True:
        sample_once(url, path)
        time.sleep(seconds)


def read_window(t_start, t_end, path=None):
    """Samples of the sampler log with t_start - 1 s <= t <= t_end + 1 s. Reads only the tail of the file (about 1 MB = 1 h of samples at 5 s)."""
    path = path or log_path()
    if not path.exists():
        return []
    with path.open("rb") as handle:
        handle.seek(0, 2)
        handle.seek(max(0, handle.tell() - 1_500_000))
        text = handle.read().decode(errors="replace")
    samples = []
    for line in text.splitlines():
        try:
            sample = json.loads(line)
        except ValueError:
            continue  # the first line of the tail may be cut
        if t_start - 1 <= sample.get("t", 0) <= t_end + 1:
            samples.append(sample)
    return samples


# ------------------------------------------------------------------ summary and contention rule
def residency(sample, model):
    """size_vram / size of the model in a sample; None if it is not loaded or the sample has no Ollama data. Ollama reports size 0 for some models: then None (not verifiable)."""
    for entry in sample.get("loaded") or []:
        if entry["name"] == model and entry["size_mib"] > 0:
            return entry["size_vram_mib"] / entry["size_mib"]
    return None


def summarize(samples, model):
    """The `gpu_state` block of an episode row and the contention decision, from the samples of the episode window (sorted by time)."""
    samples = sorted(samples, key=lambda s: s["t"])
    if not samples or all(s.get("used_mib") is None and s.get("loaded") is None for s in samples):
        return dict(state="unknown", samples=len(samples), contended=False, reasons=[], process_info=False)
    with_processes = [s for s in samples if s.get("others_mib") is not None]
    reasons = []
    max_others = max((s["others_mib"] for s in with_processes), default=None)
    if max_others is not None and max_others >= OTHER_PROCESS_MIB:
        reasons.append(f"a: other processes held {max_others} MiB")
    present = [s for s in samples if residency(s, model) is not None]
    start_residency = residency(present[0], model) if present else None
    end_residency = residency(samples[-1], model)
    if start_residency is not None and start_residency >= 1.0 and (end_residency is None or end_residency < 1.0):
        reasons.append(f"b: model fully resident at first sight, residency at the end {end_residency}")
    model_size = max((e["size_mib"] for s in samples for e in (s.get("loaded") or []) if e["name"] == model), default=None)
    first = samples[0]
    available = None
    if first.get("total_mib") is not None and first.get("others_mib") is not None:
        available = first["total_mib"] - first["others_mib"]
        if model_size is not None and available < model_size:
            reasons.append(f"c: {available} MiB available to us at the start, model needs {model_size} MiB")
    free = [s["total_mib"] - s["used_mib"] for s in samples if s.get("total_mib") is not None and s.get("used_mib") is not None]
    return dict(state="ok", samples=len(samples), contended=bool(reasons), reasons=reasons, process_info=bool(with_processes), first=first, last=samples[-1], min_free_mib=min(free) if free else None,
                max_others_mib=max_others, residency_start=start_residency, residency_end=end_residency, model_size_mib=model_size, available_to_us_start_mib=available)


def busy_reason(sample):
    """Pre-episode check (operator rule, not an evaluation criterion): why the GPU is not clean right now, or None. Needs process information."""
    others = sample.get("others_mib")
    if others is not None and others >= OTHER_PROCESS_MIB:
        return f"other processes hold {others} MiB of VRAM"
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["sample", "once"])
    parser.add_argument("--seconds", type=float, default=SAMPLE_SECONDS)
    parser.add_argument("--log", default=None)
    args = parser.parse_args()
    if args.command == "once":
        print(json.dumps(snapshot(os.environ.get("ROSA_OLLAMA_URL")), indent=1))
    else:
        sample_forever(args.seconds, Path(args.log) if args.log else log_path())


if __name__ == "__main__":
    main()
