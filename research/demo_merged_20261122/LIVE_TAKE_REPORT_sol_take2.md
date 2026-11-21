# Live take 2 (Sol), merged demo. Report for Martin, 2026-11-22

**Label:** merged method (Levinson M + Martin bounded macro), demonstration only, not evaluated. Not method M. Not scored. Credit: method M components (Levinson).
Take 1 is kept as a labelled failure (`LIVE_TAKE_REPORT_sol_take1.md`, `FREEZE_DEMO_MERGED_take1.json`).

## Wiring changes (our file `merged_demo/skill_tool.py` only; his files and his A1 prompt untouched)
1. An unknown skill id is refused before any counting and no longer uses the 2-call limit. The limit itself is unchanged.
2. The registered ids with their kind are in the `run_skill` description (ur5e.home, ur5e.park_right, ur5e.stage_left: state_change; ur5e.inspect_readiness: read_only_inspection).
3. Tests: 45 pass (2 new, zero model calls). Freeze redone: `FREEZE_DEMO_MERGED.json` tool set 2924ca6c... (was 3715fad0...). Prompt hash unchanged 917c7d99...

## D1 diagnosis (before take 2)
His 12 menu tools ARE bound and visible. The take-1 trace shows, on every request, all 12 names plus `final_answer` and `run_skill`, with correct names and full parameter schemas (e.g. `ros2_topic_info` {topics}, `ros2_topic_echo` {topic,count,...}). **No wiring bug found.** Sol chose not to use them. Likely cause (inference, not tested): our macro rule line "Use the registered skills only." (`prompts.py`) pulls Sol to skills. Not changed, per your instruction not to tune prompts.

## Take 2 results (what happened, not a score)
Gazebo healthy, 3 of 3 resets confirmed, Gazebo closed cleanly. Records: `live_takes/sol_take2/`.
| Task | Tools Sol used | Writes | Final answer |
|---|---|---|---|
| D1 | run_skill ur5e.inspect_readiness, final_answer | 0 | **Still null** (publisher and joints). Again no menu tool used. |
| D2 | inspect_readiness, then park_right, final_answer | 1 | readiness true, shoulder_pan 0.16. **Expected path reached.** |
| D3 | stage_left, final_answer | 1 | wrist_3 0.20. No fresh menu read after the move (macro verify only). |

Wiring fix worked: no wasted calls, D2 now does inspect-then-move. D1 and the D3 menu read remain Sol's choice.
## Not claimed
Not evidence that the merge works. One take per task, one model.
## Open for Martin
Take 2 is the best take so far (D2 full path), D1 fails. A further take would need a wording change (for example the rule line), which you did not authorize. Nothing else started; GPU and Gazebo free.
