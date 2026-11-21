"""Runner adapter for the loss-map measurement (protocol: PROTOCOL.md in this folder). A thin wrapper: it adds the phase `lossmap` (FULL arm only, seeds 5-8, 18 tasks) to the thinking
study's runner and re-exports that runner's worker, episode-row and environment loader unchanged. Nothing about an episode differs from the FULL arm of the thinking replication.

  uv run python research/studies/final_exam_draft_20261118/exam_queue/queue_core.py plan --spec .../specs/lossmap_spec.json
"""
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
THINK = HERE.parent / "thinking_escalation_20261119"
sys.path.insert(0, str(THINK))
import run_think as T  # noqa: E402

load_env = T.load_env          # stage3, e1h and the name-fix fixture
run_worker = T.run_worker      # starts `run_think.py episode ...` (the unchanged FULL arm) as a subprocess
episode_row = T.episode_row
MASTER_SEED = 20261120
SEEDS = [5, 6, 7, 8]           # new seeds: part A used 1-2, the replication 3-4
TASK_IDS = {"stage3": T.STAGE3_TASKS, "e1h": T.E1H_TASKS, "namefix": T.NAMEFIX_TASKS}  # 4 + 6 + 8 = 18 tasks


def plan_for(phase):
    """{session name: [cells]}: one fixture session per (model, environment), seeds and tasks shuffled together inside it (seeded by master seed, phase, model, environment)."""
    assert phase == "lossmap", phase
    sessions = {}
    for model in T.MODELS:
        for env, tasks in TASK_IDS.items():
            cells = [dict(env=env, task=task, arm="FULL", model=model, seed=seed, temperature=0.7) for task in tasks for seed in SEEDS]
            random.Random(f"{MASTER_SEED}-{phase}-{model}-{env}").shuffle(cells)
            sessions[f"{model.replace(':', '_')}-{env}"] = cells
    return sessions
