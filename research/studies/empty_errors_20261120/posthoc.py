"""POST HOC (labelled; replaces nothing; written after the frozen results were read).
A: is the typed entity of an empty-error event a name the model already had (task text / earlier results, exactly or with a leading slash)? If yes the M1 sentence "no <kind> named X was found" would be wrong or misleading.
B: same-(model, task) adjusted comparison: expected recovery of the empty events if they recovered like the non-empty not-found events of the same model and task.
C: clustering: events per episode, repeats of the same call.
D: service_info calls in P1+P3 by argument form (short vs absolute) and result.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import size_empty as S  # noqa: E402

events = [json.loads(l) for l in (HERE / "events.jsonl").read_text().splitlines()]
p13 = [e for e in events if e["pop"] in ("P1", "P3")]
tools = {e["tool"] for e in p13 if e["cls"] == "empty"}
emp = [e for e in p13 if e["cls"] == "empty"]
nf = [e for e in p13 if e["cls"] == "notfound" and e["tool"] in tools]
out = {}

# A, D need the parsed episodes
tasks = S.CC.all_tasks()
valid, d_forms = Counter(), Counter()
by_run = {}
for pop, ep in S.load_p13(tasks):
    by_run[(pop, ep["run_id"])] = ep
for e in emp:
    ep = by_run[(e["pop"], e["run_id"])]
    ledger = set(S.C.ag.names_in_text(ep["task_text"]))
    evs, _ = S.E.ledger_events(ep)
    for index, _c, new in evs:
        if index < e["index"]:
            ledger |= new
    known = S.C.known(e["typed"], ledger)
    valid[(e["model"], e["tool"], "ledger-known" if known else "not in ledger")] += 1
out["A_typed_entity_known"] = {" | ".join(k): v for k, v in sorted(valid.items())}
out["A_known_total"] = sum(v for k, v in valid.items() if k[2] == "ledger-known")
out["A_total"] = len(emp)
for (pop, rid), ep in by_run.items():
    for r in ep["requests"]:
        for c in r["calls"]:
            if c["tool"] == "ros2_service_info":
                form = "absolute" if str(c["entity"]).startswith("/") else "short"
                res = "empty error" if S.is_empty_error(c) else ("ok" if c["ok"] else "other failure")
                d_forms[(c["entity"] if form == "short" else "(absolute)", form, res)] += 1
out["D_service_info"] = {" | ".join(map(str, k)): v for k, v in sorted(d_forms.items(), key=lambda kv: -kv[1])}

# B
cells_nf = defaultdict(list)
for e in nf:
    cells_nf[(e["model"], e["task"])].append(e)
exp = obs = n = 0
unmatched = 0
for e in emp:
    c = cells_nf.get((e["model"], e["task"]))
    if not c:
        unmatched += 1
        continue
    n += 1
    exp += sum(x["recovered"] for x in c) / len(c)
    obs += e["recovered"]
out["B_matched_empty_events"] = n
out["B_unmatched_empty_events"] = unmatched
out["B_expected_recovered_if_like_notfound"] = round(exp, 2)
out["B_observed_recovered"] = obs
out["B_adjusted_gap_pp"] = round(100 * (exp - obs) / n, 1) if n else None
# per task v2 and non-v2
for name, f in (("v2", lambda e: e["task"] == "v2"), ("not_v2", lambda e: e["task"] != "v2")):
    a, b = [e for e in emp if f(e)], [e for e in nf if f(e)]
    out[f"B_{name}"] = dict(empty=(len(a), sum(e["recovered"] for e in a)), notfound=(len(b), sum(e["recovered"] for e in b)),
                            empty_pct=round(100 * sum(e["recovered"] for e in a) / len(a), 1) if a else None, notfound_pct=round(100 * sum(e["recovered"] for e in b) / len(b), 1) if b else None)
# C
per_ep = Counter((e["pop"], e["run_id"]) for e in emp)
out["C_empty_episodes"] = len(per_ep)
out["C_events_per_episode"] = {f"{k[0]} {k[1]}": v for k, v in per_ep.most_common()}
out["C_events_same_typed_repeat"] = sum(1 for k in per_ep for _ in [0]) and None
seen = set(); rep = 0
for e in sorted(emp, key=lambda e: (e["run_id"], e["index"])):
    key = (e["run_id"], e["tool"], e["typed"])
    rep += key in seen
    seen.add(key)
out["C_empty_events_repeating_an_earlier_empty_call"] = rep
out["C_empty_episodes_supported"] = len({(e["pop"], e["run_id"]) for e in emp if e["supported"]})
(HERE / "posthoc.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
