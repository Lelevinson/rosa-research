"""Integrity look (rev 2, interim-look rule, owner decision D1): counts only. This is the ONLY thing anyone may look at while a tier is incomplete and at a seed checkpoint, and its
COMPLETE flag is the gate for `analyze_when_complete.py` (which is the only way the primary comparison is run).
Prints, per tier: planned and done cells, per-system and per-model cell counts, ending-class counts per system (`supported` and `unsupported` merged into `answered`: that split is an outcome),
infrastructure counts, mean wall seconds, interrupted/failed attempts of the ledger, quarantined cells, duplicates, orphan rows, and whether the tier is COMPLETE. It never prints or computes
`supported`, tokens, requests, an answer, a difference or a ratio, and it does not read a trace. (analyze_primary.py computes comparisons even for an incomplete tier.)
A tier is COMPLETE only if: every planned cell id has exactly one full row; no full row outside the plan; no duplicate full row outside ACCEPTED_DUPLICATES.json; no quarantined cell;
the compact table of the machine joins the full log one to one (no missing compact row, no compact row without a full row, no compact row twice, anywhere in the file - an orphan row blocks every tier).
Infrastructure: `infrastructure_rows_in_compact_share` uses the frozen analysis definition (compact rows with ending `infrastructure`, denominator = the system's compact rows) and is normally 0,
because the queue never turns an infrastructure failure into a row; `attempt_level` adds what the queue keeps elsewhere: GPU-contended attempts (their own log) and zero-request attempts of the
ledger, with denominator rows + those attempts. The frozen 5% / 10% flags are defined on rows; the attempt-level figure is a diagnostic next to it.
  python3 integrity_look.py --spec SPEC --run-name RUN [--machine laptop] [--machines laptop:1] [--artifacts DIR --compact DIR] [--tier TIER]
The held-out pool is read through the environment variable the spec names (ROSA_HELDOUT_V2_TASKS), exactly as the queue does."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import queue_core_rev2 as Q  # noqa: E402  (at apply time: queue_core)


def look(spec_path, run_name, machine="all", machines="all:1", artifacts=None, compact=None):
    if artifacts:
        Q.ARTIFACTS = Path(artifacts)
    if compact:
        Q.COMPACT_ROOT = Path(compact)
    spec = Q.load_spec(spec_path)
    cells = Q.my_cells(Q.build_cells(spec), machine, Q.parse_machines(machines))
    run_dir, compact_dir = Q.ARTIFACTS / run_name, Q.COMPACT_ROOT / run_name
    salt = json.loads(Q.LOCAL_CONFIG.read_text()).get("salt", "unsalted") if Q.LOCAL_CONFIG.exists() else "unsalted"
    opaque = lambda text: hashlib.sha256((salt + text).encode()).hexdigest()[:12]
    full_ids = [r["cell_id"] for r in Q.read_jsonl(run_dir / f"RESULTS_LOG_{machine}.jsonl")]
    compact_rows = Q.read_jsonl(compact_dir / f"compact_{machine}.jsonl")
    contended = Q.read_jsonl(compact_dir / f"compact_{machine}_contended.jsonl")
    ledger = Q.read_jsonl(run_dir / f"INTERRUPTED_{machine}.jsonl")
    failures_path = run_dir / f"failures_{machine}.json"
    quarantined = set(json.loads(failures_path.read_text())["quarantined_cells"]) if failures_path.exists() else set()
    quarantined |= {e["cell_id"] for e in ledger if e.get("event") == "quarantined"}
    accepted_path = run_dir / "ACCEPTED_DUPLICATES.json"
    accepted = set(json.loads(accepted_path.read_text())) if accepted_path.exists() else set()
    planned = {c["id"]: c for c in cells}
    by_key = {opaque(i): i for i in planned}
    # the whole compact file is validated, not only the part inside the plan
    orphan_rows = [r for r in compact_rows if r["cell"] not in by_key]
    repeated_keys = [k for k, n in Counter(r["cell"] for r in compact_rows).items() if n > 1]
    full_counts = Counter(full_ids)
    out = {"run": run_name, "machine": machine, "compact_rows_outside_plan": len(orphan_rows), "compact_keys_repeated": len(repeated_keys),
           "full_rows_outside_plan": len([i for i in full_counts if i not in planned]), "tiers": {}}
    for tier in dict.fromkeys(c["tier"] for c in cells):
        ids = {i for i, c in planned.items() if c["tier"] == tier}
        done = {i for i in full_counts if i in ids}
        rows = [r for r in compact_rows if by_key.get(r["cell"]) in ids]
        dup = [i for i, n in full_counts.items() if n > 1 and i in ids]
        systems = sorted({planned[i]["system"] for i in ids})
        system_of = lambda cell_id: planned[cell_id]["system"]
        contended_per_system = Counter(r["system"] for r in contended if by_key.get(r["cell"]) in ids)
        zero_request = Counter(system_of(e["cell_id"]) for e in ledger if e.get("event") == "interrupted" and e["requests_seen"] == 0 and e["cell_id"] in ids)
        info = dict(planned=len(ids), done=len(done), missing=len(ids - done),
                    cells_per_system=dict(Counter(planned[i]["system"] for i in done)), cells_per_model=dict(Counter(planned[i]["model"] for i in done)),
                    endings_per_system={s: dict(Counter(("answered" if r["ending"] in ("supported", "unsupported") else r["ending"]) for r in rows if r["system"] == s)) for s in systems if any(r["system"] == s for r in rows)},
                    infrastructure_rows_in_compact_share={s: round(sum(r["ending"] == "infrastructure" for r in rows if r["system"] == s) / max(1, sum(r["system"] == s for r in rows)), 3) for s in systems},
                    attempt_level={s: dict(contended_attempts=contended_per_system[s], zero_request_attempts=zero_request[s],
                                           share=round((contended_per_system[s] + zero_request[s]) / max(1, sum(r["system"] == s for r in rows) + contended_per_system[s] + zero_request[s]), 3)) for s in systems},
                    mean_wall_seconds_per_system={s: round(sum(r["wall_seconds"] for r in rows if r["system"] == s) / max(1, sum(r["system"] == s for r in rows)), 1) for s in systems if any(r["system"] == s for r in rows)},
                    ledger_attempts_that_reached_the_model=sum(e.get("event") in ("interrupted", "failed_after_requests") and e["requests_seen"] > 0 and e["cell_id"] in ids for e in ledger),
                    ledger_attempts_that_did_not_reach_the_model=sum(e.get("event") in ("interrupted", "failed_after_requests") and e["requests_seen"] == 0 and e["cell_id"] in ids for e in ledger),
                    quarantined_cells=len(quarantined & ids), duplicate_full_rows=len(dup), duplicates_not_accepted=len([i for i in dup if i not in accepted]))
        join_ok = (not orphan_rows and not repeated_keys and {r["cell"] for r in rows} == {opaque(i) for i in done} and len(rows) == len(done))
        info["compact_joins_full"] = join_ok
        info["COMPLETE"] = bool(info["planned"] and info["done"] == info["planned"] and not info["quarantined_cells"] and not info["duplicates_not_accepted"] and join_ok
                                and not out["full_rows_outside_plan"])
        info["report_as"] = "analysable (tier complete)" if info["COMPLETE"] else f'{info["done"]} of {info["planned"]} cells done; no comparison'
        out["tiers"][tier] = info
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--machine", default="all")
    parser.add_argument("--machines", default="all:1")
    parser.add_argument("--artifacts")
    parser.add_argument("--compact")
    args = parser.parse_args()
    print(json.dumps(look(args.spec, args.run_name, args.machine, args.machines, args.artifacts, args.compact), indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
