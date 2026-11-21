"""Generate the name-fix development fixture (graph + 8 designed tasks) from a seed. Deterministic. Built from the public E1h/Stage 3 templates only (no held-out definitions opened).
  uv run python namefix_build.py     writes namefix_graph.json and namefix_tasks.json next to this file
Namespace /nf, independent name draws (own word list, own seed). Designed stress cases (not a representative sample); unique suffixes AND colliding suffixes exist:
  nf_single_1  one name-valued answer: the single publisher of a topic                       (unique suffix)
  nf_single_2  one name-valued answer: the single subscriber of a topic                      (unique suffix)
  nf_multi_1   nested keys that are node names: gains of the three subscribers of a topic    (3 unique suffixes)
  nf_multi_2   nested keys that are topic names, values node names: the two input topics of a node and their publishers
  nf_amb_1     two nodes with the same base name in different namespaces; pick by a parameter (colliding suffix: the short name is ambiguous)
  nf_amb_2     two nodes with the same base name; pick the publisher of a topic (colliding suffix)
  nf_exact     full-name control: the node is given by its full name; answer repeats it exactly
  nf_absent    absent-name control: asks for /<ns>/<node>, which is NOT running; /nf/<ns>/<node> is running (a unique suffix of a different node: the known harm mode of suffix repair)
"""
import json
from pathlib import Path
import random

SEED = 20261124
WORDS = ["agate", "bolt", "cipher", "dagger", "easel", "fennel", "garnet", "harrow", "ivory", "jasper", "kestrel", "lantern", "mallet", "nectar", "obsidian", "pylon", "quiver",
         "ratchet", "spindle", "talon", "umbra", "vortex", "wicker", "xylem", "yeoman", "zenith", "anchor", "bobbin", "chisel", "dynamo", "eclipse", "flint", "gimbal", "hopper",
         "indigo", "juniperus", "kiln", "lathe", "mortar", "nozzle"]
HERE = Path(__file__).resolve().parent


