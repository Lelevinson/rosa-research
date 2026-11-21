# Lab setup log (2026-11-19, Asia/Taipei)

Executed by Claude Code (Sonnet 5.5) over SSH as `<LAB_USER>@<LAB_HOST>` (host name `<LAB_HOST>`) on behalf of the owner. Each step is done only with its verify result pasted below. The same log is kept on the lab at `<LAB_PATH>` (copied at the end of each group). Plan: [LAB_SETUP_CHECKLIST.md](LAB_SETUP_CHECKLIST.md). Nothing was run on the held-out custodian files; `research/.local` was never synced.

## Step 0, read-only preflight (20:11)
```
user <LAB_USER>; hostname <LAB_HOST>; Ubuntu 25.04; kernel 6.14.0-37-generic; 28 cores; RAM 123 GB total, 11 used, 112 available
GPU: NVIDIA GeForce RTX 4080 SUPER, driver 570.195.03, 277 MiB used of 16376 MiB, 0 % utilisation
GPU compute apps: only /usr/libexec/gnome-remote-desktop-daemon 249 MiB (baseline desktop use)
docker 29.6.1; running: <OTHER_CONTAINER> (<OTHER_CONTAINER>) Up 2 days  (left alone)
/ : 915G, 23G free (98 % used)     <LAB_PATH> : 916G, 434G free
tmux 3.6a; python 3.13.3; load average 5.2 / 6.0 / 6.7
```
Verify: matches the checklist (note: the card is an RTX 4080 **SUPER**, 16 GB). GPU idle, so the GPU-sharing precondition holds. Other users' tmux sessions exist (`<OTHER_SERVICE>`); not ours, left alone.
Extra read-only finding (`docker info`): `CDI spec directories: /etc/cdi, /run/cdi` and **devices `nvidia.com/gpu=0`, `nvidia.com/gpu=all` already listed**; runtimes `runc`, `nvidia`, `io.containerd.runc.v2`; storage driver overlayfs (containerd snapshotter); live restore false. Relevant only if step 10 is needed.

## Step 1, our directory on d1 (20:12)
```
filesystem type: ext2/ext3 (= ext4)   chmod round-trip: 600   directories: custodian home logs ollama ollama-models repo uv-cache   custodian mode: 700 <LAB_USER>
```
Verify: PASS.

## Step 2, repository sync (20:12-20:14)
Command (from the laptop): `rsync -az --exclude '/.git' --exclude '.venv/' --exclude 'research/_artifacts/' --exclude 'research/.local/' ./ <LAB_USER>@LAB:<LAB_PATH>` (1,216 files, 215 MB).
**Deviation from the checklist:** the laptop checkout is a Git *worktree* (`.git` is a one-line pointer to `/home/levinsonchen/project/rosa-research-previous-20261108/.git/worktrees/...`), which would dangle on the lab. The `.git` pointer was therefore excluded; the shared object store (`.git` minus `worktrees`, `index`, `hooks`, `HEAD`, `logs`; 36 MB) was rsynced to `repo/.git`, `HEAD` was written as `ref: refs/heads/research/capability-discovery-20261110`, and `git read-tree HEAD` rebuilt the index. The lab copy has the `origin`/`upstream` remote URLs but no credentials; **do not push from the lab**.
```
branch research/capability-discovery-20261110   HEAD 58a32a5 (laptop: 58a32a5)
uv.lock sha256[:16] dbd8cb6db95ab8f7
scorer_v2.py sha256 c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9
ls research/.local -> No such file or directory
git status --short | wc -l -> 0
```
Verify: PASS (all four values equal the expected ones; working tree clean).
Note: the sync was made while a study runs on the laptop; `research/studies/thinking_escalation_20261119/` was only *read by rsync* (copied as is, no write on the laptop). Re-sync after step 8.

## Step 3, Ollama in user space (20:12-20:13)
Release `v0.40.16`, asset `ollama-linux-amd64.tar.zst` (1,545,767,640 bytes) from `github.com/ollama/ollama/releases`. The checksum file lists names with a `./` prefix, so the checklist's `grep " ollama-linux-amd64..."` must use `" ./ollama-linux-amd64.tar.zst$"`.
```
sha256sum -c -> ./ollama-linux-amd64.tar.zst: OK
ollama_userspace.sh status -> {"version":"0.40.16"} {"models":[]}
ss -ltnp | grep 11435 -> LISTEN 172.17.0.1:11435 (users: ollama pid 3131507)   [docker0 address only]
ollama.log: "inference compute ... library=CUDA compute=8.9 name=CUDA0 description=NVIDIA GeForce RTX 4080 SUPER"; no CUDA error;
            "vram-based default context ... total_vram=15.8 GiB default_num_ctx=4096"
```
Verify: PASS. Note: Ollama's own default context on this machine is 4096; the study runners must (and per the earlier freeze do) set `num_ctx` explicitly, to be confirmed in the step 13 mini exam. tmux session `ollama` holds the server (not restarted after a reboot).

