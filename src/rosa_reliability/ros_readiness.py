"""Read-only ROS 2 readiness acquisition: no controller or trajectory writes."""
from copy import deepcopy
import time

from .ros_arm import ArmTransport, JOINTS


class ArmReadinessTransport:
    """Two bounded source acquisitions, metered separately by the macro.

    Controller activation and a fresh finite joint sample do not establish
    collision safety or guarantee that a later movement will succeed.
    """

    def __init__(self):
        from controller_manager_msgs.srv import ListControllers
        self.observer = ArmTransport(read_only=True)
        self.client = self.observer.node.create_client(ListControllers, '/controller_manager/list_controllers')
        self.records = []

    def read_group(self, source, names):
        if source == 'controllers':
            allowed = {'trajectory_controller_active', 'joint_state_broadcaster_active'}
            if set(names) != allowed: raise ValueError('exact_authorized_controller_checks_required')
            if not self.client.wait_for_service(timeout_sec=2):
                raise TimeoutError('controller_readiness_service_unavailable')
            from controller_manager_msgs.srv import ListControllers
            future = self.client.call_async(ListControllers.Request())
            deadline = time.monotonic() + 6
            while not future.done() and time.monotonic() < deadline:
                self.observer.executor.spin_once(timeout_sec=0.05)
            if not future.done() or future.result() is None:
                raise TimeoutError('controller_readiness_response_timeout')
            states = {c.name: c.state for c in future.result().controller}
            result = {'trajectory_controller_active': states.get('joint_trajectory_controller') == 'active',
                      'joint_state_broadcaster_active': states.get('joint_state_broadcaster') == 'active'}
            self.records.append({'source': source, 'controller_states': states, 'observed': result,
                                 'received_monotonic': time.monotonic()})
            return result
        if source == 'joint_state':
            if names != ['joint_sample_fresh']: raise ValueError('exact_authorized_joint_check_required')
            values = self.observer.read('/ur5e', list(JOINTS))
            self.records.append({'source': source, 'joint_values': values,
                'sensor_record': deepcopy(self.observer.records[-1]), 'observed': {'joint_sample_fresh': True}})
            return {'joint_sample_fresh': True}
        raise ValueError('unauthorized_readiness_source')

    def close(self):
        self.observer.close()
