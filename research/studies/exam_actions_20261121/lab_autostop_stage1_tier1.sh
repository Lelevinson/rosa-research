#!/usr/bin/env bash
# Lab auto-stop for Stage 1: creates the lab run's STOP file once tier 1 is finished or its remaining cells are quarantined (same decision logic as the laptop's auto_stop_tier1.sh).
# SELF-CONTAINED on purpose: the lab release is the frozen checkout and does not contain the helper scripts added after it, so this file needs only bash and python3. Copy this one file to the
# lab host (for example into the deployment's ops/ folder); nothing in the frozen release is edited. It reads ONLY the whitelisted status counts of the queue's status file and, when the
# condition holds, creates the empty STOP file. It never edits the queue or the runner; the runner finishes its current episode and exits (a few tier-2 cells may start first).
#
#   lab_autostop_stage1_tier1.sh STATUS_FILE STOP_FILE          loop: check every 300 s (run it inside tmux)
#   AUTO_STOP_ONCE=1 lab_autostop_stage1_tier1.sh STATUS_FILE STOP_FILE   one check, print the decision, NEVER create STOP (test mode: do this first)
#
# On the lab host (paths from LAB_LAUNCH_HANDOVER_20261123.md; verify them with the test mode before arming):
#   STATUS_FILE = <bundle>/queue/stage1_lab_20261123/status_lab.json      STOP_FILE = <bundle>/queue/stage1_lab_20261123/STOP
#   <bundle> = <CUSTODY_PATH>
# Decision (fields of queue_core.write_status):
#   A) current_cell belongs to a tier other than TIER (default tier1_M_vs_E1): the queue has moved on, so tier 1 has no pending cell left; or
#   B) tier.done + skipped >= tier.total: every tier-1 cell is done or quarantined (group keys include the tier, and tier 2 has not started while A is false).
# `active_tier` is NOT used (a quarantined tier-1 cell keeps it at tier 1 forever). A state other than running/waiting/starting ends the loop without action (the monitor alerts on crashes).
set -u
STATUS_FILE="${1:?usage: lab_autostop_stage1_tier1.sh STATUS_FILE STOP_FILE}"; STOP_FILE="${2:?usage: lab_autostop_stage1_tier1.sh STATUS_FILE STOP_FILE}"
TIER="${TIER:-tier1_M_vs_E1}"
LOG="${AUTO_STOP_LOG:-$HOME/.config/rosa-exam/auto_stop_lab.log}"; mkdir -p "$(dirname "$LOG")"
log() { echo "$(date -Is) $*" | tee -a "$LOG"; }
decide() {   # prints: STOP <reason> | WAIT <numbers> | END <state> ; exits non-zero when the file cannot be read
  python3 - "$STATUS_FILE" "$TIER" <<'PY'
import json, sys
path, tier = sys.argv[1], sys.argv[2]
status = json.load(open(path))
if status.get("state") not in ("running", "waiting_for_ollama", "waiting_for_gpu", "starting"):
    print("END state=%s" % status.get("state")); raise SystemExit
t = status["tiers"][tier]; skipped = status.get("skipped", 0); cell = status.get("current_cell") or ""
numbers = "tier_done=%d tier_total=%d skipped=%d current_tier=%s" % (t["done"], t["total"], skipped, cell.split(":")[0] or "none")
if cell and not cell.startswith(tier + ":"):
    print("STOP A queue_moved_on " + numbers)
elif t["done"] + skipped >= t["total"]:
    print("STOP B tier_done_plus_skipped_reached_total " + numbers)
else:
    print("WAIT " + numbers)
PY
}
while true; do
  d="$(decide)" || { log "check failed (status unreadable), retry"; d="WAIT unreadable"; }
  case "$d" in
    STOP*) if [ "${AUTO_STOP_ONCE:-0}" = 1 ]; then log "TEST would create $STOP_FILE :: $d"; exit 0; fi
           touch "$STOP_FILE" && log "created STOP $STOP_FILE :: $d"; exit 0;;
    END*)  log "no action, run not running :: $d"; exit 0;;
    *)     log "$d"; [ "${AUTO_STOP_ONCE:-0}" = 1 ] && exit 0;;
  esac
  sleep 300
done
