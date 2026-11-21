"""Rerun the lfm3 cells that were infrastructure failures (C1+H1e on E1h) or superseded (C1+H7 version 1), under new run ids in a new run folder.

  uv run python pilot_repair.py OUTDIR      (ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1)
Same seeds, temperature and shuffle rule as pilot_driver.py; the first-run episodes stay in RESULTS_LOG.jsonl (listed in INFRA_EXCLUDED.json).
"""
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pilot_driver as D  # noqa: E402
import run_pilot  # noqa: E402

MODEL = "lfm3:1.7b"


def cells(env):
    tasks = D.STAGE3_TASKS if env == "stage3" else D.E1H_TASKS
    arms = ["C1+H7"] + (["C1+H1e"] if env == "e1h" else [])
    out = [dict(env=env, task=t, arm=a, model=MODEL, seed=s, temperature=D.TEMPERATURE) for t in tasks for a in arms for s in D.SEEDS]
    random.Random(f"{D.MASTER_SEED}-repair-{MODEL}-{env}").shuffle(out)
    return out


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=False)
    (out / "plans").mkdir()
    for env in ("stage3", "e1h"):
        plan = cells(env)
        path = out / "plans" / f"{env}.json"
        path.write_text(json.dumps(plan, indent=1))
        print(env, len(plan), "cells", flush=True)
        run_pilot.session(out / f"lfm3_repair-{env}", path, wall_limit_hours=2.0)
