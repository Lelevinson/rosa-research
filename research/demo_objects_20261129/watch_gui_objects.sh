#!/usr/bin/env bash
# Viewer only: attach a Gazebo GUI client to the running objects simulation and point the camera at the table (gripper, block, tray). No change to the simulation.
# usage: watch_gui_objects.sh <runs/<name>/gz_partition.txt>      (WSLg, DISPLAY=:0)
source /opt/ros/jazzy/setup.bash
export DISPLAY=${DISPLAY:-:0}
F="$1"
for i in $(seq 1 600); do [ -s "$F" ] && break; sleep 0.5; done
export GZ_PARTITION=$(cat "$F")
# wait until the world answers
for i in $(seq 1 200); do gz topic -l 2>/dev/null | grep -q "/world/objects_world/pose/info" && break; sleep 1; done
sleep 8
echo "viewer start $(date +%s.%N)"
gz sim -g &
GUI=$!
python3 - <<'PY' > /tmp/objects_cam.txt
import math
cam = (0.85, -0.62, 0.45); tgt = (0.46, -0.10, 0.10)
d = [tgt[i] - cam[i] for i in range(3)]
yaw = math.atan2(d[1], d[0]); pitch = math.atan2(-d[2], math.hypot(d[0], d[1]))
cy, sy, cp, sp = math.cos(yaw / 2), math.sin(yaw / 2), math.cos(pitch / 2), math.sin(pitch / 2)
q = (-sy * sp, cy * sp, sy * cp, cy * cp)       # roll 0, pitch, yaw -> x y z w
print('pose: {position: {x: %f, y: %f, z: %f}, orientation: {x: %f, y: %f, z: %f, w: %f}}' % (cam + q))
PY
for i in $(seq 1 30); do
  sleep 2
  if gz service -s /gui/move_to/pose --reqtype gz.msgs.GUICamera --reptype gz.msgs.Boolean --timeout 3000 --req "$(cat /tmp/objects_cam.txt)" 2>&1 | grep -q "data: true"; then echo "camera set at $(date +%s.%N) (attempt $i)"; break; fi
done
wait $GUI
