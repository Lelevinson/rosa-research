"""Bounded pick / place macros for the objects demo (no model in this file). NEW FILE; frozen demo files are not modified.
LABEL: object poses read from the simulator (ground truth); simulated gripper with grasp assist; demonstration only, not evaluated, not for the paper.

Contract of both macros (same spirit as the bounded macro): a FIXED sequence, every step verified, REFUSAL on a failed precondition (nothing moved), NO silent retries
(on any failure the macro stops, opens the gripper and detaches the grasp assist if it had attached, and reports the failing step with evidence).
Planning: MoveIt 2 (OMPL pose goals for free moves, Cartesian paths for the straight approach / lift / lower / retreat), table, tray and block in the planning scene.
Grasp assist (disclosed): when the gripper has closed on the block (fingers stopped by contact between the open and closed positions, block between the fingers),
the block is attached to the wrist link with Gazebo's DetachableJoint, and detached when the gripper opens at the target."""
import math
import subprocess
import time

import objects_lib as ol

BLOCK_SIZE = 0.045
BLOCK_HALF = BLOCK_SIZE / 2
TCP_TO_BLOCK_GRASP = 0.02          # grasp with the TCP this far above the block centre (fingertips stay above the table)
PRE_GRASP_Z = 0.17                 # TCP height of the pre-grasp / carry pose above the table
CARRY_Z = 0.20
TRAY_FLOOR_TOP = 0.01
REACH_X = (0.28, 0.72)             # reachable table region (base_link frame, metres)
REACH_Y = (-0.42, 0.42)
TRAY_HALF = (0.10, 0.07)           # block must come to rest inside these tray half-extents


def result(ok, step, detail, **evidence):
    return {'ok': ok, 'step': step, 'detail': detail, 'evidence': evidence}


def yaw_for_grasp(block_yaw):
    """Finger axis (tool y) perpendicular to the block faces: tool yaw = block yaw reduced to [-45, +45] degrees."""
    y = (block_yaw + math.pi / 4) % (math.pi / 2) - math.pi / 4
    return y


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a[:3], b[:3])))


