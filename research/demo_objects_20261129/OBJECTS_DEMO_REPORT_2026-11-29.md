# Objects demo report (2026-11-29)

**Labels:** object poses read from the simulator (ground truth); simulated gripper with grasp assist; demonstration only, not evaluated, not for the paper. Merged method (Levinson M + Martin bounded macro) plus object tools; Sol only; laptop only.
Branch `member/martin-objects` (rosa-research), folder `research/demo_objects_20261129/`. The frozen demo (`research/demo_merged_20261122/`) is unchanged: `git diff` against `member/martin-merge` is empty and its 65 scripted tests pass.

## What works
- **Interactive terminal demo (M0):** `interactive_demo.py`. Type a request, tool calls print live, then the answer and the independent final state. Rehearsal 9/9 (3 arm-demo-style prompts x 3).
- **Simulation (M1, M2):** UR5e plus a simple two-finger gripper (own xacro, not Robotiq: no mimic joints), table, red block (4.5 cm) and tray at configurable positions, controllers active, MoveIt 2 planning and execution (pose goal reached within 4 mm), table/tray/block in the planning scene, object poses read from Gazebo in the robot base frame.
- **Scripted pick and place, no model (M3):** 9/9 = 3 block positions x 3 repetitions, clean world reset before every run, each verified from ground truth.
- **Agent with object tools (M4):** `get_object_pose`, `pick`, `place` added to the merged agent in study-local files (his menu, his final_answer and the arm macro unchanged). 21 fake-model tests pass.
- **Live with Sol, 3 takes each (prompt v2, `rehearsals/m4_takes_02`):**

| Prompt | Result |
|---|---|
| "Where is the red block?" | 3/3 |
| "Pick up the red block." | 3/3 |
| "Put the red block on the tray." | 3/3 |
| "Put the red block on the tray." (already there) | 3/3, all reported "already satisfied", no movement |
| "Make me a cup of coffee." (out of scope) | 3/3 refused, no movement |

  Scoring is a script that reads the independent final state and the ground truth (`score_m4.py`); the answers are kept for a human check.
- **Visual backup (M5):** `DEMO_BACKUP_objects_take1_visual.mp4` (49 s): zoomed Gazebo view (arm, gripper, block, tray) next to the real tool-call log. The raw desktop recording is not kept.
- **One command:** `run_objects_demo.sh show_01` (see `DEMO_RUNBOOK_INTERACTIVE.md`, objects section).

## Things that went wrong and were fixed (all on record in `STATUS.md`)
- The Gazebo DetachableJoint plugin attaches at load, so the block was carried by the arm from the start. Fix: one detach after start; attach only on command.
- A finger joint limit at exactly 0 left the right finger stuck. Limits are now -0.01..0.035.
- ROS domain ids above 232 are invalid, 231 is used.
- Prompt v1 gave put-again 0/3 (Sol picked the block off the tray and put it back). v2 adds the resting state to `get_object_pose` and one rule sentence (read first; if already satisfied, say so). v1 results stay in `m4_takes_01`. This was an iteration after seeing results, so the 15/15 is a demonstration rehearsal, not a clean pre-registered test.

## Limits
One block, one tray, reachable region only. Physics is a laptop simulation; the grasp assist (not friction) holds the block. Ground-truth poses, no camera. Sol only. Hand-picked prompts, 3 takes each. No claim beyond "it works in this setup".

## Not done / open
- Sol sign-in must be valid on the day (it expired once during the weekend; sign in again before the show).
- No Robotiq gripper; no camera-based perception; no other models.
