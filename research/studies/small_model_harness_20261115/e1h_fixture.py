"""E1h fixture manager: node commands, oracle, scripted parameter change (EpisodeHook) and the floor check with real ROSA tools.

  uv run python e1h_fixture.py check OUTDIR     start the fixture, oracle, run each task's minimal route with the real tools, stop, verify empty.
No model inference. The ROS domain must be set by the caller (220).
"""
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE3 = HERE.parent / "headroom_diagnostic_20261112"
sys.path.insert(0, str(STAGE3 / "vendor"))
sys.path.insert(0, str(STAGE3))
import run_stage1 as common  # noqa: E402  (fixture helpers: start/stop/wait/cleanup)
from menu_run_study import Recorder, guarded_native  # noqa: E402
from rosa.tools import ros2  # noqa: E402

GRAPH = json.loads((HERE / "e1h_graph.json").read_text())
TASKS = json.loads((HERE / "e1h_tasks.json").read_text())
NS = GRAPH["namespace"]
NODES = {n["fqn"]: n for n in GRAPH["nodes"]}


def commands():
    return [["python3", str(HERE / "e1h_node.py"), str(HERE / "e1h_graph.json"), n["key"]] for n in GRAPH["nodes"]]


def cli(*argv, retries=3):
    for attempt in range(retries):
        p = subprocess.run(["ros2", *argv], capture_output=True, text=True, timeout=40)
        if p.returncode == 0:
            return p.stdout, attempt
        time.sleep(2)
    return None, retries


def parse_value(text):
    m = re.search(r"(Integer|String) value is:\s*(.*)", text or "")
    return (int(m[2]) if m[1] == "Integer" else m[2].strip()) if m else None


def oracle(out, recorder):
    """Direct reads of every declared fact; returns mismatches (empty = the fixture is in its declared initial state)."""
    bad, record = [], {}
    nodes_out, _ = cli("node", "list", "--no-daemon", "--spin-time", "4")
    listed = set((nodes_out or "").splitlines())
    for n in GRAPH["nodes"]:
        if n["fqn"] not in listed:
            bad.append(f"node not listed: {n['fqn']}")
    for n in GRAPH["nodes"]:
        for name, value in n["params"].items():
            text, tries = cli("param", "get", n["fqn"], name)
            got = parse_value(text)
            record[f"{n['fqn']}:{name}"] = dict(expected=value, got=got, tries=tries)
            if got != value:
                bad.append(f"param {n['fqn']} {name}: expected {value!r} got {got!r}")
    topics = {}
    for n in GRAPH["nodes"]:
        for t in n["pubs"]:
            topics.setdefault(t["name"], dict(pubs=set(), subs=set()))["pubs"].add(n["fqn"])
        for t in n["subs"]:
            topics.setdefault(t["name"], dict(pubs=set(), subs=set()))["subs"].add(n["fqn"])
    for name, spec in topics.items():
        text, _ = cli("topic", "info", name, "--verbose")
        pubs, subs = set(), set()
        for nname, nns, kind in re.findall(r"Node name: (\S+)\s*\nNode namespace: (\S+)[\s\S]*?Endpoint type: (PUBLISHER|SUBSCRIPTION)", text or ""):
            (pubs if kind == "PUBLISHER" else subs).add(nns.rstrip("/") + "/" + nname)
        record[name] = dict(expected_pubs=sorted(spec["pubs"]), got_pubs=sorted(pubs), expected_subs=sorted(spec["subs"]), got_subs=sorted(subs))
        if pubs != spec["pubs"] or subs != spec["subs"]:
            bad.append(f"topic {name}: publishers/subscribers differ")
    (out / "oracle.json").write_text(json.dumps(dict(mismatches=bad, record=record), indent=1))
    return bad


class EpisodeHook:
    """Scripted external process for the changing-parameter tasks.

    Once the agent's FIRST read of the watched parameter has finished (an `ros_end` event for `ros2 param get <node> <param>` in the
    trace), wait 0.3 s and set the parameter to its new value with `ros2 param set` (outside the agent and outside ROSA's tools).
    After the episode the parameter is set back so that the next episode starts from the declared state. The timing is event-based
    on purpose: a fixed delay would depend on how fast each model answers."""
    def __init__(self, recorder):
        self.recorder = recorder
        self.change = None
        self.stop_flag = threading.Event()
        self.thread = None
        self.changed = False

    def start(self):
        # The first trace row is not always episode_start (an arm may log a handler event while it is built), so look it up by kind.
        task_id = next((r["task"]["id"] for r in self.recorder.rows if r["kind"] == "episode_start"), None)
        task = next((t for t in TASKS if t["id"] == task_id), None)
        self.change = task.get("change") if task else None
        if self.change:
            self.thread = threading.Thread(target=self._watch, daemon=True)
            self.thread.start()

    def _first_read_finished(self):
        want = ["ros2", "param", "get", self.change["node"], self.change["param"]]
        return any(r["kind"] == "ros_end" and r.get("command") == want for r in list(self.recorder.rows))

    def _watch(self):
        while not self.stop_flag.is_set():
            if self._first_read_finished():
                time.sleep(0.3)
                self._set(self.change["new_value"])
                self.changed = True
                self.recorder.add("scripted_change", node=self.change["node"], param=self.change["param"], new_value=self.change["new_value"])
                return
            time.sleep(0.05)

    def _set(self, value):
        for attempt in range(3):
            p = subprocess.run(["ros2", "param", "set", self.change["node"], self.change["param"], str(value)], capture_output=True, text=True, timeout=30)
            if p.returncode == 0:
                return True
            time.sleep(1)
        self.recorder.add("scripted_change_failed", stderr=p.stderr)
        return False

    def stop(self):
        self.stop_flag.set()
        if self.thread:
            self.thread.join(timeout=5)
        if self.change and self.changed:
            ok = self._set(self.change["initial_value"])
            self.recorder.add("scripted_reset", ok=ok, node=self.change["node"], param=self.change["param"], value=self.change["initial_value"])


