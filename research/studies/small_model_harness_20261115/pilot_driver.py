"""Step D driver: builds the shuffled plans, runs one fixture session per (model, environment) and enforces the 10-hour wall limit.

  uv run python pilot_driver.py OUTDIR            (ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 must be set)

Plan (build document section 5): tasks u3, p3, h4, v2 (Stage 3 fixture) and the six E1h tasks; arms A1, C1, M0, C1+FN, C1+H2, C1+H1e, C1+H7 on all ten
tasks, plus C1+H1n on the two changing-parameter tasks; seeds 1 and 2; temperature 0.7. The order inside each (model, environment) session is shuffled
with a seed derived from MASTER_SEED and recorded in plans/. Models run in the order lfm3, qwen3.5, gpt-oss, bonsai so that a time-out costs the
optional model last. Stop rules (RuntimeError from the session): Ollama unreachable, oracle mismatch, write command reached ROS, wall limit.
"""
import json
from pathlib import Path
import random
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_pilot  # noqa: E402

MASTER_SEED = 20261116
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
STAGE3_TASKS = ["u3", "p3", "h4", "v2"]
E1H_TASKS = ["e1h_amb_1", "e1h_amb_2", "e1h_abs_1", "e1h_abs_2", "e1h_chg_1", "e1h_chg_2"]
ARMS = ["A1", "C1", "M0", "C1+FN", "C1+H2", "C1+H1e", "C1+H7"]
SEEDS = [1, 2]
TEMPERATURE = 0.7
WALL_HOURS = 10.0


def plan_for(model, env):
    tasks = STAGE3_TASKS if env == "stage3" else E1H_TASKS
    cells = [dict(env=env, task=t, arm=a, model=model, seed=s, temperature=TEMPERATURE) for t in tasks for a in ARMS for s in SEEDS]
    if env == "e1h":
        cells += [dict(env=env, task=t, arm="C1+H1n", model=model, seed=s, temperature=TEMPERATURE) for t in ("e1h_chg_1", "e1h_chg_2") for s in SEEDS]
    random.Random(f"{MASTER_SEED}-{model}-{env}").shuffle(cells)
    return cells


def done_cells():
    """Cells (model, env, task, arm, seed) that already have a valid row in RESULTS_LOG.jsonl. Rows listed in INFRA_EXCLUDED.json (infrastructure
    failure, superseded protocol, interrupted) do not count as done, so those cells are run again."""
    log = HERE / "RESULTS_LOG.jsonl"
    excluded = set()
    if (HERE / "INFRA_EXCLUDED.json").exists():
        for group in json.loads((HERE / "INFRA_EXCLUDED.json").read_text()).values():
            excluded |= set(group.get("run_ids", []))
    done = set()
    if log.exists():
        for line in log.read_text().splitlines():
            r = json.loads(line)
            if r["run_id"] not in excluded:
                done.add((r["model"], r["env"], r["task"], r["arm"], r["seed"]))
    return done


def remaining_plan(model, env, resume):
    plan = plan_for(model, env)
    if not resume:
        return plan
    done = done_cells()
    return [c for c in plan if (c["model"], c["env"], c["task"], c["arm"], c["seed"]) not in done]


def model_runs(model):
    """A tiny request; used to skip a model whose runner crashes (gpt-oss had a CUDA runner fault on the host)."""
    try:
        body = json.dumps(dict(model=model, prompt="hi", stream=False, options=dict(num_predict=5))).encode()
        request = urllib.request.Request(run_pilot.S1.OLLAMA + "/api/generate", data=body, headers={"Content-Type": "application/json"})
        reply = json.load(urllib.request.urlopen(request, timeout=300))
        return "error" not in reply, reply.get("error")
    except Exception as failure:
        try:
            return False, json.loads(failure.read()).get("error") if hasattr(failure, "read") else repr(failure)
        except Exception:
            return False, repr(failure)


def main(out, models=None, used_hours=0.0, resume=False, tag=""):
    """models/used_hours let a second call continue the same 10-hour budget (hours already spent are subtracted)."""
    global MODELS
    MODELS = models or MODELS
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "plans").mkdir()
    started = time.time() - used_hours * 3600
    log = out / "driver.jsonl"

    def note(**values):
        with log.open("a") as handle:
            handle.write(json.dumps(dict(utc=time.strftime("%Y-%m-%dT%H:%M:%S%z"), **values)) + "\n")
        print(json.dumps(values), flush=True)

    note(event="start", master_seed=MASTER_SEED, models=MODELS, wall_hours=WALL_HOURS)
    skipped = []
    for model in MODELS:
        ok, why = model_runs(model)
        note(event="model_probe", model=model, ok=ok, error=why)
        if not ok:
            skipped.append(model)
            continue
        for env in ("stage3", "e1h"):
            remaining = WALL_HOURS - (time.time() - started) / 3600
            if remaining <= 0.05:
                note(event="wall_limit", model=model, env=env)
                return
            plan = remaining_plan(model, env, resume)
            if not plan:
                note(event="session_skipped_nothing_left", model=model, env=env)
                continue
            name = f"{model.replace(':', '_')}-{env}{tag}"
            plan_path = out / "plans" / f"{name}.json"
            plan_path.write_text(json.dumps(plan, indent=1))
            note(event="session_start", session=name, cells=len(plan), remaining_hours=round(remaining, 2))
            try:
                run_pilot.session(out / name, plan_path, wall_limit_hours=remaining)
            except Exception as failure:
                note(event="session_stopped", session=name, error=repr(failure))
                return
            note(event="session_done", session=name)
    for model in skipped:  # one more attempt for a model whose runner failed at the start
        remaining = WALL_HOURS - (time.time() - started) / 3600
        ok, why = model_runs(model)
        note(event="model_reprobe", model=model, ok=ok, error=why)
        if not ok or remaining <= 0.05:
            continue
        for env in ("stage3", "e1h"):
            plan = remaining_plan(model, env, resume)
            if not plan:
                continue
            name = f"{model.replace(':', '_')}-{env}{tag}"
            (out / "plans" / f"{name}.json").write_text(json.dumps(plan, indent=1))
            try:
                run_pilot.session(out / name, out / "plans" / f"{name}.json", wall_limit_hours=WALL_HOURS - (time.time() - started) / 3600)
            except Exception as failure:
                note(event="session_stopped", session=name, error=repr(failure))
                return
    note(event="all_done", hours=round((time.time() - started) / 3600, 2))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--models", nargs="+")
    parser.add_argument("--used-hours", type=float, default=0.0)
    parser.add_argument("--resume", action="store_true", help="skip cells that already have a valid row in RESULTS_LOG.jsonl")
    parser.add_argument("--tag", default="", help="suffix for session folder names (keeps run ids unique across resumes)")
    parser.add_argument("--dry-run", action="store_true", help="list what would run (per model, environment, arm) and exit; nothing is started")
    args = parser.parse_args()
    if args.dry_run:
        total = 0
        for model in args.models or MODELS:
            for env in ("stage3", "e1h"):
                plan = remaining_plan(model, env, args.resume)
                counts = {}
                for c in plan:
                    counts[c["arm"]] = counts.get(c["arm"], 0) + 1
                total += len(plan)
                print(f"{model} {env}: {len(plan)} cells", counts)
        print("total", total)
        sys.exit(0)
    main(args.output, args.models, args.used_hours, args.resume, args.tag)
