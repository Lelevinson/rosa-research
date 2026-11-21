"""Commit the COMPACT results of a run to the local Git repository (never pushes). Only redacted compact tables and a status snapshot are staged:
no traces, no full rows (they hold answers), no custodian or artifact paths, nothing over 2 MB. `research/` is git-excluded in this checkout, so files are added with `git add -f`.
  python commit_results.py --run-name NAME [--machine laptop]"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import queue_core  # noqa: E402

REPO = queue_core.REPO
FORBIDDEN_PARTS = ("_artifacts", ".local", "heldout", "held_out", "traces")
MAX_BYTES = 2 * 1024 * 1024
TRAILER = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"


def git(*args, check=True, repo=None):
    return subprocess.run(["git", "-C", str(repo or REPO), *args], capture_output=True, text=True, check=check)


def commit(run_name, machine, repo=None, compact_dir=None):
    """`repo` and `compact_dir` exist so that the tests can use a throw-away repository."""
    repo = Path(repo or REPO)
    compact_dir = Path(compact_dir or queue_core.COMPACT_ROOT / run_name)
    files = sorted(p for p in compact_dir.glob("*.jsonl")) if compact_dir.exists() else []
    for path in files:
        relative = path.relative_to(repo)
        if any(part in str(relative) for part in FORBIDDEN_PARTS) or path.stat().st_size > MAX_BYTES:
            raise RuntimeError(f"refusing to commit {relative}")
    if not files:
        return "nothing to commit"
    git("add", "-f", repo=repo, *[str(p.relative_to(repo)) for p in files])
    if git("diff", "--cached", "--quiet", "--", repo=repo, *[str(p.relative_to(repo)) for p in files], check=False).returncode == 0:
        return "no change"
    rows = sum(len(p.read_text().splitlines()) for p in files)
    message = f"Exam queue results ({run_name}, machine {machine}): {rows} compact rows\n\nCompact redacted tables only (opaque task hashes, no answers, no traces).\n\n{TRAILER}\n"
    result = git("commit", "-m", message, "--", repo=repo, *[str(p.relative_to(repo)) for p in files], check=False)
    return result.stdout.strip().splitlines()[0] if result.returncode == 0 else f"commit failed: {result.stderr.strip()[:200]}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--machine", default="all")
    args = parser.parse_args()
    print(commit(args.run_name, args.machine))
