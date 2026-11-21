"""NAME-REWRITE RULE v2 (dated 2026-11-17; owner-approved collision revision of the round-2 answer rewrite). This is a NEW rule: do not call it the round-2 rewrite.

Same as the round-2 rewrite (`build_round2_20261116/round2_harness.rewrite`, 'replay protocol 3') in everything except collisions:
  * A string that is name-like (absolute or relative path of letters, digits, underscores) and is not an exact name of the ledger (full names of the task text and of successful tool
    results) but is the trailing part (whole final path segments) of EXACTLY ONE ledger full name is replaced by that full name. 2+ candidates: unchanged, logged `reject_ambiguous`.
    A full (absolute) name never seen: unchanged, logged `reject_never_seen`. Top-level keys of the answer are never rewritten. Nested keys and all values (also in lists) are.
  * COLLISION (new): inside one object, compute the candidate of every key (a key that is not rewritten is its own candidate). If a rewritten key would equal the candidate of another key
    of the same object (rewritten or not), every key of that group stays UNCHANGED and the rule logs `collision` (the values of the keys are still processed). Inside one list, compute the
    candidate of every item; if a rewritten item would equal another item's candidate (or another item's original), the rewritten items of that group stay UNCHANGED and the rule logs
    `collision`. Nothing is ever overwritten or merged, no value is dropped.
Events: dict(kind in rewrite | reject_ambiguous | reject_never_seen | collision, path, ...).
"""
import sys
from pathlib import Path

STUDIES = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STUDIES / "build_round1_20261115"))
import answer_gate as ag  # noqa: E402

RULE_NAME = "name-rewrite-v2 (collision-safe), 2026-11-17"


def candidate(value, allowed):
    """(new string, event kind or None, extra) for one name-like string."""
    if not isinstance(value, str) or not (ag.ABSOLUTE_NAME.fullmatch(value) or ag.RELATIVE_NAME.fullmatch(value)):
        return value, None, None
    if value in allowed:
        return value, None, None
    matches = ag.trailing_matches(value, allowed)
    if len(matches) == 1:
        return matches[0], "rewrite", None
    if len(matches) >= 2:
        return value, "reject_ambiguous", matches
    if ag.ABSOLUTE_NAME.fullmatch(value):
        return value, "reject_never_seen", None
    return value, None, None


def rewrite_answer(value, allowed, events, path="", top=True):
    """Returns the rewritten copy; appends events. `allowed` = ledger full names."""
    if isinstance(value, str):
        new, kind, extra = candidate(value, allowed)
        if kind == "rewrite":
            events.append(dict(kind="rewrite", path=path, old=value, new=new))
        elif kind == "reject_ambiguous":
            events.append(dict(kind="reject_ambiguous", path=path, value=value, candidates=extra))
        elif kind == "reject_never_seen":
            events.append(dict(kind="reject_never_seen", path=path, value=value))
        return new
    if isinstance(value, dict):
        keys = list(value)
        pending = []  # (key, new key, kind, extra) for nested objects
        for key in keys:
            if top:
                pending.append((key, key, None, None))
            else:
                new, kind, extra = candidate(key, allowed)
                pending.append((key, new, kind, extra))
        groups = {}
        for key, new, _kind, _extra in pending:
            groups.setdefault(new, []).append(key)
        out = {}
        for key, new, kind, extra in pending:
            final = new
            if len(groups[new]) > 1 and any(k != n for k, n, _a, _b in pending if n == new):
                final = key  # collision group containing a rewritten key: keep every key as it was
                if kind == "rewrite":
                    events.append(dict(kind="collision", path=f"{path}.key" if path else "key", keys=groups[new], would_become=new))
            elif kind == "rewrite":
                events.append(dict(kind="rewrite", path=f"{path}.key" if path else "key", old=key, new=new))
            elif kind == "reject_ambiguous":
                events.append(dict(kind="reject_ambiguous", path=f"{path}.key" if path else "key", value=key, candidates=extra))
            elif kind == "reject_never_seen":
                events.append(dict(kind="reject_never_seen", path=f"{path}.key" if path else "key", value=key))
            assert final not in out, "internal: the collision rule must make this impossible"
            out[final] = rewrite_answer(value[key], allowed, events, f"{path}.{key}" if path else key, False)
        return out
    if isinstance(value, list):
        candidates = [candidate(item, allowed) if isinstance(item, str) else (item, None, None) for item in value]
        finals = []
        for index, (item, (new, kind, extra)) in enumerate(zip(value, candidates)):
            clash = kind == "rewrite" and any(other != index and (candidates[other][0] == new) for other in range(len(value)))
            if clash:
                events.append(dict(kind="collision", path=f"{path}[{index}]", item=item, would_become=new))
                finals.append(item)
            else:
                if kind == "rewrite":
                    events.append(dict(kind="rewrite", path=f"{path}[{index}]", old=item, new=new))
                elif kind == "reject_ambiguous":
                    events.append(dict(kind="reject_ambiguous", path=f"{path}[{index}]", value=item, candidates=extra))
                elif kind == "reject_never_seen":
                    events.append(dict(kind="reject_never_seen", path=f"{path}[{index}]", value=item))
                finals.append(new)
        return [rewrite_answer(f, allowed, events, f"{path}[{i}]", False) if isinstance(f, (dict, list)) else f for i, f in enumerate(finals)]
    return value
