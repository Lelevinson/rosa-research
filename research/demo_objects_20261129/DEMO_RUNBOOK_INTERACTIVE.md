# Interactive demo runbook (Milestone 0), Sol only, laptop

**Always show this label:** merged method (Levinson M + Martin bounded macro), Sol, demonstration only, not evaluated. Credit: method M components (Levinson); bounded macro `run_skill` (Martin).
This file is NEW and separate: the frozen `research/demo_merged_20261122/DEMO_RUNBOOK.md` is not modified (it remains the fallback arm-demo runbook).

## Before the audience (5 min)
1. Laptop on power; close heavy programs (Gazebo + Sol use a lot of memory; WSL has about 7 GB).
2. Nothing else on Gazebo: in WSL `ps -eo cmd | grep -E "gz sim|ros2_control_node" | grep -v grep` must print nothing (else `pkill -INT -f "ros2 launch ur_simulation_gz"; pkill -f "gz sim"; pkill -f ros2_control_node`).
3. Sol sign-in must still work (it expires). If a run says `invalid_grant`, sign in again BEFORE the show; never on stage.
4. His files at `C:\Proj\robotics\introtorobotics\his-M-e233cf5\` (the script verifies all 26 hashes before use).

## Start (Windows terminal, Git Bash, large font)
```
MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -- bash -c 'cd /mnt/c/Proj/robotics/introtorobotics/wt-objects/research/demo_objects_20261129 && source /opt/ros/jazzy/setup.bash && /home/martin/.local/share/rosa-envs/research/bin/python -B interactive_demo.py rehearsals/show_01'
```
Use a NEW folder name every time (`show_02`, ...). It starts the simulator (about 30 s), opens the Sol session, resets the arm to home, then shows `request>`.

## At the prompt
- Type one request and press Enter. The tool calls print live (`model asks`, `>> tool`, `<< result`, `[macro] ...`), then `ANSWER`, the independent final state and the counts.
- `reset` puts the arm back to home. `quit` (or Ctrl+D) closes the simulator.
- The arm is reset to home before each request (so every request starts the same). Use `--keep-state` to turn that off.
- Prompts that worked in the rehearsal (frozen arm demo style):
  1. `Which node publishes /joint_states, and what are the current shoulder_pan_joint and wrist_3_joint positions? Answer as a JSON object.` (his method: menu tools)
  2. `Check that the arm is ready to move. If it is ready, move it to park_right. Report readiness and the final shoulder_pan_joint position as a JSON object.` (macro: inspection, then movement)
  3. `Move the arm to stage_left, then confirm with a fresh joint sample. Report the final wrist_3_joint position as a JSON object.` (macro movement, verified)

## Rehearsal without typing (what was run)
`bash run_interactive_tmux.sh <name> rehearsal0_requests.txt` runs the 9 requests in a detached WSL tmux session with the log in `rehearsals/<name>.log` (survives a VS Code restart).

## If it stalls
Ctrl+C, then `pkill -INT -f "ros2 launch ur_simulation_gz"; pkill -f "gz sim"; pkill -f ros2_control_node` in WSL. Fall back to the recorded backup video (`demo_merged_20261122/DEMO_BACKUP_take8_visual.mp4`) and say it is a recording.

---

# Objects demo (pick and place) - Sol, laptop

**Always show this label:** object poses read from the simulator (ground truth); simulated gripper with grasp assist; demonstration only, not evaluated. Merged method (Levinson M + Martin bounded macro) plus object tools. The existing arm demo above stays the fallback.
**Say plainly:** the arm sees objects through the simulator (it is told where the block is, it does not use a camera). The gripper is a simple simulated two-finger gripper; when it has closed on the block the simulator attaches the block to the gripper ("grasp assist") and detaches it when the gripper opens. Motion planning is MoveIt 2.

## Start (one command, Windows terminal, Git Bash, large font)
```
MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -- bash -c 'cd /mnt/c/Proj/robotics/introtorobotics/wt-objects/research/demo_objects_20261129 && ./run_objects_demo.sh show_01'
```
Use a NEW name each time (`show_02`, ...). It starts the simulation and MoveIt (about 60 s), opens the Sol session, sets the world to its start pose (arm home, gripper open, red block at x 0.45 y 0.10, tray at x 0.45 y -0.28), then shows `request>`. At the end (`quit`) it stops the simulation. Before starting: nothing else on Gazebo (`./cleanup_tmux.sh` in WSL cleans our own leftovers); Sol sign-in must work (sign in again BEFORE the show if it says `invalid_grant`).
Optional 3D view (viewer only): in a second WSL terminal `./watch_gui_objects.sh runs/show_01/gz_partition.txt` right after starting; the window opens after about 25 s with the camera on the table.

## Prompts that were rehearsed live with Sol (3 takes each, all passed in the v2 prompt, `STATUS.md`)
1. `Where is the red block?` reads the pose (ground truth) and answers.
2. `Pick up the red block.` pick routine (read pose, move above, descend, close, grasp assist, lift, verify it moved up with the gripper).
3. `Put the red block on the tray.` pick then place (lower, open and detach, retreat, verify it rests in the tray).
4. `Put the red block on the tray.` again, when it is already there: it says it is already satisfied and does not move.
5. `Make me a cup of coffee.` out of scope: it refuses and does not move.
At the prompt: `reset` puts the arm home, opens the gripper and puts the block back; `quit` ends. The world is NOT reset between requests, so you can pick and place as separate requests.

## What you will see
Every tool call prints live (`model asks`, `>> tool`, `[object] pick -> OK`, `<< result`), then `ANSWER`, the independent final state (block position, held, on tray) and the counts. Each pick or place takes about 15 s.

## Limits (say them)
One red block and one tray; reachable table region only; laptop physics; the grasp assist, not friction, holds the block; ground-truth poses; Sol only; hand-picked prompts, a demonstration, not an evaluation. Pick-and-place that fails reports the failing step and does not retry.

## If it stalls
Ctrl+C, `./cleanup_tmux.sh` in WSL, then show the recorded video `DEMO_BACKUP_objects_take1_visual.mp4` (zoomed Gazebo view with the real tool-call log, say it is a recording) or run the arm demo from the first part of this runbook.
