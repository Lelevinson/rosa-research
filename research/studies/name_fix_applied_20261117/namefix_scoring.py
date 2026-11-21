"""Dual scoring of the name-fix test (frozen before any model result; PROTOCOL 'Dual scoring').

STRICT (primary) = scorer v2.0 unchanged (`residual_failures_20261115/scorer_v2.py`, SHA-256 c6b02716...). The adapter only builds the inputs v2 expects from a trace: the task dict of the new fixture has exactly the
format of the E1h tasks (`answer`, `support`), so the adapter is the identity on rules; it swaps the answer of the episode (original or submitted) and calls `v2.score_events`. No v2 rule is changed.

LENIENT (secondary) = the same completeness, evidence, value, type, absence and extra-key rules as strict (it calls the same `v2.score_task` on a transformed answer); the ONLY relaxation: a string at a
name-bearing position (a value, or a nested object key, where the task's required identity is a full name of the independently known task-time graph) that is a RELATIVE name (no leading slash) and a
whole-path-segment suffix of that required name, and resolves UNIQUELY among the graph names of the same kind, is replaced by the required name. Not eligible: absolute names, a suffix shared by
two graph names of the kind, a wrong entity, a required name that is not in the graph (absent-name tasks), unrelated strings, wrong values. The graph is evaluator-only.
"""
import copy
import json
import re
import sys
from pathlib import Path

STUDIES = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
import scorer_v2 as v2  # noqa: E402

RELATIVE = re.compile(r"(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+")


def graph_names(graph):
    nodes = {n["fqn"] for n in graph["nodes"]}
    topics = {t["name"] for n in graph["nodes"] for t in n["pubs"] + n["subs"]}
    return {"node": nodes, "topic": topics}


def kind_of(name, names):
    return next((k for k, v in names.items() if name in v), None)


def resolve(value, truth, names):
    """The required full name if `value` is an eligible short form of it, else None."""
    if not (isinstance(value, str) and isinstance(truth, str)) or value == truth or not RELATIVE.fullmatch(value):
        return None
    kind = kind_of(truth, names)
    if kind is None or not truth.endswith("/" + value):
        return None
    candidates = [n for n in names[kind] if n.endswith("/" + value)]
    return truth if candidates == [truth] else None


def lenient_transform(answer, truth, names):
    """Answer with eligible short forms replaced by the required identity; returns (answer, list of replaced paths)."""
    changes = []

    def walk(a, t, path):
        if isinstance(a, dict) and isinstance(t, dict):
            out = {}
            for key, value in a.items():
                target = key
                if key not in t:
                    hit = [tk for tk in t if resolve(key, tk, names) and tk not in a]
                    if len(hit) == 1:
                        target = hit[0]
                        changes.append(f"{path}.key:{key}->{target}")
                out[target] = walk(value, t.get(target), f"{path}.{target}")
            return out
        if isinstance(a, list) and isinstance(t, list) and len(a) == len(t):
            return [walk(x, y, f"{path}[{i}]") for i, (x, y) in enumerate(zip(a, t))]
        full = resolve(a, t, names)
        if full:
            changes.append(f"{path}:{a}->{full}")
            return full
        return a

    return walk(copy.deepcopy(answer), truth, ""), changes


def score(task, answer, rows, graph=None):
    """strict (v2) and, when a graph is given, lenient scoring of one answer object on the same rows."""
    out = dict(strict=v2.score_task(task, answer, rows))
    if graph is not None:
        if answer is None:
            out["lenient"] = v2.score_task(task, None, rows)
            out["lenient_changes"] = []
        else:
            transformed, changes = lenient_transform(answer, task["answer"], graph_names(graph))
            out["lenient"] = v2.score_task(task, transformed, rows)
            out["lenient_changes"] = changes
    return out


def episode_scores(task, events, graph):
    """Four scores of one trace: strict/lenient x original/applied. `events` holds `final_answer_original` and `final_answer_accepted` (the submitted answer)."""
    rows = v2.tool_rows(events)
    original = next((e["answer"] for e in events if e["kind"] == "final_answer_original"), None)
    submitted, _source = v2.episode_answer(events)
    if original is None:  # no accepted final_answer: both are the free-text answer, if any
        original = submitted
    return dict(original=score(task, original, rows, graph), applied=score(task, submitted, rows, graph), answer_original=original, answer_submitted=submitted)
