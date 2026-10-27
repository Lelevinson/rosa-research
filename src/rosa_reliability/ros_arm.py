"""Bounded six-axis UR5e ROS 2 trajectory skill, never an arbitrary controller."""
import math
import time
from uuid import uuid4

JOINTS = ('shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
          'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint')
HOME_POSE = dict(zip(JOINTS, (0., -1.57, 1.57, -1.57, -1.57, 0.)))


class ArmTransport:
    requires_observation = True
    def __init__(self, *, read_only=False):
        import rclpy
        from rclpy.node import Node
        from rclpy.executors import SingleThreadedExecutor
        from sensor_msgs.msg import JointState
        from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
        from rclpy.qos import qos_profile_sensor_data
        self.context = rclpy.Context()
        rclpy.init(context=self.context)
        self.node = Node(('rosa_arm_observer_' if read_only else 'rosa_arm_skill_') + uuid4().hex[:8], context=self.context)
        self.executor = SingleThreadedExecutor(context=self.context)
        self.executor.add_node(self.node)
        self.subscription = self.node.create_subscription(JointState, '/joint_states', self.on_state, qos_profile_sensor_data)
        self.publisher = None if read_only else self.node.create_publisher(JointTrajectory,
            '/joint_trajectory_controller/joint_trajectory', 10)
        self.JointTrajectory, self.JointTrajectoryPoint = JointTrajectory, JointTrajectoryPoint
        self.latest = None
        self.records = []
        self.suppress_commands = self.partial_commands = self.missing_observations = False

    def on_state(self, message):
        values = dict(zip(message.name, message.position))
        if set(JOINTS) <= set(values) and all(math.isfinite(values[n]) for n in JOINTS):
            self.latest = {'values': {n: values[n] for n in JOINTS},
                'sim_stamp': [message.header.stamp.sec, message.header.stamp.nanosec],
                'received_monotonic': time.monotonic()}

    def read(self, node, names):
        if node != '/ur5e' or set(names) != set(JOINTS):
            raise ValueError('ur5e_full_joint_scope_required')
        if self.missing_observations:
            self.records.append({'kind': 'observation_timeout', 'injected': True})
            raise TimeoutError('injected_arm_observation_unavailable')
        for _ in range(30):
            self.executor.spin_once(timeout_sec=0)
        stamp = self.latest['sim_stamp'] if self.latest else None
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            self.executor.spin_once(timeout_sec=.05)
            if self.latest and self.latest['sim_stamp'] != stamp:
                self.records.append({'kind': 'observation', **self.latest})
                return dict(self.latest['values'])
        raise TimeoutError('fresh_ur5e_joint_state_timeout')

    def validate_write(self, node, values):
        if self.publisher is None:
            return 'read-only observer cannot command'
        if node != '/ur5e' or set(values) != set(JOINTS):
            return 'all six named UR5e joints are required'
        if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v-HOME_POSE[n]) > .4 for n,v in values.items()):
            return 'joint targets must remain within 0.4 radians of the documented home pose'

    def write(self, node, values):
        error = self.validate_write(node, values)
        if error:
            raise ValueError(error)
        deadline = time.monotonic() + 8
        while self.publisher.get_subscription_count() < 1:
            if time.monotonic() > deadline:
                raise TimeoutError('trajectory_controller_unavailable')
            self.executor.spin_once(timeout_sec=.05)
        commanded = dict(values)
        if self.partial_commands:
            commanded['wrist_3_joint'] = HOME_POSE['wrist_3_joint']
        message = self.JointTrajectory()
        message.joint_names = list(JOINTS)
        point = self.JointTrajectoryPoint()
        point.positions = [float(commanded[n]) for n in JOINTS]
        point.velocities = [0.] * 6
        point.time_from_start.sec = 3
        message.points = [point]
        if not self.suppress_commands:
            self.publisher.publish(message)
        self.records.append({'kind': 'trajectory_request', 'requested': dict(values), 'published_targets': commanded,
            'published': not self.suppress_commands, 'injected_partial': self.partial_commands,
            'at': time.monotonic(), 'duration_seconds': 3})
        until = time.monotonic() + 4
        while time.monotonic() < until:
            self.executor.spin_once(timeout_sec=.05)
        return {'request_accepted_locally': True, 'meaning': 'trajectory publication requested; no claim of controller or physical success'}

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        self.context.shutdown()
