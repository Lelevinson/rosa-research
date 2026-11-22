# Take 7 (Sol) with a Gazebo GUI attached as a viewer. 2026-11-22

**Label:** merged method (Levinson M + Martin bounded macro), demonstration only, not evaluated. Not method M. Not scored. Credit: method M components (Levinson).

## Viewer
- Works. WSLg is available (`DISPLAY=:0`). The viewer is `gz sim -g` started with the `GZ_PARTITION` of the running headless server (read from the server's process environment). The frozen launch code (`GazeboDemo`) and `live_demo.py` were NOT changed. Gazebo Sim window showed the world and the `ur` arm.
- Script: `live_takes/sol_take7/watch_gui_viewer.sh`; its log `gui_attach.log` (partition found about 24 s into the recording).

## Take 7 (same frozen configuration, unchanged)
Gazebo healthy, 3 of 3 resets confirmed, clean close. D1 expected path (menu tools, name-fixed publisher), D2 inspect then park_right then answer (readiness true, shoulder_pan 0.16, 1 write), D3 stage_left then answer (wrist_3 0.20, 1 write). All three reached the expected path. Records: `live_takes/sol_take7/`.
Counting take 7 with takes 3-6 (same configuration): D1, D2, D3 each 5 of 5.

## Video
`DEMO_BACKUP_take7_visual.mp4` (67 s): left = the Gazebo window (cropped and enlarged, arm in the centre), right = the recorded tool-call log of the same take, aligned by wall clock (`render_split.py`). The desktop recording was made with ffmpeg screen capture; only the cropped Gazebo window is kept in the video. The raw desktop recording (it shows the whole screen) is NOT committed and stays outside the repository.
Limits: the arm is small at the default camera and moves only a little (small joint changes), so the motion is subtle; the picture is scaled up and a little pixelated. The log panel is time-aligned by the clock, with an alignment error of well under a second.
