"""Stage 2a: offline replay of learned speculative result expansion (frozen by PROTOCOL_STAGE2A.md).

No inference, no ROS, no fixture. Reads recorded traces only.
  python3 replay_stage2a.py <repo_root> <out_dir>
Writes replay_stage2a.json (every number) ; tables are produced by summarize_stage2a.py.
"""
import ast
import collections
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from extract_requests import FROZEN, extract_episode  # noqa: E402
from label_requests import TOKEN, assembled_names, normalise, parse_args, string_leaves, NOISE_TOOLS  # noqa: E402

RUNS = "research/_artifacts/runs/headroom_diagnostic_20261112"
FIELD_ORDER = ["node_list.nodes", "topic_list.topics", "service_list.services", "node_info.publishers",
               "node_info.subscribers", "node_info.service_servers", "node_info.service_clients",
               "topic_info.endpoint_nodes", "param_list.params"]
TAUS = (0.5, 0.7, 0.9)
TASKS = ("t1", "t2", "t3", "d1", "d2", "x1")
SECTION = {"Subscribers": "subscribers", "Publishers": "publishers", "Service Servers": "service_servers", "Service Clients": "service_clients"}


# ------------------------------------------------------------------ loading
def parse_result(raw):
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return raw


def normalise_args(args):
    return {k: v for k, v in args.items() if v is not None}


def build_episode(info, requests, task_text):
    reqs = []
    for r in requests:
        calls = []
        for c in r["calls"]:
            calls.append(dict(name=c["name"], args=normalise_args(parse_args(c["args"])), obj=parse_result(c["result"]),
                              text=normalise(c["result"]), ok=not re.search(r"error|Unable to find|Node not found|not found", c["result"] or "", re.I)))
        reqs.append(dict(index=r["request_index"], calls=calls, input_tokens=r["input_tokens"] or 0, line=r["trace_line"]))
    return dict(task=info["task"], arm=info["arm"], model=info["model"], episode=info["episode"], text=task_text, requests=reqs)


def load_all(repo_root):
    tasks = {t["id"]: t["request"] for t in json.loads((HERE / "vendor/baseline_protocol.json").read_text())["tasks"]}
    training, evaluation = [], {"qwen": [], "luna": []}
    frozen = json.loads((repo_root / FROZEN / "INPUTS_FROZEN.json").read_text())
    for entry in frozen["traces"]:
        if entry["corpus"] == "baseline":
            info, requests = extract_episode(entry, repo_root)
            training.append(build_episode(info, requests, entry["request"]))
    base = repo_root / RUNS
    for run in sorted(p for p in base.glob("stage1[ac]_*") if p.is_dir() and "combined" not in p.name):
        scores = json.loads((run / "scores_1a.json").read_text())
        for row in scores["episodes"]:
            entry = {"copy": str(run / row["episode"] / "trace.jsonl"), "corpus": "stage", "episode": row["episode"], "task": row["task"]}
            info, requests = extract_episode(entry, repo_root)
            info["model"] = "luna" if "stage1c" in run.name else "qwen"
            episode = build_episode(info, requests, tasks[row["task"]])
            training.append(episode)
            if row["arm"] == "A0":
                evaluation[info["model"]].append(episode)
    return training, evaluation


# ------------------------------------------------------------------ result fields
def fields_of(call):
    """Generic parsers of ROS CLI result text; values keep order."""
    out = collections.defaultdict(list)
    obj, name = call["obj"], call["name"]
    if not call["ok"] or not isinstance(obj, dict):
        return out
    if name == "ros2_node_list":
        out["node_list.nodes"] += list(obj.get("nodes", []))
    elif name == "ros2_topic_list":
        out["topic_list.topics"] += list(obj.get("topics", []))
    elif name == "ros2_service_list":
        out["service_list.services"] += list(obj.get("services", []))
    elif name == "ros2_node_info":
        for text in obj.values():
            if not isinstance(text, str):
                continue
            section = None
            for line in text.splitlines():
                header = re.match(r"^  ([A-Za-z ]+):\s*$", line)
                if header:
                    section = SECTION.get(header.group(1))
                    continue
                item = re.match(r"^    (\S+): ", line)
                if item and section:
                    out["node_info." + section].append(item.group(1))
    elif name == "ros2_topic_info":
        for text in obj.values():
            if isinstance(text, str):
                out["topic_info.endpoint_nodes"] += sorted(assembled_names(text))
    elif name == "ros2_param_list":
        for names in obj.values():
            if isinstance(names, list):
                out["param_list.params"] += [n.strip() for n in names]
    return out


def as_set(value):
    return set(value) if isinstance(value, list) else {value}


