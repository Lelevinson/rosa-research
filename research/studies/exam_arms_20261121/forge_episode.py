"""One released-Forge episode for the exam queue (system F). Runs under the isolated Forge interpreter (forge-guardrails 0.10.1), NOT the project environment:

  ~/.local/share/rosa-exam/forge-env/bin/python forge_episode.py OUTPUT_DIR ENV TASK MODEL SEED

The episode itself is `episode()` of the 2026-11-15 pilot runner `forge_baseline_20261115/run_full.py`, imported from that frozen file and called UNCHANGED (same 12 read tools + released
`respond`, same C1 system messages with final_answer -> respond, same matched transport, same 40-call budget). Only one thing is redirected: that function appends a transport-check
line to a file in the runner's own folder; here the folder variable HERE is pointed at the output directory's parent so the frozen pilot folder is not written to.
Differences from the pilot's own session driver (`run_full.session`) are in the queue, not here: the queue's `run_pilot.session` starts the fixtures and reads the oracle with the same
5 s retry as every other arm (`run_round2.OracleWithRetry`); the pilot driver's oracle had only a CLI-timeout retry without the 5 s wait (see REPORT_BASELINE_ADAPTERS.md).
"""
import asyncio
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT_RUNNER = HERE.parent / "forge_baseline_20261115" / "run_full.py"


def load_pilot_runner():
    spec = importlib.util.spec_from_file_location("forge_pilot_run_full", PILOT_RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(PILOT_RUNNER.parent))  # the pilot file's own sibling imports, as when it is run directly
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    output, env, task, model, seed = sys.argv[1:6]
    runner = load_pilot_runner()
    runner.HERE = Path(output).resolve().parent  # transport-check log goes next to the episode folders, not into the frozen pilot folder
    asyncio.run(runner.episode(Path(output).resolve(), dict(env=env, task=task, model=model, seed=int(seed))))
