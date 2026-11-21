"""Empty errors / empty-string arguments: offline sizing (PROTOCOL.md frozen). Saved traces only.
  PYTHONDONTWRITEBYTECODE=1 nice uv run python research/studies/empty_errors_20261120/size_empty.py
"""
import hashlib
import json
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDIES = ROOT / "research/studies"
for p in ("loss_map_20261120", "offline_replay_20261116", "candidate_counts_20261118"):
    sys.path.insert(0, str(STUDIES / p))
import classify as C  # noqa: E402
import episodes as E  # noqa: E402
import count_candidates as CC  # noqa: E402

NOT_FOUND = re.compile(r"Unable to find|Unknown (node|topic|service)|Node not found|not found|does not exist", re.I)
M2_RE = re.compile(r"^Invalid arguments for (\S+): field '([^']+)': expected array or null, received string \"\"")
M2_OTHER = re.compile(r"^Invalid arguments for (\S+): field '([^']+)': expected array or null, received string \"(None|null)\"")
WINDOW = 5
SEED = 20261120


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_freeze():
    f = json.loads((HERE / "FREEZE.json").read_text())
    assert sha(HERE / "PROTOCOL.md") == f["protocol_md_sha256"], "PROTOCOL.md changed after the freeze"
    assert sha(STUDIES / "derailment_20261120/derail.py") == f["derail_py_sha256"]
    assert sha(STUDIES / "candidate_counts_20261118/count_candidates.py") == f["count_candidates_py_sha256"]


def kind_of(call):
    key = call["entity_arg"]
    if not key:
        return None
    stem = re.sub(r"_name$", "", key)
    return stem[:-1] if stem.endswith("s") else stem


def is_empty_error(c):
    return c["tool"] != "final_answer" and not c["harness_error"] and isinstance(c["output"], dict) and "error" in c["output"] and not str(c["output"]["error"]).strip()


def is_not_found(c):
    return c["tool"] != "final_answer" and not c["ok"] and not c["harness_error"] and not is_empty_error(c) and bool(NOT_FOUND.search(c["text"] if isinstance(c["text"], str) else ""))


def recovery(ep, i, call):
    """(recovered, requests to recovery) in the 5 requests after request i."""
    kind, typed = kind_of(call), call["entity"]
    n = len(ep["requests"])
    for j in range(i + 1, min(n, i + WINDOW) + 1):
        for c in ep["requests"][j - 1]["calls"]:
            if c["tool"] == "final_answer":
                if not c["harness_error"] and ep["supported"]:
                    return True, j - i
            elif c["ok"] and not c["harness_error"] and c["entity"] is not None and kind_of(c) == kind and c["entity"] != typed:
                return True, j - i
    return False, None


def episode_events(pop, ep):
    n = len(ep["requests"])
    events, m2 = [], []
    for r in ep["requests"]:
        i = r["index"]
        for cls, test in (("empty", is_empty_error), ("notfound", is_not_found)):
            first = next((c for c in r["calls"] if test(c)), None)
            if first is not None:
                ok, dist = recovery(ep, i, first)
                events.append(dict(pop=pop, run_id=ep["run_id"], model=ep["model"], task=ep["task"], cls=cls, tool=first["tool"], kind=kind_of(first), typed=first["entity"], index=i, requests=n,
                                   recovered=ok, dist=dist, censored=(not ok) and i + WINDOW > n, supported=bool(ep["supported"]), after=n - i))
        for c in r["calls"]:
            text = c["text"] if isinstance(c["text"], str) else ""
            m = M2_RE.match(text) if c["harness_error"] else None
            if m:
                later = next((j for j in range(i + 1, n + 1) if any(x["tool"] == c["tool"] and x["ok"] and not x["harness_error"] for x in ep["requests"][j - 1]["calls"])), None)
                m2.append(dict(pop=pop, run_id=ep["run_id"], model=ep["model"], task=ep["task"], tool=c["tool"], field=m.group(2), index=i, saved=(later - i) if later else 0, never=later is None, supported=bool(ep["supported"])))
    other_m2 = sum(1 for r in ep["requests"] for c in r["calls"] if c["harness_error"] and isinstance(c["text"], str) and M2_OTHER.match(c["text"]))
    return events, m2, other_m2


