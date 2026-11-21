"""Name-fix fixture manager: node commands, oracle and the reference-route check with the real ROSA tools (clone of e1h_fixture.py for the /nf graph; no scripted change).

  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python namefix_fixture.py check OUTDIR     start the fixture, oracle, run each task's minimal route with the real tools, score the
  route's answer with scorer v2.0, stop, verify empty. No model inference.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
STAGE3 = STUDIES / "headroom_diagnostic_20261112"
sys.path.insert(0, str(STAGE3 / "vendor"))
sys.path.insert(0, str(STAGE3))
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
import run_stage1 as common  # noqa: E402  (fixture helpers: start/stop/wait/cleanup)
from menu_run_study import Recorder, guarded_native  # noqa: E402
from rosa.tools import ros2  # noqa: E402

GRAPH = json.loads((HERE / "namefix_graph.json").read_text())
TASKS = json.loads((HERE / "namefix_tasks.json").read_text())
NS = GRAPH["namespace"]
NODES = {n["fqn"]: n for n in GRAPH["nodes"]}


def commands():
    return [["python3", str(HERE / "namefix_node.py"), str(HERE / "namefix_graph.json"), n["key"]] for n in GRAPH["nodes"]]


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
    """Direct reads of every declared fact; returns mismatches (empty = the fixture is in its declared state)."""
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


# ---------------------------------------------------------------- reference routes (floor check and support check)
ENDPOINT = re.compile(r"Node name: (\S+)\s*\nNode namespace: (\S+)[\s\S]*?Endpoint type: (PUBLISHER|SUBSCRIPTION)")


def call(name, args, log, stage):
    result = getattr(ros2, name).invoke(args)
    log.append(dict(stage=stage, tool=name, args=args, result=result))
    return result


def endpoints(info, kind):
    return [f"{ns.rstrip('/')}/{name}" for name, ns, k in ENDPOINT.findall(info) if k == kind]


def solve(task, log):
    """Minimal route with the real tools; arguments come only from the task text and earlier results. Returns the answer."""
    tid, text = task["id"], task["request"]
    if tid in ("nf_single_1", "nf_single_2"):
        topic = re.search(r"Topic (/\S+) ", text).group(1)
        info = call("ros2_topic_info", {"topics": [topic]}, log, 1)[topic]
        return dict(node=endpoints(info, "PUBLISHER" if tid == "nf_single_1" else "SUBSCRIPTION")[0])
    if tid == "nf_multi_1":
        topic = re.search(r"Topic (/\S+) has", text).group(1)
        names = endpoints(call("ros2_topic_info", {"topics": [topic]}, log, 1)[topic], "SUBSCRIPTION")
        return dict(gains={n: parse_value(list(call("ros2_param_get", {"node_name": n, "param_name": "gain"}, log, 2).values())[0]) for n in names})
    if tid == "nf_multi_2":
        node = re.search(r"Node (/\S+) subscribes", text).group(1)
        info = call("ros2_node_info", {"nodes": [node]}, log, 1)[node]
        section = info.split("Subscribers:")[1].split("Publishers:")[0]
        topics = [t for t in re.findall(r"(/nf/\S+?):", section)]
        return dict(upstream={t: endpoints(call("ros2_topic_info", {"topics": [t]}, log, 2)[t], "PUBLISHER")[0] for t in topics})
    if tid == "nf_amb_1":
        base = re.search(r"named '(\w+)'", text).group(1)
        nodes = call("ros2_node_list", {"pattern": f"/{base}$"}, log, 1)["nodes"]
        reads = {(n, p): call("ros2_param_get", {"node_name": n, "param_name": p}, log, 2) for n in nodes for p in ("mode", "limit")}
        fast = [n for n in nodes if parse_value(list(reads[(n, "mode")].values())[0]) == "fast"][0]
        return dict(node=fast, limit=parse_value(list(reads[(fast, "limit")].values())[0]))
    if tid == "nf_amb_2":
        topic = re.search(r"Topic (/\S+) is", text).group(1)
        publisher = endpoints(call("ros2_topic_info", {"topics": [topic]}, log, 1)[topic], "PUBLISHER")[0]
        return dict(node=publisher, gain=parse_value(list(call("ros2_param_get", {"node_name": publisher, "param_name": "gain"}, log, 2).values())[0]))
    if tid == "nf_exact":
        node = re.search(r"Node (/\S+) has", text).group(1)
        return dict(node=node, gain=parse_value(list(call("ros2_param_get", {"node_name": node, "param_name": "gain"}, log, 1).values())[0]))
    name = re.search(r"node (/\S+) running", text).group(1)  # nf_absent
    assert name not in call("ros2_node_list", {}, log, 1)["nodes"]
    return dict(node=name, running=False)


def rows_of(log):
    rows = []
    for e in log:
        text = json.dumps(e["result"]) if not isinstance(e["result"], str) else e["result"]
        bad = isinstance(e["result"], dict) and any(isinstance(v, dict) and "error" in v for v in e["result"].values())
        rows.append(dict(name=e["tool"], args=e["args"], given_args=e["args"], output=e["result"], text=text, ok=not bad))
    return rows


def check(out):
    import scorer_v2 as v2
    out.mkdir(parents=True, exist_ok=False)
    recorder = Recorder(out / "setup.jsonl")
    ros2.execute_ros_command = guarded_native(recorder)
    common.assert_domain_empty((NS,), recorder)
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
            scored = v2.score_task(task, answer, rows_of(log))
            row = dict(id=task["id"], floor=task["floor"], requests_minimal=stages + 1, answer=answer, truth=task["answer"], match=answer == task["answer"], strict_supported=scored["supported_complete"], support_missing=scored["support_missing"])
            results.append(row)
            (out / f"minimal_{task['id']}.json").write_text(json.dumps(dict(task=task["request"], log=log, answer=answer, scored=scored), indent=1, default=str))
            ok &= row["match"] and row["requests_minimal"] == task["floor"] and row["strict_supported"]
    finally:
        common.stop_processes(processes, handles, recorder)
        recorder.add("cleanup_ok", ok=common.verify_empty((NS,), recorder))
        common.stop_daemon(recorder)
    (out / "floor_check.json").write_text(json.dumps(dict(all_ok=ok, tasks=results), indent=1, default=str))
    for r in results:
        print(r["id"], "floor", r["floor"], "requests_minimal", r["requests_minimal"], "match", r["match"], "strict_supported", r["strict_supported"], r["support_missing"])
    print("ALL OK" if ok else "FLOOR CHECK FAILED")


if __name__ == "__main__":
    if sys.argv[1] == "check":
        check(Path(sys.argv[2]))
