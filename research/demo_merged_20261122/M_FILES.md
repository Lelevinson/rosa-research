# Method M: files that define its behaviour (EX-M, Stage 1)

Updated by Claude Code, 2026-11-21 (night). Read-only audit plus one push; no held-out or custodian content.

- Public branch: `origin/member/levinson` now at `e233cf51389885d0aaffa5453687f57437551764` (two normal commits after `2b1c790`: `afa52fe` M files, `e233cf5` untracked-files audit; no force).
- Frozen hashes: `FREEZE.json` (`sha256` map) and `FREEZE_REV1.json` (changes only `queue_bridge.py` and `start_stage1_laptop.sh`, not part of M).
- Status: OK = public and equals frozen hash; NOT FROZEN = public, no hash in FREEZE.json (no equality check possible). Content of all added files is unchanged from the working tree (no redactions were needed).
- Why they were missing: the 14 files were **untracked and never committed on any branch**; the repository's shared `.git/info/exclude` ignores `/research/`, so only files added with `git add -f` earlier were ever tracked. The Stage 1 freeze hashed these working-tree files. They are now committed on the working branch (`df11733`, plus a second commit for 3 data files) and on `member/levinson`.
- Import check from the branch alone (no run, `rclpy` stubbed because ROS is not sourced here): `import exam_arms` succeeds and `exam_arms.make_arm` resolves. The first attempt failed on 3 data files read at import time (`stage3_graph.json`, `stage3_tasks.json`, `e1h_tasks.json`); I added them (17 files in the commit).

**How to assemble M:** entry `research/studies/exam_arms_20261121/run_exam.py` `episode()` sets `run_pilot.make_arm = exam_arms.make_arm`; `exam_arms.make_arm('M', recorder, context)` returns `ExamArm('M', ..., run_pilot.prompt_for('A1'))` = base arm `C1` (dev name FULL) + name fix. The queue reaches it as system `EX-M` in `exam_queue/systems.py`.

## Table (all present on the public branch)

