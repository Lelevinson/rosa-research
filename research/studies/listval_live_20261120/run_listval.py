"""Runner adapter for the LISTVAL live test (protocol: PROTOCOL.md in this folder). Re-exports the thinking study's environment loader and episode-row builder; the arms come from listval_arm.py.

  uv run python research/studies/final_exam_draft_20261118/exam_queue/queue_core.py plan --spec .../specs/listval_spec.json
Plan: for every (model, environment) one fixture session holding both arms (FULL = switch off, LISTVAL = switch on) of every (task, seed 9 or 10) cell, adjacent, arm order alternated per cell.
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDIES / "loss_map_20261120"))
import listval_arm  # noqa: E402
import run_lossmap as LM  # noqa: E402  (re-exports the thinking runner T)
T = LM.T
think_arm = T.think_arm
run_pilot = T.run_pilot

load_env = T.load_env
MASTER_SEED = 20261120
SEEDS = [9, 10]
TASK_IDS = LM.TASK_IDS            # stage3 4 + e1h 6 + namefix 8 = 18 tasks
ARMS = listval_arm.ARMS           # ["FULL", "LISTVAL"]


def plan_for(phase):
    """{session name: [cells]}. One session per (model, environment). Inside a session the (task, seed) cells are shuffled (seeded by master seed, phase, model, environment); each cell is run
    as two adjacent episodes, and the arm that goes first alternates with the position of the cell (even position: FULL first, odd: LISTVAL first)."""
    assert phase == "listval", phase
    sessions = {}
    for model in T.MODELS:
        for env, tasks in TASK_IDS.items():
            pairs = [(task, seed) for task in tasks for seed in SEEDS]
            random.Random(f"{MASTER_SEED}-{phase}-{model}-{env}").shuffle(pairs)
            cells = []
            for position, (task, seed) in enumerate(pairs):
                order = ARMS if position % 2 == 0 else ARMS[::-1]
                cells += [dict(env=env, task=task, arm=arm, model=model, seed=seed, temperature=0.7) for arm in order]
            sessions[f"{model.replace(':', '_')}-{env}"] = cells
    return sessions


def run_worker(out, directory, cell, timeout, recorder):
    """Same as the thinking runner's worker, but the episode subprocess is this file (so the LISTVAL arm exists)."""
    import os, signal, subprocess, time
    timeout = T.EPISODE_TIMEOUT_SECONDS
    command = [sys.executable, str(HERE / "run_listval.py"), "episode", "--output", str(directory), "--env", cell["env"], "--task", cell["task"],
               "--arm", cell["arm"], "--model", cell["model"], "--seed", str(cell["seed"]), "--temperature", str(cell["temperature"])]
    recorder.add("worker_start", command=command)
    started, error = time.perf_counter(), None
    with (out / (directory.name + ".worker.log")).open("w") as log:
        worker = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = worker.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(worker.pid, signal.SIGTERM)
            try:
                worker.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(worker.pid, signal.SIGKILL)
                worker.wait()
            code, error = worker.returncode, f"{timeout}-second episode timeout"
    record = dict(directory=directory.name, returncode=code, error=error, seconds=time.perf_counter() - started, cell=cell)
    with (out / "attempts.jsonl").open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    print(json.dumps(record), flush=True)
    return record


def episode(args):
    think_arm.CURRENT_MODEL["name"] = args.model
    run_pilot.make_arm = listval_arm.make_arm
    run_pilot.ArmTracedModel = think_arm.ThinkTracedModel
    run_pilot.build_chat_model = think_arm.build_chat_model
    run_pilot.load_env = load_env
    run_pilot.episode(args)


def episode_row(phase, session, directory, attempt):
    """The thinking runner's row plus the LISTVAL exposure (inline lists, cap fallbacks, unreadable values, native reads made for them)."""
    row = T.episode_row(phase, session, directory, attempt)
    events = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
    inline = [e for e in events if e["kind"] == "handler" and e.get("event") == "listval_inline"]
    row["listval"] = dict(inline_lists=sum(bool(e.get("params")) for e in inline), over_cap=sum(e.get("reason") == "over_cap" for e in inline),
                          shown_params=sum(len(e.get("params", [])) for e in inline), unreadable=sum(e.get("unreadable", 0) for e in inline))
    return row


if __name__ == "__main__":
    if sys.argv[1] == "plan":
        plan = plan_for(sys.argv[2])
        print({k: len(v) for k, v in plan.items()}, "total", sum(map(len, plan.values())))
    elif sys.argv[1] == "episode":
        import argparse
        parser = argparse.ArgumentParser()
        for flag in ["--output", "--env", "--task", "--arm", "--model", "--temperature"]:
            parser.add_argument(flag, required=True)
        parser.add_argument("--seed", type=int, required=True)
        a = parser.parse_args(sys.argv[2:])
        a.temperature = float(a.temperature)
        episode(a)
