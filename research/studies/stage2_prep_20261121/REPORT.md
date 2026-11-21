# Stage 2 (turtlesim actions) wiring: code, tests and a dev smoke (2026-11-21, evening): report

Prepared by Claude Code (Sonnet 5.5) from `Claude outputs/2026-11-21_CC_STAGE2_WIRING_AND_PUSH_PREP.md`, part A (done after part B, as ordered). **Public development action tasks only, laptop only, no held-out file, no push, nothing frozen.** Rules kept: no method, harness, arm, scorer or freeze-package file was edited; all new code is in the new folder `research/studies/exam_actions_20261121/`; the git index lock was checked before each commit. The queue's `systems.py` is in the frozen file list, so the systems are registered at run time by a launcher instead of editing it.

## Top box
| item | status |
|---|---|
| A1 judge v1.2 tracked and replayed on the 128 dev traces | **done**; **finding: v1.2 does not unwrap a wrapped *structured* answer** (0 of 126 succeed in that form against 116 in every other form); a new wrapper `judge_exam.py` makes all six forms score identically (116 each, 0 disagreements). Judge not frozen |
| A2 systems XM, XS0, XE1 with the same typed action tool | **done as code + tests** (10 unit tests); dev action tasks only; reset, stable-state check, independent ground truth and event capture implemented |
| A3 smoke: 2 dev action tasks x 1 model x each system | **done**: 6 of 6 episodes through the queue launcher, rows with GPU state, not contended; one defect in my own adapter found and fixed before the final run (below). Not a comparison (n = 1 per cell) |
| A4 what the custodian must add | listed in section 4 (interface only) |

## 1. Judge v1.2 tracked and replayed (A1)
Tracked with `git add -f`: `action_dev_switch_20261118/judge_v1_1.py`, `judge_v1_2.py`, `tests/test_judge_v1_1.py`, `tests/test_judge_v1_2.py` (the 19 judge tests pass). Replay script `exam_actions_20261121/replay_judge.py` (output `replay_judge_results.json`): for each of the 128 dev episodes (phase full, traces in ignored `_artifacts`) the facts of the final answer are re-presented in six forms and scored.

| answer form (same facts) | v1.2 directly | v1.2 through `judge_exam` |
|---|---:|---:|
| object (`final_answer`) | 116 / 126 | 116 / 126 |
| wrapped object `{"answer": {...}}` | **0 / 126** | 116 / 126 |
| JSON string | 116 / 126 | 116 / 126 |
| wrapped JSON string | 116 / 126 | 116 / 126 |
| prose around a JSON object | 116 / 126 | 116 / 126 |
| prose around a wrapped JSON object | 116 / 126 | 116 / 126 |
| episodes whose six forms disagree | **116** | **0** |
(126 of 128 episodes have an answer object; the other 2 are HTTP 500 backend errors with no answer.) For reference on the recorded answers: the study's own v1.0 scoring gave 92 successes, v1.2 on the recorded answers gives 116 (the 24 gpt-oss answers that v1.0 could not read are the difference, as in the study's post-hoc note).
**Cause (read from the code, `judge_v1_1.judge`):** the singleton-wrapper rule is applied only when the recorded ending is `"text"`; a structured `final_answer` whose object is `{"answer": {...}}` is passed unchanged to the v1.0 key check and fails. **`judge_exam.py` (new, not frozen)** removes one level of `{"answer": dict}` wrapping and parses strings before calling v1.2 unchanged, so object, wrapped, string and prose forms agree. The judge files are not edited. The frozen judge for the exam, and the custodian's revised judge, should adopt the same normalisation.

## 2. The three acting systems (A2)
`action_arms.py` builds them from the existing arms, unchanged: **XM** = the exam's M arm (`exam_arms.ExamArm`: the 12 read tools, structured finish, errors as text, name fix) + the guarded action tool + a pose read tool; **XS0** (S0x) = the stock arm S0 (verbatim prompt, stock executor, 47 stock tools) + the same two tools; **XE1** (E1x) = the E1 arm (stock tools, errors as text, better prompt) + the same two tools. **"Same" is literal** (draft section 2): the typed tool `rotate_to_heading` is built once by `ActionToolKit` from the same deployment policy `TURTLESIM_POLICY` (field range [-pi, pi], goal budget 3, acknowledgement 2 s, execution deadline 15 s, cancel settlement 3 s) with the same `ExecutorOptions` (post-action state OFF, the dev default); a unit test shows the three systems' tool schemas are identical and that the budget is 3 for each. Only the system's own loop and menu differ. The stock tools' write paths remain blocked by the pilot's native guard, so the typed tool is the only way to move the robot.
Per episode (`run_actions.py`, a fresh process): **reset** = a new `turtlesim_node`; **stable-state check** = readiness plus the pose read twice, one second apart, by an independent node, start heading within 0.05 and the turtle still (otherwise the episode is recorded as infrastructure, not run); the system runs; **independent ground truth** = the dev study's `true_pose` (another node) after the episode; the **judge** is `judge_exam.judge` (v1.2 + form normalisation) on the answer, the truth and the captured events; **event capture** per episode: `action_call` (the call as made, goal id, terminal result, executor state), `pose_read` (with whether a goal had been sent), `executor_events.json` (the executor's own receipts), `ground_truth` before and after, the `judge` verdict with its reasons. `action_trace.py` converts these into the dev trace format judge v1.2 reads and maps the stock read tool `ros2_param_get` (arguments `param_name`, result `{param: "Integer value is: N"}`) to the judge's `get_parameter` read event. `run_actions_queue.py` registers the systems (`XM`, `XS0`, `XE1`, in `action_systems.py`) and runs the unchanged queue; the stub environment (`TurtlesimEnv`) satisfies the queue's fixture-session interface.
Tests (`tests/test_exam_actions.py`, 10, pass): identical typed and pose tool schemas across systems (including `theta` typed as number); same policy object and budget; menus (M: 12 + finish + 2 = 15 offered names; S0x and E1x: 47 + 2 tools); a call runs the real `ActionExecutor` against the fake robot and is captured; budget exhaustion returns REJECTED at the fourth goal; events feed judge v1.2 and the form normalisation (four answer forms succeed, a wrong true heading fails); the stock read mapping makes the read-before-dispatch rule satisfiable; the launcher registers the systems without touching `systems.py`.

