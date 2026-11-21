"""Offline replay of the three proposals (protocol: PROTOCOL.md, frozen before this file computed anything).  uv run python replay.py   -> results.json
Reads only recorded traces; no model, no ROS, no ground truth in any rule (the scorer is used only to judge rewritten answers afterwards)."""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import episodes as E  # noqa: E402

ag = E.ag
SMALL_GROUP_MAX = 4          # V2 threshold, fixed in PROTOCOL.md
MAX_SWEEP = 20
SWEEP_TOKEN_BUDGET = 3000
tasks = E.load_tasks()
eps = [E.parse(g, r, tasks) for g, r in E.run_rows()]
rtoks = lambda r: r["input_tokens"] + r["output_tokens"]
argkey = lambda c: json.dumps(c["args"], sort_keys=True)

# estimated result size (tokens) per tool: median chars of recorded successful single-entity results / 4
sizes = defaultdict(list)
for ep in eps:
    for r in ep["requests"]:
        for c in r["calls"]:
            if c["entity"] is not None and c["ok"] and not c["harness_error"]:
                sizes[c["tool"]].append(len(c["text"]))
est = {t: statistics.median(v) / 4 for t, v in sizes.items()}


# ------------------------------------------------------------------ proposal 1
def earlier_groups(ep, before_request):
    groups = []
    for r in ep["requests"]:
        if r["index"] >= before_request:
            break
        for u in r["units"]:
            if u["ok"] and not u["harness_error"] and u["tool"] != "final_answer":
                groups.extend(E.groups_of(u["output"], u["text"]))
    return groups


def sweep_set(group, exclude, tool):
    names, cost = [], 0.0
    for n in group:
        if n in exclude:
            continue
        step = est.get(tool, 500)
        if len(names) >= MAX_SWEEP or cost + step > SWEEP_TOKEN_BUDGET:
            break
        names.append(n)
        cost += step
    return names


def proposal1(ep, variant):
    calls = [c for r in ep["requests"] for c in r["calls"] if c["entity"] is not None and c["tool"] != "final_answer"]
    queried = defaultdict(set)      # (tool, argkey) -> entities queried so far
    covered = defaultdict(set)      # (tool, argkey) -> entities covered by a sweep
    triggers, saved_requests = [], set()
    by_request = defaultdict(list)
    for c in calls:
        by_request[c["request"]].append(c)
    for k in sorted(by_request):
        for c in by_request[k]:
            key = (c["tool"], argkey(c))
            fired_for = None
            if c["entity"] in covered[key] or c["entity"] in queried[key]:
                pass
            elif variant == "V1":
                for p in by_request.get(k - 1, []):
                    if p["tool"] == c["tool"] and argkey(p) == argkey(c) and p["entity"] != c["entity"]:
                        common = [g for g in earlier_groups(ep, k - 1) if p["entity"] in g and c["entity"] in g]
                        if common:
                            fired_for = (min(common, key=len), {p["entity"], c["entity"]})
                            break
            else:
                small = [g for g in earlier_groups(ep, k) if c["entity"] in g and 2 <= len(g) <= SMALL_GROUP_MAX]
                if small:
                    fired_for = (min(small, key=len), {c["entity"]})
            queried[key].add(c["entity"])
            if fired_for:
                group, called = fired_for
                names = sweep_set(group, called | queried[key] | covered[key], c["tool"])
                if names:
                    covered[key] |= set(names)
                    triggers.append(dict(request=k, tool=c["tool"], group_size=len(group), sweep=names))
                    trig_req, trig_key = k, key
                    # requests after k fully covered by this sweep / earlier coverage
                    for r in ep["requests"]:
                        if r["index"] > k and r["index"] not in saved_requests and r["calls"]:
                            if all(x["tool"] != "final_answer" and x["entity"] is not None and (x["tool"], argkey(x)) == trig_key
                                   and (x["entity"] in covered[trig_key] or x["entity"] in queried[trig_key]) for x in r["calls"]):
                                saved_requests.add(r["index"])
    later_queried = defaultdict(set)
    for c in calls:
        later_queried[(c["tool"], argkey(c))].add((c["request"], c["entity"]))
    extra_tokens = extra_execs = 0.0
    for t in triggers:
        key_tool = t["tool"]
        remaining = sum(1 for r in ep["requests"] if r["index"] > t["request"] and r["index"] not in saved_requests)
        for n in t["sweep"]:
            needed = any(e == n and rq > t["request"] for (rq, e) in
                         [x for kk, v in later_queried.items() if kk[0] == key_tool for x in v])
            if not needed:
                extra_tokens += est.get(key_tool, 500) * remaining
                extra_execs += 1
    saved_tokens = sum(rtoks(r) for r in ep["requests"] if r["index"] in saved_requests)
    return dict(triggers=len(triggers), group_sizes=[t["group_size"] for t in triggers], sweep_sizes=[len(t["sweep"]) for t in triggers],
                requests_after_trigger=sum(1 for t in triggers[:1] for r in ep["requests"] if r["index"] > t["request"]),
                saved_requests=len(saved_requests), saved_tokens=saved_tokens, extra_tokens=extra_tokens, extra_executions=extra_execs)


# ------------------------------------------------------------------ proposal 2
def is_empty_or_not_found(u):
    out = u["output"]
    if isinstance(out, dict) and out and all(v in ([], {}, None, "") for v in out.values()):
        return True
    if isinstance(out, dict) and not out:
        return True
    return bool(E.NOT_FOUND.search(u["text"])) or (isinstance(out, dict) and "error" in out)


