#!/usr/bin/env bash
# Integrity check of the lab setup. Run ON THE LAB HOST (not inside the container) before every exam block.
#   bash check_integrity.sh                      check against the recorded baseline (READ-ONLY: writes nothing)
#   bash check_integrity.sh --since "2026-11-19 21:44"   also list files changed after that time (default: the time of the recorded baseline)
#   INTEGRITY_RECORD_OK=1 bash check_integrity.sh record  write a NEW baseline (only after an intended change that the owner approved;
#                                                       the only command here that writes, and only under $ROSA_LAB_ROOT/integrity/)
# Output: one line per check, PASS / FAIL / WARN / INFO. Exit code 1 if any FAIL (do not start an exam block), 0 otherwise. WARN = look at it, a human decides.
# What it never does: stop, start or change anything; it never lists or opens the custodian folder (held-out tasks): only the folder's own mode and owner are read.
# Baseline: $ROSA_LAB_ROOT/integrity/expected.env (image id, git commit, Ollama version, model digests, folder modes) and repo_manifest.sha256 (sha256 of every file of the repo
# except .git, .venv, __pycache__, research/_artifacts, exam_results and LAB_SETUP_LOG.md, the append-only setup log). The expected values were taken from the build log, the frozen digests and the laptop, not from this check.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/lab_env.sh"
INTEG="$ROSA_LAB_ROOT/integrity"; EXPECTED="$INTEG/expected.env"; MANIFEST="$INTEG/repo_manifest.sha256"
OLLAMA_URL="http://127.0.0.1:$ROSA_LAB_PORT"
FAILS=0; WARNS=0
pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; FAILS=$((FAILS+1)); }
warn() { echo "WARN  $*"; WARNS=$((WARNS+1)); }
info() { echo "INFO  $*"; }
FOLDERS=("$ROSA_LAB_ROOT" "$ROSA_LAB_ROOT/custodian" "$ROSA_LAB_REPO" "$ROSA_LAB_OLLAMA_DIR" "$OLLAMA_MODELS" "$ROSA_LAB_HOME" "$ROSA_LAB_ROOT/logs" "$UV_CACHE_DIR")

manifest_files() {  # the files that must not change: everything of the repo except git data, the environment, caches and results
  (cd "$ROSA_LAB_REPO" && find . -type f -not -path './.git/*' -not -path './.venv/*' -not -path '*/__pycache__/*' -not -path './research/_artifacts/*' -not -path '*/exam_results/*' -not -name LAB_SETUP_LOG.md -print0 | sort -z)
}

if [ "${1:-}" = "record" ]; then
  [ "${INTEGRITY_RECORD_OK:-0}" = "1" ] || { echo "refusing: record writes a new baseline. Set INTEGRITY_RECORD_OK=1 after an approved change."; exit 2; }
  mkdir -p "$INTEG"
  IMG_ID="$(docker image inspect "$ROSA_IMAGE" --format '{{.Id}}')"; IMG_SIZE="$(docker image ls --format '{{.Size}}' "$ROSA_IMAGE")"
  HEAD_SHA="$(git -C "$ROSA_LAB_REPO" rev-parse HEAD)"; VERSION="$(curl -s "$OLLAMA_URL/api/version")"
  { echo "# written by check_integrity.sh record on $(date -Is) by $(id -un); expected values, see the header of check_integrity.sh"
    echo "RECORDED_AT=\"$(date '+%Y-%m-%d %H:%M:%S')\""
    echo "EXPECTED_IMAGE_ID=$IMG_ID"; echo "EXPECTED_IMAGE_SIZE=$IMG_SIZE"; echo "EXPECTED_GIT_HEAD=$HEAD_SHA"
    echo "EXPECTED_OLLAMA_VERSION='$VERSION'"
    for d in "${FOLDERS[@]}"; do echo "MODE_${d//[^A-Za-z0-9]/_}=\"$(stat -c '%a %U' "$d")\""; done
  } > "$EXPECTED.new"
  echo "baseline values:"; cat "$EXPECTED.new"
  echo "(model digests are kept in $INTEG/expected_digests.json; edit it by hand from the laptop's digests, it is not rewritten here)"
  (cd "$ROSA_LAB_REPO" && manifest_files | xargs -0 sha256sum) > "$MANIFEST.new"
  mv "$EXPECTED.new" "$EXPECTED"; mv "$MANIFEST.new" "$MANIFEST"; echo "recorded $(wc -l < "$MANIFEST") file hashes"; exit 0
fi

