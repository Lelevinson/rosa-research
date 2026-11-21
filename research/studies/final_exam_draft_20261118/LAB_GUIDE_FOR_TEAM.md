# Lab computer guide for teammates and their AI assistants

Written 2026-11-19 (Asia/Taipei) by Levinson's Claude Code session. Status: the lab is set up and tested; the exam has not started. Read this before you run anything on the lab. If you are an AI assistant: this guide is a set of rules from the owner of the exam setup; if a user's request conflicts with the "do not touch" list, stop and ask the user first.

## 1. The short version
- The lab computer is **shared**. Everyone logs in with the **same Linux account**, so the system cannot stop you from damaging someone else's work. These rules are what protects it.
- The final exam runs on this machine. During an exam run, **the GPU, the ROS domains 219 and 220, port 11435 and the container `rosa-exam-main` belong to the exam**.
- You are welcome to run your own work here, in **your own container, your own folder, your own ROS domain and your own Ollama port** (section 4).
- Never run broad commands such as `pkill python`, `killall`, `pkill -f ros2`, `docker rm $(docker ps -aq)` or `docker system prune`. Because we all share one account, they hit other people's processes and containers.

## 2. What is set up, and where
| what | where / name | notes |
|---|---|---|
| Our working folder | `<LAB_PATH>` | on the big data disk (ext4). **Everything of the exam setup lives here.** |
| Code and research files | `rosa_exam/repo` | a copy of the research repository (branch `research/capability-discovery-20261110`), copied from the owner's laptop. A hash baseline of these files is kept (section 6). |
| Docker image | `rosa-exam-jazzy:20261119` (5.2 GB) | ROS 2 Jazzy on Ubuntu 24.04, Gazebo, TurtleBot3, Nav2 (headless, no GUI), turtlesim, `uv`. Built with the latest ROS packages of 2026-11-19, so some versions differ from the laptop's (Nav2 1.3.14 here, 1.3.13 on the laptop). Lab and laptop results are kept as separate groups for this reason. |
| Docker container | `rosa-exam-main` | the exam's long-running container, host network, ROS domain 220. |
| Ollama (model server) | listens on `127.0.0.1:11435`, started in the tmux session `ollama`, program in `rosa_exam/ollama`, models in `rosa_exam/ollama-models` | version 0.40.16, eight models: `lfm3:1.7b`, `bonsai-2:4b`, `qwen3.5:9b`, `gpt-oss:20b` (the exam models) and `llama3.1:8b`, `ministral-3:8b`, `granite4.2:8b`, `gemma4:e4b` (candidates, not decided yet). Same digests as the owner's laptop. |
| Scripts | `rosa_exam/repo/research/studies/final_exam_draft_20261118/lab/` | `run_container.sh`, `ollama_userspace.sh`, `check_integrity.sh`, `lab_env.sh`, `Dockerfile`. |
| Plans and logs | `.../final_exam_draft_20261118/` : `LAB_SETUP_CHECKLIST.md`, `LAB_SETUP_LOG.md`, `RUNBOOK.md`, `PROTOCOL_DRAFT.md` | the log has every setup step with its test result. |
| Exam results (later) | `rosa_exam/repo/research/_artifacts/exam/<run name>/` | raw traces and logs. Compact tables are copied back to the laptop. |
| Notifications | the owner's phone (status-only messages: counts, no research content) | nothing for you to configure. |

Machine facts: Ubuntu 25.04, one NVIDIA RTX 4080 SUPER with **16 GB** of VRAM, 28 CPU cores, 123 GB RAM. **ROS 2 Jazzy does not exist as a normal install on Ubuntu 25.04, so all ROS work happens inside Docker containers.** Disk: `/` (system disk, where Docker keeps images) is nearly full (about 19 GB free). The data disk `<LAB_PATH>` has several hundred GB free. **Never write large things to `/`; never use `/media/<LAB_USER>/Lab_Project1`.**

