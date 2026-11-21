"""Stage 1c step 1 tables: A0 Qwen request labels and excess decomposition (offline)."""
import collections, json, re, sys
from pathlib import Path
d = Path(__file__).resolve().parent
eps = json.loads((d / "stage1c_a0_auto.json").read_text())
manual = json.loads((d / "manual_labels_1c.json").read_text())
out = ["# Stage 1c step 1: relabel of the 12 Stage 1a Qwen A0 episodes\n",
       "Codebook: `CODEBOOK.md`. Labels are the rule first pass plus the manual overrides in `manual_labels_1c.json` (5 overrides). "
       "'Avoidable' = RED, REC, or DEP whose arguments were available at least one request earlier (batchable). 'Needed' = DEP that depends on the preceding result, or JUDG.\n",
       "## Per request (trace line = `model_end` line)\n", "| episode | task | req | line | label | batchable | calls |", "|---|---|---:|---:|---|---|---|"]
summary = collections.defaultdict(lambda: collections.Counter())
rows_by_task = collections.defaultdict(list)
for rows in sorted(eps, key=lambda r: (r[0]["task"], r[0]["episode"])):
    for r in rows:
        k = r["request_index"]
        if k == 1:
            continue
        key = f"{r['episode']}#{k}"
        label = manual[key]["label"] if key in manual else r["auto_label"]
        r["final_label"] = label
        calls = re.sub(r"/diag_(demo|turtle)/", "/", r["calls"].replace("ros2_", ""))[:110]
        out.append(f"| {r['episode']} | {r['task']} | {k} | {r['trace_line']} | {label}{' (own error)' if r['own_call_error'] else ''} | {r['batchable']} | {calls} |")
    rows_by_task[rows[0]["task"]].append(rows)
out += ["\n## Excess decomposition per task (both repeats)\n",
        "Excess = requests - strict floor. Avoidable requests = RED + REC + batchable DEP. If avoidable equals the excess, none of the excess is dependency-driven.\n",
        "| task | episodes | floor | requests (each) | excess (each) | RED | REC | DEP batchable | DEP not batchable | JUDG | avoidable (each episode) |", "|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|"]
for task, group in sorted(rows_by_task.items()):
    floor = group[0][0]["floor_strict"]
    cnt = collections.Counter(); avoid_each = []; req_each = []
    for rows in group:
        a = 0
        for r in rows[1:]:
            lab = r["final_label"]
            if lab == "FIN": continue
            if lab == "DEP":
                cnt["DEP batchable" if r["batchable"] else "DEP not batchable"] += 1
                a += bool(r["batchable"])
            else:
                cnt[lab] += 1
                a += lab in ("RED", "REC")
        avoid_each.append(a); req_each.append(len(rows))
    out.append(f"| {task} | {len(group)} | {floor} | {req_each} | {[n - floor for n in req_each]} | {cnt['RED']} | {cnt['REC']} | {cnt['DEP batchable']} | {cnt['DEP not batchable']} | {cnt['JUDG']} | {avoid_each} |")
(d / "STAGE1C_RELABEL.md").write_text("\n".join(out) + "\n")
print("\n".join(out[-12:]))
