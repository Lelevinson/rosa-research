"""Stage 3: generate the fixture graph and the 12 tasks from a recorded seed (no ROS needed).

  python3 stage3_build.py            -> stage3_graph.json, stage3_tasks.json

Depth = number of sequential observation stages (each stage's arguments come only from earlier stages;
independent reads inside a stage are one stage). Floor = depth + 1 final answer. Entry points are named in the
task text except in the service-route template, where the node_list discovery stage counts in the depth.
"""
import json
import random
from pathlib import Path

SEED = 20261113
WORDS = ["relay", "courier", "gantry", "beacon", "harbor", "spindle", "quartz", "ember", "lattice", "vector", "mantle", "pylon",
         "tundra", "cobalt", "ridge", "falcon", "sable", "orchid", "meridian", "anvil", "cipher", "drift", "ferry", "glacier",
         "hollow", "juniper", "kiln", "lumen", "marrow", "nimbus", "opal", "prism",
         "quarry", "raven", "slate", "thistle", "umber", "valley", "willow", "xenon", "yarrow", "zephyr", "alder", "birch",
         "cedar", "dune", "elm", "fjord", "grove", "heath", "inlet", "jetty", "knoll", "lagoon", "mesa", "nettle",
         "oasis", "pebble", "quill", "reef", "shoal", "talon", "upland", "vista", "wharf", "yonder"]
TYPES = [("std_msgs/msg/String", "String"), ("std_msgs/msg/Int32", "Int32"), ("std_msgs/msg/Float32", "Float32")]


