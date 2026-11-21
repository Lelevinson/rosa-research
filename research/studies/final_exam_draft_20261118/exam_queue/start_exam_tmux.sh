#!/usr/bin/env bash
# Start the exam queue and its monitor in a detached tmux session, so closing a terminal window does not stop them.
#   bash start_exam_tmux.sh RUN_NAME SPEC_FILE [MACHINE] [MACHINES] [-- extra queue_core args, e.g. --dummy]
#   MACHINE defaults to "all" (single machine); for two machines use e.g. laptop and lab with MACHINES=laptop:0.4,lab:0.6
# Read it as: tmux new-session -d -s NAME -n WINDOW 'COMMAND'  = create a session called NAME, detached (-d), with one window (-n) running COMMAND.
# Attach later with `tmux attach -t exam-RUN_NAME`; detach again with Ctrl-b then d. Stop gracefully with: touch research/_artifacts/exam/RUN_NAME/STOP
set -euo pipefail
RUN="${1:?run name}"; SPEC="${2:?spec file}"; MACHINE="${3:-all}"; MACHINES="${4:-all:1}"
shift $(( $# < 4 ? $# : 4 )); [ "${1:-}" = "--" ] && shift
EXTRA=("$@")
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
SESSION="exam-$RUN"
if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION already exists (attach with: tmux attach -t $SESSION)"; exit 1; fi
# Ollama address (step 8a): the runner inside the lab container already has ROSA_OLLAMA_URL from `docker run -e`; the MONITOR runs on the host, so it must be given the address explicitly
# (tmux windows do not inherit this shell's variables reliably). Without it the monitor would check the laptop's default address and send false "Ollama down" messages.
OLLAMA_EXPORT=""; [ -n "${ROSA_OLLAMA_URL:-}" ] && OLLAMA_EXPORT="export ROSA_OLLAMA_URL='$ROSA_OLLAMA_URL' &&"
if [ -n "${EXAM_EXEC:-}" ] && [ -z "${ROSA_OLLAMA_URL:-}" ]; then echo "WARNING: EXAM_EXEC is set but ROSA_OLLAMA_URL is not: the host monitor will check the default (laptop) Ollama address. On the lab: source lab/lab_env.sh first."; fi
RUNNER="cd '$REPO' && $OLLAMA_EXPORT export ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 ROSA_EXAM_MACHINE='$MACHINE' && uv run python '$HERE/queue_core.py' run --spec '$SPEC' --run-name '$RUN' --machine '$MACHINE' --machines '$MACHINES' ${EXTRA[*]:-}; code=\$?; python3 '$HERE/notify_exit.py' '$RUN' '$MACHINE' \$code; echo; echo 'runner finished (exit '\$code'). Press Enter to close this window.'; read"
# Lab computer: the runner runs INSIDE a long-lived container, the monitor stays on the host (so notifications survive a dead container). Set, for example,
#   EXAM_EXEC="docker exec -it rosa-exam-main bash -lc"      (the container mounts the repo at the same path as the host)
if [ -n "${EXAM_EXEC:-}" ]; then RUNNER="$EXAM_EXEC $(printf '%q' "$RUNNER")"; fi
MONITOR="cd '$REPO' && $OLLAMA_EXPORT export ROSA_EXAM_MACHINE='$MACHINE' && python3 '$HERE/monitor.py' --run-name '$RUN' --machine '$MACHINE' ${MONITOR_ARGS:-}"
tmux new-session -d -s "$SESSION" -n runner "$RUNNER"
tmux new-window -t "$SESSION" -n monitor "$MONITOR"
tmux set-option -t "$SESSION" remain-on-exit off >/dev/null
sleep 12
if [ ! -f "$REPO/research/_artifacts/exam/$RUN/monitor_state_$MACHINE.json" ]; then echo "WARNING: the monitor has not written its state file after 12 s: notifications may not be working. Check: tmux attach -t $SESSION (window monitor)."; fi
GPULOG="$REPO/research/_artifacts/exam/gpu_state.jsonl"
if command -v nvidia-smi >/dev/null 2>&1 && { [ ! -f "$GPULOG" ] || [ $(( $(date +%s) - $(stat -c %Y "$GPULOG") )) -gt 60 ]; }; then echo "WARNING: no GPU sample in the last 60 s ($GPULOG). Start the sampler on the host: tmux new -d -s gpusample 'python3 $HERE/gpu_state.py sample'. Episodes then carry only their own start/end snapshots."; fi
echo "started tmux session $SESSION (windows: runner, monitor). Attach: tmux attach -t $SESSION"
