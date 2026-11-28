#!/usr/bin/env bash
# usage: tmux_py.sh <name> <script.py> [args]  -> detached tmux session "job_<name>", log runs/<name>.log (arguments are quoted safely)
NAME=$1; shift
D="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$D/runs"
tmux kill-session -t job_$NAME 2>/dev/null
Q=$(printf '%q ' "$@")
tmux new-session -d -s job_$NAME "cd $D && ./run_py.sh $Q > $D/runs/$NAME.log 2>&1"
