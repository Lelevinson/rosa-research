"""Extra checks for the report (computed after the main analysis; descriptive): schema cost measured between arms, hook-defect sensitivity, error types in FULL. uv run python extra_checks.py"""
import json
from collections import Counter, defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
data = [r for r in rows if r["phase"] == "full"]
cell = lambda r: (r["task"], r["model"])
by = defaultdict(dict)
for r in data:
    by[r["arm"]][cell(r)] = r
def req1(r):
    for l in (REPO / r["trace_path"]).read_text().splitlines():
        e = json.loads(l)
        if e["kind"] == "model_end":
            return (e.get("usage") or {}).get("input_tokens", 0)
out = {}
# (1) exact request-1 differences on the same cell
for arm in ("NO_MENU", "NO_FINISH"):
    per_model = defaultdict(list)
    for c, r in by[arm].items():
        per_model[c[1]].append(req1(r) - req1(by["FULL"][c]))
    out[f"request1_input_{arm}_minus_FULL_by_model"] = {m: sorted(set(v)) for m, v in per_model.items()}
# (2) hook-defect sensitivity: cells where either arm of the pair has no scripted change
def hook_missing(r):
    return "chg" in r["task"] and "scripted_change" not in (REPO / r["trace_path"]).read_text()
missing = [(r["arm"], r["task"], r["model"]) for r in data if hook_missing(r)]
out["missed_scripted_change"] = missing
sens = {}
for arm in ("NO_SOFT_ERRORS", "NO_PRECHECK", "NO_MENU", "NO_FINISH"):
    cells = [c for c in by["FULL"] if not hook_missing(by["FULL"][c]) and not hook_missing(by[arm][c])]
    f = sum(by["FULL"][c]["supported_complete"] and not by[arm][c]["supported_complete"] for c in cells)
    g = sum(by[arm][c]["supported_complete"] and not by["FULL"][c]["supported_complete"] for c in cells)
    sens[arm] = dict(cells=len(cells), full_only=f, removal_only=g, full_minus_removal=f - g)
out["pairs_without_missed_hook_cells"] = sens
# (3) error types of the failing calls in FULL
kinds = Counter()
for r in by["FULL"].values():
    ev = [json.loads(l) for l in (REPO / r["trace_path"]).read_text().splitlines()]
    starts = {e["run_id"]: e for e in ev if e["kind"] == "tool_start"}
    for e in ev:
        if e["kind"] == "tool_end":
            text = str(e.get("output"))
            tool = starts.get(e["run_id"], {}).get("name", "?")
            if "multiple repeat" in text or "nothing to repeat" in text:
                kinds["tool exception: regex pattern error (glob like *cedar* passed as pattern)"] += 1
            elif text.startswith("Invalid arguments"):
                kinds["argument validation (pre-check)"] += 1
            elif "Unable to find node" in text or "Unable to find" in text:
                kinds["not found (name that does not exist or wrong form)"] += 1
            elif text.startswith("Tool ") and "failed" in text:
                kinds["tool failure (other)"] += 1
out["FULL_error_observations_by_type"] = dict(kinds)
(HERE / "extra_checks.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
