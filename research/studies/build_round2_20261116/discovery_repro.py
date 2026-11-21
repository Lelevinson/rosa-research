"""Reproduction of the node-discovery flakes (no model episodes; CPU/ROS only). Used by DISCOVERY_FLAKES.md.

  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python discovery_repro.py run OUTDIR [SECONDS_PER_CONDITION]

Starts the stage 3 fixture (19 nodes, the same commands as run_pilot.session) once, then polls the node list in 8 conditions of SECONDS_PER_CONDITION (default 600):
  mode oracle        `ros2 node list --no-daemon --spin-time 4`     (what the oracle does today)
  mode nodaemon10    `ros2 node list --no-daemon --spin-time 10`    (longer spin)
  mode daemon_fresh  `ros2 daemon stop; ros2 daemon start; ros2 node list`   (what the agent's tool does, on a freshly restarted daemon)
  mode daemon_aged   `ros2 node list` (daemon left running from the previous condition)
  x background load  off | on (an Ollama model generating continuously on the Windows host; the load only simulates the real runs)
Each poll starts one second after the previous one ended. A poll records: duration, return code, nodes missing from the 19 declared fixture nodes, whether every fixture
process was alive (to tell a dead node from a missed discovery), the WSL load average. A separate PowerShell sampler writes the Windows power state every 60 s.
Output: OUTDIR/polls.jsonl, OUTDIR/windows_power.jsonl, OUTDIR/conditions.jsonl.
"""
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import threading
import time
import urllib.request

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(STUDIES / "headroom_diagnostic_20261112"))
import stage3_fixture as F  # noqa: E402

OLLAMA = os.environ.get("ROSA_OLLAMA_URL", "http://172.30.80.1:11434")  # lab container sets ROSA_OLLAMA_URL
LOAD_MODEL = "gpt-oss:20b"  # the heaviest of the four study models (partly on CPU); it only simulates load
POWERSHELL = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
SAMPLER = r'''
Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public static class Idle{[StructLayout(LayoutKind.Sequential)]struct LII{public uint cbSize;public uint dwTime;}[DllImport("user32.dll")]static extern bool GetLastInputInfo(ref LII p);public static double Seconds(){LII l=new LII();l.cbSize=(uint)Marshal.SizeOf(l);GetLastInputInfo(ref l);return ((uint)Environment.TickCount-l.dwTime)/1000.0;}}'
$plan=(powercfg /getactivescheme) -replace '.*\((.*)\).*','$1'
while($true){
 $b=Get-CimInstance Win32_Battery; $p=Get-CimInstance Win32_Processor
 $c=(Get-Counter '\Processor Information(_Total)\% Processor Performance','\Processor Information(_Total)\% Processor Utility').CounterSamples
 [pscustomobject]@{time=(Get-Date -Format o);plan=$plan;battery_status=$b.BatteryStatus;charge=$b.EstimatedChargeRemaining;clock_mhz=$p.CurrentClockSpeed;max_mhz=$p.MaxClockSpeed;perf_pct=$c[0].CookedValue;utility_pct=$c[1].CookedValue;idle_seconds=[Idle]::Seconds()} | ConvertTo-Json -Compress
 [Console]::Out.Flush(); Start-Sleep -Seconds 60 }
'''


class Recorder:
    def __init__(self, path):
        self.path = path

    def add(self, kind, **values):
        with open(self.path, "a") as handle:
            handle.write(json.dumps(dict(kind=kind, time=time.time(), **values), default=str) + "\n")


