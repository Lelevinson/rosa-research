#!/usr/bin/env bash
# usage: run_py.sh <script.py> [args]   runs a script in the research env with ROS sourced, domain 231
D="$(cd "$(dirname "$0")" && pwd)"
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=231 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST PYTHONDONTWRITEBYTECODE=1
cd $D
S=$1; shift
exec /home/martin/.local/share/rosa-envs/research/bin/python -B $S "$@"
