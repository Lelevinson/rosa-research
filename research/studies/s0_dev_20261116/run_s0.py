"""Stock ROSA, verbatim prompt (arm S0 of run_pilot.py: prompt = Stage 1 'A_orig', stock tools, stock executor) on the 80 pilot development cells.

  ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 uv run python run_s0.py run smoke|full OUTDIR     run, then collect into RESULTS_LOG.jsonl
  uv run python run_s0.py collect OUTDIR PHASE

Uses the pilot's own episode/session code unchanged (run_pilot.py): same Ollama settings (temperature 0.7, num_ctx 65536, num_predict 4096, think via the
pilot SDK default, 40-iteration cap, seeds 1 and 2), same fixture, oracle and cleanup checks, same observation-only guard that blocks write tools before ROS.
Scoring: frozen scorer v2.0.
"""
import hashlib
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(STUDIES / "small_model_harness_20261115"))
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
import run_pilot  # noqa: E402
import scorer_v2 as v2  # noqa: E402

REPO = HERE.parents[2]
LOG = HERE / "RESULTS_LOG.jsonl"
MASTER_SEED = 20261118
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
STAGE3_TASKS = ["u3", "p3", "h4", "v2"]
E1H_TASKS = ["e1h_amb_1", "e1h_amb_2", "e1h_abs_1", "e1h_abs_2", "e1h_chg_1", "e1h_chg_2"]
TASKS = {t["id"]: t for t in json.loads((STUDIES / "headroom_diagnostic_20261112/stage3_tasks.json").read_text())}
TASKS.update({t["id"]: t for t in json.loads((STUDIES / "small_model_harness_20261115/e1h_tasks.json").read_text())})


def plan_for(phase):
    sessions = {}
    for model in ([MODELS[1]] if phase == "smoke" else MODELS):
        for env, tasks in (("stage3", STAGE3_TASKS), ("e1h", E1H_TASKS)):
            if phase == "smoke":
                tasks = ["u3"] if env == "stage3" else ["e1h_amb_1"]
            cells = [dict(env=env, task=t, arm="S0", model=model, seed=s, temperature=0.7) for t in tasks for s in ([1] if phase == "smoke" else [1, 2])]
            random.Random(f"{MASTER_SEED}-{phase}-{model}-{env}").shuffle(cells)
            sessions[f"{model.replace(':', '_')}-{env}"] = cells
    return sessions


def episode_row(phase, session, directory, attempt):
    trace = directory / "trace.jsonl"
    events = v2.s1.read_events(trace)
    start = next(e for e in events if e["kind"] == "episode_start")
    task = TASKS[start["task"]["id"]]
    scored = v2.score_events(task, events)
    metrics = v2.s1.episode_metrics(events)
    end = [e for e in events if e["kind"] == "episode_end"]
    aborts = [x for x in [attempt.get("error"), end[-1].get("error") if end else "no episode_end"] if x]
    if metrics.get("iteration_cap"):
        aborts.append("iteration limit")
    return dict(run_id=f"{session}/{directory.name}", phase=phase, env=start["env"], task=task["id"], arm=start["arm"], model=start["model"], seed=start["seed"],
                temperature=start["temperature"], prompt_sha256=start["prompt_sha256"], scorer=scored["scorer"], supported_complete=scored["supported_complete"],
                exact=scored["exact"], issues=scored["issues"], support_missing=scored["support_missing"], answer=scored["answer_object"], answer_source=scored["answer_source"],
                llm_requests=metrics["requests"], input_tokens=metrics["input_tokens"], output_tokens=metrics["output_tokens"], native_ops=metrics["native_ops"],
                wall_seconds=round(attempt["seconds"], 2), aborts=aborts, trace_path=str(trace.relative_to(REPO)), trace_hash=hashlib.sha256(trace.read_bytes()).hexdigest())


def collect(run, phase):
    run = Path(run).resolve()
    have = {json.loads(l)["run_id"] for l in LOG.read_text().splitlines()} if LOG.exists() else set()
    added = 0
    with LOG.open("a") as handle:
        for session in sorted(p for p in run.iterdir() if p.is_dir() and (p / "attempts.jsonl").exists()):
            for line in (session / "attempts.jsonl").read_text().splitlines():
                attempt = json.loads(line)
                directory = session / attempt["directory"]
                run_id = f"{session.name}/{attempt['directory']}"
                if run_id in have or not (directory / "trace.jsonl").exists():
                    continue
                handle.write(json.dumps(episode_row(phase, session.name, directory, attempt), default=str) + "\n")
                added += 1
    print(f"added {added} episodes to {LOG.name}", flush=True)


def run(phase, out, only=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    plan = {k: v for k, v in plan_for(phase).items() if only is None or k in only}
    try:
        for name, cells in plan.items():
            path = out / f"plan_{name}.json"
            path.write_text(json.dumps(cells, indent=1))
            print(json.dumps(dict(event="session_start", session=name, cells=len(cells))), flush=True)
            run_pilot.session(out / name, path, wall_limit_hours=6.0)
            collect(out, phase)
    finally:
        collect(out, phase)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3], sys.argv[4:] or None)
    else:
        collect(sys.argv[2], sys.argv[3])
