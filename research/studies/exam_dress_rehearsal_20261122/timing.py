"""Timing (no scores): minutes per cell by model and by system, from the queue's full rows, excluding the kill-test period, plus projections.
Cells counted: rows whose episode STARTED after the cutoff (logged_at - wall_seconds >= cutoff, 2026-11-22 10:20 Asia/Taipei). wall_seconds = the worker's whole episode time (fixture start, oracle, model requests, teardown).
Also reported: elapsed time between consecutive row writes inside a model block (adds the queue's own overhead between episodes).
  uv run --no-sync python research/studies/exam_dress_rehearsal_20261122/timing.py RUN_NAME"""
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE.parents[1] / "_artifacts/runs/exam_dress_rehearsal_20261122"
name = sys.argv[1]
Q = RUN / "custody/stage1_rehearsal/queue" / name
rows = [json.loads(l) for l in (Q / "RESULTS_LOG_laptop.jsonl").read_text().splitlines() if l.strip()]
CUT = datetime.fromisoformat("2026-11-22T10:20:00+08:00")
t = lambda r: datetime.strptime(r["logged_at"], "%Y-%m-%dT%H:%M:%S%z")
kept = [r for r in rows if (t(r) - CUT).total_seconds() - r["wall_seconds"] >= 0]
print("rows", len(rows), "after cutoff", len(kept))
by = defaultdict(list)
for r in kept:
    by[(r["model"], r["system"])].append(r["wall_seconds"] / 60)
mean = lambda xs: sum(xs) / len(xs)
table = {}
print("model | system | cells | mean min/cell | min | max")
for k in sorted(by):
    xs = by[k]; table[k] = mean(xs)
    print(k[0], "|", k[1], "|", len(xs), "|", round(mean(xs), 2), "|", round(min(xs), 2), "|", round(max(xs), 2))
for label, idx in (("model", 0), ("system", 1)):
    g = defaultdict(list)
    for k, xs in by.items(): g[k[idx]] += xs
    for k, xs in sorted(g.items()): print(label, k, len(xs), "cells", round(mean(xs), 2), "min/cell")
# gaps between consecutive rows (same order of writing), kept rows only
ordered = sorted(kept, key=t)
gaps = [(t(b) - t(a)).total_seconds() / 60 for a, b in zip(ordered, ordered[1:]) if (t(b) - t(a)).total_seconds() < 1800]
print("mean minutes between consecutive row writes (overhead included):", round(mean(gaps), 2), "n", len(gaps))
overhead = mean(gaps) - mean([r["wall_seconds"] / 60 for r in ordered])
print("queue overhead per cell (gap minus episode time):", round(overhead, 2), "min")
speed = {k: v + overhead for k, v in table.items()}
models = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
m_cost = {m: speed.get((m, "EX-M")) for m in models}; e1_cost = {m: speed.get((m, "E1")) for m in models}
# Tier 1 = 76 tasks x 4 models x {EX-M, E1} x 3 seeds = 1,824 cells; 228 cells per (model, system)
t1 = sum(228 * (m_cost[m] + e1_cost[m]) for m in models)
print("PROJECTION tier 1 (1,824 cells): %.1f hours (EX-M and E1 cells per model at the measured e1h-task speed incl. overhead)" % (t1 / 60))
mean_m, mean_e1 = mean(list(m_cost.values())), mean(list(e1_cost.values()))
# Full queue (7,752 cells, F excluded): tier2 S0+MT 1,824 (47-tool systems: priced as E1), tier3 ablations 2,736 (NO_MENU priced as E1, NO_FINISH and NO_ERRORTEXT as EX-M), tier4 extra models 1,368 (EX-M and E1) priced at the mean of the four core models (those models were not measured)
t2 = 912 * mean_e1 * 2
t3 = 912 * (mean_e1 + 2 * mean_m)
t4 = 684 * (mean_m + mean_e1)
print("PROJECTION tier 2 %.1f h, tier 3 %.1f h, tier 4 %.1f h; full queue %.1f h = %.1f days" % (t2 / 60, t3 / 60, t4 / 60, (t1 + t2 + t3 + t4) / 60, (t1 + t2 + t3 + t4) / 1440))
