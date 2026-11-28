#!/usr/bin/env bash
for s in $(tmux ls 2>/dev/null | cut -d: -f1 | grep -E '^(sim_|moveit_|job_|reh)'); do tmux kill-session -t $s 2>/dev/null; done
./stop_sim.sh
ps -eo pid,cmd | grep -E 'gz sim|ros2_control_node|parameter_bridge|move_group|robot_state_publisher|spawner' | grep -v grep | grep -v cleanup | cut -c1-100
echo sessions: $(tmux ls 2>/dev/null | wc -l)
