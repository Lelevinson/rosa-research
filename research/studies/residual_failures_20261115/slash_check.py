"""Scorer decision input: how does ROS 2 treat a node name without the leading slash? Starts the Stage 3 fixture (domain 220), no model."""
import json, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "headroom_diagnostic_20261112")); sys.path.insert(0, str(HERE.parent / "headroom_diagnostic_20261112/vendor"))
import run_stage1 as common
import stage3_fixture as fx
from menu_run_study import Recorder
from rosa.tools import ros2

def run(*argv):
    p = subprocess.run(["ros2", *argv], capture_output=True, text=True, timeout=40)
    return dict(cmd="ros2 " + " ".join(argv), returncode=p.returncode, stdout=p.stdout[:160].replace("\n", " | "), stderr=p.stderr.replace("\n", " | ")[:160])

out = HERE / "slash_work"; out.mkdir(exist_ok=True)
rec = Recorder(out / "setup.jsonl")
common.assert_domain_empty((fx.NS,), rec)
procs, handles = common.start_processes(fx.commands(), out, "fx", rec)
rows = []
try:
    time.sleep(6); assert common.wait_for([n["fqn"] for n in fx.GRAPH["nodes"]], rec, attempts=10)
    for _ in range(10):  # daemon lag
        if len([n for n in ros2.ros2_node_list.invoke({})["nodes"] if n.startswith(fx.NS)]) == len(fx.GRAPH["nodes"]): break
        time.sleep(3)
    for argv in [("node", "info", "/plant32/anvil"), ("node", "info", "plant32/anvil"), ("node", "info", "/plant32/nonexistent"), ("node", "info", "plant32/nonexistent"),
                 ("param", "get", "/plant32/anvil", "gain"), ("param", "get", "plant32/anvil", "gain"), ("param", "list", "plant32/anvil"), ("param", "get", "plant32/nonexistent", "gain")]:
        rows.append(run(*argv))
    for tool, args in [("ros2_node_info", {"nodes": ["plant32/anvil"]}), ("ros2_node_info", {"nodes": ["/plant32/anvil"]}), ("ros2_param_get", {"node_name": "plant32/anvil", "param_name": "gain"})]:
        r = getattr(ros2, tool).invoke(args); rows.append(dict(cmd=f"ROSA {tool} {json.dumps(args)}", result=str(r)[:200].replace("\n", " | ")))
finally:
    common.stop_processes(procs, handles, rec); rec.add("cleanup_ok", ok=common.verify_empty((fx.NS,), rec)); common.stop_daemon(rec)
(HERE / "slash_check.json").write_text(json.dumps(rows, indent=1))
for r in rows: print(json.dumps(r)[:330])