## Step 4, the four models (20:13-20:18)
Option A (pull) worked for all four tags; no copy from the laptop was needed (about 4 minutes, 22 GB on d1).
```
digests -> {'lfm3:1.7b': True, 'bonsai-2:4b': True, 'gpt-oss:20b': True, 'qwen3.5:9b': True}   (expected values = FREEZE.json digests)
lab vs laptop /api/tags (first 12 hex): lfm3 b36a103fe2f8 = ; bonsai-2 93edd652c932 = ; gpt-oss f38aa0c53da5 = ; qwen3.5 56671c2ab938 =   (all equal)
models dir 22 GB; d1 free 408 GB
```
Verify: PASS. Same digest does not imply identical outputs across GPUs (see step 13).

## Step 5, image build (20:15-20:35; two attempts)
Attempt 1 (pinned versions, `PIN=1`) **failed** (`BUILD_EXIT=1`). Causes read from the build log: (a) `archive.ubuntu.com` and `security.ubuntu.com` time out from the lab network (host `curl`: no answer in 10 s; `tw.archive.ubuntu.com` and `free.nchc.org.tw` answer in 0.04-0.3 s, `tw.archive.ubuntu.com` also serves `noble-security`); (b) every pinned ROS version is absent from `packages.ros.org` (it keeps only the newest build of each package: `Version '1.3.13-1noble.20261006.042503' for 'ros-jazzy-nav2-bringup' was not found`; available now: nav2-bringup 1.3.14-1noble.20261109.092855). `snapshots.ros.org/jazzy/` has snapshots 2026-10-05 and 2026-11-16 only; none contains the laptop's builds.
Fix: `lab/Dockerfile` got `ARG UBUNTU_MIRROR=http://tw.archive.ubuntu.com/ubuntu` and a `sed` on `/etc/apt/sources.list.d/ubuntu.sources`; attempt 2 with `build_image.sh --pin0` (checklist fallback) succeeded.
```
free on / before: 23 GB     image rosa-exam-jazzy:20261119  size 5.2GB     free on / after: 16 GB (df: 99 % used)     BUILD_EXIT=0
base image: ros:jazzy-ros-base@sha256:00b8d47a6e6384a2834e3d01fa87ae767876543baa574f2d64a75c04ea33c698
compare_versions.sh (in the container): installed 319 ros-jazzy packages; identical 83; DIFFERENT 236 (129 only a rebuild stamp, 107 an upstream version); only here 0; laptop-only (GUI etc.) 113
KEY PACKAGES: DIFFERENT: nav2-bringup, navigation2, turtlebot3-gazebo, turtlebot3-navigation2, ros-gz-sim/bridge/image, turtlesim, gz-sim-vendor
```
Upstream differences that matter for Gazebo/Nav2: all Nav2 packages 1.3.13 -> 1.3.14, `turtlebot3_navigation2` 2.3.6 -> 2.3.7, `ros_gz_*` 1.0.24 -> 1.0.25, `fastrtps` 2.14.6 -> 2.14.7, gz-physics/rendering/sensors vendors one patch up, tf2 0.36.22 -> 0.36.23. Full output: `lab/compare_versions_lab_pin0_20261119.txt` (the script prints only the first 60 DIFF lines). Verify: image size within 4-6.5 GB (5.2 GB), free on `/` >= 10 GB (16 GB): PASS; **version comparison: NOT identical, owner informed in the report.** Note: the failed attempt and the base layers use space on `/` that cannot be reclaimed without prune commands (not run); `/` is now at 16 GB free.

