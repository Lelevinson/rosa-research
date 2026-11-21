"""Smoke check against PROTOCOL.md section 3 ('clean' criteria). Read-only.
  uv run python research/studies/repeat_finish_nudge_20261118/smoke_check.py SMOKE_RUN_DIR
One line per check; exit 1 if any check fails."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nudge_arm as A  # noqa: E402

run = Path(sys.argv[1])
failures = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not condition:
        failures.append(name)


def parse(value):
    return value


by_cell = {}
for trace in sorted(run.glob("*/*/trace.jsonl")):
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    start = next(e for e in events if e["kind"] == "episode_start")
    by_cell[(start["task"]["id"], start["arm"])] = dict(events=events, start=start)
tasks = sorted({t for t, _a in by_cell})
check("four episodes: two tasks x two arms", len(by_cell) == 4 and all((t, a) in by_cell for t in tasks for a in A.ARMS), str(sorted(by_cell)))
fires_total = 0
for (task, arm), ep in sorted(by_cell.items()):
    events = ep["events"]
    end = [e for e in events if e["kind"] == "episode_end"]
    check(f"{task}/{arm}: episode_end present and no worker error", bool(end) and not end[-1].get("error"), str(end[-1].get("error"))[:80] if end else "missing")
    repeats = [e for e in events if e["kind"] == "handler" and e.get("event") == "identical_repeat"]
    outputs = [e["output"] for e in events if e["kind"] == "tool_end"]
    with_line = [o for o in outputs if A.NUDGE_LINE in json.dumps(o)]
    fired = [r for r in repeats if r["fired"]]
    if arm == "FULL":
        check(f"{task}/FULL: no nudge line and no fire", not with_line and not fired, f"lines={len(with_line)} fired={len(fired)}")
    else:
        fires_total += len(fired)
        check(f"{task}/NUDGE: number of results with the line equals the logged fires (<= {A.MAX_FIRES})", len(with_line) == len(fired) <= A.MAX_FIRES, f"lines={len(with_line)} fired={len(fired)}")
        # every line is exactly the fixed text: the output with the text removed is a clean result, never a rewritten one
        exact = all((o.endswith("\n" + A.NUDGE_LINE)) if isinstance(o, str) else True for o in with_line)
        check(f"{task}/NUDGE: string results carry the exact line after a newline", exact)
    # recompute detection from the trace: tool_start input + tool_end output, nudge line removed
    seen, recomputed = set(), 0
    starts = {e["tool_run_id"]: e for e in events if e["kind"] == "tool_start"}
    for e in events:
        if e["kind"] != "tool_end" or e["tool_run_id"] not in starts:
            continue
        name = starts[e["tool_run_id"]]["name"]
        if name not in A.MENU_TOOLS:
            continue
        key = (name, str(starts[e["tool_run_id"]]["input"]), str(A.strip_nudge(e["output"])))
        recomputed += key in seen
        seen.add(key)
    print(f"INFO {task}/{arm}: logged identical repeats={len(repeats)} recomputed from trace (approximate, ignores item-error filter)={recomputed}")
for task in tasks:
    full, nudge = by_cell.get((task, "FULL")), by_cell.get((task, "NUDGE"))
    if full and nudge:
        check(f"{task}: prompt hash identical across arms", full["start"]["prompt_sha256"] == nudge["start"]["prompt_sha256"])
        check(f"{task}: serialized prompts identical across arms", full["start"]["prompts"] == nudge["start"]["prompts"])
        offered = lambda ep: [e["names"] for e in ep["events"] if e["kind"] == "handler" and e.get("event") == "tools_offered"]
        check(f"{task}: tools offered identical on the first request", offered(full)[0] == offered(nudge)[0])
attempts = [json.loads(l) for p in sorted(run.glob("*/attempts.jsonl")) for l in p.read_text().splitlines()]
check("four attempts, return code 0, no timeout", len(attempts) == 4 and all(a["returncode"] == 0 and not a["error"] and a["seconds"] < 900 for a in attempts), str([round(a["seconds"]) for a in attempts]))
print(f"\nINFO nudge fires in the smoke: {fires_total} (0 means the fire path was not exercised live; report it)")
print("exit", 1 if failures else 0)
sys.exit(1 if failures else 0)
