"""POST HOC, descriptive, written after the frozen results were read (labelled as such in the report; replaces nothing).
A: what the derailing request's OWN result was (not the trigger) by model and first-request flag.
B: split-name context rate with an exposure that does not depend on the next call (the frozen category 2 rate is 100% by construction).
C: category 6 and category 5 detail: per task/model derailment types and the largest waste-after episodes.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import derail as D  # noqa: E402

rows = [json.loads(l) for l in (HERE / "derail_rows.jsonl").read_text().splitlines()]
derailed = [r for r in rows if r["derailed"]]


def own_class(r):
    bad = [x for x in r["derailing"] if x["failed"]]
    if not bad:
        return "no failed call (" + r["derail_type"] + ")"
    t = bad[0]["text"]
    if "multiple repeat" in t:
        return "regex (list tool blacklist)"
    if t.startswith(("Invalid arguments", "final_answer needs", "Answer not accepted")):
        return "validation: " + bad[0]["tool"]
    if "Unable to find" in t or "Unknown" in t or "not found" in t.lower():
        return "not-found"
    if t.startswith('{"error": ""'):
        return "empty error"
    return "other"


A = defaultdict(Counter)
for r in derailed:
    A[(own_class(r))][(r["model"], "first" if r["first_request"] else "later")] += 1
out = dict(A={k: dict(sum_=sum(v.values()), **{f"{m}|{w}": n for (m, w), n in sorted(v.items())}) for k, v in sorted(A.items(), key=lambda kv: -sum(kv[1].values()))})
out["A_first_request_by_model"] = dict(Counter(r["model"] for r in derailed if r["first_request"]))
out["A_first_request_waste_after"] = sum(r["waste_after"] for r in derailed if r["first_request"])
out["A_first_request_never"] = sum(r["outcome"] == "never" for r in derailed if r["first_request"])
out["A_first_request_n"] = sum(r["first_request"] for r in derailed)

# B: context-only split exposure
tasks = D.C.all_tasks()
labelled = {l["run_id"]: l for l in map(json.loads, (D.STUDIES / "loss_map_20261120/labelled_lossmap.jsonl").read_text().splitlines())}
p1 = {r["run_id"]: r for r in D.C.load_rows("lossmap")}
p3 = [json.loads(l) for l in (D.ROOT / "research/_artifacts/exam/listval/RESULTS_LOG_all.jsonl").read_text().splitlines()]
p3 = [r for r in p3 if r["arm"] == "FULL"]
labs3 = {l["run_id"]: l for l in D.C.analyse(p3)}
p3 = {r["run_id"]: r for r in p3}
B = defaultdict(lambda: dict(contexts=0, next_derails=0, next_name_guess=0, next_uses_field=0, episodes=set()))
for r in rows:
    row, lab = (p1[r["run_id"]], labelled[r["run_id"]]) if r["pop"] == "P1" else (p3[r["run_id"]], labs3[r["run_id"]])
    ep = D.E.parse(r["pop"], dict(row), tasks)
    types = lab["request_types"]
    Dx = r["derail_index"]
    for k in range(1, len(ep["requests"])):
        if Dx is not None and k + 1 > Dx:
            break
        req = ep["requests"][k - 1]
        pairs = [m for c in req["calls"] if c["tool"] != "final_answer" for m in D.SPLIT.findall(D.text_of(c))]
        if not pairs:
            continue
        nxt = ep["requests"][k]
        ents = [c["entity"] for c in nxt["calls"] if c["entity"] is not None]
        uses = any(e in (a, b) for a, b in pairs for e in ents)
        b = B[r["model"]]
        b["contexts"] += 1
        b["next_derails"] += types[k] in D.DERAIL_TYPES
        b["next_name_guess"] += types[k] == "name_guess"
        b["next_uses_field"] += uses
        b["episodes"].add(r["run_id"])
out["B_split_context_by_model"] = {m: dict(v, episodes=len(v["episodes"])) for m, v in sorted(B.items())}
out["B_all"] = {k: sum(v[k] for v in B.values()) for k in ("contexts", "next_derails", "next_name_guess", "next_uses_field")}
out["B_episodes_with_split_context"] = len(set().union(*[v["episodes"] for v in B.values()])) if B else 0

# C
C6 = [r for r in derailed if r["category"] == 6]
out["C6_by_task_model"] = {f"{t}|{m}": dict(n=n, waste=sum(r["waste_after"] for r in C6 if r["task"] == t and r["model"] == m), never=sum(r["outcome"] == "never" for r in C6 if r["task"] == t and r["model"] == m))
                           for (t, m), n in sorted(Counter((r["task"], r["model"]) for r in C6).items())}
out["C6_top_waste"] = [dict(run=r["run_id"], waste=r["waste_after"], outcome=r["outcome"], type=r["derail_type"], idx=r["derail_index"], trace=r["trace_path"]) for r in sorted(C6, key=lambda r: -r["waste_after"])[:8]]
C5 = [r for r in derailed if r["category"] == 5]
out["C5_never"] = [dict(run=r["run_id"], waste=r["waste_after"], type=r["derail_type"], trace=r["trace_path"]) for r in C5 if r["outcome"] == "never"]
out["share_of_waste_after_in_unsupported"] = round(sum(r["waste_after"] for r in derailed if not r["supported"]) / sum(r["waste_after"] for r in derailed), 3)
# waste_after vs derailment index: do late derailments cost more?
for lo, hi in ((1, 1), (2, 3), (4, 99)):
    g = [r for r in derailed if lo <= r["derail_index"] <= hi]
    out[f"index_{lo}-{hi}"] = dict(n=len(g), mean_waste=round(sum(r["waste_after"] for r in g) / max(len(g), 1), 2), unsupported=sum(not r["supported"] for r in g))
(HERE / "posthoc.json").write_text(json.dumps(out, indent=1, default=list))
print(json.dumps(out, indent=1, default=list)[:6000])

# D: first request (k = 0 context): rate and outcome by model
rows_by_model = defaultdict(list)
for r in rows:
    rows_by_model[r["model"]].append(r)
D0 = {}
for m, eps in sorted(rows_by_model.items()):
    first = [r for r in eps if r["derailed"] and r["first_request"]]
    D0[m] = dict(episodes=len(eps), first_request_derailments=len(first), rate_pct=round(100 * len(first) / len(eps), 1), waste_after=sum(r["waste_after"] for r in first),
                 mean_waste_after=round(sum(r["waste_after"] for r in first) / max(len(first), 1), 2), outcomes=dict(Counter(r["outcome"] for r in first)), own=dict(Counter(own_class(r) for r in first)))
out["D_first_request_by_model"] = D0
out["D_error_texts_cat1"] = [dict(text=r["error_text"], run=r["run_id"], waste=r["waste_after"], outcome=r["outcome"], trace=r["trace_path"]) for r in derailed if r["category"] == 1]
(HERE / "posthoc.json").write_text(json.dumps(out, indent=1, default=list))
print(json.dumps(D0, indent=1)); print(json.dumps(out["D_error_texts_cat1"], indent=1))