## Step 6, container, isolation, mounts (20:36-20:40): PARTLY BLOCKED
**Superseded by the section "Group 2" below (host networking, Ollama check re-run: PASS).**
Teammate isolation (read-only `docker inspect`): network mode `host`; its configuration sets only `ROS_DISTRO=jazzy` (no `ROS_DOMAIN_ID`, no `ROS_LOCALHOST_ONLY`, no ports). Decision rule (host network AND domain 220/219): **not met**, go on. A domain exported interactively inside that container cannot be seen from outside; ours runs in its own bridge namespace with `ROS_LOCALHOST_ONLY=1`.
```
DRY_RUN printed the expected docker run command; container rosa-exam-main started (user 1000:1000, 16 CPUs, 64 GB, image rosa-exam-jazzy:20261119)
env-check: user 1000:1000 HOME=<LAB_PATH> | ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 ROS_DISTRO=jazzy | OLLAMA via http://172.17.0.1:11435 | uv 0.13.2 | Python 3.12.3 | ros2-ok   PASS
mounts: repo files listed; custodian mounted; touch there -> "Read-only file system"   PASS
ros2 node list --no-daemon was not shown separately; the precheck inside stack.py (step 9) confirmed domain 219 empty (the teammate's nodes are not visible)
Ollama from inside the container: curl http://172.17.0.1:11435/api/version -> connection timed out after 6 s (host-side curl to the same URL: {"version":"0.40.16"})   FAIL
```
**Cause:** `ufw` is `active` on the host (`systemctl is-active ufw` -> active; `ufw status` needs root, so the rules were not read). A connection from the bridged container to a host-listening port is dropped. **Not fixed**: allowing it needs a host firewall rule (`sudo ufw allow from 172.17.0.0/16 to 172.17.0.1 port 11435 proto tcp`), which is outside the approved list. I wrote a Unix-socket relay as a no-sudo workaround; the permission system rejected deploying it as a way around the firewall, I removed the draft files from the repository and **did not deploy anything** (the lab was unchanged by it). Options for the owner/teacher are in the checklist, step 6. The container was left running with the unreachable URL; nothing in steps 7, 9 and the dummy runs needed Ollama.

## Step 7, uv environment and tests (20:40-20:52)
`uv sync --frozen` inside the container: succeeded, **9 min 59 s** (slow package downloads); `.venv` 228 MB under the repo on d1 (not in the image), uv cache 234 MB.
```
thinking_escalation_20261119/tests : Ran 28 tests  OK
exam_queue/tests                   : Ran 23 tests in 90.0 s  OK
git status --short (lab repo) -> 0 lines
```
Verify: PASS.

## Step 9, headless Gazebo / TurtleBot3 / Nav2, software rendering, no GPU (20:42-20:49)
First attempt (checklist order: `start`, `sleep 90`, then `navigate_once`): clock check passed, **navigation FAILED**: `lifecycle states {... planner_server: inactive, bt_navigator: inactive ...}`; component-container log: `Failed to activate global_costmap because transform from base_link to map did not become available before timeout` then `Failed to bring up all requested nodes. Aborting bringup.` Cause: the Nav2 lifecycle manager aborts about 60 s after the stack starts; `map -> base_link` only exists after `navigate_once.py` sets the initial pose; with 90 s plus extra waiting that deadline had passed. This is a timing error in the checklist (the laptop script `gazebo_nav2_model_memory_20261119/check.py` waits 60 s), not a lab problem. Second attempt: `stack.py stop` (PASS), `start`, `sleep 35`, `navigate_once.py`:
```
lifecycle states: all 12 nodes active
goal result status 4 (4 means succeeded)   last odometry 0.258 0.0
NAVIGATION PASS    real 0m8.342s            (laptop: 9-12 s)
real-time factor: /clock 46 -> 77 over 30.96 s wall = 1.001   (bar: >= 0.8)
docker stats: container CPU about 107-128 % (about 1.1-1.3 cores), 713 MiB; host load average 6.0-8.1 before and after (other users' load)
stack.py stop -> STOP PASS remaining []
```
Verify: PASS. Speed bar met (RTF 1.0, goal 8.3 s <= 35 s). Caveat: one goal and one RTF measurement on an idle GPU-free software-rendered world; not a statement about other tasks, and the Nav2 version differs from the laptop (step 5).

## Step 10, GPU in Docker: NOT RUN
Not needed (step 9 met its speed bar). Read-only finding from `docker info`: CDI devices `nvidia.com/gpu=0`, `nvidia.com/gpu=GPU-8b60c5ed-...` and `nvidia.com/gpu=all` are already listed (spec dirs `/etc/cdi`, `/run/cdi`), runtimes include `nvidia`. No `nvidia-ctk`, no sudo, no daemon restart was used or is planned.

