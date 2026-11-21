# Lab computer setup checklist: this machine, Docker for ROS (rewritten 2026-11-19, draft)

Owner decision: the exam and other heavy runs go on the lab computer (SSH); the laptop is for dev runs. This version is written for the machine as the owner described it after read-only checks on 2026-11-19. **Nothing here was run on the lab computer by the author; the author only wrote scripts and commands.** Each step has a verify command and says who runs it. The first generic version is kept as `LAB_SETUP_CHECKLIST_v1_generic_20261119.md`.

## The lab machine (facts from the owner, 2026-11-19)
Ubuntu 25.04 (kernel 6.14), RTX 4080 **SUPER** 16 GB (driver 570.195.03, CUDA 12.8; confirmed by `nvidia-smi` on 2026-11-19), 28 cores, 123 GB RAM; no ROS, no Ollama, no uv; python3 3.13, git, tmux 3.6a, Docker 29.6.1 (user in the docker group). **ROS 2 Jazzy has no binary packages for 25.04, so ROS runs in a Docker container (Ubuntu 24.04).** `/` has only **23 GB free and Docker's root (`/var/lib/docker`) is on `/`**; large data goes to **`<LAB_PATH>` (ext4, 434 GB free)**; **never** `/media/<LAB_USER>/Lab_Project1` (exFAT). GPU inside Docker is **not confirmed** (`docker run --gpus all ubuntu nvidia-smi -L` failed: the runtime exists but nvidia-smi was not found in the container). **Shared machine:** we use the teacher's account (`<LAB_USER>`, passwordless sudo); a student (`<STUDENT_ID>`) also uses it. **Update 2026-11-19: the teammate's container `<OTHER_CONTAINER>` and its image were removed at the teammate's request; other users (student `<STUDENT_ID>`, others) remain, do not touch their processes, files or containers.**

## Rules for this setup (apply to every step)
1. **No system-wide change and no `sudo` unless a step is marked `ASK THE TEACHER FIRST`.** Nothing is installed with apt on the host. Everything lives in **one directory, `<LAB_PATH>`**, plus one image and one container of ours.
2. **Docker is shared.** Our names are explicit: image `rosa-exam-jazzy:20261119`, container `rosa-exam-main`. **Never run `docker system prune`, `docker builder prune`, `docker image prune`, `docker container prune`, `docker stop/rm` on anything but our own named container, and never restart the Docker daemon** (it would stop every other container on the host unless live-restore is on; live restore is off).
3. **Check `/` before anything that writes to Docker** (`df -h /`); stop and ask if under 14 GB.
4. **ROS isolation (changed 2026-11-19):** our container uses **host networking** (`--network host`, because the host firewall drops bridge -> host traffic) with `ROS_LOCALHOST_ONLY=1` (DDS on the loopback only) and domain 220 (the study runners hard-code 220, the Nav2 stack 219; the Gazebo transport uses a unique partition per stack). Isolation therefore rests on loopback-only discovery and the domain numbers, not on a separate network namespace: before every run check that no one else runs ROS/Gazebo on the host (`ps -eo user,args | grep -Ei 'ros2|gz sim|component_container'`; our own `ros2-daemon` shows up there too).
5. Be considerate of the GPU and CPUs: check what others use before a long run (`nvidia-smi`, `uptime`); the container is capped (default 16 CPUs, 64 GB RAM; tune with the teacher).
6. Held-out task files never enter the repository, the image or a log; only the custodian directory, mounted read-only.

