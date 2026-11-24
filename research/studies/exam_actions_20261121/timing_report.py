"""Timing report of the Stage 2 timing episodes (PUBLIC dev action tasks). Reads only the run's compact table: wall seconds, system, model, ending class, GPU state. No outcome is read or printed.
Gives seconds per cell by system x model, the projected hours of the exam design for 1, 2 and 3 seeds, and which seed count fits the time available with a safety margin.
  python3 timing_report.py --run-name s2time_... --machine laptop [--pool-size 14] [--hours-available 36] [--margin 0.8] [--speedup 1.0]
`--speedup` rescales to another machine (lab seconds = laptop seconds x speedup). It is an ASSUMPTION unless measured on the lab: the Stage 1 lab ran about 40 s per cell on its smallest model and the
laptop about 87 s, but those were different cells; do not read 0.46 as a measured ratio. Excluded from timing: contended and infrastructure rows (reported as counts)."""
import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYSTEMS, MODELS = 3, 4
OVERHEAD_FACTOR = 1.15       # fixture-session overhead seen in earlier queue runs (13-25% at small blocks, about 14% at 48); an assumption


def summarize(rows):
    usable = [r for r in rows if r.get("ending") not in ("infrastructure", "infrastructure_gpu_contended") and r.get("wall_seconds") is not None]
    by_cell = defaultdict(list)
    for r in usable:
        by_cell[(r["system"], r["model"])].append(r["wall_seconds"])
    table = [dict(system=s, model=m, cells=len(v), mean_s=round(statistics.mean(v), 1), median_s=round(statistics.median(v), 1), max_s=round(max(v), 1)) for (s, m), v in sorted(by_cell.items())]
    models_seen = {r["model"] for r in usable}
    per_model_mean = {m: statistics.mean([r["wall_seconds"] for r in usable if r["model"] == m]) for m in models_seen}
    return dict(table=table, per_model_mean_s={m: round(v, 1) for m, v in sorted(per_model_mean.items())}, usable_rows=len(usable), excluded_infrastructure=sum(r.get("ending") == "infrastructure" for r in rows),
                excluded_contended=sum(r.get("ending") == "infrastructure_gpu_contended" for r in rows), per_model_complete=len(models_seen) == MODELS)


def project(summary, pool_size, speedup=1.0, overhead=OVERHEAD_FACTOR):
    """Hours for the exam design (pool x 3 systems x 4 models x seeds). Needs a timing mean for every model; equal weight per model (the design is balanced)."""
    if not summary["per_model_complete"]:
        return None
    mean_cell = sum(summary["per_model_mean_s"].values()) / MODELS * speedup * overhead
    return {seeds: dict(cells=pool_size * SYSTEMS * MODELS * seeds, hours=round(pool_size * SYSTEMS * MODELS * seeds * mean_cell / 3600, 1)) for seeds in (1, 2, 3)}


def recommend(projection, hours_available, margin):
    if projection is None:
        return None
    fits = [seeds for seeds, p in projection.items() if p["hours"] <= hours_available * margin]
    return max(fits) if fits else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--machine", required=True)
    parser.add_argument("--compact-root")
    parser.add_argument("--pool-size", type=int, default=14)
    parser.add_argument("--hours-available", type=float, default=36.0)
    parser.add_argument("--margin", type=float, default=0.8)
    parser.add_argument("--speedup", type=float, default=1.0)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    root = Path(args.compact_root) if args.compact_root else HERE.parent / "final_exam_draft_20261118" / "exam_results"
    path = root / args.run_name / f"compact_{args.machine}.jsonl"
    if not path.exists():
        print(f"no compact table at {path}", file=sys.stderr)
        return 2
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    summary = summarize(rows)
    projection = project(summary, args.pool_size, args.speedup)
    report = dict(run=args.run_name, machine=args.machine, speedup_assumed=args.speedup, overhead_factor_assumed=OVERHEAD_FACTOR, summary=summary, projection_hours=projection,
                  hours_available=args.hours_available, margin=args.margin, seeds_that_fit=recommend(projection, args.hours_available, args.margin),
                  note="projection uses the PUBLIC dev timing cells; held-out tasks may differ (more steps, retries). Hours are wall-clock for the whole queue, excluding fixture failures and re-runs.")
    print(json.dumps(report, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
