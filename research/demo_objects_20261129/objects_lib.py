"""Low-level helpers for the objects demo (UR5e + simple gripper, Gazebo, MoveIt 2). NEW FILE; frozen demo files are not modified.
LABEL: object poses read from the simulator (ground truth); simulated gripper with grasp assist; demonstration only, not evaluated, not for the paper.
Needs ROS sourced, domain 231, the simulation (sim/start_sim.sh) and move_group (sim/start_moveit.launch.py) running."""
import json
import math
import os
import re
import subprocess
import time

import rclpy
from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import Pose, PoseStamped
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (BoundingVolume, Constraints, MotionPlanRequest, OrientationConstraint, PlanningOptions, PositionConstraint, PlanningScene,
                             CollisionObject, MoveItErrorCodes, RobotTrajectory)
from moveit_msgs.srv import ApplyPlanningScene, GetCartesianPath
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import Empty
from tf2_ros import Buffer, TransformListener
from trajectory_msgs.msg import JointTrajectoryPoint

GROUP = 'ur_manipulator'
TCP = 'gripper_tcp'
BASE = 'base_link'
ARM_JOINTS = ('shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint', 'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint')
FINGERS = ('left_finger_joint', 'right_finger_joint')
GRIPPER_OPEN, GRIPPER_CLOSED = 0.0, 0.034
DOWN = (0.0, 1.0, 0.0, 0.0)            # xyzw: tool z pointing down (rotation of pi about y)


def quat_down_yaw(yaw):
    """Orientation with the tool pointing down and the finger axis rotated by yaw about the vertical (xyzw)."""
    cz, sz = math.cos(yaw / 2), math.sin(yaw / 2)
    # q = Rz(yaw) * Ry(pi); Ry(pi) = (0,1,0,0) -> (x,y,z,w) of product
    x, y, z, w = 0.0, 1.0, 0.0, 0.0
    return (cz * x - sz * y, cz * y + sz * x, cz * z + sz * w, cz * w - sz * z)


def parse_gz_poses(text):
    """Parse `gz topic -e` text output of gz.msgs.Pose_V into {name: (x,y,z,qx,qy,qz,qw)}."""
    out = {}
    for block in re.findall(r'pose \{(.*?)\n\}', text, flags=re.S):
        name = re.search(r'name: "([^"]+)"', block)
        pos = re.search(r'position \{(.*?)\}', block, flags=re.S)
        ori = re.search(r'orientation \{(.*?)\}', block, flags=re.S)
        if not name or not pos:
            continue
        def val(s, k, default=0.0):
            m = re.search(k + r': ([-+0-9.eE]+)', s or '')
            return float(m.group(1)) if m else default
        out[name.group(1)] = (val(pos.group(1), 'x'), val(pos.group(1), 'y'), val(pos.group(1), 'z'),
                              val(ori.group(1), 'x'), val(ori.group(1), 'y'), val(ori.group(1), 'z'), val(ori.group(1), 'w', 1.0))
    return out


def yaw_of(q):
    x, y, z, w = q
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


class GroundTruth:
    """Object poses read from the Gazebo simulator (ground truth, via gz transport). Poses are in the robot base_link frame (the robot is at the world origin)."""
    def __init__(self, partition, world='objects_world'):
        self.partition, self.world = partition, world

    def all(self, timeout=15):
        env = {**os.environ, 'GZ_PARTITION': self.partition}
        result = subprocess.run(['gz', 'topic', '-e', '-t', '/world/%s/pose/info' % self.world, '-n', '1'], capture_output=True, text=True, timeout=timeout, env=env)
        poses = parse_gz_poses(result.stdout)
        if not poses:
            raise RuntimeError('ground_truth_unavailable')
        return poses

    def pose(self, name):
        poses = self.all()
        if name not in poses:
            raise KeyError(name)
        return poses[name]


