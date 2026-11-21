"""Inputs for the power note of the final-exam protocol DRAFT: how much the SAME loop varies between runs on the SAME 40 development cells.
CPU only, saved logs only. Run from the repo root:  uv run python research/studies/final_exam_draft_20261118/power_inputs.py
Cohorts = runs of the unchanged fixed loop (pilot C1, round-1 C1, ablation FULL, compaction FULL) on the 10 dev tasks x 4 models; each (cohort, seed) = 40 cells.
Supported = scorer v2.0 as logged (pilot: the v2 re-score). Requests and tokens as logged. No new rule; nothing here is a held-out number."""
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
S = ROOT / "research/studies"
TASKS = {"u3", "p3", "h4", "v2", "e1h_amb_1", "e1h_amb_2", "e1h_abs_1", "e1h_abs_2", "e1h_chg_1", "e1h_chg_2"}
excluded = {r for g in json.loads((S / "small_model_harness_20261115/INFRA_EXCLUDED.json").read_text()).values() for r in g["run_ids"]}
pilot_scores = {r["run_id"]: r["new"] for r in json.loads((S / "residual_failures_20261115/rescore_v2.json").read_text())}
sources = [("pilot C1", "small_model_harness_20261115", "C1", None), ("round1 C1", "build_round1_20261115", "C1", "full"),
           ("ablation FULL", "steady_loop_ablation_20261117", "FULL", "full"), ("compaction FULL", "tool_description_compaction_20261117", "FULL", "full")]
cells = defaultdict(list)
for label, folder, arm, phase in sources:
    for line in (S / folder / "RESULTS_LOG.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["arm"] != arm or r["task"] not in TASKS or (phase and r.get("phase") != phase) or r["run_id"] in excluded:
            continue
        supported = pilot_scores.get(r["run_id"]) if label == "pilot C1" else r["supported_complete"]
        cells[(label, r["seed"])].append(dict(model=r["model"], task=r["task"], supported=bool(supported), requests=r["llm_requests"], tokens=r["input_tokens"] + r["output_tokens"]))
rows = []
for (label, seed), items in sorted(cells.items()):
    rows.append(dict(cohort=label, seed=seed, cells=len(items), supported=sum(i["supported"] for i in items), requests=sum(i["requests"] for i in items), tokens=sum(i["tokens"] for i in items),
                     supported_by_model={m: sum(i["supported"] for i in items if i["model"] == m) for m in sorted({i["model"] for i in items})}))
full40 = [r for r in rows if r["cells"] == 40]
out = dict(cohort_seed_rows=rows,
           n_runs_of_40=len(full40), supported_values=[r["supported"] for r in full40], supported_min=min(r["supported"] for r in full40), supported_max=max(r["supported"] for r in full40),
           supported_mean=round(statistics.mean(r["supported"] for r in full40), 2), supported_sd_cells=round(statistics.stdev(r["supported"] for r in full40), 2),
           requests_values=[r["requests"] for r in full40], requests_cv_percent=round(100 * statistics.stdev(r["requests"] for r in full40) / statistics.mean(r["requests"] for r in full40), 1),
           tokens_values=[r["tokens"] for r in full40], tokens_cv_percent=round(100 * statistics.stdev(r["tokens"] for r in full40) / statistics.mean(r["tokens"] for r in full40), 1))
(Path(__file__).parent / "power_inputs.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "cohort_seed_rows"}, indent=1))
for r in rows:
    print(r["cohort"], r["seed"], r["cells"], r["supported"], r["requests"], r["tokens"])


# ---------------------------------------------------------------- pairwise noise of the same loop on the same cells, and the normal-approximation power table
import itertools
import math

runs = {key: {(i["model"], i["task"]): i for i in items} for key, items in cells.items() if len(items) == 40}
log_ratios, flip_rates = [], []
for a, b in itertools.combinations(runs, 2):
    common = sorted(set(runs[a]) & set(runs[b]))
    for key in common:
        log_ratios.append(math.log(runs[a][key]["requests"] / runs[b][key]["requests"]))
    flips = sum(runs[a][k]["supported"] != runs[b][k]["supported"] for k in common)
    flip_rates.append(flips / len(common))
per_cell_log_ratio_sd = statistics.pstdev(log_ratios)
mean_flip_rate = statistics.mean(flip_rates)          # share of cells whose supported flag differs between two runs of the same loop
# Two independent runs flip a cell with probability 2 q (1 - q) = flip_rate, so the per-cell variance of one run's flag is v = q (1 - q) = flip_rate / 2.
v_dev = mean_flip_rate / 2
z = 2.8  # (1.96 + 0.84): two-sided alpha 0.05, power 0.80


def mde_supported(cells_per_arm, v):
    """Smallest true difference in supported rate detected with 80% power by a two-arm comparison, treating cells as independent (a lower bound on the noise)."""
    return z * math.sqrt(2 * v / cells_per_arm)


def mde_requests_percent(cells_per_arm):
    """Same for the mean log ratio of requests per cell between two arms, using the per-cell log-ratio SD measured between two runs of the same loop (already a two-run difference)."""
    return 100 * (math.exp(z * per_cell_log_ratio_sd / math.sqrt(cells_per_arm)) - 1)


power = dict(per_cell_log_ratio_sd_between_two_runs=round(per_cell_log_ratio_sd, 3), mean_flip_rate_between_two_runs=round(mean_flip_rate, 3), v_dev_per_cell=round(v_dev, 3), table=[])
for label, n in (("dev 40 cells", 40), ("dev 80 cells (this finish split)", 80), ("one model x 110 tasks x 3 seeds", 330), ("4 models x 110 tasks x 1 seed", 440), ("4 models x 110 tasks x 3 seeds", 1320),
                 ("held-out v2 only: 4 models x 76 tasks x 3 seeds", 912), ("Nav2 inspection: 4 models x 24 tasks x 3 seeds", 288), ("Nav2 read-then-act: 4 models x 10 tasks x 3 seeds", 120)):
    power["table"].append(dict(design=label, cells_per_arm=n, mde_supported_pp_at_dev_noise=round(100 * mde_supported(n, v_dev), 1),
                               mde_supported_pp_at_worst_noise_v025=round(100 * mde_supported(n, 0.25), 1), mde_requests_percent=round(mde_requests_percent(n), 1)))
out["power"] = power
(Path(__file__).parent / "power_inputs.json").write_text(json.dumps(out, indent=1))
print(json.dumps(power, indent=1))