class Skills:
    def __init__(self, arm):
        self.arm = arm
        self.held = False
        self.grasp_yaw = 0.0

    # ---------------------------------------------------------------- helpers
    def block_pose(self):
        return self.arm.truth.pose('red_block')

    def is_held(self):
        """Ground truth: block clearly above the table and within a hand's width of the TCP."""
        b, t = self.block_pose(), self.arm.tcp_pose()
        return b[2] > 0.06 and dist(b, t) < 0.05

    def fail_safe(self, step, detail, **evidence):
        """Stop, open the gripper, detach the assist, report. No retry."""
        self.arm.detach_block()
        self.arm.set_gripper(ol.GRIPPER_OPEN)
        self.held = False
        try:
            evidence['block'] = [round(x, 4) for x in self.block_pose()[:3]]
        except Exception:
            pass
        return result(False, step, detail, **evidence)

    # ---------------------------------------------------------------- pick
    def pick(self, name='red_block'):
        arm = self.arm
        if name != 'red_block':
            return result(False, 'precondition', 'unknown object %s (only red_block exists)' % name)
        try:
            b = self.block_pose()
        except Exception as error:
            return result(False, 'read_pose', 'ground truth unavailable: %s' % error)
        evidence = {'block_before': [round(x, 4) for x in b[:3]]}
        if self.is_held():
            return result(False, 'precondition', 'the block is already held', **evidence)
        if b[2] > 0.06 and not (b[2] < TRAY_FLOOR_TOP + BLOCK_HALF + 0.02):
            return result(False, 'precondition', 'the block is not resting on a surface (z=%.3f)' % b[2], **evidence)
        if not (REACH_X[0] <= b[0] <= REACH_X[1] and REACH_Y[0] <= b[1] <= REACH_Y[1]):
            return result(False, 'precondition', 'the block is outside the reachable region (x %.2f, y %.2f)' % (b[0], b[1]), **evidence)
        tilt = abs(b[3]) + abs(b[4])
        if tilt > 0.15:
            return result(False, 'precondition', 'the block is tilted (not resting flat)', **evidence)
        yaw = yaw_for_grasp(ol.yaw_of(b[3:]))
        quat = ol.quat_down_yaw(yaw)
        self.grasp_yaw = yaw
        arm.detach_block()
        if not arm.set_gripper(ol.GRIPPER_OPEN):
            return self.fail_safe('open_gripper', 'gripper did not open', **evidence)
        arm.sync_scene(include_block=True)
        x, y = b[0], b[1]
        ok, d = arm.move_to_pose((x, y, PRE_GRASP_Z), quat)
        if not ok:
            return self.fail_safe('plan_pre_grasp', 'MoveIt could not reach the pre-grasp pose (%s)' % d, **evidence)
        grasp_z = b[2] + TCP_TO_BLOCK_GRASP
        ok, d = arm.move_straight((x, y, grasp_z), quat)
        if not ok:
            return self.fail_safe('descend', 'straight descent failed (%s)' % d, **evidence)
        tcp = arm.tcp_pose()
        if dist(tcp, b) > 0.06:
            return self.fail_safe('align', 'gripper is not centred over the block (%.3f m)' % dist(tcp, b), **evidence)
        arm.set_gripper(ol.GRIPPER_CLOSED, seconds=2.0)
        fingers = arm.finger_positions()
        evidence['fingers_after_close'] = [round(f, 4) for f in fingers]
        if not all(0.010 < f < 0.030 for f in fingers):
            return self.fail_safe('close', 'fingers did not stop on the block (positions %s)' % evidence['fingers_after_close'], **evidence)
        arm.attach_block()
        time.sleep(0.4)
        arm.remove_object('red_block')                       # carried block is no longer a scene obstacle
        ok, d = arm.move_straight((x, y, CARRY_Z), quat)
        if not ok:
            return self.fail_safe('lift', 'straight lift failed (%s)' % d, **evidence)
        time.sleep(0.5)
        b2, t2 = self.block_pose(), arm.tcp_pose()
        evidence['block_after_lift'] = [round(v, 4) for v in b2[:3]]
        if not (b2[2] > b[2] + 0.10 and dist(b2, t2) < 0.06):
            return self.fail_safe('verify', 'the block did not move up with the gripper', **evidence)
        self.held = True
        return result(True, 'done', 'picked up the red block (lifted %.3f m with the gripper)' % (b2[2] - b[2]), **evidence)

    # ---------------------------------------------------------------- place
    def place(self, name='red_block', target='tray'):
        arm = self.arm
        if name != 'red_block':
            return result(False, 'precondition', 'unknown object %s (only red_block exists)' % name)
        if target != 'tray':
            return result(False, 'precondition', 'unknown target %s (only the tray exists)' % target)
        try:
            b = self.block_pose()
            tray = arm.truth.pose('tray')
        except Exception as error:
            return result(False, 'read_pose', 'ground truth unavailable: %s' % error)
        evidence = {'block_before': [round(x, 4) for x in b[:3]], 'tray': [round(x, 4) for x in tray[:3]]}
        if not self.is_held():
            return result(False, 'precondition', 'the gripper is not holding the block', **evidence)
        tx, ty = tray[0], tray[1]
        if not (REACH_X[0] <= tx <= REACH_X[1] and REACH_Y[0] <= ty <= REACH_Y[1]):
            return self.fail_safe('precondition', 'the tray is outside the reachable region', **evidence)
        quat = ol.quat_down_yaw(self.grasp_yaw)
        arm.sync_scene(include_block=False)
        ok, d = arm.move_to_pose((tx, ty, CARRY_Z), quat)
        if not ok:
            return self.fail_safe('plan_above_target', 'MoveIt could not reach the pose above the tray (%s)' % d, **evidence)
        rest_z = TRAY_FLOOR_TOP + BLOCK_HALF
        ok, d = arm.move_straight((tx, ty, rest_z + TCP_TO_BLOCK_GRASP + 0.003), quat)
        if not ok:
            return self.fail_safe('lower', 'straight lowering failed (%s)' % d, **evidence)
        arm.detach_block()
        arm.set_gripper(ol.GRIPPER_OPEN, seconds=1.5)
        self.held = False
        ok, d = arm.move_straight((tx, ty, CARRY_Z), quat)
        if not ok:
            return self.fail_safe('retreat', 'straight retreat failed (%s)' % d, **evidence)
        time.sleep(0.8)
        b2 = self.block_pose()
        evidence['block_after'] = [round(v, 4) for v in b2[:3]]
        inside = abs(b2[0] - tx) < TRAY_HALF[0] and abs(b2[1] - ty) < TRAY_HALF[1]
        resting = abs(b2[2] - rest_z) < 0.012 and abs(b2[3]) + abs(b2[4]) < 0.15
        if not (inside and resting):
            return result(False, 'verify', 'the block is not resting in the tray (inside=%s, resting=%s)' % (inside, resting), **evidence)
        return result(True, 'done', 'the red block rests on the tray', **evidence)

    # ---------------------------------------------------------------- queries
    def where(self, name='red_block'):
        if name not in ('red_block', 'tray'):
            return result(False, 'precondition', 'unknown object %s' % name)
        p = self.arm.truth.pose(name)
        extra = {}
        if name == 'red_block':
            held, on_tray = self.is_held(), self.block_on_tray()
            extra = {'held_by_gripper': held, 'resting_on': 'gripper' if held else 'tray' if on_tray else 'table'}
        return result(True, 'done', '%s pose in the robot base frame (ground truth from the simulator)' % name, position=[round(v, 4) for v in p[:3]],
                      yaw_deg=round(math.degrees(ol.yaw_of(p[3:])), 1), **extra)

    def block_on_tray(self):
        b, tray = self.block_pose(), self.arm.truth.pose('tray')
        return abs(b[0] - tray[0]) < TRAY_HALF[0] and abs(b[1] - tray[1]) < TRAY_HALF[1] and b[2] < TRAY_FLOOR_TOP + BLOCK_HALF + 0.012