[ -f "$EXPECTED" ] || { echo "FAIL  no baseline at $EXPECTED (run the record command once, with the owner's approval)"; exit 1; }
source "$EXPECTED"
SINCE="$RECORDED_AT"; [ "${1:-}" = "--since" ] && SINCE="${2:?time}"
echo "integrity check $(date -Is) on $(hostname) as $(id -un); baseline recorded $RECORDED_AT; changes listed since: $SINCE"

# 1. our container and image
CTR_STATE="$(docker inspect "$ROSA_CONTAINER" --format '{{.State.Running}}|{{.Image}}|{{.Config.Image}}|{{.HostConfig.NetworkMode}}|{{.State.StartedAt}}' 2>/dev/null)"
if [ -z "$CTR_STATE" ]; then fail "container $ROSA_CONTAINER does not exist"; else
  IFS='|' read -r RUNNING CTR_IMG CTR_TAG NETMODE STARTED <<< "$CTR_STATE"
  [ "$RUNNING" = "true" ] && pass "container $ROSA_CONTAINER running (started $STARTED)" || fail "container $ROSA_CONTAINER is not running"
  [ "$CTR_IMG" = "$EXPECTED_IMAGE_ID" ] && pass "container runs from the expected image id ${CTR_IMG:7:12}" || fail "container image id ${CTR_IMG:7:12} differs from expected ${EXPECTED_IMAGE_ID:7:12}"
  [ "$NETMODE" = "host" ] && pass "network mode host (the design since 2026-11-19)" || fail "network mode is $NETMODE, expected host"
  ENVS="$(docker inspect "$ROSA_CONTAINER" --format '{{range .Config.Env}}{{println .}}{{end}}')"
  echo "$ENVS" | grep -qx 'ROS_DOMAIN_ID=220' && echo "$ENVS" | grep -qx 'ROS_LOCALHOST_ONLY=1' && pass "ROS_DOMAIN_ID=220 and ROS_LOCALHOST_ONLY=1 in the container configuration" || fail "container ROS settings differ from 220 / localhost-only"
  CUSTODIAN_RW="$(docker inspect "$ROSA_CONTAINER" --format '{{range .Mounts}}{{if eq .Destination "'"$ROSA_CUSTODIAN_DIR"'"}}{{.RW}}{{end}}{{end}}')"
  [ "$CUSTODIAN_RW" = "false" ] && pass "custodian folder is mounted read-only" || fail "custodian mount is not read-only (RW='$CUSTODIAN_RW')"
fi
IMG_ID_NOW="$(docker image inspect "$ROSA_IMAGE" --format '{{.Id}}' 2>/dev/null)"; IMG_SIZE_NOW="$(docker image ls --format '{{.Size}}' "$ROSA_IMAGE" 2>/dev/null)"
[ "$IMG_ID_NOW" = "$EXPECTED_IMAGE_ID" ] && pass "image $ROSA_IMAGE id unchanged (${IMG_ID_NOW:7:12})" || fail "image $ROSA_IMAGE id is '${IMG_ID_NOW:7:12}', expected ${EXPECTED_IMAGE_ID:7:12}"
[ "$IMG_SIZE_NOW" = "$EXPECTED_IMAGE_SIZE" ] && pass "image size unchanged ($IMG_SIZE_NOW)" || fail "image size '$IMG_SIZE_NOW', expected $EXPECTED_IMAGE_SIZE"

# 2. repository
HEAD_NOW="$(git -C "$ROSA_LAB_REPO" rev-parse HEAD 2>/dev/null)"
[ "$HEAD_NOW" = "$EXPECTED_GIT_HEAD" ] && pass "git HEAD ${HEAD_NOW:0:7} as expected" || fail "git HEAD ${HEAD_NOW:0:7}, expected ${EXPECTED_GIT_HEAD:0:7}"
CHANGED="$(git -C "$ROSA_LAB_REPO" --no-optional-locks status --porcelain --untracked-files=no 2>/dev/null)"
[ -z "$CHANGED" ] && pass "tracked files match the commit (git compares content hashes)" || fail "tracked files modified: $(echo "$CHANGED" | head -5 | tr '\n' ';')"
if [ -f "$MANIFEST" ]; then
  BAD="$(cd "$ROSA_LAB_REPO" && sha256sum -c --quiet "$MANIFEST" 2>&1 | grep -v ': OK$' | head -5)"
  [ -z "$BAD" ] && pass "all $(wc -l < "$MANIFEST") manifest files (tracked and research files) have their recorded hash" || fail "manifest mismatch: $(echo "$BAD" | tr '\n' ';')"
  NEW="$(cd "$ROSA_LAB_REPO" && comm -13 <(cut -c67- "$MANIFEST" | sort) <(manifest_files | tr '\0' '\n' | sort) | head -5)"
  [ -z "$NEW" ] && pass "no file outside the manifest" || warn "files not in the manifest (new since the baseline): $(echo "$NEW" | tr '\n' ' ')"
