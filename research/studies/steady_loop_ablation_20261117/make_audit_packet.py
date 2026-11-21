"""Blind finish-tool audit packet for Codex (owner request 2026-11-17). Pairs of episodes (fresh FULL vs minus-finish-tool) of 14 cells:
  7 cells where FULL was supported and NO_FINISH was not (the 8 FULL-only cells minus the one whose scripted change never fired = hook defect, which cannot be supported),
  7 cells chosen at random (seed below) from the 28 cells supported in both arms.
Both episodes of a cell are shown as Episode A / Episode B in random order; cells are shuffled; arm names, scorer verdicts, issues and handler events are removed. The final answer is shown as
'FINAL RESPONSE' in both arms (the FULL final_answer call is rendered as the answer it carried; the minus-finish final message is the model's own last text), so the final-response formats may still differ.
The key (cell -> which episode is which arm, selection) is written OUTSIDE the studies folder (research/_artifacts/.../audit_key/KEY.json, not mirrored). uv run python make_audit_packet.py"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SEED = 20261123
KEY = REPO / "research/_artifacts/runs/steady_loop_ablation_20261117/audit_key/KEY.json"
tasks = {t["id"]: t for t in json.loads((REPO / "research/studies/headroom_diagnostic_20261112/stage3_tasks.json").read_text())}
tasks.update({t["id"]: t for t in json.loads((REPO / "research/studies/small_model_harness_20261115/e1h_tasks.json").read_text())})
rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
by = {a: {(r["task"], r["model"]): r for r in rows if r["phase"] == "full" and r["arm"] == a} for a in ("FULL", "NO_FINISH")}
extract = lambda r: [json.loads(l) for l in (REPO / r["trace_path"]).read_text().splitlines()]
missed_hook = lambda r: "chg" in r["task"] and "scripted_change" not in (REPO / r["trace_path"]).read_text()

cells = sorted(by["FULL"])
full_only = [c for c in cells if by["FULL"][c]["supported_complete"] and not by["NO_FINISH"][c]["supported_complete"]]
hook = [c for c in full_only if missed_hook(by["NO_FINISH"][c]) or missed_hook(by["FULL"][c])]
audit_full_only = [c for c in full_only if c not in hook]
both = [c for c in cells if by["FULL"][c]["supported_complete"] and by["NO_FINISH"][c]["supported_complete"]]
rng = random.Random(SEED)
audit_both = rng.sample(both, 7)
chosen = [(c, "FULL_only") for c in audit_full_only] + [(c, "both_supported") for c in audit_both]
assert len(audit_full_only) == 7 and len(chosen) == 14, (len(audit_full_only), len(chosen))
rng.shuffle(chosen)


def render(row):
    ev = extract(row)
    starts = {e["run_id"]: e for e in ev if e["kind"] == "tool_start"}
    ends = {e["run_id"]: e for e in ev if e["kind"] == "tool_end"}
    lines, n = [], 0
    answer_text = None
    for e in ev:
        if e["kind"] == "model_end":
            n += 1
        elif e["kind"] == "tool_start":
            if e["name"] == "final_answer":
                continue  # shown below as the final response
            out = str(ends.get(e["run_id"], {}).get("output"))
            lines.append(f"- request {n}: call `{e['name']}` arguments {e['input']}\n  result: {out[:350]}{' ...[cut]' if len(out) > 350 else ''}")
    accepted = [e for e in ev if e["kind"] == "final_answer_accepted"]
    end = [e for e in ev if e["kind"] == "episode_end"][-1]
    if accepted:
        answer_text = json.dumps(accepted[-1]["answer"])
    else:
        answer_text = end.get("answer") if end.get("answer") else f"(no final response; the episode ended with the error: {str(end.get('error'))[:200]})"
    return "\n".join(lines) if lines else "- (no tool call)", answer_text, n


L = ["# Blind audit packet: 14 cells, two episodes each (arm labels removed)", "",
     "Each cell is one task for one model. Episode A and Episode B are two separate runs of the same cell under two settings that are not named. For each episode you see the task, the tool calls (arguments) and the first 350 characters of each result, and the final response. You do not see any scorer verdict. Fill in AUDIT_FORM.md.", ""]
key_cells = []
for number, ((task, model), kind) in enumerate(chosen, 1):
    order = ["FULL", "NO_FINISH"]
    rng.shuffle(order)
    L += [f"## Cell {number:02d}", f"**Task text:** {tasks[task]['request']}", ""]
    entry = dict(cell=number, task=task, model=model, kind=kind, episodes={})
    for letter, arm in zip("AB", order):
        calls, final, requests = render(by[arm][(task, model)])
        L += [f"### Cell {number:02d}, Episode {letter}", calls, f"**FINAL RESPONSE:** {final}", ""]
        entry["episodes"][letter] = dict(arm=arm, run_id=by[arm][(task, model)]["run_id"], supported=by[arm][(task, model)]["supported_complete"])
    key_cells.append(entry)
(HERE / "AUDIT_PACKET.md").write_text("\n".join(L) + "\n")
KEY.write_text(json.dumps(dict(seed=SEED, note="PRIVATE: do not give to the auditor", excluded_hook_defect=[list(c) for c in hook], cells=key_cells), indent=1))
print("packet cells", len(chosen), "hook-excluded", hook, "both-supported pool", len(both))
