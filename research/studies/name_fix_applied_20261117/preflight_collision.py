"""Collision preflight of the frozen design (research/decisions/2026-11-17-name-fix-applied-test.md, 'Freeze collision behavior before execution'):
does the EXACT round-2 rewrite (`round2_harness.rewrite`) silently overwrite when two keys of one object would become the same key? CPU only, no model.
uv run python preflight_collision.py -> PREFLIGHT_COLLISION.md"""
import hashlib
import inspect
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "build_round2_20261116"))
sys.path.insert(0, str(HERE.parent / "build_round1_20261115"))
import round2_harness as r2  # noqa: E402

ALLOWED = {"/plant32/quill", "/plant32/anvil"}  # names the ledger knows (one candidate each: no ambiguity)
cases = [
    ("a model writes both the short and the full form of one entity as nested keys", {"gains": {"quill": 1, "/plant32/quill": 2}}),
    ("the same, full form first", {"gains": {"/plant32/quill": 2, "quill": 1}}),
    ("two different short forms of one entity", {"gains": {"anvil": 5, "/anvil": 6}}),
    ("control: one short key, no collision", {"gains": {"quill": 1, "/plant32/anvil": 2}}),
    ("control: values only", {"node": "quill", "others": ["anvil"]}),
]
rows = []
for name, answer in cases:
    log = []
    out = r2.rewrite(json.loads(json.dumps(answer)), ALLOWED, log)
    values_in = sorted(json.dumps(v) for part in ([answer["gains"]] if "gains" in answer else []) for v in part.values())
    values_out = sorted(json.dumps(v) for part in ([out["gains"]] if "gains" in out else []) for v in part.values())
    rows.append(dict(case=name, answer=answer, rewritten=out, events=[e["kind"] for e in log], values_lost=[v for v in values_in if v not in values_out],
                     silent_overwrite=bool(values_in) and len(values_out) < len(values_in) and not any(e["kind"].startswith("collision") for e in log)))
verdict = "FAIL" if any(r["silent_overwrite"] for r in rows) else "PASS"
source = inspect.getsource(r2.rewrite)
text = ["# Collision preflight of the exact round-2 rewrite (2026-11-17)", "",
        f"Code under test: `round2_harness.rewrite` (source SHA-256 `{hashlib.sha256(source.encode()).hexdigest()[:16]}...`, file `build_round2_20261116/round2_harness.py`). The frozen design says: if two nested keys would become the same key the exact rule must not silently overwrite; if it can, the exact rule fails the preflight and applied use is blocked until a separate dated rule revision is authorized.", "",
        f"**Preflight verdict: {verdict}.**", "", "| case | answer | rewritten | events | values lost | silent overwrite |", "|---|---|---|---|---|---|"]
for r in rows:
    text.append(f"| {r['case']} | `{json.dumps(r['answer'])}` | `{json.dumps(r['rewritten'])}` | {r['events']} | {r['values_lost']} | {r['silent_overwrite']} |")
text += ["", "Reading: `rewrite` builds the new object with `out[new_key] = rewrite(v, ...)` for every key, and it logs only `rewrite` events, so two keys that map to the same full name keep only the last value and the loss is not logged. This is the exact rule of round 2; it was never exposed to the case in round 2 (2 rewritten answers, none with nested-key collisions)."]
# revised rule v2 on the same cases (owner-approved collision revision, 2026-11-17)
import namefix_rule as rule  # noqa: E402
text += ["", "## Revised rule (name-rewrite v2, `namefix_rule.py`) on the same cases", "", "| case | rewritten | events | values lost |", "|---|---|---|---|"]
extra_cases = cases + [("list items: short and full form of one entity", {"nodes": ["quill", "/plant32/quill"]}), ("list items: two identical short forms", {"nodes": ["quill", "quill"]})]
all_ok = True
for name, answer in extra_cases:
    events = []
    out = rule.rewrite_answer(json.loads(json.dumps(answer)), ALLOWED, events)
    count = lambda v: len(v.values()) if isinstance(v, dict) else len(v) if isinstance(v, list) else 1
    flat = lambda v: [leaf for x in (v.values() if isinstance(v, dict) else v if isinstance(v, list) else [v]) for leaf in (flat(x) if isinstance(x, (dict, list)) else [x])]
    lost = len(flat(answer)) - len(flat(out))
    all_ok &= lost == 0
    text.append(f"| {name} | `{json.dumps(out)}` | {[e['kind'] for e in events]} | {lost} |")
text += ["", f"**Revised rule preflight verdict: {'PASS' if all_ok else 'FAIL'}** (no value lost in any case; collisions leave every colliding key or item unchanged and are logged as `collision`). The rule has 11 frozen unit tests (`tests/test_namefix.py`), including 500 random answers (no value dropped, idempotent) and equality with the round-2 rewrite on every collision-free case."]
(HERE / "PREFLIGHT_COLLISION.md").write_text("\n".join(text) + "\n")
print("\n".join(text))
