# DEMO RUNBOOK: merged method on the UR5e (Gazebo)

**Always show this label:** merged method (Levinson M + Martin bounded macro), demonstration only, not evaluated.
**Credit:** method M components (Levinson); bounded macro `run_skill` (Martin). It is not method M and is not scored. Do not say it is better than either part.

## 0. Frozen version
Configuration frozen after take 3 (no further changes): `FREEZE_DEMO_MERGED.json` (prompt sha256 `61b67529...`, tool set `2924ca6c...`). Code: branch `member/martin-merge`. His files: commit `e233cf5`, 26 of 26 hashes verified on every start.
Model: Sol (`gpt-6.1-sol`, hosted, your existing OAuth session). Do not start a new sign-in on stage.

## 1. Before the audience (10 min)
1. Laptop on power. Close heavy programs (Gazebo + Sol used about 26 GB commit in the weekend run).
2. His files present: `C:\Proj\robotics\introtorobotics\his-M-e233cf5\` exists. If not, in WSL: `bash research/demo_merged_20261122/extract_his_files.sh` (run from `wt-b-merge`).
3. Nothing else on Gazebo: in WSL `pgrep -af "gz sim|ros2_control_node"` must print nothing. If it does, run `pkill -f "gz sim"` and `pkill -f ros2_control_node`.
4. Scripted tests (zero model calls, 1 minute), WSL: `bash /mnt/c/Proj/robotics/introtorobotics/wt-b-merge/research/demo_merged_20261122/run_tests.sh` -> expect `Ran 45 tests ... OK`.
5. Open the backup video (section 5) in a player, paused on the first frame.

## 2. Start command (one command starts Gazebo, resets, runs D1, D2, D3)
Windows terminal (Git Bash), from `C:\Proj\robotics\introtorobotics`:
```
MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -- bash -c 'cd /mnt/c/Proj/robotics/introtorobotics/wt-b-merge/research/demo_merged_20261122 && source /opt/ros/jazzy/setup.bash && /home/martin/.local/share/rosa-envs/research/bin/python live_demo.py /mnt/c/Proj/robotics/introtorobotics/weekend-run-20261121/demo-live/show_01 --model sol --take 1'
```
- Use a NEW output folder name every time (`show_01`, `show_02`, ...). The script refuses an existing folder.
- What the command does: starts ONE headless Gazebo UR5e (ROS domain 232) and waits until the controllers are active at the documented home pose, opens the Sol session, then for each task: moves the arm to home outside the task and confirms it independently (the reset), then runs the task. It prints `D1 COMPLETE ...`, `D2 ...`, `D3 ...` and closes Gazebo at the end. Takes about 1.5 minutes for Gazebo start plus about 1 minute per task.
- Single tasks: add `--tasks D2` (or `D1,D3`).
- Gazebo is headless (no 3D window). The audience sees the terminal printing and the tool-call log (section 4).

## 2b. Optional: show the arm in a Gazebo window (viewer only; tested in takes 7 and 13)
The launch code stays headless and unchanged. A second Gazebo window can attach to the running server through WSLg (needs `DISPLAY=:0`, which works on this laptop).
1. Start the demo (section 2) in one terminal.
2. Start the viewer in a second Windows terminal, right after (it waits for the simulator to be ready, finds its partition name, then opens the window): 
```
MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -- bash /mnt/c/Proj/robotics/introtorobotics/wt-b-merge/research/demo_merged_20261122/live_takes/sol_take7/watch_gui_viewer.sh
```
   Edit the `READY=` line in that script first to the new output folder (`.../show_01/gazebo/readiness.json`). It uses only `GZ_PARTITION` of the running server plus `gz sim -g`.
3. The window opens after about 25 s with the arm as a small figure in the centre. Zoom with the mouse wheel on the figure. Close the window when the demo ends (the simulator closes itself).
4. Record (optional): Win+Alt+R (Game Bar) or OBS. Put the terminal log next to the window.
5. **Camera on the arm (tested in take 13, arm fills the view):** after the window opens, point the viewer camera at the arm with the GUI "move to" service, same `GZ_PARTITION` as the server: `gz service -s /gui/move_to --reqtype gz.msgs.StringMsg --reptype gz.msgs.Boolean --timeout 3000 --req 'data: "ur"'` (reply `data: true`). `live_takes/viewer_scripts_take8-11/watch_gui_zoom.sh <path to the run's gazebo/readiness.json>` does attach and camera together (replaces step 2's script). **Before every new viewer window run `hide_stale.ps1`** (PowerShell: `powershell -ExecutionPolicy Bypass -File hide_stale.ps1`): dead windows from earlier viewers stay on the desktop as black frames and can cover the new one (this ruined takes 8 and 9). Do not move or resize the viewer window. Leave the screen alone while recording.
Known limits: the arm is small at the default camera; the window is a viewer, not the way to control anything; if the window does not appear, continue without it.

