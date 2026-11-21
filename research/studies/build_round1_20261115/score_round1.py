"""Scoring adapter for round 1 episodes: frozen scorer v2.0 (scorer_v2.py, unchanged) plus ONE expansion step.

A list-argument call is one tool call for the model but several original calls. The harness logs each item as a 'list_item' handler event; this adapter
turns those back into one ordinary single-entity row per item (same name/args/output shape as any other call) before calling scorer v2's
score_task, so a fact read through a list call counts exactly as if it had been read by a single call. Nothing else is changed.
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
sys.path.insert(0, str(STUDIES / "small_model_harness_20261115"))
import json  # noqa: E402

import pilot_score as ps  # noqa: E402  (metrics only)
import scorer_v2 as v2  # noqa: E402


def expanded_rows(events):
    rows = v2.tool_rows(events)
    starts = [e for e in events if e["kind"] == "tool_start"]
    ends = {e.get("run_id") for e in events if e["kind"] == "tool_end"}
    paired = [s for s in starts if s.get("run_id") in ends]
    items_by_run = {}
    for e in events:
        if e["kind"] == "handler" and e.get("event") == "list_item":
            items_by_run.setdefault(e.get("tool_run_id"), []).append(e)
    out = []
    for row, start in zip(rows, paired):
        items = items_by_run.get(start.get("run_id"))
        if not items:
            out.append(row)
            continue
        for item in items:
            text = json.dumps(item["output"]) if not isinstance(item["output"], str) else item["output"]
            out.append(dict(name=item["tool"], args=item["args"], given_args=item["args"], output=item["output"], text=text,
                            ok=not v2.s1.ERROR.search(text), line=row["line"]))
    return out


def score_events(task, events):
    answer, source = v2.episode_answer(events)
    scored = v2.score_task(task, answer, expanded_rows(events))
    scored.update(answer_object=answer, answer_source=source, metrics=ps.s1.episode_metrics(events))
    return scored
