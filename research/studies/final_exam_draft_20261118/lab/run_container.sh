#!/usr/bin/env bash
# One long-lived container of ours (name $ROSA_CONTAINER). Subcommands: start | stop | status | shell | env-check.   DRY_RUN=1 prints the docker command instead of running it.
# Safety: never touches any other container (the teammate's container was removed with the teammate's agreement on 2026-11-19); the name is always explicit; no sudo; no --privileged. Host network since 2026-11-19 (the host firewall drops bridge -> host traffic, so a bridged container cannot reach Ollama); ROS isolation then rests on ROS_LOCALHOST_ONLY=1 and domain 220/219.
# ROS isolation: host network + ROS_LOCALHOST_ONLY=1 (loopback only), ROS_DOMAIN_ID=220 (the value the study runners require), unique Gazebo partition per stack (stack.py does that).
# Mounts: the whole $ROSA_LAB_ROOT at the same path inside (repo, results, logs, uv cache, ROS logs), the custodian directory READ-ONLY at the same path.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/lab_env.sh"
CPUS="${ROSA_CPUS:-16}"; MEM="${ROSA_MEMORY:-64g}"      # shared machine (28 cores, 123 GB): leave room for the student and the teammate; tune with the teacher
run() { if [ "${DRY_RUN:-0}" = "1" ]; then echo "+ $*"; else "$@"; fi; }
case "${1:-}" in
  start)
    run mkdir -p "$ROSA_LAB_HOME" "$UV_CACHE_DIR" "$ROSA_LAB_HOME/ros" "$ROSA_LAB_HOME/ros-log"
    GW=127.0.0.1   # host networking: Ollama listens on the host loopback
    MOUNTS=(-v "$ROSA_LAB_ROOT:$ROSA_LAB_ROOT")
    [ -d "$ROSA_CUSTODIAN_DIR" ] && MOUNTS+=(-v "$ROSA_CUSTODIAN_DIR:$ROSA_CUSTODIAN_DIR:ro")
    run docker run -d --name "$ROSA_CONTAINER" --label owner=rosa-exam --restart no --network host \
      --user "$(id -u):$(id -g)" --cpus "$CPUS" --memory "$MEM" --pids-limit 8192 \
      -e HOME="$ROSA_LAB_HOME" -e UV_CACHE_DIR="$UV_CACHE_DIR" -e ROS_HOME="$ROSA_LAB_HOME/ros" -e ROS_LOG_DIR="$ROSA_LAB_HOME/ros-log" \
      -e ROS_DOMAIN_ID=220 -e ROS_LOCALHOST_ONLY=1 -e TURTLEBOT3_MODEL=burger \
      -e ROSA_OLLAMA_URL="http://$GW:$ROSA_LAB_PORT" -e ROSA_CUSTODIAN_DIR="$ROSA_CUSTODIAN_DIR" \
      ${ROSA_GPU_ARGS:-} "${MOUNTS[@]}" -w "$ROSA_LAB_REPO" "$ROSA_IMAGE" sleep infinity ;;   # ROSA_GPU_ARGS: only after the teacher has enabled CDI/GPU (checklist step 10), e.g. "--device nvidia.com/gpu=all -e NVIDIA_DRIVER_CAPABILITIES=all"
  stop)   run docker stop "$ROSA_CONTAINER"; run docker rm "$ROSA_CONTAINER" ;;
  status) run docker ps -a --filter "name=^/${ROSA_CONTAINER}\$" --format '{{.Names}}  {{.Status}}  {{.Image}}'; run docker stats --no-stream "$ROSA_CONTAINER" ;;
  shell)  run docker exec -it "$ROSA_CONTAINER" bash -l ;;
  env-check)
    run docker exec "$ROSA_CONTAINER" bash -lc 'echo "user $(id -u):$(id -g)  HOME=$HOME"; echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY ROS_DISTRO=$ROS_DISTRO"; echo "OLLAMA via $ROSA_OLLAMA_URL"; uv --version; python3 --version; ros2 --help >/dev/null && echo ros2-ok' ;;
  *) echo "usage: DRY_RUN=1 $0 start|stop|status|shell|env-check"; exit 1 ;;
esac
