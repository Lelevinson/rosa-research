"""Frozen analysis of the Stage 1 primary comparison (DRAFT freeze package; hash recorded in analyze_primary.sha256 before any held-out result exists).

Specification: final_exam_draft_20261118/PROTOCOL_DRAFT.md revision 4, sections 5, 5b and 9c items 4 and 8. Success criteria text: SUCCESS_AND_INVALIDATION_DRAFT.md.

  uv run python research/studies/final_exam_draft_20261118/freeze_package_20261121/analyze_primary.py \
      --rows RESULTS_LOG_laptop.jsonl [more files] --primary EX-M --baseline E1 --out OUTPUT_PREFIX
      [--machine laptop] [--system-field system] [--models m1 m2 ...] [--planned-pairs 912] [--draws 10000] [--bootstrap-seed 20261122]

What it computes (all on the PAIRED cells (pool, task, model, seed) in which both systems have a row, restricted to the 4 core models; every assigned episode is a row, capped, failed and
unscored episodes included; nothing is dropped because of its outcome):
  1. supported-complete difference, primary minus baseline, in percentage points: 100 * (sum of supported(M) - sum of supported(E1)) / number of pairs.
  2. token ratio: total (input + output) tokens of M over total tokens of E1 on the same pairs.
  3. 95% intervals by a cluster bootstrap over TASKS (a task carries all its models and seeds), `--draws` resamples with Python's `random.Random(--bootstrap-seed)`, percentile interval
     (lower = sorted[floor(0.025 d)], upper = sorted[d - 1 - floor(0.025 d)]).
  4. Verdict, fixed in advance: (a) lower bound of the difference ABOVE -5 points, and (b) upper bound of the token ratio BELOW 0.80; both must hold.
  5. Invalidation (protocol section 9c item 8): share of rows with ending "infrastructure" (or zero requests) per system; more than 5% flags that system in every table; more than 10% of all
     rows reports the exam as COMPROMISED and the verdict is withheld. (Proxy: the queue's class (a) / (c) cells are the rows whose ending is "infrastructure".)
  6. Secondary, labelled so: per-model rows; the same comparison without pairs in which either episode is capped (iteration cap, backend error, timeout, no answer, validation abort);
     the name fix scored both ways (M's own rows carry `supported_raw`, the raw answer's score; the E1 side is unaffected) and the group of rewritten answers.
Strata are never pooled: if the rows come from more than one machine, `--machine` is required. Duplicate cells are an error. The output states INTERIM unless the number of pairs equals --planned-pairs.
The script reads aggregate row fields only (supported flag, token counts, ending, model, seed, opaque task id): never an answer, a trace or a task text.
"""
import argparse
import hashlib
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

