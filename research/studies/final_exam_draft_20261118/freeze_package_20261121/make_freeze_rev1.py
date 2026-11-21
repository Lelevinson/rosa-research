"""Writes FREEZE_REV1.json: the dated revision 1 of the Stage 1 freeze. Keeps FREEZE.json (original, hash below) unchanged and lists the files whose hash changed (old and new), the files added, the reason,
and the Ollama state. Refuses to write if a listed file is not committed and clean.  python3 make_freeze_rev1.py write"""
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CU = "research/studies/custodian_stage1_20261121/"
FP = "research/studies/final_exam_draft_20261118/freeze_package_20261121/"
EQ = "research/studies/final_exam_draft_20261118/exam_queue/"
CHANGED = [CU + "queue_bridge.py", FP + "start_stage1_laptop.sh"]
ADDED = [CU + "test_bridge.py", CU + "REVISION_1_20261121.md", FP + "verify_freeze.py", FP + "version_guard.py", FP + "make_freeze_rev1.py"]
ORIGINAL_FREEZE_SHA256 = "40b26b0fc0ca391294541553c912225e612f94a4a22b2c567321375a0e8b974b"
SECOND_ORIGINAL_ENTRY = "test_bridge.py was not in the original file list; it is added with its revision-1 hash"


def sha(path):
    return hashlib.sha256((REPO / path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def write(url="http://172.30.80.1:11434"):
    dirty = git("status", "--porcelain", "--", *CHANGED, *ADDED, FP + "FREEZE.json")
    if dirty:
        raise SystemExit("refusing: not committed/clean:\n" + dirty)
    if hashlib.sha256((HERE / "FREEZE.json").read_bytes()).hexdigest() != ORIGINAL_FREEZE_SHA256:
        raise SystemExit("FREEZE.json is not the original")
    original = json.loads((HERE / "FREEZE.json").read_text())
    version = json.load(urllib.request.urlopen(url + "/api/version", timeout=15))["version"]
    record = dict(
        revision=1, date="2026-11-21", original_freeze_sha256=ORIGINAL_FREEZE_SHA256, original_freeze_git_commit="a608d0a", git_head=git("rev-parse", "HEAD"),
        reason=("Row-plumbing defect found by the first start of the laptop queue (2026-11-21 17:52): the custodian bridge row had no `model` and `seed`, so queue_core.compact() raised KeyError after the first episode. "
                "Revision 1 copies model and seed from the attempt's queue cell into the bridge row (queue_bridge.py), adds a regression test through the real compact serializer, and rebuilds the missing compact rows "
                "in custody (Codex, REVISION_1_20261121.md; two completed cells kept, never re-run). Scoring, prompts, tasks, arms, specs and success criteria are unchanged: every other file hash of FREEZE.json verifies."),
        changed_files={path: dict(old_sha256=original["sha256"][path], new_sha256=sha(path)) for path in CHANGED},
        added_files={path: sha(path) for path in ADDED},
        changed_files_note="queue_bridge.py: Codex (row fields). start_stage1_laptop.sh: Claude Code (calls the revision-aware verify_freeze.py and starts the Ollama version guard). Codex also edited FREEZE.json in place in commit 236f372; that edit was reverted and replaced by this file so that the original record stays unchanged.",
        ollama_version=version, ollama_version_note="recorded at the revision; the laptop's Ollama (Windows) updated itself from 0.40.16 to 0.40.17 on 2026-11-21 17:27 (dev studies and the lab: 0.40.16). verify_freeze.py and version_guard.py stop the run on any change.",
        ollama_auto_update=("NOT DISABLED: Ollama for Windows has no documented switch; its updater (updater.go, hourly check) downloads to %LOCALAPPDATA%\\Ollama\\updates_v2 and installs silently. A Windows ACL deny on that folder "
                            "was refused by the permission system and not applied. Detection only: version_guard.py. An update during the run restarts the server and fails the episode in flight."),
        every_other_hash_verifies="see verify_freeze.py",
    )
    (HERE / "FREEZE_REV1.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print("FREEZE_REV1.json written;", hashlib.sha256((HERE / "FREEZE_REV1.json").read_bytes()).hexdigest())


if __name__ == "__main__":
    write() if sys.argv[1:] == ["write"] else sys.exit("usage: make_freeze_rev1.py write")
