"""Cause attribution of above-floor requests, implementing WASTE_BY_CAUSE_RULES.md (frozen before computing). No model, no ROS. Writes by_cause.json."""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "small_model_harness_20261115"))
import scorer_v2 as v2, view, harness
resc = {x["run_id"]: x for x in json.loads((HERE / "rescore_v2.json").read_text())}
rows = [json.loads(l) for l in (view.PILOT / "RESULTS_LOG.jsonl").read_text().splitlines()]
rows = [r for r in rows if r["run_id"] not in view.EXC and resc[r["run_id"]]["new"]]
CAUSES = ["a", "b", "c", "d", "e", "f"]
NOTFOUND = re.compile(r"not found|Unable to find", re.I)
REJECT = re.compile(r"^(Invalid arguments|Invalid plan|Tool .* (is not available|failed))|Observation-only study: command rejected")
LISTS = ("ros2_node_list", "ros2_topic_list", "ros2_service_list")
INFO = {"ros2_node_info": "nodes", "ros2_topic_info": "topics", "ros2_service_info": "services"}

def strings(x):
    if isinstance(x, str): return [x] if len(x) >= 2 else []
    if isinstance(x, dict): return [s for v in x.values() for s in strings(v)]
    if isinstance(x, list): return [s for v in x for s in strings(v)]
    return []

def requests_of(events):
    reqs, cur = [], None
    for e in events:
        if e["kind"] == "model_end":
            cur = dict(calls=[dict(name=c["name"], args=c["args"]) for c in e["message"].get("tool_calls", [])], results=[], out=e["message"]["content"]); reqs.append(cur)
        elif e["kind"] == "tool_end" and cur is not None:
            cur["results"].append(e["output"])
    return reqs

def text(r): return r if isinstance(r, str) else json.dumps(r)
VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 1   # 1 = WASTE_BY_CAUSE_RULES.md, 2 = WASTE_BY_CAUSE_RULES_V2.md
def empty_error(res): return isinstance(res, dict) and any(isinstance(v, dict) and v.get("error") == "" for v in res.values())
def is_notfound(res): return bool(NOTFOUND.search(text(res))) or (VERSION == 2 and empty_error(res))