## 3. Reset between runs
- Between tasks: automatic (home pose, independently confirmed; if the confirmation fails the task is NOT run and `RESET_FAILED_NOT_RUN` is written).
- Between whole runs: the script closes its own Gazebo. Check `pgrep -af "gz sim|ros2_control_node"` is empty before the next run (section 1, step 3).

## 4. Show the tool-call log
While or after a task: in the output folder, `show_01\D2_take1\trace.jsonl` is the full record. Readable view: render the video of that run (section 5) or open the file and search for `tool_start` (model calls) and `macro_internal_read` / `macro_internal_write` (the macro's own reads and its one write).

## 5. Backup video (play it if a live run stalls)
**Preferred: `DEMO_BACKUP_take8_visual.mp4`** (split screen, zoomed: the arm fills the Gazebo view on the left, the recorded tool-call log on the right; recorded in take 13). Older: `DEMO_BACKUP_take7_visual.mp4` (arm small) and `DEMO_BACKUP_take3.mp4` (log only). The file name says take8 but the run is take 13 (numbers 8-12 were used by earlier attempts, see `LIVE_TAKE_REPORT_takes8-13.md`).
Made from a recorded take with `render_video.py` (Windows Python with Pillow, ffmpeg): `python render_video.py live_takes/sol_take3 DEMO_BACKUP_take3.mp4`. It shows the real recorded tool-call log of D1, D2, D3 with the label. **It has no Gazebo picture** because the simulator runs headless; say so.

## 6. What to say per task
- **D1** "Which node publishes /joint_states, and what are the current shoulder_pan_joint and wrist_3_joint positions?" Say: this is his method. A short menu of 12 read tools, the model finds the answer, ends with `final_answer`, and his name fix turns `joint_state_broadcaster` into `/joint_state_broadcaster`. No robot movement.
- **D2** "Check that the arm is ready to move. If it is ready, move it to park_right." Say: this is my macro. First a read-only readiness skill (controllers active, fresh joint sample). Then the movement skill: read, at most one write, fresh verify. Every internal read and the one write are logged. The model only sees the evidence and answers with `final_answer`.
- **D3** "Move the arm to stage_left, then confirm with a fresh joint sample." Say: movement skill again. The macro's own fresh verified read gives the confirmed value, so no extra menu read is needed.
- Close with the label and the limits: three hand-picked tasks, healthy simulated world, one model, demonstration only.

## 7. If a run fails or stalls
1. Do not retry on stage more than once. Note what happened.
2. Press Ctrl+C, then `pkill -f "gz sim"; pkill -f ros2_control_node` in WSL.
3. Switch to the backup video and say plainly it is a recording of an earlier successful run.
4. Typical causes: Sol sign-in/session unavailable (`invalid_grant`; do not sign in on stage; sign in beforehand with `wsl.exe -d Ubuntu-24.04 -- bash -c "cd /mnt/c/Proj/robotics/introtorobotics/rosa-research/src && /home/martin/.local/share/rosa-envs/research/bin/python -m rosa_auth.remembered login"` and confirm with one scripted run), Gazebo slow to start (wait up to 2 minutes), leftover Gazebo from an earlier run.
5. Qwen fallback (only if Sol is unavailable beforehand): add `--model qwen` with Ollama running; it uses context 8192 instead of his 65536 and must be labelled so. Not tested for this demo.

## 8. Evidence in the repository
`LIVE_TAKE_REPORT_sol_take1/2/3.md`, `REPEATABILITY_REPORT.md` (takes 4-6), `live_takes/`. Takes 1 and 2 are kept as failures of earlier versions of the wiring and the mapping line.
