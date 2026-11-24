"""Post-hoc count (rev 2, known limitation of the once-only ledger): how many cells had MORE THAN ONE attempt that made a model request, per system. Run it at the end of a tier, never as an interim look.
Why it exists: if the receipt write itself fails after inference, the attempt is not in the ledger and the cell can be run again without being counted there (documented limitation, owner decision 2026-11-22).
This count does not rely on the ledger: it joins the start receipts (STARTS_<machine>.jsonl) and the runner's attempt lines (runs_<machine>/*/attempts.jsonl) to cells, and counts the attempt folders whose
trace contains at least one `model_start` event. It reads no answer, score or tool result: only the number of `model_start` lines per trace.
  python3 multi_attempt_count.py --spec SPEC --run-name RUN [--machine M --machines MS] [--artifacts DIR] [--tier TIER]"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import queue_core_rev2 as Q  # noqa: E402  (at apply time: queue_core)


def count(spec_path, run_name, machine="all", machines="all:1", artifacts=None, tier=None):
    if artifacts:
        Q.ARTIFACTS = Path(artifacts)
    cells = {c["id"]: c for c in Q.my_cells(Q.build_cells(Q.load_spec(spec_path)), machine, Q.parse_machines(machines)) if tier in (None, c["tier"])}
    run_dir = Q.ARTIFACTS / run_name
    runs = run_dir / f"runs_{machine}"
    attempts = defaultdict(set)                       # cell id -> {run folder ids}
    for row in Q.read_jsonl(run_dir / f"STARTS_{machine}.jsonl"):
        if row.get("event") == "start":
            attempts[row["cell_id"]].add(row["run_id"])
    for path in runs.glob("*/attempts.jsonl"):
        for row in Q.read_jsonl(path):
            if row.get("cell", {}).get("id"):
                attempts[row["cell"]["id"]].add(f"{path.parent.name}/{row['directory']}")
    multi, with_requests = Counter(), Counter()
    for cell_id, run_ids in attempts.items():
        if cell_id not in cells:
            continue
        reached = 0
        for run_id in run_ids:
            trace = runs / run_id / "trace.jsonl"
            if trace.exists() and trace.read_text(errors="replace").count('"kind": "model_start"') > 0:
                reached += 1
        with_requests[cells[cell_id]["system"]] += reached > 0
        multi[cells[cell_id]["system"]] += reached > 1
    systems = sorted({c["system"] for c in cells.values()})
    return {s: dict(cells_planned=sum(c["system"] == s for c in cells.values()), cells_with_a_model_request_attempt=with_requests[s], cells_with_more_than_one_model_request_attempt=multi[s]) for s in systems}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--machine", default="all")
    parser.add_argument("--machines", default="all:1")
    parser.add_argument("--artifacts")
    parser.add_argument("--tier")
    args = parser.parse_args()
    print(json.dumps(count(args.spec, args.run_name, args.machine, args.machines, args.artifacts, args.tier), indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
