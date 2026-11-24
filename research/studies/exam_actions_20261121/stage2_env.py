"""Worker environment and run-mode interlocks of the Stage 2 launcher (`run_actions_queue.py run`). The queue sets ROSA_EXAM_RUN itself and every worker inherits this process's environment, so
the environment is prepared once, here, validated, and returned as a new dict (the caller applies it).

Modes (ROSA_STAGE2_MODE, required for `run`):
  timing      public DEV action tasks through the DEV bridge (no ROSA_ACTION_BRIDGE_FILE). Run names must start `s2time_`.
  live_check  the REAL custody bridge on a PUBLIC task Codex provides in custody format (its own bridge file and bank). Run names must start `s2check_`. The held-out bridge is refused.
  exam        the held-out Stage 2 pool. Run names must start `stage2_`. Needs FREEZE_STAGE2.json that verifies (all code hashes, the held-out bridge hash and the spec hash).
No held-out Stage 2 task can therefore run before the freeze: the held-out bridge file is recognised by the sha256 recorded in the candidate manifest and refused in every mode but `exam`.

Isolation: ROS_DOMAIN_ID defaults to 220 (the harness domain the queue's session asserts; Stage 1 custody runs use 219 and 219 is refused here), ROS_LOCALHOST_ONLY=1, a private ROS_HOME and
ROS_LOG_DIR inside the custody directory (the queue's daemon-ownership rule uses ROS_HOME). No Stage 1 runner may be alive on the machine (one GPU job at a time; the owner pauses Stage 1 first).
Custody settings: ROSA_ACTION_BRIDGE_FILE (an existing file), ROSA_ACTION_CUSTODY_DIR (mode 0700), ROSA_STAGE2_TASKS_FILE (the planner index with opaque ids, named by the spec's tasks_file_env)."""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
FREEZE_FILE = HERE / "FREEZE_STAGE2.json"
CANDIDATE_FILE = HERE / "FREEZE_STAGE2_CANDIDATE.json"
DEFAULT_DOMAIN = "220"
FORBIDDEN_DOMAINS = {"219"}
RUN_PREFIX = {"timing": "s2time_", "live_check": "s2check_", "exam": "stage2_"}


class EnvironmentRefused(RuntimeError):
    """The launcher must not start. The message says why; nothing has run."""


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stage1_runner_alive(proc_root="/proc"):
    """True if a Stage 1 queue runner (`queue_bridge.py ... run` or `queue_core.py ... run`) is alive on this machine. Command lines only."""
    for entry in Path(proc_root).iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        names = [Path(a.decode(errors="replace")).name for a in argv]
        if any(n in ("queue_bridge.py", "queue_core.py") for n in names) and b"run" in argv:
            return True
    return False


def private_dir(path):
    path = Path(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def prepare(environ, run_name, spec_path=None, *, stage1_alive=stage1_runner_alive, freeze_file=FREEZE_FILE, candidate_file=CANDIDATE_FILE, verify_freeze=None):
    """Validate everything and return (new environment dict, record dict). Raises EnvironmentRefused before anything is started."""
    mode = environ.get("ROSA_STAGE2_MODE")
    if mode not in RUN_PREFIX:
        raise EnvironmentRefused(f"ROSA_STAGE2_MODE must be one of {sorted(RUN_PREFIX)}, got {mode!r}")
    if not run_name.startswith(RUN_PREFIX[mode]):
        raise EnvironmentRefused(f"mode {mode} needs a run name starting {RUN_PREFIX[mode]!r}, got {run_name!r}")
    domain = environ.get("ROSA_STAGE2_ROS_DOMAIN", DEFAULT_DOMAIN)
    if not domain.isdecimal() or not 0 < int(domain) <= 232 or str(int(domain)) in FORBIDDEN_DOMAINS:
        raise EnvironmentRefused(f"ROS domain {domain!r} refused (valid 1-232; 219 belongs to the Stage 1 custody runs)")
    if stage1_alive():
        raise EnvironmentRefused("a Stage 1 queue runner is alive on this machine: stop it (STOP file) before any Stage 2 run")
    env = dict(environ, ROS_DOMAIN_ID=str(int(domain)), ROS_LOCALHOST_ONLY="1",
               ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST")
    record = dict(mode=mode, run_name=run_name, ros_domain=domain)
    bridge = environ.get("ROSA_ACTION_BRIDGE_FILE")
    if mode == "timing":
        if bridge:
            raise EnvironmentRefused("timing mode uses the public dev bridge: unset ROSA_ACTION_BRIDGE_FILE")
        return env, dict(record, bridge="dev")
    if not bridge or not Path(bridge).is_file():
        raise EnvironmentRefused("ROSA_ACTION_BRIDGE_FILE must name an existing custody bridge file")
    custody = environ.get("ROSA_ACTION_CUSTODY_DIR")
    if not custody or not Path(custody).is_dir() or Path(custody).stat().st_mode & 0o077:
        raise EnvironmentRefused("ROSA_ACTION_CUSTODY_DIR must name an existing mode-0700 directory")
    tasks = environ.get("ROSA_STAGE2_TASKS_FILE")
    if not tasks or not Path(tasks).is_file():
        raise EnvironmentRefused("ROSA_STAGE2_TASKS_FILE must name the planner index file (opaque ids only)")
    bridge_sha = sha256_file(bridge)
    heldout_sha = None
    for manifest in (candidate_file, freeze_file):
        if Path(manifest).exists():
            heldout_sha = json.loads(Path(manifest).read_text()).get("custody_bridge_sha256") or heldout_sha
    if mode == "live_check":
        if heldout_sha is not None and bridge_sha == heldout_sha:
            raise EnvironmentRefused("live_check refuses the held-out Stage 2 bridge: use the public-task bridge Codex provides")
        if heldout_sha is None:
            raise EnvironmentRefused("no recorded held-out bridge hash (run freeze_stage2.py write first), so the interlock cannot tell the public bridge from the held-out one")
    if mode == "exam":
        if not Path(freeze_file).exists():
            raise EnvironmentRefused("exam mode needs FREEZE_STAGE2.json: the Stage 2 freeze has not been made")
        frozen = json.loads(Path(freeze_file).read_text())
        verified = verify_freeze() if verify_freeze else (None, ["no verifier supplied"])
        if verified[1]:
            raise EnvironmentRefused("the Stage 2 freeze does not verify: " + "; ".join(verified[1][:3]))
        if frozen.get("custody_bridge_sha256") != bridge_sha:
            raise EnvironmentRefused("the bridge file is not the one recorded in FREEZE_STAGE2.json")
        if spec_path is None or frozen.get("spec_sha256") != sha256_file(spec_path):
            raise EnvironmentRefused("the spec file is not the one recorded in FREEZE_STAGE2.json")
    env["ROS_HOME"] = str(private_dir(Path(custody) / "ros-home"))
    env["ROS_LOG_DIR"] = str(private_dir(Path(custody) / "ros-logs"))
    return env, dict(record, bridge="custody", bridge_sha256=bridge_sha, custody_dir=custody, ros_home=env["ROS_HOME"])