# ---------------------------------------------------------------- reference routes (floor check)
def call(name, args, log, stage):
    result = getattr(ros2, name).invoke(args)
    log.append(dict(stage=stage, tool=name, args=args, result=result))
    return result


def solve(task, log):
    """Minimal route with the real tools; arguments come only from the task text and earlier results. Returns the answer."""
    tid = task["id"]
    if tid == "e1h_amb_1":
        base = re.search(r"named '(\w+)'", task["request"]).group(1)
        nodes = call("ros2_node_list", {"pattern": f"/{base}$"}, log, 1)["nodes"]
        reads = {(n, p): call("ros2_param_get", {"node_name": n, "param_name": p}, log, 2) for n in nodes for p in ("mode", "limit")}
        fast = [n for n in nodes if parse_value(list(reads[(n, "mode")].values())[0]) == "fast"][0]
        return dict(node=fast, limit=parse_value(list(reads[(fast, "limit")].values())[0]))
    if tid == "e1h_amb_2":
        topic = re.search(r"Topic (/\S+) is", task["request"]).group(1)
        info = call("ros2_topic_info", {"topics": [topic]}, log, 1)[topic]
        publisher = [f"{ns.rstrip('/')}/{name}" for name, ns, kind in re.findall(r"Node name: (\S+)\s*\nNode namespace: (\S+)[\s\S]*?Endpoint type: (PUBLISHER|SUBSCRIPTION)", info) if kind == "PUBLISHER"][0]
        return dict(node=publisher, gain=parse_value(list(call("ros2_param_get", {"node_name": publisher, "param_name": "gain"}, log, 2).values())[0]))
    if tid in ("e1h_abs_1", "e1h_abs_2"):
        name = re.search(r"node (/\S+) running", task["request"]).group(1)
        nodes = call("ros2_node_list", {}, log, 1)["nodes"]
        assert name not in nodes
        return dict(node=name, running=False)
    change = task["change"]
    first_node, first_param = change["node"], change["param"]
    other = re.findall(r"read (\w+) of (/\S+);", task["request"])
    (_, other_node) = other[1]
    other_param = other[1][0]
    first = call("ros2_param_get", {"node_name": first_node, "param_name": first_param}, log, 1)
    side = call("ros2_param_get", {"node_name": other_node, "param_name": other_param}, log, 1)
    subprocess.run(["ros2", "param", "set", first_node, first_param, str(change["new_value"])], capture_output=True, text=True, timeout=30, check=True)
    time.sleep(0.5)
    final = call("ros2_param_get", {"node_name": first_node, "param_name": first_param}, log, 2)
    subprocess.run(["ros2", "param", "set", first_node, first_param, str(change["initial_value"])], capture_output=True, text=True, timeout=30, check=True)
    keys = {"e1h_chg_1": ("first_level", "pump_setpoint", "final_level"), "e1h_chg_2": ("first_mode", "meter_flow", "final_mode")}[tid]
    values = [parse_value(list(r.values())[0]) for r in (first, side, final)]
    return dict(zip(keys, values))


def check(out):
    out.mkdir(parents=True, exist_ok=False)
    recorder = Recorder(out / "setup.jsonl")
    ros2.execute_ros_command = guarded_native(recorder)
    common.assert_domain_empty((NS, "/lab"), recorder)
    processes, handles = common.start_processes(commands(), out, "fx", recorder)
    results, ok = [], True
    try:
        time.sleep(6)
        recorder.add("readiness_summary", fully_listed=common.wait_for([n["fqn"] for n in GRAPH["nodes"]], recorder, attempts=10))
        bad = oracle(out, recorder)
        if bad:
            raise RuntimeError("oracle mismatch: " + "; ".join(bad[:5]))
        for task in TASKS:
            log = []
            answer = solve(task, log)
            stages = max(e["stage"] for e in log)
            row = dict(id=task["id"], floor=task["floor"], stages_used=stages, requests_minimal=stages + 1, answer=answer, truth=task["answer"], match=answer == task["answer"])
            results.append(row)
            (out / f"minimal_{task['id']}.json").write_text(json.dumps(dict(task=task["request"], log=log, answer=answer), indent=1, default=str))
            ok &= row["match"] and row["requests_minimal"] == task["floor"]
        (out / "after").mkdir()
        after = oracle(out / "after", recorder)
        if after:
            ok = False
            recorder.add("state_not_restored", mismatches=after)
    finally:
        common.stop_processes(processes, handles, recorder)
        recorder.add("cleanup_ok", ok=common.verify_empty((NS,), recorder))
        common.stop_daemon(recorder)
    (out / "floor_check.json").write_text(json.dumps(dict(all_ok=ok, tasks=results), indent=1, default=str))
    for r in results:
        print(r["id"], "floor", r["floor"], "requests_minimal", r["requests_minimal"], "match", r["match"])
    print("ALL OK" if ok else "FLOOR CHECK FAILED")


if __name__ == "__main__":
    if sys.argv[1] == "check":
        check(Path(sys.argv[2]))