## GPU sharing and per-episode GPU-state logging (design 2026-11-19; implemented 2026-11-20, see RUNBOOK section 4)
**Problem.** The RTX 4080 SUPER is shared (a desktop process, other users' processes). Another process can take VRAM or compute while an episode runs; Ollama then offloads layers to the CPU or slows down, and the episode's time and sometimes its behaviour change for reasons unrelated to the method. This must be visible and must not silently enter the results.
**Preflight before any GPU step or run (today's baseline: 277 MiB used, 0 % utilisation, only `gnome-remote-desktop-daemon` 249 MiB):** `nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader; nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader`. Go only if used VRAM is below 2 GiB and no other compute process holds 1 GiB or more; otherwise wait or ask the owner. This is a human/operator rule, not an evaluation criterion.
**What is logged (design).**
1. A host-side sampler (standard library only, own tmux session `gpusample`; it runs on the host because the container has no `nvidia-smi`) appends one JSON line every 5 s to `<LAB_PATH>`: timestamp, `memory.used/total`, utilisation, **every compute process (pid, name, used MiB)** from `nvidia-smi --query-compute-apps`, our Ollama's process ids (so our own processes can be told apart from others), Ollama `/api/ps` (model, `size`, `size_vram`) and the load average.
2. The runner (inside the container; the file is on the shared disk) attaches to every episode row a `gpu_state` block built from the samples between the episode's start and end time: first and last sample, minimum free VRAM, maximum VRAM held by processes that are **not ours**, residency `size_vram / size` of the episode's model at start and end, number of samples (0 samples = `gpu_state_unknown`, not contention).
**Contention rule (frozen before the exam, applied independently of the episode's outcome):** an episode is `gpu_contended` if, in its window, (a) a process that is not ours holds 1024 MiB or more, or (b) the episode's model was fully resident (`size_vram == size`) at the start and is not at the end, or (c) free VRAM at the start was below the model's size. The 1 GiB threshold lies above the 249 MiB desktop baseline; it is a design choice to be fixed in the protocol amendment, not a measured optimum.
**Handling.** A contended episode is an **infrastructure failure**: its row stays in the raw log with the flag (never deleted), it does not count as a result, and its cell is retried by the existing retry rule (`ending_class` `infrastructure`, `quarantine_after` tries) after the runner waits until the GPU preflight holds again. Because the rule depends only on the GPU state and never on the answer, retrying cannot select good outcomes.
**Reporting.** A new table in `exam_tables.py` gives contended episodes / started episodes (the **contention frequency**), per machine, model and block, plus the median wall time of contended versus clean episodes. The final report states the frequency and what was retried. A high frequency is itself a finding about running on a shared GPU, not something to hide.
**Limits.** `nvidia-smi` inside a shared container setup may not show the process names of other containers' processes (it shows host pids); the rule therefore uses "not one of our Ollama pids" rather than a name. Sampling every 5 s can miss a burst shorter than 5 s. Compute contention without a VRAM change (a neighbour using the SMs) shows only in utilisation and in slower tokens/s; the logged utilisation lets this be checked after the fact but is not part of the rule.

## Files provided (laptop, `research/studies/final_exam_draft_20261118/lab/`; copied to the lab with the repo)
| file | purpose |
|---|---|
| `Dockerfile` | `ros:jazzy-ros-base` + pinned Nav2, TurtleBot3, Gazebo (gz-sim vendor), ros-gz, turtlesim + Mesa software GL + uv 0.13.2; **no GUI/desktop stack** |
| `versions_laptop.txt`, `compare_versions.sh` | the laptop's `ros-jazzy-*` / gz versions (432 lines) and a script that compares them with the image |
| `build_image.sh` | builds our image (free-space guard, no prune, `--pin0` fallback) |
| `lab_env.sh` | all paths and names in one place (everything under `<LAB_PATH>`) |
| `run_container.sh` | start / stop / status / shell / env-check of our container (`DRY_RUN=1` prints the command) |
| `ollama_userspace.sh`, `ollama_copy_list.py` | Ollama in user space (own port, models on d1) and the list of files to copy the four models with identical digests |
| `check_teammate_isolation.sh` | **read-only** `docker inspect` of the teammate's container to decide whether our ROS settings can clash |
| `../exam_queue/start_exam_tmux.sh` | now supports `EXAM_EXEC="docker exec -it rosa-exam-main bash -lc"` (runner in the container, monitor on the host) |

**Findings of the first real build (2026-11-19):** (1) the lab network cannot reach `archive.ubuntu.com` or `security.ubuntu.com` (timeouts); the Dockerfile now rewrites the Ubuntu apt sources to `http://tw.archive.ubuntu.com/ubuntu` (build arg `UBUNTU_MIRROR`; `packages.ros.org` over http works, https does not). (2) **The ROS apt archive keeps only the newest build of each package, so every pinned version was gone (`Version ... was not found`): the pinned build cannot be reproduced with apt**, and no `snapshots.ros.org` date matches the laptop (snapshots exist for 2026-10-05 and 2026-11-16, the laptop's builds fall between). The image was therefore built with `--pin0` (latest). Result: 5.2 GB, `/` 23 GB -> 16 GB free; version comparison saved as `lab/compare_versions_lab_pin0_20261119.txt`: of 319 shared `ros-jazzy-*` packages 83 are identical, 129 differ only by rebuild stamp, **107 differ in upstream version** (all Nav2 packages 1.3.13 -> 1.3.14, `turtlebot3_navigation2` 2.3.6 -> 2.3.7, `ros_gz` 1.0.24 -> 1.0.25, tf2 0.36.22 -> 0.36.23, `ros2cli`, `fastrtps` 2.14.6 -> 2.14.7, Gazebo vendor libraries gz-physics/rendering/sensors); the compare script prints only the first 60 DIFF lines. Consequence for the exam: lab and laptop use different ROS/Nav2 patch levels, another reason to keep them as separate strata. Base image digest: `ros@sha256:00b8d47a6e6384a2834e3d01fa87ae767876543baa574f2d64a75c04ea33c698` (from the build log; `docker image inspect ros:jazzy-ros-base` finds no tag with the containerd image store).

**Expected image size: about 4-6.5 GB on disk (estimate, not measured): about 1 GB base, 1.5 GB Gazebo, 1 GB Nav2, 0.5 GB TurtleBot3 and ros-gz, 0.4 GB turtlesim with Qt, small tools; target under 8 GB.** Disk plan on d1: models 23.0 GB (the four, measured from the laptop's store), Ollama about 3-5 GB, repo and research about 1 GB, uv cache and `.venv` about 2-3 GB, results: raw traces measured at about 0.22 MB per episode (part A: 160 episodes = 35 MB), so a 10,000-episode exam is about 2-3 GB. **d1 total about 35 GB of the 434 GB.**

## Steps

### 0. Read-only preflight (owner or author's commands, no change)
```
whoami; hostname; lsb_release -ds; uname -r; nproc; free -g | sed -n 2p
nvidia-smi --query-gpu=name,driver_version,memory.used,memory.total,utilization.gpu --format=csv,noheader
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader     # who uses the GPU now
docker --version; docker ps --format '{{.Names}}  {{.Image}}  {{.Status}}'            # list only; leave other users' containers alone
df -h / <LAB_PATH> | cat; tmux -V; python3 --version; uptime
```
Verify: Ubuntu 25.04, one RTX 4080 with 16 GB, our container is `Up` if it was started (the teammate's container `<OTHER_CONTAINER>` existed on 2026-11-19 and was removed that evening), `/` has at least 14 GB free, d1 has about 434 GB free. Write the output into `LAB_SETUP_LOG.md` (below). This is also the **GPU preflight** (see the section on GPU sharing): note the baseline VRAM use and the compute processes of others.

### 1. Our directory on the data disk (no sudo)
```
mkdir -p <LAB_PATH>{repo,ollama,ollama-models,home,uv-cache,logs,custodian} && chmod 700 <LAB_PATH>
stat -f -c %T <LAB_PATH>            # filesystem type
touch <LAB_PATH> && chmod 600 <LAB_PATH> && stat -c %a <LAB_PATH> && rm <LAB_PATH>
```
Verify: the type is `ext2/ext3` (how `stat` names ext4), the chmod round-trips to `600` (exFAT cannot), and all directories exist. Start a log: `echo "$(date -Is) step 1 ok" >> <LAB_PATH>`.

### 2. Repository, research files and held-out exclusions (run on the laptop)
`research/` is Git-excluded here, so rsync the whole checkout, **except** the virtual environment, raw runs and the custodian folder:
```
rsync -az --exclude '.venv/' --exclude 'research/_artifacts/' --exclude 'research/.local/' ~/project/rosa-research/ <LAB_USER>@LABHOST:<LAB_PATH>
```
**The laptop checkout is a Git worktree** (`.git` is a pointer file to a directory that does not exist on the lab). What was done on 2026-11-19: add `--exclude '/.git'` to the rsync above, then `rsync -az --exclude worktrees --exclude index --exclude hooks --exclude HEAD --exclude logs <common-git-dir>/ <LAB_USER>@LABHOST:.../repo/.git/` (the common git dir is `git rev-parse --git-common-dir`, 36 MB), then on the lab `echo 'ref: refs/heads/research/capability-discovery-20261110' > .git/HEAD && git read-tree HEAD`. Never push from the lab. Verify on the lab: `cd <LAB_PATH> && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD` (branch `research/capability-discovery-20261110`, same hash as the laptop), `sha256sum uv.lock | cut -c1-16` -> `dbd8cb6db95ab8f7`, `sha256sum research/studies/residual_failures_20261115/scorer_v2.py` -> `c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9`, `ls research/.local 2>&1` -> no such directory. Re-run the rsync after the prerequisite code changes of step 8.

### 3. Ollama in user space (no sudo, no service)
1. Check the port: `ss -ltn | grep -c 11435` -> `0` (if not 0 pick another: `export ROSA_LAB_PORT=11436`). **Ollama binds to `127.0.0.1:11435` only** (our container uses host networking, so it reaches the loopback; nothing is opened to the lab network or the docker bridge; any local user of the host can still reach it, Ollama has no authentication). The first version bound the docker0 address `172.17.0.1`, which the host firewall blocked for bridged containers.
2. Get the official Linux amd64 release archive of **the laptop's version, 0.40.16** (laptop: `curl -s http://172.30.80.1:11434/api/version` -> `0.40.16`) from the Ollama releases page, plus the release's checksum file; verify the checksum before extracting: the asset is `ollama-linux-amd64.tar.zst` and the lines of `sha256sum.txt` start with `./`, so `grep " ./ollama-linux-amd64.tar.zst$" sha256sum.txt | sha256sum -c` -> `OK` (done 2026-11-19; download on the lab itself with `curl -sSLf`, GitHub is reachable).
3. Install and start (own tmux session, so it survives SSH):
```
source <LAB_PATH>
bash $ROSA_LAB_REPO/research/studies/final_exam_draft_20261118/lab/ollama_userspace.sh install /path/to/ollama-linux-amd64.<tgz|tar.zst>
tmux new -d -s ollama "bash $ROSA_LAB_REPO/research/studies/final_exam_draft_20261118/lab/ollama_userspace.sh start"
sleep 5; bash $ROSA_LAB_REPO/research/studies/final_exam_draft_20261118/lab/ollama_userspace.sh status
```
Verify: `status` prints `{"version":"0.40.16"}` and `{"models":[]}`; `ss -ltnp | grep 11435` shows `127.0.0.1:11435` and our process; `<LAB_PATH>` has no CUDA error and mentions the RTX 4080 (the archive bundles CUDA 12 libraries; the host driver 570 supports 12.8). Ollama is not restarted after a reboot: start it again with the same command.

### 4. The four models with the laptop's digests
Option A (pull; **worked on 2026-11-19, all four digests True, no copy needed**): `OLLAMA_HOST=127.0.0.1:11435 <LAB_PATH> pull lfm3:1.7b` (and `bonsai-2:4b`, `gpt-oss:20b`, `qwen3.5:9b`), if the tags are downloadable. Option B (copy; the laptop's models are at `D:\Ollama_Models`, WSL path `/mnt/d/Ollama_Models`, 4 models = 30 files = 23.0 GB): on the laptop
```
python3 research/studies/final_exam_draft_20261118/lab/ollama_copy_list.py /mnt/d/Ollama_Models > /tmp/ollama_files.txt
rsync -a --files-from=/tmp/ollama_files.txt /mnt/d/Ollama_Models/ <LAB_USER>@LABHOST:<LAB_PATH>
```
(then restart Ollama so it rescans). Verify (**digests must equal ours**): `bash .../lab/ollama_userspace.sh digests` -> `{'lfm3:1.7b': True, 'bonsai-2:4b': True, 'gpt-oss:20b': True, 'qwen3.5:9b': True}` (digests are listed in `thinking_escalation_20261119/FREEZE.json`). **Same digest does not make outputs bit-identical across GPUs** (different hardware and kernels): see step 13.

### 5. Build our image (no sudo; about 10-20 minutes, needs internet)
```
df -h / | tail -1                                         # at least 14 GB free (the script also checks)
bash $ROSA_LAB_REPO/research/studies/final_exam_draft_20261118/lab/build_image.sh      # if a pinned ROS version is gone from the archive: add --pin0
```
Verify: the last lines print `image rosa-exam-jazzy:20261119  size ...` (**expect 4-6.5 GB; report the real number; if above 8 GB stop and tell the owner**) and `free on / after the build` of at least 10 GB. Version check inside the running container (step 6): `docker exec rosa-exam-main bash -lc 'bash <LAB_PATH>'` -> `KEY PACKAGES: all identical` (with `--pin0` record the DIFF lines in the log and tell the owner). Record the base image digest: `docker image inspect ros:jazzy-ros-base --format '{{index .RepoDigests 0}}'` and pin it in the Dockerfile (`BASE_IMAGE=ros@sha256:...`) after the first successful build.

### 6. Container, ROS isolation, mounts
1. **Read-only decision about the teammate (historical; the teammate's container `<OTHER_CONTAINER>` and image `<OTHER_CONTAINER>` were removed on 2026-11-19 at the teammate's request, by name, no prune; `/` went from 16 to 19 GB free):** the container had used network mode `host` and set no ROS_DOMAIN_ID / ROS_LOCALHOST_ONLY. `check_teammate_isolation.sh` is kept for any container another user starts later.
**Decision 2026-11-19 (owner, with the teammate gone): our container runs with `--network host`, Ollama on `127.0.0.1:11435`, `ROS_DOMAIN_ID=220`, `ROS_LOCALHOST_ONLY=1`; no firewall change, no sudo.** History: with a bridged container, `ufw` (active on the host) made Ollama at `172.17.0.1:11435` unreachable from inside (curl timed out; the same URL worked on the host). A Unix-socket relay around the firewall was drafted and deliberately not deployed. Before the switch the host had no other ROS/Gazebo process (only our own `ros2-daemon`).
   **Re-run 2026-11-19 after the switch: PASS.** In the container `curl $ROSA_OLLAMA_URL/api/version` -> `{"version":"0.40.16"}` with `OLLAMA via http://127.0.0.1:11435`; `ros2 node list --no-daemon` empty, `rc=0`; custodian read-only.
2. Start ours: `DRY_RUN=1 bash .../lab/run_container.sh start` (check the printed command), then `bash .../lab/run_container.sh start`.
Verify: `bash .../lab/run_container.sh env-check` prints your numeric user and group, `HOME=<LAB_PATH>`, `ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 ROS_DISTRO=jazzy`, `OLLAMA via http://127.0.0.1:11435`, `uv 0.13.2`, `Python 3.12.x`, `ros2-ok`. Reach Ollama from inside: `docker exec rosa-exam-main bash -lc 'curl -s $ROSA_OLLAMA_URL/api/version'` -> `{"version":"0.40.16"}`. Our ROS graph is empty and separate: `docker exec rosa-exam-main bash -lc 'ros2 node list --no-daemon; echo rc=$?'` -> empty, `rc=0` (on a host network this also shows that no other process of the host is on domain 220). Mount check: `docker exec rosa-exam-main bash -lc 'ls <LAB_PATH> | head -3; test -d <LAB_PATH> && echo custodian-mounted-readonly; touch <LAB_PATH> 2>&1 | tail -1'` -> repo files, `custodian-mounted-readonly`, "Read-only file system".

### 7. uv environment on d1, tests (inside the container)
```
docker exec rosa-exam-main bash -lc 'cd <LAB_PATH> && uv sync --frozen && uv run python -m unittest discover -s research/studies/thinking_escalation_20261119/tests 2>&1 | tail -3'
docker exec rosa-exam-main bash -lc 'cd <LAB_PATH> && uv run python -m unittest discover -s research/studies/final_exam_draft_20261118/exam_queue/tests 2>&1 | tail -3'
```
Verify: `.venv` appears under the repo on d1 (not in the image), both runs end `OK` (28 and 21+ tests; about 2 minutes). `uv` uses the container's system Python 3.12 (no download: `UV_PYTHON_DOWNLOADS=never`), the same minor version as the laptop (3.12.3).

### 8. Prerequisite code changes (laptop; then rsync again; **required before any model run on the lab**)
**Status 2026-11-20: 8a done (commit 7663bf0, 36 queue + 28 thinking tests pass on the laptop); 8b and 8c not done.** The GPU-state logging (section above) was implemented in the same commit.
a. **Ollama address from an environment variable, default unchanged.** The dev scripts hard-code `http://172.30.80.1:11434`. In each file replace the constant by `os.environ.get("ROSA_OLLAMA_URL", "http://172.30.80.1:11434")`: `research/studies/headroom_diagnostic_20261112/run_stage1.py`, `research/studies/headroom_diagnostic_20261112/vendor/menu_run_study.py`, `research/studies/final_exam_draft_20261118/exam_queue/health.py` (`OLLAMA_DEFAULT`), `research/studies/gazebo_nav2_model_memory_20261119/check.py`, `think_probe.py` and `gpt_oss_level_probe.py` (thinking study). **Do not edit while a study is running** (the thinking replication is using these files now); test on the laptop with the default (no variable set: behaviour identical) and with the variable set to the same address; re-record the hashes in the next freeze. Verify: `grep -rn "172.30.80.1" --include=*.py research src | grep -v "environ.get" | grep -v make_freeze` -> no hard-coded use left; on the lab `docker exec rosa-exam-main bash -lc 'cd $ROSA_LAB_REPO && uv run python -c "import sys; sys.path.insert(0, \"research/studies/headroom_diagnostic_20261112\"); import run_stage1 as S; print(S.OLLAMA)"'` -> `http://127.0.0.1:11435` (inside the container with host networking).
b. **Held-out adapter** (does not exist: the dev runners only know the development tasks; the queue already loads a pool's task list from the file named by an environment variable). To be built with Codex's paths and a custodian-approved dummy task file; verify: a runner started with the variable missing stops with the planner's error (tested), and with the dummy file loads and runs one episode.
c. **Only if step 6 found a host-network clash:** make the ROS domain configurable (`run_pilot.DOMAIN`, `stack.py DOMAIN`), default 220 / 219 unchanged; re-test; re-freeze.
d. Re-freeze the files changed in a, b, c in a dated amendment before any exam episode.

### 9. Headless Gazebo, TurtleBot3 and Nav2 in the container, **without GPU first**
Inside the container (the stack script runs the world with `--headless-rendering` and software OpenGL; domain 219, its own Gazebo partition):
```
**Order matters (corrected 2026-11-19):** Nav2's navigation lifecycle manager gives up about 60 s after the stack starts, because the `map -> base_link` transform exists only after `navigate_once.py` has set the initial pose. With the original `sleep 90` before `navigate_once` the goal failed (`planner_server` stayed inactive, `Failed to activate global_costmap ... transform from base_link to map`). Start, wait about 35 s, navigate, and measure the clock afterwards:
```
docker exec rosa-exam-main bash -lc 'cd <LAB_PATH> && uv run --no-project --python /usr/bin/python3 python research/studies/turtlebot3_nav2_smoke_20261116/stack.py start && sleep 35 && export ROS_DOMAIN_ID=219 && time uv run --no-project --python /usr/bin/python3 python research/studies/turtlebot3_nav2_smoke_20261116/navigate_once.py 2>&1 | tail -3'
# real-time factor: two /clock readings with wall timestamps about 30 s apart (RTF = simulated seconds / wall seconds)
```
docker exec rosa-exam-main bash -lc 'cd <LAB_PATH> && uv run --no-project --python /usr/bin/python3 python research/studies/turtlebot3_nav2_smoke_20261116/stack.py stop'
```
**Result 2026-11-19 (software rendering, no GPU): real-time factor 1.001 (46 -> 77 s of clock in 30.96 s wall), `NAVIGATION PASS` in 8.3 s, `STOP PASS remaining []`, container CPU about 1.3 cores, host load unchanged: step 10 is not needed.** Verify: the two `/clock` seconds differ by about 10 or more per 10 wall seconds (**real-time factor = simulated seconds / 10 wall seconds; need at least 0.8**), the goal prints `NAVIGATION PASS` in **at most about 35 s of wall time** (laptop: 9-12 s), and `stop` prints `STOP PASS remaining []`. **If the real-time factor is below 0.5 or the goal takes over about 60 s, software rendering is too slow: go to step 10.** Also check CPU use while it runs (`docker stats --no-stream rosa-exam-main`) and that the host's other users are not slowed (`uptime`).

### 10. Optional: GPU inside Docker (**ASK THE TEACHER FIRST: it changes host configuration**)
Read-only diagnosis first (anyone): `docker info 2>/dev/null | grep -iE "runtimes|default runtime|cdi"; cat /etc/docker/daemon.json 2>&1 | head -20; nvidia-ctk --version; nvidia-ctk cdi list 2>&1 | head; ls /etc/cdi /var/run/cdi 2>&1 | head`. The earlier failure ("nvidia-smi not found in the container") means the nvidia runtime is not wired into the daemon. **2026-11-19 read-only finding: `docker info` already lists CDI devices `nvidia.com/gpu=0`, `nvidia.com/gpu=GPU-...` and `nvidia.com/gpu=all` (spec directories `/etc/cdi`, `/run/cdi`), so a CDI file may already exist; check `ls /etc/cdi /run/cdi` and try `docker run --rm --device nvidia.com/gpu=all ubuntu:24.04 nvidia-smi -L` before asking the teacher for anything.** Not needed so far: step 9 passed without a GPU. Options, in order of least risk:
1. **CDI device (preferred, no daemon restart; Docker 29 supports CDI natively):** the teacher runs `sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml` (writes one file in `/etc/cdi`); then, without `--gpus`: `docker run --rm --device nvidia.com/gpu=all -e NVIDIA_DRIVER_CAPABILITIES=all ubuntu:24.04 nvidia-smi -L` -> lists the RTX 4080. For our container add `ROSA_GPU_ARGS="--device nvidia.com/gpu=all -e NVIDIA_DRIVER_CAPABILITIES=all"` when starting (the script passes it through).
2. `sudo nvidia-ctk runtime configure --runtime=docker` **requires restarting the Docker daemon, which stops every container on the host unless `live-restore` is set. Do not do this without the teacher's explicit agreement and a plan for the teammate's container.**
Verify after enabling: `docker exec rosa-exam-main nvidia-smi -L`; for GPU rendering `docker exec rosa-exam-main bash -lc 'eglinfo 2>/dev/null | grep -i "nvidia" | head -2'` and repeat step 9 with `LIBGL_ALWAYS_SOFTWARE=0`; the real-time factor should rise. Note that the GPU is then shared between Ollama (host) and Gazebo rendering (container): check free VRAM (`nvidia-smi`): the four models need up to about 14-15 GB at context 65536 (gpt-oss:20b is 13.5 GB).

### 11. Held-out access through the custodian (never in the repo)
Codex puts the task files **only** in `<LAB_PATH>` (mode 700, owner `<LAB_USER>`) and names the files; the environment variables the spec expects are set in the container's start command, not in a tracked file (`ROSA_HELDOUT_V2_TASKS`, `ROSA_TURTLESIM_HELDOUT_TASKS`, `ROSA_NAV2_INSPECTION_TASKS`, `ROSA_NAV2_ACTION_TASKS`). Verify (names and counts only, never content): `docker exec rosa-exam-main bash -lc 'for v in ROSA_HELDOUT_V2_TASKS ROSA_NAV2_INSPECTION_TASKS ROSA_NAV2_ACTION_TASKS; do test -f "${!v}" && python3 -c "import json,sys;print(sys.argv[1], len(json.load(open(sys.argv[2]))))" $v "${!v}" || echo "$v MISSING"; done'` -> 76, 24, 10 (the sizes the owner stated); `git -C <LAB_PATH> status --short | grep -ci held` -> 0; `ls <LAB_PATH> 2>&1` -> no such directory.

### 12. Queue runner, notifications, SSH-disconnect test
1. ntfy on the host (Python 3.13, standard library only): `python3 <LAB_PATH> init` (the lab's own random topic in `~/.config/rosa-exam/` of the teacher's account: **this is a shared account, so the file is readable by anyone using `<LAB_USER>`; use a topic that carries status only (it does) and tell the owner**); subscribe in the ntfy app; `python3 .../notify.py test finished` -> arrives on the phone.
2. Notification kinds: `python3 .../trigger_notifications_once.py` -> 7 messages arrive.
3. Dummy run **in the container** with the runner inside and the monitor on the host:
```
# corrected 2026-11-19: the shares must name the machine (`lab lab:1`; `lab all:1` selects ZERO cells and the queue still reports `finished 0 0`),
# and the dummy delay must be passed INTO the container (an exported variable does not reach `docker exec`); 15 s x 30 cells = about 8 minutes
export EXAM_EXEC="docker exec -e DUMMY_DELAY_SECONDS=15 -it rosa-exam-main bash -lc"
bash <LAB_PATH> lab_dummy <LAB_PATH> lab lab:1 -- --dummy
```
Verify: `tmux ls` shows `exam-lab_dummy`; `python3 .../queue_core.py status --run-name lab_dummy --machine lab` (host Python is enough for status) -> `running`, `done` increasing; after about 8 minutes `finished 30 30` and the monitor sent "finished" (the launcher prints no WARNING about the monitor).
3b. **(after the GPU logging is implemented) GPU sampler:** `tmux new -d -s gpusample 'python3 .../exam_queue/gpu_sampler.py'`; verify that `gpu_state.jsonl` gets a line every 5 s and that a dummy episode row carries a `gpu_state` block with `samples > 0`.
4. **SSH-disconnect test:** while it runs (use a fresh dummy run name) note `done`; **close the SSH connection abruptly** (close the terminal window or `kill -9` the local `ssh` process); wait 3 minutes; reconnect: `tmux ls` shows the session, `docker ps --filter name=rosa-exam-main` shows `Up`, `done` is larger, the heartbeat recent. If the tmux session is gone after logout, **ASK THE TEACHER FIRST** about `loginctl enable-linger <LAB_USER>` (a host setting); the container itself is managed by the Docker daemon and survives anyway. Clean up: `touch <LAB_PATH>; tmux kill-session -t exam-lab_dummy`, then remove only `research/_artifacts/exam/lab_dummy` and `research/studies/final_exam_draft_20261118/exam_results/lab_dummy`.

### 13. Memory check and mini exam on the lab (after step 8a)
```
# lab run 2026-11-20: the container has no nvidia-smi, so check.py reads the host sampler (`gpu_state.py sample --seconds 1 --log $ROSA_GPU_STATE_LOG`), writes to $ROSA_CHECK_OUT and waits $ROSA_STACK_WAIT seconds (35) after the stack start
docker exec -e ROSA_CHECK_OUT=<LAB_PATH> -e ROSA_STACK_WAIT=35 -e ROSA_GPU_STATE_LOG=<LAB_PATH> rosa-exam-main bash -lc 'cd <LAB_PATH> && uv run --no-project --python /usr/bin/python3 python research/studies/gazebo_nav2_model_memory_20261119/check.py'
# corrected 2026-11-20: `lab all:1` is now refused by the zero-cell guard; name the machine in the shares (`lab lab:1`); `source lab/lab_env.sh` first so the host monitor knows the Ollama address; start the host GPU sampler first (RUNBOOK section 4)
source .../lab/lab_env.sh; EXAM_EXEC="docker exec -it rosa-exam-main bash -lc" bash .../exam_queue/start_exam_tmux.sh mini_exam_lab $PWD/research/studies/final_exam_draft_20261118/exam_queue/specs/mini_exam_spec.json lab lab:1
```
Also report the **GPU contention frequency** of the mini exam (contended / started episodes, from the `gpu_state` blocks) and the VRAM residency per model. Verify: every model in `gazebo_nav2_model_memory_20261119/results.json` has `failures: []` and `C_navigation_passed: true`; record how much of each model is resident in VRAM (`size_vram_mib`: on the 16 GB card all four may now fit; the laptop's 8 GB card offloads qwen3.5 and gpt-oss) and tokens per second (laptop: lfm3 152.7, bonsai 106.7, qwen3.5 12.1, gpt-oss 24.3). The mini exam ends with `merge-check` 0 duplicates / 0 missing and `exam_tables.py` table 5 gives the lab's episode times; write the ratio to the laptop's (E1 lfm3 29 s, E1 qwen3.5 55 s, M lfm3 23 s, M qwen3.5 33 s median). **Different hardware (GPU, kernels, no CPU offload) will change outputs and timing; the same digest is not the same output.** Consequence for the exam: report the lab and laptop results as separate strata and keep both systems of a pair on one machine (the queue does).

### 14. Two machines and results
Shares set by the owner from the speed ratio (lab primary, for example `--machines lab:0.8,laptop:0.2`). Exchange logs before changing shares (`RUNBOOK.md` section 3); results stay under `<LAB_PATH>`; copy compact tables back with `rsync`.

### 15. Cleanup and teardown (our names only)
`bash .../lab/run_container.sh stop` (stops and removes `rosa-exam-main`), `docker rmi rosa-exam-jazzy:20261119`, `tmux kill-session -t ollama`, then `rm -rf <LAB_PATH>` **only when the owner says the exam data are archived**. No prune commands.

## `LAB_SETUP_LOG.md`
One line per step in `<LAB_PATH>`: date, step, the verify result (pasted), who ran it. A step is done only with its verify result.

## Prerequisites before the first exam episode on the lab (go / no-go)
All of: steps 0-7 and 9 logged with their verify results; image size and version comparison reported; model digests all True; the Ollama-address change (8a) made, tested on the laptop, re-frozen; the held-out adapter (8b) built and tested with a custodian-approved dummy; the ROS-isolation decision (step 6) recorded; the SSH-disconnect test passed; the mini exam finished with 0 duplicates; the memory check without failures; notifications reaching the phone; the frozen exam spec hashed; the GPU-state logging implemented, tested with a dummy run and its contention rule frozen in the protocol amendment; the Ollama-from-container path working (step 6 blocker resolved by the teacher). **Missing any: do not start the exam; report the open step.**

## Open search (noticed while writing this)
- **Docker root on `/` with 23 GB free** is the one hard resource limit; the image build is the largest write there. Nothing in the plan moves Docker's root (that is a system change for the teacher).
- **Shared `<LAB_USER>` account:** anything in `~/.config/rosa-exam/` (the ntfy topic, an optional Gmail app password) is readable by every user of that account (the student too). Prefer no email credentials on the lab; keep ntfy status-only.
- **Ollama has no authentication:** it listens on `127.0.0.1:11435`, so any local user of the lab host (and any host-network container) can use our Ollama and its GPU time.
- **GPU is shared and unmeasured:** other users' processes may use the RTX 4080; check `nvidia-smi` before each long run; a busy GPU changes speed (and, with offload, nothing else).
- **The laptop's Ollama models live on `D:` (`D:\Ollama_Models`), not in `~/.ollama`**; the older generic checklist pointed at the wrong default location.
- **ROS domain 219/220 are hard-coded** in the runners and the stack script; with host networking, isolation relies on `ROS_LOCALHOST_ONLY=1` (loopback only) and on nobody else using those domains on the host, unless step 8c is done.
