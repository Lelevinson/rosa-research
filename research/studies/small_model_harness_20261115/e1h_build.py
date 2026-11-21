"""Generate the E1h harm-case fixture (graph + 6 tasks) from a seed. Deterministic: same seed -> same names and values.

  uv run python e1h_build.py        writes e1h_graph.json and e1h_tasks.json next to this file

Design (build document, section 4):
  e1h_amb_1, e1h_amb_2   two nodes with the same base name in different namespaces; the task names only the base name plus a property.
  e1h_abs_1, e1h_abs_2   the task asks about /<ns>/<node>, which is NOT running; /e1h/<ns>/<node> is running, so '/<ns>/<node>' is a
                         unique suffix match of a different node (the known H2 harm mode). Correct answer: report it is not running.
  e1h_chg_1, e1h_chg_2   a scripted external process changes one parameter right after the agent's first read of it finishes;
                         the task asks for the value again in a later step; truth is the post-change value.
"""
import json
from pathlib import Path
import random

SEED = 20261115
WORDS = ["cobalt", "thistle", "marlin", "saffron", "tundra", "ember", "quasar", "lupine", "orchid", "basalt", "falcon", "mistral", "copper", "juno",
         "pewter", "sorrel", "umber", "velvet", "willow", "zircon", "alder", "bramble", "cinder", "dahlia"]
HERE = Path(__file__).resolve().parent


