"""Smoke check for amendment A2 (6 episodes: qwen3.5, u3 and nf_single_1, seed 3, three arms). Derived from smoke_check.py; against PROTOCOL.md section 3 ('clean' criteria). Read-only.
  uv run python research/studies/thinking_escalation_20261119/smoke_check.py SMOKE_RUN_DIR
One line per check; exit 1 if any check fails."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import think_arm as A  # noqa: E402

run = Path(sys.argv[1])
failures = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not condition:
        failures.append(name)


cells = {}
for trace in sorted(run.glob("*/*/trace.jsonl")):
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    start = next(e for e in events if e["kind"] == "episode_start")
    cells[(start["model"], start["task"]["id"], start["arm"])] = dict(events=events, start=start, path=trace)
ARMS3 = ("FULL", "ESCALATE", "ESCALATE_CAPPED")
check("six episodes: 1 model x 2 tasks x 3 arms", len(cells) == 6, str(len(cells)))
totals = {"fires": 0, "escalated": 0, "reasoning_seen": 0, "escalated_without_reasoning": 0}
for (model, task, arm), ep in sorted(cells.items()):
    events, tag = ep["events"], f"{model}/{task}/{arm}"
    end = [e for e in events if e["kind"] == "episode_end"]
    check(f"{tag}: episode_end present and no worker error", bool(end) and not end[-1].get("error"), str(end[-1].get("error"))[:80] if end else "missing")
    starts = [e for e in events if e["kind"] == "model_start"]
    ends = [e for e in events if e["kind"] == "model_end"]
    levels = [e["level"] for e in events if e["kind"] == "handler" and e.get("event") == "think_request"]
    options = [(e.get("options") or {}).get("reasoning") for e in starts]
    on = A.thinking_on_value(model)
    check(f"{tag}: one think_request and one model_start per request", len(levels) == len(starts), f"{len(levels)} vs {len(starts)}")
    check(f"{tag}: options logged in model_start equal the think_request levels", options == levels, f"{options[:6]} vs {levels[:6]}")
    # simulate the window from the logged call_class events
    triggers = {}
    for e in events:
        if e["kind"] == "handler" and e.get("event") == "call_class" and e["klass"] != "ok":
            triggers[e["request"]] = True
    remaining, expected, sent, capped = 0, [], 0, False
    for i in range(1, len(starts) + 1):
        use = arm == "ALWAYS" or (arm in ("ESCALATE", "ESCALATE_CAPPED") and remaining > 0)
        if use and arm == "ESCALATE_CAPPED" and sent >= A.CAP:
            use, remaining, capped = False, 0, True
        expected.append(on if use else None)
        if use and arm != "ALWAYS":
            sent += 1
        if arm in ("ESCALATE", "ESCALATE_CAPPED") and remaining > 0 and use:
            remaining -= 1
        if arm in ("ESCALATE", "ESCALATE_CAPPED") and triggers.get(i) and not capped:
            remaining = A.WINDOW
    check(f"{tag}: levels equal the protocol window recomputed from the trigger events", levels == expected, f"{levels[:8]} vs {expected[:8]}")
    if arm == "FULL":
        check(f"{tag}: no override on any request", all(v is None for v in levels))
    totals["fires"] += sum(1 for e in events if e["kind"] == "handler" and e.get("event") == "trigger_fire")
    for index, (s, m) in enumerate(zip(starts, ends)):
        content = m["message"].get("content") or ""
        check(f"{tag}: request {index + 1} content has no think tag", "<think>" not in content and "</think>" not in content)
        if levels[index] is not None:
            totals["escalated"] += 1
            if (m["message"].get("additional_kwargs") or {}).get("reasoning_content"):
                totals["reasoning_seen"] += 1
            else:
                totals["escalated_without_reasoning"] += 1
    outputs = [json.loads(json.dumps(e["output"])) for e in events if e["kind"] == "tool_end"]
    names = {e["tool_run_id"]: e["name"] for e in events if e["kind"] == "tool_start"}
    menu_outputs = [e["output"] for e in events if e["kind"] == "tool_end" and names.get(e["tool_run_id"]) in A.MENU_TOOLS]
    recomputed = {k: sum(1 for o in menu_outputs if not isinstance(o, str) or True and A.classify_result(o) == k) for k in ("not_found", "empty")}
    logged = {k: sum(1 for e in events if e["kind"] == "handler" and e.get("event") == "call_class" and e["klass"] == k) for k in ("not_found", "empty")}
    check(f"{tag}: logged not_found / empty counts do not exceed the recomputed ones from tool outputs", all(logged[k] <= recomputed[k] for k in logged), f"logged={logged} recomputed={recomputed}")
for model in sorted({m for m, _t, _a in cells}):
    for task in sorted({t for _m, t, _a in cells}):
        trio = [cells.get((model, task, a)) for a in ARMS3]
        if all(trio):
            check(f"{model}/{task}: prompt hash and serialized prompts identical across the 3 arms", len({t["start"]["prompt_sha256"] for t in trio}) == 1 and len({json.dumps(t["start"]["prompts"]) for t in trio}) == 1)
            first = lambda t: [e["names"] for e in t["events"] if e["kind"] == "handler" and e.get("event") == "tools_offered"][0]
            check(f"{model}/{task}: tools offered on request 1 identical across the 3 arms", len({json.dumps(first(t)) for t in trio}) == 1)
            schemas = [json.dumps([e["schemas"] for e in t["events"] if e["kind"] == "model_start"][0], sort_keys=True) for t in trio]
            check(f"{model}/{task}: tool schemas sent on request 1 identical across the 3 arms", len(set(schemas)) == 1)
nf = [k for k in cells if k[1].startswith("nf_")]
check("name-fix episodes ran for all three arms", sorted(a for _m, t, a in nf) == sorted(ARMS3), str(sorted(a for _m, t, a in nf)))
attempts = [json.loads(l) for p in sorted(run.glob("*/attempts.jsonl")) for l in p.read_text().splitlines()]
check("six attempts, return code 0, no timeout (limit 1800 s)", len(attempts) == 6 and all(a["returncode"] == 0 and not a["error"] and a["seconds"] < 1800 for a in attempts), str(sorted(round(a["seconds"]) for a in attempts)))
print(f"\nINFO trigger fires over the 12 episodes: {totals['fires']}; escalated/always requests: {totals['escalated']}; with reasoning_content: {totals['reasoning_seen']}; without: {totals['escalated_without_reasoning']}")
print("INFO seconds by arm:", {a: round(sum(x["seconds"] for x in attempts if x["cell"]["arm"] == a)) for a in ARMS3})
print("exit", 1 if failures else 0)
sys.exit(1 if failures else 0)