# ------------------------------------------------------------------ candidates and signatures
def availability(episode, upto):
    """first_available[token] = 0 (task text) or the index of the first request whose results contain it; env = tokens from results."""
    first = {t: 0 for t in TOKEN.findall(episode["text"])}
    env = set()
    for r in episode["requests"][:upto]:
        for c in r["calls"]:
            tokens = set(TOKEN.findall(c["text"])) | assembled_names(c["text"])
            env |= tokens
            for t in tokens:
                first.setdefault(t, r["index"])
    return first, env


def candidates(episode, k):
    """Calls of request k+1 that are candidates: info tool, args derivable only after request k."""
    nxt = episode["requests"][k]  # request index k+1 (0-based list)
    first, _ = availability(episode, k)
    out = []
    for call in nxt["calls"]:
        if call["name"] in NOISE_TOOLS or not call["args"]:
            out.append(False)
            continue
        leaves = [x for x in string_leaves(call["args"]) if x != "use_sim_time"]
        if any(x not in first for x in leaves) or not leaves:
            out.append(False)
            continue
        out.append(max(first[x] for x in leaves) == k)
    return out


def signature(episode, k, t_call, call):
    """Binding signature of candidate `call` against tool-call `t_call` of request k, or None if not speculable."""
    fields = fields_of(t_call)
    _, env = availability(episode, k)
    carried = {x for x in string_leaves(t_call["args"])}
    sig, bound = [], 0
    for arg, value in sorted(call["args"].items()):
        if isinstance(value, (int, float, bool)):
            sig.append((arg, "const:" + repr(value)))
            continue
        strings = as_set(value)
        if not all(isinstance(s, str) for s in strings):
            return None
        for field in FIELD_ORDER:
            if strings <= set(fields.get(field, [])):
                sig.append((arg, "field:" + field))
                bound += 1
                break
        else:
            if strings <= carried:
                carried_arg = next(a for a, v in t_call["args"].items() if strings <= as_set(v))
                sig.append((arg, "carry:" + carried_arg))
            elif not (strings & env):
                sig.append((arg, "const:" + json.dumps(sorted(strings) if isinstance(value, list) else value)))
            else:
                return None  # an environment entity the framework cannot supply
    if bound != 1:
        return None
    return tuple(sig)


def pairs_of_episode(episode):
    """Yield (k, tool t, (t', signature)) for every candidate follow-up pair; also (k, t, None) for occurrences."""
    n = len(episode["requests"])
    for k in range(1, n):
        cand = candidates(episode, k)
        calls_k = episode["requests"][k - 1]["calls"]
        seen_tools = {c["name"] for c in calls_k}
        found = collections.defaultdict(set)
        for t_call in calls_k:
            for call, is_cand in zip(episode["requests"][k]["calls"], cand):
                if is_cand:
                    sig = signature(episode, k, t_call, call)
                    if sig:
                        found[t_call["name"]].add((call["name"], sig))
        for t in seen_tools:
            yield k, t, found.get(t, set())


def train(episodes):
    occurrences, pair_counts = collections.Counter(), collections.Counter()
    sizes = collections.defaultdict(list)
    for e in episodes:
        for k, t, pairs in pairs_of_episode(e):
            occurrences[t] += 1
            for p in pairs:
                pair_counts[(t, p)] += 1
        for r in e["requests"]:
            for c in r["calls"]:
                list_args = [v for v in c["args"].values() if isinstance(v, list)]
                units = max(1, len(list_args[0])) if list_args else 1
                sizes[c["name"]].append(len(c["text"]) / units)
    return occurrences, pair_counts, {t: statistics.median(v) for t, v in sizes.items()}


# ------------------------------------------------------------------ speculation and evaluation
def speculate(episode, k, selected):
    """selected: dict tool -> list of (t', sig). Returns list of specs (tool, fixed args, bound arg, values)."""
    specs = []
    for t_call in episode["requests"][k - 1]["calls"]:
        fields = fields_of(t_call)
        for t2, sig in selected.get(t_call["name"], []):
            fixed, bound_arg, values, ok = {}, None, [], True
            for arg, how in sig:
                kind, _, rest = how.partition(":")
                if kind == "field":
                    bound_arg, values = arg, list(dict.fromkeys(fields.get(rest, [])))
                elif kind == "carry":
                    fixed[arg] = t_call["args"].get(rest)
                else:
                    fixed[arg] = json.loads(rest) if rest.startswith(("[", '"')) else ast.literal_eval(rest)
            if bound_arg and values and ok:
                specs.append((t2, fixed, bound_arg, values))
    return specs


def covered(call, specs):
    for tool, fixed, bound_arg, values in specs:
        if call["name"] != tool or bound_arg not in call["args"]:
            continue
        if all(call["args"].get(a) == v for a, v in fixed.items()) and as_set(call["args"][bound_arg]) <= set(values):
            return True
    return False