def proposal2(ep):
    seen_results, seen_with_args, seen_values = set(), set(), defaultdict(set)
    ledger = set(ag.names_in_text(ep["task_text"]))
    counter = defaultdict(int)
    stalls = {"a": [], "a2": [], "b": []}
    stall_by_tool = defaultdict(list)       # tool -> [(request, rule)]
    useful_next = []
    for r in ep["requests"]:
        for u in r["units"]:
            if u["tool"] == "final_answer" or u["harness_error"]:
                continue
            new = set()
            if u["ok"]:
                names = ag.names_in_text(u["text"])
                if isinstance(u["output"], dict) and isinstance(u["output"].get("nodes"), list):
                    names |= {n for n in u["output"]["nodes"] if isinstance(n, str) and ag.ABSOLUTE_NAME.fullmatch(n)}
                new = names - ledger
            rules = []
            if (u["tool"], u["text"]) in seen_results:
                rules.append("a")
            if (u["tool"], json.dumps(u["args"], sort_keys=True), u["text"]) in seen_with_args:
                rules.append("a2")
            if is_empty_or_not_found(u):
                counter[u["tool"]] += 1
                if counter[u["tool"]] >= 2:
                    rules.append("b")
            for rule in rules:
                stalls[rule].append((r["index"], u["tool"]))
            if "a" in rules or "b" in rules:
                stall_by_tool[u["tool"]].append((r["index"], "a" if "a" in rules else "b"))
            seen_results.add((u["tool"], u["text"]))
            seen_with_args.add((u["tool"], json.dumps(u["args"], sort_keys=True), u["text"]))
            if new:
                counter.clear()
                ledger |= new
    first = second = None
    hide_total = hide_useful = 0
    first_req = [v[0][0] for v in stall_by_tool.values()]
    second_req = []
    for tool, lst in stall_by_tool.items():
        if len(lst) >= 2:
            req = lst[1][0]
            second_req.append(req)
            hide_total += 1
            nxt = next((r for r in ep["requests"] if r["index"] == req + 1), None)
            used = [u for u in (nxt["units"] if nxt else []) if u["tool"] == tool and not u["harness_error"]]
            useful = False
            for u in used:
                # useful = successful and new: its text was never returned by this tool before request req+1
                prior = {x["text"] for rr in ep["requests"] if rr["index"] <= req for x in rr["units"] if x["tool"] == tool}
                if u["ok"] and not is_empty_or_not_found(u) and u["text"] not in prior:
                    useful = True
            hide_useful += useful
    n = len(ep["requests"])
    return dict(stalls_a=len(stalls["a"]), stalls_a2=len(stalls["a2"]), stalls_b=len(stalls["b"]), stalled_tools=len(stall_by_tool),
                requests_after_first=sum(n - q for q in first_req), requests_after_second=sum(n - q for q in second_req),
                second_stalls=len(second_req), hide_total=hide_total, hide_useful=hide_useful)


# ------------------------------------------------------------------ proposal 3
def rewrite(value, allowed, log, path="", top=True):
    if isinstance(value, str):
        if ag.ABSOLUTE_NAME.fullmatch(value) or ag.RELATIVE_NAME.fullmatch(value):
            if value in allowed:
                return value
            m = ag.trailing_matches(value, allowed)
            if len(m) == 1:
                log.append(dict(kind="rewrite", path=path, old=value, new=m[0]))
                return m[0]
            if len(m) >= 2:
                log.append(dict(kind="reject_ambiguous", path=path, value=value, candidates=m))
            elif ag.ABSOLUTE_NAME.fullmatch(value):
                log.append(dict(kind="reject_never_seen", path=path, value=value))
        return value
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            nk = k if top else rewrite(k, allowed, log, path + ".key", False)
            out[nk] = rewrite(v, allowed, log, f"{path}.{k}" if path else k, False)
        return out
    if isinstance(value, list):
        return [rewrite(v, allowed, log, f"{path}[{i}]", False) for i, v in enumerate(value)]
    return value


def proposal3(ep):
    if not isinstance(ep["answer"], dict):
        return dict(status="no_answer")
    outputs = [u["output"] for r in ep["requests"] for u in r["units"] if u["tool"] != "final_answer" and not u["harness_error"]]
    allowed = ag.allowed_names(ep["task_text"], outputs)
    log = []
    new = rewrite(ep["answer"], allowed, log)
    rejects = [x for x in log if x["kind"].startswith("reject")]
    rewrites = [x for x in log if x["kind"] == "rewrite"]
    after = E.v2.score_task(ep["task_def"], new, ep["rows"])["supported_complete"] if rewrites else ep["supported"]
    listed_unread = None
    if any(x["kind"] == "reject_never_seen" for x in rejects):
        queried = {c["entity"] for r in ep["requests"] for c in r["calls"] if c["entity"]}
        listed_unread = sorted(n for n in allowed if n not in queried)
    return dict(status="reject" if rejects else ("rewritten" if rewrites else "unchanged"), supported_before=ep["supported"], supported_after=after,
                rewrites=rewrites, rejects=rejects, has_next_step=bool(listed_unread) if listed_unread is not None else None)


def main():
    out = dict(episodes=[], protocol_sha=(HERE / "PROTOCOL.sha256").read_text().split()[0])
    for ep in eps:
        out["episodes"].append(dict(run_id=ep["run_id"], group=ep["group"], model=ep["model"], arm=ep["arm"], task=ep["task"], seed=ep["seed"],
                                    supported=ep["supported"], requests=len(ep["requests"]), tokens=sum(rtoks(r) for r in ep["requests"]),
                                    p1_v1=proposal1(ep, "V1"), p1_v2=proposal1(ep, "V2"), p2=proposal2(ep), p3=proposal3(ep)))
    (HERE / "results.json").write_text(json.dumps(out, indent=1, default=str))
    print("episodes", len(out["episodes"]))


if __name__ == "__main__":
    main()
