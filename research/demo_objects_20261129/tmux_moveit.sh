#!/usr/bin/env bash
# usage: tmux_moveit.sh <name>   (sim must already run; log runs/<name>_moveit.log)
NAME=$1
D="$(cd "$(dirname "$0")" && pwd)"
tmux kill-session -t moveit_$NAME 2>/dev/null
tmux new-session -d -s moveit_$NAME "source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=231 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST OBJECTS_SIM_DIR=$D/sim; ros2 launch $D/sim/start_moveit.launch.py > $D/runs/${NAME}_moveit.log 2>&1"
