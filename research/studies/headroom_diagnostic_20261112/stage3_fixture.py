"""Stage 3 fixture manager: start/stop nodes, oracle check, and the reference (minimal-sequence) solver.

  uv run python stage3_fixture.py check OUTDIR     start fixture, oracle check, run every task's minimal stage
                                                   sequence with the real ROSA tools, stop, verify empty.
No model inference. ROS domain must be set by the caller (213 for the floor check).
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor"))
sys.path.insert(0, str(HERE))
import run_stage1 as common  # noqa: E402  (fixture helpers reused: start/stop/wait/cleanup)
from menu_run_study import Recorder, guarded_native  # noqa: E402
from rosa.tools import ros2  # noqa: E402

GRAPH = json.loads((HERE / "stage3_graph.json").read_text())
TASKS = json.loads((HERE / "stage3_tasks.json").read_text())
NS = GRAPH["namespace"]
NODES = {n["key"]: n for n in GRAPH["nodes"]}


def commands():
    return [["python3", str(HERE / "stage3_node.py"), str(HERE / "stage3_graph.json"), n["key"]] for n in GRAPH["nodes"]]


def cli(*argv, retries=3):
    for attempt in range(retries):
        p = subprocess.run(["ros2", *argv], capture_output=True, text=True, timeout=40)
        if p.returncode == 0:
            return p.stdout, attempt
        time.sleep(2)
    return None, retries


def oracle(out, recorder):
    """Direct reads of every declared fact. Returns list of mismatches (empty = oracle agrees with the declared graph)."""
    bad, record = [], {}
    nodes_out, _ = cli("node", "list", "--no-daemon", "--spin-time", "4")
    listed = set((nodes_out or "").splitlines())
    for n in GRAPH["nodes"]:
        if n["fqn"] not in listed:
            bad.append(f"node not listed: {n['fqn']}")
    for n in GRAPH["nodes"]:
        for name, value in n["params"].items():
            text, tries = cli("param", "get", n["fqn"], name)
            got = None
            if text:
                m = re.search(r"(Integer|String) value is:\s*(.*)", text)
                got = int(m[2]) if m and m[1] == "Integer" else (m[2].strip() if m else None)
            record[f"{n['fqn']}:{name}"] = dict(expected=value, got=got, tries=tries)
            if got != value:
                bad.append(f"param {n['fqn']} {name}: expected {value!r} got {got!r}")
    topics = {}
    for n in GRAPH["nodes"]:
        for t in n["pubs"]:
            topics.setdefault(t["name"], dict(type=t["type"], pubs=set(), subs=set()))["pubs"].add(n["fqn"])
        for t in n["subs"]:
            topics.setdefault(t["name"], dict(type=t["type"], pubs=set(), subs=set()))["subs"].add(n["fqn"])
    for name, spec in topics.items():
        text, _ = cli("topic", "info", name, "--verbose")
        pubs = set()
        subs = set()
        for nname, nns, kind in re.findall(r"Node name: (\S+)\s*\nNode namespace: (\S+)[\s\S]*?Endpoint type: (PUBLISHER|SUBSCRIPTION)", text or ""):
            (pubs if kind == "PUBLISHER" else subs).add(nns.rstrip("/") + "/" + nname)
        record[name] = dict(expected_pubs=sorted(spec["pubs"]), got_pubs=sorted(pubs), expected_subs=sorted(spec["subs"]), got_subs=sorted(subs))
        if pubs != spec["pubs"] or subs != spec["subs"]:
            bad.append(f"topic {name}: publishers/subscribers differ")
    for n in GRAPH["nodes"]:
        for s in n["services"]:
            text, _ = cli("node", "info", n["fqn"])
            if not text or s["name"] not in text:
                bad.append(f"service {s['name']} not on {n['fqn']}")
    (out / "oracle.json").write_text(json.dumps(dict(mismatches=bad, record=record), indent=1))
    return bad


# ---------------------------------------------------------------- reference solver
def call(name, args, log, stage):
    result = getattr(ros2, name).invoke(args)
    log.append(dict(stage=stage, tool=name, args=args, result=result))
    return result


def endpoints(text):
    out = []
    for nname, nns, kind in re.findall(r"Node name: (\S+)\s*\nNode namespace: (\S+)[\s\S]*?Endpoint type: (PUBLISHER|SUBSCRIPTION)", text):
        out.append((nns.rstrip("/") + "/" + nname, kind))
    return out


def node_sections(text):
    sections, current = {}, None
    for line in text.splitlines():
        h = re.match(r"^  ([A-Za-z ]+):\s*$", line)
        if h:
            current = h.group(1)
            sections[current] = {}
            continue
        i = re.match(r"^    (\S+): (\S+)", line)
        if i and current:
            sections[current][i.group(1)] = i.group(2)
    return sections


def pvalue(result):
    raw = list(result.values())[0]
    m = re.search(r"(Integer|String) value is:\s*(.*)", str(raw))
    return int(m[2]) if m[1] == "Integer" else m[2].strip()


def solve(task):
    """Minimal stage sequence. Each stage's arguments come only from the task text and earlier stages' results."""
    log, tid, req = [], task["id"], task["request"]
    topic = lambda: re.search(rf"({re.escape(NS)}/\w+_t)", req).group(1)
    first_node = lambda: re.search(rf"({re.escape(NS)}/\w+)\b", req).group(1)
    app = lambda d: {k: v for k, v in d.items() if k not in ("/parameter_events", "/rosout")}
    kind = tid[0]
    if kind == "u":
        c4 = topic()
        info = call("ros2_topic_info", {"topics": [c4]}, log, 1)
        pub = [n for n, k in endpoints(info[c4]) if k == "PUBLISHER"][0]
        if tid == "u2":
            return log, dict(node=pub, gain=pvalue(call("ros2_param_get", {"node_name": pub, "param_name": "gain"}, log, 2)))
        sec = node_sections(call("ros2_node_info", {"nodes": [pub]}, log, 2)[pub])
        inp = list(app(sec["Subscribers"]))[0]
        up = [n for n, k in endpoints(call("ros2_topic_info", {"topics": [inp]}, log, 3)[inp]) if k == "PUBLISHER"][0]
        ans = dict(publisher=pub, input_topic=inp, upstream=up)
        if tid == "u4":
            ans["upstream_gain"] = pvalue(call("ros2_param_get", {"node_name": up, "param_name": "gain"}, log, 4))
        return log, ans
    if kind == "p":
        node = first_node()
        hops = {"p2": 1, "p3": 2, "p4": 3}[tid]
        names, stage = [], 1
        for _ in range(hops):
            node = pvalue(call("ros2_param_get", {"node_name": node, "param_name": "next_node"}, log, stage))
            names.append(node)
            stage += 1
        sp = pvalue(call("ros2_param_get", {"node_name": node, "param_name": "setpoint"}, log, stage))
        keys = {"p2": ["next_node"], "p3": ["first", "second"], "p4": ["first", "second", "third"]}[tid]
        return log, dict(zip(keys, names), setpoint=sp)
    if kind == "h":
        out = topic()
        hub = [n for n, k in endpoints(call("ros2_topic_info", {"topics": [out]}, log, 1)[out]) if k == "PUBLISHER"][0]
        subs = app(node_sections(call("ros2_node_info", {"nodes": [hub]}, log, 2)[hub])["Subscribers"])
        if tid == "h2":
            return log, dict(node=hub, inputs=subs)
        info = call("ros2_topic_info", {"topics": list(subs)}, log, 3)
        pubs = {t: [n for n, k in endpoints(info[t]) if k == "PUBLISHER"][0] for t in subs}
        if tid == "h3":
            return log, dict(node=hub, publishers=pubs)
        gains = {n: pvalue(call("ros2_param_get", {"node_name": n, "param_name": "gain"}, log, 4)) for n in pubs.values()}
        return log, dict(node=hub, publishers=pubs, gains=gains)
    svc = re.search(rf"({re.escape(NS)}/\w+_reset)", req).group(1)
    listed = [n for n in call("ros2_node_list", {}, log, 1)["nodes"] if n.startswith(NS + "/")]
    infos = call("ros2_node_info", {"nodes": listed}, log, 2)
    provider, stype = [(n, node_sections(t)["Service Servers"][svc]) for n, t in infos.items() if svc in node_sections(t).get("Service Servers", {})][0]
    if tid == "v2":
        return log, dict(node=provider, type=stype)
    if tid == "v3":
        return log, dict(node=provider, gain=pvalue(call("ros2_param_get", {"node_name": provider, "param_name": "gain"}, log, 3)))
    peer = pvalue(call("ros2_param_get", {"node_name": provider, "param_name": "peer"}, log, 3))
    return log, dict(node=provider, peer=peer, peer_gain=pvalue(call("ros2_param_get", {"node_name": peer, "param_name": "gain"}, log, 4)))


def check(out):
    out.mkdir(parents=True, exist_ok=False)
    recorder = Recorder(out / "setup.jsonl")
    ros2.execute_ros_command = guarded_native(recorder)
    prefix = (NS,)
    common.assert_domain_empty(prefix, recorder)
    processes, handles = common.start_processes(commands(), out, "fx", recorder)
    results, ok = [], True
    try:
        time.sleep(6)
        expected = [n["fqn"] for n in GRAPH["nodes"]]
        listed = common.wait_for(expected, recorder, attempts=10)
        recorder.add("readiness_summary", fully_listed=listed)
        bad = oracle(out, recorder)
        if bad:
            raise RuntimeError("oracle mismatch: " + "; ".join(bad[:5]))
        for task in TASKS:
            log, answer = solve(task)
            stages = max(e["stage"] for e in log)
            truth = task["answer"]
            row = dict(id=task["id"], depth=task["depth"], floor=task["floor"], stages_used=stages, requests_minimal=stages + 1,
                       answer=answer, truth=truth, match=answer == truth, stages_plan=task["stages"], calls=len(log))
            results.append(row)
            (out / f"minimal_{task['id']}.json").write_text(json.dumps(dict(task=task["request"], log=log, answer=answer), indent=1, default=str))
            ok &= row["match"] and stages == task["depth"] and stages + 1 == task["floor"]
    finally:
        common.stop_processes(processes, handles, recorder)
        recorder.add("cleanup_ok", ok=common.verify_empty(prefix, recorder))
        common.stop_daemon(recorder)
    (out / "floor_check.json").write_text(json.dumps(dict(all_ok=ok, tasks=results), indent=1, default=str))
    for r in results:
        print(r["id"], "depth", r["depth"], "floor", r["floor"], "stages used", r["stages_used"], "match", r["match"])
    print("ALL OK" if ok else "FLOOR CHECK FAILED")


if __name__ == "__main__":
    if sys.argv[1] == "check":
        check(Path(sys.argv[2]))
