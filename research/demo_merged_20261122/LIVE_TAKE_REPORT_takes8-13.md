# Takes 8-11 (zoomed GUI viewer attempt). 2026-11-22. Status: NOT FINISHED, Sol sign-in invalid

**Label:** merged method (Levinson M + Martin bounded macro), demonstration only, not evaluated. Not method M. Not scored.

| Take | What happened |
|---|---|
| 8 | Same frozen configuration. All 3 tasks reached the expected path (D1, D2, D3). Camera moved to the `ur` model with the GUI "move to" service (works: `gz service -s /gui/move_to`, reply true). **Video unusable:** the Gazebo window in the recording is black. |
| 9 | Same: 3 of 3 reached the expected path. Window black again. |
| 10 | **No task ran.** Sol session failed at start (`protected_storage_unavailable`). Gazebo closed cleanly. No model request. |
| 11 | **No task ran.** Sol session failed at start (`invalid_grant`, HTTP 400). Gazebo closed cleanly. No model request. |

## Why the window was black (cause found, from our own helper)
Earlier viewer windows (WSLg) stay on the desktop as dead black frames after their process ends. My helper put the FIRST "Gazebo Sim" window on top and resized it, and that was a dead one from take 7. It covered the live window in takes 8 and 9. Fix: `hide_stale.ps1` hides all leftover "Gazebo Sim" windows before a take (7 were hidden), and no window is moved or resized. The new window then appears on top as in take 7. This was not yet shown on a recording because Sol stopped working.

## Why it stops here
Sol's remembered sign-in now fails (`invalid_grant`): the refresh token is no longer accepted. A new sign-in needs Martin and a new OAuth consent, which is not authorized here. I did not try it, and I did not switch the model (a Qwen run at context 8192 would be a different model and a labelled deviation; not requested).

## What works already (GUI only, no code or launch change)
- Viewer: `gz sim -g` with the server's `GZ_PARTITION` (take 7).
- Camera on the arm: `gz service -s /gui/move_to --reqtype gz.msgs.StringMsg --reptype gz.msgs.Boolean --req 'data: "ur"'` (taken 8-11, reply true).
- Scripts: `live_takes/viewer_scripts_take8-11/` (`watch_gui_zoom.sh` does attach + camera; `hide_stale.ps1`).

## To finish (needs Martin)
1. Sign in to Sol again yourself, the way you did before (Session A's route).
2. Tell me. I run take 12 with: `hide_stale.ps1`, desktop recording, `watch_gui_zoom.sh`, `live_demo.py` (unchanged), then make `DEMO_BACKUP_take8_visual.mp4`-style split screen and update the runbook (camera step + preferred backup). The raw desktop recordings are not committed (they show the whole screen).

---
## Update 2026-11-22 21:1x: takes 12 and 13 (Sol signed in again)
**Correction to the numbering (facts from the records).** Take 8 was NOT interrupted: it ran 19:31-19:32 and completed (3 of 3, clean close). VS Code was closed at about 21:05; the run active then was take 12 (21:05-21:06), which also completed (3 of 3). The closing only caused a duplicate start of the take 12 command, which stopped at once (folder existed). Nothing was logged as "interrupted" because nothing was. Numbers 9-12 were already used (9: black window; 10, 11: Sol sign-in failed; 12: check run), so the redo is **take 13**.
**Cleanup:** no Gazebo server, no ffmpeg, no viewer left (4 stale `gz sim -g` viewers from takes 8-11 were stopped with `kill -9`; `hide_stale.ps1` found 0 dead windows).
**Take 13** (same frozen configuration, Sol): D1, D2, D3 all reached the expected path (D2: inspect then park_right, 1 write; D3: stage_left, 1 write); 3 of 3 resets, clean close. Gazebo viewer window with the camera moved to the arm (`/gui/move_to`, reply true) and `hide_stale.ps1` run before: the window rendered normally and the arm fills the view.
**Video:** `DEMO_BACKUP_take8_visual.mp4` (72 s), split screen made by `render_split.py` (crop of the Gazebo window only, scaled; log panel from the recorded trace, aligned by wall clock). The raw desktop recording shows the whole screen and is not committed. Clearer than take 7 (arm much larger), so it is now the preferred backup in `DEMO_RUNBOOK.md`.
