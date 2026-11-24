"""Stage 1 analysis revision 3 (2026-11-24). ANALYSIS ONLY: no runner, scorer, queue, analyzer or freeze file is edited, and nothing here runs a model. It replaces `analyze_when_complete.py`
for result looks (rev 2 listed it as "to be fixed before the first tier look"). Written from scratch on 2026-11-24 after an earlier untracked draft was discarded by the owner.

Defects fixed (CODEX_REVIEW.md 2026-11-22, section "Spec"; REV2 known limitations):
  1. Cross-tier orphan. `integrity_look` validated the full/compact join one tier at a time, so a compact row of a PLANNED cell of another tier whose full row was missing passed. Here the
     join is validated over the whole plan: full log and compact log must describe exactly the same set of cells, once each, with pair/task/system/model/seed/tier/pool/machine fields equal to
     what the plan implies for that cell.
  2. Denominator and rereads. The planned pair count comes from the PLAN (the spec's cells), never from observed rows, and every input file is read ONCE into one snapshot (sha256 recorded);
     the frozen analyzer is called in-process on that snapshot, not on files re-read later.
  3. Pre-start sensitivity (D4). The caller must state `--prestart-expected N`. N > 0: PRESTART_CELLS.json must exist, list exactly N distinct ids, each a planned finished cell of this
     machine. N = 0: the file must not exist. Any mismatch stops the run (exit 2). It can no longer be skipped silently.
  4. Import: the applied frozen `queue_core` (identical bytes to `queue_core_rev2.py`), not `queue_core_rev2`.
Quarantine rule (owner decision 2026-11-23, decisions/2026-11-23-stage1-quarantined-cells.md), applied to the comparison PRIMARY (EX-M) against BASELINE (E1) of one tier on ONE machine:
  * PRIMARY = paired exclusion. A pair is (pool, task, model, seed). If either of its two cells is skipped (quarantined, or inside a quarantined block group) the whole pair leaves the
    comparison and its denominator; a pair counts once even if both cells are skipped. The frozen `analyze_primary.analyse` then runs on the remaining pairs with
    planned_pairs = planned pairs minus excluded pairs, so its FINAL/INTERIM status is checked against the plan.
  * SENSITIVITY = worst case for M, binary outcome only: a skipped M cell counts as FAILURE, a skipped E1 cell as SUCCESS, the observed counterpart is kept, both skipped -> M fails, E1 succeeds.
    Tokens are not imputed, so the sensitivity has no token ratio and no verdict; it reports the supported difference, its interval and whether criterion (a) alone holds.
  * REPORT always, per machine, never pooled: skipped cells per system x model x cause, pairs excluded, the denominator used.
  * A tier is analysable when every planned cell is finished (exactly one full row) or skipped, and the whole-plan join is clean. "Pending" cells (neither) block the look.
Pre-start cohort (D4): every result is produced twice, `all` and `without_prestart` (pairs containing a pre-start cell removed from plan and rows alike), as separate groups.

Codex pre-look review (CODEX_PRELOOK_REVIEW.md, 2026-11-24, of an earlier candidate): (1) task and machine identity of every compact row are validated against the plan (`validate`; already so here);
(2) on the approved `analyze` path the compact comparison fields (supported, ending, tokens, requests) are checked against the accepted full row (`validate_outcome_fields`), and the analyzer's pair
count must equal the plan's denominator; `check` stays outcome-blind; (3) an individual quarantine of a cell that has a completed row blocks until the owner lists it in QUARANTINE_ADJUDICATED.json.

Commands. `check` prints counts and states only and never reads an outcome. `analyze` computes the comparison and refuses to run unless `--result-look-approved` is given: that flag means the
owner has opened the result look (frozen analysis gate). Exit codes: 0 done; 2 integrity or input problem (nothing analysed); 3 tier not yet analysable.
  python3 analysis_rev3.py check   --spec SPEC --run-name RUN --machine laptop --machines laptop:1 --tier TIER --primary EX-M --baseline E1 --prestart-expected N
  python3 analysis_rev3.py analyze (same flags) --out PREFIX --result-look-approved [--draws 10000] [--models ...]"""
import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXAM = HERE.parent / "final_exam_draft_20261118"
QUEUE_DIR = EXAM / "exam_queue"
ANALYZER = EXAM / "freeze_package_20261121" / "analyze_primary.py"
ANALYZER_SHA_FILE = EXAM / "freeze_package_20261121" / "analyze_primary.sha256"


