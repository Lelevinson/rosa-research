"""Extra wiring check (not one of rules 1-6): the FIRST model request (messages, tool schemas, options) of every rehearsal cell versus the dev seed-1 trace of the same task, model and arm
(EX-M vs steady-loop ablation FULL seed 1; E1 vs fairness E1 seed 1). Identical first requests = same prompt, menu and settings reach the model on both paths.
  uv run --no-sync python research/studies/exam_dress_rehearsal_20261122/first_request_check.py"""
import hashlib, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RUN = REPO / "research/_artifacts/runs/exam_dress_rehearsal_20261122"
Q = RUN / "custody/stage1_rehearsal/queue/rehearsal_144_20261122"
idmap = json.loads((HERE / "idmap.json").read_text())
dev = {}
for path, arm, ph, tag in (("research/studies/steady_loop_ablation_20261117/RESULTS_LOG.jsonl", "FULL", "full", "EX-M"), ("research/studies/fairness_errors_as_text_20261117/RESULTS_LOG.jsonl", "E1", "full", "E1")):
    for l in (REPO / path).read_text().splitlines():
        r = json.loads(l)
        if r.get("phase") == ph and r.get("arm") == arm and r.get("seed") == 1:
            dev[(tag, r["model"], r["task"])] = REPO / r["trace_path"]
def first(p):
    for l in p.read_text().splitlines():
        e = json.loads(l)
        if e["kind"] == "model_start":
            return e
h = lambda o: hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()
out, same_first_call, n = [], 0, 0
for l in (Q / "RESULTS_LOG_laptop.jsonl").read_text().splitlines():
    r = json.loads(l); task = idmap[r["task"]]
    key = (r["system"], r["model"], task)
    if key not in dev or not dev[key].exists():
        out.append((key, "no dev seed-1 trace")); continue
    a, b = first(dev[key]), first((Q / "runs_laptop" / r["run_id"]) / "trace.jsonl")
    ident = all(h(a.get(k)) == h(b.get(k)) for k in ("messages", "schemas", "options"))
    out.append((key, ident)); n += 1
print("compared", n, "cells; first request identical in", sum(1 for k, v in out if v is True), "; not identical:", [k for k, v in out if v is False], "; no dev trace:", [k for k, v in out if isinstance(v, str)])