def unit_keys(specs):
    return {(t, tuple(sorted((a, json.dumps(v)) for a, v in fixed.items())), bound, v) for t, fixed, bound, values in specs for v in values}


def used_units(call, specs):
    used = set()
    for tool, fixed, bound_arg, values in specs:
        if call["name"] == tool and bound_arg in call["args"] and all(call["args"].get(a) == v for a, v in fixed.items()):
            for v in as_set(call["args"][bound_arg]):
                if v in values:
                    used.add((tool, tuple(sorted((a, json.dumps(x)) for a, x in fixed.items())), bound_arg, v))
    return used


def evaluate(episode, selector, sizes):
    """selector(k) -> specs for the speculation fired after actual request k; None = oracle."""
    n = len(episode["requests"])
    removable, partial, fired = {}, {}, {}
    for j in range(2, n):  # request j (1-based), never the final request n
        cand = candidates(episode, j - 1)
        calls = episode["requests"][j - 1]["calls"]
        allcand = bool(calls) and all(cand)
        if selector is None:
            removable[j] = allcand
            partial[j] = False
            continue
        specs = selector(j - 1)
        cov = [covered(c, specs) for c in calls]
        removable[j] = allcand and all(cov)
        partial[j] = any(cov) and not removable[j]
    # speculation cost along the primary (non-chained) trajectory
    removed = {}
    prev_removed = False
    for j in range(2, n):
        removed[j] = removable[j] and not prev_removed
        prev_removed = removed[j]
    chained = {j: removable[j] for j in range(2, n)}
    cost = dict(units=0, used=0, extra_native=0, extra_tokens=0.0)
    if selector is not None:
        k = 1
        while k < n:
            if k >= 2 and removed.get(k):
                k += 1
                continue
            specs = selector(k)
            if specs:
                keys = unit_keys(specs)
                nxt_calls = episode["requests"][k]["calls"]
                used = set()
                for c in nxt_calls:
                    used |= used_units(c, specs)
                unused = keys - used
                cost["units"] += len(keys)
                cost["used"] += len(used)
                cost["extra_native"] += len(unused)
                for (t, _, _, _) in unused:
                    cost["extra_tokens"] += sizes.get(t, 600) / 4 * (n - k)
            k += 1
    saved_tokens = sum(episode["requests"][j - 1]["input_tokens"] for j, v in removed.items() if v)
    return dict(n=n, removable_candidates=sum(removable.values()), removed=sum(removed.values()), removed_chained=sum(chained.values()),
                removed_requests=[j for j, v in removed.items() if v], partial=sum(partial.values()),
                candidate_requests=sum(1 for j in range(2, n) if any(candidates(episode, j - 1))),
                saved_input_tokens=saved_tokens, **cost)


def main():
    repo_root, out_dir = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    training, evaluation = load_all(repo_root)
    results = {"training_episodes": len(training), "evaluation": {m: len(v) for m, v in evaluation.items()}, "rows": []}
    for task in TASKS:
        train_set = [e for e in training if e["task"] != task and not (task == "d1" and e["task"] == "d1_recovery")]
        occ, pairs, sizes = train(train_set)
        top1 = {}
        for (t, p), n in sorted(pairs.items(), key=lambda kv: (-kv[1], str(kv[0]))):
            top1.setdefault(t, []).append((p, n))
        top1 = {t: [v[0][0]] for t, v in top1.items()}
        learned = {tau: {} for tau in TAUS}
        for (t, p), n in pairs.items():
            for tau in TAUS:
                if n / occ[t] >= tau:
                    learned[tau].setdefault(t, []).append(p)
        results.setdefault("pairs", {})[task] = {f"{t}|{p}": [n, occ[t]] for (t, p), n in sorted(pairs.items(), key=lambda kv: -kv[1])[:12]}
        for model, episodes in evaluation.items():
            for e in [x for x in episodes if x["task"] == task]:
                row = dict(task=task, model=model, episode=e["episode"], requests=len(e["requests"]))
                row["oracle"] = evaluate(e, None, sizes)
                row["static_top1"] = evaluate(e, lambda k, e=e: speculate(e, k, {t: [p[1:] if False else (p[0], p[1])] for t, ps in top1.items() for p in ps}), sizes)
                for tau in TAUS:
                    sel = {t: [(p[0], p[1]) for p in ps] for t, ps in learned[tau].items()}
                    row[f"tau{tau}"] = evaluate(e, lambda k, e=e, sel=sel: speculate(e, k, sel), sizes)
                results["rows"].append(row)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "replay_stage2a.json").write_text(json.dumps(results, indent=1, default=str))
    print("wrote", out_dir / "replay_stage2a.json", len(results["rows"]), "episode rows")


if __name__ == "__main__":
    main()
