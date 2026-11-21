"""Forge smoke gate (PROTOCOL_DRAFT section 2b, freeze-prep 9d-5): released Forge 0.10.1 through the pilot's unchanged `run_full.py` (copied here byte for byte so that its
append-only logs land in THIS folder, not in the frozen 2026-11-15 pilot folder). Public development tasks only: 3 tasks x 2 models x seed 1 = 6 episodes, one fixture session per
(model, environment). Label: smoke gate, no scores used. Run with the isolated Forge interpreter (forge-guardrails 0.10.1):

  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 /tmp/rosa-forge-env-20261121/bin/python gate_driver.py OUTDIR
"""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_full as F  # noqa: E402

MODELS = ["lfm3:1.7b", "qwen3.5:9b"]
TASKS = {"stage3": ["u3", "p3"], "e1h": ["e1h_amb_1"]}

if __name__ == "__main__":
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    for name, cells in F.FROZEN_PLAN["sessions"].items():
        model, env = name.rsplit("-", 1)
        if model not in MODELS or (os.environ.get("GATE_ONLY") and name != os.environ["GATE_ONLY"]):  # GATE_ONLY=<session name>: continue after a stopped session
            continue
        chosen = [c for c in cells if c["seed"] == 1 and c["task"] in TASKS[env]]
        print(json.dumps(dict(event="session_start", name=name, cells=[c["task"] for c in chosen])), flush=True)
        F.session(out / name.replace(":", "_"), chosen, time.time() + 3600)
    print(json.dumps(dict(event="gate_complete")), flush=True)
