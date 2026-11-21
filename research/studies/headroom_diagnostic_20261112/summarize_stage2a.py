"""Tables and kill-bar evaluation for Stage 2a (writes STAGE2A_TABLES.md)."""
import collections, json, sys
from pathlib import Path
d = Path(sys.argv[1])
data = json.loads((d / "replay_stage2a.json").read_text())
rows = data["rows"]
TASKS = ("t1", "t2", "t3", "d1", "d2", "x1")
PRED = [("oracle", "oracle"), ("tau0.5", "learned 0.5"), ("tau0.7", "learned 0.7"), ("tau0.9", "learned 0.9"), ("static_top1", "static top-1")]
out = ["# Stage 2a tables (offline replay; leave-one-task-out; A0 traces)\n",
       f"Training episodes available: {data['training_episodes']} (each fold excludes the held-out task). Evaluation episodes: {data['evaluation']}.\n"]
def agg(model, task, key, field):
    return sum(r[key][field] for r in rows if r["model"] == model and r["task"] == task)
for model, name in (("qwen", "Qwen A0 (Stage 1a)"), ("luna", "gpt-6-luna A0 (Stage 1c)")):
    out += [f"## {name}: per task (both repeats summed)\n",
            "Removed = primary non-chained count (chained count in brackets). Candidate = requests with at least one candidate call; oracle-removable = every call is a candidate.\n",
            "| task | requests | candidate requests | " + " | ".join(label + " removed" for _, label in PRED) + " |", "|---|---:|---:|" + "---:|" * len(PRED)]
    for t in TASKS:
        req = sum(r["requests"] for r in rows if r["model"] == model and r["task"] == t)
        cand = agg(model, t, "oracle", "candidate_requests")
        cells = [f"{agg(model, t, k, 'removed')} ({agg(model, t, k, 'removed_chained')})" for k, _ in PRED]
        out.append(f"| {t} | {req} | {cand} | " + " | ".join(cells) + " |")
    total = sum(r["requests"] for r in rows if r["model"] == model)
    out.append(f"| **all** | {total} | {sum(agg(model, t, 'oracle', 'candidate_requests') for t in TASKS)} | " +
               " | ".join(f"{sum(agg(model, t, k, 'removed') for t in TASKS)} ({sum(agg(model, t, k, 'removed_chained') for t in TASKS)})" for k, _ in PRED) + " |")
    out += ["", "Saving as a share of requests, with per-task spread (primary count):\n", "| predictor | removed / requests | saving % | per-task saving % (t1..x1) | tasks contributing |", "|---|---:|---:|---|---:|"]
    for k, label in PRED:
        per = []
        for t in TASKS:
            req = sum(r["requests"] for r in rows if r["model"] == model and r["task"] == t)
            per.append(100 * agg(model, t, k, "removed") / req)
        rem = sum(agg(model, t, k, "removed") for t in TASKS)
        out.append(f"| {label} | {rem}/{total} | {100 * rem / total:.1f} | " + ", ".join(f"{p:.0f}" for p in per) + f" | {sum(p > 0 for p in per)} |")
    out += ["", "Cost side (primary trajectory; speculation fires after every actual request):\n",
            "| predictor | speculative units | used by the model's next request | precision | extra native ops | extra input tokens (est.) | input tokens of removed requests | partial requests |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for k, label in PRED[1:]:
        u = sum(agg(model, t, k, "units") for t in TASKS); us = sum(agg(model, t, k, "used") for t in TASKS)
        out.append(f"| {label} | {u} | {us} | {(100 * us / u) if u else 0:.0f}% | {sum(agg(model, t, k, 'extra_native') for t in TASKS)} | "
                   f"{sum(agg(model, t, k, 'extra_tokens') for t in TASKS):,.0f} | {sum(agg(model, t, k, 'saved_input_tokens') for t in TASKS):,} | {sum(agg(model, t, k, 'partial') for t in TASKS)} |")
    out.append("")
# kill bar
total_q = sum(r["requests"] for r in rows if r["model"] == "qwen")
learned = {t: agg("qwen", t, "tau0.7", "removed") for t in TASKS}
static = {t: agg("qwen", t, "static_top1", "removed") for t in TASKS}
L, S = sum(learned.values()), sum(static.values())
a = 100 * L / total_q < 10
b = L <= S
c = sum(v > 0 for v in learned.values()) <= 1
out += ["## Kill bar (frozen; evaluated at tau 0.7 on Qwen A0, 63 requests)\n",
        f"- (a) saving under 10% of requests: learned removes {L} of {total_q} = {100 * L / total_q:.1f}% -> **{'FIRES' if a else 'does not fire'}**.",
        f"- (b) learned does not beat static top-1: learned {L} vs static {S} -> **{'FIRES' if b else 'does not fire'}**.",
        f"- (c) all removals from one task: tasks with removals {[t for t, v in learned.items() if v]} -> **{'FIRES' if c else 'does not fire'}** (two tasks would be reported prominently, not auto-stop).",
        f"- Direction stopped: **{'YES' if (a or b or c) else 'no'}**. At tau 0.5 learned removes {sum(agg('qwen', t, 'tau0.5', 'removed') for t in TASKS)}, at 0.9 {sum(agg('qwen', t, 'tau0.9', 'removed') for t in TASKS)} (reported, do not rescue a failure at 0.7).", ""]
out += ["## Pair table examples (training counts, per fold, top pairs)\n"]
for t in TASKS:
    out.append(f"- held out {t}: " + "; ".join(f"{k.split('|')[0].replace('ros2_','')}->{k.split('|')[1][:60]} {v[0]}/{v[1]}" for k, v in list(data['pairs'][t].items())[:3]))
(d / "STAGE2A_TABLES.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
