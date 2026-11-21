#!/usr/bin/env bash
# Start the Stage 1 laptop run (tier 1 first; the queue works through the tiers in order) in detached tmux sessions: runner, monitor (status counts only) and the GPU sampler.
# Read `tmux new-session -d -s NAME -n WINDOW 'COMMAND'` as: create a session called NAME, detached (-d, it keeps running without a terminal), with a window (-n) running COMMAND.
# Held-out cells go ONLY through the custodian launcher queue_bridge.py (opaque ids, custodian scoring, ROS domain 219). Stop gracefully: touch <custodian queue dir>/RUN/STOP (the runner
# finishes the current episode and exits); resume = run this script again with the same RUN name (the queue skips every logged cell).
set -euo pipefail
RUN="${1:-stage1_laptop_20261122}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
SPEC="$HERE/exam_spec_stage1.json"
QDIR="$REPO/research/studies/final_exam_draft_20261118/exam_queue"
SESSION="exam-$RUN"
python3 "$HERE/verify_freeze.py" || { echo "FREEZE.json + FREEZE_REV1.json do not verify: refusing to start"; exit 1; }
tmux has-session -t "$SESSION" 2>/dev/null && { echo "tmux session $SESSION already exists"; exit 1; }
RUNNER="cd '$REPO' && export ROS_DOMAIN_ID=219 ROS_LOCALHOST_ONLY=1 ROSA_EXAM_MACHINE=laptop && uv run --no-sync python research/studies/custodian_stage1_20261121/queue_bridge.py run --spec '$SPEC' --run-name '$RUN' --machine laptop --machines laptop:1; CODE=\$?; python3 '$QDIR/monitor_stage1.py' exit '$RUN' laptop \$CODE"
MONITOR="cd '$REPO' && export ROSA_EXAM_MACHINE=laptop && python3 '$QDIR/monitor_stage1.py' --run-name '$RUN' --machine laptop"
tmux has-session -t gpusample 2>/dev/null || tmux new-session -d -s gpusample "python3 '$QDIR/gpu_state.py' sample"
tmux new-session -d -s "$SESSION" -n runner "$RUNNER"
tmux new-window -t "$SESSION" -n monitor "$MONITOR"
tmux new-window -t "$SESSION" -n guard "cd '$REPO' && python3 '$HERE/version_guard.py' '$RUN'"
tmux set-option -t "$SESSION" remain-on-exit off >/dev/null
echo "started tmux sessions $SESSION (runner, monitor, guard) and gpusample at $(date -Is)"
