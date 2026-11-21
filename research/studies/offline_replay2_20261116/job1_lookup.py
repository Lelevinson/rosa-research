"""Job 1: name-keyed lookup, offline replay (PROTOCOL.md). uv run python job1_lookup.py
Dead-end trigger: a successful per-entity read of e whose result names no other entity. Action: run the other per-entity read tools over ledger entities
(max 20 runs) and append only the lines that contain e's exact full name. Outputs come from snapshots.json (node_info, param_list) and a cache of recorded results."""
import json
import re
from collections import defaultdict
import common
from common import E, ag, rtokens, PER_ENTITY_TOOLS, KIND_OF_TOOL, LIST_TOOLS

episodes = common.load_episodes()
SNAPSHOTS = json.loads((common.STUDIES / "snapshot_replay_20261115/snapshots.json").read_text())
TOOL_ORDER = [t for t in PER_ENTITY_TOOLS if t != "ros2_param_get"]  # param_get is never run by the lookup (its parameter name is unknown)
TRIGGER_TOOLS = set(PER_ENTITY_TOOLS)
MAX_RUNS = 20

# cache of recorded successful results: (env, tool, entity, other-args) -> text
cache = {}
for ep in episodes:
    for request in ep["requests"]:
        for c in request["calls"]:
            if c["entity"] is not None and c["ok"] and not c["harness_error"] and c["tool"] in PER_ENTITY_TOOLS:
                cache.setdefault((ep["env"], c["tool"], c["entity"], json.dumps(c["args"], sort_keys=True)), c["text"])


def stored_output(env, tool, entity):
    """Text of `tool` on `entity` from the snapshot or the cache, or None (not computable)."""
    snapshot = SNAPSHOTS[env]["B"]
    if tool == "ros2_node_info" and entity in snapshot["node_info"]:
        return snapshot["node_info"][entity]
    if tool == "ros2_param_list" and entity in snapshot["param_list"]:
        return json.dumps(snapshot["param_list"][entity])
    return cache.get((env, tool, entity, "{}"))


def contains_name(line, name):
    return re.search(r"(?<![\w/])" + re.escape(name) + r"(?![\w/])", line) is not None


def edit_distance_at_most_one(a, b):
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    short, long = sorted((a, b), key=len)
    return any(long[:i] + long[i + 1:] == short for i in range(len(long)))


def look_alikes(line, name):
    last = name.rsplit("/", 1)[-1]
    found = []
    for other in ag.names_in_text(line):
        if other != name and (other.rsplit("/", 1)[-1] == last or edit_distance_at_most_one(other.rsplit("/", 1)[-1], last)):
            found.append(other)
    return sorted(set(found))


def firings_of(ep):
    """Dead-end firings with the ledger (names and kinds) as it stood at that call."""
    seen = list(dict.fromkeys(ag.names_in_text(ep["task_text"])))
    kinds, fired, out = {}, set(), []
    for index, call, new in E.ledger_events(ep)[0]:
        if call["ok"] and not call["harness_error"]:
            if call["tool"] in LIST_TOOLS and isinstance(call["output"], dict):
                key, kind = LIST_TOOLS[call["tool"]]
                for n in call["output"].get(key, []):
                    if isinstance(n, str):
                        kinds.setdefault(n, kind)
            if call["entity"] is not None and call["tool"] in KIND_OF_TOOL:
                kinds.setdefault(call["entity"], KIND_OF_TOOL[call["tool"]])
        for n in new:
            if n not in seen:
                seen.append(n)
        if call["tool"] in TRIGGER_TOOLS and call["entity"] is not None and call["ok"] and not call["harness_error"] and call["entity"] not in fired:
            names = ag.names_in_text(call["text"] if isinstance(call["text"], str) else "") - {call["entity"]}
            if not names:
                fired.add(call["entity"])
                out.append(dict(request=index, call=call, ledger=[n for n in seen if n in kinds], kinds=dict(kinds)))
    return out


def lookup(ep, firing):
    e, tool = firing["call"]["entity"], firing["call"]["tool"]
    runs, not_computable, lines, ran_with_lines = 0, 0, [], set()
    for x in firing["ledger"]:
        for other in TOOL_ORDER:
            if other == tool or KIND_OF_TOOL[other] != firing["kinds"][x]:
                continue
            if runs >= MAX_RUNS:
                break
            runs += 1
            text = stored_output(ep["env"], other, x)
            if text is None:
                not_computable += 1
                continue
            kept = [f"{other} of {x}: {line.strip()}" for line in text.replace("\\n", "\n").split("\n") if contains_name(line, e)]
            if kept:
                ran_with_lines.add((other, x))
                lines.extend(kept)
    return dict(runs=runs, not_computable=not_computable, lines=lines, ran_with_lines=ran_with_lines)


