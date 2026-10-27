"""Headless UR5e demonstration lifecycle, independent of experiment runners.

Uses installed ROS packages unchanged. Joint outcomes do not certify path safety.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time

from .ros_arm import ArmTransport, HOME_POSE, JOINTS

INSTALLED_DESCRIPTION = Path('/opt/ros/jazzy/share/ur_simulation_gz/urdf/ur_gz.urdf.xacro')
MARKER = 'transmission_hw_interface="$(arg transmission_hw_interface)"'


def home_description(original):
    if original.count(MARKER) != 1:
        raise RuntimeError('unsupported_installed_urdf_template')
    expression = '${dict(' + ','.join(k + '=' + repr(v) for k, v in HOME_POSE.items()) + ')}'
    return original.replace(MARKER, MARKER + '\n    initial_positions="' + expression + '"')


def require_home(observed, tolerance=0.025):
    if set(observed) != set(HOME_POSE) or any(
            type(observed[k]) not in (int, float) or not math.isfinite(observed[k]) or
            abs(observed[k] - v) > tolerance for k, v in HOME_POSE.items()):
        raise RuntimeError('spawned_initial_state_is_not_documented_home')


class GazeboDemo:
    """Own only the process group launched here; caller must always close()."""

    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.folder.mkdir(parents=True, exist_ok=False)
        self.child = self.log = None

    def start(self):
        if self.child is not None:
            raise RuntimeError('simulator_already_started')
        original = INSTALLED_DESCRIPTION.read_text()
        generated = home_description(original)
        description = self.folder / 'ur_gz_home.urdf.xacro'
        description.write_text(generated)
        (self.folder / 'description-change.json').write_text(json.dumps({
            'installed_path': str(INSTALLED_DESCRIPTION),
            'original_sha256': hashlib.sha256(original.encode()).hexdigest(),
            'generated_sha256': hashlib.sha256(generated.encode()).hexdigest(),
            'only_change': 'explicit_initial_positions_attribute'}, indent=2))
        environment = {**os.environ, 'GZ_PARTITION': 'rosa-macro-module-v1-' + str(os.getpid())}
        self.log = (self.folder / 'launch.log').open('w')
        self.child = subprocess.Popen(['ros2', 'launch', 'ur_simulation_gz', 'ur_sim_control.launch.py',
            'ur_type:=ur5e', 'launch_rviz:=false', 'gazebo_gui:=false',
            'initial_joint_controller:=joint_trajectory_controller', 'description_file:=' + str(description)],
            env=environment, stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)
        from controller_manager_msgs.srv import ListControllers
        probe, queries = ArmTransport(read_only=True), []
        try:
            client = probe.node.create_client(ListControllers, '/controller_manager/list_controllers')
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if self.child.poll() is not None:
                    raise RuntimeError('simulator_exited_before_readiness')
                if not client.wait_for_service(timeout_sec=2):
                    continue
                future = client.call_async(ListControllers.Request())
                while not future.done() and time.monotonic() < deadline:
                    probe.executor.spin_once(timeout_sec=0.05)
                if future.done() and future.result():
                    states = {c.name: c.state for c in future.result().controller}
                    queries.append({'at': time.monotonic(), 'states': states})
                    if states.get('joint_state_broadcaster') == 'active' and states.get('joint_trajectory_controller') == 'active':
                        observed = probe.read('/ur5e', list(JOINTS))
                        require_home(observed)
                        (self.folder / 'readiness.json').write_text(json.dumps({
                            'pass': True, 'queries': queries, 'observed_values': observed,
                            'sensor_record': probe.records[-1]}, indent=2))
                        return
                time.sleep(0.05)
            raise RuntimeError('active_controllers_not_ready_within_120_seconds')
        finally:
            probe.close()

    def close(self):
        if self.child and self.child.poll() is None:
            os.killpg(self.child.pid, signal.SIGINT)
            try:
                self.child.wait(20)
            except subprocess.TimeoutExpired:
                os.killpg(self.child.pid, signal.SIGKILL)
                self.child.wait(5)
        if self.log:
            self.log.close()
        return {'pid': self.child.pid if self.child else None,
                'returncode': self.child.returncode if self.child else None}
