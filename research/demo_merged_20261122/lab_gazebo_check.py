"""Lab setup check (ZERO model calls): launch the UR5e Gazebo world headless, read home, move away, reset to home, close. Run INSIDE the lab container.
LABEL: merged-method demo, lab setup, demonstration only, not evaluated, not for the paper. Usage: python lab_gazebo_check.py <new output folder>"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.update(ROS_DOMAIN_ID=os.environ.get('ROS_DOMAIN_ID', '213'), ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST')
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rosa_reliability.gazebo_demo import GazeboDemo  # noqa: E402
from rosa_reliability.ros_arm import ArmTransport, HOME_POSE, JOINTS  # noqa: E402

TOL = 0.025


def procs():
    out = subprocess.run(['pgrep', '-af', 'gz sim|ros2_control_node|ros2 launch'], capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if 'pgrep' not in line]


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=False)
    record = {'domain': os.environ['ROS_DOMAIN_ID'], 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'before_processes': procs()}
    assert not record['before_processes'], 'another gz/ros2 process is running in this container'
    demo = GazeboDemo(out / 'gazebo')
    mover = observer = None
    try:
        t0 = time.monotonic()
        demo.start()
        record['launch_to_ready_s'] = round(time.monotonic() - t0, 1)
        mover, observer = ArmTransport(), ArmTransport(read_only=True)
        record['home_read'] = observer.read('/ur5e', list(JOINTS))
        away = {**HOME_POSE, 'shoulder_pan_joint': .16, 'wrist_3_joint': -.12}
        mover.read('/ur5e', list(JOINTS))
        mover.write('/ur5e', away)
        record['after_move'] = observer.read('/ur5e', list(JOINTS))
        record['moved_ok'] = all(abs(record['after_move'][k] - v) <= TOL for k, v in away.items())
        mover.write('/ur5e', HOME_POSE)
        record['after_reset'] = observer.read('/ur5e', list(JOINTS))
        record['reset_ok'] = all(abs(record['after_reset'][k] - v) <= TOL for k, v in HOME_POSE.items())
    finally:
        for item in (mover, observer):
            try:
                if item:
                    item.close()
            except Exception:
                pass
        record['gazebo_close'] = demo.close()
        time.sleep(3)
        record['after_close_processes'] = procs()
        (out / 'LAB_GAZEBO_CHECK.json').write_text(json.dumps(record, indent=1, default=str))
    print(json.dumps({k: record.get(k) for k in ('launch_to_ready_s', 'moved_ok', 'reset_ok', 'after_close_processes')}))


if __name__ == '__main__':
    main()
