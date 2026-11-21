"""Capture the structure snapshot (variants A and B) with the real ROSA read tools on each pilot fixture. No model. Usage: capture_snapshot.py (ROS_DOMAIN_ID=220)."""
import json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "small_model_harness_20261115"
sys.path.insert(0, str(PILOT)); sys.path.insert(0, str(HERE.parent / "headroom_diagnostic_20261112")); sys.path.insert(0, str(HERE.parent / "headroom_diagnostic_20261112/vendor"))
import run_stage1 as common
from menu_run_study import Recorder
from rosa.tools import ros2

def capture(env_name, module):
    out = HERE / "capture_work" / env_name
    out.mkdir(parents=True, exist_ok=True)
    rec = Recorder(out / "setup.jsonl")
    common.assert_domain_empty((module.NS,), rec)
    procs, handles = common.start_processes(module.commands(), out, "fx", rec)
    try:
        time.sleep(6)
        assert common.wait_for([n["fqn"] for n in module.GRAPH["nodes"]], rec, attempts=10)
        want = {n["fqn"] for n in module.GRAPH["nodes"]}
        for attempt in range(20):  # the ros2 daemon cache can lag behind discovery
            nodes = [n for n in ros2.ros2_node_list.invoke({})["nodes"] if n.startswith(module.NS)]
            if want <= set(nodes):
                break
            time.sleep(3)
        assert want <= set(nodes), f"only {len(nodes)} of {len(want)} nodes listed"
        snap = dict(node_list=ros2.ros2_node_list.invoke({}), topic_list=ros2.ros2_topic_list.invoke({}), service_list=ros2.ros2_service_list.invoke({}),
                    node_info=ros2.ros2_node_info.invoke({"nodes": nodes}))
        bad = [k for k, v in snap["node_info"].items() if isinstance(v, dict)]
        assert not bad, f"node_info errors: {bad}"
        param = {}
        for n in nodes:  # names only, one call per node
            result = ros2.ros2_param_list.invoke({"node_name": n})
            assert "error" not in result, (n, result)
            param.update(result)
        return dict(A=snap, B=dict(snap, param_list=param), nodes_in_fixture=len(module.GRAPH["nodes"]), nodes_captured=len(nodes))
    finally:
        common.stop_processes(procs, handles, rec)
        rec.add("cleanup_ok", ok=common.verify_empty((module.NS,), rec)); common.stop_daemon(rec)

if __name__ == "__main__":
    import stage3_fixture, e1h_fixture
    result = {name: capture(name, mod) for name, mod in (("stage3", stage3_fixture), ("e1h", e1h_fixture))}
    (HERE / "snapshots.json").write_text(json.dumps(result, indent=1))
    for k, v in result.items():
        print(k, "nodes", v["nodes_captured"], "/", v["nodes_in_fixture"], "chars A", len(json.dumps(v["A"])), "chars B", len(json.dumps(v["B"])))