| Path | Role in M | SHA-256 on public branch | = FREEZE hash? |
|---|---|---|---|
| `research/studies/final_exam_draft_20261118/exam_queue/systems.py` | System id `EX-M` -> `run_exam.py`, arm `M` (SYSTEMS table, line 29) | `fc1de9e165fd08b96ddea11de3441c6bb10b644cad07b4d667a1b107ad619b94` | OK |
| `research/studies/exam_arms_20261121/run_exam.py` | ENTRY: `episode()` sets `run_pilot.make_arm = exam_arms.make_arm`, then runs the pilot episode; `episode_row()` scores both ways | `39e659d8f1e4928f715d2c47e8e27c67824ff3a851f11e8bf3f95bc6bb3692af` | OK |
| `research/studies/exam_arms_20261121/exam_arms.py` | ARM ASSEMBLY: `make_arm('M')` -> `ExamArm` (base = dev arm FULL); `ExamArm.final_answer_tool` applies the name fix and logs raw answer | `d8ee1959cb27449dc54dc79c1e46a514ee5f9bb3fac938c9ccbeee973c5a4be0` | OK |
| `research/studies/steady_loop_ablation_20261117/ablation_arms.py` | `AblationArm` = base arm `C1` (FULL) with ablation switches; imported by `exam_arms.py` | `cb1633d1f1dd023bef8ed0ee1efbd28270caee26eb38e9f72603220a6c51bb2e` | OK |
| `research/studies/small_model_harness_20261115/harness.py` | MENU + RULES: `DOMAIN_TOOLS` (12 tools), `FINAL_ANSWER_LINE`, `strict_error` (strict pre-check), `PilotTool`/`Arm.wrap_tools` (soft errors), `Arm.final_answer_tool`, `Arm.base_menu`/`visible_schemas` | `62364091a5190708aca62cd963524d3686ce0d819b95e78e1390246350ecdc1c` | OK |
| `research/studies/small_model_harness_20261115/run_pilot.py` | `prompt_for('A1')`, `build_chat_model`, `episode()`, ollama settings (NUM_CTX 65536, MAX_ITERATIONS 40) | `d08fd6a6c981eab60f95eaf9422ff36b9e23191477ca236719e846585cbf741a` | OK |
| `research/studies/headroom_diagnostic_20261112/run_stage3b.py` | A1 PROMPT: `prompt_messages_a1()` and the `NEUTRAL` line replacing 3 discovery messages | `79002d21d120fae41093c9e492a2b40f601487e96f5ea0fbc87f7fc91aba77b5` | NOT FROZEN |
| `research/studies/headroom_diagnostic_20261112/run_stage1.py` | `prompt_messages('A0')` (stock prompt list + permission line), `TracedModel`, `ROSA` import; `rosa.prompts.system_prompts` | `6dc86b3a5fe22c5ca14f10b87d5e81601074d3ddc06ae8dbbeb835cf279a3804` | OK |
| `research/studies/headroom_diagnostic_20261112/run_stage3.py` | imported by run_stage3b (`build_model`, `TASKS`) | `ad2d18152b9fe7bea5e0d2d9203f0dffa55381ba5a550d7523da31f86a0e0211` | NOT FROZEN |
| `research/studies/headroom_diagnostic_20261112/stage3_fixture.py` | imported by run_stage3b (fixture helpers) | `17026be69505643705191788d17c16869a8d7a079f64f438cca1b12bc5e857ad` | NOT FROZEN |
| `research/studies/headroom_diagnostic_20261112/vendor/menu_run_study.py` | `Recorder`, `ToolRecorder`, `guarded_native`, `save` (trace recording, native-tool guard) | `9736756e64f74c7eaed62690b0552427cebf9118c71f891d3e2873a2ae0770b7` | OK |
| `research/studies/headroom_diagnostic_20261112/vendor/menu_policy.py` | imported by menu_run_study | `6265cb94c3fdf610a884c75c675a7b89dce7ad298e39dcdf2d2b6f6a8b69dd9f` | NOT FROZEN |
| `research/studies/headroom_diagnostic_20261112/vendor/baseline_protocol.json` | read by run_stage1 (`BASELINE`) | `3c62da11a8ad5f9b2d0df189ba02fdfcedc5158a185833742815632cefc74b6d` | NOT FROZEN |
| `research/studies/name_fix_applied_20261117/namefix_rule.py` | NAME FIX: `RULE_NAME` name-rewrite-v2, `candidate`, `rewrite_answer` | `4f9312f366b4de6d0bf1460ada099dfca1669421c3a678841d2263002faadc1a` | OK |
| `research/studies/build_round1_20261115/answer_gate.py` | LEDGER: `allowed_names(task_text, tool_outputs)` and regexes it uses | `795e882b88c2a96354e5d786e0f235d547219297a9ce1490638147f92afac456` | OK |
| `research/studies/residual_failures_20261115/scorer_v2.py` | scoring only (not behaviour); imported by exam_arms | `c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9` | OK |
| `research/studies/small_model_harness_20261115/pilot_score.py` | `last_json_object` used by harness final_answer parsing | `5d9de512a74b9e3ef39ab01bdce0c4724012327125c52ed53a06b95f205107da` | NOT FROZEN |
| `research/studies/headroom_diagnostic_20261112/score_stage1.py` | scoring helpers imported by scorer_v2/pilot_score | `462b34cdfedcb842d668d9a43ecaccc7a23ca4746fb24aa2796ee60b636aeb5e` | NOT FROZEN |
| `research/studies/headroom_diagnostic_20261112/vendor/baseline_audit.py` | imported by score_stage1/pilot_score | `7a0808afa816b85f56b0e2f8ab2d22c35e30c9c7f5926425c81ce0afef9513a9` | NOT FROZEN |
| `research/studies/thinking_escalation_20261119/run_think.py` | imported by run_exam (`T.TASKS`, session driver) | `9481a111815af291bea0d361d0285962881963f7fdbf0716d5446a0dcc22d7d5` | OK |
| `research/studies/build_round2_20261116/run_round2.py` | imported by run_exam | `707b7f6f8465157cc086a592e57a4ec0e1fc03c7e3e029e9dfcab54dbe704e25` | OK |
| `pyproject.toml` | dependency lock | `101d7701ca3bb93c3f60e6570e2bc6afce7aa68d2c526d3220bcacf9383537fa` | OK |
| `uv.lock` | dependency lock | `dbd8cb6db95ab8f7865c008f0a878e02f8f993f3da5145935ea801ea31009e9d` | OK |
| `research/studies/headroom_diagnostic_20261112/stage3_graph.json` | fixture graph, read at import by stage3_fixture | `0a2c345a60c56b96343e3bf0e6d05f3ebf5356d7c2da98a34c13ba9e57352678` | NOT FROZEN |
| `research/studies/headroom_diagnostic_20261112/stage3_tasks.json` | task set, read at import (run_think.TASKS, stage3_fixture) | `b61f8be16f7211e34b821c758472d784fcfa7c4cbd9c8bc95fcc9891a7c6ec67` | NOT FROZEN |
| `research/studies/small_model_harness_20261115/e1h_tasks.json` | task set, read at import by run_think | `5802e8987ce1805d5023fb58338e268eee60f92682854d2085a01a09eb230a85` | NOT FROZEN |

`src/rosa/*` (stock prompt text and tools) is public and not in FREEZE.json; hashes are in the earlier version of this file and the git tree.

## Limits

- Not frozen: 8 files that M or the baselines import, plus 3 data files (see `research/studies/exam_prep_20261121/FREEZE_GAP_20261121.md`). Their bytes are recorded now, but not covered by the freeze.
- `stage3_node.py` and `stage3_build.py` (fixture runtime files) are now public (commit `e233cf5`, with all untracked study code). Other runtime files the fixtures need were found by file name and import only, not by running the fixture.
- Import check used a stubbed `rclpy`; no episode was run.

## Open search

- Other files not on the public branch but referenced by M's runner at run time (fixture processes, tmux, queue scripts): not searched beyond imports and data files read at import.
