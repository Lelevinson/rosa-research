# Repeatability, takes 4-6 (Sol), merged demo. 2026-11-22

**Label:** merged method (Levinson M + Martin bounded macro), demonstration only, not evaluated. Not method M. Not scored. Credit: method M components (Levinson).

Frozen configuration, unchanged (code hashes checked against `FREEZE_DEMO_MERGED.json` before the run: prompt `61b67529...`, tool set `2924ca6c...`). Takes 3-6 use the same configuration. Takes 1-2 used earlier versions (kept).
Each take: one fresh Gazebo (ROS domain 232), 3 of 3 resets independently confirmed, clean Gazebo close, tasks D1-D3.

| Take | D1 | D2 | D3 |
|---|---|---|---|
| 3 (reference) | expected path | expected path | expected path |
| 4 | expected path | expected path | expected path |
| 5 | expected path | expected path | expected path, with one extra menu read (ros2_topic_list, ros2_topic_echo) after the move |
| 6 | expected path | expected path | expected path |

**Takes 4-6: D1 3/3, D2 3/3, D3 3/3.** Including take 3 (same configuration): 4 of 4 for each task.
"Expected path" = D1 menu tools then `final_answer` with the name-fixed publisher; D2 inspect_readiness, park_right, `final_answer` (readiness true, shoulder_pan 0.16); D3 stage_left then `final_answer` (wrist_3 0.20). D3 take 5 reached the same answer and the same pose, with one extra read that the updated expected path does not require but does not forbid. D1 tool order varies slightly (a repeated `ros2_topic_info` in takes 4 and 6); answers are the same.
Writes: D1 0, D2 1, D3 1 in every take. No take errored.

## Not claimed
4 takes (3-6) on 3 hand-picked tasks, one model, healthy simulated world. This shows the demo is repeatable in this setup. It does not show the merge is better or worse than either part, and 4 of 4 is not a rate guarantee. The run was on the laptop with Sol's hosted session; a live demo can still fail (network, sign-in, Gazebo start), hence the backup video.
