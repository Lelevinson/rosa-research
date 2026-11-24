"""Generates the Stage 2 queue specs (one place, so the cell count is computed and not typed). Three specs:
  exam        the held-out pool named by the environment variable ROSA_STAGE2_TASKS_FILE (opaque ids, from custody), 3 systems x 4 models x N seeds. Seeds N is decided after the timing episodes.
  live_check  2 public tasks in custody format x 1 model x 3 systems x seed 1 (6 episodes) through the custody bridge. The task index is public (same variable).
  timing      public DEV action tasks through the DEV bridge, 4 models x 3 systems x seed 1, to measure seconds per cell per model and system.
  python3 stage2_spec.py exam --seeds 2 --out specs/exam_spec_stage2.json
  python3 stage2_spec.py timing --out specs/timing_spec_stage2.json
  python3 stage2_spec.py live_check --model qwen3.5:9b --out specs/live_check_spec_stage2.json"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE_MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
SYSTEMS = ["XM", "XE1", "XS0"]
MASTER_SEED = 20261124
TASKS_FILE_ENV = "ROSA_STAGE2_TASKS_FILE"
TIMING_TASKS = {"S3": "turtlesim", "R1": "turtlesim", "M1": "turtlesim"}      # public dev tasks: single (out-of-range heading), act-then-read, two-step
QUEUE = {"block_size": 24, "heartbeat_seconds": 30, "quarantine_after": 3}


def exam_spec(seeds):
    if seeds not in (1, 2, 3):
        raise ValueError("seeds must be 1, 2 or 3")
    return {"name": "stage2_exam", "master_seed": MASTER_SEED, "temperature": 0.7, "models": CORE_MODELS,
            "_status": "Stage 2 held-out action pool (14 tasks from custody). Seeds are fixed before the first held-out request.",
            "pools": {"stage2_turtlesim": {"tasks_file_env": TASKS_FILE_ENV}},
            "tiers": [{"name": "stage2", "systems": SYSTEMS, "pools": ["stage2_turtlesim"], "seeds": list(range(1, seeds + 1))}], "queue": QUEUE}


def live_check_spec(model):
    spec = exam_spec(1)
    spec.update(name="stage2_live_check", models=[model], _status="Public custody live check: successful rotation and cancelled rotation across 3 systems and 1 seed.")
    spec["pools"] = {"stage2_public_check": {"tasks_file_env": TASKS_FILE_ENV}}
    spec["tiers"] = [{"name": "live_check", "systems": SYSTEMS, "pools": ["stage2_public_check"], "seeds": [1]}]
    return spec


def timing_spec():
    return {"name": "stage2_timing", "master_seed": MASTER_SEED, "temperature": 0.7, "models": CORE_MODELS,
            "_status": "Timing episodes on PUBLIC dev action tasks (dev bridge). Seconds per cell per model and system; no scores are used.",
            "pools": {"dev_actions": {"tasks": TIMING_TASKS}},
            "tiers": [{"name": "timing", "systems": SYSTEMS, "pools": ["dev_actions"], "seeds": [1]}], "queue": QUEUE}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=["exam", "live_check", "timing"])
    parser.add_argument("--seeds", type=int, default=2)
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    spec = {"exam": lambda: exam_spec(args.seeds), "live_check": lambda: live_check_spec(args.model), "timing": timing_spec}[args.kind]()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
