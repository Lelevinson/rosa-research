"""STUDY-LOCAL MoveIt 2 move_group launch for UR5e plus simple gripper (objects demo, demonstration only). Start AFTER start_sim.sh (domain 231).
usage: ros2 launch start_moveit.launch.py   (path), sim time on."""
import os
from pathlib import Path

from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

HERE = Path(os.environ.get('OBJECTS_SIM_DIR', Path(__file__).resolve().parent))


def generate_launch_description():
    moveit_config = (
        MoveItConfigsBuilder(robot_name='ur', package_name='ur_moveit_config')
        .robot_description(file_path=str(HERE / 'ur5e_gripper.urdf.xacro'), mappings={'name': 'ur', 'ur_type': 'ur5e', 'tf_prefix': '', 'simulation_controllers': str(HERE / 'controllers.yaml')})
        .robot_description_semantic(file_path=str(HERE / 'ur5e_gripper.srdf.xacro'))
        .trajectory_execution(file_path=str(HERE / 'moveit_controllers.yaml'))
        .planning_pipelines(pipelines=['ompl'])
        .to_moveit_configs()
    )
    move_group = Node(package='moveit_ros_move_group', executable='move_group', output='screen',
                      parameters=[moveit_config.to_dict(), {'use_sim_time': True, 'publish_robot_description_semantic': True}])
    return LaunchDescription([move_group])
