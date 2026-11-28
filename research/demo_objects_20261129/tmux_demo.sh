#!/usr/bin/env bash
# usage: tmux_demo.sh <name> <requests-file>  -> detached tmux session demo_<name>; log rehearsals/<name>.log
NAME=$1; REQ=$2
D="$(cd "$(dirname "$0")" && pwd)"
tmux kill-session -t demo_$NAME 2>/dev/null
tmux new-session -d -s demo_$NAME "cd $D && ./run_objects_demo.sh $NAME $REQ > /dev/null 2>&1"
