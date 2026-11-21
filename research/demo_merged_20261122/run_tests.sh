#!/usr/bin/env bash
# Scripted tests of the merged demo: zero model calls, no GPU, no Gazebo. Run inside WSL: bash run_tests.sh [pattern]
# Uses the research environment (rosa and rosa_reliability resolve to the rosa-research checkout at member/martin 8713f9b).
HERE="$(cd "$(dirname "$0")" && pwd)"
PY=/home/martin/.local/share/rosa-envs/research/bin/python
set +u; source /opt/ros/jazzy/setup.bash; set -u
cd "$HERE" && PYTHONDONTWRITEBYTECODE=1 "$PY" -B -m unittest discover -s tests -p "${1:-test_*.py}" -v