def build():
    rng = random.Random(SEED)
    ns = f"/plant{rng.randint(10, 99)}"
    names = rng.sample(WORDS, len(WORDS))
    take = iter(names)
    def node(role, **kw):
        short = next(take)
        return dict(key=role, name=short, fqn=f"{ns}/{short}", params=kw.get("params", {}), pubs=[], subs=[], services=[])
    def topic(role_type=None):
        word = next(take)
        msg = TYPES[rng.randrange(3)] if role_type is None else role_type
        return dict(name=f"{ns}/{word}_t", type=msg[0], short=msg[1])
    gain = lambda: rng.randint(10, 99)
    nodes, topics = {}, {}
    def add(n):
        nodes[n["key"]] = n
        return n
    # pipeline s0..s4 : s_i publishes c_i, subscribes c_{i-1}
    pipe = [add(node(f"s{i}", params={"gain": gain()})) for i in range(5)]
    ctop = [topic() for _ in range(5)]
    for i, n in enumerate(pipe):
        n["pubs"].append(ctop[i])
        if i:
            n["subs"].append(ctop[i - 1])
    # pointer chain q0..q3
    chain = [add(node(f"q{i}", params={"setpoint": rng.randint(100, 999)})) for i in range(4)]
    for i, n in enumerate(chain):
        n["params"]["next_node"] = chain[i + 1]["fqn"] if i < 3 else "none"
        n["pubs"].append(topic())  # every node publishes something so graph queries are not empty
    # hub with three inputs and its own output
    hub = add(node("hub", params={"gain": gain()}))
    ins = [topic(TYPES[k]) for k in range(3)]
    hub["subs"] += ins
    hubout = topic(TYPES[0])
    hub["pubs"].append(hubout)
    ws = [add(node(f"w{k}", params={"gain": gain()})) for k in range(3)]
    for k, w in enumerate(ws):
        w["pubs"].append(ins[k])
    # service provider, its peer, and a decoy provider
    peer = add(node("peer", params={"gain": gain()}))
    z = add(node("prov", params={"gain": gain(), "peer": peer["fqn"]}))
    z2 = add(node("decoy", params={"gain": gain()}))
    svc = dict(name=f"{ns}/{next(take)}_reset", type="std_srvs/srv/Trigger")
    svc2 = dict(name=f"{ns}/{next(take)}_reset", type="std_srvs/srv/Trigger")
    z["services"].append(svc)
    z2["services"].append(svc2)
    for n in (peer, z, z2):
        n["pubs"].append(topic())
    # distractors
    for i in range(3):
        d = add(node(f"d{i}", params={"gain": gain()}))
        d["pubs"].append(topic())
        d["subs"].append(ctop[i])  # listen to early pipeline topics, as extra subscribers (not c3 or c4)
    graph = dict(seed=SEED, namespace=ns, nodes=list(nodes.values()))
    # ---- tasks
    P = lambda n, k: n["params"][k]
    tasks = []
    def task(tid, template, depth, request, answer, support, stages):
        tasks.append(dict(id=tid, template=template, depth=depth, floor=depth + 1, request=request, answer=answer,
                          support=support, stages=stages))
    c4, c3 = ctop[4], ctop[3]
    s4, s3 = pipe[4], pipe[3]
    ignore = "(ignore /parameter_events and /rosout)"
    task("u2", "upstream", 2, f"Topic {c4['name']} is published by one node. Find that node and read its gain parameter. Return JSON with keys node (the full node name) and gain (integer).",
         dict(node=s4["fqn"], gain=P(s4, "gain")), [["text", s4["fqn"]], ["param", s4["fqn"], "gain", P(s4, "gain")]],
         ["topic_info(c4) -> publisher node", "param_get(node, gain)"])
    req3 = (f"Topic {c4['name']} is published by one node, and that node subscribes to exactly one application topic {ignore}. "
            f"Find the node that publishes that input topic. Return JSON with keys publisher (full name of the node that publishes {c4['name']}), "
            f"input_topic (full name of the topic that node subscribes to) and upstream (full name of the node that publishes that input topic)")
    ans3 = dict(publisher=s4["fqn"], input_topic=c3["name"], upstream=s3["fqn"])
    sup3 = [["text", s4["fqn"]], ["text", c3["name"]], ["text", s3["fqn"]]]
    task("u3", "upstream", 3, req3 + ".", ans3, sup3, ["topic_info(c4) -> publisher", "node_info(publisher) -> input topic", "topic_info(input) -> upstream node"])
    task("u4", "upstream", 4, req3 + " and upstream_gain (the integer gain parameter of that upstream node).", dict(ans3, upstream_gain=P(s3, "gain")),
         sup3 + [["param", s3["fqn"], "gain", P(s3, "gain")]], ["topic_info(c4)", "node_info(publisher)", "topic_info(input)", "param_get(upstream, gain)"])
    q = chain
    pn = "has a string parameter next_node that names the node it hands off to and an integer parameter setpoint"
    task("p2", "pointer", 2, f"Node {q[2]['fqn']} {pn}. Read its next_node, then read the setpoint of the node it names. Return JSON with keys next_node (the full node name) and setpoint (integer).",
         dict(next_node=q[3]["fqn"], setpoint=P(q[3], "setpoint")), [["text", q[3]["fqn"]], ["param", q[3]["fqn"], "setpoint", P(q[3], "setpoint")], ["param", q[2]["fqn"], "next_node", q[3]["fqn"]]],
         ["param_get(q2, next_node)", "param_get(q3, setpoint)"])
    task("p3", "pointer", 3, f"Node {q[1]['fqn']} {pn}, and so does every node in the chain. Read next_node of {q[1]['fqn']}, then read next_node of the node it names, then read the setpoint of the node named by that second read. Return JSON with keys first (the node named by {q[1]['fqn']}), second (the node named by first) and setpoint (integer, the setpoint of second).",
         dict(first=q[2]["fqn"], second=q[3]["fqn"], setpoint=P(q[3], "setpoint")),
         [["param", q[1]["fqn"], "next_node", q[2]["fqn"]], ["param", q[2]["fqn"], "next_node", q[3]["fqn"]], ["param", q[3]["fqn"], "setpoint", P(q[3], "setpoint")]],
         ["param_get(q1,next)", "param_get(q2,next)", "param_get(q3,setpoint)"])
    task("p4", "pointer", 4, f"Node {q[0]['fqn']} {pn}, and so does every node in the chain. Follow next_node three times starting at {q[0]['fqn']}, then read the setpoint of the last node. Return JSON with keys first, second and third (the full names of the nodes reached by the first, second and third next_node reads) and setpoint (integer, the setpoint of third).",
         dict(first=q[1]["fqn"], second=q[2]["fqn"], third=q[3]["fqn"], setpoint=P(q[3], "setpoint")),
         [["param", q[0]["fqn"], "next_node", q[1]["fqn"]], ["param", q[1]["fqn"], "next_node", q[2]["fqn"]], ["param", q[2]["fqn"], "next_node", q[3]["fqn"]], ["param", q[3]["fqn"], "setpoint", P(q[3], "setpoint")]],
         ["param_get(q0,next)", "param_get(q1,next)", "param_get(q2,next)", "param_get(q3,setpoint)"])
    h = hub
    base = f"Topic {hubout['name']} is published by one node. Find that node and list the application topics it subscribes to {ignore}"
    inputs = {t["name"]: t["type"] for t in ins}
    task("h2", "hub", 2, base + " with their message types. Return JSON with keys node (the full node name) and inputs (an object mapping each input topic's full name to its message type).",
         dict(node=h["fqn"], inputs=inputs), [["text", h["fqn"]]] + [["text", k] for k in inputs] + [["text", v] for v in set(inputs.values())],
         ["topic_info(out) -> hub node", "node_info(hub) -> inputs and types"])
    pubs = {t["name"]: ws[k]["fqn"] for k, t in enumerate(ins)}
    task("h3", "hub", 3, base + ". Then find which node publishes each of those input topics. Return JSON with keys node (the full node name) and publishers (an object mapping each input topic's full name to the full name of the node that publishes it).",
         dict(node=h["fqn"], publishers=pubs), [["text", h["fqn"]]] + [["text", k] for k in pubs] + [["text", v] for v in pubs.values()],
         ["topic_info(out)", "node_info(hub)", "topic_info(each input) [fan-out, one request]"])
    gains = {ws[k]["fqn"]: P(ws[k], "gain") for k in range(3)}
    task("h4", "hub", 4, base + ". Then find which node publishes each of those input topics and read each publisher's gain parameter. Return JSON with keys node (the full node name), publishers (an object mapping each input topic's full name to the full name of the node that publishes it) and gains (an object mapping each publisher's full name to its integer gain).",
         dict(node=h["fqn"], publishers=pubs, gains=gains), [["text", h["fqn"]]] + [["text", k] for k in pubs] + [["text", v] for v in pubs.values()] + [["param", n, "gain", g] for n, g in gains.items()],
         ["topic_info(out)", "node_info(hub)", "topic_info(each input) [fan-out]", "param_get(each publisher, gain) [fan-out]"])
    sb = f"Service {svc['name']} is provided by exactly one running node."
    task("v2", "service", 2, sb + " Find which node provides it and the service's message type. Return JSON with keys node (the full node name) and type.",
         dict(node=z["fqn"], type=svc["type"]), [["text", z["fqn"]], ["text", svc["type"]]],
         ["node_list", "node_info(all nodes) [fan-out] (+ service_info optional)"])
    task("v3", "service", 3, sb + " Find which node provides it and read that node's gain parameter. Return JSON with keys node (the full node name) and gain (integer).",
         dict(node=z["fqn"], gain=P(z, "gain")), [["text", z["fqn"]], ["param", z["fqn"], "gain", P(z, "gain")]],
         ["node_list", "node_info(all nodes) [fan-out]", "param_get(provider, gain)"])
    task("v4", "service", 4, sb + " Find which node provides it. That node has a string parameter peer that names another node; read that parameter, then read the gain of the node it names. Return JSON with keys node (the provider's full name), peer (the full name read from its peer parameter) and peer_gain (integer).",
         dict(node=z["fqn"], peer=peer["fqn"], peer_gain=P(peer, "gain")), [["text", z["fqn"]], ["param", z["fqn"], "peer", peer["fqn"]], ["param", peer["fqn"], "gain", P(peer, "gain")]],
         ["node_list", "node_info(all nodes) [fan-out]", "param_get(provider, peer)", "param_get(peer, gain)"])
    return graph, tasks


if __name__ == "__main__":
    graph, tasks = build()
    here = Path(__file__).resolve().parent
    (here / "stage3_graph.json").write_text(json.dumps(graph, indent=1))
    (here / "stage3_tasks.json").write_text(json.dumps(tasks, indent=1))
    print(len(graph["nodes"]), "nodes;", len(tasks), "tasks; namespace", graph["namespace"])
    for t in tasks:
        print(t["id"], "depth", t["depth"], "floor", t["floor"], "|", t["request"][:110])
