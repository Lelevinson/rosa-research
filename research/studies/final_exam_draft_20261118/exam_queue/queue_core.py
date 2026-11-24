"""Exam queue, REVISION 2 (draft, not applied): plan, shard, run one GPU job at a time, resume, heartbeat. Read RUNBOOK.md (section "Queue") first.
At apply time this file replaces queue_core.py (rev 2 of the Stage 1 freeze, see exam_dress_rehearsal_20261122/REV2_FREEZE_DRAFT.md). Differences from the frozen queue_core.py:
 1. Result writes (Results.add / add_contended): both JSON lines are ENCODED before either is appended; the cell is marked done right after the full row is durable; a failed or
    interrupted compact append is repaired by reconcile() from the durable full row (no rescoring, no re-run) before any dispatch. In-process recovery can no longer append a
    second full row for the same cell.
 2. Torn last line of an own JSONL log (crash in the middle of a write): the torn bytes are preserved in a `.torn_*` evidence file next to the log and the log is cut back to
    the last complete line; a torn line that is not the last one stops the run. Conflicting duplicate full rows (same cell, different outcome or cost) stop the run;
    agreeing duplicates (old incident) are counted and reported, never silently dropped.
 3. Durable per-cell accounting of interrupted attempts: a start receipt before every worker, a close receipt after it returns or raises (STARTS_<machine>.jsonl). At start-up an
    attempt with a start receipt and no close receipt, no attempt line and no result row is INTERRUPTED: it is written once to INTERRUPTED_<machine>.jsonl (with the number of model
    requests seen in its trace and whether it had an episode_end) and the cell is run again ONCE; a second interrupted attempt that made model requests quarantines the cell.
    The decision uses only these durable markers, never the content of a trace.
 5. Candidate 3: discovery daemon stopped by PID only (no domain-wide RPC), positive ownership (domain + run marker ROSA_EXAM_RUN + ROS_HOME), survivor gate (DaemonSurvivorError blocks dispatch and
    the run never ends as "finished").
 4. Candidate 2 (after Codex's review): the run-owned ROS discovery daemon is stopped between episodes, at resume and at the end; legacy full rows without model/seed are completed in memory
    from the cell id; a failed compact append can no longer end in "finished" (reconcile before every exit, integrity errors are fatal, never a block retry); torn attempt receipts are repaired
    before recovery; a worker attempt that has an attempt line but no result after model requests is under the same once-only ledger as an interrupted attempt (second one quarantines);
    the failure count of zero-request interruptions is derived from the ledger (idempotent).
Rules in words: REV2_FREEZE_DRAFT.md.

  python queue_core.py plan   --spec SPEC [--machines laptop:0.4,lab:0.6]
  python queue_core.py run    --spec SPEC --run-name NAME [--machine laptop] [--machines laptop:0.4,lab:0.6] [--dummy]
  python queue_core.py status --run-name NAME [--machine laptop]
  python queue_core.py merge-check --run-name NAME --spec SPEC [--machines ...]
  python queue_core.py recover --run-name NAME [--machine ...]       (log finished-but-unlogged episodes; `run` does this itself)

Ideas that make it safe to stop anywhere:
 * Cells are ordered by priority tier, then by seed, then by task, so every stopping point leaves complete (task, model, seed) pairs of the tier in progress.
 * A cell is finished only when its row is appended (with fsync) to RESULTS_LOG_<machine>.jsonl; the cell id is the dedupe key. A killed episode has no row and is simply run again.
 * Two machines split the work by hashing the PAIR (pool, task, model, seed) into buckets, so all systems of a pair run on one machine and no cell is run twice.
 * Held-out content stays private: full rows (with answers) go to the git-excluded artifacts folder; only a redacted compact table (opaque task hash, no ids, no answers) is committed."""
import argparse
import hashlib
import json
import os
import random
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
STUDIES = REPO / "research/studies"
sys.path.insert(0, str(HERE))
import gpu_state  # noqa: E402
import health  # noqa: E402
import notify  # noqa: E402
import systems  # noqa: E402

ARTIFACTS = REPO / "research/_artifacts/exam"
COMPACT_ROOT = HERE.parent / "exam_results"
LOCAL_CONFIG = notify.CONFIG_DIR / "local.json"
DEFAULTS = dict(block_size=48, heartbeat_seconds=30, retry_wait_seconds=30, ollama_wait_seconds=1800, min_free_gb=20, quarantine_after=3, episode_timeout_seconds=900, gpu_wait_seconds=1800, gpu_poll_seconds=30)  # gpu_wait_seconds: wait this long for other users' GPU processes to go away before an episode (0 = never wait, only record)


# ------------------------------------------------------------------ planning
def load_spec(path):
    spec = json.loads(Path(path).read_text())
    for key in ("name", "master_seed", "models", "pools", "tiers"):
        assert key in spec, f"spec is missing {key!r}"
    return spec


def pool_tasks(pool_spec, pool_name):
    """{task id: environment} of a pool. A pool either lists its tasks in the spec (development pools) or names an ENVIRONMENT VARIABLE that holds the path of a JSON file
    {task id: environment} kept by the custodian (held-out pools): the task list is then read at run time and never stored in a tracked file. A missing variable or file stops the planner."""
    if "tasks" in pool_spec:
        return pool_spec["tasks"]
    variable = pool_spec["tasks_file_env"]
    path = os.environ.get(variable)
    if not path or not Path(path).is_file():
        raise RuntimeError(f"pool {pool_name!r}: environment variable {variable} must point to the custodian's task list file (got {path!r}); no fallback, no empty pool")
    return json.loads(Path(path).read_text())


def frozen_plan_cells(tier, tier_index):
    """A tier whose cells come from a study's own frozen plan (the thinking study, amendment A1): the sessions, their order and the shuffle inside each session are exactly the study's
    `plan_for(phase)`, and the plan's SHA-256 must equal the hash frozen in the spec, otherwise the planner stops. One session of the plan = one queue block."""
    plan_spec = tier["frozen_plan"]
    module = systems.runner_module(plan_spec["system_prefix"] + plan_spec["arms_probe"])
    plan = module.plan_for(plan_spec["phase"])
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    if digest != plan_spec["manifest_sha256"]:
        raise RuntimeError(f"the plan of {plan_spec['phase']} does not match the frozen manifest hash (got {digest[:12]}, spec says {plan_spec['manifest_sha256'][:12]}): code or plan changed after the freeze")
    pool, cells = plan_spec["pool"], []
    for session, session_cells in plan.items():
        for c in session_cells:
            system = plan_spec["system_prefix"] + c["arm"]
            cells.append(dict(id=f"{pool}|{c['task']}|{system}|{c['model']}|{c['seed']}", tier=tier["name"], tier_index=tier_index, pool=pool, task=c["task"], env=c["env"], model=c["model"],
                              seed=c["seed"], system=system, arm=c["arm"], temperature=c["temperature"], pair=f"{pool}|{c['task']}|{c['model']}|{c['seed']}", session=session))
    return cells


