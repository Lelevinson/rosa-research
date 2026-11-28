# Arm (b) "M + primitives" (merged-method demo, demonstration only, not evaluated, not for the paper)

Arm (a) = his M + `run_skill` (bounded macro). Arm (b) = the SAME his M files (e233cf5, hashes in M_FILES.md, unedited) + four primitive tools instead of `run_skill`:
`read_pose`, `read_readiness`, `write_pose(skill_id)`, `verify_pose(skill_id)`. The model sequences read -> write -> verify; in arm (a) the macro does.

Same guards as the macro: registered targets only, transport validate_write bound, one write per task, no replay after an unconfirmed write, 10 native operations,
16 tool attempts, 180 s, tolerance 0.025, one primitive call per response, a read before any write. Difference: the macro skips a write that is already at target
(logged); in (b) the model decides.
Prompt: his A1 messages + the arm (a) rule sentences word for word, except the first sentence and the skill line, which name the four tools instead of `run_skill`.
Same for every model; no per-model tuning.

Files (all new; no arm (a) file changed): `merged_demo/primitives_tool.py`, `merged_demo/primitive_prompts.py`, `merged_demo/his_m_primitives.py`, `tests/test_primitives_arm.py`,
`freeze_primitives.py`, `FREEZE_DEMO_PRIMITIVES.json` (hashes). A live driver for both arms comes with the lab run.
Tests: 20 new, fake model, zero model calls. LAPTOP DRY CHECK, NOT THE LAB RUN (`TEST_LOG_arm_b_laptop_dry_check.txt`); rerun on the lab before the window.
