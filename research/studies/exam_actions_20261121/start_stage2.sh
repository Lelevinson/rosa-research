#!/usr/bin/env bash
# Start a Stage 2 queue run in detached tmux sessions: runner (with the exit hook), monitor (status counts only, ntfy) and the GPU sampler.
#   bash start_stage2.sh MODE RUN SPEC MACHINE [MACHINES]
#   STAGE2_DRY=1 bash start_stage2.sh ...      print what would be started and exit (nothing is created or started)
# MODE = timing | live_check | exam (stage2_env.py: run-name prefixes s2time_ / s2check_ / stage2_). The launcher validates everything and REFUSES (exit 2, message in the log and in the monitor's crash
# alert) before anything starts. Needed for custody modes: ROSA_ACTION_BRIDGE_FILE, ROSA_ACTION_CUSTODY_DIR (mode 0700), ROSA_STAGE2_TASKS_FILE.
# Stop gracefully: touch research/_artifacts/exam/RUN/STOP (the runner finishes the current episode and exits); resume = the same command.
# Monitor and ntfy: the unchanged Stage 1 monitor.py reads the queue's STATUS FILE only (counts, state, tier:system:model, heartbeat) and sends fixed-template messages (finished, crash, no progress,
# Ollama down, low disk, daily) to the topic in ~/.config/rosa-exam/notify.env; it never reads a trace or a row and never commits results (commit interval set beyond the run). The exit hook
# (notify_exit.py) marks the run `crashed` when the runner exits non-zero, so a refusal or a crash alerts at once instead of after a stale heartbeat.
# Read `tmux new-session -d -s NAME -n WINDOW 'COMMAND'` as: create a detached session NAME whose window WINDOW runs COMMAND; `set -euo pipefail` stops at the first error or unset variable.
set -euo pipefail
MODE="$1"; RUN="$2"; SPEC="$3"; MACHINE="$4"; MACHINES="${5:-$MACHINE:1}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
QDIR="$REPO/research/studies/final_exam_draft_20261118/exam_queue"
LOG_DIR="$REPO/research/_artifacts/exam_stage2_logs"
SESSION="exam-$RUN"
WRAPPER="$LOG_DIR/run_$RUN.sh"
read -r -d '' WRAPPER_BODY <<EOF || true
#!/usr/bin/env bash
cd '$REPO'
export ROSA_STAGE2_MODE='$MODE' ROSA_EXAM_MACHINE='$MACHINE'
uv run python research/studies/exam_actions_20261121/run_actions_queue.py run --spec '$SPEC' --run-name '$RUN' --machine '$MACHINE' --machines '$MACHINES' 2>&1 | tee -a '$LOG_DIR/$RUN.log'
code=\${PIPESTATUS[0]}
python3 '$QDIR/notify_exit.py' '$RUN' '$MACHINE' "\$code" | tee -a '$LOG_DIR/$RUN.log'
exit "\$code"
EOF
MONITOR="cd '$REPO' && export ROSA_EXAM_MACHINE='$MACHINE' && python3 '$QDIR/monitor.py' --run-name '$RUN' --machine '$MACHINE' --commit-every-hours 1000000"
if [ "${STAGE2_DRY:-0}" = 1 ]; then
  echo "[dry] would create $WRAPPER:"; echo "$WRAPPER_BODY"
  echo "[dry] tmux new-session -d -s $SESSION -n runner 'bash $WRAPPER'"
  echo "[dry] tmux new-window -t $SESSION -n monitor \"$MONITOR\""
  echo "[dry] tmux new-session -d -s gpusample \"python3 '$QDIR/gpu_state.py' sample\"   (only if no gpusample session exists)"
  exit 0
fi
mkdir -p "$LOG_DIR"
if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION already exists"; exit 1; fi
printf '%s\n' "$WRAPPER_BODY" > "$WRAPPER"
tmux has-session -t gpusample 2>/dev/null || tmux new-session -d -s gpusample "python3 '$QDIR/gpu_state.py' sample"
tmux new-session -d -s "$SESSION" -n runner "bash '$WRAPPER'"
tmux new-window -t "$SESSION" -n monitor "$MONITOR"
tmux set-option -t "$SESSION" remain-on-exit off >/dev/null
echo "started tmux session $SESSION (runner, monitor) and gpusample at $(date -Is); log $LOG_DIR/$RUN.log; tmux attach -t $SESSION to look, Ctrl-b then d to leave"
