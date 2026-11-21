"""Offline replay of the frozen PROTOCOL.md on the pilot's C1 traces. No model, no ROS. Writes results.json; REPORT.md is written by report.py."""
import json, re, statistics, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "small_model_harness_20261115"
REPO = HERE.parents[2]
SNAP = json.loads((HERE / "snapshots.json").read_text())
EXCLUDED = set()
for g in json.loads((PILOT / "INFRA_EXCLUDED.json").read_text()).values():
    EXCLUDED |= set(g["run_ids"])
INFO_NEVER = {"ros2_param_get", "ros2_topic_echo", "ros2_doctor", "roslog_list", "read_log", "supertool", "final_answer", "ros2_topic_info"}
NOT_FOUND = re.compile(r"not found|Unable to find", re.I)


def index_snapshot(env):
    s = SNAP[env]["A"]
    nodes = set(s["node_list"]["nodes"])
    services = set(s["service_list"]["services"])
    served = set()
    for text in s["node_info"].values():
        block = text.split("Service Servers:")[1].split("Service Clients:")[0] if "Service Servers:" in text else ""
        served |= set(re.findall(r"^\s+(/\S+):", block, re.M))
    return dict(nodes=nodes, services=services, served=served, topics=set(s["topic_list"]["topics"]),
                tokens={v: len(json.dumps(SNAP[env][v])) / 4 for v in ("A", "B")})


def answered(call, result_text, snap, variant, derivable=False):
    name, args = call["name"], call.get("args") or {}
    if result_text is not None and re.match(r"(Invalid arguments|Tool .* (is not available|failed)|Invalid plan)", result_text):
        return False
    if name in ("ros2_node_list", "ros2_topic_list", "ros2_service_list"):
        return True
    if name == "ros2_node_info":
        names = args.get("nodes") or []
        return bool(names) and all(n in snap["nodes"] or (result_text and NOT_FOUND.search(result_text)) for n in names)
    if name == "ros2_service_info":
        names = args.get("services") or []
        return bool(names) and all(n in snap["served"] or (n not in snap["services"] and result_text and NOT_FOUND.search(result_text)) for n in names)
    if name == "ros2_param_list":
        node = args.get("node_name")
        return variant == "B" and (node is None or node in snap["nodes"])
    if name == "ros2_topic_info":
        return derivable and bool(args.get("topics")) and all(t in snap["topics"] for t in args["topics"])
    return False


def requests_of(trace):
    """List of dict(calls, results, input_tokens) in request order; results aligned to calls by tool_start order."""
    events = [json.loads(l) for l in trace.read_text().splitlines()]
    reqs, cur = [], None
    for e in events:
        if e["kind"] == "model_end":
            m = e["message"]
            cur = dict(calls=[dict(name=c["name"], args=c["args"]) for c in m.get("tool_calls", [])], results=[], input_tokens=(e.get("usage") or {}).get("input_tokens", 0))
            reqs.append(cur)
        elif e["kind"] == "tool_end" and cur is not None:
            cur["results"].append(json.dumps(e["output"]) if not isinstance(e["output"], str) else e["output"])
    return reqs


def analyse():
    rows = [json.loads(l) for l in (PILOT / "RESULTS_LOG.jsonl").read_text().splitlines()]
    rows = [r for r in rows if r["arm"] == "C1" and r["run_id"] not in EXCLUDED]
    snaps = {e: index_snapshot(e) for e in SNAP}
    out = []
    for r in rows:
        snap, reqs = snaps[r["env"]], requests_of(REPO / r["trace_path"])
        ep = dict(run_id=r["run_id"], model=r["model"], task=r["task"], env=r["env"], seed=r["seed"], requests=len(reqs), supported=r["supported_complete"])
        for variant in ("A", "B", "A_topicinfo_derivable"):
            v, derivable = variant[0], variant != "A" and variant != "B"
            removable, saved = [], 0
            for i, q in enumerate(reqs):
                if not q["calls"] or any(c["name"] == "final_answer" for c in q["calls"]):
                    continue
                ok = all(answered(c, q["results"][j] if j < len(q["results"]) else None, snap, v, derivable) for j, c in enumerate(q["calls"]))
                if ok:
                    removable.append(i); saved += q["input_tokens"]
            tokens = snap["tokens"][v]
            ep[variant] = dict(removable=len(removable), saved_tokens=saved, added_tokens=tokens * (len(reqs) - len(removable)), snapshot_tokens=tokens)
            ep[variant]["net_tokens"] = ep[variant]["added_tokens"] - saved
        ep["nonfinal_requests"] = sum(1 for q in reqs if not any(c["name"] == "final_answer" for c in q["calls"]) and q["calls"])
        out.append(ep)
    (HERE / "results.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    out = analyse()
    print(len(out), "C1 episodes")