class IntegrityError(Exception):
    """Any input problem. The message is what the owner reads; nothing is analysed."""


def opaque_factory(salt):
    return lambda text: hashlib.sha256((salt + text).encode()).hexdigest()[:12]


# ------------------------------------------------------------------ reading: every file once
def read_once(path):
    """(bytes, sha256) of a file, or (None, None) when it does not exist."""
    path = Path(path)
    if not path.exists():
        return None, None
    data = path.read_bytes()
    return data, hashlib.sha256(data).hexdigest()


def parse_jsonl(data, name):
    rows = []
    for number, line in enumerate((data or b"").decode().splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError as error:
                raise IntegrityError(f"{name} line {number} is not valid JSON ({error}); a torn log must be repaired by the queue before an analysis") from None
    return rows


def load_snapshot(Q, spec_path, run_name, machine, machines, artifacts=None, compact=None, salt=None):
    """Plan plus all logs of ONE machine, read once. `Q` is the frozen queue module (build_cells, my_cells...)."""
    if machine in (None, "all"):
        raise IntegrityError("--machine must name one machine: strata are never pooled")
    artifacts = Path(artifacts) if artifacts else Q.ARTIFACTS
    compact = Path(compact) if compact else Q.COMPACT_ROOT
    spec = Q.load_spec(spec_path)
    plan = Q.my_cells(Q.build_cells(spec), machine, Q.parse_machines(machines))
    if salt is None:
        salt = json.loads(Q.LOCAL_CONFIG.read_text()).get("salt", "unsalted") if Q.LOCAL_CONFIG.exists() else "unsalted"
    run_dir, compact_dir = artifacts / run_name, compact / run_name
    files = {"full": run_dir / f"RESULTS_LOG_{machine}.jsonl", "compact": compact_dir / f"compact_{machine}.jsonl", "ledger": run_dir / f"INTERRUPTED_{machine}.jsonl",
             "failures": run_dir / f"failures_{machine}.json", "accepted": run_dir / "ACCEPTED_DUPLICATES.json", "prestart": run_dir / "PRESTART_CELLS.json",
             "adjudicated": run_dir / "QUARANTINE_ADJUDICATED.json"}
    raw = {key: read_once(path) for key, path in files.items()}
    failures = json.loads(raw["failures"][0]) if raw["failures"][0] else dict(quarantined_cells=[], quarantined_groups=[])
    snapshot = dict(plan=plan, machine=machine, salt=salt, spec_sha256=hashlib.sha256(Path(spec_path).read_bytes()).hexdigest(),
                full_rows=parse_jsonl(raw["full"][0], "full log"), compact=parse_jsonl(raw["compact"][0], "compact log"),
                ledger=parse_jsonl(raw["ledger"][0], "interrupted ledger"), quarantined_cells=set(failures.get("quarantined_cells", [])),
                quarantined_groups=set(failures.get("quarantined_groups", [])), accepted_duplicates=set(json.loads(raw["accepted"][0])) if raw["accepted"][0] else set(),
                adjudicated=set(json.loads(raw["adjudicated"][0])) if raw["adjudicated"][0] else set(),
                prestart_ids=json.loads(raw["prestart"][0]) if raw["prestart"][0] else None,
                input_sha256={key: sha for key, (data, sha) in raw.items() if sha})
    snapshot["full_ids"] = [r["cell_id"] for r in snapshot["full_rows"]]
    return snapshot


# ------------------------------------------------------------------ cell states and validation
def individual_quarantines(snapshot):
    return set(snapshot["quarantined_cells"]) | {e["cell_id"] for e in snapshot["ledger"] if e.get("event") == "quarantined"}


def cell_states(snapshot):
    """id -> 'done' | 'skipped_cell' | 'skipped_group' | 'pending' for every planned cell. A cell with a full row is done even if a quarantine list names it
    (counted separately in `listed_but_finished`)."""
    done = set(snapshot["full_ids"])
    quarantined = individual_quarantines(snapshot)
    states = {}
    for cell in snapshot["plan"]:
        if cell["id"] in done:
            states[cell["id"]] = "done"
        elif cell["id"] in quarantined:
            states[cell["id"]] = "skipped_cell"
        elif f"{cell['model']}|{cell['env']}|{cell['tier']}" in snapshot["quarantined_groups"]:
            states[cell["id"]] = "skipped_group"
        else:
            states[cell["id"]] = "pending"
    return states, sorted(i for i in quarantined if i in done)


def validate(snapshot):
    """Whole-plan validation. Returns a list of problems; an empty list means the snapshot is consistent."""
    opaque = opaque_factory(snapshot["salt"])
    planned = {c["id"]: c for c in snapshot["plan"]}
    by_key = {opaque(i): i for i in planned}
    problems = []
    counts = Counter(snapshot["full_ids"])
    outside = [i for i in counts if i not in planned]
    if outside:
        problems.append(f"{len(outside)} full row(s) for cells outside the plan")
    repeated = [i for i, n in counts.items() if n > 1 and i not in snapshot["accepted_duplicates"]]
    if repeated:
        problems.append(f"{len(repeated)} cell(s) with several full rows that are not in ACCEPTED_DUPLICATES.json")
    keys = Counter(r.get("cell") for r in snapshot["compact"])
    if [k for k, n in keys.items() if n > 1]:
        problems.append(f"{sum(n > 1 for n in keys.values())} compact key(s) repeated")
    outside_keys = [k for k in keys if k not in by_key]
    if outside_keys:
        problems.append(f"{len(outside_keys)} compact row(s) for cells outside the plan")
    full_keys = {opaque(i) for i in counts if i in planned}
    compact_keys = {k for k in keys if k in by_key}
    if compact_keys - full_keys:
        problems.append(f"{len(compact_keys - full_keys)} compact row(s) without a full row (planned cells, any tier)")
    if full_keys - compact_keys:
        problems.append(f"{len(full_keys - compact_keys)} full row(s) without a compact row")
    # Blocker 3 (Codex pre-look review): an INDIVIDUAL quarantine of a cell that also has a completed row is a conflict the owner must adjudicate (QUARANTINE_ADJUDICATED.json lists the
    # adjudicated ids, which are then treated as finished). Finished cells inside a block group quarantined LATER are valid observations and are not a conflict.
    conflicts = sorted(i for i in individual_quarantines(snapshot) if i in counts and i not in snapshot.get("adjudicated", set()))
    if conflicts:
        problems.append(f"{len(conflicts)} individually quarantined cell(s) also have a completed row: adjudicate before any look")
    wrong = 0
    for row in snapshot["compact"]:
        cell = planned.get(by_key.get(row.get("cell")))
        if cell is None:
            continue
        expected = dict(pair=opaque(cell["pair"]), task=opaque(cell["pool"] + cell["task"]), pool=cell["pool"], tier=cell["tier"], system=cell["system"], model=cell["model"],
                        seed=cell["seed"], machine=snapshot["machine"])
        wrong += any(row.get(k) != v for k, v in expected.items())
    if wrong:
        problems.append(f"{wrong} compact row(s) whose pair/task/system/model/seed/tier/pool/machine disagree with the plan")
    return problems


def validate_outcome_fields(snapshot, Q):
    """Blocker 2 (Codex pre-look review). Only on the approved `analyze` path, because it compares outcome fields. For every finished cell, the fields the analysis consumes (supported flag,
    ending class, tokens, request count) in the compact row must equal what the queue's own compaction rule gives for the accepted full row; duplicate full rows must agree with each other.
    A mismatch blocks the comparison."""
    opaque = opaque_factory(snapshot["salt"])
    consumed = lambda full: dict(supported=bool(full.get("supported_complete")), ending=Q.ending_class(full), input_tokens=full.get("input_tokens"), output_tokens=full.get("output_tokens"),
                                 requests=full.get("llm_requests"))
    by_id = defaultdict(list)
    for full in snapshot["full_rows"]:
        by_id[full["cell_id"]].append(full)
    compact_of = {r["cell"]: r for r in snapshot["compact"]}
    bad = 0
    for cell_id, rows in by_id.items():
        expected = [consumed(r) for r in rows]
        row = compact_of.get(opaque(cell_id))
        if row is None or any(e != expected[0] for e in expected) or any(row.get(k) != v for k, v in expected[0].items()):
            bad += 1
    if bad:
        raise IntegrityError(f"{bad} compact row(s) disagree with their accepted full row on analysis fields (or duplicate full rows disagree): the comparison is blocked")


def cause_of(cell_id, how, snapshot):
    """Why a cell is skipped, from the durable ledger (not from a trace)."""
    if how == "skipped_group":
        return "block_group_quarantine"
    attempts = [e for e in snapshot["ledger"] if e.get("cell_id") == cell_id and e.get("event") in ("interrupted", "failed_after_requests") and e.get("requests_seen", 0) > 0]
    if len(attempts) >= 2:
        return "two_attempts_reached_model(" + "+".join(sorted(e["event"] for e in attempts[:2])) + ")"
    if any(e.get("event") == "quarantined" and e.get("cell_id") == cell_id for e in snapshot["ledger"]) or cell_id in snapshot["quarantined_cells"]:
        return "failure_count_limit"
    return "quarantined_other"


def skipped_table(snapshot, states):
    """Skipped cell counts per tier x system x model x cause. This is the reporting required by the owner decision."""
    planned = {c["id"]: c for c in snapshot["plan"]}
    counts = Counter((planned[i]["tier"], planned[i]["system"], planned[i]["model"], cause_of(i, how, snapshot)) for i, how in states.items() if how.startswith("skipped"))
    return [dict(machine=snapshot["machine"], tier=t, system=s, model=m, cause=c, cells=n) for (t, s, m, c), n in sorted(counts.items())]


# ------------------------------------------------------------------ pairs
def planned_pairs(snapshot, tier, primary, baseline, models):
    """pair id -> {system: cell}, for pairs that the PLAN gives both systems, restricted to `models`. The denominator therefore comes from the plan."""
    pairs = defaultdict(dict)
    for cell in snapshot["plan"]:
        if cell["tier"] == tier and cell["system"] in (primary, baseline) and cell["model"] in models:
            pairs[cell["pair"]][cell["system"]] = cell
    return {p: v for p, v in pairs.items() if primary in v and baseline in v}


def load_prestart(snapshot, expected, states):
    ids = snapshot["prestart_ids"]
    if expected == 0:
        if ids is not None:
            raise IntegrityError("PRESTART_CELLS.json exists but --prestart-expected is 0")
        return set()
    if ids is None:
        raise IntegrityError(f"--prestart-expected {expected} but PRESTART_CELLS.json is missing: the pre-start sensitivity must never be skipped silently")
    if len(ids) != expected or len(set(ids)) != len(ids):
        raise IntegrityError(f"PRESTART_CELLS.json lists {len(ids)} id(s) ({len(set(ids))} distinct), expected {expected}")
    bad = [i for i in ids if states.get(i) != "done"]
    if bad:
        raise IntegrityError(f"{len(bad)} pre-start id(s) are not planned, finished cells of this machine")
    return set(ids)


# ------------------------------------------------------------------ the assessment
def assess(snapshot, tier, primary, baseline, models, prestart_expected):
    problems = validate(snapshot)
    if problems:
        return dict(status="integrity_problem", problems=problems)
    states, listed_but_finished = cell_states(snapshot)
    tier_cells = [c for c in snapshot["plan"] if c["tier"] == tier]
    if not tier_cells:
        raise IntegrityError(f"tier {tier!r} has no cells on machine {snapshot['machine']!r}")
    tier_states = Counter(states[c["id"]] for c in tier_cells)
    prestart = load_prestart(snapshot, prestart_expected, states)
    pairs = planned_pairs(snapshot, tier, primary, baseline, models)
    skipped = {p: [c["id"] for c in v.values() if states[c["id"]].startswith("skipped")] for p, v in pairs.items()}
    excluded = {p for p, ids in skipped.items() if ids}
    prestart_pairs = {p for p, v in pairs.items() if any(c["id"] in prestart for c in v.values())}
    report = dict(machine=snapshot["machine"], tier=tier, planned_cells=len(tier_cells), cell_states=dict(tier_states), listed_in_quarantine_but_finished=listed_but_finished,
                  skipped_by_system_model_cause=[r for r in skipped_table(snapshot, {i: s for i, s in states.items() if i in {c["id"] for c in tier_cells}})],
                  planned_pairs=len(pairs), pairs_excluded=len(excluded), primary_denominator=len(pairs) - len(excluded), prestart_cells=len(prestart),
                  prestart_pairs=len(prestart_pairs), input_sha256=snapshot["input_sha256"], spec_sha256=snapshot["spec_sha256"])
    report["status"] = "analysable" if not tier_states.get("pending") else "not_analysable_pending_cells"
    report["_internal"] = dict(states=states, pairs=pairs, excluded=excluded, prestart_pairs=prestart_pairs)
    return report


def load_analyzer():
    expected = ANALYZER_SHA_FILE.read_text().split()[0]
    actual = hashlib.sha256(ANALYZER.read_bytes()).hexdigest()
    if actual != expected:
        raise IntegrityError(f"analyze_primary.py hash {actual[:12]} differs from the frozen {expected[:12]}")
    spec = importlib.util.spec_from_file_location("analyze_primary_frozen", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compute(snapshot, report, A, primary, baseline, models, draws, seed, Q=None):
    """The comparison per group. Needs a validated, analysable report. Returns dict group -> dict(primary=analyzer result, sensitivity=...)."""
    if Q is not None:
        validate_outcome_fields(snapshot, Q)
    opaque = opaque_factory(snapshot["salt"])
    internal = report["_internal"]
    states, pairs, excluded = internal["states"], internal["pairs"], internal["excluded"]
    compact_of = {r["cell"]: r for r in snapshot["compact"]}
    row_of = lambda cell: dict(compact_of[opaque(cell["id"])], _system=cell["system"])
    groups = {"all": set()}
    if internal["prestart_pairs"]:
        groups["without_prestart"] = internal["prestart_pairs"]
    out = {}
    for name, removed in groups.items():
        in_scope = {p: v for p, v in pairs.items() if p not in removed}
        kept = {p: v for p, v in in_scope.items() if p not in excluded}
        rows = [row_of(c) for v in kept.values() for c in v.values()]
        denominator = len(kept)
        primary_result = A.analyse(rows, primary, baseline, models, draws, seed, denominator) if rows else None
        if primary_result and (primary_result["primary_comparison"]["pairs"] != denominator or primary_result["unpaired_cells"]):
            raise IntegrityError(f"the analyzer paired {primary_result['primary_comparison']['pairs']} pairs ({primary_result['unpaired_cells']} unpaired) but the plan gives {denominator}: blocked")
        sensitivity_pairs = []
        for pair, v in in_scope.items():
            m_cell, b_cell = v[primary], v[baseline]
            m_row = row_of(m_cell) if states[m_cell["id"]] == "done" else dict(supported=False, input_tokens=0, output_tokens=0)      # skipped M: failure
            b_row = row_of(b_cell) if states[b_cell["id"]] == "done" else dict(supported=True, input_tokens=0, output_tokens=0)       # skipped E1: success
            sensitivity_pairs.append(((m_cell["pool"], opaque(m_cell["pool"] + m_cell["task"])), m_row, b_row))
        s = A.bootstrap(sensitivity_pairs, draws, seed)
        interval = s["difference_interval"]
        sensitivity = dict(pairs=s["pairs"], tasks=s["tasks"], supported_primary=s["supported_primary"], supported_baseline=s["supported_baseline"], difference_points=s["difference_points"],
                           difference_interval=interval, criterion_a_alone_holds=None if interval is None else interval[0] > A.MARGIN_POINTS,
                           note="worst case for M on the binary outcome; tokens not imputed, no token ratio and no verdict")
        out[name] = dict(pairs_in_scope=len(in_scope), pairs_excluded_in_scope=len(in_scope) - len(kept), primary_denominator=denominator, primary=primary_result, sensitivity=sensitivity)
    return out


def public(report):
    return {k: v for k, v in report.items() if k != "_internal"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["check", "analyze"])
    parser.add_argument("--spec", required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--machine", required=True)
    parser.add_argument("--machines", required=True)
    parser.add_argument("--tier", required=True)
    parser.add_argument("--primary", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--prestart-expected", type=int, required=True)
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
    sys.path.insert(0, str(QUEUE_DIR))
    try:
        import queue_core as Q
        A = load_analyzer()
        models = args.models or A.CORE_MODELS
        snapshot = load_snapshot(Q, args.spec, args.run_name, args.machine, args.machines, args.artifacts, args.compact, args.salt)
        report = assess(snapshot, args.tier, args.primary, args.baseline, models, args.prestart_expected)
    except IntegrityError as error:
        print(json.dumps(dict(status="integrity_problem", problems=[str(error)])))
        return 2
    print(json.dumps(public(report), indent=1, sort_keys=True))
    if report["status"] == "integrity_problem":
        return 2
    if report["status"] != "analysable":
        return 3
    if args.command == "check":
        return 0
    try:
        results = compute(snapshot, report, A, args.primary, args.baseline, models, args.draws, A.DEFAULT_BOOTSTRAP_SEED, Q)
    except IntegrityError as error:
        print(json.dumps(dict(status="integrity_problem", problems=[str(error)])))
        return 2
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out + ".json").write_text(json.dumps(dict(report=public(report), results=results, analyzer_sha256=hashlib.sha256(ANALYZER.read_bytes()).hexdigest(),
                                                           this_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), indent=1, sort_keys=True, default=str) + "\n")
    print(f"wrote {args.out}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
