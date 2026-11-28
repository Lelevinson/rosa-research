# Lab model proposal (merged-method demo, demonstration only, not evaluated, not for the paper)

Status 2026-11-28 ~22:45 lab time. Read-only checks only (process list, tmux, docker ps, nvidia-smi query, df, file listing of OUR model folder). Nothing was started, loaded or downloaded.

## Lab state (read-only)
- GPU: RTX 4080 SUPER, 16376 MiB total, 15832 MiB free, 0 % use. Only compute process: gnome-remote-desktop (251 MiB, not Levinson's).
- **Levinson's things are still present, not running GPU work:** tmux `exam-stage1_lab_20261123` (3 windows), `exam-stage2_lab_01`, `rosa-stage1-ollama` (his Ollama on 11435); docker `rosa-exam-stage1-lab` Up 2 days; his guard/monitor/gpu_state sampler processes still run. Per your rule ("if anything of his is running, stop and tell me") I did not go further. Please confirm with Levinson that his queue is finished before the window; I will re-check at the start of the window and stop if a job or GPU process of his appears.
- Our side: container `marvel-g1-extension-20261119` is Exited; our Ollama (11439) is not running. Both would be started inside the window.
- Disk: **root `/` is 100 % full (3.7 GB free)**. The data disk `/media/naeem/d1` has 379 GB free (our models live there). Runs and logs must go to d1.

## Models already installed (our folder `/media/naeem/d1/marvel-proj/models`, 21 GB)
| Tag | Manifest sha256 (first 16) | Size |
|---|---|---|
| qwen3.5:9b | 85879493124988ce | 6.55 GB |
| ministral-3:8b-instruct-2512-q4_K_M | 7b4d1edb7627cfc6 | 6.02 GB |
| llama3.1:8b-instruct-q4_K_M | 3fc95d284915704c | 4.92 GB |
| granite3.3:8b (not on your list) | aacf043297ef43fd | 4.94 GB |
Reuse only if the digests match the G1 backend records (I will compare before use; I have not yet).

## Candidates not installed (download needs your OK; all over 1 GB except possibly lfm3)
- gpt-oss:20b (about 13 GB), bonsai-2:4b (about 2.5 GB, size unverified), lfm3:1.7b (about 1.2 GB, size unverified). I have not looked up the exact tags or digests (no network call made). **Recommendation: skip the downloads.** gpt-oss:20b leaves under 3 GB for a 65536-token context on a 16 GB card, so it would almost surely need a smaller context.

## Proposed order
1. Sol (hosted, reference; existing sign-in only, no local GPU).
2. qwen3.5:9b.
3. llama3.1:8b (native-schema-v1).
4. ministral-3:8b if time allows.
Granite and the three downloads: not proposed.

## VRAM fit of num_ctx 65536 (estimates only, load-only check at the window)
Weights + f16 KV cache (flash attention on): llama3.1:8b about 4.9 + 8.6 = 13.5 GB (probably fits); ministral-3:8b about 6.0 + 9 = 15 GB (likely does NOT fit fully); qwen3.5:9b is a hybrid model with a smaller KV cache (unknown, check). If one does not fit: propose num_ctx 32768 (or 16384) as a labelled deviation applied to BOTH arms for that model, decided only from the load-only check, never from run results.

## Unique settings for the window
Our own Ollama on a new port (not 11435, not 11439 if another process holds it) with `OLLAMA_MODELS=/media/naeem/d1/marvel-proj/models`; ROS_DOMAIN_ID 247 (laptop used 232), localhost discovery only; one Gazebo instance; shut everything down at the end.

## Task set (no held-out)
D1, D2, D3 plus the 6 D2 DEV cases (artifacts/gazebo-d-20261121 dev set in rosa-evaluation). The 20 held-out D2 cases are not opened.
