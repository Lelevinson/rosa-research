# Lab demo test cancelled by owner (2026-11-28)

Merged-method demo (Levinson M + Martin bounded macro), demonstration only, not evaluated, not for the paper. The owner cancelled the lab demo test on 2026-11-28 while a qwen3.5:9b run and a laptop Sol run were in progress. **No results below are findings; they are an interrupted partial smoke record. Nothing is complete, nothing goes to the paper.**

## Stopped and cleaned
- Lab runner stopped with SIGINT (Gazebo closed by its own code), no gz/ros2 processes left in our container; our container `marvel-merged-demo-20261128` stopped (487 kB on `/`); our Ollama (tmux `marvel-demo-ollama`, port 11449) killed, model unloaded, port closed. Laptop Gazebo (WSL) from the Sol run killed.
- Lab check after stop: `df -h /` 3.6 GB free (100 % used; was 3.7 GB before our work, our container layer is only 487 kB, so the 0.1 GB difference is not attributable to us); GPU 362 MiB used, only gnome-remote-desktop (251 MiB), no process of ours.
- Levinson's processes (tmux exam-stage1_lab_20261123, exam-stage2_lab_01, rosa-stage1-ollama, his Ollama 11435, docker rosa-exam-stage1-lab) were only listed, never touched.
- No download or install was in progress; no partial files. Completed items stay on the data disk: `/media/naeem/d1/marvel-proj/ros-demo` (950 MB: ROS tree copy with the UR5e Gazebo packages, `PACKAGE_LIST.txt`, one extracted 10 KB deb) and `/media/naeem/d1/marvel-proj/merged-demo-20261128` (code copy, runs, logs). Removing them is the owner's call.

## Partial run records (interrupted, not findings)
Lab qwen3.5:9b (num_ctx 65536, both arms, interrupted after 7 of 18 runs): D1 macro reached/supported yes (4 calls), D1 primitives not reached (3 calls); D2 primitives and macro yes (5 / 3 calls); D3 both yes (5 / 5 calls); D-dev-01 primitives yes (8 calls). Laptop Sol (labelled laptop): D1 macro and primitives completed before the stop. Records: lab `.../merged-demo-20261128/runs/qwen_full`, laptop `lab_demo_runs/sol_laptop_01` (not committed).

## What exists
Arm (b) code and 20 tests (commit d99d6ac), model proposal (9227f99), and now the lab scripts `lab_runner.py`, `lab_load_check.py`, `lab_gazebo_check.py`, `d2_dev_cases.json` (dev split only; held-out never opened). Lab setup facts: UR5e world launches headless in about 5 s, resets and closes cleanly; his 26 files verified; 65 scripted tests OK on the lab; all three local models load fully on the GPU at num_ctx 65536 (qwen3.5:9b 7.7 GB, llama3.1:8b 13.4 GB, ministral-3:8b 14.3 GB reported by Ollama).
