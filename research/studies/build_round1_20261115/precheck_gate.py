"""Offline pre-check of the answer gate (no model, no ROS, no GPU).

Replays the 80 recorded fixed-loop (C1) pilot episodes (SAME_CELL_COMPARISON.json, scorer v2.0 labels, trace hashes already verified there)
through answer_gate.check_answer on the answer the episode actually ended with, and reports:
  - false rejections: scorer-v2 supported answers that the gate would have rejected on their first submission (target 0)
  - catches: unsupported answers that the gate would have rejected (not a claim that the model would then have fixed them)
Also: how many supported episodes ended with a bare-text finish (the nudge would have fired there; its effect cannot be replayed).
Tool outputs: only genuine tool results; harness error strings (invalid arguments, tool not offered, tool failed) are excluded because
they echo the model's own argument values. The task text is the task request text recorded in the trace; ground truth is never read.

  uv run python precheck_gate.py [--out precheck_gate.json]
"""
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import answer_gate  # noqa: E402

HARNESS_TEXT = re.compile(r"^(Invalid arguments|Tool \S+ (is not available|failed)|final_answer needs|Answer recorded)")


def load_episode(trace_path):
    events = [json.loads(line) for line in (ROOT / trace_path).read_text().splitlines()]
    task_text = next(e["request"] for e in events if e["kind"] == "effective_request")
    starts = {}
    outputs = []
    for e in events:
        key = e.get("run_id") or e.get("tool_run_id")
        if e["kind"] == "tool_start":
            starts[key] = e["name"]
        elif e["kind"] == "tool_end" and key in starts:
            output = e.get("output")
            if starts[key] in ("final_answer", "supertool"):
                continue
            if isinstance(output, str) and HARNESS_TEXT.match(output):
                continue
            outputs.append(output)
    accepted = [e for e in events if e["kind"] == "final_answer_accepted"]
    return dict(task_text=task_text, outputs=outputs, used_final_answer=bool(accepted))


def main(out_path):
    cells = json.loads((ROOT / "research/studies/forge_baseline_20261115/SAME_CELL_COMPARISON.json").read_text())
    rows = []
    for cell in cells:
        c1 = cell["C1"]
        episode = load_episode(c1["trace_path"])
        answer = c1.get("answer_object")
        result = answer_gate.check_answer(answer, episode["task_text"], episode["outputs"]) if isinstance(answer, dict) else None
        rows.append(dict(model=c1["model"], task=c1["task"], seed=c1["seed"], supported=c1["supported_complete"], used_final_answer=episode["used_final_answer"],
                         answer=answer, reject=bool(result and result["reject"]), problems=result["problems"] if result else None,
                         numbers_unseen=result["numbers_unseen"] if result else None))
    supported = [r for r in rows if r["supported"]]
    failed = [r for r in rows if not r["supported"]]
    summary = dict(episodes=len(rows), supported=len(supported), false_rejections=[r for r in supported if r["reject"]],
                   supported_bare_text_finish=sum(not r["used_final_answer"] for r in supported),
                   failed=len(failed), caught=[r for r in failed if r["reject"]],
                   numbers_unseen_in_supported=[r for r in supported if r["numbers_unseen"]], numbers_unseen_in_failed=[r for r in failed if r["numbers_unseen"]])
    Path(out_path).write_text(json.dumps(dict(summary=summary, rows=rows), indent=1))
    print(f"episodes {len(rows)}; supported {len(supported)}; FALSE REJECTIONS {len(summary['false_rejections'])}; supported bare-text finishes {summary['supported_bare_text_finish']}")
    print(f"failed {len(failed)}; would reject {len(summary['caught'])}; unseen numbers: supported {len(summary['numbers_unseen_in_supported'])}, failed {len(summary['numbers_unseen_in_failed'])}")
    for r in summary["false_rejections"]:
        print("FALSE REJECTION", r["model"], r["task"], r["seed"], json.dumps(r["answer"])[:200], [p["hint"] for p in r["problems"]])
    for r in summary["caught"]:
        print("caught", r["model"], r["task"], r["seed"], json.dumps(r["answer"])[:160], [p["rule"] for p in r["problems"]])


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else HERE / "precheck_gate.json")
