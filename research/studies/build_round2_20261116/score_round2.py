"""Scoring adapter for round 2 episodes: frozen scorer v2.0 (scorer_v2.py, unchanged) plus ONE expansion step, like round 1's score_round1.py.

A sweep appends the results of other names to the triggering call's result. For scoring, the triggering call keeps its ORIGINAL result (stored in the
`sweep_fire` event) and every swept name becomes one ordinary single-entity row (same tool, same other arguments, the raw result the tool returned for it), so a
fact read through a sweep counts exactly as if the model had read it with a single call. Episodes without a sweep give exactly scorer v2.0's rows.
The submitted answer is scored as it is; if the shadow rewrite changed it, the rewritten answer is scored on the same rows (`rewritten`).
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(STUDIES / "build_round1_20261115"))
import score_round1  # noqa: E402  (puts scorer_v2 and the pilot scoring on sys.path)
import scorer_v2 as v2  # noqa: E402

ps = score_round1.ps


def expanded_rows(events):
    assert not any(e["kind"] == "handler" and e.get("event") == "list_item" for e in events), "round 2 arms have no list arguments"
    rows = v2.tool_rows(events)
    starts = [e for e in events if e["kind"] == "tool_start"]
    ends = {e.get("run_id") for e in events if e["kind"] == "tool_end"}
    paired = [s for s in starts if s.get("run_id") in ends]
    fires = {e.get("tool_run_id"): e for e in events if e["kind"] == "handler" and e.get("event") == "sweep_fire"}
    out = []
    for row, start in zip(rows, paired):
        fire = fires.get(start.get("run_id"))
        if fire is None:
            out.append(row)
            continue
        original = fire["original_output"]
        text = original if isinstance(original, str) else json.dumps(original)
        out.append(dict(row, output=original, text=text, ok=not v2.s1.ERROR.search(text)))
        for item in fire["items"]:
            item_text = item["output"] if isinstance(item["output"], str) else json.dumps(item["output"])
            out.append(dict(name=fire["tool"], args=item["args"], given_args=item["args"], output=item["output"], text=item_text,
                            ok=not v2.s1.ERROR.search(item_text), line=row["line"]))
    return out


def score_events(task, events):
    answer, source = v2.episode_answer(events)
    rows = expanded_rows(events)
    scored = v2.score_task(task, answer, rows)
    scored.update(answer_object=answer, answer_source=source, metrics=ps.s1.episode_metrics(events))
    shadow = [e for e in events if e["kind"] == "handler" and e.get("event") == "rewrite_shadow"]
    if shadow and shadow[-1]["changed"]:
        scored["rewritten"] = dict(answer=shadow[-1]["rewritten"], **{k: v for k, v in v2.score_task(task, shadow[-1]["rewritten"], rows).items() if k != "scorer"})
    return scored