def covered_requests(ep, firing, outcome):
    e = firing["call"]["entity"]
    covered = []
    for request in ep["requests"]:
        if request["index"] <= firing["request"] or not request["calls"]:
            continue
        if all(c["tool"] != "final_answer" and c["ok"] and not c["harness_error"] and (c["tool"], c["entity"]) in outcome["ran_with_lines"] and isinstance(c["text"], str) and contains_name(c["text"], e)
               for c in request["calls"]):
            covered.append(request["index"])
    return covered


rows, harm = [], []
for ep in episodes:
    n = len(ep["requests"])
    done = []
    for firing in firings_of(ep):
        outcome = lookup(ep, firing)
        covered = covered_requests(ep, firing, outcome)
        done.append((firing, outcome, covered))
    union = sorted({r for _f, _o, cov in done for r in cov})
    for firing, outcome, covered in done:
        text = "\n".join(outcome["lines"])
        remaining = [r for r in range(firing["request"] + 1, n + 1) if r not in union]
        mates = sorted({m for line in outcome["lines"] for m in look_alikes(line, firing["call"]["entity"])})
        row = dict(run_id=ep["run_id"], model=ep["model"], task=ep["task"], arm=ep["arm"], control_type=ep["control_type"], request=firing["request"], tool=firing["call"]["tool"],
                   entity=firing["call"]["entity"], runs=outcome["runs"], not_computable=outcome["not_computable"], lines=len(outcome["lines"]), covered_requests=len(covered),
                   saved_tokens=sum(rtokens(ep["requests"][r - 1]) for r in covered if r in union), added_tokens=len(text) / 4 * len(remaining), harm=bool(mates), look_alikes=mates)
        rows.append(row)
        if mates:
            harm.append(dict(row, lines_text=outcome["lines"]))
    ep["_union_saved"] = (len(union), sum(rtokens(ep["requests"][r - 1]) for r in union))


def summarize(subset_rows, subset_eps):
    requests = sum(len(e["requests"]) for e in subset_eps)
    saved_requests = sum(e["_union_saved"][0] for e in subset_eps)
    saved_tokens = sum(e["_union_saved"][1] for e in subset_eps)
    added = sum(r["added_tokens"] for r in subset_rows)
    by_task = defaultdict(int)
    for e in subset_eps:
        by_task[e["task"]] += e["_union_saved"][0]
    top = max(by_task.items(), key=lambda kv: kv[1]) if by_task and saved_requests else (None, 0)
    return dict(episodes=len(subset_eps), episodes_with_firing=len({r["run_id"] for r in subset_rows}), firings=len(subset_rows), requests=requests, predicted_saved_requests=saved_requests,
                saved_share=saved_requests / requests if requests else 0, predicted_saved_tokens=saved_tokens, tokens_added=added, lines_added=sum(r["lines"] for r in subset_rows),
                firings_with_lines=sum(r["lines"] > 0 for r in subset_rows), runs=sum(r["runs"] for r in subset_rows), not_computable_runs=sum(r["not_computable"] for r in subset_rows),
                harm_firings=sum(r["harm"] for r in subset_rows), largest_task=top[0], largest_task_share_of_saving=top[1] / saved_requests if saved_requests else None)


def verdict(s):
    ok = s["saved_share"] >= 0.03 and s["tokens_added"] < s["predicted_saved_tokens"] and not (s["largest_task_share_of_saving"] or 0) > 0.6
    return dict(saved_share_ge_3pct=s["saved_share"] >= 0.03, tokens_added_lt_saved=s["tokens_added"] < s["predicted_saved_tokens"],
                carried_by_one_task=(s["largest_task_share_of_saving"] or 0) > 0.6, passes=ok)


result = dict(protocol_sha=open("PROTOCOL.sha256").read().split()[0])
total = summarize(rows, episodes)
result["dead_end"] = dict(total=total, verdict=verdict(total), control_type_only=summarize([r for r in rows if r["control_type"]], [e for e in episodes if e["control_type"]]),
                          per_model={m: summarize([r for r in rows if r["model"] == m], [e for e in episodes if e["model"] == m]) for m in sorted({e["model"] for e in episodes})},
                          per_task={t: summarize([r for r in rows if r["task"] == t], [e for e in episodes if e["task"] == t]) for t in sorted({e["task"] for e in episodes})},
                          firings_per_tool={t: sum(r["tool"] == t for r in rows) for t in sorted({r["tool"] for r in rows})},
                          lines_per_tool={t: sum(r["lines"] for r in rows if r["tool"] == t) for t in sorted({r["tool"] for r in rows})})
