# Lab computer setup checklist (primary exam machine; written 2026-11-19, draft)

Owner decision (2026-11-19): **heavy work (the exam, simulations, bulk model runs) runs on the lab computer (Ubuntu, reached by SSH)**; the laptop is for dev runs. Each step has a command whose output proves it. Tick a step only when its verify command gives the stated result; paste the outputs into `research/studies/final_exam_draft_20261118/LAB_SETUP_LOG.md` on the lab machine (one line per step: date, command, result). Reference values are from the laptop (the dev machine) on 2026-11-19.

**Not decided here (the owner / lab):** the lab's GPU, RAM, and whether the exam needs the lab's Ollama on `localhost` (the dev scripts assume the laptop's Windows-hosted Ollama, see step 4).

## 0. Access and housekeeping
| step | verify |
|---|---|
| SSH key login works from the laptop; a short alias exists | `ssh lab 'hostname; whoami; date; timedatectl | grep "Time zone"'` -> the lab host, your user, a current date, time zone noted (the team uses Asia/Taipei) |
| `sudo` available for the install steps (or an admin does them) | `ssh lab 'sudo -n true && echo sudo-ok'` |
| enough disk for raw traces (about 50-100 GB for the full exam, see `RUNBOOK.md` section 4) | `ssh lab 'df -h ~ | tail -1'` -> at least 200 GB free |
| record the machine | `ssh lab 'lscpu | grep -E "Model name|^CPU\(s\)"; free -g | sed -n 2p; nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader; lsb_release -ds'` (laptop: 12 CPUs, 15 GB RAM, RTX 4060 Laptop 8,188 MiB, driver 621.24 on the Windows side, Ubuntu 24.04.5 LTS) |
| the exam machine does not sleep, suspend or auto-reboot | `systemctl is-enabled sleep.target suspend.target hibernate.target 2>&1` -> `masked` (else `sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target`); `grep -E "Automatic-Reboot" /etc/apt/apt.conf.d/50unattended-upgrades` -> `"false"` |
| CPU frequency is not throttled while idle | `cpupower frequency-info 2>/dev/null | grep -i governor` -> `performance` (or the closest available; note it) |

## 1. ROS 2 Jazzy
| step | verify |
|---|---|
| Ubuntu **24.04** (Jazzy needs it) | `lsb_release -rs` -> `24.04` |
| ROS 2 Jazzy desktop (laptop: `ros-jazzy-desktop 0.11.0-1noble.20260905`) | `dpkg -l ros-jazzy-desktop | tail -1`; `source /opt/ros/jazzy/setup.bash && printenv ROS_DISTRO` -> `jazzy` |
| the exam's ROS settings (every fixture session) | `export ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1; ros2 node list --no-daemon` -> empty and exit code 0 |
| turtlesim (the turtlesim pool) | `dpkg -l ros-jazzy-turtlesim | tail -1`; `ros2 pkg executables turtlesim | head -3` |

## 2. Gazebo, TurtleBot3 and Nav2 (headless)
Laptop packages: `ros-jazzy-nav2-bringup 1.3.13`, `ros-jazzy-navigation2 1.3.13`, `ros-jazzy-turtlebot3-gazebo 2.3.7`, `ros-jazzy-turtlebot3-navigation2 2.3.6`, `ros-jazzy-ros-gz 1.0.24` (bridge, sim, image), `ros-jazzy-gz-sim-vendor 0.0.13`. Use the same versions if the repository offers them.
| step | verify |
|---|---|
| packages installed | `dpkg -l | awk '/^ii/ {print $2" "$3}' | grep -E "^ros-jazzy-(nav2-bringup|navigation2|turtlebot3-gazebo|turtlebot3-navigation2|ros-gz) "` -> 5 lines |
| model variable | `export TURTLEBOT3_MODEL=burger` (the stack script sets it itself; check it is the Burger) |
| the owned stack starts, Nav2 goes active and a goal succeeds | `cd ~/project/rosa-research && uv run --no-project --python /usr/bin/python3 python research/studies/turtlebot3_nav2_smoke_20261116/stack.py start && source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=219 ROS_LOCALHOST_ONLY=1 && sleep 60 && uv run --no-project --python /usr/bin/python3 python research/studies/turtlebot3_nav2_smoke_20261116/navigate_once.py` -> last line `NAVIGATION PASS` |
| clean shutdown | `uv run --no-project --python /usr/bin/python3 python research/studies/turtlebot3_nav2_smoke_20261116/stack.py stop` -> `STOP PASS remaining []` and `pgrep -af "gz sim|nav2"` empty |
| headless on the lab's GPU/CPU (no display needed over SSH) | the stack runs with `--headless-rendering`; run the two commands above from an SSH session without `DISPLAY` set |

## 3. uv, the repository, the branch
| step | verify |
|---|---|
| uv installed (laptop 0.13.2) | `uv --version` |
| clone and branch (research branch of this repository; **no pushes from the lab**) | `git -C ~/project/rosa-research rev-parse --abbrev-ref HEAD` -> `research/capability-discovery-20261110` (or the branch the owner names); `git rev-parse --short HEAD` -> the same short hash as the laptop (laptop: `e0e5c3c` plus the uncommitted research files: copy `research/` with rsync, it is Git-excluded) |
| `research/` copied (it is excluded from Git) | `rsync -a --exclude _artifacts --exclude .local laptop:~/project/rosa-research/research/ ~/project/rosa-research/research/` ; `ls research/studies | wc -l` equals the laptop's |
| dependencies locked identically | `uv sync` then `sha256sum uv.lock | cut -c1-16` -> `dbd8cb6db95ab8f7` (the hash recorded in `thinking_escalation_20261119/FREEZE.json`) |
| the study tests pass on the lab | `uv run python -m unittest discover -s research/studies/thinking_escalation_20261119/tests` -> `OK`; `uv run python -m unittest discover -s research/studies/final_exam_draft_20261118/exam_queue/tests` -> `OK` (about 1-2 minutes) |
| scorer unchanged | `sha256sum research/studies/residual_failures_20261115/scorer_v2.py` -> `c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9` |
| tmux | `tmux -V` (laptop 3.4) |

## 4. Ollama and the four models (digests must match)
**Code change needed first (not made yet; do not edit during a run):** the dev scripts assume the laptop's Windows-hosted Ollama at `http://172.30.80.1:11434` (hard-coded in `headroom_diagnostic_20261112/run_stage1.py`, `vendor/menu_run_study.py`, `final_exam_draft_20261118/exam_queue/health.py`, `gazebo_nav2_model_memory_20261119/check.py`, the probe scripts). On the lab Ollama runs on the same host (`http://127.0.0.1:11434`). Minimum change: read an environment variable (for example `ROSA_OLLAMA_URL`, default unchanged) in those places, test on the laptop, record the new file hashes in the next freeze. Until then the lab runs fail at the first model request (the queue's Ollama check will report "Ollama unreachable").
| step | verify |
|---|---|
| Ollama installed, same version as the laptop (**0.40.16**) | `ollama --version`; `curl -s http://127.0.0.1:11434/api/version` -> `{"version":"0.40.16"}` |
| one model resident, no parallel requests (the studies assume it) | `systemctl show ollama -p Environment` includes `OLLAMA_NUM_PARALLEL=1` and `OLLAMA_MAX_LOADED_MODELS=1` (set them with `sudo systemctl edit ollama` if absent); note any other `OLLAMA_*` setting of the laptop's service |
| the four models are present | `ollama list` shows `lfm3:1.7b`, `qwen3.5:9b`, `gpt-oss:20b`, `bonsai-2:4b`; pull them, or copy `~/.ollama/models` from a machine that has them if a tag cannot be downloaded |
| **digests equal ours** | `curl -s http://127.0.0.1:11434/api/tags | python3 -c "import sys,json;d={m['name']:m['digest'] for m in json.load(sys.stdin)['models']};e={'lfm3:1.7b':'b36a103fe2f8fbe9df2ceec88b9cfdf842dc04aaabe2b4677d1acf8e16570b5d','bonsai-2:4b':'93edd652c9326fb1e782c1f54e997ce6a46e2351c763777db0c63b8a51cf6bec','gpt-oss:20b':'f38aa0c53da5f8c49d08c43a99df24ff53167fe68e24664a7777288e7656fdfe','qwen3.5:9b':'56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90'};print({k:d.get(k)==v for k,v in e.items()})"` -> all `True` |
| context 65536 fits | after the memory check (step 7) `curl -s http://127.0.0.1:11434/api/ps` shows `context_length` 65536 for the loaded model |
| thinking behaviour as on the laptop (gpt-oss cannot be switched off; `think:false` maps to a medium-like level) | `python3 research/studies/thinking_escalation_20261119/gpt_oss_level_probe.py` on the lab (about 40 minutes; compare `gpt_oss_level_probe.json` medians with the laptop's: false 216 / 53, low 91 / 34, medium 214 / 49, high 462 / 187) |

## 5. Held-out access through the custodian (never copied into the repository)
| step | verify |
|---|---|
| Codex supplies the **paths** (a custodian location on the lab, outside any Git working tree) and the environment variable names the spec expects (`ROSA_HELDOUT_V2_TASKS`, `ROSA_TURTLESIM_HELDOUT_TASKS`, `ROSA_NAV2_INSPECTION_TASKS`, `ROSA_NAV2_ACTION_TASKS`) | `for v in ROSA_HELDOUT_V2_TASKS ROSA_TURTLESIM_HELDOUT_TASKS ROSA_NAV2_INSPECTION_TASKS ROSA_NAV2_ACTION_TASKS; do test -f "${!v}" && echo "$v ok" || echo "$v MISSING"; done` (prints names only) |
| counts only, no content | `python3 -c "import json,os;[print(v,len(json.load(open(os.environ[v])))) for v in ('ROSA_HELDOUT_V2_TASKS','ROSA_NAV2_INSPECTION_TASKS','ROSA_NAV2_ACTION_TASKS') if v in os.environ]"` -> 76, 24, 10 (the sizes the owner stated) |
| not inside a Git tree and not world-readable | `for v in ROSA_HELDOUT_V2_TASKS ROSA_NAV2_INSPECTION_TASKS; do git -C "$(dirname "${!v}")" rev-parse 2>&1 | head -1; stat -c '%a %U' "${!v}"; done` -> "not a git repository", mode 600 or 640 |
| **a held-out adapter exists in the runners** (does not yet: the dev runners only know the dev tasks) | built by whoever prepares the exam runners with Codex; verify with a custodian-approved dummy task file that the runner loads it and fails loudly when the variable is missing |
| nothing held-out in the mirror or Git | `rosa-context-sync --dry-run | grep -c "would copy"` and `git status --short | grep -ci held` -> 0 (the sync script already excludes `research/.local/` and the old held-out folders) |

## 6. Queue runner and notifications
| step | verify |
|---|---|
| ntfy topic on the lab (its own random topic, kept in `~/.config/rosa-exam/`) | `python3 research/studies/final_exam_draft_20261118/exam_queue/notify.py init && python3 .../notify.py show-topic`; subscribe to it in the ntfy app |
| every notification reaches the phone | `python3 research/studies/final_exam_draft_20261118/exam_queue/trigger_notifications_once.py` -> 7 messages (finished, crash, no progress, Ollama down, low disk, daily, a block keeps failing) arrive; then `cat ~/.config/rosa-exam/notify.log | tail -8` shows 7 `sent` lines |
| the monitor starts cleanly even before the run folder exists | `uv run python -m unittest research.studies.final_exam_draft_20261118.exam_queue.tests.test_queue.MonitorStartupTests` -> `OK` (the race that silenced thinking part A) |
| optional email (Gmail app password) | see `RUNBOOK.md` section 5; test with `python3 .../notify.py test finished` (email line appears if configured) |
| the queue's plan is accepted | `uv run python research/studies/final_exam_draft_20261118/exam_queue/queue_core.py plan --spec research/studies/final_exam_draft_20261118/exam_queue/specs/thinking_replA2_spec.json` -> 432 cells, no warning (this also checks the frozen plan hash against the code on the lab) |
| a dummy run works end to end | `DUMMY_DELAY_SECONDS=1 bash research/studies/final_exam_draft_20261118/exam_queue/start_exam_tmux.sh lab_dummy $PWD/research/studies/final_exam_draft_20261118/exam_queue/specs/dummy_spec.json all all:1 -- --dummy` then, after about 1 minute, `uv run python .../queue_core.py status --run-name lab_dummy --machine all` -> `finished 30 30` |

## 7. Gazebo / model memory check on the lab
| step | verify |
|---|---|
| run the memory check (after the Ollama URL change of step 4) | `uv run --no-project --python /usr/bin/python3 python research/studies/gazebo_nav2_model_memory_20261119/check.py` (about 15 minutes) |
| compare with the laptop's `REPORT.md` table | `python3 -c "import json;r=json.load(open('research/studies/gazebo_nav2_model_memory_20261119/results.json'));[print(m,v['A_loaded'].get('size_vram_mib'),v['C_inference_with_stack'].get('peak_gpu_used_mib'),v['C_inference_with_stack'].get('tokens_per_second'),v['C_navigation_passed'],v['failures']) for m,v in r['models'].items()]"` -> every `C_navigation_passed` True, every `failures` empty; record VRAM resident, peak GPU memory and tokens/s per model (laptop: lfm3 152.7 -> 143.8, bonsai 106.7 -> 88.2, qwen3.5 12.1 -> 9.3, gpt-oss 24.3 -> 16.2 tokens/s alone -> with stack) |

## 8. Mini exam: speed on the lab
| step | verify |
|---|---|
| run the 8-episode mini exam | `ROSA_EXAM_MACHINE=lab bash research/studies/final_exam_draft_20261118/exam_queue/start_exam_tmux.sh mini_exam_lab $PWD/research/studies/final_exam_draft_20261118/exam_queue/specs/mini_exam_spec.json lab all:1` |
| complete and clean | `uv run python .../queue_core.py merge-check --spec .../specs/mini_exam_spec.json --run-name mini_exam_lab` -> `duplicates 0, missing 0` |
| speed against the laptop | `uv run python .../exam_tables.py --run-name mini_exam_lab` -> table 5 (episode wall times). Laptop reference (seconds, median): E1 lfm3 29, E1 qwen3.5 55, M lfm3 23, M qwen3.5 33 (total 6.7 minutes of episode time). Write the ratio lab / laptop per row into `LAB_SETUP_LOG.md`; it sizes the exam (`RUNBOOK.md` section 10) |

## 9. SSH-disconnect test with tmux
| step | verify |
|---|---|
| tmux survives a dropped SSH connection | in an SSH session: `DUMMY_DELAY_SECONDS=15 bash .../start_exam_tmux.sh ssh_test $PWD/.../specs/dummy_spec.json all all:1 -- --dummy`; note `done` with `uv run python .../queue_core.py status --run-name ssh_test --machine all | grep -E '"state"|"done"'`; **kill the SSH client** (close the terminal window or `kill -9` the local `ssh` process); wait 3 minutes; reconnect: `tmux ls` shows `exam-ssh_test` and `done` is larger and the heartbeat recent |
| user processes survive logout | `loginctl show-user $USER | grep -E "Linger|State"` -> `Linger=yes` (else `sudo loginctl enable-linger $USER`); `grep -E "^KillUserProcesses" /etc/systemd/logind.conf` -> `no` or absent |
| cleanup | `touch research/_artifacts/exam/ssh_test/STOP; rm -rf research/_artifacts/exam/ssh_test research/studies/final_exam_draft_20261118/exam_results/ssh_test` |

## 10. Two machines (laptop + lab)
| step | verify |
|---|---|
| both use the same spec file and share string | on each: `sha256sum <spec>`; `queue_core.py plan --spec <spec> --machines laptop:0.2,lab:0.8` prints the same cell counts per tier (the owner sets the shares; the lab is primary) |
| logs can be exchanged | `rsync -a lab:~/project/rosa-research/research/_artifacts/exam/RUN/RESULTS_LOG_lab.jsonl research/_artifacts/exam/RUN/` then `queue_core.py merge-check ... --machines laptop:0.2,lab:0.8` -> duplicates 0 |

## 11. Go / no-go before the first exam episode on the lab
All of: steps 0-9 ticked and logged; model digests all True; scorer and `uv.lock` hashes equal; the mini exam finished with 0 duplicates; the SSH-disconnect test passed; the notification test reached the phone; the Ollama URL change made, tested on the laptop and re-frozen; the held-out adapter built and tested with a custodian-approved dummy; the frozen exam spec hashed. Missing any: do not start; report which step is open.

## Open search (things noticed while writing the checklist)
- The Ollama address is hard-coded in at least 6 scripts (listed in step 4); the lab cannot run anything until it is configurable.
- `research/` and `_artifacts/` are Git-excluded: the lab gets the code by rsync, not by `git clone`; any file edited on one machine and not copied is a silent difference. The freeze files record hashes; compare them on the lab (`FREEZE.json` hashes against `sha256sum`).
- The laptop's WSL host passes the GPU through D3D12 (`/dev/dxg`); a native Linux lab GPU behaves differently (driver, memory reporting); the memory check and the mini exam are the only evidence of equivalence.
