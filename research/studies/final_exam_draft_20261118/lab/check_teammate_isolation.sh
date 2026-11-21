#!/usr/bin/env bash
# READ-ONLY. Looks at the metadata of the teammate's container (docker inspect only: no exec, no stop, no change) to decide whether our ROS settings can clash with it.
#   bash check_teammate_isolation.sh [container-name]
set -euo pipefail
T="${1:-<OTHER_CONTAINER>}"
echo "network mode : $(docker inspect --format '{{.HostConfig.NetworkMode}}' "$T")"
echo "ROS/GZ/RMW env of the container (from its configuration):"
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$T" | grep -E '^(ROS_|RMW_|GZ_|IGN_|FASTRTPS|CYCLONEDDS)' || echo "  (none set: it uses the default domain 0)"
echo "published ports: $(docker inspect --format '{{json .NetworkSettings.Ports}}' "$T")"
echo
echo "DECISION: if the network mode is 'host' AND its ROS_DOMAIN_ID is 220 or 219 (or both ROS_LOCALHOST_ONLY are unset on a host network), STOP and tell the owner: the study runners hard-code domain 220 (run_pilot.DOMAIN) and the Nav2 stack 219."
echo "          if the network mode is 'bridge' (default) our container is in its own network namespace: DDS discovery cannot cross, and ROS_LOCALHOST_ONLY=1 inside our container adds a second guard."