def build_cells(spec):
    """Every cell of the spec in priority order. Within a tier: seeds in the tier's order, then tasks (seeded shuffle), then models, then systems (seeded shuffle inside the pair)."""
    cells = []
    for tier_index, tier in enumerate(spec["tiers"]):
        if "frozen_plan" in tier:
            cells += frozen_plan_cells(tier, tier_index)
            continue
        for seed in tier["seeds"]:
            for pool in tier["pools"]:
                tasks = list(pool_tasks(spec["pools"][pool], pool).items())
                random.Random(f"{spec['master_seed']}-{tier['name']}-{pool}-{seed}").shuffle(tasks)
                for task, env in tasks:
                    for model in tier.get("models", spec["models"]):  # a tier may name its own models (the extra-model tier); default: the spec's core models
                        order = list(tier["systems"])
                        random.Random(f"{spec['master_seed']}-{tier['name']}-{pool}-{task}-{model}-{seed}").shuffle(order)
                        for system in order:
                            cells.append(dict(id=f"{pool}|{task}|{system}|{model}|{seed}", tier=tier["name"], tier_index=tier_index, pool=pool, task=task, env=env, model=model, seed=seed,
                                              system=system, arm=systems.arm_of(system), temperature=spec.get("temperature", 0.7), pair=f"{pool}|{task}|{model}|{seed}"))
    ids = [c["id"] for c in cells]
    assert len(ids) == len(set(ids)), "duplicate cell ids in the spec (the same system, pool, task, model, seed twice)"
    return cells


def parse_machines(text):
    """'laptop:0.4,lab:0.6' -> [('lab', 0.6), ('laptop', 0.4)] sorted by name; shares are normalised."""
    shares = {}
    for part in text.split(","):
        name, share = part.split(":")
        shares[name] = float(share)
    total = sum(shares.values())
    return sorted((name, share / total) for name, share in shares.items())


