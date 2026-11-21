# Shared settings of the lab setup. `source` it in every lab shell: `source <LAB_PATH>`
# Everything lives under ONE directory on the ext4 data disk (never on / which has 23 GB, never on the exFAT disk Lab_Project1).
export ROSA_LAB_ROOT="${ROSA_LAB_ROOT:-<LAB_PATH>}"
export ROSA_LAB_REPO="$ROSA_LAB_ROOT/repo"            # git checkout + research/ (rsync from the laptop), mounted into the container at the SAME path
export ROSA_LAB_OLLAMA_DIR="$ROSA_LAB_ROOT/ollama"          # the Ollama binary and its libraries (user space, no sudo, no service)
export OLLAMA_MODELS="$ROSA_LAB_ROOT/ollama-models"         # model blobs and manifests
export ROSA_LAB_PORT="${ROSA_LAB_PORT:-11435}"              # not 11434 (the default): verify it is free before starting
export ROSA_LAB_HOME="$ROSA_LAB_ROOT/home"                  # HOME inside the container; ROS logs and uv cache live below it
export UV_CACHE_DIR="$ROSA_LAB_ROOT/uv-cache"
export ROSA_CUSTODIAN_DIR="$ROSA_LAB_ROOT/custodian"        # held-out task files: supplied by Codex, mode 700, NEVER inside the repo, mounted read-only
export ROSA_IMAGE="rosa-exam-jazzy:20261119"                # our image tag (the teammate's image is <OTHER_CONTAINER>: never touched)
export ROSA_CONTAINER="${ROSA_CONTAINER:-rosa-exam-main}"   # our container name; every docker command of ours names it explicitly
# Where the container reaches Ollama: the docker0 gateway of the host (bridge network), on our own port. Resolved when used (docker0 must exist).
rosa_docker0_ip() { ip -4 -o addr show docker0 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -1; }
# Where the HOST reaches our Ollama (the monitor, the GPU sampler and any host-side script); the container gets the same value from run_container.sh. Study runners and the queue read ROSA_OLLAMA_URL.
export ROSA_OLLAMA_URL="${ROSA_OLLAMA_URL:-http://127.0.0.1:$ROSA_LAB_PORT}"
