"""Job 2: no-progress cutoff, exact offline count (PROTOCOL.md). uv run python job2_cutoff.py"""
import json
from collections import defaultdict
import common
from common import E, rtokens

episodes = common.load_episodes()


def progress_by_request(ep):
    """{request index: True if the request made progress}; a request is progress if it adds a ledger name, makes a first-time successful call,
    or repeats a successful call whose result text changed."""
    new_names = defaultdict(set)
    for index, call, new in E.ledger_events(ep)[0]:
        new_names[index] |= new
    previous = {}  # (tool, other arguments, entity) -> last successful result text
    progress = {}
    for request in ep["requests"]:
        made = bool(new_names[request["index"]])
        for call in request["calls"]:
            if call["tool"] == "final_answer" or call["harness_error"] or not call["ok"]:
                continue
            key = (call["tool"], json.dumps(call["args"], sort_keys=True), call["entity"])
            if key not in previous or previous[key] != call["text"]:
                made = True
            previous[key] = call["text"]
        progress[request["index"]] = made
    return progress


def cut_effect(ep, progress, k):
    """First time k consecutive no-progress requests end at request j: the system offers only the finish tool at j+1."""
    n, streak = len(ep["requests"]), 0
    for request in ep["requests"]:
        streak = 0 if progress[request["index"]] else streak + 1
        if streak >= k:
            at = request["index"] + 1
            if at > n:
                return None  # the episode ended before the offer would happen
            later = [r for r in ep["requests"] if r["index"] > at]
            return dict(fires_after=request["index"], offered_at=at, removed_requests=len(later), removed_tokens=sum(rtokens(r) for r in later))
    return None


rows = []
for ep in episodes:
    progress = progress_by_request(ep)
    base = dict(run_id=ep["run_id"], model=ep["model"], task=ep["task"], arm=ep["arm"], control_type=ep["control_type"], supported=ep["supported"],
                requests=len(ep["requests"]), tokens=sum(rtokens(r) for r in ep["requests"]))
    for k in (3, 4, 5):
        effect = cut_effect(ep, progress, k)
        rows.append(dict(base, k=k, fires=effect is not None, **(effect or dict(removed_requests=0, removed_tokens=0, fires_after=None, offered_at=None))))


def summarize(subset):
    out = dict(episodes=len(subset), requests=sum(r["requests"] for r in subset), tokens=sum(r["tokens"] for r in subset),
               fires=sum(r["fires"] for r in subset), cut=sum(r["removed_requests"] > 0 for r in subset),
               fires_at_recorded_final_request=sum(r["fires"] and r["removed_requests"] == 0 for r in subset),
               removed_requests=sum(r["removed_requests"] for r in subset), removed_tokens=sum(r["removed_tokens"] for r in subset),
               supported_episodes=sum(r["supported"] for r in subset), supported_cut=sum(r["supported"] and r["removed_requests"] > 0 for r in subset))
    out["removed_requests_share"] = out["removed_requests"] / out["requests"] if out["requests"] else 0
    out["removed_tokens_share"] = out["removed_tokens"] / out["tokens"] if out["tokens"] else 0
    return out


result = dict(protocol_sha=open("PROTOCOL.sha256").read().split()[0], rows=rows)
for k in (3, 4, 5):
    at_k = [r for r in rows if r["k"] == k]
    result[f"K{k}"] = dict(total=summarize(at_k), control_type_only=summarize([r for r in at_k if r["control_type"]]),
                           per_model={m: summarize([r for r in at_k if r["model"] == m]) for m in sorted({r["model"] for r in at_k})},
                           supported_cut_cases=[dict(run_id=r["run_id"], model=r["model"], task=r["task"], offered_at=r["offered_at"], removed_requests=r["removed_requests"])
                                                for r in at_k if r["supported"] and r["removed_requests"] > 0],
                           eligible=summarize(at_k)["supported_cut"] == 0)
json.dump(result, open("results_job2.json", "w"), indent=1)
for k in (3, 4, 5):
    t = result[f"K{k}"]["total"]
    print(k, {x: t[x] for x in ("fires", "cut", "removed_requests", "removed_tokens", "supported_cut")}, "eligible", result[f"K{k}"]["eligible"])