else fail "no manifest at $MANIFEST"; fi
[ -d "$ROSA_LAB_REPO/research/.local" ] && fail "research/.local exists in the lab repo (must never be synced)" || pass "no research/.local in the lab repo"

# 3. Ollama (ours)
VERSION_NOW="$(curl -s -m 8 "$OLLAMA_URL/api/version")"
[ "$VERSION_NOW" = "$EXPECTED_OLLAMA_VERSION" ] && pass "Ollama version $VERSION_NOW" || fail "Ollama version '$VERSION_NOW', expected '$EXPECTED_OLLAMA_VERSION'"
LISTEN="$(ss -ltnH "sport = :$ROSA_LAB_PORT" 2>/dev/null | awk '{print $4}' | sort -u | tr '\n' ' ')"
[ "$LISTEN" = "127.0.0.1:$ROSA_LAB_PORT " ] && pass "port $ROSA_LAB_PORT listens on 127.0.0.1 only" || fail "port $ROSA_LAB_PORT listeners: '$LISTEN' (expected only 127.0.0.1:$ROSA_LAB_PORT)"
OLLAMA_PIDS="$(ss -ltnpH "sport = :$ROSA_LAB_PORT" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u | tr '\n' ' ')"
for pid in $OLLAMA_PIDS; do [ "$(readlink /proc/$pid/exe 2>/dev/null)" = "$ROSA_LAB_OLLAMA_DIR/bin/ollama" ] && pass "listener pid $pid is our Ollama binary" || fail "listener pid $pid is not $ROSA_LAB_OLLAMA_DIR/bin/ollama"; done
if [ -f "$INTEG/expected_digests.json" ]; then
  DIGEST_OUT="$(curl -s -m 8 "$OLLAMA_URL/api/tags" | python3 -I -c '
import sys, json
have = {m["name"]: m["digest"] for m in json.load(sys.stdin)["models"]}
want = json.load(open(sys.argv[1]))
bad = [k for k in want if have.get(k) != want[k]]
extra = [k for k in have if k not in want]
print(("PASS  all %d model digests unchanged" % len(want)) if not bad else ("FAIL  model digest missing or changed: %s" % bad))
if extra: print("WARN  models not in the baseline: %s" % extra)
' "$INTEG/expected_digests.json" 2>&1)"
  [ -n "$DIGEST_OUT" ] || DIGEST_OUT="FAIL  could not read the model list from Ollama"
  echo "$DIGEST_OUT"; FAILS=$((FAILS + $(echo "$DIGEST_OUT" | grep -c '^FAIL'))); WARNS=$((WARNS + $(echo "$DIGEST_OUT" | grep -c '^WARN')))
else fail "no $INTEG/expected_digests.json"; fi

# 4. foreign containers, Ollama servers and ROS / Gazebo processes
OTHER_OLLAMA="$(ss -ltnpH 2>/dev/null | grep '"ollama"' | grep -v ":$ROSA_LAB_PORT " | awk '{print $4}' | tr '\n' ' ')"
[ -z "$OTHER_OLLAMA" ] && pass "no other Ollama server listening" || warn "other Ollama server(s) on this host: $OTHER_OLLAMA (not ours; they share the GPU: an idle one holds no VRAM, a loaded model does)"
OTHERS="$(docker ps --format '{{.Names}}' | grep -vx "$ROSA_CONTAINER")"
for c in $OTHERS; do
  D="$(docker inspect "$c" --format '{{.Config.Image}}|{{.HostConfig.NetworkMode}}|{{.State.StartedAt}}')"; E="$(docker inspect "$c" --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E '^ROS_(DOMAIN_ID|LOCALHOST_ONLY)=' | tr '\n' ' ')"
  if echo "$E" | grep -qE 'ROS_DOMAIN_ID=(219|220)( |$)'; then fail "running container $c uses our ROS domain: $E"; else warn "other running container $c (image/net/started: $D; ${E:-no ROS_* in its configuration}), not ours: do not touch, confirm it is not on domain 219/220"; fi
