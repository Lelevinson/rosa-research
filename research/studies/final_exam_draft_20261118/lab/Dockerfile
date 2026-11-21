# syntax=docker/dockerfile:1
# ROSA exam image: ROS 2 Jazzy (Ubuntu 24.04) + headless Gazebo + Nav2 + TurtleBot3 + turtlesim + uv. Built on the lab computer (Ubuntu 25.04 host, which has no Jazzy binaries).
# Official base: the ROS project's `ros:jazzy-ros-base` (no GUI tools: rviz and the desktop stack are NOT installed, which keeps the image small).
# Versions are pinned to the laptop's (see versions_laptop.txt). If the ROS apt archive no longer has a pinned version the build FAILS LOUDLY; rebuild with `--build-arg PIN=0` and run
# compare_versions.sh to record the differences. Expected size: about 4-6.5 GB on disk (an estimate from the package sets, NOT measured; check `docker image ls`).
#   build:  bash build_image.sh            run:  bash run_container.sh start
ARG BASE_IMAGE=ros:jazzy-ros-base
FROM ${BASE_IMAGE}

ARG PIN=1
# The lab network cannot reach archive.ubuntu.com / security.ubuntu.com (connection timeouts, found 2026-11-19); the Taiwan mirror serves the same signed archive, including the noble-security pocket.
ARG UBUNTU_MIRROR=http://tw.archive.ubuntu.com/ubuntu
ARG V_NAV2_BRINGUP=1.3.13-1noble.20261006.042503
ARG V_NAVIGATION2=1.3.13-1noble.20260921.033624
ARG V_TB3_GAZEBO=2.3.7-1noble.20261006.041329
ARG V_TB3_NAV2=2.3.6-1noble.20261006.044113
ARG V_GZ_SIM_VENDOR=0.0.13-1noble.20260905.073557
ARG V_ROS_GZ_SIM=1.0.24-1noble.20261006.035056
ARG V_ROS_GZ_BRIDGE=1.0.24-1noble.20260920.234644
ARG V_ROS_GZ_IMAGE=1.0.24-1noble.20260921.023911
ARG V_TURTLESIM=1.8.4-1noble.20260903.071057

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 TURTLEBOT3_MODEL=burger \
    ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 \
    LIBGL_ALWAYS_SOFTWARE=1 \
    UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

# Pinned ROS packages (pin = "package=version"; with PIN=0 the latest is installed). Software OpenGL/EGL (Mesa) for headless rendering without a GPU.
RUN set -eux; \
    pin() { if [ "$PIN" = "1" ]; then echo "$1=$2"; else echo "$1"; fi; }; \
    sed -i "s|http://archive.ubuntu.com/ubuntu|${UBUNTU_MIRROR}|g; s|http://security.ubuntu.com/ubuntu|${UBUNTU_MIRROR}|g" /etc/apt/sources.list.d/ubuntu.sources; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        $(pin ros-jazzy-nav2-bringup "$V_NAV2_BRINGUP") \
        $(pin ros-jazzy-navigation2 "$V_NAVIGATION2") \
        $(pin ros-jazzy-turtlebot3-gazebo "$V_TB3_GAZEBO") \
        $(pin ros-jazzy-turtlebot3-navigation2 "$V_TB3_NAV2") \
        $(pin ros-jazzy-gz-sim-vendor "$V_GZ_SIM_VENDOR") \
        $(pin ros-jazzy-ros-gz-sim "$V_ROS_GZ_SIM") \
        $(pin ros-jazzy-ros-gz-bridge "$V_ROS_GZ_BRIDGE") \
        $(pin ros-jazzy-ros-gz-image "$V_ROS_GZ_IMAGE") \
        $(pin ros-jazzy-turtlesim "$V_TURTLESIM") \
        libegl1 libegl-mesa0 libgl1-mesa-dri libglx-mesa0 mesa-utils-bin \
        tmux git curl ca-certificates procps iproute2 less rsync \
    ; \
    apt-get clean; rm -rf /var/lib/apt/lists/*

# uv, same version as the laptop (0.13.2), copied from the official image; Python comes from the system (3.12 on Ubuntu 24.04), never downloaded.
COPY --from=ghcr.io/astral-sh/uv:0.13.2 /uv /uvx /usr/local/bin/

# Login shells (docker exec ... bash -lc) get ROS without the base image's entrypoint.
RUN printf '%s\n' 'source /opt/ros/jazzy/setup.bash' > /etc/profile.d/ros2.sh

# The container runs as the host user (docker run --user), HOME and ROS_HOME point to the mounted data disk (set by run_container.sh); nothing is written inside the image at run time.
WORKDIR <LAB_PATH>
CMD ["sleep", "infinity"]
