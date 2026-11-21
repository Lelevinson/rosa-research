#!/usr/bin/env bash
# Build OUR image only. No sudo (the user is in the docker group). Does not touch other images or containers. Never runs prune commands (the Docker daemon is shared).
#   bash build_image.sh [--pin0]      (--pin0 = install the latest ROS packages instead of the laptop's pinned versions, if the archive no longer has them)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/lab_env.sh"
PIN=1; [ "${1:-}" = "--pin0" ] && PIN=0
FREE_GB=$(df -BG --output=avail / | tail -1 | tr -dc 0-9)
echo "free on / (Docker root lives there): ${FREE_GB} GB"
if [ "$FREE_GB" -lt 14 ]; then echo "STOP: less than 14 GB free on /. Ask the teacher first (the image build needs about 2x its size temporarily)."; exit 2; fi
CMD=(docker build --pull=false --build-arg "PIN=$PIN" -t "$ROSA_IMAGE" -f "$HERE/Dockerfile" "$HERE")
echo "${CMD[*]}"
[ "${DRY_RUN:-0}" = "1" ] && exit 0
"${CMD[@]}"
docker image ls --format 'image {{.Repository}}:{{.Tag}}  size {{.Size}}' "$ROSA_IMAGE"
docker image inspect --format 'base image digest layers: {{.RootFS.Layers | len}}; image id {{.Id}}' "$ROSA_IMAGE"
echo "free on / after the build: $(df -BG --output=avail / | tail -1 | tr -dc 0-9) GB"
