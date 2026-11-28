#!/usr/bin/env bash
# stop everything of the objects sim (ours only)
pkill -INT -f "ros2 launch ur_simulation_gz" ; sleep 5
pkill -f "gz sim" ; pkill -f ros2_control_node ; pkill -f parameter_bridge ; pkill -f move_group
sleep 1; echo "left: $(ps -eo cmd | grep -E 'gz sim|ros2_control_node|parameter_bridge|move_group' | grep -v grep | grep -v stop_sim | wc -l)"