done
[ -z "$OTHERS" ] && pass "no other running container"
OURS_PIDS="$(docker top "$ROSA_CONTAINER" -eo pid 2>/dev/null | tail -n +2 | tr -d ' ' | sort -u)"
FOREIGN="$(ps -eo user,pid,args | grep -Ei 'ros2|gz sim|gzserver|component_container|nav2_|turtlesim|rmw_|fast-?discovery' | grep -v grep | while read -r u p rest; do echo "$OURS_PIDS" | grep -qx "$p" || echo "$u $p $(echo "$rest" | cut -c1-70)"; done)"
# processes of other containers show up in ps too: tell them apart by the pid lists of the running containers
for c in $OTHERS; do P="$(docker top "$c" -eo pid 2>/dev/null | tail -n +2 | tr -d ' ')"; FOREIGN="$(echo "$FOREIGN" | while read -r u p rest; do [ -z "$p" ] && continue; echo "$P" | grep -qx "$p" || echo "$u $p $rest"; done)"; done
[ -z "$FOREIGN" ] && pass "no ROS / Gazebo process outside our container and the other containers' own" || warn "ROS/Gazebo-like processes not in any container of the host: $(echo "$FOREIGN" | tr '\n' ';')"
ROS_IN_OTHERS=0; for c in $OTHERS; do n="$(docker top "$c" -eo args 2>/dev/null | grep -Eci 'ros2 |gz sim|gzserver|component_container|nav2_')"; ROS_IN_OTHERS=$((ROS_IN_OTHERS+n)); done
[ "$ROS_IN_OTHERS" -eq 0 ] && pass "no ROS / Gazebo process inside the other containers" || warn "$ROS_IN_OTHERS ROS/Gazebo-like process(es) inside other containers: check their ROS_DOMAIN_ID (listed above)"

# 5. permissions of our folders
for d in "${FOLDERS[@]}"; do
  var="MODE_${d//[^A-Za-z0-9]/_}"; want="${!var}"; have="$(stat -c '%a %U' "$d" 2>/dev/null)"
  [ "$have" = "$want" ] && pass "mode/owner of $d = $have" || fail "mode/owner of $d is '$have', baseline '$want'"
done

# 6. modified since: by which user (the custodian folder is only stat-ed, never listed)
info "files under $ROSA_LAB_ROOT changed since $SINCE (modification or status-change time; excluded: custodian contents, .venv, uv-cache, home, logs, downloads, results, git objects):"
CHG="$(find "$ROSA_LAB_ROOT" \( -path "$ROSA_LAB_ROOT/custodian" -o -path "$ROSA_LAB_ROOT/repo/.venv" -o -path "$UV_CACHE_DIR" -o -path "$ROSA_LAB_HOME" -o -path "$ROSA_LAB_ROOT/logs" -o -path "$ROSA_LAB_ROOT/downloads" -o -path "$ROSA_LAB_ROOT/repo/.git/objects" -o -path "$OLLAMA_MODELS" -o -path '*/__pycache__' -o -path '*/_artifacts' -o -path '*/exam_results' \) -prune -o -type f \( -newermt "$SINCE" -o -newerct "$SINCE" \) -printf '%u %TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort -k2,3 | head -60)"
[ -z "$CHG" ] && info "  (none)" || echo "$CHG" | sed 's/^/INFO    /'
CUST_M="$(stat -c '%y' "$ROSA_CUSTODIAN_DIR" | cut -c1-16)"; info "custodian folder itself: last status/modification $CUST_M (contents not read)"
NMOD="$(find "$OLLAMA_MODELS" -type f \( -newermt "$SINCE" -o -newerct "$SINCE" \) 2>/dev/null | wc -l)"; info "model store: $NMOD file(s) changed since $SINCE (new models add files; digests are checked above)"

# 7. resources (information for the operator; not part of pass/fail except low disk)
FREE_ROOT=$(df -BG --output=avail / | tail -1 | tr -dc 0-9); FREE_D1=$(df -BG --output=avail "$ROSA_LAB_ROOT" | tail -1 | tr -dc 0-9)
[ "$FREE_ROOT" -ge 14 ] && pass "/ has $FREE_ROOT GB free" || warn "/ has only $FREE_ROOT GB free (Docker's root is there; the rule says stop under 14 GB for builds)"
[ "$FREE_D1" -ge 50 ] && pass "d1 has $FREE_D1 GB free" || warn "d1 has only $FREE_D1 GB free"
info "GPU: $(nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null)"
OTHERGPU="$(nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader,nounits 2>/dev/null | awk -F', ' '$3+0 >= 1024 {print $1" "$2" "$3" MiB"}')"
[ -z "$OTHERGPU" ] && pass "no compute process holds 1 GiB or more of VRAM (the GPU contention threshold)" || warn "GPU processes holding >= 1 GiB (ours are ollama runners of our server): $(echo "$OTHERGPU" | tr '\n' ';')"
echo "RESULT  $FAILS FAIL, $WARNS WARN"
[ "$FAILS" -eq 0 ]
