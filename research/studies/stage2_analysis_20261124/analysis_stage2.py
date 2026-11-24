"""Stage 2 analysis (2026-11-24), written before the freeze and listed in the Stage 2 manifest. ANALYSIS ONLY: reads the logs of ONE machine, runs no model, edits nothing.

It reuses the Stage 1 analysis revision 3 (`analysis_rev3.py`: whole-plan validation of the full/compact join, plan-derived denominators, one snapshot read once, full-row field check, individual
quarantine adjudication) and the frozen `analyze_primary.py` statistics, and adds what Stage 2 needs:
  * Comparisons (protocol section 6): XM against XE1x (PRIMARY, with the worst-case-for-M sensitivity), XM against XS0x (same, descriptive), XE1x against XS0x (primary statistics only; the
    worst case for M is meaningless without M). Each comparison applies the owner's quarantine rule on its own pairs: paired exclusion is primary (a pair = task, model, seed), skipped cells
    are reported per system x model x cause, and the denominator used is shown. Machines are never pooled.
  * Ending classes per system x model, including the two Stage 2 classes `unscored` (class (c): fixture or independent reader lost after a request) and `unresolved_motion` (class (b)).
  * UNSCORED rule of the protocol: results are reported with unscored cells COUNTED AS FAILURE (the primary: their rows carry supported = false) and, as a labelled secondary, with every pair that
    contains an unscored cell EXCLUDED. A system with more than 3% unscored cells STOPS the study for an owner decision; more than 5% class (a) + (c) flags the system; more than 10% overall
    marks the study compromised. Shares are of the system's planned cells.
  * The claim counter 2x2 (claimed arrival x arrived) per system x model, read from the full rows' `claim_audit` (derived booleans, no task content), with `claimed_but_not_arrived` totals.
Commands (same gating as Stage 1): `check` prints counts and states only and never reads an outcome; `analyze` needs `--out` and `--result-look-approved` (the owner opening the result look).
  python3 analysis_stage2.py check   --spec SPEC --run-name RUN --machine lab --machines lab:1 [--tier stage2]
  python3 analysis_stage2.py analyze (same) --out PREFIX --result-look-approved [--draws 10000]
Exit codes: 0 done; 2 integrity or input problem; 3 tier not yet analysable."""
import argparse
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(STUDIES / "exam_actions_20261121"))
sys.path.insert(0, str(STUDIES / "final_exam_draft_20261118" / "exam_queue"))
import claim_counter  # noqa: E402
import run_actions_queue  # noqa: E402,F401  (registers XM/XE1/XS0 and the two Stage 2 ending classes in queue_core)
import queue_core as Q  # noqa: E402

_spec = importlib.util.spec_from_file_location("analysis_rev3", STUDIES / "analysis_rev3_20261124" / "analysis_rev3.py")
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

TIER = "stage2"
COMPARISONS = [("XM", "XE1"), ("XM", "XS0"), ("XE1", "XS0")]     # (primary, baseline); the first is the protocol's primary comparison
UNSCORED_STOP, CLASS_AC_FLAG, OVERALL_COMPROMISED = 0.03, 0.05, 0.10


def ending_table(snapshot, blind=False):
    """Cells per system x model x ending class. `blind` (the `check` command) merges `supported` and `unsupported` into `answered`: that split is an outcome."""
    merge = (lambda e: "answered" if e in ("supported", "unsupported") else e) if blind else (lambda e: e)
    counts = Counter((r["system"], r["model"], merge(r["ending"])) for r in snapshot["compact"])
    return [dict(system=s, model=m, ending=e, cells=n) for (s, m, e), n in sorted(counts.items())]


def validity(snapshot, states, tier):
    """Shares of the system's PLANNED cells. (a) = rows with ending `infrastructure`; (c) = `unscored`. Skipped cells are reported separately and are not (a) or (c)."""
    planned = Counter(c["system"] for c in snapshot["plan"] if c["tier"] == tier)
    rows = Counter((r["system"], r["ending"]) for r in snapshot["compact"] if r["tier"] == tier)
    per_system, total_ac, total = {}, 0, sum(planned.values())
    for system, n in sorted(planned.items()):
        a, c = rows[(system, "infrastructure")], rows[(system, "unscored")]
        total_ac += a + c
        per_system[system] = dict(planned_cells=n, class_a=a, class_c_unscored=c, share_a_plus_c=round((a + c) / n, 4), flagged=(a + c) / n > CLASS_AC_FLAG, stop_for_owner=c / n > UNSCORED_STOP)
    return dict(per_system=per_system, overall_share_a_plus_c=round(total_ac / total, 4) if total else 0.0, compromised=bool(total) and total_ac / total > OVERALL_COMPROMISED)