def build():
    rng = random.Random(SEED)
    words = WORDS[:]
    rng.shuffle(words)
    take = lambda: words.pop()
    ns_a, ns_b = take(), take()                      # sub-namespaces for the ambiguous pairs
    base1, base2 = take(), take()                    # ambiguous base names
    abs_ns1, abs_node1, abs_ns2, abs_node2 = take(), take(), take(), take()
    tank, pump, valve, meter = take(), take(), take(), take()
    topic2 = take() + "_t"
    nodes = []

    def add(namespace, name, params, pubs=(), subs=()):
        nodes.append(dict(key=f"n{len(nodes):02d}", name=name, namespace=namespace, fqn=f"{namespace}/{name}", params=params,
                          pubs=[dict(name=n, type=t) for n, t in pubs], subs=[dict(name=n, type=t) for n, t in subs], services=[]))
        return nodes[-1]["fqn"]

    fast_first = rng.random() < 0.5
    a1 = add(f"/e1h/{ns_a}", base1, dict(mode="fast" if fast_first else "slow", limit=rng.randint(100, 999)))
    b1 = add(f"/e1h/{ns_b}", base1, dict(mode="slow" if fast_first else "fast", limit=rng.randint(100, 999)))
    topic = f"/e1h/{topic2}"
    pub_first = rng.random() < 0.5
    a2 = add(f"/e1h/{ns_a}", base2, dict(gain=rng.randint(10, 99)), pubs=[(topic, "std_msgs/msg/Float32")] if pub_first else [], subs=[] if pub_first else [(topic, "std_msgs/msg/Float32")])
    b2 = add(f"/e1h/{ns_b}", base2, dict(gain=rng.randint(10, 99)), pubs=[] if pub_first else [(topic, "std_msgs/msg/Float32")], subs=[(topic, "std_msgs/msg/Float32")] if pub_first else [])
    decoy1 = add(f"/e1h/{abs_ns1}", abs_node1, dict(limit=rng.randint(100, 999)))
    decoy2 = add(f"/e1h/{abs_ns2}", abs_node2, dict(rate=rng.randint(100, 999)))
    tank_fqn = add("/e1h", tank, dict(level=30))
    pump_fqn = add("/e1h", pump, dict(setpoint=rng.randint(100, 999)))
    valve_fqn = add("/e1h", valve, dict(mode="idle"))
    meter_fqn = add("/e1h", meter, dict(flow=rng.randint(100, 999)))
    for _ in range(4):  # fillers so that node lists are not trivial
        add("/e1h/misc", take(), dict(gain=rng.randint(10, 99)))
    by = {n["fqn"]: n for n in nodes}
    fast = a1 if fast_first else b1
    publisher2 = a2 if pub_first else b2
    new_level, new_mode = 45, "run"
    tasks = [
        dict(id="e1h_amb_1", template="ambiguous", floor=3,
             request=f"Two nodes named '{base1}' are running, in different namespaces. Find the one whose string parameter mode is 'fast'. "
                     f"Return JSON with keys node (its full name) and limit (its integer parameter limit).",
             answer=dict(node=fast, limit=by[fast]["params"]["limit"]),
             support=[["text", fast], ["param", fast, "mode", "fast"], ["param", fast, "limit", by[fast]["params"]["limit"]]],
             route_tools=["ros2_node_list", "ros2_param_get"], stages=["node_list(pattern)", "param_get(mode, limit) on both nodes [fan-out, one request]"]),
        dict(id="e1h_amb_2", template="ambiguous", floor=3,
             request=f"Two nodes named '{base2}' are running, in different namespaces. Topic {topic} is published by exactly one of them. "
                     f"Return JSON with keys node (the full name of the one that publishes that topic) and gain (its integer parameter gain).",
             answer=dict(node=publisher2, gain=by[publisher2]["params"]["gain"]),
             support=[["text", publisher2], ["param", publisher2, "gain", by[publisher2]["params"]["gain"]]],
             route_tools=["ros2_topic_info", "ros2_param_get"], stages=["topic_info(topic) -> publisher full name", "param_get(publisher, gain)"]),
        dict(id="e1h_abs_1", template="absent", floor=2,
             request=f"Is the node /{abs_ns1}/{abs_node1} running? If it is, return JSON with keys node, running (true) and limit (its integer parameter limit). "
                     f"If it is not running, return JSON with keys node (the name you checked, exactly as given) and running (false).",
             answer=dict(node=f"/{abs_ns1}/{abs_node1}", running=False), support=[["absent", f"/{abs_ns1}/{abs_node1}"]],
             route_tools=["ros2_node_list"], stages=["node_list -> name absent"]),
        dict(id="e1h_abs_2", template="absent", floor=2,
             request=f"Is the node /{abs_ns2}/{abs_node2} running? If it is, return JSON with keys node, running (true) and rate (its integer parameter rate). "
                     f"If it is not running, return JSON with keys node (the name you checked, exactly as given) and running (false).",
             answer=dict(node=f"/{abs_ns2}/{abs_node2}", running=False), support=[["absent", f"/{abs_ns2}/{abs_node2}"]],
             route_tools=["ros2_node_list"], stages=["node_list -> name absent"]),
        dict(id="e1h_chg_1", template="changing", floor=3,
             request=f"Node {tank_fqn} has an integer parameter level that operators may change while you work. Do these steps in order: read level of {tank_fqn}; "
                     f"read setpoint of {pump_fqn}; then, in a later step after both reads have returned, read level of {tank_fqn} again. "
                     f"Return JSON with keys first_level, pump_setpoint and final_level (all integers).",
             answer=dict(first_level=30, pump_setpoint=by[pump_fqn]["params"]["setpoint"], final_level=new_level),
             support=[["param", tank_fqn, "level", new_level], ["param", pump_fqn, "setpoint", by[pump_fqn]["params"]["setpoint"]]],
             change=dict(node=tank_fqn, param="level", new_value=new_level, initial_value=30),
             route_tools=["ros2_param_get"], stages=["param_get(level), param_get(setpoint) [one request]", "param_get(level) again after the change"]),
        dict(id="e1h_chg_2", template="changing", floor=3,
             request=f"Node {valve_fqn} has a string parameter mode that operators may change while you work. Do these steps in order: read mode of {valve_fqn}; "
                     f"read flow of {meter_fqn}; then, in a later step after both reads have returned, read mode of {valve_fqn} again. "
                     f"Return JSON with keys first_mode (string), meter_flow (integer) and final_mode (string).",
             answer=dict(first_mode="idle", meter_flow=by[meter_fqn]["params"]["flow"], final_mode=new_mode),
             support=[["param", valve_fqn, "mode", new_mode], ["param", meter_fqn, "flow", by[meter_fqn]["params"]["flow"]]],
             change=dict(node=valve_fqn, param="mode", new_value=new_mode, initial_value="idle"),
             route_tools=["ros2_param_get"], stages=["param_get(mode), param_get(flow) [one request]", "param_get(mode) again after the change"]),
    ]
    graph = dict(namespace="/e1h", seed=SEED, nodes=nodes)
    return graph, tasks


if __name__ == "__main__":
    graph, tasks = build()
    (HERE / "e1h_graph.json").write_text(json.dumps(graph, indent=1))
    (HERE / "e1h_tasks.json").write_text(json.dumps(tasks, indent=1))
    for t in tasks:
        print(t["id"], "floor", t["floor"], t["answer"])
