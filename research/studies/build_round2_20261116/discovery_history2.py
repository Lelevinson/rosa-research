"""History scan 2 (read-only): did the agent's `ros2 node info` / `ros2 topic info --verbose` ever return less than the declared stage 3 fixture graph says?
Counts calls whose stdout lacks a declared topic/service of that node (node info) or a declared publisher/subscriber (topic info). stage 3 graph only."""
import glob, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
G = json.loads((ROOT / "research/studies/headroom_diagnostic_20261112/stage3_graph.json").read_text())
nodes = {n["fqn"]: n for n in G["nodes"]}
topics = {}
for n in G["nodes"]:
    for t in n["pubs"]: topics.setdefault(t["name"], dict(pubs=set(), subs=set()))["pubs"].add(n["fqn"])
    for t in n["subs"]: topics.setdefault(t["name"], dict(pubs=set(), subs=set()))["subs"].add(n["fqn"])
stats = dict(node_info=[0, 0, []], topic_info=[0, 0, []])
for trace in glob.glob(str(ROOT / "research/_artifacts/runs/**/trace.jsonl"), recursive=True):
    text = Path(trace).read_text(errors="replace")
    if "plant32" not in text or '"ros_end"' not in text:
        continue
    for line in text.splitlines():
        if '"ros_end"' not in line:
            continue
        e = json.loads(line); cmd = e.get("command") or []
        if e.get("returncode") != 0 or len(cmd) < 4:
            continue
        if cmd[1:3] == ["node", "info"] and cmd[3] in nodes:
            n = nodes[cmd[3]]; want = [t["name"] for t in n["pubs"] + n["subs"]] + [s["name"] for s in n["services"]]
            miss = [w for w in want if w not in e["stdout"]]
            stats["node_info"][0] += 1; stats["node_info"][1] += bool(miss)
            if miss and len(stats["node_info"][2]) < 5: stats["node_info"][2].append((trace.split("runs/")[1][:70], cmd[3], miss))
        elif cmd[1:3] == ["topic", "info"] and cmd[3] in topics and "--verbose" in cmd:
            pubs, subs = set(), set()
            for nn, ns, kind in re.findall(r"Node name: (\S+)\s*\nNode namespace: (\S+)[\s\S]*?Endpoint type: (PUBLISHER|SUBSCRIPTION)", e["stdout"]):
                (pubs if kind == "PUBLISHER" else subs).add(ns.rstrip("/") + "/" + nn)
            bad = pubs != topics[cmd[3]]["pubs"] or subs != topics[cmd[3]]["subs"]
            stats["topic_info"][0] += 1; stats["topic_info"][1] += bad
            if bad and len(stats["topic_info"][2]) < 5: stats["topic_info"][2].append((trace.split("runs/")[1][:70], cmd[3], sorted(topics[cmd[3]]["pubs"] - pubs), sorted(topics[cmd[3]]["subs"] - subs)))
print(json.dumps(stats, indent=1, default=str))
