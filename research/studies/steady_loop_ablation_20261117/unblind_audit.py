"""Unblinds Codex's blind finish-tool audit (AUDIT_ANSWERS.md, sha256 67360c5f...) with the private key and cross-tabulates it with the scorer. CPU only.
Reads AUDIT_ANSWERS.md and the key (research/_artifacts/runs/steady_loop_ablation_20261117/audit_key/KEY.json, written by make_audit_packet.py). uv run python unblind_audit.py -> AUDIT_UNBLINDED.md, audit_unblinded.json"""
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
text = (HERE / "AUDIT_ANSWERS.md").read_text()
assert hashlib.sha256(text.encode()).hexdigest().startswith("67360c5f"), "AUDIT_ANSWERS.md changed"
key = json.loads((REPO / "research/_artifacts/runs/steady_loop_ablation_20261117/audit_key/KEY.json").read_text())
answers = {}
for cell_block in re.split(r"\n## Cell ", text)[1:]:
    number = int(cell_block[:2])
    for letter, block in re.findall(r"### ([AB])\n(.*?)(?=\n### |\n## |\Z)", cell_block, flags=re.S):
        correct = re.search(r"Correct: \*\*(correct|incorrect|cannot tell)\*\*", block).group(1)
        format_only = re.search(r"Format-only: \*\*(yes|no|cannot tell)\*\*", block).group(1)
        complete = re.search(r"Complete evidence: \*\*(yes|no|cannot tell)", block).group(1)
        stopped = re.search(r"Stopped early: \*\*(yes|no|cannot tell)\*\*", block).group(1)
        cause = re.search(r"Failure cause: \*\*?([^*\n]*)", block)
        answers[(number, letter)] = dict(correct=correct, format_only=format_only, complete=complete, stopped_early=stopped, cause=(cause.group(1).strip(" .—") if cause else ""))
assert len(answers) == 28, len(answers)
rows = []
for cell in key["cells"]:
    for letter, ep in cell["episodes"].items():
        a = answers[(cell["cell"], letter)]
        verdict = "format-only" if a["format_only"] == "yes" else {"correct": "correct", "incorrect": "wrong", "cannot tell": "uncertain"}[a["correct"]]
        rows.append(dict(cell=cell["cell"], task=cell["task"], model=cell["model"], kind=cell["kind"], arm=ep["arm"], scorer_supported=ep["supported"], codex=a, codex_verdict=verdict))
out = {}
# (1) the 7 FULL-only cells
full_only = [r for r in rows if r["kind"] == "FULL_only"]
out["full_only_cells"] = [dict(cell=c, task=next(r["task"] for r in full_only if r["cell"] == c), model=next(r["model"] for r in full_only if r["cell"] == c),
                               FULL=next(r["codex_verdict"] for r in full_only if r["cell"] == c and r["arm"] == "FULL"), NO_FINISH=next(r["codex_verdict"] for r in full_only if r["cell"] == c and r["arm"] == "NO_FINISH"),
                               NO_FINISH_cause=next(r["codex"]["cause"] for r in full_only if r["cell"] == c and r["arm"] == "NO_FINISH")) for c in sorted({r["cell"] for r in full_only})]
out["full_only_counts"] = {arm: dict(Counter(r["codex_verdict"] for r in full_only if r["arm"] == arm)) for arm in ("FULL", "NO_FINISH")}
# (2) format-only episodes
out["format_only_episodes"] = [dict(cell=r["cell"], task=r["task"], model=r["model"], kind=r["kind"], arm=r["arm"], scorer_supported=r["scorer_supported"], codex_correct=r["codex"]["correct"]) for r in rows if r["codex"]["format_only"] == "yes"]
# (3) agreement on all 28
tab = defaultdict(Counter)
for r in rows:
    tab[r["codex"]["correct"]]["scorer supported" if r["scorer_supported"] else "scorer unsupported"] += 1
out["agreement_table"] = {k: dict(v) for k, v in tab.items()}
decided = [r for r in rows if r["codex"]["correct"] != "cannot tell"]
agree = [r for r in decided if (r["codex"]["correct"] == "correct") == r["scorer_supported"]]
out["agreement"] = dict(episodes=28, codex_decided=len(decided), agree=len(agree), disagree=[dict(cell=r["cell"], arm=r["arm"], task=r["task"], model=r["model"], codex=r["codex"]["correct"], format_only=r["codex"]["format_only"], scorer_supported=r["scorer_supported"], cause=r["codex"]["cause"]) for r in decided if r not in agree])
out["uncertain_episodes"] = [dict(cell=r["cell"], arm=r["arm"], kind=r["kind"], scorer_supported=r["scorer_supported"]) for r in rows if r["codex"]["correct"] == "cannot tell"]
by_arm = defaultdict(Counter)
for r in rows:
    by_arm[r["arm"]][r["codex_verdict"]] += 1
out["verdict_by_arm_all_28"] = {a: dict(c) for a, c in by_arm.items()}
out["rows"] = rows
(HERE / "audit_unblinded.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
