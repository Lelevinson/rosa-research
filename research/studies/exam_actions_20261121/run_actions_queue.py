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

if __name__ == "__main__":
    queue_core.main()