v1_episodes = {e["run_id"] for e in json.loads((common.STUDIES / "offline_replay_20261116/results.json").read_text())["episodes"] if e["p1_v1"]["triggers"]}
result["dead_end"]["overlap_with_sweep_v1_episodes"] = dict(firings_in_v1_episodes=sum(r["run_id"] in v1_episodes for r in rows), episodes_with_firing_and_v1=len({r["run_id"] for r in rows} & v1_episodes))
result["dead_end"]["harm_cases"] = harm
result["dead_end"]["rows"] = rows


# ------------------------------------------------------------------ optional start trigger
def start_block(ep, listed):
    words = list(dict.fromkeys(re.findall(r"[A-Za-z0-9_]+", ep["task_text"])))
    full_names = ag.names_in_text(ep["task_text"])
    lines, mapped, not_listed = [], set(), set()
    bare_failed = {c["entity"] for r in ep["requests"] for c in r["calls"] if c["entity"] is not None and not c["ok"] and not c["entity"].startswith("/")}
    for word in words:
        matches = [(n, k) for n, k in listed if n.rsplit("/", 1)[-1] == word]
        if matches:
            mapped.add(word)
            lines.append(f"{word} -> " + ", ".join(f"{n} ({k})" for n, k in matches))
        elif word in bare_failed:
            not_listed.add(word)
            lines.append(f"{word} -> not listed")
    for n in full_names:
        for name, kind in listed:
            if name == n:
                mapped.add(n)
                lines.append(f"{n} -> {n} ({kind})")
    return lines, mapped, not_listed


start_rows = []
for ep in episodes:
    snapshot = SNAPSHOTS[ep["env"]]["A"]
    listed = [(n, kind) for key, kind in (("node_list", "node"), ("topic_list", "topic"), ("service_list", "service")) for n in snapshot[key][key.replace("_list", "s")]]
    lines, mapped, not_listed = start_block(ep, listed)
    n = len(ep["requests"])
    covered = []
    for request in ep["requests"]:
        if not request["calls"]:
            continue
        def call_covered(c):
            if c["tool"] in LIST_TOOLS:
                pattern = c["args"].get("pattern")
                return bool(pattern) and any(w in str(pattern) for w in mapped)
            return c["entity"] is not None and not c["ok"] and c["entity"] in (mapped | not_listed)
        if all(c["tool"] != "final_answer" and call_covered(c) for c in request["calls"]):
            covered.append(request["index"])
    block_tokens = len("\n".join(lines)) / 4
    start_rows.append(dict(run_id=ep["run_id"], model=ep["model"], task=ep["task"], arm=ep["arm"], control_type=ep["control_type"], block_lines=len(lines), block_tokens=block_tokens,
                           requests=n, covered_requests=len(covered), saved_tokens=sum(rtokens(ep["requests"][r - 1]) for r in covered), added_tokens=block_tokens * (n - len(covered)) if lines else 0))


def start_summary(subset):
    requests, saved = sum(r["requests"] for r in subset), sum(r["covered_requests"] for r in subset)
    by_task = defaultdict(int)
    for r in subset:
        by_task[r["task"]] += r["covered_requests"]
    top = max(by_task.items(), key=lambda kv: kv[1]) if saved else (None, 0)
    s = dict(episodes=len(subset), episodes_with_block=sum(r["block_lines"] > 0 for r in subset), requests=requests, predicted_saved_requests=saved, saved_share=saved / requests if requests else 0,
             predicted_saved_tokens=sum(r["saved_tokens"] for r in subset), tokens_added=sum(r["added_tokens"] for r in subset), largest_task=top[0], largest_task_share_of_saving=top[1] / saved if saved else None)
    s.update(verdict(s))
    return s


result["start_block"] = dict(total=start_summary(start_rows), control_type_only=start_summary([r for r in start_rows if r["control_type"]]),
                             per_model={m: start_summary([r for r in start_rows if r["model"] == m]) for m in sorted({e["model"] for e in episodes})},
                             per_task={t: start_summary([r for r in start_rows if r["task"] == t]) for t in sorted({e["task"] for e in episodes})})
json.dump(result, open("results_job1.json", "w"), indent=1, default=str)
print(json.dumps(dict(dead_end=result["dead_end"]["total"], verdict=result["dead_end"]["verdict"], per_tool=result["dead_end"]["firings_per_tool"], overlap=result["dead_end"]["overlap_with_sweep_v1_episodes"],
                      harm=len(harm), start=result["start_block"]["total"]), indent=1, default=str))