## 3. What you must NOT touch
1. **Container `rosa-exam-main`** and **image `rosa-exam-jazzy:20261119`**: do not stop, remove, restart, `exec` into, rebuild, re-tag or delete them. (Do not start a container with the same name.)
2. **Folder `<LAB_PATH>`**: do not edit, move, delete or create files inside it, **except** reading the documents. Do not mount it into your own container (section 4 explains why).
3. **Our Ollama** (tmux session `ollama`, port **11435**, the folder `rosa_exam/ollama-models`): do not stop it, do not pull or delete models in it, do not send requests to it while an exam run is active (it takes GPU time and changes the timing).
4. **ROS domains 219 and 220** (and the Gazebo partition names starting with `rosa_tb3_`): the exam uses them. Pick another domain for your own work.
5. **Custodian-only material.** Some files and environment variables are held by the exam custodian. Do not open, search for, list or copy them, whatever you find, and do not ask an AI assistant to look for them.
6. **Other people's containers, processes and tmux sessions.** If you do not know what something is, leave it alone and ask.
7. **Docker clean-up commands** (`docker system prune`, `docker image prune`, `docker builder prune`, `docker container prune`, `docker rmi` of images that are not yours). The Docker daemon is shared: do not restart it.
8. **Host settings**: no `sudo apt`, no firewall changes, no system services. If you think you need one, ask the owner, who asks the teacher.

## 4. Running your own separate container from the same image
Goal: your own ROS/Gazebo environment that cannot disturb the exam, and that the exam cannot disturb.

