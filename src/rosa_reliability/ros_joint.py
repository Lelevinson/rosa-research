"""Bounded ROS 2 transport for the single-joint Gazebo fixture.

The evaluator creates a separate read-only subscription; it never reads cached
agent observations or commanded target values as if they were actual positions.
"""
import math
import time
from uuid import uuid4


class JointTransport:
    requires_observation = True

    def __init__(self, *, read_only=False, suppress_commands=False):
        import rclpy
        from rclpy.node import Node
        from rclpy.executors import SingleThreadedExecutor
        from sensor_msgs.msg import JointState
        from std_msgs.msg import Float64
        from rclpy.qos import qos_profile_sensor_data
        self.rclpy, self.Float64 = rclpy, Float64
        self.context = rclpy.Context()
        rclpy.init(context=self.context)
        self.node = Node(('rosa_observer_' if read_only else 'rosa_skill_') + uuid4().hex[:8], context=self.context)
        self.executor = SingleThreadedExecutor(context=self.context)
        self.executor.add_node(self.node)
        self.publisher = None if read_only else self.node.create_publisher(Float64, '/rosa_arm/command', 10)
        self.subscription = self.node.create_subscription(JointState, '/rosa_arm/joint_states', self.on_state,
                                                         qos_profile_sensor_data)
        self.latest, self.sequence = None, 0
        self.suppress_commands = suppress_commands
        self.records = []

    def on_state(self, message):
        for index, name in enumerate(message.name):
            if name.split('::')[-1] == 'shoulder' and index < len(message.position):
                position = message.position[index]
                if math.isfinite(position):
                    self.sequence += 1
                    self.latest = {'position': position, 'sequence': self.sequence,
                                   'sim_stamp': [message.header.stamp.sec, message.header.stamp.nanosec],
                                   'received_monotonic': time.monotonic()}

    def read(self, node, names):
        if node != '/rosa_arm' or names != ['shoulder']:
            raise ValueError('invalid_joint_scope')
        # Drain queued history, then require a newer simulator timestamp.
        for _ in range(20):
            self.executor.spin_once(timeout_sec=0)
        stamp = self.latest['sim_stamp'] if self.latest else None
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            self.executor.spin_once(timeout_sec=0.05)
            if self.latest and self.latest['sim_stamp'] != stamp:
                self.records.append({'kind': 'observation', **self.latest})
                return {'shoulder': self.latest['position']}
        raise TimeoutError('no_fresh_joint_state_within_5_seconds')

    def validate_write(self, node, values):
        if node != '/rosa_arm' or set(values) != {'shoulder'}:
            return 'one shoulder value on /rosa_arm required'
        angle = values['shoulder']
        if type(angle) not in (int, float) or not math.isfinite(angle) or not -0.6 <= angle <= 0.6:
            return 'shoulder must be a finite number within [-0.6, 0.6] radians'
        return None

    def write(self, node, values):
        error = self.validate_write(node, values)
        if error or self.publisher is None:
            raise ValueError(error or 'read_only_observer')
        deadline = time.monotonic() + 5
        while self.publisher.get_subscription_count() < 1:
            if time.monotonic() > deadline:
                raise TimeoutError('command_bridge_unavailable')
            self.executor.spin_once(timeout_sec=0.05)
        if not self.suppress_commands:
            self.publisher.publish(self.Float64(data=float(values['shoulder'])))
        self.records.append({'kind': 'command', 'requested': values['shoulder'],
                             'published': not self.suppress_commands, 'at': time.monotonic()})
        # A fixed bounded controller settling allowance, not an outcome check.
        until = time.monotonic() + 1.5
        while time.monotonic() < until:
            self.executor.spin_once(timeout_sec=0.05)
        return {'accepted': True, 'meaning': 'command request accepted; outcome requires observation'}

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        self.context.shutdown()
