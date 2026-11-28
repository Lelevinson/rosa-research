import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rclpy
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
import objects_lib as ol
arm = ol.ObjectsArm(Path(sys.argv[1]).read_text().strip(), need_moveit=False)
for pos in ([0.0, 0.03], [0.03, 0.0], [0.0, -0.01], [0.0, 0.0]):
    goal = FollowJointTrajectory.Goal(); goal.trajectory.joint_names = list(ol.FINGERS)
    goal.trajectory.points = [JointTrajectoryPoint(positions=pos, time_from_start=rclpy.duration.Duration(seconds=2).to_msg())]
    f = arm.gripper_traj.send_goal_async(goal); print('sent', arm.wait_future(f, 5), 'accepted', f.result().accepted)
    r = f.result().get_result_async(); print('done', arm.wait_future(r, 8), 'status', r.result().status, 'err', r.result().result.error_code, r.result().result.error_string)
    time.sleep(0.5); g = arm.truth.all(); print(pos, 'fingers', [round(x, 4) for x in arm.finger_positions()], 'gz LF', [round(x, 3) for x in g['left_finger'][:3]], 'RF', [round(x, 3) for x in g['right_finger'][:3]], flush=True)
arm.close()