def claim_tables(snapshot, tier):
    """2x2 per system x model from the full rows' claim_audit. Rows without an audit (no scored answer) count as `no_audit`."""
    audits = defaultdict(list)
    no_audit = Counter()
    for full in snapshot["full_rows"]:
        if full.get("tier") != tier:
            continue
        audit = (full.get("exposure") or {}).get("claim_audit")
        if audit is None:
            no_audit[(full["system"], full["model"])] += 1
        else:
            audits[(full["system"], full["model"])].append(audit)
    keys = sorted(set(audits) | set(no_audit))
    return [dict(system=s, model=m, no_audit=no_audit[(s, m)], claimed_but_not_arrived=sum(a["claimed_but_not_arrived"] for a in audits[(s, m)]), **claim_counter.table(audits[(s, m)])) for s, m in keys]


def comparison_blocks(snapshot, tier, A, models, draws, seed):
    """Per comparison: assessment (counts, skipped cells with causes, pairs excluded, denominator) and, if analysable, the statistics."""
    blocks = {}
    unscored_cells = {full["cell_id"] for full in snapshot["full_rows"] if full.get("ending_override") == "unscored"}
    for primary, baseline in COMPARISONS:
        report = R.assess(snapshot, tier, primary, baseline, models, 0)
        block = dict(report=R.public(report))
        if report["status"] == "analysable":
            results = R.compute(snapshot, report, A, primary, baseline, models, draws, seed, Q)
            if primary != "XM":
                for group in results.values():
                    group.pop("sensitivity", None)           # the worst case is defined for M only
            internal = report["_internal"]
            with_unscored = {p for p, v in internal["pairs"].items() if any(c["id"] in unscored_cells for c in v.values())}
            secondary = None
            if with_unscored:
                compact_of = {r["cell"]: r for r in snapshot["compact"]}
                opaque = R.opaque_factory(snapshot["salt"])
                kept = {p: v for p, v in internal["pairs"].items() if p not in internal["excluded"] and p not in with_unscored}
                rows = [dict(compact_of[opaque(c["id"])], _system=c["system"]) for v in kept.values() for c in v.values()]
                secondary = A.analyse(rows, primary, baseline, models, draws, seed, len(kept)) if rows else None
            block["results"] = results["all"]
            block["without_unscored_pairs_secondary"] = dict(pairs_removed=len(with_unscored - internal["excluded"]), analysis=secondary)
        blocks[f"{primary}_vs_{baseline}"] = block
    return blocks


def stage2_report(snapshot, tier, A, models, draws, seed, with_outcomes):
    problems = R.validate(snapshot)
    if problems:
        return dict(status="integrity_problem", problems=problems)
    states, _ = R.cell_states(snapshot)
    out = dict(machine=snapshot["machine"], tier=tier, input_sha256=snapshot["input_sha256"], validity=validity(snapshot, states, tier), ending_classes=ending_table(snapshot, blind=not with_outcomes),
               cell_states=dict(Counter(states[c["id"]] for c in snapshot["plan"] if c["tier"] == tier)))
    if not with_outcomes:
        reports = {f"{p}_vs_{b}": R.public(R.assess(snapshot, tier, p, b, models, 0)) for p, b in COMPARISONS}
        out.update(status="check", comparisons=reports)
        out["status"] = "analysable" if all(r["status"] == "analysable" for r in reports.values()) else "not_analysable_pending_cells"
        return out
    out["claim_counter"] = claim_tables(snapshot, tier)
    out["comparisons"] = comparison_blocks(snapshot, tier, A, models, draws, seed)
    out["status"] = "analysed"
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["check", "analyze"])
    parser.add_argument("--spec", required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--machine", required=True)
    parser.add_argument("--machines", required=True)
    parser.add_argument("--tier", default=TIER)
    parser.add_argument("--models", nargs="+")
    parser.add_argument("--artifacts")
    parser.add_argument("--compact")
    parser.add_argument("--salt")
    parser.add_argument("--out")
    parser.add_argument("--draws", type=int, default=10000)
    parser.add_argument("--result-look-approved", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "analyze" and not (args.result_look_approved and args.out):
        print("analyze needs --out and --result-look-approved (the owner's opening of the result look)", file=sys.stderr)
        return 2
    try:
        A = R.load_analyzer()
        models = args.models or A.CORE_MODELS
        snapshot = R.load_snapshot(Q, args.spec, args.run_name, args.machine, args.machines, args.artifacts, args.compact, args.salt)
        if args.command == "analyze":
            report = R.assess(snapshot, args.tier, "XM", "XE1", models, 0)
            if report["status"] == "integrity_problem" or report["status"] != "analysable":
                print(json.dumps(R.public(report), indent=1, sort_keys=True))
                return 2 if report["status"] == "integrity_problem" else 3
        result = stage2_report(snapshot, args.tier, A, models, args.draws, A.DEFAULT_BOOTSTRAP_SEED, args.command == "analyze")
    except R.IntegrityError as error:
        print(json.dumps(dict(status="integrity_problem", problems=[str(error)])))
        return 2
    text = json.dumps(result, indent=1, sort_keys=True, default=str)
    if args.command == "check":
        print(text)
        return 2 if result["status"] == "integrity_problem" else (0 if result["status"] == "analysable" else 3)
    if result["status"] == "integrity_problem":
        print(text)
        return 2
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out + ".json").write_text(text + "\n")
    print(f"wrote {args.out}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
