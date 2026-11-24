"""Launcher: the unchanged exam queue with the Stage 2 action systems registered at run time (no queue file is edited).
  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python research/studies/exam_actions_20261121/run_actions_queue.py plan|run --spec SPEC --run-name RUN --machine laptop --machines laptop:1
DEVELOPMENT action tasks only. A spec lists pools of {task id: "turtlesim"}; the queue starts one stub fixture session per block and each episode starts its own simulator."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUEUE = HERE.parent / "final_exam_draft_20261118" / "exam_queue"
sys.path.insert(0, str(QUEUE))
sys.path.insert(0, str(HERE))
import queue_core  # noqa: E402
import systems  # noqa: E402
from action_systems import ACTION_SYSTEMS  # noqa: E402

systems.SYSTEMS.update(ACTION_SYSTEMS)

_frozen_ending_class = queue_core.ending_class


def ending_class_stage2(row):
    """Adds the two action endings the frozen queue cannot express: `unscored` (class (c), fixture or independent reader lost after a request) and `unresolved_motion` (class (b)).
    Everything else is the frozen function, unchanged. Patched at run time like the system registry, so no frozen file is edited."""
    return row.get("ending_override") or _frozen_ending_class(row)


queue_core.ending_class = ending_class_stage2

def apply_stage2_environment(argv):
    """For `run` only: validate and apply the worker environment and the run-mode interlocks (stage2_env) BEFORE the queue starts; a refusal exits with a message and nothing runs."""
    import os
    import stage2_env
    options = dict(zip(argv[1:], argv[2:]))
    spec = options.get("--spec")
    try:
        env, record = stage2_env.prepare(os.environ, options.get("--run-name", ""), spec, verify_freeze=_verify_freeze)
    except stage2_env.EnvironmentRefused as refusal:
        print(f"REFUSED: {refusal}", file=sys.stderr)
        sys.exit(2)
    os.environ.update(env)
    print("stage2 environment:", record, flush=True)


def _verify_freeze():
    import freeze_stage2
    return freeze_stage2.verify_frozen()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        apply_stage2_environment(sys.argv)
    queue_core.main()
