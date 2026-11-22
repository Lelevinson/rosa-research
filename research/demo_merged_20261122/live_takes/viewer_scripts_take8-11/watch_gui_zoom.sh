#!/usr/bin/env bash
# Viewer only. Attach a Gazebo GUI client to the running headless server and point the GUI camera at the arm (GUI "move to" service). No launch-code change.
# Usage: watch_gui_zoom.sh <path to the run's gazebo/readiness.json>
source /opt/ros/jazzy/setup.bash
READY="$1"
for i in $(seq 1 400); do [ -f "$READY" ] && break; sleep 0.5; done
P=""
for pid in $(pgrep -f "gz sim"); do
  v=$(tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | grep '^GZ_PARTITION=' | head -1)
  [ -n "$v" ] && P="${v#GZ_PARTITION=}" && break
done
echo "partition=$P at $(date +%s.%N)"
export GZ_PARTITION="$P"
gz sim -g &
GUI=$!
for i in $(seq 1 30); do
  sleep 2
  if gz service -s /gui/move_to --reqtype gz.msgs.StringMsg --reptype gz.msgs.Boolean --timeout 3000 --req 'data: "ur"' 2>&1 | grep -q "data: true"; then
    echo "camera moved to ur at $(date +%s.%N) (attempt $i)"; break
  fi
done
wait $GUI