## 3. Dev smoke (A3): qwen3.5:9b, tasks S3 and R1, seed 1, three systems, laptop, through the queue (run `stage2_smoke_d_20261121`, 6 of 6 rows, GPU state `ok`, none contended)
| task | system | supported (judge) | requests | goals sent | action results | pose reads (after goal) | judge reasons when unsupported |
|---|---|---|---:|---:|---|---|---|
| S3 | XM | **yes** | 5 | 1 | REJECTED, SUCCEEDED | 1 (1) | |
| S3 | XS0 | no | 2 | 0 | REJECTED | 0 | no answer object; true heading 0 vs target 4.0 |
| S3 | XE1 | no | 5 | 2 | REJECTED, SUCCEEDED, SUCCEEDED | 1 (1) | true heading 3.136 vs target 4.0; dispatched goal differs from the ordered task step |
| R1 | XM | **yes** | 3 | 1 | SUCCEEDED | 0 | |
| R1 | XS0 | no | 3 | 1 | SUCCEEDED | 0 | no answer object |
| R1 | XE1 | **yes** | 4 | 1 | SUCCEEDED | 0 | |
(S3 asks for heading 4.0 rad, outside the policy range [-pi, pi]: the executor rejects it and a system must find the equivalent heading.) **One episode per cell: no comparison, no effect, no ranking.** The final run repeated a run with identical rows (same seed, deterministic).
**Defects found in my own wiring during the smoke and fixed before the final run (all in the new folder):** (1) the first run had every call REJECTED: the tool's `theta` was untyped in the schema, so the model sent strings; it is now `float` like the dev study's tool schema, with a test; (2) the queue's oracle wrapper needs a `cli` attribute on the stub environment; (3) the first R1 rows were judged "required read unavailable before goal dispatch" although the read happened: the stock read tool's argument is `param_name`, not `parameter_name`; the adapter now maps it, with a test. The earlier runs (`stage2_smoke_`, `_b_`, `_c_`) are kept in ignored `_artifacts`; their rows are not used.

## 4. What the custodian (Codex) must add so held-out action cells route through the bridge (interface only)
1. **Task source:** an opaque-id lookup for action cells that returns, inside custody, the request text and the judge's task definition: the ordered steps (tool, targets, tolerances), required reads and the answer keys (what `judge_v1_2.dev_steps` and `judge.TASKS` hold for dev). The runner must take the request from the bridge, not from `judge.TASKS`.
2. **Fixture and ground truth:** reset, stable-state check and the independent observation (pose, still flag) provided by the custodian fixture (today `run_actions.episode` starts its own simulator and reads `true_pose` itself); isolated ROS domain 219 with custody-held ROS logs.
3. **Event feed:** a receipt hook for the executor's events (`ExternalRunner` has `observe_native` and `observe_tools`; action cells need the goal receipts and terminal status as well) so the custodian judge can run `verify_sequence` on custody-side evidence.
4. **Judge on the custody path:** v1.2's `judge_contract(base_verdict, steps, events)` is generic; the custodian supplies the answer-time `base_verdict` and `steps`, and must apply the form normalisation of `judge_exam.normalise` (section 1).
5. **Row and endings:** the opaque row adds goals sent, executor final state and the action ending classes the draft needs (agent-caused unresolved motion = `UNKNOWN_LOCKED` or motion at the end; "claims arrival but did not arrive" counted separately; class (a) reset failure, class (c) post-start oracle loss).
6. **Bridge system list:** `XM`, `XS0`, `XE1` in `SYSTEMS`, and a parameterised episode (request, fixture and truth supplied by the bridge) in `run_actions.py`, which I have not written because it depends on items 1 to 3.
7. **Tolerances:** the dev angular tolerance 0.1 rad is the dev value; the held-out tolerances belong to the custodian's frozen design.

## Limits
- Dev action tasks only (the study's 8 authored tasks); nothing about the protected 14-task pool. The smoke is 6 episodes with one model; it shows the wiring runs, not how the systems compare.
- The judge's "claims arrival but did not arrive" count and a per-episode "agent-caused unresolved motion" class are not computed in the row yet (the executor final state is recorded).
- `judge_exam.py` is a wrapper written today and not reviewed by anyone else; the replay (128 episodes, six forms) is the only check beyond its unit tests.
- Nav2 read-then-act (Stage 3) is not covered: no backend, judge or runner exists for it (unchanged from the readiness report).
- Held-out routing and the lab (domain 219, container) were not touched.

## Open search (unfiltered)
- The stock arms (XS0) failed twice on "no answer object": their free-text final answers carried no JSON object in these cells; the answers were not read further.
- XS0 on S3 ended after 2 requests with a single REJECTED call and no retry.
- The dev study's own runner used a different prompt and tool list (and no ROSA stack): these systems are not comparable to its numbers.
- `run_actions.py` uses the dev study's `true_pose` and the S2 test helpers (`start_turtlesim`, `WallClock`) by import; they are not edited.
- The queue launcher registers systems by mutating `systems.SYSTEMS` at run time; a later freeze should add the three lines to `systems.py` properly.
