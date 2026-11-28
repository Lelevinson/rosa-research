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
