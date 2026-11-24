#!/usr/bin/env bash
# Auto-stop for the laptop Stage 1 run: creates the run's STOP file once tier 1 is finished or its remaining cells are quarantined.
# Plain bash, no Claude session. It only READS the whitelisted status counts (status_stage1.py) and, when the condition holds, creates the empty STOP file.
# It never edits the queue, the runner or any frozen file. The runner finishes its current episode and exits when it sees STOP (a few tier-2 cells may start first).
#
#   auto_stop_tier1.sh [RUN] [MACHINE]        loop: check every 300 s
#   AUTO_STOP_ONCE=1 auto_stop_tier1.sh       one check, print the decision, NEVER create STOP (test mode)
#
# Condition (status fields from queue_core.write_status):
#   A) current_cell belongs to a tier other than tier1_M_vs_E1  -> the queue already moved on (tier 1 has no pending cell left); or
#   B) tier1.done + skipped >= tier1.total                       -> every tier-1 cell is done or quarantined. `skipped` counts quarantined, not-done cells; group keys include the tier,
#                                                                   and tier 2 has not started while A is false, so these skips are tier-1 cells.
# `active_tier` is NOT used: a quarantined tier-1 cell keeps it at tier 1 forever.
# Not acted on: a state other than running (finished/crashed/blocked/stopped: logged, loop ends; the monitor alerts about crashes).
set -u
RUN="${1:-stage1_laptop_20261122}"; MACHINE="${2:-laptop}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIER="tier1_M_vs_E1"
LOG="$HOME/.config/rosa-exam/auto_stop.log"
STOP_PATH="$(python3 -c "import sys; sys.path.insert(0,'$HERE'); import monitor_stage1 as m; print(m.custody_queue_dir()/'$RUN'/'STOP')")" || { echo "cannot resolve STOP path"; exit 1; }
log() { echo "$(date -Is) $*" | tee -a "$LOG"; }
decide() {   # prints: STOP <reason> | WAIT <numbers> | END <state>
  python3 "$HERE/status_stage1.py" "$RUN" "$MACHINE" | python3 -c '
import sys, json
tier = sys.argv[1]
s = json.loads(sys.stdin.read())
if s.get("state") not in ("running", "waiting_for_ollama", "waiting_for_gpu", "starting"):
    print("END state=%s" % s.get("state")); raise SystemExit
t = s["tiers"][tier]; skipped = s.get("skipped", 0); cell = s.get("current_cell") or ""
numbers = "tier1_done=%d tier1_total=%d skipped=%d current_tier=%s" % (t["done"], t["total"], skipped, cell.split(":")[0] or "none")
if cell and not cell.startswith(tier + ":"):
    print("STOP A queue_moved_on " + numbers)
elif t["done"] + skipped >= t["total"]:
    print("STOP B tier1_done_plus_skipped_reached_total " + numbers)
else:
    print("WAIT " + numbers)
' "$TIER"
}
while true; do
  d="$(decide)" || { log "check failed (status unreadable), retry"; d="WAIT unreadable"; }
  case "$d" in
    STOP*) if [ "${AUTO_STOP_ONCE:-0}" = 1 ]; then log "TEST would create $STOP_PATH :: $d"; exit 0; fi
           touch "$STOP_PATH" && log "created STOP $STOP_PATH :: $d"; exit 0;;
    END*)  log "no action, run not running :: $d"; exit 0;;
    *)     log "$d"; [ "${AUTO_STOP_ONCE:-0}" = 1 ] && exit 0;;
  esac
  sleep 300
done
