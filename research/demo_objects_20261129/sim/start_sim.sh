#!/usr/bin/env bash
# Start the objects simulation (headless) in WSL: UR5e + simple gripper + table/block/tray, controllers, pose bridge. Detached-friendly (run in tmux). LABEL: demonstration only.
# usage: start_sim.sh <run folder> [block x y yaw] [tray x y]      stop: pkill -INT -f "ros2 launch ur_simulation_gz"; pkill -f "gz sim"; pkill -f ros2_control_node; pkill -f parameter_bridge
set -u
RUN=$1; shift
D="$(cd "$(dirname "$0")" && pwd)"
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-233} ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST LIBGL_ALWAYS_SOFTWARE=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$RUN"
BLOCK=${1:-"0.45 0.10 0.0"}; TRAY=${2:-"0.45 -0.28"}
python3 "$D/make_world.py" "$RUN/world.sdf" --block $BLOCK --tray $TRAY >/dev/null
export GZ_PARTITION=objects-demo-$$
echo "$GZ_PARTITION" > "$RUN/gz_partition.txt"
ros2 launch ur_simulation_gz ur_sim_control.launch.py ur_type:=ur5e launch_rviz:=false gazebo_gui:=false initial_joint_controller:=joint_trajectory_controller \
  description_file:="$D/ur5e_gripper.urdf.xacro" controllers_file:="$D/controllers.yaml" world_file:="$RUN/world.sdf" > "$RUN/launch.log" 2>&1 &
LAUNCH=$!
echo $LAUNCH > "$RUN/launch.pid"
# gripper controller + ground-truth pose bridge (Gazebo dynamic poses -> ROS tf2_msgs/TFMessage on /objects/poses)
sleep 12
ros2 run controller_manager spawner gripper_position_controller -c /controller_manager > "$RUN/gripper_spawner.log" 2>&1
ros2 run ros_gz_bridge parameter_bridge "/world/objects_world/dynamic_pose/info@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V" \
  "/objects/red_block/attach@std_msgs/msg/Empty]gz.msgs.Empty" "/objects/red_block/detach@std_msgs/msg/Empty]gz.msgs.Empty" \
  --ros-args -r /world/objects_world/dynamic_pose/info:=/objects/poses > "$RUN/bridge.log" 2>&1 &
echo $! > "$RUN/bridge.pid"
wait $LAUNCH