def start_windows_sampler(path):
    process = subprocess.Popen([POWERSHELL, "-NoProfile", "-Command", SAMPLER], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

    def read():
        for line in process.stdout:
            line = line.strip()
            if line.startswith("{"):
                with open(path, "a") as handle:
                    handle.write(line + "\n")
    threading.Thread(target=read, daemon=True).start()
    return process


class OllamaLoad:
    """Keeps one model generating on the Windows host until stopped (simulates the real runs' CPU/GPU/memory load; its output is discarded)."""
    def __init__(self):
        self.stop = threading.Event()
        self.thread = None
        self.requests = 0

    def start(self):
        self.stop.clear()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def loop(self):
        while not self.stop.is_set():
            body = json.dumps(dict(model=LOAD_MODEL, prompt="Write a long, detailed essay about the history of robotics.", stream=True,
                                   options=dict(num_predict=600, num_ctx=65536, temperature=0.7))).encode()
            try:
                request = urllib.request.Request(OLLAMA + "/api/generate", data=body, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(request, timeout=120) as response:
                    for _ in response:
                        if self.stop.is_set():
                            break
                self.requests += 1
            except Exception:
                time.sleep(2)

    def end(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=30)
        body = json.dumps(dict(model=LOAD_MODEL, keep_alive=0)).encode()  # unload the model again
        try:
            urllib.request.urlopen(urllib.request.Request(OLLAMA + "/api/generate", data=body, headers={"Content-Type": "application/json"}), timeout=60).read()
        except Exception:
            pass


COMMANDS = {"oracle": ["ros2", "node", "list", "--no-daemon", "--spin-time", "4"],
            "nodaemon10": ["ros2", "node", "list", "--no-daemon", "--spin-time", "10"],
            "daemon_fresh": ["ros2", "node", "list"],
            "daemon_aged": ["ros2", "node", "list"]}


def run_condition(mode, load, seconds, processes, expected, out, loader):
    if mode == "daemon_fresh":
        subprocess.run(["ros2", "daemon", "stop"], capture_output=True, text=True, timeout=60)
        subprocess.run(["ros2", "daemon", "start"], capture_output=True, text=True, timeout=60)
        time.sleep(5)
    if load == "on":
        loader.start()
        time.sleep(20)  # model load time
    rec = Recorder(out / "polls.jsonl")
    started = time.time()
    count = 0
    while time.time() - started < seconds:
        began = time.time()
        try:
            result = subprocess.run(COMMANDS[mode], capture_output=True, text=True, timeout=60)
            code, listed, error = result.returncode, set(result.stdout.split()), result.stderr[-200:]
        except subprocess.TimeoutExpired:
            code, listed, error = "timeout", set(), "60 s timeout"
        alive = all(p.poll() is None for p in processes)
        missing = sorted(expected - listed)
        rec.add("poll", mode=mode, load=load, index=count, seconds=round(time.time() - began, 2), returncode=code, missing=missing, n_listed=len(listed & expected),
                fixture_alive=alive, loadavg=open("/proc/loadavg").read().split()[:3], error=error if code != 0 else "")
        count += 1
        time.sleep(1)
    if load == "on":
        loader.end()
        time.sleep(15)  # let the machine settle before the next condition


def main(out, seconds):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    for key, value in {"ROS_DOMAIN_ID": "220", "ROS_LOCALHOST_ONLY": "1"}.items():
        assert os.environ.get(key) == value, f"set {key}={value}"
    recorder = Recorder(out / "setup.jsonl")
    expected = {n["fqn"] for n in F.GRAPH["nodes"]}
    sampler = start_windows_sampler(out / "windows_power.jsonl")
    F.common.assert_domain_empty((F.NS,), recorder)
    processes, handles = F.common.start_processes(F.commands(), out, "fx", recorder)
    loader = OllamaLoad()
    try:
        time.sleep(6)
        recorder.add("ready", ok=F.common.wait_for(sorted(expected), recorder, attempts=10))
        seed = random.Random("20261116-discovery")
        plan = []
        for mode in COMMANDS:
            loads = ["off", "on"]
            seed.shuffle(loads)  # order of the load levels inside each pair is random
            plan += [(mode, load) for load in loads]
        for mode, load in plan:
            Recorder(out / "conditions.jsonl").add("condition_start", mode=mode, load=load, seconds=seconds)
            run_condition(mode, load, seconds, processes, expected, out, loader)
    finally:
        loader.end()
        F.common.stop_processes(processes, handles, recorder)
        recorder.add("cleanup_ok", ok=F.common.verify_empty((F.NS,), recorder))
        F.common.stop_daemon(recorder)
        sampler.terminate()


if __name__ == "__main__":
    if sys.argv[1] == "run":
        main(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 600)