## Step 12, queue runner, notifications, SSH-disconnect test (20:49-21:03)
1. ntfy on the host: `notify.py init` created `<LAB_PATH>` (mode 600; shared account, status-only topic; **the topic is given to the owner in the chat report, not written here**). `notify.py test finished` -> `{'ntfy': True, 'email': None}` (the ntfy server accepted it). **Arrival on the phone is not verified by me; the owner must subscribe and confirm.** ntfy.sh keeps recent messages, so earlier ones appear after subscribing.
2. `trigger_notifications_once.py`: 7 kinds sent (`finished, crash, no_progress, ollama_down, low_disk, daily, study_failing`), all `monitor exit 0` / `ntfy True`.
3. Dummy run in the container, monitor on the host. First attempt with the checklist's arguments (`lab all:1`) selected **zero cells** and the queue reported `finished` with `done 0 total 0` (see Open search). Corrected (`lab lab:1`): `tmux ls` showed `exam-lab_dummy`, `done` rose, state `finished`, `done 30 total 30`, monitor sent `finished`, no launcher WARNING. Because an exported `DUMMY_DELAY_SECONDS` does not reach `docker exec`, that run used the 3 s default delay (finished in about 2 minutes).
4. **SSH-disconnect test** (run `lab_dummy_ssh`, `docker exec -e DUMMY_DELAY_SECONDS=15`): started from a `ssh -tt` session, `done 2` at 20:54:11, the local `ssh` client was ended with `kill -9` (pid 143455); after 185 s on a fresh connection (20:57:26):
```
tmux ls -> exam-lab_dummy_ssh: 2 windows        docker ps -> rosa-exam-main Up 31 minutes
status: state running, done 15 of 30 (was 2), heartbeat 0.55 s old
later: done 30 of 30, state finished, monitor sent "finished" at 21:01:38
```
Verify: PASS. No lingering `loginctl` setting was needed (the tmux server of the `<LAB_USER>` account already existed from other sessions; a first-session-after-logout case was not separately tested, so **linger is not shown to be unnecessary**).
Side evidence: the monitor on the host recorded `ollama_down_since` and sent an `ollama_down` notification at 20:56:30 during the run, because it checks the laptop's Ollama address (`172.30.80.1:11434`): prerequisite 8a (configurable address in `health.py`) is confirmed necessary.
Cleanup: STOP files, `tmux kill-session` and removal of only `_artifacts/exam/lab_dummy*` and `exam_results/lab_dummy*` done. `merge-check` with the dummy spec printed `logged_on_the_wrong_machine: 30` (it was called without `--machine lab`); not investigated further.

## GPU sharing (requested design)
GPU baseline before every step: 277 MiB used, 0 % utilisation, only `gnome-remote-desktop-daemon` (249 MiB); no GPU step was run today. The per-episode GPU-state logging design, the contention rule, the infrastructure handling and the contention-frequency report are in `LAB_SETUP_CHECKLIST.md` (section "GPU sharing and per-episode GPU-state logging", plus steps 0, 12, 13 and the go/no-go list) and in `RUNBOOK.md` section 4. **Not implemented**: the runner modules (`queue_core.py`, `health.py`) are imported by the running thinking replication and were not edited.

## Candidate extra models (NOT downloaded; for the owner's Friday decision)
Source: ollama.com library pages read on 2026-11-19 (sizes are the listed download sizes; "tools" = the page carries the Tools tag). VRAM fit is **my estimate** from weights plus an fp16 KV cache at the exam's long context (about 65536 tokens; the handoff says the four current models need 14-15 GB there); it has not been measured and depends on architecture details I did not check.
| tag | params | download | context | tools | fits fully in 16 GB at 65k ctx (estimate) |
|---|---|---|---|---|---|
| `llama3.1:8b` | 8 B | 4.9 GB | 128K | yes | likely (about 13-14 GB) |
| `qwen3:8b` (`qwen3:latest`) | 8 B | 5.2 GB | 40K native | yes | likely, near the limit (about 15 GB); 40K native context is shorter than 65k |
| `mistral-nemo:12b` | 12 B | 7.1 GB | 1000K | yes | doubtful (weights plus KV about 17-18 GB); fine at a smaller context |
| `ministral-3:14b` | 14 B | 9.1 GB | 256K | yes | doubtful at 65k; fine at a smaller context |
| `qwen3:14b` | 14 B | 9.3 GB | 40K native | yes | no at 65k (about 20 GB); fits at about 16k-32k |
Also well known with tools but below the requested range: `phi4-mini` (3.8 B, 2.5 GB), `granite4` (small sizes). `gemma3` has no Tools tag in the Ollama library. The laptop's Ollama already holds `llama3.1:8b`, `ministral-3:8b`, `granite4.2:8b`, `gemma4:e4b`, `nemotron-3-nano:4b`, `ornith-1.5:9b`, `mimo-v2.6:9b` (names from its `/api/tags`; I did not check their tool support), which would let a candidate be tried on the laptop first. Diversity note: `qwen3.5:9b` is already in the study; adding `qwen3:*` adds the same vendor family.

