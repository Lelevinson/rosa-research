"""Writes FREEZE_REV2.json (the dated revision 2 of the Stage 1 freeze) and, only when asked, applies it. FREEZE.json and FREEZE_REV1.json stay unchanged.
  python3 make_freeze_rev2.py write     list files, hash them (changed files with the hash of their CANDIDATE) and write FREEZE_REV2.json; refuses if a listed file or candidate is not committed and clean
  python3 make_freeze_rev2.py apply     copy each candidate over its target (queue_core_rev2.py -> queue_core.py, start_stage1_laptop_rev2.sh -> start_stage1_laptop.sh), then run verify_freeze_rev2.py. NOT RUN by the preparation.
The record is static: whether revision 2 is applied is read from the working files by verify_freeze_rev2.py (exit 2 = prepared, not applied)."""
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
FP = "research/studies/final_exam_draft_20261118/freeze_package_20261121/"
EQ = "research/studies/final_exam_draft_20261118/exam_queue/"
DR = "research/studies/exam_dress_rehearsal_20261122/"
FD = "research/studies/final_exam_draft_20261118/"
APPLY = {EQ + "queue_core.py": EQ + "queue_core_rev2.py", FP + "start_stage1_laptop.sh": FP + "start_stage1_laptop_rev2.sh"}   # target <- candidate
ADDED = [EQ + "queue_core_rev2.py", EQ + "integrity_look.py", EQ + "analyze_when_complete.py", EQ + "multi_attempt_count.py", EQ + "tests_rev2/test_rev2_crash.py", EQ + "tests_rev2/dummy_system_rev2.py",
         EQ + "tests_rev2/run_rev2.py", EQ + "tests_rev2/negative_control.py", EQ + "tests_rev2/rev2_spec.json", EQ + "tests_rev2/rev2_spec_small.json",
         FP + "start_stage1_laptop_rev2.sh", FP + "verify_freeze_rev2.py", FP + "make_freeze_rev2.py", FD + "RUNBOOK.md",
         DR + "REV2_FREEZE_DRAFT.md", DR + "REPORT.md", DR + "RULES.md", DR + "PARITY.md", DR + "OLLAMA_AUTOUPDATE.md"]


def sha(path):
    return hashlib.sha256((REPO / path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def write(url="http://172.30.80.1:11434"):
    dirty = git("status", "--porcelain", "--", *APPLY.values(), *APPLY.keys(), *ADDED, FP + "FREEZE.json", FP + "FREEZE_REV1.json")
    if dirty:
        raise SystemExit("refusing: not committed/clean:\n" + dirty)
    original_bytes, rev1_bytes = (HERE / "FREEZE.json").read_bytes(), (HERE / "FREEZE_REV1.json").read_bytes()
    rev1 = json.loads(rev1_bytes)
    original = json.loads(original_bytes)
    expected = dict(original["sha256"])
    for path, change in rev1["changed_files"].items():
        expected[path] = change["new_sha256"]
    expected.update(rev1["added_files"])
    for target in APPLY:
        if sha(target) != expected[target]:
            raise SystemExit(f"refusing: {target} does not have its revision-1 hash (already applied or changed)")
    version = json.load(urllib.request.urlopen(url + "/api/version", timeout=15))["version"]
    record = dict(
        revision=2, date="2026-11-22", status_note="PREPARED: candidates are hashed but not copied over their targets; `make_freeze_rev2.py apply` does that; verify_freeze_rev2.py exit 2 = prepared, not applied",
        original_freeze_sha256=hashlib.sha256(original_bytes).hexdigest(), rev1_sha256=hashlib.sha256(rev1_bytes).hexdigest(), git_head=git("rev-parse", "HEAD"),
        reason=("Revision 2 repairs the queue after the dress rehearsal and the independent review (REV2_FREEZE_DRAFT.md): compact-row crash window and log integrity (encode before append, reconcile before every dispatch and exit, "
                "torn-line evidence, conflicting duplicates stop the run, legacy rows without model/seed carried forward from the cell id); durable interrupted-attempt ledger and the revised crash re-run rule (owner decisions D2, D3); "
                "run-owned ROS discovery daemon stopped by PID with positive ownership and a survivor gate; the integrity look and the only comparison entry point analyze_when_complete.py (D1, D4); "
                "post-hoc count of cells with more than one model-request attempt. Arms, prompts, tool menus, tasks, scorer v2.0, success criteria, seeds, models, master seed, specs, analyze_primary.py, queue_bridge.py and bridge.py are unchanged."),
        changed_files={target: dict(old_sha256=expected[target], new_sha256=sha(candidate)) for target, candidate in APPLY.items()},
        apply=APPLY, added_files={path: sha(path) for path in ADDED},
        ollama_version=version, ollama_auto_update="off: auto_update_enabled = 0 in the app database (read-only check 2026-11-22), context_length = 65536; verify_freeze_rev2.py and version_guard.py stop the run on any version or digest change",
        known_limitations=["D2 receipt-write failure after inference is not caught by the ledger (post-hoc count: multi_attempt_count.py)",
                           "analysis wrapper issues (orphan compact row in another tier, planned pair count from observed rows, D4 sensitivity skipped without cohort file) are to be fixed after the start and before the first tier-1 look"],
    )
    (HERE / "FREEZE_REV2.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print("FREEZE_REV2.json written;", hashlib.sha256((HERE / "FREEZE_REV2.json").read_bytes()).hexdigest())


def apply():
    record = json.loads((HERE / "FREEZE_REV2.json").read_text())
    for target, candidate in record["apply"].items():
        if sha(candidate) != record["changed_files"][target]["new_sha256"]:
            raise SystemExit(f"refusing: candidate {candidate} changed after the record was written")
        shutil.copy2(REPO / candidate, REPO / target)
    sys.exit(subprocess.call([sys.executable, str(HERE / "verify_freeze_rev2.py")]))


if __name__ == "__main__":
    {"write": write, "apply": apply}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit("usage: make_freeze_rev2.py write|apply"))()
