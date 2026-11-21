"""Exam queue: plan, shard, run one GPU job at a time, resume, heartbeat. Read RUNBOOK.md (section "Queue") first.

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
class Results:
    """Append-only per-machine log of full rows (private) plus a redacted compact table (committed). Deduplicates by cell id."""

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
        self.lock = threading.Lock()
        self.done = self.read_done()
        self.contended_run_ids = self.read_contended_run_ids()

    def read_contended_run_ids(self):
        """run_id (block folder / episode folder) of every episode kept as GPU-contended. recover() must not turn such an attempt into a result later: it has no GPU data of its own."""
        ids = set()
        if self.contended_path.exists():
            ids = {json.loads(line)["run_id"] for line in self.contended_path.read_text().splitlines() if line.strip()}
        return ids

    def read_done(self):
        done = set()
        for path in self.dir.glob("RESULTS_LOG_*.jsonl"):  # all machines' logs that are present locally
            for line in path.read_text().splitlines():
                if line.strip():
                    done.add(json.loads(line)["cell_id"])
        return done

    @staticmethod
    def append_line(path, record):
        with path.open("a") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def add_contended(self, cell, row):
        """Keep the full row of an episode that ran under GPU contention (infrastructure failure). It is NOT in `done`, so the cell is run again."""
        with self.lock:
            full = dict(row, cell_id=cell["id"], system=cell["system"], pool=cell["pool"], tier=cell["tier"], pair=cell["pair"], machine=self.machine, logged_at=time.strftime("%FT%T%z"),
                        spec_sha256=self.spec_sha256, git_head=self.git_head)
            self.append_line(self.contended_path, full)
            self.contended_run_ids.add(full["run_id"])
            self.append_line(self.compact_contended_path, dict(compact(full, self.salt), ending="infrastructure_gpu_contended", gpu_reasons=full["gpu_state"]["reasons"]))

    def add(self, cell, row):
        with self.lock:
            if cell["id"] in self.done:
                return False
            full = dict(row, cell_id=cell["id"], system=cell["system"], pool=cell["pool"], tier=cell["tier"], pair=cell["pair"], machine=self.machine, logged_at=time.strftime("%FT%T%z"),
                        spec_sha256=self.spec_sha256, git_head=self.git_head)
            self.append_line(self.path, full)
            self.append_line(self.compact_path, compact(full, self.salt))
            self.done.add(cell["id"])
            return True


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
        self.lock = threading.Lock()

    # failures: a block group that keeps failing is skipped (and reported); so is a cell that never produces a result
    def save_failures(self):
        self.failures_path.write_text(json.dumps(self.failures, indent=1))

    def group_key(self, cell):
        return f"{cell['model']}|{cell['env']}|{cell['tier']}"

    def note_group_failure(self, group):
        n = self.failures["groups"].get(group, 0) + 1
        self.failures["groups"][group] = n
        if n >= self.cfg["quarantine_after"] and group not in self.failures["quarantined_groups"]:
            self.failures["quarantined_groups"].append(group)
            notify.send("study_failing", machine=self.machine, tries=n, **self.counts())
        self.save_failures()

    def note_cell_failure(self, cell):
        n = self.failures["cells"].get(cell["id"], 0) + 1
        self.failures["cells"][cell["id"]] = n
        if n >= self.cfg["quarantine_after"] and cell["id"] not in self.failures["quarantined_cells"]:
            self.failures["quarantined_cells"].append(cell["id"])
        self.save_failures()

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
                      active_tier=next((t for t, v in by_tier.items() if v["done"] < v["total"]), None), quarantined_groups=self.failures["quarantined_groups"], contended_episodes=self.contended_count, **self.counts())
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


def episode_cleanup(ctx, cell):
    """Between episodes: kill ros2 command-line children that outlived their episode (a hung `ros2 param get` would block the next episode's oracle) and, for a Gazebo environment,
    call the configured reset hook. Fixture nodes of the running block are NOT touched (they carry other command lines)."""
    leftovers = health.ros_leftovers(os.environ.get("ROS_DOMAIN_ID", "220"), patterns=("ros2 param", "ros2 node", "ros2 topic", "ros2 service", "ros2 action"))
    if leftovers:
        health.kill_leftovers(os.environ.get("ROS_DOMAIN_ID", "220"), patterns=("ros2 param", "ros2 node", "ros2 topic", "ros2 service", "ros2 action"))
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
        attempt = (module.run_worker if dummy_module else systems.worker_of(module))(out, directory, dict(cell), timeout, recorder)
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
        ctx.note_cell_failure(cell)
        return False
    if gpu is not None:
        row["gpu_state"] = gpu
    if gpu is not None and gpu["contended"]:  # infrastructure failure by the frozen contention rule: row kept apart, cell tried again, decided without looking at the answer
        ctx.results.add_contended(cell, row)
        ctx.note_cell_failure(cell)
        ctx.contended_count += 1
        notify.log(f"episode under GPU contention ({'; '.join(gpu['reasons'])}) for a {cell['tier']} cell; it will be run again")
        return False
    if ctx.results.add(cell, row):
        ctx.last_progress = time.time()
    return True


def recover(ctx, dummy_module=None):
    """Log episodes that finished (attempt record + trace) but whose row was not written because the runner died in between. Idempotent."""
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
    ctx = Context(args, spec, cells, machines)
    dummy = None
    if args.dummy:
        import dummy_system
        dummy = dummy_system
    killed = kill_orphan_workers(ctx.runs_dir)
    if dummy is None:  # fixture nodes of a session whose runner was hard-killed still hold the ROS domain; the next session would refuse to start (found in the mini exam)
        fixtures_killed, _alive = health.kill_leftovers(os.environ.get("ROS_DOMAIN_ID", "220"))
        killed = dict(workers=killed, fixture_processes=len(fixtures_killed))
    recovered = recover(ctx, dummy)
    if args.cleanup_only:  # test hook: run only the start-up cleanup (orphan workers, fixture leftovers, recovery) and exit
        print(json.dumps(dict(event="cleanup_only", killed=killed, recovered=recovered)), flush=True)
        return 0
    ctx.start_heartbeat()
    print(json.dumps(dict(event="start", machine=ctx.machine, cells=len(ctx.mine), done=len(ctx.results.done), killed_orphans=killed, recovered=recovered)), flush=True)
    block_number = len([p for p in ctx.runs_dir.iterdir() if p.is_dir()]) + 1  # block folders from earlier starts are kept; numbering continues
    exit_code = 0
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
    this_spec = hashlib.sha256(Path(args.spec).read_bytes()).hexdigest()
    for path in sorted(run_dir.glob("RESULTS_LOG_*.jsonl")):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get("spec_sha256") not in (None, "", this_spec):
                wrong_spec.append(row["cell_id"])
            if row["cell_id"] in seen:
                duplicates.append(row["cell_id"])
            elif row["cell_id"] not in expected:
                outside.append(row["cell_id"])
            seen.setdefault(row["cell_id"], row["machine"])
    missing = [i for i in expected if i not in seen]
    incomplete_pairs = {c["pair"] for i, c in expected.items() if i not in seen} & {c["pair"] for i, c in expected.items() if i in seen}
    machines = parse_machines(args.machines)
    names = [name for name, _share in machines]
    # With the single pseudo-machine "all" (the default --machines all:1) no cell has a real owner: every row is fine whichever machine logged it. Before 2026-11-20 this case reported
    # every row as logged on the wrong machine (found in the lab dummy run, which logged as "lab" but was checked without --machines lab:1).
    ownership_checked = names != ["all"]
    wrong_machine = [i for i, m in seen.items() if i in expected and ownership_checked and owner_of(expected[i]["pair"], machines) != m]
    unknown_machines = sorted({m for m in seen.values()} - set(names)) if ownership_checked else []
    print(json.dumps(dict(expected=len(expected), logged=len(seen), duplicates=len(duplicates), outside_spec=len(outside), missing=len(missing), pairs_with_some_systems_missing=len(incomplete_pairs),
                          logged_on_the_wrong_machine=len(wrong_machine) if ownership_checked else "not checked (--machines all:1 has no owners)",
                          machines_in_logs_not_in_machines_arg=unknown_machines, rows_from_a_different_spec=len(wrong_spec)), indent=1))
    return 0 if not duplicates and not outside and not wrong_spec else 1


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
        print("recovered", recover(ctx, __import__("dummy_system") if args.dummy else None))


if __name__ == "__main__":
    main()
