"""Milestone 1 check (no model): gripper open/close, MoveIt pose goal, ground-truth block pose. LABEL: simulated gripper with grasp assist; demonstration only."""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import objects_lib as ol

partition = Path(sys.argv[1]).read_text().strip()
arm = ol.ObjectsArm(partition)
out = {}
out['joints_start'] = {k: round(v, 3) for k, v in arm.joint_state().items()}
out['gripper_close'] = arm.set_gripper(ol.GRIPPER_CLOSED); out['fingers_closed'] = [round(x, 4) for x in arm.finger_positions()]
out['gripper_open'] = arm.set_gripper(ol.GRIPPER_OPEN); out['fingers_open'] = [round(x, 4) for x in arm.finger_positions()]
out['scene'] = arm.sync_scene()
out['tcp_before'] = [round(x, 3) for x in arm.tcp_pose()]
goal = (0.40, 0.0, 0.25)
ok, detail = arm.move_to_pose(goal, ol.DOWN)
out['move_ok'], out['move_detail'] = ok, detail
t = arm.tcp_pose()
out['tcp_after'] = [round(x, 4) for x in t]
out['tcp_error_m'] = round(((t[0] - goal[0]) ** 2 + (t[1] - goal[1]) ** 2 + (t[2] - goal[2]) ** 2) ** 0.5, 4)
poses = arm.truth.all()
out['truth_block'] = [round(x, 4) for x in poses['red_block']]
out['truth_tray'] = [round(x, 4) for x in poses['tray']]
print(json.dumps(out, indent=1))
arm.close()
