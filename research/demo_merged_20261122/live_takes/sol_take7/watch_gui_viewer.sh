#!/usr/bin/env bash
# Viewer only: attach a Gazebo GUI client to the running headless server. Does not touch the frozen launch code.
source /opt/ros/jazzy/setup.bash
READY=/mnt/c/Proj/robotics/introtorobotics/weekend-run-20261121/demo-live/sol_take7/gazebo/readiness.json
for i in $(seq 1 400); do [ -f "$READY" ] && break; sleep 0.5; done
P=""
for pid in $(pgrep -f "gz sim"); do
  v=$(tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | grep '^GZ_PARTITION=' | head -1)
  [ -n "$v" ] && P="${v#GZ_PARTITION=}" && break
done
echo "partition=$P at $(date +%s.%N)"
export GZ_PARTITION="$P"
exec gz sim -g
