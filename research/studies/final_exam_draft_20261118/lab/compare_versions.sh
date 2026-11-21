#!/usr/bin/env bash
# Run INSIDE the container: compare the ros-jazzy-* / gz packages installed here with the laptop's (versions_laptop.txt). Packages that exist only on the laptop (the desktop/GUI stack) are expected to be missing.
#   docker exec rosa-exam-main bash -lc 'bash <LAB_PATH>'
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dpkg-query -W -f='${Package}=${Version}\n' | grep -E "^(ros-jazzy-|libgz|gz-)" | sort > /tmp/lab_versions.txt
python3 - "$HERE/versions_laptop.txt" /tmp/lab_versions.txt <<'PY'
import sys
laptop = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
lab = dict(l.strip().split("=", 1) for l in open(sys.argv[2]) if "=" in l)
both = sorted(set(laptop) & set(lab))
same = [p for p in both if laptop[p] == lab[p]]
diff = [p for p in both if laptop[p] != lab[p]]
print(f"installed here {len(lab)}; also on the laptop {len(both)}; identical version {len(same)}; DIFFERENT version {len(diff)}; only here {len(set(lab) - set(laptop))}; laptop-only (GUI etc., expected) {len(set(laptop) - set(lab))}")
for p in diff[:60]:
    print(f"DIFF {p}: laptop {laptop[p]} lab {lab[p]}")
key = ["ros-jazzy-nav2-bringup", "ros-jazzy-navigation2", "ros-jazzy-turtlebot3-gazebo", "ros-jazzy-turtlebot3-navigation2", "ros-jazzy-ros-gz-sim", "ros-jazzy-ros-gz-bridge", "ros-jazzy-ros-gz-image", "ros-jazzy-turtlesim", "ros-jazzy-gz-sim-vendor"]
bad = [p for p in key if laptop.get(p) != lab.get(p)]
print("KEY PACKAGES:", "all identical" if not bad else f"DIFFERENT: {bad}")
sys.exit(1 if bad else 0)
PY