def load_p13(tasks):
    out = []
    for r in C.load_rows("lossmap"):
        out.append(("P1", E.parse("loss", dict(r), tasks)))
    for line in (ROOT / "research/_artifacts/exam/listval/RESULTS_LOG_all.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["arm"] == "FULL":
            out.append(("P3", E.parse("loss", dict(r), tasks)))
    return out


def rate(events):
    n = len(events)
    return dict(events=n, recovered=sum(e["recovered"] for e in events), rate_pct=round(100 * sum(e["recovered"] for e in events) / n, 1) if n else None,
                censored=sum(e["censored"] for e in events), mean_dist=round(statistics.mean(e["dist"] for e in events if e["recovered"]), 2) if any(e["recovered"] for e in events) else None,
                supported_episodes=sum(e["supported"] for e in events))


def block(events, tools):
    emp = [e for e in events if e["cls"] == "empty"]
    nf = [e for e in events if e["cls"] == "notfound" and e["tool"] in tools]
    out = dict(empty=rate(emp), notfound=rate(nf))
    if emp and nf:
        out["gap_pp"] = round(out["notfound"]["rate_pct"] - out["empty"]["rate_pct"], 1)
    first = {}
    for e in emp:
        first.setdefault(e["run_id"], e)
    firstnf = {}
    for e in nf:
        firstnf.setdefault(e["run_id"], e)
    out["first_event_per_episode"] = dict(empty=rate(list(first.values())), notfound=rate(list(firstnf.values())))
    return out


def main():
    check_freeze()
    tasks = CC.all_tasks()
    pops = {"P1": [], "P3": [], "P2": []}
    events, m2, other, requests = [], [], Counter(), Counter()
    for pop, ep in load_p13(tasks):
        ev, m, o = episode_events(pop, ep)
        events += ev
        m2 += m
        other[pop] += o
        requests[pop] += len(ep["requests"])
        pops[pop].append(ep["run_id"])
    for study, row in CC.load_population():
        ep = CC.parse_episode(study, row, tasks)
        ev, m, o = episode_events("P2", ep)
        events += ev
        m2 += m
        other["P2"] += o
        requests["P2"] += len(ep["requests"])
        pops["P2"].append(ep["run_id"])
    tools = sorted({e["tool"] for e in events if e["cls"] == "empty" and e["pop"] in ("P1", "P3")})
    res = dict(requests=dict(requests), episodes={k: len(v) for k, v in pops.items()}, empty_tools_p13=tools)
    sel = {"P1": ("P1",), "P3": ("P3",), "P1+P3": ("P1", "P3"), "P2": ("P2",)}
    for name, ps in sel.items():
        ev = [e for e in events if e["pop"] in ps]
        t = sorted({e["tool"] for e in ev if e["cls"] == "empty"}) if name != "P1+P3" else tools
        b = block(ev, set(t))
        emp = [e for e in ev if e["cls"] == "empty"]
        b["empty_by_model"] = dict(Counter(e["model"] for e in emp))
        b["empty_by_task"] = dict(Counter(e["task"] for e in emp))
        b["empty_by_tool"] = dict(Counter(e["tool"] for e in emp))
        b["v2_share_pct"] = round(100 * sum(e["task"] == "v2" for e in emp) / len(emp), 1) if emp else None
        b["max_task_share_pct"] = round(100 * max(Counter(e["task"] for e in emp).values()) / len(emp), 1) if emp else None
        b["by_model"] = {m: block([e for e in ev if e["model"] == m], set(t)) for m in sorted({e["model"] for e in ev})}
        b["by_task_empty"] = {tk: rate([e for e in emp if e["task"] == tk]) for tk in sorted({e["task"] for e in emp})}
        b["by_task_notfound"] = {tk: rate([e for e in ev if e["cls"] == "notfound" and e["tool"] in t and e["task"] == tk]) for tk in sorted({e["task"] for e in ev if e["cls"] == "notfound" and e["tool"] in t})}
        b["by_tool"] = {tl: dict(empty=rate([e for e in emp if e["tool"] == tl]), notfound=rate([e for e in ev if e["cls"] == "notfound" and e["tool"] == tl])) for tl in t}
        # size: first non-recovered empty event per episode
        seen, after = set(), 0
        for e in sorted(emp, key=lambda e: (e["run_id"], e["index"])):
            if not e["recovered"] and e["run_id"] not in seen:
                seen.add(e["run_id"])
                after += e["after"]
        reqs = sum(requests[p] for p in ps)
        b["size"] = dict(nonrecovered_episodes=len(seen), requests_after=after, total_requests=reqs, share_pct=round(100 * after / reqs, 2))
        m2s = [m for m in m2 if m["pop"] in ps]
        b["M2"] = dict(events=len(m2s), episodes=len({m["run_id"] for m in m2s}), saved_max=sum(m["saved"] for m in m2s), never_retried=sum(m["never"] for m in m2s), saved_share_pct=round(100 * sum(m["saved"] for m in m2s) / reqs, 2),
                       by_tool=dict(Counter(m["tool"] for m in m2s)), by_field=dict(Counter(m["field"] for m in m2s)), by_model=dict(Counter(m["model"] for m in m2s)), by_task=dict(Counter(m["task"] for m in m2s)),
                       other_string_rejections_none_null=sum(other[p] for p in ps))
        res[name] = b
    # bars
    g = res["P1+P3"]
    emp_models = [m for m, n in g["empty_by_model"].items() if n >= 5]
    res["bars"] = dict(gap_pp=g.get("gap_pp"), gap_met=(g.get("gap_pp") or -999) >= 15, models_with_5=emp_models, models_met=len(emp_models) >= 2,
                       M1_case=((g.get("gap_pp") or -999) >= 15) and len(emp_models) >= 2, tools=len(g["empty_by_tool"]), tools_met=len(g["empty_by_tool"]) >= 2, max_task_share_pct=g["max_task_share_pct"],
                       task_met=(g["max_task_share_pct"] or 100) <= 60, size_share_pct=g["size"]["share_pct"], size_met=g["size"]["share_pct"] >= 3)
    # hand-reading sample
    rng = random.Random(SEED)
    emp = sorted([e for e in events if e["cls"] == "empty" and e["pop"] in ("P1", "P3")], key=lambda e: (e["run_id"], e["index"]))
    sample = []
    for m in sorted({e["model"] for e in emp}):
        pool = [e for e in emp if e["model"] == m]
        sample += rng.sample(pool, min(2, len(pool)))
    rest = [e for e in emp if e not in sample]
    if len(sample) < 8:
        sample += rng.sample(rest, 8 - len(sample))
    res["handread"] = [dict(e, trace=None) for e in sample]
    (HERE / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    (HERE / "m2_events.jsonl").write_text("\n".join(json.dumps(m) for m in m2) + "\n")
    (HERE / "results.json").write_text(json.dumps(res, indent=1, default=list))
    print(json.dumps(res["bars"], indent=1))


if __name__ == "__main__":
    main()
