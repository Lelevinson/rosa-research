"""Real-fixture check of amendment 4 (no model): the actual run_round2.OracleWithRetry around the actual stage 3 fixture module, three oracle reads.
  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python discovery_amendment4_check.py OUTDIR [READS]"""
import json, os, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import discovery_repro as R  # noqa: E402
import run_round2  # noqa: E402
F = R.F
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=False)
reads = int(sys.argv[2]) if len(sys.argv) > 2 else 3
assert os.environ.get("ROS_DOMAIN_ID") == "220" and os.environ.get("ROS_LOCALHOST_ONLY") == "1"
rec = R.Recorder(out / "setup.jsonl")
F.common.assert_domain_empty((F.NS,), rec)
processes, handles = F.common.start_processes(F.commands(), out, "fx", rec)
try:
    time.sleep(6)
    rec.add("ready", ok=F.common.wait_for(sorted(n["fqn"] for n in F.GRAPH["nodes"]), rec, attempts=10))
    wrapper = run_round2.OracleWithRetry(F)
    for i in range(reads):
        d = out / "session" / f"oracle-{'before' if i == 0 else f'after-{i:03d}'}"; d.mkdir(parents=True)
        began = time.time(); bad = wrapper.oracle(d, rec)
        print(json.dumps(dict(read=i, seconds=round(time.time() - began, 1), mismatches=bad)), flush=True)
finally:
    F.cli = F._round2_original_cli
    F.common.stop_processes(processes, handles, rec)
    rec.add("cleanup_ok", ok=F.common.verify_empty((F.NS,), rec)); F.common.stop_daemon(rec)
