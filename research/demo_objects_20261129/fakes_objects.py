"""Test doubles for the objects tools: a small kinematic fake of ObjectsArm (no Gazebo, no MoveIt, no ROS graph). Zero model calls. Demonstration only."""
import math

import objects_lib as ol

BLOCK_HALF = 0.0225


class FakeTruth:
    def __init__(self, arm):
        self.arm = arm

    def all(self):
        return {'red_block': self.arm.block, 'tray': self.arm.tray, 'table': (0.55, 0, -0.35, 0, 0, 0, 1)}

    def pose(self, name):
        poses = self.all()
        if name not in poses:
            raise KeyError(name)
        return poses[name]


class FakeObjectsArm:
    def __init__(self, block=(0.45, 0.10, 0.0225), tray=(0.45, -0.28, 0.0), fail=None):
        self.block = (block[0], block[1], block[2], 0.0, 0.0, 0.0, 1.0)
        self.tray = (tray[0], tray[1], tray[2], 0.0, 0.0, 0.0, 1.0)
        self.tcp = (0.49, 0.13, 0.38)
        self.fingers = [0.0, 0.0]
        self.attached = False
        self.fail = fail or set()          # e.g. {'move_to_pose'}, {'close_no_block'}
        self.writes = 0
        self.moves = []
        self.truth = FakeTruth(self)

    # --- queries
    def tcp_pose(self, timeout=5):
        return (*self.tcp, 0.0, 1.0, 0.0, 0.0)

    def finger_positions(self):
        return list(self.fingers)

    def joint_state(self):
        return {n: v for n, v in zip(ol.ARM_JOINTS, (0.0, -1.57, 1.57, -1.57, -1.57, 0.0))} | {'left_finger_joint': self.fingers[0], 'right_finger_joint': self.fingers[1]}

    # --- actions
    def _carry(self):
        if self.attached:
            self.block = (self.tcp[0], self.tcp[1], self.tcp[2] - 0.02, *self.block[3:])

    def move_to_pose(self, xyz, quat=ol.DOWN, **kw):
        self.moves.append(('pose', tuple(xyz)))
        if 'move_to_pose' in self.fail:
            return False, 'error_code=-2'
        self.tcp = tuple(xyz); self._carry()
        return True, 'error_code=1'

    def move_straight(self, xyz, quat=ol.DOWN, **kw):
        self.moves.append(('straight', tuple(xyz)))
        if 'move_straight' in self.fail:
            return False, 'cartesian_fraction=0.40'
        self.tcp = tuple(xyz); self._carry()
        return True, 'trajectory_status=4'

    def set_gripper(self, position, seconds=1.5, wait=3.0):
        if position >= ol.GRIPPER_CLOSED - 1e-6:
            near = math.dist(self.tcp, (self.block[0], self.block[1], self.block[2] + 0.02)) < 0.03
            width = 0.020 if near and 'close_no_block' not in self.fail else 0.0336
            self.fingers = [width, width]
        else:
            self.fingers = [0.0, 0.0]
            if self.attached:
                self.attached = False
            self._settle()
        return True

    def attach_block(self):
        near = math.dist(self.tcp, (self.block[0], self.block[1], self.block[2] + 0.02)) < 0.05
        if near and 0.01 < self.fingers[0] < 0.03:
            self.attached = True

    def detach_block(self):
        if self.attached:
            self.attached = False
            self._settle()

    def _settle(self):
        x, y, z = self.block[:3]
        tx, ty = self.tray[0], self.tray[1]
        floor = 0.01 + BLOCK_HALF if abs(x - tx) < 0.12 and abs(y - ty) < 0.09 else BLOCK_HALF
        if z < floor + 0.08:
            self.block = (x, y, floor, *self.block[3:])

    def sync_scene(self, include_block=True):
        return True

    def remove_object(self, name):
        return True

    def spin_until(self, predicate, timeout):
        return True

    def close(self):
        pass
