"""Validity flags for round 1 episodes (read-only; the primary tables are NOT changed by this file).
 - missed_hook: a changing-parameter task (e1h_chg_*) whose trace has no 'scripted_change' event (the mid-episode fixture change never happened; known defect, see forge_baseline REPORT)
 - backend_crash: an episode whose abort text is an Ollama/llama-server process fault (CUDA/exit status), not a model or loop behaviour
A cell (model, task, seed) is 'clean' when none of its four arms has a flag. Output: validity_round1.json and a sensitivity table.  uv run python validity_round1.py"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[2]
rows = [r for r in map(json.loads, (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()) if r["phase"] == "full"]
flags = {}
for r in rows:
    ev = [json.loads(l) for l in (REPO / r["trace_path"]).read_text().splitlines()]
    f = []
    if r["task"].startswith("e1h_chg") and not any(e["kind"] == "scripted_change" for e in ev):
        f.append("missed_hook")
    if any("llama-server" in a or "CUDA" in a for a in r["aborts"]):
        f.append("backend_crash")
    flags[r["run_id"]] = f
bad_cells = {(r["model"], r["task"], r["seed"]) for r in rows if flags[r["run_id"]]}
ARMS = ["C1", "C1+AG", "C1+LA", "C1+AG+LA"]
out = dict(flagged_episodes={k: v for k, v in flags.items() if v}, flagged_cells=sorted(map(list, bad_cells)))
Path(HERE / "validity_round1.json").write_text(json.dumps(out, indent=1))
print("flagged episodes:", len(out["flagged_episodes"]), "in", len(bad_cells), "cells")
for k, v in out["flagged_episodes"].items(): print("  ", k, v)
print("\nSensitivity: only cells with no flagged episode in any arm (%d of 80 cells)\n" % (80 - len(bad_cells)))
print("| arm | cells | supported-complete | LLM requests | tokens |\n|---|---:|---:|---:|---:|")
for a in ARMS:
    s = [r for r in rows if r["arm"] == a and (r["model"], r["task"], r["seed"]) not in bad_cells]
    print(f"| {a} | {len(s)} | {sum(r['supported_complete'] for r in s)} | {sum(r['llm_requests'] for r in s)} | {sum(r['input_tokens'] + r['output_tokens'] for r in s)} |")
