"""The interface between the Stage 2 runner and the custodian. Two kinds of bridge:

 * DEV bridge (default; public development tasks, public smoke): `request_text(task_id)`, `judge(task_id, answer, true_state, *, ending, trace)`, `start_state_ok(state)`. The runner starts its
   own simulator.
 * CUSTODY bridge (held-out run): a Python file in custody named by ROSA_ACTION_BRIDGE_FILE, with the contract of `custodian.py` (Codex, 2026-11-24). The runner REQUIRES:
     episode(task_id, seed, private_ros_directory) -> context manager yielding the active episode (`.request`, `.backend`); a `FixtureError` while ENTERING it is a pre-start failure (class (a));
     recorder(private_trace_path, episode) -> the one recorder used by the model, native command guard, action kit and tool callbacks (it feeds the episode's evidence);
     judge(episode, answer, executor, requests_started, *, evidence_path) -> dict, called INSIDE the context (before teardown), returning opaque row fields (ending_class, supported_complete,
     goals_sent, executor_final_state, arrived, arrival_claim, claim_audit, success, reasons, judge_version); FixtureError (the exception class).
   The runner opens the episode BEFORE building a model, takes the request only from `active.request` and the robot only from `active.backend`, keeps the trace and evidence in a mode-0700
   directory under ROSA_ACTION_CUSTODY_DIR, and writes no request text anywhere in the queue folder. A file that only offers `request_text` (a callback bridge) is REFUSED when
   ROSA_ACTION_BRIDGE_FILE is set: it would let the runner bypass the evidence capture. A missing function stops the run before any request (no fallback to the dev bridge)."""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "action_dev_switch_20261118"))
import judge as dev_judge  # noqa: E402
import judge_stage2  # noqa: E402

CUSTODY_REQUIRED = ("episode", "recorder", "judge", "FixtureError")
START_POSE_TOLERANCE = 0.05


class DevBridge:
    """Public development tasks only (the 8 authored tasks of the dev action study)."""
    name = "dev"
    kind = "dev"

    @staticmethod
    def request_text(task_id):
        return dev_judge.TASKS[task_id]["text"]

    @staticmethod
    def judge(task_id, answer, true_state, *, ending, trace):
        return judge_stage2.judge(task_id, answer, true_state, ending=ending, trace=trace)

    @staticmethod
    def start_state_ok(state):
        return bool(state["still"]) and abs(state["heading"]) <= START_POSE_TOLERANCE


def load_bridge(environ=None):
    environ = os.environ if environ is None else environ
    path = environ.get("ROSA_ACTION_BRIDGE_FILE")
    if not path:
        return DevBridge
    if not Path(path).is_file():
        raise RuntimeError(f"ROSA_ACTION_BRIDGE_FILE={path!r} is not a file; refusing to fall back to the dev bridge")
    spec = importlib.util.spec_from_file_location("custodian_action_bridge", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "episode", None)) and callable(getattr(module, "request_text", None)):
        raise RuntimeError("callback-only bridge refused: a held-out bridge must provide episode(), recorder() and judge() so that evidence capture cannot be bypassed")
    missing = [name for name in CUSTODY_REQUIRED if not hasattr(module, name) or (name != "FixtureError" and not callable(getattr(module, name)))]
    if missing:
        raise RuntimeError(f"the custody bridge lacks required item(s) {missing}")
    module.name = getattr(module, "name", "custodian")
    module.kind = "custody"
    return module
