"""Registry of the systems the queue can run. Each real system is an existing dev runner that exposes the same three hooks:
run_worker(out, directory, cell, timeout, recorder), episode_row(phase, session, directory, attempt) and an `episode` command line.
A queue cell names a system id; the registry maps it to the runner file and to the arm name that runner expects.
Add a system by adding one line. A system without a runner adapter (Forge, MetaTool) is listed with runner=None and refuses to run with a clear error."""
import importlib.util
import sys
from pathlib import Path

STUDIES = Path(__file__).resolve().parents[2]

# system id -> (runner file relative to research/studies, arm name, short description)
SYSTEMS = {
    "M": ("steady_loop_ablation_20261117/run_ablation.py", "FULL", "the steady loop (ablation FULL arm); the method's component list is OPEN until the freeze"),
    "E1": ("fairness_errors_as_text_20261117/run_fair.py", "E1", "strong ordinary baseline: stock executor, errors as text, better prompt"),
    "S0": ("s0_dev_20261116/run_s0.py", "S0", "original ROSA, verbatim prompt, stock executor, 47 tools"),
    "M-NO_SOFT_ERRORS": ("steady_loop_ablation_20261117/run_ablation.py", "NO_SOFT_ERRORS", "ablation arm"),
    "M-NO_PRECHECK": ("steady_loop_ablation_20261117/run_ablation.py", "NO_PRECHECK", "ablation arm"),
    "M-NO_MENU": ("steady_loop_ablation_20261117/run_ablation.py", "NO_MENU", "ablation arm"),
    "M-NO_FINISH": ("steady_loop_ablation_20261117/run_ablation.py", "NO_FINISH", "ablation arm"),
    "TH-FULL": ("thinking_escalation_20261119/run_think.py", "FULL", "thinking study (amendment A1), arm FULL: reasoning off, as in earlier runs (gpt-oss cannot be turned off)"),
    "TH-ESCALATE": ("thinking_escalation_20261119/run_think.py", "ESCALATE", "thinking study, arm ESCALATE: thinking on for 2 requests after an error / not-found / empty / identical repeat"),
    "TH-ESCALATE_CAPPED": ("thinking_escalation_20261119/run_think.py", "ESCALATE_CAPPED", "thinking study amendment A2, arm ESCALATE_CAPPED: ESCALATE with at most 6 escalated requests per episode"),
    "TH-ALWAYS": ("thinking_escalation_20261119/run_think.py", "ALWAYS", "thinking study part B, arm ALWAYS (separate sessions, later)"),
    "LM-FULL": ("loss_map_20261120/run_lossmap.py", "FULL", "loss-map measurement (2026-11-20): the thinking runner's FULL arm on seeds 5-8, nothing under test"),
    "LV-FULL": ("listval_live_20261120/run_listval.py", "FULL", "list-values live test (2026-11-20): FULL arm, inline_param_values switch OFF (identical to the thinking study's FULL)"),
    "LV-LISTVAL": ("listval_live_20261120/run_listval.py", "LISTVAL", "list-values live test (2026-11-20): LISTVAL arm, ros2_param_list returns name: value (<= 2,000 characters)"),
    # Stage 1 exam systems (exam_arms_20261121, freeze-prep 2026-11-21): the method M with the answer name fix and the approved ablations. Ids carry the prefix EX- so that the
    # development ids above (M = ablation FULL without the name fix, used by the 2026-11-19 mini exam) keep their meaning.
    "EX-M": ("exam_arms_20261121/run_exam.py", "M", "Stage 1 method M: steady loop + name fix (raw answer logged, scored both ways)"),
    "EX-NO_MENU": ("exam_arms_20261121/run_exam.py", "NO_MENU", "Stage 1 ablation: 47 stock tools + final_answer"),
    "EX-NO_FINISH": ("exam_arms_20261121/run_exam.py", "NO_FINISH", "Stage 1 ablation: no final_answer tool and prompt line"),
    "EX-NO_ERRORTEXT": ("exam_arms_20261121/run_exam.py", "NO_ERRORTEXT", "Stage 1 ablation: soft errors and strict pre-check both off"),
    # Baseline adapters (2026-11-21, freeze-prep). Labels: F = "Forge 0.10.1 as released, run through the pilot's unchanged episode function" (runs in the isolated Forge interpreter,
    # ROSA_FORGE_PYTHON); MT = "MetaTool mechanism ported from the released source (echo planning tool + prompt), not the original package" (stock executor, stock tools).
    "F": ("exam_arms_20261121/run_forge.py", "F", "Forge 0.10.1 as released, unchanged pilot episode function, matched transport; queue adapter of 2026-11-21"),
    "MT": ("exam_arms_20261121/run_exam.py", "MT", "MetaTool mechanism ported from the released source (echo planning tool + prompt), not the original package; stock executor and tools"),
}
_loaded = {}


def arm_of(system):
    return SYSTEMS[system][1]


def runner_module(system):
    """Import the runner of a real system (cached). Raises for a system without an adapter."""
    path = SYSTEMS[system][0]
    if path is None:
        raise RuntimeError(f"system {system!r} has no runner adapter yet: {SYSTEMS[system][2]}")
    if path not in _loaded:
        full = STUDIES / path
        spec = importlib.util.spec_from_file_location("runner_" + full.stem, full)
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(full.parent))  # the runners import their sibling files
        spec.loader.exec_module(module)
        _loaded[path] = module
    return _loaded[path]


def worker_of(module):
    """The worker function of a runner module. A runner that has none of its own (s0_dev's run_s0.py) uses the pilot's default worker, which handles the arms S0 and A1."""
    if hasattr(module, "run_worker"):
        return module.run_worker
    sys.path.insert(0, str(STUDIES / "small_model_harness_20261115"))
    import run_pilot
    return run_pilot.run_worker
