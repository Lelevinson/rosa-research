"""Health checks and cleanup used by the queue runner and the monitor: Ollama, GPU memory, disk, leftover ROS / Gazebo processes."""
import json
import os
import shutil
import signal
import subprocess
import time
import urllib.request
from pathlib import Path

OLLAMA_DEFAULT = os.environ.get("ROSA_OLLAMA_URL", "http://172.30.80.1:11434")  # the monitor on the lab host needs the variable too
# Command-line fragments of processes a study fixture or the Nav2 stack leaves behind if a runner dies.
LEFTOVER_PATTERNS = ("stage3_node.py", "e1h_node.py", "namefix_node.py", "turtlesim_node", "gz sim", "gzserver", "component_container", "nav2_", "ros2 launch")


def ollama_ok(url=OLLAMA_DEFAULT, timeout=8):
    try:
        urllib.request.urlopen(url + "/api/tags", timeout=timeout).read()
        return True
    except Exception:
        return False


def ollama_loaded(url=OLLAMA_DEFAULT, timeout=8):
    """Names of the models currently loaded (empty list if none or unreachable)."""
    try:
        return [m["name"] for m in json.load(urllib.request.urlopen(url + "/api/ps", timeout=timeout)).get("models", [])]
    except Exception:
        return []


def unload_all(url=OLLAMA_DEFAULT, keep=None):
    """Unload every loaded model except `keep` (keep_alive 0). Two models on the 8 GB GPU would slow or break an episode."""
    for name in ollama_loaded(url):
        if name == keep:
            continue
        request = urllib.request.Request(url + "/api/generate", json.dumps({"model": name, "keep_alive": 0}).encode(), {"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(request, timeout=30).read()
        except Exception:
            pass


def gpu_memory_mib():
    """(used, total) in MiB from nvidia-smi, or None."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout.strip().split("\n")[0]
        used, total = (int(x) for x in out.split(","))
        return used, total
    except Exception:
        return None


def disk_free_gb(path):
    return round(shutil.disk_usage(path).free / 1e9, 1)


def ros_leftovers(domain="220", patterns=LEFTOVER_PATTERNS, exclude_pids=()):
    """PIDs of processes of this user whose command line matches a leftover pattern AND whose environment has ROS_DOMAIN_ID=domain (our fixtures only)."""
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) in exclude_pids or int(entry.name) == os.getpid():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            environ = (entry / "environ").read_bytes().split(b"\0")
        except (OSError, PermissionError):
            continue
        if f"ROS_DOMAIN_ID={domain}".encode() in environ and any(p in cmdline for p in patterns):
            found.append(int(entry.name))
    return sorted(found)


def kill_leftovers(domain="220", patterns=LEFTOVER_PATTERNS, exclude_pids=(), grace=4.0):
    """TERM, wait, then KILL the processes found by ros_leftovers. Returns (killed_pids, still_alive_pids)."""
    pids = ros_leftovers(domain, patterns, exclude_pids)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.time() + grace
    while time.time() < deadline and ros_leftovers(domain, patterns, exclude_pids):
        time.sleep(0.2)
    for pid in ros_leftovers(domain, patterns, exclude_pids):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    time.sleep(0.3)
    return pids, ros_leftovers(domain, patterns, exclude_pids)
