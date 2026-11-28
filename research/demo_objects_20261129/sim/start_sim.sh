#!/usr/bin/env bash
# Start the objects simulation (headless) in WSL: UR5e + simple gripper + table/block/tray, controllers, pose bridge. Detached-friendly (run in tmux). LABEL: demonstration only.
# usage: start_sim.sh <run folder> [block x y yaw] [tray x y]      stop: pkill -INT -f "ros2 launch ur_simulation_gz"; pkill -f "gz sim"; pkill -f ros2_control_node; pkill -f parameter_bridge
RUN=$1; shift
D="$(cd "$(dirname "$0")" && pwd)"
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-231} ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST LIBGL_ALWAYS_SOFTWARE=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$RUN"
BLOCK=${BLOCK_ARGS:-${1:-"0.45 0.10 0.0"}}; TRAY=${TRAY_ARGS:-${2:-"0.45 -0.28"}}
python3 "$D/make_world.py" "$RUN/world.sdf" --block $BLOCK --tray $TRAY >/dev/null
export GZ_PARTITION=objects-demo-$$
echo "$GZ_PARTITION" > "$RUN/gz_partition.txt"
ros2 launch ur_simulation_gz ur_sim_control.launch.py ur_type:=ur5e launch_rviz:=false gazebo_gui:=false initial_joint_controller:=joint_trajectory_controller \
  description_file:="${DESC:-$D/ur5e_gripper.urdf.xacro}" controllers_file:="$D/controllers.yaml" world_file:="$RUN/world.sdf" > "$RUN/launch.log" 2>&1 &
LAUNCH=$!
echo $LAUNCH > "$RUN/launch.pid"
# gripper controller + ground-truth pose bridge (Gazebo world poses -> ROS tf2_msgs/TFMessage on /world/objects_world/pose/info)
sleep 12
# the DetachableJoint plugin attaches at load (observed 2026-11-29: block was carried by the arm). Detach once so the block starts free; attach happens only on command.
for i in 1 2 3 4 5 6; do gz topic -t /objects/red_block/detach -m gz.msgs.Empty -p ' ' >/dev/null 2>&1; sleep 1; done
ros2 run controller_manager spawner gripper_controller -c /controller_manager > "$RUN/gripper_spawner.log" 2>&1
ros2 run ros_gz_bridge parameter_bridge "/world/objects_world/pose/info@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V" \
  "/objects/red_block/attach@std_msgs/msg/Empty]gz.msgs.Empty" "/objects/red_block/detach@std_msgs/msg/Empty]gz.msgs.Empty" \
  > "$RUN/bridge.log" 2>&1 &
echo $! > "$RUN/bridge.pid"
wait $LAUNCH
