"""History scan for DISCOVERY_FLAKES.md (read-only): (1) did the AGENT's `ros2 node list` calls ever return an incomplete fixture node list; (2) which sessions ever had an oracle
mismatch or a retried oracle, with file times.   uv run python discovery_history.py > discovery_history.json"""
import datetime
import glob
import json
import os
from pathlib import Path
import re
import sys
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "research/_artifacts/runs"
stage3 = {n["fqn"] for n in json.loads((ROOT / "research/studies/headroom_diagnostic_20261112/stage3_graph.json").read_text())["nodes"]}
e1h = {n["fqn"] for n in json.loads((ROOT / "research/studies/small_model_harness_20261115/e1h_graph.json").read_text())["nodes"]}
stamp = lambda p: datetime.datetime.fromtimestamp(os.path.getmtime(p)).astimezone().isoformat(timespec="minutes")

node_lists = defaultdict(lambda: dict(calls=0, incomplete=0, examples=[]))
for trace in glob.glob(str(RUNS / "**/trace.jsonl"), recursive=True):
    text = Path(trace).read_text(errors="replace")
    if '"ros_end"' not in text:
        continue
    session = str(Path(trace).relative_to(RUNS).parent.parent)
    for line in text.splitlines():
        if '"ros_end"' not in line or '"node"' not in line:
            continue
        e = json.loads(line)
        cmd = e.get("command") or []
        if len(cmd) < 3 or cmd[1:3] != ["node", "list"] or e.get("returncode") != 0:
            continue
        listed = set(e["stdout"].split())
        expected = stage3 if listed & stage3 or "stage3" in session or "plant32" in e["stdout"] else (e1h if listed & e1h else None)
        if expected is None:
            expected = stage3 if "e1h" not in session else e1h
        d = node_lists[session]
        d["calls"] += 1
        miss = sorted(expected - listed)
        if miss and len(listed & expected) > 0:  # some but not all fixture nodes listed
            d["incomplete"] += 1
            if len(d["examples"]) < 3:
                d["examples"].append(dict(trace=str(Path(trace).relative_to(ROOT)), missing=miss, listed=len(listed & expected), when=stamp(trace)))

oracle = []
for f in glob.glob(str(RUNS / "**/oracle*/oracle.json"), recursive=True):
    d = json.loads(Path(f).read_text())
    if d.get("mismatches"):
        oracle.append(dict(file=str(Path(f).relative_to(ROOT)), mismatches=d["mismatches"][:5], when=stamp(f)))
events = []
for f in glob.glob(str(RUNS / "**/setup.jsonl"), recursive=True):
    for line in Path(f).read_text(errors="replace").splitlines():
        if '"session_error"' in line or '"oracle_cli_timeout"' in line or "oracle_failure_logged" in line:
            e = json.loads(line)
            events.append(dict(file=str(Path(f).relative_to(ROOT)), kind=e["kind"], text=str(e.get("error") or e.get("mismatches") or e.get("command"))[:200], file_mtime=stamp(f)))
failures = []
for f in glob.glob(str(RUNS / "**/oracle_failures.jsonl"), recursive=True):
    failures += [dict(json.loads(l), file=str(Path(f).relative_to(ROOT)), file_mtime=stamp(f)) for l in Path(f).read_text().splitlines()]
print(json.dumps(dict(node_list_by_session={k: v for k, v in sorted(node_lists.items())}, oracle_files_with_mismatch=oracle, setup_events=events, round2_oracle_failures=failures), indent=1))
