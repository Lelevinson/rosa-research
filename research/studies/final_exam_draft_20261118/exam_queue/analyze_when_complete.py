"""The only way the primary comparison is run (rev 2, owner decision D1 and D4): runs the frozen `analyze_primary.py` for a tier ONLY when `integrity_look` says the tier is COMPLETE.
An incomplete tier prints "X of Y cells done; no comparison" and exits with code 3 without reading an outcome. For a complete tier the analysis is run twice and the two results are kept as separate
groups (D4): `<out>_all` = every row; `<out>_without_prestart` = without the pairs that contain a pre-start cell (the two cells run before revision 1; they stay results of their cells, same frozen
arms, tasks and scorer, and are never re-run). The pre-start cells are listed by cell id in PRESTART_CELLS.json in the run's artifact folder (written by the owner or Codex from the custody log).
  python3 analyze_when_complete.py --spec SPEC --run-name RUN --tier TIER --primary EX-M --baseline E1 --out PREFIX [--machine laptop --machines laptop:1] [--models ...] [--artifacts DIR --compact DIR]"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import integrity_look as L  # noqa: E402

ANALYZER = HERE.parent / "freeze_package_20261121" / "analyze_primary.py"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--tier", required=True)
    parser.add_argument("--primary", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--machine", default="all")
    parser.add_argument("--machines", default="all:1")
    parser.add_argument("--models", nargs="+")
    parser.add_argument("--artifacts")
    parser.add_argument("--compact")
    parser.add_argument("--analyzer", default=str(ANALYZER))
    args = parser.parse_args()
    report = L.look(args.spec, args.run_name, args.machine, args.machines, args.artifacts, args.compact)
    info = report["tiers"].get(args.tier)
    if info is None:
        print(f"unknown tier {args.tier!r}", file=sys.stderr)
        return 2
    if not info["COMPLETE"]:
        print(json.dumps(dict(tier=args.tier, report_as=info["report_as"], COMPLETE=False, analysis="not run")))
        return 3
    spec = L.Q.load_spec(args.spec)
    cells = [c for c in L.Q.my_cells(L.Q.build_cells(spec), args.machine, L.Q.parse_machines(args.machines)) if c["tier"] == args.tier]
    salt = json.loads(L.Q.LOCAL_CONFIG.read_text()).get("salt", "unsalted") if L.Q.LOCAL_CONFIG.exists() else "unsalted"
    opaque = lambda text: hashlib.sha256((salt + text).encode()).hexdigest()[:12]
    ids = {opaque(c["id"]) for c in cells}
    rows = [r for r in L.Q.read_jsonl(L.Q.COMPACT_ROOT / args.run_name / f"compact_{args.machine}.jsonl") if r["cell"] in ids]
    pairs_total = len({r["pair"] for r in rows if r["system"] == args.primary} & {r["pair"] for r in rows if r["system"] == args.baseline})
    prestart_path = L.Q.ARTIFACTS / args.run_name / "PRESTART_CELLS.json"
    prestart = {opaque(i) for i in json.loads(prestart_path.read_text())} if prestart_path.exists() else set()
    drop_pairs = {r["pair"] for r in rows if r["cell"] in prestart}
    groups = {"all": (rows, pairs_total)}
    if prestart:
        kept = [r for r in rows if r["pair"] not in drop_pairs]
        groups["without_prestart"] = (kept, pairs_total - len({p for p in drop_pairs if p in {r["pair"] for r in rows if r["system"] == args.primary}}))
    code = 0
    for name, (group_rows, pairs) in groups.items():
        rows_path = Path(f"{args.out}_{name}_rows.jsonl")
        rows_path.write_text("".join(json.dumps(r) + "\n" for r in group_rows))
        command = [sys.executable, args.analyzer, "--rows", str(rows_path), "--primary", args.primary, "--baseline", args.baseline, "--machine", args.machine,
                   "--planned-pairs", str(pairs), "--out", f"{args.out}_{name}"]
        if args.models:
            command += ["--models", *args.models]
        result = subprocess.run(command, capture_output=True, text=True)
        print(json.dumps(dict(group=name, pairs=pairs, rows=len(group_rows), analyzer_exit=result.returncode)))
        code = code or result.returncode
    if prestart:
        print(json.dumps(dict(prestart_cells=len(prestart), pairs_dropped_in_second_group=len(drop_pairs))))
    return code


if __name__ == "__main__":
    sys.exit(main())
