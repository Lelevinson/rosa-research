#!/usr/bin/env bash
# Extract Levinson's files at the pinned commit, byte for byte, next to the worktree: <introtorobotics>/his-M-e233cf5/
# `git archive` applies eol conversion on Windows unless disabled, which changes the SHA-256: the -c flags below prevent that.
# Then verify against M_FILES.md. Zero model calls. Needs the commit locally:
#   git fetch origin +refs/heads/member/levinson:refs/remotes/origin/member/levinson
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"               # the merge worktree (or any checkout that has the commit)
DEST="${HIS_ROOT:-$REPO/../his-M-e233cf5}"
COMMIT=e233cf51389885d0aaffa5453687f57437551764
rm -rf "$DEST" && mkdir -p "$DEST"
git -C "$REPO" -c core.autocrlf=false -c core.eol=lf archive "$COMMIT" research pyproject.toml uv.lock | tar -x -C "$DEST"
python3 "$HERE/verify_his_files.py" --root "$DEST" --git-dir "$REPO" --commit "$COMMIT" | tail -3
