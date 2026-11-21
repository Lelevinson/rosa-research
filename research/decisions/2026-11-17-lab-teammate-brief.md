# Lab computer: project brief

**17 November 2026**

We are studying how to make NASA/JPL ROSA work reliably and efficiently with small language models while it uses robot tools. We will compare our steady loop with other methods and check whether the answers and robot actions are correct. Your role is to prepare the lab computer now, help us run the Gazebo robot and prepare the **2 December demo**, and help design the full test later. We will agree on the test design before running it.

## Robot scope

The virtual-robot test must include the robot **doing something in simulation**, not just answering questions about the robot. Our main target is **TurtleBot3 with Nav2 in Gazebo**. A robot arm is a stretch goal. Turtlesim is our debugging workbench; it is not the main robot demonstration.

## Installation checklist

The reference computer uses Ubuntu **24.04.5**, ROS 2 **Jazzy** and Python **3.12.3**. The versions below are the installed reference on 17 November or the versions recorded in the earlier smoke; **they are not all frozen experiment pins**. Match them where available, record any differences, and ask us to confirm final versions and model digests before an experiment. These commands check installations; they do not start the robot.

| Item and reference version | One-line check |
|---|---|
| ROS 2 **Jazzy**; `ros-jazzy-ros-base` **0.11.0** | `source /opt/ros/jazzy/setup.bash && echo "$ROS_DISTRO"` |
| Ollama server/client: **0.40.16** was recorded earlier; current server version **to confirm** | `ollama --version` |
| Ollama models: **`lfm3:1.7b`, `qwen3.5:9b`, `gpt-oss:20b`, `bonsai-2:4b`** | `ollama list` |
| Gazebo Harmonic, **Gazebo Sim 8.15.0**; ROS bridge `ros_gz_sim` **1.0.24** | `gz sim --versions` |
| TurtleBot3 Burger: `turtlebot3_gazebo` **2.3.7**, `turtlebot3_navigation2` **2.3.6** | `dpkg-query -W ros-jazzy-turtlebot3-gazebo ros-jazzy-turtlebot3-navigation2` |
| Nav2: `nav2_bringup` **1.3.13** | `dpkg-query -W ros-jazzy-nav2-bringup` |
| `uv` **0.13.2**, for the locked Python environment | `uv --version` |
| `tmux` **3.4**, for persistent terminal sessions | `tmux -V` |

Source the ROS setup first if a ROS or Gazebo command is not found. Model tags can point to different files over time: compare the **full model digests** with ours as well as the tags. We will provide the approved repository commit, model digests, exact server version and run settings. Please report mismatches instead of silently choosing replacements.

## How we will run and return results

Our agents stay on my laptop. They connect to the lab computer over SSH and start an approved run inside `tmux`; the lab computer runs the model and simulator. For a named session, `tmux new -s rosa-study` creates it, **Ctrl-b then d** detaches, and `tmux attach -t rosa-study` reconnects. An SSH disconnect does not stop the session; a reboot does.

The **experiment harness must also run on the lab computer next to Gazebo**. Our earlier Nav2 smoke used ROS domain 219 and localhost-only discovery, while the experiment harness used domain 220. Both sides must use the same approved isolated domain and localhost settings; a process on my laptop cannot discover a localhost-only ROS stack on the lab computer. We will check the settings before a run.

Only **one GPU/ROS job at a time**: coordinate with us before starting an Ollama inference job, a ROS stack or Gazebo. Headless Gazebo used the GPU interface in our smoke, so do not assume it is GPU-free. Return approved results over Git or `rsync` over SSH; put compact reports in Git and transfer large traces separately. Verify the commit, file counts and checksums, and never overwrite an earlier run.

**Cleanup check after an authorized Nav2 smoke:** our previous run completed its goal, but shutdown logged a Nav2 component crash and Gazebo needed termination escalation. Use the run's approved cleanup procedure; check for `STOP PASS` with no remaining processes, then run `python3 research/studies/turtlebot3_nav2_smoke_20261116/stack.py status` from the repository root. It should say `No recorded stack.` Check this run's `cleanup.json` for `"clean": true` and an empty `"remaining"` list, and the supervisor log for a crash or forced shutdown. Tell us if cleanup is missing or fails; do not kill unrelated processes. The smoke helper is local-only in our current checkout; we must transfer an approved, hash-checked copy before it can be used on the lab machine.

## Working rules and reading

- Do not request or share held-out task texts, answers, oracle data or task-level details with anyone on the method side, including us. We will coordinate protected evaluation separately.
- Ask me before installing **agent tools** on the lab machine. Do not change the repository's experiment code.
- For project context, please read only the [one-page steady-loop summary](2026-11-17-steady-loop-teammate-one-page.md) and the [updated goal contract](../PAPER_GOAL_CONTRACT.md).
