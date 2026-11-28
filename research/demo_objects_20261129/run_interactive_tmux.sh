#!/usr/bin/env bash
# usage: run_interactive_tmux.sh <name> [requests-file]   (start in WSL; detached tmux job, log on disk)
NAME=$1; REQ=$2
D=/mnt/c/Proj/robotics/introtorobotics/wt-objects/research/demo_objects_20261129
source /opt/ros/jazzy/setup.bash
export PYTHONDONTWRITEBYTECODE=1
cd $D
if [ -n "$REQ" ]; then ARGS="--requests-file $REQ"; else ARGS=""; fi
/home/martin/.local/share/rosa-envs/research/bin/python -B interactive_demo.py rehearsals/$NAME $ARGS 2>&1 | tee rehearsals/$NAME.log