def tag_episode(task, reqs):
    route = harness.route_tools(task) | {"final_answer"}
    req_text = task["request"]
    param_names_later = lambda k: {c["args"].get("param_name") for q in reqs[k + 1:] for c in q["calls"] if c["name"] == "ros2_param_get"}
    tags = {}
    for k, q in enumerate(reqs):
        calls, res = q["calls"], q["results"]
        if not calls or any(c["name"] == "final_answer" for c in calls):
            continue
        earlier = [(c["name"], json.dumps(c["args"], sort_keys=True)) for p in reqs[:k] for c in p["calls"]]
        here = [(c["name"], json.dumps(c["args"], sort_keys=True)) for c in calls]
        # (e)
        if any(REJECT.search(text(r)) for r in res): tags[k] = "e"; continue
        # (d)
        if all(h in earlier for h in here): tags[k] = "d"; continue
        # (b)
        later_args = [s for p in reqs[k + 1:] for c in p["calls"] for s in strings(c["args"])]
        is_b = False
        for c, r in zip(calls, res):
            if is_notfound(r):
                for n in strings(c["args"]):
                    bare = n.lstrip("/")
                    if (not n.startswith("/") or n.startswith("//")) and bare and any(s != n and s.endswith("/" + bare) for s in later_args):
                        is_b = True
        if not is_b and k > 0:  # recovery search directly after a (b) request
            if tags.get(k - 1) == "b" and all(c["name"] in LISTS for c in calls):
                prev_names = {n.lstrip("/") for c, r in zip(reqs[k - 1]["calls"], reqs[k - 1]["results"]) if is_notfound(r) for n in strings(c["args"])}
                if VERSION == 2 or any(n and n in (c["args"].get("pattern") or "") for c in calls for n in prev_names): is_b = True
        if is_b: tags[k] = "b"; continue
        # (c)
        is_c = True
        for c, r in zip(calls, res):
            ok = False
            if c["name"] in LISTS:
                ok = any(p_c["name"] == c["name"] and not p_c["args"].get("pattern") and isinstance(p_r, dict) and "error" not in p_r and not REJECT.search(text(p_r))
                         for p in reqs[:k] for p_c, p_r in zip(p["calls"], p["results"]))
            elif c["name"] == "ros2_param_list":
                later = param_names_later(k)
                ok = bool(later) and all(n and n in req_text for n in later)
            elif c["name"] in INFO:
                key = INFO[c["name"]]; need = c["args"].get(key) or []
                seen = set()
                for p in reqs[:k]:
                    for p_c, p_r in zip(p["calls"], p["results"]):
                        if p_c["name"] == c["name"] and isinstance(p_r, dict):
                            seen |= {n for n in (p_c["args"].get(key) or []) if not (isinstance(p_r.get(n), dict) and "error" in p_r[n])}
                ok = bool(need) and all(n in seen for n in need)
            if not ok: is_c = False
        if is_c: tags[k] = "c"; continue
        off = any(c["name"] not in route for c in calls)
        if VERSION == 2 and off: tags[k] = "f"; continue
        # (a)
        if VERSION == 1:
            if k >= 1 and reqs[k - 1]["calls"]:
                known = req_text + " " + " ".join(s for p in reqs[:k] for c in p["calls"] for s in strings(c["args"])) + " " + " ".join(text(r) for p in reqs[:k - 1] for r in p["results"])
                args = [s for c in calls for s in strings(c["args"])]
                if all(s in known for s in args) and not any(is_notfound(r) for r in res): tags[k] = "a"; continue
        else:
            prev = reqs[k - 1] if k >= 1 else None
            if prev and prev["calls"] and not any(REJECT.search(text(r)) or is_notfound(r) for r in prev["results"]):
                earlier_args = " ".join(s for p in reqs[:k] for c in p["calls"] for s in strings(c["args"]))
                known = req_text + " " + earlier_args + " " + " ".join(text(r) for p in reqs[:k - 1] for r in p["results"])
                prev_res = " ".join(text(r) for r in prev["results"])
                args = [s for c in calls for s in strings(c["args"])]
                known_ok = all(s in known for s in args)
                depends = any(s in prev_res and s not in req_text and s not in " ".join(x for p in reqs[:k - 1] for c in p["calls"] for x in strings(c["args"])) for s in args)
                if known_ok and not depends and not any(is_notfound(r) for r in res): tags[k] = "a"; continue
        # (f)
        empty = any(c["name"] in LISTS and c["args"].get("pattern") and isinstance(r, dict) and not (r.get("nodes") or r.get("topics") or r.get("services")) for c, r in zip(calls, res))
        guess = any(is_notfound(r) for r in res)
        if off or empty or guess: tags[k] = "f"; continue
    return tags

def attribute(excess, tags):
    t = {c: sum(1 for v in tags.values() if v == c) for c in CAUSES}; W = sum(t.values())
    if excess <= 0: return {c: 0.0 for c in CAUSES + ["g"]}, t
    if W <= excess: att = {c: float(t[c]) for c in CAUSES}; att["g"] = float(excess - W)
    else: att = {c: excess * t[c] / W for c in CAUSES}; att["g"] = 0.0
    return att, t

out = []
for r in rows:
    task = view.TASKS[r["task"]]
    reqs = requests_of(v2.s1.read_events(view.REPO / r["trace_path"]))
    tags = tag_episode(task, reqs); excess = len(reqs) - task["floor"]
    att, raw = attribute(excess, tags)
    out.append(dict(run_id=r["run_id"], model=r["model"], arm=r["arm"], task=r["task"], seed=r["seed"], requests=len(reqs), floor=task["floor"], excess=excess,
                    tags={str(k + 1): v for k, v in tags.items()}, raw=raw, attributed=att))
(HERE / f"by_cause_v{VERSION}.json").write_text(json.dumps(out, indent=1))
print(len(out), "episodes;", sum(1 for x in out if x["excess"] <= 0), "with excess <= 0")
