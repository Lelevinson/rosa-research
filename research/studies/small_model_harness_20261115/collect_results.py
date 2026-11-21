"""Build RESULTS_LOG.jsonl (append-only, one line per episode) from the pilot run folders, and validate it.

  uv run python collect_results.py collect RUNDIR         add episodes that are not in the log yet (never rewrites existing lines)
  uv run python collect_results.py validate RUNDIR        schema, duplicate run ids, trace hashes, episode count vs attempts

Run id = <session folder>/<episode folder>. Traces stay in research/_artifacts (not in Git); the log keeps the path and the sha256 of each trace.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pilot_score as ps  # noqa: E402

LOG = HERE / "RESULTS_LOG.jsonl"
REPO = HERE.parents[2]
TASKS = {t["id"]: t for t in json.loads((HERE.parent / "headroom_diagnostic_20261112" / "stage3_tasks.json").read_text())}
TASKS.update({t["id"]: t for t in json.loads((HERE / "e1h_tasks.json").read_text())})
FIELDS = ["run_id", "env", "task", "arm", "model", "seed", "temperature", "supported_complete", "answer", "llm_requests", "input_tokens", "output_tokens",
          "native_ops", "wall_seconds", "aborts", "handler_fires", "failure_rows", "trace_path", "trace_hash"]


def interrupted_ids():
    path = HERE / "INFRA_EXCLUDED.json"
    return set(json.loads(path.read_text()).get("interrupted", {}).get("run_ids", [])) if path.exists() else set()


def existing_ids():
    return {json.loads(line)["run_id"] for line in LOG.read_text().splitlines()} if LOG.exists() else set()


def handler_fires(events):
    fires = []
    for e in events:
        if e["kind"] == "handler" and e["event"] not in ("tools_offered", "monitor_started", "monitor_stopped"):
            detail = {k: v for k, v in e.items() if k not in ("kind", "monotonic", "tool_run_id", "handler", "event")}
            fires.append(dict(event=e["event"], **detail))
        elif e["kind"] in ("scripted_change", "scripted_reset", "scripted_change_failed"):
            fires.append(dict(event=e["kind"], **{k: v for k, v in e.items() if k not in ("kind", "monotonic", "tool_run_id")}))
    monitor = [e for e in events if e["kind"] == "handler" and e["event"] in ("monitor_started", "monitor_stopped")]
    if monitor:
        fires.append(dict(event="monitor_overhead", details=[{k: v for k, v in e.items() if k in ("event", "startup_seconds", "events_seen", "seconds")} for e in monitor]))
    return fires


def episode_row(session, directory, attempt):
    trace = directory / "trace.jsonl"
    events = ps.s1.read_events(trace)
    start = next(e for e in events if e["kind"] == "episode_start")
    task = TASKS[start["task"]["id"]]
    scored = ps.score_events(task, events)
    metrics = scored["metrics"]
    end = [e for e in events if e["kind"] == "episode_end"]
    aborts = [x for x in [attempt.get("error"), end[-1].get("error") if end else "no episode_end"] if x]
    hit_cap = bool(metrics.get("iteration_cap"))
    if hit_cap:
        aborts.append("iteration limit")
    return dict(run_id=f"{session}/{directory.name}", env=start["env"], task=task["id"], arm=start["arm"], model=start["model"], seed=start["seed"],
                temperature=start["temperature"], supported_complete=scored["supported_complete"], answer=scored["answer_object"],
                llm_requests=metrics["requests"], input_tokens=metrics["input_tokens"], output_tokens=metrics["output_tokens"], native_ops=metrics["native_ops"],
                wall_seconds=round(attempt["seconds"], 2), aborts=aborts, handler_fires=handler_fires(events),
                failure_rows=ps.failure_rows(task, events, scored) if not scored["supported_complete"] else [],
                trace_path=str(trace.relative_to(REPO)), trace_hash=hashlib.sha256(trace.read_bytes()).hexdigest())


def collect(run):
    run, have, added, skipped = Path(run).resolve(), existing_ids(), 0, []
    with LOG.open("a") as handle:
        for session in sorted(p for p in run.iterdir() if p.is_dir() and (p / "attempts.jsonl").exists()):
            for line in (session / "attempts.jsonl").read_text().splitlines():
                attempt = json.loads(line)
                run_id = f"{session.name}/{attempt['directory']}"
                directory = session / attempt["directory"]
                if run_id in have or run_id in interrupted_ids():
                    continue
                if not (directory / "trace.jsonl").exists():
                    skipped.append(run_id)
                    continue
                handle.write(json.dumps(episode_row(session.name, directory, attempt), default=str) + "\n")
                added += 1
    print(f"added {added}, skipped without trace {len(skipped)}", skipped[:3])


def validate(run):
    run, problems, rows = Path(run).resolve(), [], []
    for line in LOG.read_text().splitlines():
        rows.append(json.loads(line))
    ids = [r["run_id"] for r in rows]
    if len(ids) != len(set(ids)):
        problems.append("duplicate run ids")
    for r in rows:
        missing = [f for f in FIELDS if f not in r]
        if missing:
            problems.append(f"{r['run_id']}: missing fields {missing}")
            continue
        trace = REPO / r["trace_path"]
        if not trace.exists():
            problems.append(f"{r['run_id']}: trace missing")
        elif hashlib.sha256(trace.read_bytes()).hexdigest() != r["trace_hash"]:
            problems.append(f"{r['run_id']}: trace hash differs")
    attempts = sum(len((s / "attempts.jsonl").read_text().splitlines()) for s in run.iterdir() if s.is_dir() and (s / "attempts.jsonl").exists())
    print(f"{len(rows)} log rows, {attempts} attempts in run folders, {len(problems)} problems")
    for p in problems[:20]:
        print(" ", p)
    return not problems


if __name__ == "__main__":
    {"collect": collect, "validate": validate}[sys.argv[1]](sys.argv[2])
