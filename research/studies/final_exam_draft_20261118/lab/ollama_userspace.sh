#!/usr/bin/env bash
# Ollama in user space: no sudo, no system service, no change to the host. Binary and libraries under $ROSA_LAB_OLLAMA_DIR, models under $OLLAMA_MODELS (both on the ext4 data disk).
#   bash ollama_userspace.sh install ARCHIVE_PATH     (ARCHIVE_PATH = the official Linux amd64 release archive of the SAME version as the laptop, 0.40.16, already downloaded and checksum-verified)
#   bash ollama_userspace.sh start | stop | status | digests
# `start` binds to 127.0.0.1 and our own port (the container runs with --network host). Any local user of the host can still reach it (Ollama has no authentication), but nothing else on the network can.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/lab_env.sh"
BIN="$ROSA_LAB_OLLAMA_DIR/bin/ollama"
HOSTADDR=127.0.0.1   # loopback only: our container uses host networking (since 2026-11-19), so it reaches this address; nothing is opened to the lab network or the docker bridge
export OLLAMA_HOST="$HOSTADDR:$ROSA_LAB_PORT" OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=5m
case "${1:-}" in
  install)
    ARCHIVE="${2:?path of the release archive}"; mkdir -p "$ROSA_LAB_OLLAMA_DIR" "$OLLAMA_MODELS"
    case "$ARCHIVE" in *.tgz|*.tar.gz) tar -xzf "$ARCHIVE" -C "$ROSA_LAB_OLLAMA_DIR" ;; *.tar.zst) tar --zstd -xf "$ARCHIVE" -C "$ROSA_LAB_OLLAMA_DIR" ;; *) echo "unknown archive type"; exit 2 ;; esac
    "$BIN" --version ;;
  start)
    if ss -ltn "sport = :$ROSA_LAB_PORT" | grep -q LISTEN; then echo "port $ROSA_LAB_PORT is already in use: pick another (ROSA_LAB_PORT=...)"; exit 3; fi
    mkdir -p "$ROSA_LAB_ROOT/logs"
    echo "starting $BIN on $OLLAMA_HOST, models in $OLLAMA_MODELS (run this inside tmux so it survives the SSH session: tmux new -d -s ollama 'bash $0 start')"
    exec "$BIN" serve >> "$ROSA_LAB_ROOT/logs/ollama.log" 2>&1 ;;
  stop)   pkill -u "$(id -u)" -f "$BIN serve" && echo stopped || echo "no Ollama of ours was running" ;;
  status) curl -s "http://$OLLAMA_HOST/api/version"; echo; curl -s "http://$OLLAMA_HOST/api/ps"; echo ;;
  digests) curl -s "http://$OLLAMA_HOST/api/tags" | python3 -c "
import sys, json
d = {m['name']: m['digest'] for m in json.load(sys.stdin)['models']}
e = {'lfm3:1.7b': 'b36a103fe2f8fbe9df2ceec88b9cfdf842dc04aaabe2b4677d1acf8e16570b5d', 'bonsai-2:4b': '93edd652c9326fb1e782c1f54e997ce6a46e2351c763777db0c63b8a51cf6bec',
     'gpt-oss:20b': 'f38aa0c53da5f8c49d08c43a99df24ff53167fe68e24664a7777288e7656fdfe', 'qwen3.5:9b': '56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90'}
print({k: d.get(k) == v for k, v in e.items()})" ;;
  *) echo "usage: $0 install ARCHIVE | start | stop | status | digests"; exit 1 ;;
esac
