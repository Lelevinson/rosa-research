"""Task-clustered sizing for the primary comparison (exam draft section 7b). CPU only, saved dev logs only.
  nice uv run python research/studies/final_exam_draft_20261118/power_clustered.py
Dev analogue of "M vs E1": the fixed loop (pilot arm C1 = M proxy) against E1 (fairness study), same 10 dev tasks x 4 models x 2 seeds. The task is the unit:
per-task paired differences are formed over the 8 (model, seed) cells of each task; their spread between tasks gives the standard error for N tasks.
Noise model: Var(task mean difference) = sigma_between^2 + sigma_within^2 / cells_per_task (sigma_within from the per-cell paired differences, sigma_between by subtraction, floored at 0).
Caveat: E1 and C1 ran in different sessions, so the per-cell pairing is by (task, model, seed) only; the within-task variance includes session noise (conservative)."""
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research/studies/candidate_counts_20261118"))
import count_candidates as C  # noqa: E402

PILOT_SCORES = {r["run_id"]: r["new"] for r in json.loads((ROOT / "research/studies/residual_failures_20261115/rescore_v2.json").read_text())}
cells = {"E1": {}, "M": {}}
for study, row in C.load_population():
    if (study, row["arm"]) not in (("fairness", "E1"), ("pilot", "C1")):
        continue
    key = (row["task"], row["model"], row["seed"])
    supported = row["supported_complete"] if "supported_complete" in row else PILOT_SCORES[row["run_id"]]  # pilot rows carry no flag; scorer v2.0 re-score as in the candidate counts
    value = (bool(supported), row["input_tokens"] + row["output_tokens"], row["llm_requests"])
    cells["E1" if study == "fairness" else "M"][key] = value
keys = sorted(set(cells["E1"]) & set(cells["M"]))
tasks = sorted({k[0] for k in keys})
by_task = defaultdict(list)
for k in keys:
    by_task[k[0]].append(k)
n_cells = statistics.mean(len(v) for v in by_task.values())
diff = {t: [cells["M"][k][0] - cells["E1"][k][0] for k in by_task[t]] for t in tasks}
task_mean = {t: statistics.mean(v) for t, v in diff.items()}
sigma_w2 = statistics.mean(statistics.pvariance(v) for v in diff.values())
var_tasks = statistics.pvariance(list(task_mean.values()))
sigma_b2 = max(0.0, var_tasks - sigma_w2 / n_cells)
z = 1.96 + 0.84  # two-sided 5%, 80% power


def mde(n_tasks, cells_per_task):
    return z * math.sqrt((sigma_b2 + sigma_w2 / cells_per_task) / n_tasks)


# cost: log ratio of total tokens per task (sums over the task's cells)
log_ratio = {t: math.log(sum(cells["M"][k][1] for k in by_task[t]) / sum(cells["E1"][k][1] for k in by_task[t])) for t in tasks}
sd_log = statistics.pstdev(list(log_ratio.values()))
pooled_ratio = sum(cells["M"][k][1] for k in keys) / sum(cells["E1"][k][1] for k in keys)
req_ratio = sum(cells["M"][k][2] for k in keys) / sum(cells["E1"][k][2] for k in keys)
rng = random.Random(20261119)
boot = []
for _ in range(5000):
    sample = [rng.choice(tasks) for _ in tasks]
    num = sum(cells["M"][k][1] for t in sample for k in by_task[t]); den = sum(cells["E1"][k][1] for t in sample for k in by_task[t])
    boot.append(num / den)
boot.sort()
out = dict(source="fairness E1 vs pilot C1 (fixed loop), same 10 dev tasks, 4 models, 2 seeds", cells=len(keys), tasks=len(tasks), cells_per_task=n_cells,
           supported=dict(M=sum(cells["M"][k][0] for k in keys), E1=sum(cells["E1"][k][0] for k in keys), pooled_difference_points=round(100 * statistics.mean(d for v in diff.values() for d in v), 2),
                          sd_between_tasks_of_task_mean_diff=round(math.sqrt(var_tasks), 4), sigma_within=round(math.sqrt(sigma_w2), 4), sigma_between=round(math.sqrt(sigma_b2), 4)),
           detectable_supported_difference_points={f"{n} tasks x {c} cells per task": round(100 * mde(n, c), 1) for n, c in [(76, 12), (76, 8), (76, 4), (110, 12), (24, 12), (10, 12), (10, 8)]},
           cost=dict(tokens_ratio_M_over_E1=round(pooled_ratio, 3), requests_ratio=round(req_ratio, 3), bootstrap_95_over_tasks_tokens_ratio=[round(boot[125], 3), round(boot[4874], 3)],
                     sd_of_task_log_ratio=round(sd_log, 3), detectable_tokens_ratio_76_tasks=[round(math.exp(-z * sd_log / math.sqrt(76)), 3), round(math.exp(z * sd_log / math.sqrt(76)), 3)],
                     per_task_ratio={t: round(math.exp(v), 3) for t, v in log_ratio.items()}),
           note="Dev analogue only. The held-out tasks' between-task spread is unknown; 10 tasks give a very rough estimate of it. Normal approximation; cluster bootstrap on 10 tasks is illustrative, not a CI to quote.")
(HERE / "power_clustered.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