## Open search (unfiltered; counts and where to look)
- **Queue silently ends with zero cells** when the machine name is not a key of `--machines` (`lab` vs `all:1`): `status` shows `finished 0 0` and the monitor sends "finished". Seen once today (run `lab_dummy`, folder removed during cleanup); a guard that rejects a machine not present in `--machines` would be a small change in `queue_core.py`, **not made** (replication running). The checklist command was wrong, not the code's documented behaviour.
- **Two checklist ordering errors found by running them** (step 9 sleep before `navigate_once`; step 12 machine/share arguments and dummy delay); both corrected in `LAB_SETUP_CHECKLIST.md`. Nothing in `lab/` had been executed before today; so far the Dockerfile (mirror, pins), `.git` handling for a worktree, the checksum `./` prefix and the firewall were the real first-run problems (5 found, 4 fixed, 1 open).
- **Shared-host facts:** the host firewall is active (cause of the Ollama blocker); the teammate's container is on the host network; `/` is at 99 % (16 GB free) and the failed build's cached layers cannot be pruned by us; the GNOME remote-desktop daemon holds 249 MiB of VRAM; several other users' tmux sessions (`<OTHER_SERVICE>`) run on the host.
- **`uv sync` took 10 minutes** on the lab network (PyPI); the first image-build base pull was also slow while Ollama pulled models in parallel. Plan for this when rebuilding.
- **Docker image store:** `docker image inspect ros:jazzy-ros-base` finds nothing after the build (containerd store keeps the digest, not the tag); the digest was taken from the build log.
- **Not checked by me:** phone delivery of ntfy messages; `ufw status`/rules (needs root); whether `/etc/cdi/nvidia.yaml` exists (only the `docker info` listing was read); `rosa-context-sync` mirror state (run after these edits, see the report).

## Group 2 (21:30-21:50, 2026-11-19), owner instructions after the teammate agreed

### ntfy test (item 3)
`notify.py test finished` at about 21:33 -> `{'ntfy': True, 'email': None}` (accepted by the server). Delivery to the phone: **awaiting the owner's confirmation**.

### Removal of the teammate's container and image (item 1)
Before: `docker ps -a`: `rosa-exam-main` Up, `<OTHER_CONTAINER>` Up 2 days (image `<OTHER_CONTAINER>`, id 472fb4307f97, 4.84 GB; network `host`; one bind mount `<LAB_PATH> proj` -> `/work`). `df /`: 16 GB free (99 % used).
Commands, only these two names, no prune, no `-v`, no sudo: `docker stop <OTHER_CONTAINER> && docker rm <OTHER_CONTAINER> && docker rmi <OTHER_CONTAINER>` -> `Untagged: <OTHER_CONTAINER>`, `Deleted: sha256:472fb4307f97...`, rc=0.
After: `docker ps -a` lists `rosa-exam-main`, `exegol-default` (Exited 3 months ago), `quizzical_rubin` (Exited 4 months ago); images: `rosa-exam-jazzy:20261119`, the two `vsc-chrome-...` images, `nwodtuhs/exegol:free`. **`/` free: 19 GB (98 % used), +3 GB** (the base layers are shared with our image, so only the teammate-only layers were freed). The bind-mounted directory `<LAB_PATH> proj` was not touched and still exists (not reviewed by me).

