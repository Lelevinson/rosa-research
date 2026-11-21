"""Verification of the proposed fix (not applied to round 2): run the REAL stage 3 oracle repeatedly against one live fixture, interleaving
  A = oracle as it is today (node list: `ros2 node list --no-daemon --spin-time 4`)
  B = the same oracle with ONE change: that node-list read goes through a freshly restarted daemon (`ros2 node list`), nothing else changed
with an Ollama model generating the whole time (worst case seen in discovery_repro). Output: OUTDIR/verify.jsonl.
  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python discovery_verify.py OUTDIR PAIRS"""
import json, os, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import discovery_repro as R  # noqa: E402
F = R.F
original_cli = F.cli


def daemon_cli(*argv, retries=3):
    if tuple(argv[:3]) == ("node", "list", "--no-daemon"):
        argv = ("node", "list")  # the one change
    return original_cli(*argv, retries=retries)


def main(out, pairs):
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    assert os.environ.get("ROS_DOMAIN_ID") == "220" and os.environ.get("ROS_LOCALHOST_ONLY") == "1"
    rec = R.Recorder(out / "setup.jsonl")
    F.common.assert_domain_empty((F.NS,), rec)
    processes, handles = F.common.start_processes(F.commands(), out, "fx", rec)
    loader = R.OllamaLoad()
    try:
        time.sleep(6)
        rec.add("ready", ok=F.common.wait_for(sorted(n["fqn"] for n in F.GRAPH["nodes"]), rec, attempts=10))
        subprocess.run(["ros2", "daemon", "stop"], capture_output=True, timeout=60); subprocess.run(["ros2", "daemon", "start"], capture_output=True, timeout=60)
        loader.start(); time.sleep(20)
        log = R.Recorder(out / "verify.jsonl")
        for i in range(pairs):
            for variant in (("A", original_cli), ("B", daemon_cli)) if i % 2 == 0 else (("B", daemon_cli), ("A", original_cli)):
                F.cli = variant[1]
                (out / f"o-{i}-{variant[0]}").mkdir()
                began = time.time()
                try:
                    bad = F.oracle(out / f"o-{i}-{variant[0]}", rec)
                except Exception as error:
                    bad = [f"exception {error!r}"]
                log.add("oracle", pair=i, variant=variant[0], seconds=round(time.time() - began, 1), mismatches=bad, fixture_alive=all(p.poll() is None for p in processes))
    finally:
        F.cli = original_cli
        loader.end()
        F.common.stop_processes(processes, handles, rec)
        rec.add("cleanup_ok", ok=F.common.verify_empty((F.NS,), rec))
        F.common.stop_daemon(rec)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