class ObjectsArm:
    def __init__(self, partition, node_name='objects_arm', need_moveit=True):
        if not rclpy.ok():
            rclpy.init()
        self.node = Node(node_name + '_' + str(os.getpid()), parameter_overrides=[rclpy.parameter.Parameter('use_sim_time', rclpy.Parameter.Type.BOOL, True)])
        self.truth = GroundTruth(partition)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self.node)
        self.move_group = ActionClient(self.node, MoveGroup, '/move_action')
        self.arm_traj = ActionClient(self.node, FollowJointTrajectory, '/joint_trajectory_controller/follow_joint_trajectory')
        self.gripper_traj = ActionClient(self.node, FollowJointTrajectory, '/gripper_controller/follow_joint_trajectory')
        self.cartesian = self.node.create_client(GetCartesianPath, '/compute_cartesian_path')
        self.scene = self.node.create_client(ApplyPlanningScene, '/apply_planning_scene')
        self.attach_pub = self.node.create_publisher(Empty, '/objects/red_block/attach', 1)
        self.detach_pub = self.node.create_publisher(Empty, '/objects/red_block/detach', 1)
        self.joints = {}
        self.node.create_subscription(JointState, '/joint_states', self._on_joint, 10)
        for client, label in (((self.move_group, 'move_action'),) if need_moveit else ()) + ((self.arm_traj, 'arm trajectory'), (self.gripper_traj, 'gripper trajectory')):
            if not client.wait_for_server(timeout_sec=30):
                raise RuntimeError('action_server_unavailable:' + label)
        for client, label in (((self.cartesian, 'compute_cartesian_path'), (self.scene, 'apply_planning_scene')) if need_moveit else ()):
            if not client.wait_for_service(timeout_sec=30):
                raise RuntimeError('service_unavailable:' + label)

    def _on_joint(self, msg):
        for n, p in zip(msg.name, msg.position):
            self.joints[n] = p

    def spin_until(self, predicate, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.05)
            if predicate():
                return True
        return False

    def wait_future(self, future, timeout):
        return self.spin_until(future.done, timeout) and future.result() is not None

    # ------------------------------------------------------------ state
    def joint_state(self):
        self.spin_until(lambda: all(j in self.joints for j in ARM_JOINTS + FINGERS), 5)
        return dict(self.joints)

    def tcp_pose(self, timeout=5):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.05)
            try:
                t = self.tf_buffer.lookup_transform(BASE, TCP, rclpy.time.Time())
                p, q = t.transform.translation, t.transform.rotation
                return (p.x, p.y, p.z, q.x, q.y, q.z, q.w)
            except Exception:
                continue
        raise RuntimeError('tcp_transform_unavailable')

    # ------------------------------------------------------------ gripper
    def set_gripper(self, position, seconds=1.5, wait=3.0):
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = list(FINGERS)
        point = JointTrajectoryPoint(positions=[position, position], time_from_start=rclpy.duration.Duration(seconds=seconds).to_msg())
        goal.trajectory.points = [point]
        future = self.gripper_traj.send_goal_async(goal)
        if not self.wait_future(future, 5):
            return False
        result = future.result().get_result_async()
        self.wait_future(result, seconds + wait)
        time.sleep(0.3)
        got = self.joint_state()
        return all(abs(got[f] - position) < 0.012 for f in FINGERS) or position == GRIPPER_CLOSED

    def finger_positions(self):
        j = self.joint_state()
        return [j[f] for f in FINGERS]

    # ------------------------------------------------------------ planning scene
    def add_box(self, name, xyz, size, quat=(0.0, 0.0, 0.0, 1.0)):
        obj = CollisionObject()
        obj.header.frame_id = BASE
        obj.id = name
        prim = SolidPrimitive(type=SolidPrimitive.BOX, dimensions=list(size))
        pose = Pose()
        pose.position.x, pose.position.y, pose.position.z = xyz
        pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w = quat
        obj.primitives, obj.primitive_poses, obj.operation = [prim], [pose], CollisionObject.ADD
        scene = PlanningScene(is_diff=True)
        scene.world.collision_objects = [obj]
        request = ApplyPlanningScene.Request(scene=scene)
        return self.wait_future(self.scene.call_async(request), 10)

    def sync_scene(self, include_block=True):
        """Put the table, tray and (optionally) the block into the MoveIt planning scene from the simulator ground truth, so plans avoid them."""
        poses = self.truth.all()
        ok = self.add_box('table_top', (0.60, 0.0, -0.05), (0.90, 1.2, 0.1))
        tx, ty = poses['tray'][0], poses['tray'][1]
        fw, fd, fh, w, wh = 0.24, 0.18, 0.01, 0.012, 0.03
        parts = {'tray_floor': (tx, ty, fh / 2, fw, fd, fh), 'tray_n': (tx, ty + fd / 2 - w / 2, fh + wh / 2, fw, w, wh), 'tray_s': (tx, ty - fd / 2 + w / 2, fh + wh / 2, fw, w, wh),
                 'tray_e': (tx + fw / 2 - w / 2, ty, fh + wh / 2, w, fd, wh), 'tray_w': (tx - fw / 2 + w / 2, ty, fh + wh / 2, w, fd, wh)}
        for name, (x, y, z, sx, sy, sz) in parts.items():
            ok = self.add_box(name, (x, y, z), (sx, sy, sz)) and ok
        if include_block:
            b = poses['red_block']
            ok = self.add_box('red_block', (b[0], b[1], b[2]), (0.045, 0.045, 0.045), quat=b[3:]) and ok
        return ok

    def remove_object(self, name):
        obj = CollisionObject()
        obj.header.frame_id = BASE
        obj.id = name
        obj.operation = CollisionObject.REMOVE
        scene = PlanningScene(is_diff=True)
        scene.world.collision_objects = [obj]
        return self.wait_future(self.scene.call_async(ApplyPlanningScene.Request(scene=scene)), 10)

    # ------------------------------------------------------------ motion
    def move_to_pose(self, xyz, quat=DOWN, planning_time=5.0, velocity=0.3, tolerance=0.004):
        """MoveIt 2 pose goal for the gripper TCP (plan and execute). Returns (ok, detail)."""
        request = MotionPlanRequest()
        request.group_name = GROUP
        request.num_planning_attempts = 5
        request.allowed_planning_time = planning_time
        request.max_velocity_scaling_factor = velocity
        request.max_acceleration_scaling_factor = velocity
        request.pipeline_id = 'ompl'
        pc = PositionConstraint()
        pc.header.frame_id = BASE
        pc.link_name = TCP
        region = BoundingVolume()
        region.primitives = [SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[tolerance])]
        centre = Pose()
        centre.position.x, centre.position.y, centre.position.z = xyz
        centre.orientation.w = 1.0
        region.primitive_poses = [centre]
        pc.constraint_region, pc.weight = region, 1.0
        oc = OrientationConstraint()
        oc.header.frame_id = BASE
        oc.link_name = TCP
        oc.orientation.x, oc.orientation.y, oc.orientation.z, oc.orientation.w = quat
        oc.absolute_x_axis_tolerance = oc.absolute_y_axis_tolerance = oc.absolute_z_axis_tolerance = 0.03
        oc.weight = 1.0
        request.goal_constraints = [Constraints(position_constraints=[pc], orientation_constraints=[oc])]
        goal = MoveGroup.Goal(request=request, planning_options=PlanningOptions(plan_only=False))
        future = self.move_group.send_goal_async(goal)
        if not self.wait_future(future, 10):
            return False, 'move_group_goal_not_accepted'
        handle = future.result()
        if not handle.accepted:
            return False, 'move_group_goal_rejected'
        result_future = handle.get_result_async()
        if not self.wait_future(result_future, planning_time + 60):
            return False, 'move_group_timeout'
        code = result_future.result().result.error_code.val
        return code == MoveItErrorCodes.SUCCESS, 'error_code=%d' % code

    def move_straight(self, xyz_target, quat=DOWN, step=0.005, velocity=0.15):
        """Straight-line (Cartesian) move of the TCP to xyz_target, executed through the arm trajectory controller. Returns (ok, detail)."""
        request = GetCartesianPath.Request()
        request.group_name = GROUP
        request.link_name = TCP
        request.header.frame_id = BASE
        wp = Pose()
        wp.position.x, wp.position.y, wp.position.z = xyz_target
        wp.orientation.x, wp.orientation.y, wp.orientation.z, wp.orientation.w = quat
        request.waypoints = [wp]
        request.max_step = step
        request.jump_threshold = 0.0
        request.avoid_collisions = True
        request.max_velocity_scaling_factor = velocity
        request.max_acceleration_scaling_factor = velocity
        future = self.cartesian.call_async(request)
        if not self.wait_future(future, 15):
            return False, 'cartesian_service_timeout'
        reply = future.result()
        if reply.error_code.val != MoveItErrorCodes.SUCCESS or reply.fraction < 0.99:
            return False, 'cartesian_fraction=%.2f error_code=%d' % (reply.fraction, reply.error_code.val)
        goal = FollowJointTrajectory.Goal()
        goal.trajectory = reply.solution.joint_trajectory
        # time-parameterise simply: scale by path length for a gentle speed
        points = goal.trajectory.points
        if len(points) < 2:
            return False, 'cartesian_path_too_short'
        n = len(points)
        total = max(2.0, n * step / max(velocity * 0.2, 0.02))
        for i, pt in enumerate(points):
            pt.time_from_start = rclpy.duration.Duration(seconds=total * i / (n - 1)).to_msg()
            pt.velocities, pt.accelerations = [], []
        send = self.arm_traj.send_goal_async(goal)
        if not self.wait_future(send, 10) or not send.result().accepted:
            return False, 'arm_trajectory_rejected'
        res = send.result().get_result_async()
        if not self.wait_future(res, total + 15):
            return False, 'arm_trajectory_timeout'
        return res.result().status == GoalStatus.STATUS_SUCCEEDED, 'trajectory_status=%d' % res.result().status

    # ------------------------------------------------------------ grasp assist
    def attach_block(self):
        self.attach_pub.publish(Empty())
        rclpy.spin_once(self.node, timeout_sec=0.1)

    def detach_block(self):
        self.detach_pub.publish(Empty())
        rclpy.spin_once(self.node, timeout_sec=0.1)

    def close(self):
        try:
            self.node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()
