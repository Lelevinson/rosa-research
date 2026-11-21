"""Smoke check against the frozen protocol, section 5 ('clean' criteria 1-3). Read-only.  uv run python research/studies/finish_split_20261118/smoke_check.py SMOKE_RUN_DIR
Prints one line per check and exits 1 if any check fails."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import split_arms as A  # noqa: E402

run = Path(sys.argv[1])
failures = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not condition:
        failures.append(name)


episodes = {}
for trace in sorted(run.glob("*/*/trace.jsonl")):
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    start = next(e for e in events if e["kind"] == "episode_start")
    episodes[start["arm"]] = dict(events=events, start=start, trace=trace)
check("three arms present", sorted(episodes) == sorted(A.ARMS), str(sorted(episodes)))
prompts = {arm: [tuple(m) for m in ep["start"]["prompts"]] for arm, ep in episodes.items()}
for arm, ep in episodes.items():
    events = ep["events"]
    check(f"{arm}: has episode_end", any(e["kind"] == "episode_end" for e in events))
    end = [e for e in events if e["kind"] == "episode_end"][-1]
    check(f"{arm}: no worker error in episode_end", not end.get("error"), str(end.get("error"))[:80])
    offered = [e["names"] for e in events if e["kind"] == "handler" and e.get("event") == "tools_offered"]
    check(f"{arm}: tools_offered logged on every request", len(offered) == sum(e["kind"] == "model_start" for e in events) and len(offered) > 0)
    has_final = [("final_answer" in names) for names in offered]
    expected = arm != "LINE_JSON"
    check(f"{arm}: final_answer {'offered' if expected else 'NOT offered'} on every request", all(h == expected for h in has_final))
    accepted = sum(e["kind"] == "final_answer_accepted" for e in events)
    check(f"{arm}: finish path as designed", (accepted >= 1) if expected else (accepted == 0), f"accepted={accepted}")
    text = " ".join(m[1] for m in prompts[arm])
    check(f"{arm}: prompt finish text as designed",
          ("final_answer" in text) if arm == "FULL" else ("final_answer" not in text), f"{'contains' if 'final_answer' in text else 'no'} 'final_answer'")
check("FULL prompt = base + FINAL_ANSWER_LINE", prompts["FULL"][-1] == A.harness.FINAL_ANSWER_LINE)
base = prompts["FULL"][:-1]
check("TOOL_ONLY prompt = base", prompts["TOOL_ONLY"] == base)
check("LINE_JSON prompt = base + JSON-only line", prompts["LINE_JSON"] == base + [A.JSON_ONLY_LINE])
attempts = [json.loads(l) for p in sorted(run.glob("*/attempts.jsonl")) for l in p.read_text().splitlines()]
check("three attempts, return code 0, no timeout", len(attempts) == 3 and all(a["returncode"] == 0 and not a["error"] and a["seconds"] < 900 for a in attempts), str([round(a["seconds"]) for a in attempts]))
print("\nexit", 1 if failures else 0)
sys.exit(1 if failures else 0)
