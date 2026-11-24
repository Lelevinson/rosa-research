# Part C: Ollama auto-update on the laptop (Windows Ollama used from WSL)

## What I found (read-only; I changed nothing on Windows)
- The Windows app is installed in `D:\Ollama_App` (`ollama app.exe`), version **0.40.17**, data in `C:\Users\user\AppData\Local\Ollama`. Models are in `D:\Ollama_Models`.
- The app's own log says: `msg="beginning update checker" interval=1h0m0s` (`app.log`, 2026-11-22 09:47:56). In `app-2.log` it logged "New update available ... v0.40.17" and "update already downloaded" every hour, then on 2026-11-21 17:27:59 "starting upgrade" and ran `OllamaSetup.exe` (`upgrade.log`, finished 17:29:49). That update changed 0.40.16 to 0.40.17 and restarted the server.
- The app keeps its settings in `Ollama\db.sqlite`, table `settings`. It has a column **`auto_update_enabled`**, currently **1** (on). So the app has an on/off setting for this; it is on.
- The web search found no documented switch (the official FAQ only says the Windows app downloads updates in the background and you restart to apply). So the exact label of the setting in the window is **not verified** by me.
- I could not reach the app's local settings API from WSL (port 54833 gave no answer), and I did not edit the database while the app is running: that is the app's own state and a wrong edit could corrupt chat history. So the switch has to be turned by you.

## Steps for you (laptop, about 2 minutes, before the exam run starts)
1. In Windows, click the Ollama icon in the system tray (bottom right, near the clock; click the `^` arrow if it is hidden) and choose **Settings**. (If the Ollama chat window is open, use its Settings page instead: the gear or your name at the bottom left.)
2. Look for a switch about updates (expected wording: **"Auto-download updates"**). Turn it **off**. If you see no such switch, stop and tell me what the Settings page shows.
3. Close the Settings page. Do not click "Restart to update" if the tray menu shows it. If the tray menu shows "Restart to update", an update is already downloaded and would install at the next restart: tell me first (the freeze needs 0.40.17).
4. Check it worked. In WSL, run (the lines copy the settings database to a temporary folder and read one value; they change nothing):
```
cp /mnt/c/Users/user/AppData/Local/Ollama/db.sqlite* /tmp/ && python3 -c "import sqlite3;print(sqlite3.connect('/tmp/db.sqlite').execute('select auto_update_enabled from settings').fetchone())"
```
   Expected after the switch: `(0,)`. Before it was `(1,)`. (Read it as: copy the three database files `db.sqlite`, `db.sqlite-wal`, `db.sqlite-shm` to `/tmp`, open the copy with Python's sqlite3, ask for the column `auto_update_enabled` of the `settings` table.) If it still shows `(1,)`, the app has not written it yet: close and reopen the Settings page and run the line again.
5. Also confirm the version did not move: `curl -s http://172.30.80.1:11434/api/version` must print `{"version":"0.40.17"}`.
6. After the next Ollama restart, `app.log` should no longer contain a new `beginning update checker` line, or it should say updates are disabled. Check: `grep -i update /mnt/c/Users/user/AppData/Local/Ollama/app.log | tail -3`. (I have not seen the log of a disabled app, so I cannot say what the line will be: treat the database value in step 4 as the proof.)

## If there is no switch or it does not stick (unverified fallbacks, ask me before using)
- Windows Firewall rule that blocks outbound connections of `D:\Ollama_App\ollama app.exe` only. Risk: it may also block sign-in or cloud features; model files already on disk are not affected. Needs an administrator PowerShell. A file-permission lock on `updates_v2` was tried on 2026-11-21 and refused by the permission system; it was not applied.

## The guard (what happens if an update gets through anyway)
`version_guard.py` (frozen, started by `start_stage1_laptop.sh` in its own tmux window) polls `/api/version` and `/api/tags` every 30 s. **Tested today** with a fake Ollama and the frozen file unchanged (`test_version_guard.py`):
| Case | Stop file written | Message sent |
|---|---|---|
| nothing changes for 6 s | no | no |
| version 0.40.17 -> 0.40.18 | yes | yes |
| digest of one of the 7 frozen models changes | yes | yes |
| one frozen model disappears | yes | yes |
| an unlisted extra model appears | no (not part of the freeze, correct) | no |
| Ollama unreachable 3 polls in a row | yes | yes |
The stop file is `<custody queue dir>/<run>/STOP`. The queue refuses to start any further episode when that file exists (seen working in the smoke run: state `stopped`, 2 of 144 done). Limits: it detects and stops after the current episode; it cannot prevent an update, and an update that restarts the server mid-episode fails that episode (the queue retries failed cells). `verify_freeze.py` also refuses to start the run if the version or a digest differs (passed today: all frozen files, 7 digests and version 0.40.17 match).

## Restore auto-update after the exam
Same place as step 1-2: turn the **auto-download updates** switch back **on**, then run the step 4 line: expected `(1,)`. Then you may restart Ollama to apply the pending update. Do not do this until the last exam cell is finished and the results are copied.
