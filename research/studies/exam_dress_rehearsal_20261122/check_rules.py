"""Evaluate pass rules 1-6 of RULES.md on the rehearsal run. Reads only public dev traces and rows.
  source env.sh; uv run --no-sync python research/studies/exam_dress_rehearsal_20261122/check_rules.py RUN_NAME [--partial]
Writes rules_result.json and RULES_RESULT.md next to this file (partial runs write rules_result_partial.*)."""
import copy
import json
import subprocess
import sys
import os
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
REPO = HERE.parents[2]
RUN = REPO / "research/_artifacts/runs/exam_dress_rehearsal_20261122"
name = sys.argv[1]
partial = "--partial" in sys.argv
SUBSET_ENV = "e1h"  # Amendment 1 of RULES.md: the balanced 48-cell subset = the six e1h tasks x 4 models x 2 systems
Q = RUN / "custody/stage1_rehearsal/queue" / name
C = RUN / "custody/stage1_rehearsal/compact" / name
for sub in ("exam_arms_20261121", "thinking_escalation_20261119", "small_model_harness_20261115", "build_round2_20261116", "residual_failures_20261115", "final_exam_draft_20261118/exam_queue"):
    sys.path.insert(0, str(STUDIES / sub))
import exam_arms  # noqa: E402
import run_exam  # noqa: E402
import queue_core  # noqa: E402

idmap = json.loads((HERE / "idmap.json").read_text())
full = [json.loads(l) for l in (Q / "RESULTS_LOG_laptop.jsonl").read_text().splitlines() if l.strip()]
compact = [json.loads(l) for l in (C / "compact_laptop.jsonl").read_text().splitlines() if l.strip()]
spec = json.loads((HERE / "rehearsal_spec.json").read_text())
MODELS = spec["models"]
out = {}

# ---- rule 1 (planned cell ids come from the frozen planner on the rehearsal pool, restricted to the subset environment)
index = json.loads((RUN / "custody/stage1_rehearsal/task-index.json").read_text())
plan_spec = dict(spec, pools={"held_out_v2": {"tasks": index}})
planned_ids = {c["id"] for c in queue_core.build_cells(plan_spec) if c["env"] == SUBSET_ENV}
salt = json.loads(queue_core.LOCAL_CONFIG.read_text()).get("salt", "unsalted") if queue_core.LOCAL_CONFIG.exists() else "unsalted"
opaque = lambda text: __import__("hashlib").sha256((salt + text).encode()).hexdigest()[:12]
planned = len(planned_ids)
ids = [r["cell_id"] for r in full]
need = ("model", "seed", "system", "supported", "supported_raw", "name_fix_changed", "input_tokens", "output_tokens", "requests", "ending", "exact")
ok_endings = {"supported", "unsupported", "no_answer", "timeout", "iteration_cap", "validation_abort", "backend_error"}
bad = []
for r in compact:
    p = [k for k in need if k not in r]
    if r.get("model") not in MODELS or r.get("seed") != 1 or r.get("system") not in ("EX-M", "E1"): p.append("model/seed/system")
    if not isinstance(r.get("supported"), bool): p.append("supported type")
    if r.get("system") == "EX-M" and not isinstance(r.get("supported_raw"), bool): p.append("supported_raw must be bool for EX-M")
    if r.get("system") == "E1" and r.get("supported_raw") is not None: p.append("supported_raw must be null for E1")
    if not isinstance(r.get("name_fix_changed"), bool): p.append("name_fix_changed type")
    for k in ("input_tokens", "output_tokens"):
        if not isinstance(r.get(k), int): p.append(k)
    if not (isinstance(r.get("requests"), int) and r["requests"] >= 1): p.append("requests")
    if r.get("ending") not in ok_endings: p.append("ending " + str(r.get("ending")))
    if p: bad.append((r.get("cell"), p))
full_keys = {opaque(r["cell_id"]) for r in full}
compact_keys = [c["cell"] for c in compact]
out["rule1"] = dict(planned_cells_in_subset=planned, full_rows=len(full), compact_rows=len(compact), unique_full_cell_ids=len(set(ids)), full_duplicates=len(ids) - len(set(ids)),
                    full_ids_equal_plan=(set(ids) == planned_ids), unique_compact_keys=len(set(compact_keys)), compact_keys_equal_full_keys=(set(compact_keys) == full_keys),
                    bad_rows=bad[:10], bad_count=len(bad),
                    PASS=(set(ids) == planned_ids and len(ids) == planned and len(compact) == planned and len(set(compact_keys)) == planned and set(compact_keys) == full_keys and not bad))