# ---------------------------------------------------------------- world reset (test and demo helper, outside the agent)
def gz_set_pose(partition, name, xyz, yaw=0.0, world='objects_world'):
    import os
    env = {**os.environ, 'GZ_PARTITION': partition}
    qz, qw = math.sin(yaw / 2), math.cos(yaw / 2)
    req = 'name: "%s", position: {x: %f, y: %f, z: %f}, orientation: {x: 0, y: 0, z: %f, w: %f}' % (name, xyz[0], xyz[1], xyz[2], qz, qw)
    out = subprocess.run(['gz', 'service', '-s', '/world/%s/set_pose' % world, '--reqtype', 'gz.msgs.Pose', '--reptype', 'gz.msgs.Boolean', '--timeout', '3000', '--req', req],
                         capture_output=True, text=True, env=env, timeout=20)
    return 'true' in out.stdout


HOME_JOINTS = (0.0, -1.57, 1.57, -1.57, -1.57, 0.0)


def reset_world(arm, block_xy_yaw, partition):
    """Outside the agent: detach, open the gripper, arm to home, block back to its start pose, planning scene refreshed. Returns (ok, evidence)."""
    import rclpy
    from control_msgs.action import FollowJointTrajectory
    from trajectory_msgs.msg import JointTrajectoryPoint
    arm.detach_block()
    time.sleep(0.2)
    arm.set_gripper(ol.GRIPPER_OPEN)
    goal = FollowJointTrajectory.Goal()
    goal.trajectory.joint_names = list(ol.ARM_JOINTS)
    goal.trajectory.points = [JointTrajectoryPoint(positions=list(HOME_JOINTS), time_from_start=rclpy.duration.Duration(seconds=6).to_msg())]
    f = arm.arm_traj.send_goal_async(goal)
    arm.wait_future(f, 5)
    r = f.result().get_result_async()
    arm.wait_future(r, 15)
    x, y, yaw = block_xy_yaw
    moved = gz_set_pose(partition, 'red_block', (x, y, BLOCK_HALF + 0.001), yaw)
    time.sleep(1.2)
    arm.remove_object('red_block')
    j = arm.joint_state()
    home_ok = all(abs(j[n] - v) < 0.03 for n, v in zip(ol.ARM_JOINTS, HOME_JOINTS))
    b = arm.truth.pose('red_block')
    block_ok = abs(b[0] - x) < 0.01 and abs(b[1] - y) < 0.01 and b[2] < 0.04
    return (moved and home_ok and block_ok), {'set_pose': moved, 'home_ok': home_ok, 'block': [round(v, 4) for v in b[:3]]}
