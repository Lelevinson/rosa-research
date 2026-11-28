#!/usr/bin/env bash
# One command for the objects demo (WSL). Starts simulation + MoveIt (detached tmux), waits until ready, runs the interactive terminal (Sol), stops everything at the end.
# usage: run_objects_demo.sh <name> [requests-file]       (name = NEW folder name, e.g. show_01)
# LABEL: object poses read from the simulator (ground truth); simulated gripper with grasp assist; demonstration only.
NAME=${1:?name}; REQ=$2
D="$(cd "$(dirname "$0")" && pwd)"
cd "$D"
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=231 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST PYTHONDONTWRITEBYTECODE=1
[ -e "rehearsals/$NAME" ] && { echo "rehearsals/$NAME exists, use a new name"; exit 1; }
./stop_sim.sh > /dev/null
trap './stop_sim.sh > /dev/null' EXIT
./tmux_sim.sh "$NAME"; ./tmux_moveit.sh "$NAME"
echo "Starting simulation and MoveIt (about 60 s) ..."
for i in $(seq 1 90); do
  if grep -q "Configured and activated gripper_controller" "runs/$NAME/gripper_spawner.log" 2>/dev/null && grep -q "You can start planning now" "runs/${NAME}_moveit.log" 2>/dev/null; then break; fi
  sleep 2
done
sleep 5
if [ -n "$REQ" ]; then ARGS="--requests-file $REQ"; else ARGS=""; fi
/home/martin/.local/share/rosa-envs/research/bin/python -B interactive_demo_objects.py "rehearsals/$NAME" "runs/$NAME/gz_partition.txt" $ARGS 2>&1 | tee "rehearsals/$NAME.log"