# ---- rule 2 (dev code path on a copy of every trace with the dev task id)
scratch = RUN / "rescore_copies" / name
disagreements, checked = [], 0
for r in full:
    block, ep = r["run_id"].split("/")
    d = Q / "runs_laptop" / block / ep
    events = [json.loads(l) for l in (d / "trace.jsonl").read_text().splitlines()]
    dev_id = None
    for e in events:
        if e["kind"] == "episode_start":
            dev_id = idmap[e["task"]["id"]]
            e["task"]["id"] = dev_id
            e.setdefault("prompt_sha256", "not recorded by the exam worker")  # dev row builder wants this field; scoring does not use it
    cp = scratch / block / ep
    cp.mkdir(parents=True, exist_ok=True)
    (cp / "trace.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    attempt = next(json.loads(l) for l in (Q / "runs_laptop" / block / "attempts.jsonl").read_text().splitlines() if json.loads(l)["directory"] == ep)
    attempt = dict(attempt, error=None)
    dev = run_exam.episode_row("exam", "dev", cp, attempt)
    dev_ending = queue_core.ending_class(dev)
    comp = next(c for c in compact if c["cell"] == opaque(r["cell_id"]))
    mine = dict(supported=comp["supported"], exact=comp["exact"], requests=comp["requests"], input_tokens=comp["input_tokens"], output_tokens=comp["output_tokens"], native_ops=comp["native_ops"],
                ending=comp["ending"], name_fix_changed=comp["name_fix_changed"], supported_raw=comp["supported_raw"])
    theirs = dict(supported=bool(dev["supported_complete"]), exact=bool(dev["exact"]), requests=dev["llm_requests"], input_tokens=dev["input_tokens"], output_tokens=dev["output_tokens"],
                  native_ops=dev["native_ops"], ending=dev_ending, name_fix_changed=bool(dev["name_fix_changed"]),
                  supported_raw=bool(dev["supported_raw"]) if r["system"] == "EX-M" else None)
    checked += 1
    diff = {k: (mine[k], theirs[k]) for k in mine if mine[k] != theirs[k]}
    if diff:
        disagreements.append((r["cell_id"], diff))
out["rule2"] = dict(traces_checked=checked, disagreements=len(disagreements), detail=disagreements[:10], PASS=(checked == planned and not disagreements))

# ---- rule 6
writes = []
for r in full:
    block, ep = r["run_id"].split("/")
    for line in (Q / "runs_laptop" / block / ep / "trace.jsonl").read_text().splitlines():
        e = json.loads(line)
        if e["kind"] == "ros_start" and tuple(e["command"][1:3]) in {("param", "set"), ("service", "call"), ("topic", "pub")}:
            writes.append((r["run_id"], e["command"]))
scripted = sum(1 for r in full for line in (Q / "runs_laptop" / r["run_id"].split("/")[0] / r["run_id"].split("/")[1] / "trace.jsonl").read_text().splitlines() if '"scripted_change"' in line and '"kind": "scripted_change"' in line)
out["rule6"] = dict(traces_scanned=len(full), write_commands_in_ros_start=len(writes), detail=writes[:5], scripted_fixture_changes_outside_agent=scripted, PASS=(not writes))

# ---- rule 5
ref_sup = {"lfm3:1.7b": 6.0, "qwen3.5:9b": 6.0, "gpt-oss:20b": 6.0, "bonsai-2:4b": 5.0}  # Amendment 1: dev FULL on the same six e1h tasks
ref_ratio = {"lfm3:1.7b": 0.42, "qwen3.5:9b": 0.33, "gpt-oss:20b": 0.38, "bonsai-2:4b": 0.25}
rule5 = {}
for m in MODELS:
    em = [c for c in compact if c["model"] == m and c["system"] == "EX-M"]
    e1 = [c for c in compact if c["model"] == m and c["system"] == "E1"]
    sup = sum(c["supported"] for c in em)
    tm, te = sum(c["input_tokens"] + c["output_tokens"] for c in em), sum(c["input_tokens"] + c["output_tokens"] for c in e1)
    paired = {c["pair"] for c in em} & {c["pair"] for c in e1}
    em_p = sum(c["input_tokens"] + c["output_tokens"] for c in em if c["pair"] in paired)
    e1_p = sum(c["input_tokens"] + c["output_tokens"] for c in e1 if c["pair"] in paired)
    rule5[m] = dict(exm_cells=len(em), e1_cells=len(e1), exm_supported=sup, dev_full_reference=ref_sup[m], drop_cells=round(ref_sup[m] - sup, 1) if len(em) == 6 else None,
                    e1_supported=sum(c["supported"] for c in e1), paired_pairs=len(paired), token_ratio_exm_over_e1_on_pairs=round(em_p / e1_p, 3) if e1_p else None, dev_ratio_reference=ref_ratio[m],
                    FLAG_drop=(len(em) == 6 and (ref_sup[m] - sup) / 6 * 100 > 15), FLAG_ratio=bool(e1_p and em_p / e1_p > 0.8))
out["rule5"] = dict(per_model=rule5, FLAGS=[m for m, v in rule5.items() if v["FLAG_drop"] or v["FLAG_ratio"]])

# ---- rule 3 (needs the full run)
rows_path = HERE / ("compact_rows_partial.jsonl" if partial else "compact_rows.jsonl")
rows_path.write_text("\n".join(json.dumps(c) for c in compact) + "\n")
prefix = HERE / ("analysis_primary_partial" if partial else "analysis_primary")
proc = subprocess.run([sys.executable, str(STUDIES / "final_exam_draft_20261118/freeze_package_20261121/analyze_primary.py"), "--rows", str(rows_path), "--primary", "EX-M", "--baseline", "E1",
                       "--machine", "laptop", "--planned-pairs", "24", "--out", str(prefix)], capture_output=True, text=True)
md = Path(str(prefix) + ".md").read_text() if Path(str(prefix) + ".md").exists() else ""
aj = json.loads(Path(str(prefix) + ".json").read_text()) if Path(str(prefix) + ".json").exists() else {}
def find_pairs(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("pairs", "n_pairs", "paired_cells") and isinstance(v, int): return v
            r_ = find_pairs(v)
            if r_ is not None: return r_
    return None
n_pairs = find_pairs(aj)
out["rule3"] = dict(returncode=proc.returncode, stderr_tail=proc.stderr[-400:], pairs_reported_by_analyzer=n_pairs, interim=("INTERIM" in md), json_keys=list(aj)[:12],
                    PASS=(proc.returncode == 0 and not partial and n_pairs == 24))
(HERE / ("rules_result_partial.json" if partial else "rules_result.json")).write_text(json.dumps(out, indent=1, default=str))
print(json.dumps({k: (v.get("PASS") if "PASS" in v else v.get("FLAGS")) for k, v in out.items()}))
print(json.dumps(out["rule5"], indent=1)[:3000])