def build():
    rng = random.Random(SEED)
    words = WORDS[:]
    rng.shuffle(words)
    take = lambda: words.pop()
    area1, area2, area3, amb_a, amb_b, abs_area = take(), take(), take(), take(), take(), take()
    nodes = []

    def add(namespace, name, params, pubs=(), subs=()):
        nodes.append(dict(key=f"n{len(nodes):02d}", name=name, namespace=namespace, fqn=f"{namespace}/{name}", params=params,
                          pubs=[dict(name=n, type=t) for n, t in pubs], subs=[dict(name=n, type=t) for n, t in subs], services=[]))
        return nodes[-1]["fqn"]

    F32, I32 = "std_msgs/msg/Float32", "std_msgs/msg/Int32"
    topic = lambda: f"/nf/{take()}_t"
    # single_1: one publisher of S1; single_2: one subscriber of S2 (decoy publishers/subscribers elsewhere)
    s1, s2 = topic(), topic()
    p1 = add(f"/nf/{area1}", take(), dict(gain=rng.randint(10, 99)), pubs=[(s1, F32)])
    q2 = add(f"/nf/{area2}", take(), dict(gain=rng.randint(10, 99)), subs=[(s2, I32)])
    add(f"/nf/{area3}", take(), dict(gain=rng.randint(10, 99)), subs=[(s1, F32)])   # subscriber of S1 (not asked)
    add(f"/nf/{area3}", take(), dict(gain=rng.randint(10, 99)), pubs=[(s2, I32)])   # publisher of S2 (not asked)
    # multi_1: topic M1 with exactly three subscribers in three namespaces
    m1 = topic()
    add(f"/nf/{area1}", take(), dict(gain=rng.randint(10, 99)), pubs=[(m1, I32)])
    subs3 = [add(f"/nf/{a}", take(), dict(gain=rng.randint(10, 99)), subs=[(m1, I32)]) for a in (area1, area2, area3)]
    # multi_2: node R publishes T4 and subscribes to two topics U1, U2, each published by a different node
    t4, u1, u2 = topic(), topic(), topic()
    v1 = add(f"/nf/{area2}", take(), dict(gain=rng.randint(10, 99)), pubs=[(u1, F32)])
    v2 = add(f"/nf/{area3}", take(), dict(gain=rng.randint(10, 99)), pubs=[(u2, I32)])
    r = add(f"/nf/{area1}", take(), dict(gain=rng.randint(10, 99)), pubs=[(t4, F32)], subs=[(u1, F32), (u2, I32)])
    # amb_1 / amb_2: two nodes with the same base name in different namespaces
    base1, base2, atopic = take(), take(), topic()
    fast_first, pub_first = rng.random() < 0.5, rng.random() < 0.5
    a1 = add(f"/nf/{amb_a}", base1, dict(mode="fast" if fast_first else "slow", limit=rng.randint(100, 999)))
    b1 = add(f"/nf/{amb_b}", base1, dict(mode="slow" if fast_first else "fast", limit=rng.randint(100, 999)))
    a2 = add(f"/nf/{amb_a}", base2, dict(gain=rng.randint(10, 99)), pubs=[(atopic, F32)] if pub_first else [], subs=[] if pub_first else [(atopic, F32)])
    b2 = add(f"/nf/{amb_b}", base2, dict(gain=rng.randint(10, 99)), pubs=[] if pub_first else [(atopic, F32)], subs=[(atopic, F32)] if pub_first else [])
    # exact control and absent control
    exact_node = add(f"/nf/{area1}", take(), dict(gain=rng.randint(10, 99)))
    abs_node = take()
    add(f"/nf/{abs_area}", abs_node, dict(rate=rng.randint(100, 999)))
    for _ in range(3):  # fillers
        add(f"/nf/misc", take(), dict(gain=rng.randint(10, 99)))
    by = {n["fqn"]: n for n in nodes}
    fast, publisher2 = (a1 if fast_first else b1), (a2 if pub_first else b2)
    g = lambda fqn: by[fqn]["params"]["gain"]
    tasks = [
        dict(id="nf_single_1", template="single_name", floor=2, request=f"Topic {s1} is published by exactly one node. Find it. Return JSON with the key node (the full name of the node that publishes {s1}).",
             answer=dict(node=p1), support=[["text", p1]], route_tools=["ros2_topic_info"]),
        dict(id="nf_single_2", template="single_name", floor=2, request=f"Topic {s2} has exactly one subscriber. Find it. Return JSON with the key node (the full name of the node that subscribes to {s2}).",
             answer=dict(node=q2), support=[["text", q2]], route_tools=["ros2_topic_info"]),
        dict(id="nf_multi_1", template="multi_name", floor=3,
             request=f"Topic {m1} has exactly three subscribers. Return JSON with the key gains: an object whose keys are the full names of those three nodes and whose values are their integer parameter gain.",
             answer=dict(gains={n: g(n) for n in subs3}), support=[["text", n] for n in subs3] + [["param", n, "gain", g(n)] for n in subs3], route_tools=["ros2_topic_info", "ros2_param_get"]),
        dict(id="nf_multi_2", template="multi_name", floor=3,
             request=f"Node {r} subscribes to exactly two topics. Return JSON with the key upstream: an object whose keys are the full names of those two topics and whose values are the full names of the nodes that publish them.",
             answer=dict(upstream={u1: v1, u2: v2}), support=[["text", u1], ["text", u2], ["text", v1], ["text", v2]], route_tools=["ros2_node_info", "ros2_topic_info"]),
        dict(id="nf_amb_1", template="ambiguous", floor=3,
             request=f"Two nodes named '{base1}' are running, in different namespaces. Find the one whose string parameter mode is 'fast'. Return JSON with keys node (its full name) and limit (its integer parameter limit).",
             answer=dict(node=fast, limit=by[fast]["params"]["limit"]), support=[["text", fast], ["param", fast, "mode", "fast"], ["param", fast, "limit", by[fast]["params"]["limit"]]],
             route_tools=["ros2_node_list", "ros2_param_get"]),
        dict(id="nf_amb_2", template="ambiguous", floor=3,
             request=f"Two nodes named '{base2}' are running, in different namespaces. Topic {atopic} is published by exactly one of them. Return JSON with keys node (the full name of the one that publishes that topic) and gain (its integer parameter gain).",
             answer=dict(node=publisher2, gain=g(publisher2)), support=[["text", publisher2], ["param", publisher2, "gain", g(publisher2)]], route_tools=["ros2_topic_info", "ros2_param_get"]),
        dict(id="nf_exact", template="exact", floor=2,
             request=f"Node {exact_node} has an integer parameter gain. Read it. Return JSON with keys node (exactly as given here) and gain (the integer).",
             answer=dict(node=exact_node, gain=g(exact_node)), support=[["param", exact_node, "gain", g(exact_node)]], route_tools=["ros2_param_get"]),
        dict(id="nf_absent", template="absent", floor=2,
             request=f"Is the node /{abs_area}/{abs_node} running? If it is, return JSON with keys node, running (true) and rate (its integer parameter rate). If it is not running, return JSON with keys node (the name you checked, exactly as given) and running (false).",
             answer=dict(node=f"/{abs_area}/{abs_node}", running=False), support=[["absent", f"/{abs_area}/{abs_node}"]], route_tools=["ros2_node_list"]),
    ]
    return dict(namespace="/nf", seed=SEED, nodes=nodes), tasks


if __name__ == "__main__":
    graph, tasks = build()
    (HERE / "namefix_graph.json").write_text(json.dumps(graph, indent=1))
    (HERE / "namefix_tasks.json").write_text(json.dumps(tasks, indent=1))
    print(len(graph["nodes"]), "nodes")
    for t in tasks:
        print(t["id"], "floor", t["floor"], json.dumps(t["answer"]))