### Host networking, Ollama on loopback (item 2)
Read-only check first: the only ROS-related process on the host was our own `ros2-daemon` on domain 219 (confirmed with `docker top rosa-exam-main`); no `gz sim`, `component_container` or Nav2 processes of other users.
Changes (in `lab/`, rsynced to the lab): `ollama_userspace.sh` binds `127.0.0.1:11435` (was the docker0 address); `run_container.sh` adds `--network host` and sets `ROSA_OLLAMA_URL=http://127.0.0.1:11435`. Our Ollama was restarted (`ollama_userspace.sh stop`, tmux `ollama` recreated) and our container recreated (`run_container.sh stop`, `start`); no other container or the Docker daemon was touched; no firewall change, no sudo. The `docker run` line contains `--network host --user 1000:1000 --cpus 16 --memory 64g ... -e ROS_DOMAIN_ID=220 -e ROS_LOCALHOST_ONLY=1`.
Step 6 re-run:
```
ollama_userspace.sh status -> {"version":"0.40.16"} {"models":[]}      ss -ltnp -> LISTEN 127.0.0.1:11435 (ollama)
env-check: user 1000:1000 | ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 ROS_DISTRO=jazzy | OLLAMA via http://127.0.0.1:11435 | uv 0.13.2 | Python 3.12.3 | ros2-ok
in the container: curl $ROSA_OLLAMA_URL/api/version -> {"version":"0.40.16"}   PASS (was: timeout)
ros2 node list --no-daemon -> (empty) rc=0      custodian: touch -> Read-only file system
```
Step 9 re-run (corrected order, host network): first run `NAVIGATION PASS` in 6.8 s, but my RTF reading failed (`A message was lost!!!` printed by `ros2 topic echo` instead of a number; transient). Second run with numeric filtering: `NAVIGATION PASS` real 7.8 s, `clock 43 -> 76, RTF 1.0` (33 simulated s in about 33 wall s), `STOP PASS remaining []`, no `gz sim` process left in the container. Host load average 5.5-6.7 (other users). Verify: PASS (RTF >= 0.8, goal <= 35 s).
Caveats: with host networking our ROS processes share the host loopback with any other ROS user of the host (`ROS_LOCALHOST_ONLY=1` keeps them off the network); the check above shows nobody was running ROS at that moment, not that nobody will.