def bucket(pair):
    return int(hashlib.sha256(pair.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def owner_of(pair, machines):
    """The machine that owns a pair: the bucket in [0,1) is mapped onto the cumulative shares."""
    x, edge = bucket(pair), 0.0
    for name, share in machines:
        edge += share
        if x < edge:
            return name
    return machines[-1][0]


def my_cells(cells, machine, machines):
    return [c for c in cells if machine == "all" or owner_of(c["pair"], machines) == machine]


# ------------------------------------------------------------------ results log
class QueueIntegrityError(RuntimeError):
    """A log is inconsistent in a way the queue must not repair silently (conflicting duplicates, corrupt middle line, compact row without full row ...). The run stops."""


OUTCOME_FIELDS = ("supported_complete", "supported_raw", "name_fix_changed", "exact", "llm_requests", "input_tokens", "output_tokens", "native_ops", "ending", "run_id")


def repair_torn_tail(path):
    """Own JSONL log only. A crash in the middle of an append can leave a last line without its newline or with broken JSON.
    - last line is complete JSON but lacks the newline: the record is kept, the newline is added;
    - last line is broken: its bytes are copied to `<name>.torn_<UTC time>` (evidence, never deleted) and the log is cut back to the last complete line;
    - a broken line that is not the last line: QueueIntegrityError (nothing is changed).
    Returns a short description of what was done, or None."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return None
    data = path.read_bytes()
    lines = data.split(b"\n")
    complete, tail = lines[:-1], lines[-1]           # tail is b"" when the file ends with a newline
    for number, line in enumerate(complete, 1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except ValueError:
            if number == len(complete) and tail == b"":      # a broken last line that does end with a newline: treat as torn as well
                tail, complete = line, complete[:-1]
                break
            raise QueueIntegrityError(f"{path.name}: line {number} is not valid JSON and is not the last line; refusing to continue")
    if tail.strip() == b"":
        if len(complete) != len(lines) - 1 or data.endswith(b"\n"):
            keep = b"".join(line + b"\n" for line in complete)
            if keep != data:
                _replace_durably(path, keep)
        return None
    try:
        json.loads(tail)
        _replace_durably(path, data if data.endswith(b"\n") else data + b"\n")
        return f"{path.name}: last record complete, newline added"
    except ValueError:
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        evidence, number = path.with_name(path.name + ".torn_" + stamp), 0
        while evidence.exists():                     # never overwrite another copy of torn evidence
            number += 1
            evidence = path.with_name(f"{path.name}.torn_{stamp}_{number}")
        with evidence.open("xb") as handle:          # the evidence is on disk before the source is cut back
            handle.write(tail)
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(path.parent)
        _replace_durably(path, b"".join(line + b"\n" for line in complete))
        return f"{path.name}: torn last line ({len(tail)} bytes) kept in {evidence.name}, log cut back to the last complete line"


def _fsync_directory(directory):
    descriptor = os.open(str(directory), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def repair_attempt_ledgers(runs_dir):
    """The runner's own attempt lines (`attempts.jsonl` in every block folder of this run) get the same torn-tail repair as the queue's ledgers, before recover() or the interruption accounting read them.
    A torn attempt line means the worker's completion receipt is not durable: the attempt is then treated as having no attempt line (see account_interrupted)."""
    notes = []
    for path in sorted(Path(runs_dir).glob("*/attempts.jsonl")):
        note = repair_torn_tail(path)
        if note:
            notes.append(note)
            notify.log("torn attempt receipt repaired: " + note)
    return notes


LEGACY_NOTE = "model/seed completed in memory from the cell id (archived full row of the revision-1 incident); the stored row is not changed"


def fill_legacy_fields(row):
    """The archived full rows of the two cells run before revision 1 have no `model` and `seed` (the bridge row did not carry them). They are recovered IN MEMORY from the cell id
    `pool|task|system|model|seed`; the stored record is never rewritten. Every row (old or new) is checked against its cell id: a disagreement stops the run."""
    parts = row["cell_id"].split("|")
    if len(parts) != 5 or not parts[4].lstrip("-").isdigit():
        raise QueueIntegrityError("a full row has a cell id that is not pool|task|system|model|seed")
    pool, task, system, model, seed = parts
    for key, value in (("pool", pool), ("task", task), ("system", system), ("model", model)):
        if key in row and row[key] != value:
            raise QueueIntegrityError(f"a full row disagrees with its cell id in `{key}`")
    if "seed" in row and str(row["seed"]) != seed:
        raise QueueIntegrityError("a full row disagrees with its cell id in `seed`")
    if "model" in row and "seed" in row:
        return row
    return dict(row, model=row.get("model", model), seed=row.get("seed", int(seed)))


def _replace_durably(path, content):
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def read_jsonl(path):
    path = Path(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


class Results:
    """Append-only per-machine log of full rows (private) plus a redacted compact table (committed). Deduplicates by cell id.
    Revision 2: encode both lines first, mark the cell done when the FULL row is durable, repair the compact table from the full log (reconcile), stop on inconsistent logs."""

    def __init__(self, run_name, machine, salt, spec_sha256="", git_head=""):
        self.spec_sha256, self.git_head = spec_sha256, git_head
        self.dir = ARTIFACTS / run_name
        self.compact_dir = COMPACT_ROOT / run_name
        self.dir.mkdir(parents=True, exist_ok=True)
        self.compact_dir.mkdir(parents=True, exist_ok=True)
        self.machine, self.salt = machine, salt
        self.path = self.dir / f"RESULTS_LOG_{machine}.jsonl"
        self.compact_path = self.compact_dir / f"compact_{machine}.jsonl"
        self.contended_path = self.dir / f"CONTENDED_LOG_{machine}.jsonl"  # episodes that ran under GPU contention: kept, never deleted, never counted as results
        self.compact_contended_path = self.compact_dir / f"compact_{machine}_contended.jsonl"
        self.starts_path = self.dir / f"STARTS_{machine}.jsonl"            # start / close receipts of every worker
        self.interrupted_path = self.dir / f"INTERRUPTED_{machine}.jsonl"  # durable accounting of discarded interrupted attempts
        self.lock = threading.Lock()
        self.repairs = [r for r in (repair_torn_tail(p) for p in (self.path, self.compact_path, self.contended_path, self.compact_contended_path, self.starts_path, self.interrupted_path)) if r]
        for note in self.repairs:
            notify.log("torn log repaired: " + note)
        self.done = self.read_done()
        self.contended_run_ids = self.read_contended_run_ids()
        self.duplicate_agreeing = self.check_duplicates()

    def read_contended_run_ids(self):
        """run_id (block folder / episode folder) of every episode kept as GPU-contended. recover() must not turn such an attempt into a result later: it has no GPU data of its own."""
        return {row["run_id"] for row in read_jsonl(self.contended_path)}

    def read_done(self):
        done = set()
        for path in self.dir.glob("RESULTS_LOG_*.jsonl"):  # all machines' logs that are present locally
            for row in self.read_other_or_own(path):
                done.add(row["cell_id"])
        return done

    def read_other_or_own(self, path):
        """Own log: already repaired. Another machine's log is read only: an incomplete last line there is ignored (never edited)."""
        rows = []
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                if Path(path) == self.path:
                    raise QueueIntegrityError(f"{Path(path).name}: unreadable line after repair")
        return rows

    def check_duplicates(self):
        """Same cell twice in the own full log: agreeing records (outcome and cost fields equal) are an old incident and are only counted; a disagreement stops the run."""
        first, agreeing = {}, 0
        for row in read_jsonl(self.path):
            cell = row["cell_id"]
            if cell not in first:
                first[cell] = row
            elif {k: first[cell].get(k) for k in OUTCOME_FIELDS} == {k: row.get(k) for k in OUTCOME_FIELDS}:
                agreeing += 1
            else:
                raise QueueIntegrityError(f"conflicting duplicate full rows for one cell ({cell.split('|')[0]}|...): outcome or cost fields differ")
        return agreeing

    @staticmethod
    def append_line(path, record):
        line = record if isinstance(record, str) else json.dumps(record, default=str)
        with path.open("a") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def add_contended(self, cell, row):
        """Keep the full row of an episode that ran under GPU contention (infrastructure failure). It is NOT in `done`, so the cell is run again."""
        with self.lock:
            full = dict(row, cell_id=cell["id"], system=cell["system"], pool=cell["pool"], tier=cell["tier"], pair=cell["pair"], machine=self.machine, logged_at=time.strftime("%FT%T%z"),
                        spec_sha256=self.spec_sha256, git_head=self.git_head)
            full_line = json.dumps(full, default=str)                                                   # encode both before appending either
            compact_line = json.dumps(self.contended_compact(full), default=str)
            self.append_line(self.contended_path, full_line)
            self.contended_run_ids.add(full["run_id"])
            self.append_line(self.compact_contended_path, compact_line)

    def contended_compact(self, full):
        return dict(compact(full, self.salt), ending="infrastructure_gpu_contended", gpu_reasons=full["gpu_state"]["reasons"])

    def add(self, cell, row):
        with self.lock:
            if cell["id"] in self.done:
                return False
            full = dict(row, cell_id=cell["id"], system=cell["system"], pool=cell["pool"], tier=cell["tier"], pair=cell["pair"], machine=self.machine, logged_at=time.strftime("%FT%T%z"),
                        spec_sha256=self.spec_sha256, git_head=self.git_head)
            full_line = json.dumps(full, default=str)                 # 1. encode both lines: a serialization error leaves nothing half written
            compact_line = json.dumps(compact(full, self.salt), default=str)
            self.append_line(self.path, full_line)                    # 2. the FULL row is the durable result; the cell is done from here on, so an in-process recovery cannot add it twice
            self.done.add(cell["id"])
            try:
                self.append_line(self.compact_path, compact_line)     # 3. the compact row; if this fails or the process dies here, reconcile() writes it from the full row
            except OSError as error:
                notify.log(f"compact row not written ({type(error).__name__}); it will be rebuilt from the full row before the next dispatch")
            return True

    def reconcile(self):
        """Make the compact tables equal to the full logs of THIS machine, before any dispatch. A full row without compact row gets its compact row (same function, same salt, no rescoring,
        no re-run). The join is verified afterwards; a compact row without a full row, or a compact row that differs from its full row, stops the run. Returns the number of rows written."""
        with self.lock:
            written = self._reconcile_pair(self.path, self.compact_path, lambda full: compact(full, self.salt))
            written += self._reconcile_ordered(self.contended_path, self.compact_contended_path, self.contended_compact)
            return written

    def _reconcile_ordered(self, full_path, compact_path, make_compact):
        """Contended episodes: one full row and one compact row per ATTEMPT (a cell can have several, and their compact rows carry no run id), appended in the same order.
        The compact table must equal the first rows of the rebuilt compact rows; missing rows at the end are written; anything else stops the run."""
        wanted = [make_compact(row) for row in read_jsonl(full_path)]
        have = read_jsonl(compact_path)
        comparable = lambda rec: {k: v for k, v in rec.items() if k not in ("gpu_state", "gpu_samples")}
        if len(have) > len(wanted) or any(comparable(h) != comparable(w) for h, w in zip(have, wanted)):
            raise QueueIntegrityError(f"{compact_path.name}: does not match the compact rows rebuilt from {full_path.name}")
        for want in wanted[len(have):]:
            self.append_line(compact_path, json.dumps(want, default=str))
        return len(wanted) - len(have)

    def _reconcile_pair(self, full_path, compact_path, make_compact, key="cell_id"):  # results: one compact row per CELL
        fulls, seen = [], set()
        for row in read_jsonl(full_path):
            if row[key] not in seen:                     # the first full record of a cell is the result (as in add())
                seen.add(row[key])
                fulls.append(fill_legacy_fields(row) if key == "cell_id" else row)
        existing = read_jsonl(compact_path)
        comparable = lambda rec: {k: v for k, v in rec.items() if k not in ("gpu_state", "gpu_samples")}
        by_cell = {}
        for rec in existing:
            by_cell.setdefault(rec["cell"] if key == "cell_id" else json.dumps(comparable(rec), sort_keys=True), []).append(rec)
        written = 0
        expected_keys = set()
        for row in fulls:
            want = make_compact(row)
            ident = want["cell"] if key == "cell_id" else json.dumps(comparable(want), sort_keys=True)
            expected_keys.add(ident)
            have = by_cell.get(ident)
            if not have:
                self.append_line(compact_path, json.dumps(want, default=str))
                written += 1
            else:
                if any(comparable(rec) != comparable(want) for rec in have):
                    raise QueueIntegrityError(f"{compact_path.name}: a compact row differs from the compact row rebuilt from its full row")
                if len(have) > 1:
                    raise QueueIntegrityError(f"{compact_path.name}: the same cell has {len(have)} compact rows")
        extra = set(by_cell) - expected_keys
        if extra:
            raise QueueIntegrityError(f"{compact_path.name}: {len(extra)} compact row(s) without a full row")
        return written


def ending_class(row):
    aborts = " ".join(str(a) for a in row.get("aborts", []))
    if row.get("llm_requests", 0) == 0:
        return "infrastructure"
    if "timeout" in aborts:
        return "timeout"
    if "iteration limit" in aborts:
        return "iteration_cap"
    # A stock-executor argument-validation abort (pydantic "validation error for <tool>") or the NO_ERRORTEXT arm's HardToolError ends the episode by design of that arm;
    # it is its own row, counted as no answer in the capped totals (owner approval 2026-11-21, draft revision 5 section 9c item 3 / freeze-prep 9d-4).
    if "validation error for " in aborts or "HardToolError" in aborts:
        return "validation_abort"
    if aborts.strip():
        return "backend_error"
    if row.get("answer") in (None, {}, ""):
        return "no_answer"
    return "supported" if row.get("supported_complete") else "unsupported"


def compact(row, salt):
    """The committed row: opaque hashes instead of task ids, no answer, no support list, no trace path."""
    opaque = lambda text: hashlib.sha256((salt + text).encode()).hexdigest()[:12]
    return dict(cell=opaque(row["cell_id"]), pair=opaque(row["pair"]), task=opaque(row["pool"] + row["task"]), pool=row["pool"], tier=row["tier"], system=row["system"], model=row["model"],
                seed=row["seed"], machine=row["machine"], supported=bool(row.get("supported_complete")), ending=ending_class(row), requests=row.get("llm_requests"),
                input_tokens=row.get("input_tokens"), output_tokens=row.get("output_tokens"), native_ops=row.get("native_ops"), wall_seconds=row.get("wall_seconds"),
                gpu_state=(row.get("gpu_state") or {}).get("state", "not_recorded"), gpu_samples=(row.get("gpu_state") or {}).get("samples"))


# ------------------------------------------------------------------ the run context: config, status, failures
class StopRequested(Exception):
    pass


class Context:
    def __init__(self, args, spec, cells, machines):
        self.args, self.spec, self.machines = args, spec, machines
        local = json.loads(LOCAL_CONFIG.read_text()) if LOCAL_CONFIG.exists() else {}
        self.cfg = {**DEFAULTS, **spec.get("queue", {}), **local.get("queue", {})}
        self.machine = args.machine
        self.salt = local.get("salt", "unsalted")
        self.mine = my_cells(cells, args.machine, machines)
        spec_sha256 = hashlib.sha256(Path(args.spec).read_bytes()).hexdigest() if args.spec else ""
        git_head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.results = Results(args.run_name, args.machine, self.salt, spec_sha256, git_head)
        self.dir = self.results.dir
        self.runs_dir = self.dir / f"runs_{args.machine}"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.status_path = self.dir / f"status_{args.machine}.json"
        self.failures_path = self.dir / f"failures_{args.machine}.json"
        self.stop_path = self.dir / "STOP"
        self.failures = json.loads(self.failures_path.read_text()) if self.failures_path.exists() else dict(groups={}, cells={}, quarantined_groups=[], quarantined_cells=[])
        self.state, self.current, self.block, self.last_progress, self.started = "starting", None, None, time.time(), time.time()
        self.current_trace = None
        self.ollama_ok, self.notified = True, set()
        self.contended_count = 0
        self.interrupted_total = 0
        self.current_run_id = None
        self.lock = threading.Lock()

    # failures: a block group that keeps failing is skipped (and reported); so is a cell that never produces a result
    def save_failures(self):
        _replace_durably(self.failures_path, json.dumps(self.failures, indent=1).encode())   # rev 2: atomic, never half written

    def group_key(self, cell):
        return f"{cell['model']}|{cell['env']}|{cell['tier']}"

    def note_group_failure(self, group):
        n = self.failures["groups"].get(group, 0) + 1
        self.failures["groups"][group] = n
        if n >= self.cfg["quarantine_after"] and group not in self.failures["quarantined_groups"]:
            self.failures["quarantined_groups"].append(group)
            notify.send("study_failing", machine=self.machine, tries=n, **self.counts())
        self.save_failures()

    def ledger_entries(self):
        return [e for e in read_jsonl(self.results.interrupted_path) if e.get("event") in ("interrupted", "failed_after_requests")]

    def note_cell_failure(self, cell, reason=None):
        """A failed attempt of a cell. Rev 2 (owner decision D2): an attempt that made model requests and has no result (nonzero worker exit, missing ending marker, no trace row ...) is
        written to the once-only ledger (event `failed_after_requests`, once per run folder): the cell may run once more, a second such attempt quarantines it. Attempts without a model request,
        and GPU-contended attempts (their own frozen rule), keep the generic count (quarantine after `quarantine_after`)."""
        run_id = getattr(self, "current_run_id", None)
        if reason not in ("contended", "zero_requests") and run_id:
            trace = self.runs_dir / run_id / "trace.jsonl"
            requests = trace.read_text(errors="replace").count('"kind": "model_start"') if trace.exists() else 0
            if requests > 0:
                known = {e["run_id"] for e in self.ledger_entries()}
                if run_id not in known:
                    self.results.append_line(self.results.interrupted_path, dict(event="failed_after_requests", cell_id=cell["id"], run_id=run_id, requests_seen=requests, trace_exists=True,
                                                                                trace_had_episode_end='"kind": "episode_end"' in trace.read_text(errors="replace"),
                                                                                reason="attempt line without result after model requests", detected_at=time.strftime("%FT%T%z")))
                self.apply_ledger_quarantine()
                return
        counted = self.failures.setdefault("counted_runs", [])
        if run_id and run_id in counted:   # rev 2: one failed attempt is one failure. The frozen code counted it again every time recover() re-logged the same attempt (end of each block, every restart)
            return
        if run_id:
            counted.append(run_id)
        n = self.failures["cells"].get(cell["id"], 0) + 1
        self.failures["cells"][cell["id"]] = n
        if n >= self.cfg["quarantine_after"] and cell["id"] not in self.failures["quarantined_cells"]:
            self.failures["quarantined_cells"].append(cell["id"])
        self.save_failures()

    def apply_ledger_quarantine(self):
        """Quarantine decisions that follow from the durable ledger (idempotent, recomputed from the file, so a crash between a ledger write and this call loses nothing):
        two ledger entries with model requests (interrupted or failed after requests) for one cell; or the generic failure count plus the cell's zero-request interruptions reaching `quarantine_after`."""
        entries, by_cell, quarantined = self.ledger_entries(), {}, []
        for e in entries:
            by_cell.setdefault(e["cell_id"], []).append(e)
        already = {e["cell_id"] for e in read_jsonl(self.results.interrupted_path) if e.get("event") == "quarantined"}
        for cell_id, mine in by_cell.items():
            if cell_id in self.results.done:
                continue
            with_requests = [e for e in mine if e["requests_seen"] > 0]
            zero = [e for e in mine if e["requests_seen"] == 0]
            why = None
            if len(with_requests) >= 2:
                why = "second interrupted or failed attempt with model requests"
            elif self.failures["cells"].get(cell_id, 0) + len(zero) >= self.cfg["quarantine_after"]:
                why = "failure count reached the quarantine limit"
            if why and cell_id not in self.failures["quarantined_cells"]:
                self.failures["quarantined_cells"].append(cell_id)
                self.save_failures()
                quarantined.append(cell_id)
            if why and cell_id not in already:
                self.results.append_line(self.results.interrupted_path, dict(event="quarantined", cell_id=cell_id, reason=why, at=time.strftime("%FT%T%z")))
        return quarantined

    def pending(self):
        bad_groups, bad_cells = set(self.failures["quarantined_groups"]), set(self.failures["quarantined_cells"])
        return [c for c in self.mine if c["id"] not in self.results.done and c["id"] not in bad_cells and self.group_key(c) not in bad_groups]

    def counts(self):
        skipped = len([c for c in self.mine if c["id"] not in self.results.done and (c["id"] in self.failures["quarantined_cells"] or self.group_key(c) in self.failures["quarantined_groups"])])
        return dict(done=len([c for c in self.mine if c["id"] in self.results.done]), total=len(self.mine), skipped=skipped)

    def write_status(self):
        trace_time = None
        if self.current_trace and Path(self.current_trace).exists():
            trace_time = Path(self.current_trace).stat().st_mtime
        progress = max(self.last_progress, trace_time or 0)
        by_tier = {}
        for c in self.mine:
            t = by_tier.setdefault(c["tier"], dict(done=0, total=0))
            t["total"] += 1
            t["done"] += c["id"] in self.results.done
        gpu = health.gpu_memory_mib()
        status = dict(machine=self.machine, pid=os.getpid(), state=self.state, started_at=self.started, heartbeat_at=time.time(), last_progress_at=progress, current_cell=self.current, block=self.block,
                      ollama_ok=self.ollama_ok, disk_free_gb=health.disk_free_gb(self.dir), gpu_used_mib=gpu[0] if gpu else None, gpu_total_mib=gpu[1] if gpu else None, tiers=by_tier,
                      active_tier=next((t for t, v in by_tier.items() if v["done"] < v["total"]), None), quarantined_groups=self.failures["quarantined_groups"], contended_episodes=self.contended_count, interrupted_attempts=self.interrupted_total, **self.counts())
        tmp = self.status_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(status, indent=1))
        os.replace(tmp, self.status_path)

    def start_heartbeat(self):
        def loop():
            while True:
                try:
                    with self.lock:
                        self.write_status()
                except Exception:  # noqa: BLE001  a status write must never kill the runner
                    pass
                time.sleep(self.cfg["heartbeat_seconds"])
        threading.Thread(target=loop, daemon=True).start()


# ------------------------------------------------------------------ one episode
class Recorder:
    """Minimal stand-in for the pilot's trace recorder when a session is not used (dummy mode)."""
    def add(self, kind, **values):
        pass


def kill_orphan_workers(runs_dir):
    """After a hard kill of the runner an episode worker (its own session) may still run. Kill any `... episode --output <runs_dir>/...` process before resuming."""
    killed = []
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit() and int(entry.name) != os.getpid():
            try:
                cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            except OSError:
                continue
            if " episode " in cmd and str(runs_dir) in cmd:
                try:
                    os.killpg(os.getpgid(int(entry.name)), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    continue
                killed.append(int(entry.name))
    return killed


class DaemonSurvivorError(QueueIntegrityError):
    """A run-owned ROS discovery daemon is still alive after TERM and KILL. Dispatch is blocked and the run can never end as "finished"."""


def run_daemon_pids(domain, home, marker):
    """PIDs of the ROS 2 discovery daemons that POSITIVELY belong to this run. All of these must hold: the command line is the daemon's (`python3 -c from ros2cli.daemon.daemonize import main; main()
    --name ros2-daemon ...`, checked on Jazzy; a shell that merely mentions it is not matched); the process environment has ROS_DOMAIN_ID=domain; it has ROSA_EXAM_RUN=marker (the queue sets
    this variable to `<run name>/<machine>` at start, every worker and every ros2 command line inherits it, so a daemon started by this run's agent tools carries it; a daemon started by anyone else,
    by another run name or by a person does not); and, when the runner has ROS_HOME (the custodian launcher sets one bundle-wide home), the same ROS_HOME. Domain-only or home-only matching is
    never enough: without a marker nothing is matched."""
    if not domain or not marker:
        return []
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            environ = (entry / "environ").read_bytes().split(b"\0")
        except (OSError, PermissionError):
            continue
        if not cmdline.startswith(("/usr/bin/python", "python")) or "ros2cli.daemon.daemonize" not in cmdline:
            continue
        if f"ROS_DOMAIN_ID={domain}".encode() not in environ or f"ROSA_EXAM_RUN={marker}".encode() not in environ:
            continue
        if home and f"ROS_HOME={home}".encode() not in environ:
            continue
        found.append(int(entry.name))
    return sorted(found)


def stop_run_daemon(grace=6.0):
    """Stop the discovery daemon(s) this run started (every `ros2 node list` without --no-daemon starts one; it shows up as a hidden node, which the real static fixtures reject at start).
    PID-scoped: SIGTERM to each run-owned PID, a wait, then SIGKILL to those still alive. The domain-wide `ros2 daemon stop` RPC is NOT used (it would stop whichever daemon answers in the domain).
    Ownership is re-checked immediately before every signal (a recycled PID is not signalled). Returns (pids found, pids still alive after TERM and KILL)."""
    domain, marker, home = os.environ.get("ROS_DOMAIN_ID"), os.environ.get("ROSA_EXAM_RUN"), os.environ.get("ROS_HOME")
    pids = run_daemon_pids(domain, home, marker)
    if not pids:
        return [], []
    for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, 2.0)):
        for pid in run_daemon_pids(domain, home, marker):
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        deadline = time.time() + wait
        while time.time() < deadline and run_daemon_pids(domain, home, marker):
            time.sleep(0.2)
        if not run_daemon_pids(domain, home, marker):
            break
    return pids, run_daemon_pids(domain, home, marker)


def stop_run_daemon_or_block(where):
    """The survivor gate: stop the run-owned daemon(s); if one is still alive raise DaemonSurvivorError (dispatch blocked, run ends as integrity_error, never "finished")."""
    pids, survivors = stop_run_daemon()
    if survivors:
        raise DaemonSurvivorError(f"{len(survivors)} run-owned ROS discovery daemon(s) still alive after TERM and KILL ({where}); no further episode is dispatched")
    return pids


def daemon_cleanup_enabled(dummy):
    """Real runs always; dummy (queue test) runs only when a test asks for it, with an explicit unused domain."""
    return dummy is None or os.environ.get("ROSA_QUEUE_DAEMON_CLEANUP") == "1"


def episode_cleanup(ctx, cell):
    """Between episodes: kill ros2 command-line children that outlived their episode (a hung `ros2 param get` would block the next episode's oracle) and, for a Gazebo environment,
    call the configured reset hook. Fixture nodes of the running block are NOT touched (they carry other command lines)."""
    leftovers = health.ros_leftovers(os.environ.get("ROS_DOMAIN_ID", "220"), patterns=("ros2 param", "ros2 node", "ros2 topic", "ros2 service", "ros2 action"))
    if leftovers:
        health.kill_leftovers(os.environ.get("ROS_DOMAIN_ID", "220"), patterns=("ros2 param", "ros2 node", "ros2 topic", "ros2 service", "ros2 action"))
    if daemon_cleanup_enabled(getattr(ctx, "dummy_run", None)):
        stop_run_daemon_or_block("after an episode")   # rev 2: the run's own discovery daemon is not a leftover pattern of the frozen cleanup; a survivor blocks the next dispatch
    hook = ctx.cfg.get("gazebo_reset_command", {}).get(cell["env"])
    if hook:
        subprocess.run(hook, shell=True, timeout=120, check=False)  # the Nav2 / TurtleBot3 reset hook (stack.py stop + start) is configured per environment
    return len(leftovers)


def wait_for_clean_gpu(ctx):
    """Operator rule before an episode: wait (up to cfg gpu_wait_seconds) until no other user's process holds >= 1 GiB of VRAM. Needs process information (not available under WSL, where this
    never waits). Waiting depends only on the GPU state, never on any answer. Raises after the wait so the block counts as failed and is retried later."""
    limit = ctx.cfg["gpu_wait_seconds"]
    if limit <= 0:
        return
    deadline, waited = time.time() + limit, False
    while True:
        reason = gpu_state.busy_reason(gpu_state.snapshot())
        if reason is None:
            break
        if not waited:
            notify.log(f"waiting for the GPU: {reason}")
            ctx.state, waited = "waiting_for_gpu", True
        if time.time() > deadline:
            ctx.state = "running"
            raise RuntimeError(f"GPU still busy after {limit} s: {reason}")
        ctx.last_progress = time.time()  # waiting is not a stall
        time.sleep(ctx.cfg["gpu_poll_seconds"])
    ctx.state = "running"


def make_dispatcher(ctx, dummy_module=None):
    """The run_worker the pilot session calls for every cell: health check, stop file, GPU check, the system's own worker, then the row is logged at once (durable per episode)."""
    def run_worker(out, directory, cell, timeout, recorder):
        if ctx.stop_path.exists():
            raise StopRequested("STOP file present")
        ctx.ollama_ok = dummy_module is not None or health.ollama_ok()
        if not ctx.ollama_ok:
            raise RuntimeError("Ollama unreachable before the episode")
        wait_for_clean_gpu(ctx)
        module = dummy_module or systems.runner_module(cell["system"])
        # status shows tier, system and model only (never a task id), so it is safe to copy into a notification or a screenshot
        ctx.current = f"{cell['tier']}:{cell['system']}:{cell['model']}"
        ctx.current_trace, ctx.last_progress = directory / "trace.jsonl", time.time()
        before = gpu_state.snapshot()
        try:
            ctx.results.reconcile()  # rev 2: compact tables equal the full logs before any new episode starts
        except OSError as error:
            raise QueueIntegrityError(f"compact table could not be brought up to date: {error!r}") from error
        run_id = f"{out.name}/{directory.name}"
        ctx.current_run_id = run_id
        ctx.results.append_line(ctx.results.starts_path, dict(event="start", cell_id=cell["id"], run_id=run_id, at=time.strftime("%FT%T%z")))  # durable start receipt
        try:
            attempt = (module.run_worker if dummy_module else systems.worker_of(module))(out, directory, dict(cell), timeout, recorder)
        except BaseException as error:
            if not isinstance(error, (KeyboardInterrupt, SystemExit)):  # an exception the runner survives is not an interruption; a hard kill never reaches this line
                ctx.results.append_line(ctx.results.starts_path, dict(event="close", run_id=run_id, how="raised", error=type(error).__name__))
            raise
        ctx.results.append_line(ctx.results.starts_path, dict(event="close", run_id=run_id, how="returned"))
        after = gpu_state.snapshot()
        # samples of the episode window: the runner's own two snapshots plus whatever the host-side sampler logged in between
        gpu = gpu_state.summarize([before] + gpu_state.read_window(before["t"], after["t"]) + [after], cell["model"])
        log_episode(ctx, module, out, directory, attempt, cell, gpu)
        episode_cleanup(ctx, cell)
        ctx.current_trace = None
        return attempt
    return run_worker


def log_episode(ctx, module, out, directory, attempt, cell, gpu=None):
    """Turn a finished episode into a row. `gpu` is the episode's gpu_state block (None when recovered after a crash: then the row says gpu_state `not_recorded`)."""
    try:
        row = module.episode_row("exam", out.name, directory, attempt)
    except Exception as error:  # noqa: BLE001  no trace: the worker died before the first event
        ctx.note_cell_failure(cell)
        notify.log(f"episode without trace ({type(error).__name__}) for a {cell['tier']} cell")
        return False
    if row.get("llm_requests", 0) == 0:  # infrastructure failure (no model request): not a result, the cell is tried again
        ctx.note_cell_failure(cell, reason="zero_requests")
        return False
    if gpu is not None:
        row["gpu_state"] = gpu
    if gpu is not None and gpu["contended"]:  # infrastructure failure by the frozen contention rule: row kept apart, cell tried again, decided without looking at the answer
        ctx.results.add_contended(cell, row)
        ctx.note_cell_failure(cell, reason="contended")
        ctx.contended_count += 1
        notify.log(f"episode under GPU contention ({'; '.join(gpu['reasons'])}) for a {cell['tier']} cell; it will be run again")
        return False
    if ctx.results.add(cell, row):
        ctx.last_progress = time.time()
    return True


def account_interrupted(ctx):
    """Revision 2, crash re-run rule. An attempt is INTERRUPTED when its start receipt has no attempt line in any attempts.jsonl (the durable completion boundary; a torn attempt line counts as
    missing) and no result or contended row, and the worker function did not merely raise. (An attempt with an attempt line but no row is not interrupted: recover() and the failed-attempt
    path of note_cell_failure handle it, with the same once-only ledger when it made model requests.) Each interrupted attempt is written once to
    INTERRUPTED_<machine>.jsonl with the number of model requests in its trace and whether the trace had an episode_end; the content of the trace is never used for the decision.
      * first interrupted attempt of a cell: the cell is simply run again (once); the discarded attempt stays on disk;
      * an interrupted attempt that made no model request: the generic failure count (quarantine after `quarantine_after`);
      * a second interrupted attempt that made model requests: the cell is quarantined and reported (the tier is then 'finished with skips').
    Returns (new ledger entries, cells quarantined now)."""
    results = ctx.results
    repair_attempt_ledgers(ctx.runs_dir)
    starts = read_jsonl(results.starts_path)
    closed = {r["run_id"] for r in starts if r["event"] == "close" and r.get("how") == "raised"}   # a worker function that RAISED is an ordinary block failure; one that RETURNED must have left an attempt line
    receipts = {f"{a.parent.name}/{json.loads(line)['directory']}" for a in ctx.runs_dir.glob("*/attempts.jsonl") for line in a.read_text().splitlines() if line.strip()}
    result_runs = {r.get("run_id") for r in read_jsonl(results.path)} | results.contended_run_ids
    ledger = read_jsonl(results.interrupted_path)
    known = {e["run_id"] for e in ledger if e.get("event") in ("interrupted", "failed_after_requests")}
    by_id = {c["id"]: c for c in ctx.mine}
    new_entries = []
    for start in (r for r in starts if r["event"] == "start"):
        run_id = start["run_id"]
        if run_id in closed or run_id in receipts or run_id in result_runs or run_id in known:
            continue
        trace = ctx.runs_dir / run_id / "trace.jsonl"
        text = trace.read_text(errors="replace") if trace.exists() else ""
        entry = dict(event="interrupted", cell_id=start["cell_id"], run_id=run_id, requests_seen=text.count('"kind": "model_start"'), trace_exists=trace.exists(),
                     trace_had_episode_end='"kind": "episode_end"' in text, reason="start receipt without close receipt, attempt line or result", detected_at=time.strftime("%FT%T%z"))
        results.append_line(results.interrupted_path, entry)
        ledger.append(entry)
        new_entries.append(entry)
        known.add(run_id)
    quarantined = ctx.apply_ledger_quarantine()   # derived from the durable ledger: zero-request interruptions are charged here, idempotently
    return len(new_entries), quarantined


def recover(ctx, dummy_module=None):
    """Log episodes that finished (attempt record + trace) but whose row was not written because the runner died in between. Idempotent."""
    repair_attempt_ledgers(ctx.runs_dir)   # a torn attempt line must not block recovery
    added = 0
    for attempts in sorted(ctx.runs_dir.glob("*/attempts.jsonl")):
        for line in attempts.read_text().splitlines():
            attempt = json.loads(line)
            cell = attempt.get("cell", {})
            if "id" not in cell or cell["id"] in ctx.results.done:
                continue
            directory = attempts.parent / attempt["directory"]
            if not (directory / "trace.jsonl").exists() or f"{attempts.parent.name}/{directory.name}" in ctx.results.contended_run_ids:
                continue
            ctx.current_run_id = f"{attempts.parent.name}/{directory.name}"
            module = dummy_module or systems.runner_module(cell["system"])
            added += log_episode(ctx, module, attempts.parent, directory, attempt, cell)
    return added


# ------------------------------------------------------------------ blocks and the run loop
def next_block(pending, size):
    """The next block: the first pending cell in priority order plus the following pending cells of the same (tier, seed, model, env), up to `size`."""
    first = pending[0]
    group = lambda c: (c["tier"], c["session"]) if "session" in c else (c["tier"], c["seed"], c["model"], c["env"])  # a frozen plan's session stays one block
    return [c for c in pending if group(c) == group(first)][:size]


def run_block_real(ctx, block, number):
    sys.path.insert(0, str(STUDIES / "small_model_harness_20261115"))
    sys.path.insert(0, str(STUDIES / "build_round2_20261116"))
    import run_pilot  # noqa: E402
    import run_round2  # noqa: E402
    block_dir = ctx.runs_dir / f"block_{number:04d}"
    plan_path = ctx.runs_dir / f"block_{number:04d}.plan.json"
    plan_path.write_text(json.dumps(block, indent=1))
    original_load_env = run_pilot.load_env
    runner = systems.runner_module(block[0]["system"])
    loader = getattr(runner, "load_env", original_load_env)  # a runner may know more environments (the thinking study adds the name-fix fixture)
    run_pilot.run_worker = make_dispatcher(ctx)
    run_pilot.load_env = lambda name: run_round2.OracleWithRetry(loader(name))
    try:
        run_pilot.session(block_dir, plan_path, wall_limit_hours=6.0)
    finally:
        run_pilot.load_env = original_load_env


def run_block_dummy(ctx, block, number, dummy_module):
    block_dir = ctx.runs_dir / f"block_{number:04d}"
    block_dir.mkdir()
    dispatcher = make_dispatcher(ctx, dummy_module)
    for index, cell in enumerate(block):
        directory = block_dir / f"{index:03d}-{cell['task']}-{cell['arm']}-{cell['model'].replace(':', '_')}-s{cell['seed']}"
        dispatcher(block_dir, directory, cell, 900, Recorder())


def check_machine_selection(machine, machines, cells):
    """Stop loudly when this machine would own no cell. Found on the lab: `--machine lab --machines all:1` selects ZERO cells, and the queue used to report `finished 0 0` (and the monitor
    sent "finished"). `--machine all` runs every cell and ignores the shares; any other machine name must be one of the names in --machines."""
    names = [name for name, _share in machines]
    if machine != "all" and machine not in names:
        raise SystemExit(f"--machine {machine!r} is not one of the machines in --machines {names}: it would own no cell. Use --machine all, or name this machine in --machines (for example 'lab:1').")
    owned = my_cells(cells, machine, machines)
    if not owned:
        raise SystemExit(f"machine {machine!r} owns 0 of the {len(cells)} cells with shares {dict(machines)}: nothing to run (a share of 0, or no cell hashed to this machine).")
    return len(owned)


def run(args):
    spec = load_spec(args.spec)
    cells = build_cells(spec)
    machines = parse_machines(args.machines)
    check_machine_selection(args.machine, machines, cells)
    os.environ["ROSA_EXAM_RUN"] = f"{args.run_name}/{args.machine}"   # ownership marker inherited by every worker, ros2 command line and discovery daemon of this run
    ctx = Context(args, spec, cells, machines)
    dummy = None
    if args.dummy:
        import dummy_system
        dummy = dummy_system
    killed = kill_orphan_workers(ctx.runs_dir)
    if dummy is None:  # fixture nodes of a session whose runner was hard-killed still hold the ROS domain; the next session would refuse to start (found in the mini exam)
        fixtures_killed, _alive = health.kill_leftovers(os.environ.get("ROS_DOMAIN_ID", "220"))
        killed = dict(workers=killed, fixture_processes=len(fixtures_killed))
    ctx.dummy_run = dummy
    if daemon_cleanup_enabled(dummy):
        try:
            stopped = stop_run_daemon_or_block("at start-up")
        except DaemonSurvivorError as error:   # nothing has been dispatched: end here, loudly
            ctx.state = "integrity_error"
            print(json.dumps(dict(event="integrity_error", error=repr(error)[:300])), flush=True)
            ctx.write_status()
            return 5
        if not isinstance(killed, dict):
            killed = dict(workers=killed, fixture_processes=0)
        killed = dict(killed, discovery_daemons_stopped=len(stopped), discovery_daemons_surviving=0)
    recovered = recover(ctx, dummy)
    reconciled = ctx.results.reconcile()                      # rev 2: compact tables equal the full logs before anything is dispatched
    interrupted, quarantined = account_interrupted(ctx)        # rev 2: durable accounting of interrupted attempts
    ctx.interrupted_total = len([e for e in read_jsonl(ctx.results.interrupted_path) if e.get("event") == "interrupted"])
    integrity = dict(torn_repairs=ctx.results.repairs, compact_rows_rebuilt=reconciled, interrupted_attempts_recorded=interrupted, quarantined_after_second_interruption=len(quarantined),
                     duplicate_full_rows_agreeing=ctx.results.duplicate_agreeing)
    if args.cleanup_only:  # test hook: run only the start-up cleanup (orphan workers, fixture leftovers, recovery) and exit
        print(json.dumps(dict(event="cleanup_only", killed=killed, recovered=recovered, **integrity)), flush=True)
        return 0
    ctx.start_heartbeat()
    print(json.dumps(dict(event="start", machine=ctx.machine, cells=len(ctx.mine), done=len(ctx.results.done), killed_orphans=killed, recovered=recovered, **integrity)), flush=True)
    block_number = len([p for p in ctx.runs_dir.iterdir() if p.is_dir()]) + 1  # block folders from earlier starts are kept; numbering continues
    exit_code = 0
    try:
      try:
        while True:
            pending = ctx.pending()
            if not pending:
                ctx.state = "finished" if not ctx.counts()["skipped"] else "finished_with_skips"
                break
            if ctx.stop_path.exists():
                ctx.state = "stopped"
                break
            if not wait_for_health(ctx, dummy is not None):
                exit_code = 3 if not ctx.ollama_ok else 4
                break
            block = next_block(pending, ctx.cfg["block_size"])
            ctx.state, ctx.block = "running", block_number
            if dummy is None:
                health.unload_all(keep=block[0]["model"])  # one model on the 8 GB GPU at a time
            print(json.dumps(dict(event="block_start", block=block_number, cells=len(block), tier=block[0]["tier"], model=block[0]["model"], env=block[0]["env"])), flush=True)
            try:
                if dummy:
                    run_block_dummy(ctx, block, block_number, dummy)
                else:
                    run_block_real(ctx, block, block_number)
            except StopRequested:
                ctx.state = "stopped"
                break
            except QueueIntegrityError:
                raise                                   # rev 2: an inconsistent log is never a block retry that could quarantine the wrong cells
            except Exception as error:  # noqa: BLE001  a failed block: count it, recover finished episodes, wait, go on
                print(json.dumps(dict(event="block_failed", block=block_number, error=repr(error)[:200])), flush=True)
                ctx.note_group_failure(ctx.group_key(block[0]))
                time.sleep(ctx.cfg["retry_wait_seconds"])
            finally:
                recover(ctx, dummy)
                if dummy is None:
                    health.kill_leftovers(os.environ.get("ROS_DOMAIN_ID", "220"))  # fixture or stack processes that a failed session did not stop
                block_number += 1
      except KeyboardInterrupt:
        ctx.state = "stopped"
      except QueueIntegrityError as error:
        ctx.state, exit_code = "integrity_error", 5
        print(json.dumps(dict(event="integrity_error", error=repr(error)[:300])), flush=True)
      try:   # rev 2: no exit (finished, stopped, failed) while a full row lacks its compact row
        ctx.results.reconcile()
      except (QueueIntegrityError, OSError) as error:
        ctx.state, exit_code = "integrity_error", 5
        print(json.dumps(dict(event="integrity_error", error=repr(error)[:300])), flush=True)
      if daemon_cleanup_enabled(dummy):
        try:
            stop_run_daemon_or_block("at the end of the run")
        except DaemonSurvivorError as error:   # never "finished" with a run-owned daemon alive
            ctx.state, exit_code = "integrity_error", 5
            print(json.dumps(dict(event="integrity_error", error=repr(error)[:300])), flush=True)
    finally:
        with ctx.lock:
            if dummy is None:
                health.unload_all()
            ctx.current = ctx.current_trace = None
            ctx.write_status()
    print(json.dumps(dict(event="end", state=ctx.state, **ctx.counts())), flush=True)
    return exit_code


def wait_for_health(ctx, dummy):
    """Ollama reachable and enough disk before a block. Waits up to ollama_wait_seconds for Ollama; returns False to stop with a clear state."""
    if health.disk_free_gb(ctx.dir) < ctx.cfg["min_free_gb"]:
        ctx.state = "blocked_disk"
        return False
    if dummy:
        return True
    deadline = time.time() + ctx.cfg["ollama_wait_seconds"]
    while not health.ollama_ok():
        ctx.ollama_ok, ctx.state = False, "waiting_for_ollama"
        if time.time() > deadline:
            ctx.state = "blocked_ollama"
            return False
        time.sleep(30)
    ctx.ollama_ok = True
    return True


# ------------------------------------------------------------------ plan, status, merge check
def plan_report(args):
    spec = load_spec(args.spec)
    cells = build_cells(spec)
    machines = parse_machines(args.machines)
    summary = {}
    for c in cells:
        key = (c["tier"], owner_of(c["pair"], machines))
        summary[key] = summary.get(key, 0) + 1
    no_adapter = sorted({c["system"] for c in cells if systems.SYSTEMS[c["system"]][0] is None})
    print(json.dumps(dict(cells=len(cells), by_tier_and_machine={f"{t}|{m}": n for (t, m), n in sorted(summary.items())}, first=[c["id"] for c in cells[:6]],
                          WARNING_systems_without_runner_adapter=no_adapter or None), indent=1))


def merge_check(args):
    """Across every machine's log that is present: duplicates, cells outside the spec, cells missing, pair completeness per tier."""
    spec = load_spec(args.spec)
    expected = {c["id"]: c for c in build_cells(spec)}
    run_dir = ARTIFACTS / args.run_name
    seen, duplicates, outside, wrong_spec = {}, [], [], []
    first_row, conflicting = {}, []
    accepted_path = run_dir / "ACCEPTED_DUPLICATES.json"  # evidence-backed list of cell ids whose agreeing duplicate full rows are an old incident (written by the owner or Codex, never by the queue)
    accepted = set(json.loads(accepted_path.read_text())) if accepted_path.exists() else set()
    this_spec = hashlib.sha256(Path(args.spec).read_bytes()).hexdigest()
    for path in sorted(run_dir.glob("RESULTS_LOG_*.jsonl")):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get("spec_sha256") not in (None, "", this_spec):
                wrong_spec.append(row["cell_id"])
            if row["cell_id"] in seen:
                duplicates.append(row["cell_id"])
                if {k: first_row[row["cell_id"]].get(k) for k in OUTCOME_FIELDS} != {k: row.get(k) for k in OUTCOME_FIELDS}:
                    conflicting.append(row["cell_id"])
            elif row["cell_id"] not in expected:
                outside.append(row["cell_id"])
            seen.setdefault(row["cell_id"], row["machine"])
            first_row.setdefault(row["cell_id"], row)
    missing = [i for i in expected if i not in seen]
    incomplete_pairs = {c["pair"] for i, c in expected.items() if i not in seen} & {c["pair"] for i, c in expected.items() if i in seen}
    machines = parse_machines(args.machines)
    names = [name for name, _share in machines]
    # With the single pseudo-machine "all" (the default --machines all:1) no cell has a real owner: every row is fine whichever machine logged it. Before 2026-11-20 this case reported
    # every row as logged on the wrong machine (found in the lab dummy run, which logged as "lab" but was checked without --machines lab:1).
    ownership_checked = names != ["all"]
    wrong_machine = [i for i, m in seen.items() if i in expected and ownership_checked and owner_of(expected[i]["pair"], machines) != m]
    unknown_machines = sorted({m for m in seen.values()} - set(names)) if ownership_checked else []
    unaccepted = [c for c in duplicates if c not in accepted]
    compact_dir = COMPACT_ROOT / args.run_name
    salt = json.loads(LOCAL_CONFIG.read_text()).get("salt", "unsalted") if LOCAL_CONFIG.exists() else "unsalted"
    opaque = lambda text: hashlib.sha256((salt + text).encode()).hexdigest()[:12]
    compact_keys = {json.loads(l)["cell"] for path in compact_dir.glob("compact_*.jsonl") if "contended" not in path.name for l in path.read_text().splitlines() if l.strip()}
    full_without_compact = sum(opaque(i) not in compact_keys for i in seen)
    print(json.dumps(dict(expected=len(expected), logged=len(seen), duplicates=len(duplicates), duplicates_conflicting=len(conflicting), duplicates_not_in_accepted_list=len(unaccepted), full_rows_without_compact_row=full_without_compact, outside_spec=len(outside), missing=len(missing), pairs_with_some_systems_missing=len(incomplete_pairs),
                          logged_on_the_wrong_machine=len(wrong_machine) if ownership_checked else "not checked (--machines all:1 has no owners)",
                          machines_in_logs_not_in_machines_arg=unknown_machines, rows_from_a_different_spec=len(wrong_spec)), indent=1))
    return 0 if not unaccepted and not conflicting and not outside and not wrong_spec and not full_without_compact else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["plan", "run", "status", "merge-check", "recover"])
    parser.add_argument("--spec")
    parser.add_argument("--run-name")
    parser.add_argument("--machine", default=os.environ.get("ROSA_EXAM_MACHINE", "all"))
    parser.add_argument("--machines", default="all:1")
    parser.add_argument("--cleanup-only", action="store_true", help="run only the start-up cleanup and exit (live test of the resume cleanup)")
    parser.add_argument("--dummy", action="store_true", help="fake episodes (no ROS, no Ollama) to test the queue itself")
    args = parser.parse_args()
    if args.command == "plan":
        plan_report(args)
    elif args.command == "run":
        sys.exit(run(args))
    elif args.command == "merge-check":
        sys.exit(merge_check(args))
    elif args.command == "status":
        print((ARTIFACTS / args.run_name / f"status_{args.machine}.json").read_text())
    elif args.command == "recover":
        spec = load_spec(args.spec)
        ctx = Context(args, spec, build_cells(spec), parse_machines(args.machines))
        recovered = recover(ctx, __import__("dummy_system") if args.dummy else None)
        rebuilt = ctx.results.reconcile()
        interrupted, quarantined = account_interrupted(ctx)
        print("recovered", recovered, "compact_rows_rebuilt", rebuilt, "interrupted_recorded", interrupted, "quarantined", len(quarantined), "torn_repairs", ctx.results.repairs)


if __name__ == "__main__":
    main()
