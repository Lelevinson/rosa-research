"""Analysis of the finish-tool split run, applying the frozen reading rule of PROTOCOL.md section 4. CPU only.
  uv run python research/studies/finish_split_20261118/analyze_split.py [full|smoke]
Reads RESULTS_LOG.jsonl (rows of the phase), writes results.json (full) or results_smoke.json. Written after the protocol was hashed and before the full run ended; it adds no rule."""
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ["FULL", "TOOL_ONLY", "LINE_JSON"]
MODELS = ["bonsai-2:4b", "lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b"]


def ending(row):
    if row["exposure"]["final_answer_accepted"] >= 1:
        return "final_answer"
    return "none" if row["answer"] in (None, {}) else "text"


def aggregate(rows):
    return dict(episodes=len(rows), supported=sum(bool(r["supported_complete"]) for r in rows), requests=sum(r["llm_requests"] for r in rows),
                input_tokens=sum(r["input_tokens"] for r in rows), output_tokens=sum(r["output_tokens"] for r in rows),
                endings=dict(Counter(ending(r) for r in rows)), supported_by_ending={e: sum(bool(r["supported_complete"]) for r in rows if ending(r) == e) for e in ("final_answer", "text", "none")},
                finish_invalid=sum(r["exposure"]["final_answer_invalid"] for r in rows), tool_not_offered=sum(r["exposure"]["tool_not_offered"] for r in rows),
                capped_or_aborted=sum(1 for r in rows if r["aborts"]))


def reading(d_tool, d_line):
    """d_tool = FULL - TOOL_ONLY, d_line = FULL - LINE_JSON in supported cells. 'close' <= 3, 'separated' >= 6 (PROTOCOL.md section 4)."""
    close = lambda d: d <= 3
    separated = lambda d: d >= 6
    if close(d_tool) and separated(d_line):
        return 1, "the tool is sufficient and the prompt-only route loses cells"
    if close(d_line) and separated(d_tool):
        return 2, "the instruction route is sufficient and the tool alone loses cells"
    if close(d_tool) and close(d_line):
        return 3, "either component suffices; the earlier gap is not attributable to one of them"
    if separated(d_tool) and separated(d_line):
        return 4, "both parts are needed together"
    return 5, "inconclusive"


def main(phase="full"):
    rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
    rows = [r for r in rows if r["phase"] == phase]
    out = dict(protocol_sha256=(HERE / "PROTOCOL.sha256").read_text().split()[0], phase=phase, episodes=len(rows), overall={}, by_model={})
    for arm in ARMS:
        out["overall"][arm] = aggregate([r for r in rows if r["arm"] == arm])
        out["by_model"][arm] = {m: aggregate([r for r in rows if r["arm"] == arm and r["model"] == m]) for m in MODELS}
    cells = defaultdict(dict)
    for r in rows:
        cells[(r["task"], r["model"], r["seed"])][r["arm"]] = bool(r["supported_complete"])
    paired = {}
    for other in ("TOOL_ONLY", "LINE_JSON"):
        both = [c for c in cells.values() if "FULL" in c and other in c]
        paired[other] = dict(cells=len(both), both=sum(c["FULL"] and c[other] for c in both), FULL_only=sum(c["FULL"] and not c[other] for c in both),
                             other_only=sum(not c["FULL"] and c[other] for c in both), neither=sum(not c["FULL"] and not c[other] for c in both))
    out["paired"] = paired
    full, tool, line = (out["overall"][a]["supported"] for a in ARMS)
    out["d_tool"], out["d_line"] = full - tool, full - line
    if phase == "full":
        out["reading_rule_case"], out["reading_rule_text"] = reading(out["d_tool"], out["d_line"])
    (HERE / ("results.json" if phase == "full" else f"results_{phase}.json")).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("episodes", "d_tool", "d_line", "paired")}, indent=1))
    for arm in ARMS:
        a = out["overall"][arm]
        print(arm, a["episodes"], "supported", a["supported"], "requests", a["requests"], "tokens", a["input_tokens"] + a["output_tokens"], "endings", a["endings"])
    if phase == "full":
        print("reading rule case", out["reading_rule_case"], out["reading_rule_text"])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "full")