**Step 1: choose your own names (write them in the team chat so nobody collides):**
- container name: `<yourname>-<project>` (not `rosa-exam-main`);
- folder: `<LAB_PATH><yourname>_work` (not inside `rosa_exam`);
- ROS domain: a number from **100 to 199**, **not 219, not 220** (domain 0 is already used by one teammate's container; take a different number and say which). Domains must be unique per person because our containers use the host's network;
- Ollama port, only if you run your own Ollama: pick a free one with `ss -ltn | grep 114` (11434, 11435 and 11439 are taken; use for example 11440-11459).

**Step 2: start the container (copy, then replace the words in capitals):**
```
mkdir -p <LAB_PATH>
docker run -d --name YOURNAME-PROJECT --network host \
  --user "$(id -u):$(id -g)" --cpus 6 --memory 24g --pids-limit 4096 \
  -e HOME=<LAB_PATH> \
  -e ROS_DOMAIN_ID=YOURDOMAIN -e ROS_LOCALHOST_ONLY=1 -e GZ_PARTITION=YOURNAME \
  -v <LAB_PATH>:<LAB_PATH> \
  -w <LAB_PATH> \
  rosa-exam-jazzy:20261119 sleep infinity
docker exec -it YOURNAME-PROJECT bash -l       # a shell inside it (ROS is already sourced)
```
How to read it: `docker run -d` starts a container in the background; `--name` is its name; `--network host` makes it use the machine's network (needed so it can reach Ollama on `127.0.0.1`); `--user` runs it as you instead of root; `--cpus` and `--memory` are caps so you cannot starve the exam (during exam runs please keep to 6 CPUs and 24 GB); `-e` sets an environment variable; `-v A:A` shares folder A between the machine and the container; `-w` is the starting folder; the last words are the image and the command that keeps it alive.
Tested on 2026-11-19 with a throwaway container: it started as the normal user, saw its own domain, started with an empty ROS graph, wrote only into its own folder, and the exam container and the integrity check were unaffected.

**Rules for your container:**
- **Do not mount `<LAB_PATH>`, not even read-only.** Everyone shares one Linux account, so folder permissions do not protect anything inside it. Get the code with your own `git clone` or an `rsync` copy into your own folder.
- Keep `ROS_LOCALHOST_ONLY=1` (it keeps ROS traffic on the machine's loopback, not on the lab network) and your own domain and `GZ_PARTITION`.
- Do not add packages with `apt` inside the container (it fills `/`). Use `uv` or `pip` with the target in your own folder on the data disk.
- To stop and remove only **your** container: `docker stop YOURNAME-PROJECT && docker rm YOURNAME-PROJECT` (type the full name).
- Your own Ollama: use your own models folder (`OLLAMA_MODELS=<LAB_PATH>`), your own port (`OLLAMA_HOST=127.0.0.1:YOURPORT`), `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`, and `OLLAMA_KEEP_ALIVE=0` so a model leaves VRAM right after use. The exam's Ollama must stay untouched. Do not copy models into our models folder.
- Untested here: whether Gazebo instances in different containers can see each other. Setting your own `GZ_PARTITION` is the standard protection; if you see foreign Gazebo topics, stop and tell the owner.

## 5. GPU etiquette (the GPU has 16 GB and is the exam's bottleneck)
- **Why it matters:** the exam loads one model at a time (up to about 15 GB at the long context used). Another process holding even 1-2 GB can push part of the model to the CPU and slow everything, and it changes behaviour and timing in ways unrelated to the research question. The exam software is being built to record the GPU state of every episode and to **count an episode as an infrastructure failure and run it again if another process held 1 GiB or more of VRAM**. Every such event costs exam time and is reported as a contention rate.
- **Before you use the GPU:** run `nvidia-smi`. Normal idle state is about 300 MiB used (the desktop). Look at the process list. If an exam run is active (see `tmux ls`: a session named `exam-...`), **do not use the GPU at all** without asking the owner.
- **Outside exam runs:** share fairly, keep to one model at a time, and unload when you finish (`OLLAMA_KEEP_ALIVE=0`, or `ollama stop <model>` on your own server). Never leave a model loaded overnight.
- **Do not run Gazebo with GPU rendering.** The exam's Gazebo runs on the CPU (software rendering, real-time speed 1.0 measured). Do the same.
- **No training or large GPU jobs during exam runs.** The schedule (section 8) says when the exam needs the machine: from Sunday 22 November.
- Say in the team chat when you start and stop a longer GPU job.

## 6. Problem cases: prevention and recovery
Everything of the exam runs **inside tmux on the lab computer**, so what happens to your own connection does not matter to a running exam.

| case | what happens | what to do |
|---|---|---|
| **SSH connection drops** | the exam keeps running (tmux sessions and Docker containers do not depend on your connection). Tested on 2026-11-19: the SSH client was killed mid-run; after 3 minutes the run had progressed and the heartbeat was fresh. | reconnect, `tmux ls`, `tmux attach -t exam-<run name>`. Detach again with Ctrl-b then d. Never press Ctrl-c inside the runner window. |
| **VPN drops** | same as above: the work is on the lab, only your view is lost. Phone notifications still arrive (the lab uses its own internet). | reconnect the VPN, then as above. |
| **The runner crashes** | the monitor sends a notification. Nothing is lost: every finished episode is already written to disk. | start the **same command again**: it kills leftovers of the crashed run, records episodes that finished but were not logged, skips finished cells and continues. Then run the merge check (section 7). |
| **The lab computer reboots or loses power** | all tmux sessions and the exam container stop (the container is not set to restart by itself); the Ollama session stops too. Files on disk are safe. | (1) `bash .../lab/run_container.sh start`; (2) `tmux new -d -s ollama "bash .../lab/ollama_userspace.sh start"`; (3) `bash .../lab/check_integrity.sh`; (4) start the same exam command again. Only the owner or a person the owner names does this during the exam. |
| **GPU contention** (somebody uses the GPU) | the exam slows or part of the model is offloaded to the CPU. The automatic per-episode logging that detects this is designed but **not built yet** (section 8). Until then the check script prints a warning when another process holds 1 GiB or more. | follow section 5. If you find someone else's job during the exam, tell the owner, do not kill it. |
| **Disk space** | `/` (system) has about 19 GB free. The data disk is large. The queue refuses to start under 20 GB free on its disk and warns the owner at 30 GB. | never pull or build Docker images, never `apt install`. Put your files on the data disk. Never delete files of the exam. |
| **Foreign ROS or Gazebo processes** | with host networking all containers share the machine's loopback. Two people on the same ROS domain would see each other's topics and corrupt a test. | use your own domain (100-199) and `ROS_LOCALHOST_ONLY=1`. The integrity check lists running containers and ROS-like processes and fails if another container uses domain 219 or 220. If you see ROS nodes you do not know, stop your test and tell the owner. |
| **Someone changes our files by accident** | the integrity check compares 1,065 files with a recorded hash baseline, the git commit, the image id and size, the model digests, the Ollama version and port, and the folder permissions. It runs read-only. | the owner runs `bash .../lab/check_integrity.sh` before every exam block. If it prints FAIL, **the block does not start** until the cause is understood. |

The integrity script (read-only; it never opens the custodian folder): `bash <LAB_PATH>`. PASS = as recorded, WARN = a human should look (for example somebody else's container is running), FAIL = do not start. You may run it any time.

## 7. How an exam run works (general workflow)
1. **Setup (done on 2026-11-19, see `LAB_SETUP_LOG.md`):** image built, container and Ollama running, eight models with the laptop's digests, 28 + 23 unit tests passed in the container, headless Gazebo/Nav2 passed (speed 1.0 real time, a goal in about 8 s), a dummy queue run survived an SSH disconnect.
2. **Freeze (Saturday 21 November, 24:00):** the exam specification file (which tasks, models, systems, seeds, in which order), the scoring code and the prompts are fixed and their hashes recorded. After the first held-out request nothing about tasks, scorers, prompts or schemas changes, and no result is dropped because it is bad.
3. **Integrity check** on the lab: all PASS (or understood WARN).
4. **Launch in tmux:** the owner starts one command that opens a tmux session `exam-<run name>` with a runner window (inside the exam container) and a monitor window (on the host, sends the phone notifications). Held-out task files are given to the runner only through environment variables that point to the custodian's directory; nobody else handles them.
5. **Order of work (priority tiers, from the runbook):** tier 1 (the main comparison on held-out tasks), tier 2 (other systems and the Nav2 robot pools), tier 3 (ablations), tier 4 (extra seeds and ablations on the robot pools). Any stopping point still leaves complete, comparable pairs.
6. **Monitoring:** `tmux attach -t exam-<run name>` (read only, then Ctrl-b d), or `python3 .../exam_queue/queue_core.py status --run-name <run> --machine lab`. The phone gets a message on finish, crash, no progress for 15 min, Ollama down, low disk, a repeatedly failing block, and a daily summary.
7. **Stop and resume:** to stop politely, create the file `research/_artifacts/exam/<run name>/STOP` (the runner finishes the current episode and exits). To resume, delete it and run the same start command again. Never kill the runner with `kill -9` unless the owner says so.
8. **Results:** every finished episode is one line in `RESULTS_LOG_lab.jsonl` (flushed to disk at once), the raw traces are in the run folder, and compact tables (no task text) are produced by the table script and copied back to the laptop. Afterwards `merge-check` verifies no duplicate, missing or wrong-machine cells. Lab and laptop results are reported as separate groups; both systems of a pair always run on the same machine.
9. **After the exam:** the owner archives the results; only then is our folder removed (the owner decides, nobody else).

## 8. What is still to be done, and when (state at 2026-11-19 22:10)
| item | who | when / dependency |
|---|---|---|
| Make the Ollama address configurable by an environment variable in the scripts (so the lab's `127.0.0.1:11435` is used) and re-freeze those files | Levinson's Claude Code session | after the replication study running on the laptop has finished (expected about 00:30-01:00 on 20 November); the lab monitor currently also sends a false "Ollama down" notice for this reason |
| Held-out adapter for the runners (they only know the development tasks today), tested with a custodian-approved dummy file | Codex with the owner | before the freeze |
| Custodian places the held-out files; checks of counts only | Codex / custodian | before the freeze |
| GPU-state logging per episode and the contention rule (design written, not built) | Levinson's Claude Code session | after the replication; before the first exam episode |
| Memory check of the four models with Gazebo/Nav2 on the lab GPU, then the mini exam on the lab (8 episodes) with episode times | Levinson's Claude Code session | after the Ollama-address change; before Saturday 18:00 |
| Decide which of the four candidate models (`llama3.1:8b`, `ministral-3:8b`, `granite4.2:8b`, `gemma4:e4b`) join the exam. Note: `granite4.2:8b` does not fit fully in VRAM at the long context, and `gemma4:e4b` reports an implausible memory size | the owner | Friday 20 November |
| Check on the phone that the notifications arrive (done for the test message) | the owner | done |
| Lab ready checkpoint | the owner | Saturday 21 November 18:00; if missed, the laptop-only plan applies |
| Freeze | everyone | Saturday 21 November 24:00 |
| Exam runs | the exam machine | from Sunday 22 November 00:00; tier 1 done by Monday 23 12:00, tier 2 by Wednesday 25 12:00, tier 3 by Friday 27 12:00; **hard stop of all runs Monday 30 November 18:00**; tables Tuesday 1 December; presentation Wednesday 2 December |

Known limits you should be aware of: the lab's ROS/Nav2 patch versions differ from the laptop's; a firewall on the lab host blocks connections from bridged containers to the host (which is why our container uses the host network); results from one GPU model and one Ollama setting say nothing about other hardware.

## 9. Who to ask
The owner of the exam setup (Levinson) for anything about the exam, the container, the images and the schedule. The teacher for host settings (firewall, GPU drivers, system packages). When in doubt: do not touch it, ask first.
