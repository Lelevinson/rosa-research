#!/usr/bin/env bash
# usage: [BLOCK_ARGS="x y yaw"] [TRAY_ARGS="x y"] [DESC=path.xacro] tmux_sim.sh <name>   -> detached tmux session "sim_<name>", run folder runs/<name>, log runs/<name>.log
NAME=$1
D="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$D/runs"
tmux kill-session -t sim_$NAME 2>/dev/null
E=()
[ -n "$BLOCK_ARGS" ] && E+=(-e "BLOCK_ARGS=$BLOCK_ARGS")
[ -n "$TRAY_ARGS" ] && E+=(-e "TRAY_ARGS=$TRAY_ARGS")
[ -n "$DESC" ] && E+=(-e "DESC=$DESC")
tmux new-session -d -s sim_$NAME "${E[@]}" "bash $D/sim/start_sim.sh $D/runs/$NAME > $D/runs/$NAME.log 2>&1"
