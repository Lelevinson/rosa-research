"""Smoke check against PROTOCOL_LIVE.md section 6 ('clean' criteria 1-3). Read-only.
  uv run python research/studies/canonical_render_20261118/smoke_check_live.py SMOKE_RUN_DIR
One line per check; exit 1 if any check fails."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_core as R  # noqa: E402

run = Path(sys.argv[1])
failures = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not condition:
        failures.append(name)


by_cell = {}
for trace in sorted(run.glob("*/*/trace.jsonl")):
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    start = next(e for e in events if e["kind"] == "episode_start")
    by_cell[(start["task"]["id"], start["arm"])] = dict(events=events, start=start)
tasks = sorted({t for t, _a in by_cell})
check("six episodes: three tasks x two arms", len(by_cell) == 6 and all((t, a) in by_cell for t in tasks for a in ("FULL", "RENDER")), str(sorted(by_cell)))
for (task, arm), ep in sorted(by_cell.items()):
    events = ep["events"]
    end = [e for e in events if e["kind"] == "episode_end"]
    check(f"{task}/{arm}: episode_end present and no worker error", bool(end) and not end[-1].get("error"), str(end[-1].get("error"))[:80] if end else "missing")
    renders = [e for e in events if e["kind"] == "handler" and e.get("event") == "render_applied"]
    outputs = [e["output"] for e in events if e["kind"] == "tool_end"]
    derived = sum(("full name: /" in json.dumps(o)) for o in outputs)
    if arm == "FULL":
        check(f"{task}/FULL: no render events and no derived lines", not renders and derived == 0, f"renders={len(renders)} derived={derived}")
    else:
        raw_renders = [R.render_result(e["raw"]) for e in renders]
        unmatched = [r for r in raw_renders if r not in outputs]
        check(f"{task}/RENDER: every render event equals the result returned to the model", not unmatched, f"events={len(renders)} unmatched={len(unmatched)}")
        check(f"{task}/RENDER: no result with a derived line lacks a render event", derived <= len(renders), f"derived={derived} events={len(renders)}")
for task in tasks:
    full, render = by_cell.get((task, "FULL")), by_cell.get((task, "RENDER"))
    if full and render:
        check(f"{task}: prompt hash identical across arms", full["start"]["prompt_sha256"] == render["start"]["prompt_sha256"])
        check(f"{task}: serialized prompts identical across arms", full["start"]["prompts"] == render["start"]["prompts"])
        offered = lambda ep: [e["names"] for e in ep["events"] if e["kind"] == "handler" and e.get("event") == "tools_offered"]
        check(f"{task}: tools offered identical on the first request", offered(full)[0] == offered(render)[0])
attempts = [json.loads(l) for p in sorted(run.glob("*/attempts.jsonl")) for l in p.read_text().splitlines()]
check("six attempts, return code 0, no timeout", len(attempts) == 6 and all(a["returncode"] == 0 and not a["error"] and a["seconds"] < 900 for a in attempts), str([round(a["seconds"]) for a in attempts]))
rendered_any = sum(1 for (_t, a), ep in by_cell.items() if a == "RENDER" for e in ep["events"] if e["kind"] == "handler" and e.get("event") == "render_applied")
print(f"\nINFO render events in the smoke: {rendered_any} (0 would mean the rendering was never exercised; report it)")
print("exit", 1 if failures else 0)
sys.exit(1 if failures else 0)