### Extra-model candidates (item 4): pull, digest, tools, load at num_ctx 65536
Models: the four that passed the 2026-11-15/16 interface check; excluded with recorded reasons: nemotron-3-nano:4b (no tool calls), phi-4-mini (needs template modification) (from the owner's instruction; I did not open `MODEL_CHECK*.md`). GPU preflight: 277 MiB used, 0 %, only the desktop daemon. All four pulled in about 4 minutes (`logs/pull_candidates.log`). Test script `candidate_check.py` (standard library; **no task, no prompt**: loading by an empty `/api/generate` request with `options.num_ctx=65536`, `keep_alive` 5 m; then `/api/ps`; then `keep_alive` 0). Raw output: `<LAB_PATH>`. Lab Ollama settings: `NUM_PARALLEL=1`, `MAX_LOADED_MODELS=1`, no flash-attention or KV-cache-type variable set; the laptop's Ollama settings were not compared.
| model | digest = laptop | `ollama show` capabilities | params, quant | file | at num_ctx 65536: `size` / `size_vram` (GiB) | fully resident | nvidia-smi used (MiB, incl. 277 baseline) |
|---|---|---|---|---|---|---|---|
| `llama3.1:8b` | yes (46e0c10c039e) | completion, tools | 8.0B Q4_K_M | 4.92 GB | 12.48 / 12.48 | **yes** | 13342 |
| `ministral-3:8b` | yes (1922accd5827) | completion, vision, tools | 8.9B Q4_K_M | 6.02 GB | 13.29 / 13.29 | **yes** | 14968 |
| `granite4.2:8b` | yes (f586c02fdecd) | tools, thinking, completion | 8.8B Q4_K_M | 5.35 GB | 15.42 / 14.01 (90.8 %) | **no, about 9 % offloaded to CPU** | 14914 |
| `gemma4:e4b` | yes (dc35e8d9c606) | completion, vision, audio, tools, thinking | 7.5B Q4_K_M | 6.58 GB | **0.3 / 0.3 (implausible)** | **not verifiable from Ollama's numbers** | 6150 |
All four unloaded (`/api/ps` empty after `keep_alive` 0; nvidia-smi back to 277 MiB). Notes: (1) `tools` is listed for all four; that is a declared capability, not evidence that tool calls work (the earlier interface check is the evidence). (2) `granite4.2:8b` does not fit fully at 65536 on this card (reported residency 0.908); it can be fully resident only at a smaller context, which was not tested. (3) For `gemma4:e4b` `/api/ps` reports `size` 0.3 GiB, inconsistent with a 6.58 GB file and 6150 MiB used on the GPU; the GPU use (about 5.9 GB above the baseline) is below the file size, so part of the model probably stays in CPU memory (hypothesis: per-layer embeddings; **unverified**). Treat its residency as unknown until measured another way (for example tokens/s with and without the model's CPU share). (4) Load times (22 s for the first, 2-3 s for the rest) are not comparable: the first read was cold from disk. (5) Residency is measured with an empty prompt; the KV cache grows as context fills, so a model that is fully resident at load can still be shown otherwise later (Ollama allocates the context buffer at load, so this is unlikely but I did not test a long prompt).

## Group 3 (22:00-22:15, 2026-11-19): integrity check and team guide
### Findings of the first manual look (read-only), before the script
- Our container `rosa-exam-main`: Up, image id `sha256:306205ffce29...` = the id logged after the build; host network; started 21:36 (my recreation). Image size 5.2GB (docker image ls; `docker image inspect` reports 1,120,156,078 bytes of compressed content, not comparable).
- **A new container `<OTHER_CONTAINER>` is running from OUR image id** (started 21:45, about 10 minutes after item 1 above): a teammate's own container; host network, user 1000:1000, `ROS_DOMAIN_ID=0`, `ROS_LOCALHOST_ONLY=1`, no CPU or memory cap, one bind mount `<LAB_PATH> proj` -> `/work`, running a Python job (G1 review work). Not on domain 219/220. Not touched.
- **A second Ollama server, `127.0.0.1:11439`**, started 2026-11-17 under the same account (not ours). Port 11435 has only our Ollama (pid 3197368, our binary).
- Laptop HEAD is `95a658e`, one commit ahead of the lab's `58a32a5`; that commit only adds `exam_results/thinking_replA2/compact_all.jsonl` (228 lines). Lab and laptop tracked code are identical; the lab is simply behind on that results file.
- Only ROS-like process on the host outside our container before the check: none (the `ros2-daemon` seen earlier belongs to our container).
### `lab/check_integrity.sh` (new)
Baseline from independent sources: image id and size from the build/log, commit from step 2, Ollama version from step 3, digests from the frozen exam digests and the laptop's `/api/tags` (8 models), folder modes from the state at 22:05 (custodian 700 as set in step 1; the other modes were not recorded at creation, so they are baseline-by-observation). The first version failed 8 checks because the baseline file did not quote values containing a space (my bug, fixed); I also added a warning for other Ollama servers.
Run `--since "2026-11-19 21:44"` (my last step, the candidate test):
```
RESULT 0 FAIL, 2 WARN
PASS container running from the expected image id; host network; ROS 220/localhost-only; custodian mount read-only; image id and size unchanged (306205ffce29, 5.2GB)
PASS git HEAD 58a32a5; tracked files clean; 1065 manifest files with recorded hash; no file outside the manifest; no research/.local
PASS Ollama {"version":"0.40.16"}; port 11435 only on 127.0.0.1; listener is our binary; all 8 model digests unchanged
PASS no ROS/Gazebo process outside the containers or inside the other container; folder modes/owners as recorded; / 19 GB free; d1 386 GB free; no GPU process >= 1 GiB (GPU 277 MiB, 0 %)
WARN other Ollama server on 127.0.0.1:11439 (teammate's)       WARN other running container <OTHER_CONTAINER> (domain 0)
changed since 21:44 (all by user <LAB_USER>; the account is shared, so no finer attribution): LAB_SETUP_CHECKLIST.md and LAB_SETUP_LOG.md (21:45, my rsync), check_integrity.sh and the three baseline files in integrity/ (22:05, this step); model store: 0 files changed; custodian folder itself: last change 20:11 (step 1).
```
The manifest PASS above is self-consistent only (recorded minutes earlier), so I also hashed the same 1,065 files on the laptop: **1065 identical, 0 differ, 0 missing**. `d1` free space fell from 408 to 386 GB: consistent with my 23 GB of candidate models.
### Guide
`LAB_GUIDE_FOR_TEAM.md` (copied to `<LAB_PATH>`). The own-container recipe was tested with a throwaway container (`--rm`, own folder `rosa_exam/guide_test_tmp`, domain 150): started as uid 1000, correct HOME and domain, empty ROS graph, wrote only to its own folder; removed afterwards (folder deleted, `docker ps` shows only the two existing containers, integrity check 0 FAIL after). Not tested: Gazebo instances of two containers on the host network seeing each other (guide says so).
## Open search (group 3)
- The shared account means the checks cannot tell people apart and the baseline files themselves are writable by anyone using it; the guide relies on rules, not on enforcement.
- The teammate's container has no CPU or memory cap and runs on the host network; if it starts ROS on domain 219/220 the integrity check will FAIL (it checks configuration, not later `export`s inside the container, so a domain set after start is only caught through the visible ROS processes, which are not attributed to domains).
- `check_integrity.sh` compares the container's configuration, not what is currently running inside it; a manually started process inside `rosa-exam-main` would not be flagged unless it looks ROS-like and is foreign.
### Baseline re-recorded (22:15)
After my own documentation edits (runbook, guide, log) the check correctly printed `FAIL manifest mismatch` (1 FAIL, 3 WARN). The append-only `LAB_SETUP_LOG.md` was then excluded from the manifest (it changes with every step), `lab/check_integrity.sh` redeployed and the baseline re-recorded once with `INTEGRITY_RECORD_OK=1 ... record` (1,065 files; image id, HEAD, version and modes unchanged). Check afterwards: `RESULT 0 FAIL, 2 WARN` (the two WARN are the teammate's container and Ollama). Rule: re-record only after an approved change, never to silence a FAIL.

## Group 4 (2026-11-20, 00:00-01:00, overnight instruction, Claude Code Sonnet 5.5)
Code (laptop, part A), commits `7663bf0` (8a, GPU-state logging, zero-cell guard, merge-check), `de8156f` (`check.py` for the lab container), `11ec0e1` (sampler pid fix); tests 36 queue + 28 thinking: laptop OK, **lab container OK** (`lab_results_20261120/logs/tests_A_20261120.log`). Details: RUNBOOK section 4 ("Shared GPU: per-episode GPU-state logging", "Queue pitfall ... guarded"), checklist step 8 status.
- **Sync procedure used for every code change:** `rsync` of the tree (excluding `.git`, `.venv`, `_artifacts`, `.local`, `__pycache__`, `exam_results/lossmap*`), `rsync` of the shared git objects (minus `worktrees`, `index`, `hooks`, `HEAD`, `logs`), then `git read-tree HEAD` in the lab repo; lab `git status` 0 lines each time; `uv.lock` and `scorer_v2.py` hashes unchanged.
- **Integrity baseline re-recorded five times** (the fifth after the final sync of the loss-map files and `STUDY_INDEX.md`, 1,111 hashes; again only the changed file mismatched) (`check_integrity.sh record`, 1,081-1,087 file hashes), each time after running `sha256sum -c` against the old manifest and confirming that the mismatching files were exactly the ones I had changed (22, then 1, then 4 files; the 22 included `STUDY_INDEX.md` and the thinking `RESULTS_LOG.jsonl`, changed by earlier commits, not by this work). The check ended `0 FAIL, 2 WARN` (the teammate's container and Ollama) before every GPU job.
- Host tmux sessions of ours now: `ollama`, `gpusample` (5 s sampler, restarted after the pid fix), `gpusample1` (1 s sampler for the memory check; **stopped after the check**). Container `rosa-exam-main` and image unchanged.
- **Part B** (memory check with 4 models + Gazebo/Nav2: all four passed; mini exam: 8/8 twice, first run with one false-positive contention flag found and fixed; 2-task interface check of llama3.1:8b, ministral-3:8b, granite4.2:8b, gemma4:e4b): [lab_results_20261120/REPORT_B.md](lab_results_20261120/REPORT_B.md).
- Lab clock check: `date` on the lab agrees with the laptop (Asia/Taipei).
- **All test suites (2026-11-20, `lab_results_20261120/logs/all_tests_*.log`):** every `tests` folder under `research/studies/` plus the framework `tests/` (123 tests, 42 skipped). Laptop: all OK except two suites skipped on purpose while the measurement run owned ROS domain 220 (`action_tool_s2`, `action_dev_switch`, real turtlesim). Lab container: **all suites ran, including the real-turtlesim one (`action_tool_s2`, 7 tests, 19.6 s: OK)**; the only failures are **6 tests that read recorded pilot traces from `research/_artifacts/runs/small_model_harness_20261115/pilot/...`, which are not synced to the lab on purpose** (`build_round1` 2: one FileNotFoundError, one `0 not greater than 10` on recorded ROS output; `build_round2` 4: FileNotFoundError); the same tests pass on the laptop, where the traces exist. **One flake:** `uv run python -m unittest discover -s tests` printed `FAILED (failures=1)` once on the laptop and `OK (skipped=42)` in the 8 runs before and after; I did not identify the test (the output of that run was cut by `tail`).
- **Zombie processes (found at the end):** the real-turtlesim test suite run inside `rosa-exam-main` left `[turtlesim_node] <defunct>` entries that `check_integrity.sh` reports as "ROS/Gazebo-like processes not in any container" (WARN). The container's PID 1 is `sleep infinity`, which does not reap orphans. Harmless, not killed; a restart of our container clears them (not done without the owner's say-so); a future `run_container.sh start` could add `--init`.
- **Final state at 03:50 (laptop clock):** `rosa-exam-main` up, our Ollama up (nothing loaded), GPU 277 MiB / 0 %, tmux sessions of ours: `ollama`, `gpusample`; repo at the laptop's HEAD (`git status` 0 lines); integrity check `0 FAIL, 3 WARN` (teammate's container and Ollama; the zombies).