# ---- fixed in advance (draft section 9c, owner approval 2026-11-21); changing any of them is a protocol revision
MARGIN_POINTS = -5.0          # (a) lower bound of supported(M) - supported(E1) must be ABOVE this
TOKEN_RATIO_BAR = 0.80        # (b) upper bound of the token ratio M / E1 must be BELOW this
INFRA_SYSTEM_FLAG = 0.05      # share of infrastructure rows that flags a system
INFRA_OVERALL_COMPROMISED = 0.10
CORE_MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
CAPPED_ENDINGS = {"iteration_cap", "backend_error", "timeout", "no_answer", "validation_abort"}
DEFAULT_DRAWS = 10000
DEFAULT_BOOTSTRAP_SEED = 20261122


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_rows(paths, system_field, machine):
    rows, machines = [], set()
    for path in paths:
        for number, line in enumerate(Path(path).read_text().splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if system_field not in row or "task" not in row or "model" not in row or "seed" not in row:
                continue  # a note line, not an episode row
            if machine is not None and row.get("machine") != machine:
                continue
            machines.add(row.get("machine"))
            row["_system"] = row[system_field]
            rows.append(row)
    if machine is None and len(machines - {None}) > 1:
        raise SystemExit(f"rows from several machines {sorted(m for m in machines if m)}: pass --machine; strata are never pooled")
    return rows


def flag(row):
    return bool(row["supported_complete"] if "supported_complete" in row else row.get("supported"))


def tokens(row):
    return (row.get("input_tokens") or 0) + (row.get("output_tokens") or 0)


def is_infrastructure(row):
    if "ending" in row:
        return row["ending"] == "infrastructure"
    return (row.get("llm_requests") or row.get("requests") or 0) == 0


def is_capped(row):
    return row.get("ending") in CAPPED_ENDINGS


def percentile_interval(values, draws):
    values = sorted(values)
    cut = int(0.025 * draws)
    return values[cut], values[len(values) - 1 - cut]


def bootstrap(pairs, draws, seed, value_primary=None):
    """pairs: list of (task_key, primary_row, baseline_row). Returns dict with point estimates and intervals. value_primary: optional function giving the primary supported flag (name fix raw)."""
    value_primary = value_primary or flag
    by_task = defaultdict(lambda: [0, 0, 0, 0, 0])  # pairs, supported M, supported E, tokens M, tokens E
    for key, primary, baseline in pairs:
        cell = by_task[key]
        cell[0] += 1
        cell[1] += value_primary(primary)
        cell[2] += flag(baseline)
        cell[3] += tokens(primary)
        cell[4] += tokens(baseline)
    tasks = list(by_task.values())
    n_pairs = sum(t[0] for t in tasks)
    total = [sum(t[i] for t in tasks) for i in range(5)]
    result = dict(pairs=n_pairs, tasks=len(tasks), supported_primary=total[1], supported_baseline=total[2], tokens_primary=total[3], tokens_baseline=total[4],
                  difference_points=100 * (total[1] - total[2]) / n_pairs if n_pairs else None, token_ratio=total[3] / total[4] if total[4] else None, difference_interval=None, ratio_interval=None,
                  draws=draws, ratio_draws_skipped=0)
    if len(tasks) < 2:
        return result
    rng = random.Random(seed)
    differences, ratios, skipped = [], [], 0
    for _ in range(draws):
        picked = rng.choices(tasks, k=len(tasks))
        n = sum(t[0] for t in picked)
        differences.append(100 * (sum(t[1] for t in picked) - sum(t[2] for t in picked)) / n)
        denominator = sum(t[4] for t in picked)
        if denominator:
            ratios.append(sum(t[3] for t in picked) / denominator)
        else:
            skipped += 1
    result["difference_interval"] = percentile_interval(differences, draws)
    result["ratio_interval"] = percentile_interval(ratios, len(ratios)) if ratios else None
    result["ratio_draws_skipped"] = skipped
    return result


def verdict(stat):
    """The pass/fail rule of section 9c item 4. Returns (text, a_holds, b_holds)."""
    if stat["difference_interval"] is None or stat["ratio_interval"] is None:
        return "NOT EVALUABLE (fewer than 2 tasks or an empty token denominator)", None, None
    a = stat["difference_interval"][0] > MARGIN_POINTS
    b = stat["ratio_interval"][1] < TOKEN_RATIO_BAR
    if a and b:
        return "PASS: claim supported (both criteria hold)", a, b
    failed = ", ".join(name for name, ok in (("(a) correctness", a), ("(b) cost", b)) if not ok)
    return f"FAIL: claim not supported, {failed} not met", a, b


def analyse(rows, primary, baseline, models, draws, seed, planned_pairs):
    by_system = defaultdict(list)
    cells = defaultdict(dict)
    for row in rows:
        system = row["_system"]
        key = (row.get("pool", "dev"), row["task"], row["model"], row["seed"])
        if system in cells[key]:
            raise SystemExit(f"duplicate episode for cell {key[1:]} of system {system}: a cell may appear once per system")
        cells[key][system] = row
        by_system[system].append(row)
    core = [(k, v) for k, v in cells.items() if k[2] in models]
    paired = [(k, v[primary], v[baseline]) for k, v in core if primary in v and baseline in v]
    unpaired = sum(1 for k, v in core if (primary in v) != (baseline in v))
    task_key = lambda k: (k[0], k[1])
    pairs = [((task_key(k)), p, b) for k, p, b in paired]

    out = dict(primary=primary, baseline=baseline, models=models, planned_pairs=planned_pairs, unpaired_cells=unpaired)
    out["status"] = "FINAL" if planned_pairs and len(pairs) == planned_pairs else f"INTERIM ({len(pairs)} pairs" + (f" of {planned_pairs} planned)" if planned_pairs else ")")

    infra = {}
    for system, items in by_system.items():
        n = len(items)
        share = sum(is_infrastructure(r) for r in items) / n if n else 0.0
        infra[system] = dict(rows=n, infrastructure=sum(is_infrastructure(r) for r in items), share=share, flagged=share > INFRA_SYSTEM_FLAG)
    total_rows = sum(v["rows"] for v in infra.values())
    overall = sum(v["infrastructure"] for v in infra.values()) / total_rows if total_rows else 0.0
    out["invalidation"] = dict(per_system=infra, overall_share=overall, compromised=overall > INFRA_OVERALL_COMPROMISED)

    main = bootstrap(pairs, draws, seed)
    text, a, b = verdict(main)
    if out["invalidation"]["compromised"]:
        text = "WITHHELD: the exam is reported as compromised (more than 10% infrastructure cells) and is not used for the primary claim"
    out["primary_comparison"] = dict(main, verdict=text, criterion_a_holds=a, criterion_b_holds=b, margin_points=MARGIN_POINTS, token_ratio_bar=TOKEN_RATIO_BAR)

    out["per_model_secondary"] = {m: bootstrap([p for p in pairs if p[1]["model"] == m], draws, seed) for m in models if any(p[1]["model"] == m for p in pairs)}
    uncapped = [p for p in pairs if not is_capped(p[1]) and not is_capped(p[2])]
    out["without_capped_secondary"] = dict(bootstrap(uncapped, draws, seed), removed_pairs=len(pairs) - len(uncapped)) if any("ending" in p[1] for p in pairs) else None

    have_raw = all("supported_raw" in p[1] for p in pairs) and bool(pairs)
    if have_raw:
        raw = bootstrap(pairs, draws, seed, value_primary=lambda r: bool(r["supported_raw"]))
        flips_up = sum(flag(p[1]) and not p[1]["supported_raw"] for p in pairs)
        flips_down = sum(p[1]["supported_raw"] and not flag(p[1]) for p in pairs)
        out["name_fix_both_ways"] = dict(rewritten=dict(main, label="primary: the answer M submitted (name fix applied)"), raw=dict(raw, label="the same episodes scored on the raw answer (name fix off)"),
                                         rewritten_answers=sum(bool(p[1].get("name_fix_changed")) for p in pairs), flips_unsupported_to_supported=flips_up, flips_supported_to_unsupported=flips_down)
    else:
        out["name_fix_both_ways"] = "not available: the primary rows carry no `supported_raw` field (the raw-answer score)"
    return out


def interval_text(interval, digits):
    return "n/a" if interval is None else f"{interval[0]:+.{digits}f} to {interval[1]:+.{digits}f}" if digits == 1 else f"{interval[0]:.3f} to {interval[1]:.3f}"


def stat_line(label, s):
    return (f"| {label} | {s['pairs']} | {s['tasks']} | {s['supported_primary']} / {s['supported_baseline']} | "
            f"{'n/a' if s['difference_points'] is None else format(s['difference_points'], '+.1f')} | {interval_text(s['difference_interval'], 1)} | "
            f"{'n/a' if s['token_ratio'] is None else format(s['token_ratio'], '.3f')} | {interval_text(s['ratio_interval'], 3)} |")


def markdown(result, meta):
    p = result["primary_comparison"]
    head = "| scope | pairs | tasks | supported (primary / baseline) | difference (points) | 95% interval (points) | token ratio | 95% interval |\n|---|---:|---:|---|---:|---|---:|---|"
    lines = [f"# Primary comparison {result['primary']} against {result['baseline']} ({result['status']})", "",
             f"Generated by `analyze_primary.py` (script SHA-256 `{meta['script_sha256']}`), {meta['draws']} bootstrap draws, bootstrap seed {meta['bootstrap_seed']}, machine filter {meta['machine']}. "
             "Aggregate fields only.", "",
             f"**Verdict: {p['verdict']}.** Criteria: (a) lower bound of the supported difference above {MARGIN_POINTS:+.0f} points: "
             f"{p['criterion_a_holds']}; (b) upper bound of the token ratio below {TOKEN_RATIO_BAR}: {p['criterion_b_holds']}.", "",
             "## Primary (core models pooled, all assigned episodes)", head, stat_line("pooled", p), ""]
    if result["status"] != "FINAL":
        lines += ["*Not the final population: interim numbers are descriptive and are not the primary claim.*", ""]
    if result["unpaired_cells"]:
        lines += [f"*{result['unpaired_cells']} core-model cells have a row for only one of the two systems and are not in the paired statistics.*", ""]
    lines += ["## Per model (secondary)", head] + [stat_line(m, s) for m, s in result["per_model_secondary"].items()] + [""]
    if result["without_capped_secondary"]:
        lines += ["## Without pairs that contain a capped episode (secondary)", head, stat_line(f"pooled ({result['without_capped_secondary']['removed_pairs']} pairs removed)", result["without_capped_secondary"]), ""]
    nf = result["name_fix_both_ways"]
    if isinstance(nf, dict):
        lines += ["## Name fix scored both ways (secondary)", head, stat_line("rewritten answer (as submitted)", nf["rewritten"]), stat_line("raw answer", nf["raw"]),
                  "", f"Answers rewritten: {nf['rewritten_answers']}; episodes flipped unsupported to supported by the rewrite: {nf['flips_unsupported_to_supported']}; supported to unsupported: {nf['flips_supported_to_unsupported']}.", ""]
    else:
        lines += ["## Name fix scored both ways (secondary)", nf, ""]
    inv = result["invalidation"]
    lines += ["## Invalidation check (infrastructure rows)", "| system | rows | infrastructure | share | flagged (> 5%) |", "|---|---:|---:|---:|---|"]
    lines += [f"| {s} | {v['rows']} | {v['infrastructure']} | {100 * v['share']:.1f}% | {v['flagged']} |" for s, v in sorted(inv["per_system"].items())]
    lines += ["", f"Overall infrastructure share {100 * inv['overall_share']:.1f}% (compromised above 10%: {inv['compromised']}).", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", nargs="+", required=True)
    parser.add_argument("--primary", default="EX-M")
    parser.add_argument("--baseline", default="E1")
    parser.add_argument("--system-field", default="system")
    parser.add_argument("--models", nargs="+", default=CORE_MODELS)
    parser.add_argument("--machine")
    parser.add_argument("--planned-pairs", type=int, default=0, help="pairs of the full design (76 tasks x 4 models x 3 seeds = 912); 0 = unknown")
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument("--bootstrap-seed", type=int, default=DEFAULT_BOOTSTRAP_SEED)
    parser.add_argument("--out", required=True, help="output prefix: writes PREFIX.json and PREFIX.md")
    args = parser.parse_args(argv)
    rows = load_rows(args.rows, args.system_field, args.machine)
    if not rows:
        raise SystemExit("no episode rows")
    result = analyse(rows, args.primary, args.baseline, args.models, args.draws, args.bootstrap_seed, args.planned_pairs)
    meta = dict(script_sha256=sha256(__file__), inputs={str(p): sha256(p) for p in args.rows}, draws=args.draws, bootstrap_seed=args.bootstrap_seed, machine=args.machine or "any (single stratum in the rows)",
                margin_points=MARGIN_POINTS, token_ratio_bar=TOKEN_RATIO_BAR)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(str(args.out) + ".json").write_text(json.dumps(dict(meta=meta, result=result), indent=1, sort_keys=True) + "\n")
    Path(str(args.out) + ".md").write_text(markdown(result, meta))
    print(result["primary_comparison"]["verdict"], f"({result['status']}; difference {result['primary_comparison']['difference_points']}, token ratio {result['primary_comparison']['token_ratio']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
