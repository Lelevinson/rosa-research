# Build round 1 protocol (frozen 2026-11-15, before any model run)

Source assignment: `Claude outputs/2026-11-15_PROMPT_CLAUDECODE_build_round1.md` (context mirror). Owner decision: the fixed loop (arm C1 of the pilot) is the base. Development/pilot tasks only; no held-out set (E2, E3, E3b) is opened. Scorer v2.0 (sha256 `c6b02716...`) is unchanged.

## What is tested
| arm name in code | plain name | difference from the fixed loop |
|---|---|---|
| C1 | fixed loop (fresh control) | none (the gate runs in shadow mode: it logs what it would do and changes nothing) |
| C1+AG | fixed loop + answer gate | bare-text nudge (max 2), name check + key check on `final_answer` (max 2 rejections), numbers logged only |
| C1+LA | fixed loop + list arguments | `ros2_param_get.node_name`, `ros2_param_list.node_name`, `ros2_topic_echo.topic` accept one name or a list of up to 20 |
| C1+AG+LA | fixed loop + both | both |

Rules, in code with their definitions: `answer_gate.py` (module docstring), `list_args.py` (module docstring). Arm wiring: `round1_harness.py`. Scoring: `score_round1.py` = scorer v2.0 plus one expansion step (a list call is turned back into one single-entity row per item before scoring, so a fact read through a list is credited exactly as through single calls).

## List rule: wider than the assignment's literal wording (OWNER-CONFIRMED 2026-11-16: this is the intended rule; the literal version is not to be run)
The assignment says list support is for "every read tool whose single required argument names one entity". Literally that selects only `ros2_topic_echo` (`ros2_param_get` has two required arguments, `ros2_param_list` none; `ros2_node_info`, `ros2_topic_info`, `ros2_service_info` already take lists). The measured batching waste is mostly parameter reads (WASTE_BY_CAUSE), so the literal reading would leave the add-on nearly empty. Implemented rule: a read tool's plain string argument whose docstring line says it is a *name* of one node/topic/service accepts a list; the tool's other arguments are shared by all items. This yields three tools (above). To test the literal reading, restrict `list_args.applicable_tools` to `ros2_topic_echo`.

## Fixed conditions
Same as the pilot: local Ollama (172.30.80.1), think false for all four models (pilot SDK default `reasoning=False`), temperature 0.7, num_ctx 65536, num_predict 4096, seeds 1 and 2, 40-iteration cap (nudge requests are extra and capped at 2), 90 s HTTP timeout, 900 s episode timeout, ROS domain 220 localhost only, same Stage 3 / E1h fixtures, same oracle/cleanup checks and stop rules (`run_pilot.session`). Prompt = pilot's A1 prompt + final_answer line (unchanged); list arguments change only the argument's line in the tool description and its schema type.
Cells: 10 tasks (u3, p3, h4, v2, e1h_amb_1, e1h_amb_2, e1h_abs_1, e1h_abs_2, e1h_chg_1, e1h_chg_2) x 2 seeds x 4 models (lfm3:1.7b, qwen3.5:9b, gpt-oss:20b, bonsai-2:4b) = the 80 pilot cells, each run in all four arms = 320 episodes. All arms of one model/environment share one fixture session, order shuffled with seed 20261117.
Smoke: qwen3.5:9b, tasks h4 and e1h_amb_1, seed 1, four arms (8 episodes). Smoke rows are logged with phase "smoke" and never enter the totals.

## Success criteria (decided now)
Computed on the 80 cells against the fresh control of this same session, scorer v2.0. Descriptive; two seeds, no significance claims; per-cell agreements and disagreements are reported.
- **Answer gate helps** if: (1) it has more supported-complete episodes than the fresh control (C1+AG > C1), and (2) no cell that is supported in the fresh control is unsupported in C1+AG *because of a wrong rejection*. A wrong rejection = the gate rejected an answer (or nudged) in that episode and the episode then ended unsupported while the control's cell was supported; each such cell is hand-read and reported with trace lines. Cells where the control is supported and the gate arm is unsupported for another visible reason (model variance without any gate firing) are reported separately and not counted as wrong rejections.
- **List arguments help** if: (1) total LLM requests are lower than the fresh control, (2) total reported tokens (input + output) are lower than the fresh control, and (3) supported-complete is not lower than the fresh control. Adoption is reported either way: share of episodes with at least one list call, share of calls that are lists, items per list call. If adoption is near zero, the result is "not adopted", not "no effect".
- Both add-ons together are reported against the control with the same two sets of criteria.
- Not claims: novelty, significance, generalisation beyond these 10 tasks and 4 models. Round 1 results choose the claim; a claim is frozen by the owner afterwards.

## Stop rules
Offline pre-check false-rejection target 0 (met: `precheck_gate.json`, `precheck_all_arms` output in REPORT.md). Smoke: stop and report on any surprise (crash, write command reaching ROS, an arm that behaves identically to the control because a flag did nothing, oracle mismatch, unexplained rejection of a correct answer). Full run: session stop rules of `run_pilot.session` (Ollama unreachable, oracle mismatch, write reached ROS, cleanup failure); 6 h wall limit per session.

## Credits and related papers (unverified, not novelty judgments)
Bare-text nudge: Forge (forge-guardrails; bare-text retry nudge). Related papers to compare later (unverified): LLM-Tool Compiler 2405.17438 (fused tools), AgentLTL 2607.02599 (answer entities grounded in tool outputs), Entity Binding Failures 2606.30531.

## Amendment 2026-11-16 (after the run, wording only)
The owner confirmed the list rule as implemented (`ros2_param_get.node_name`, `ros2_param_list.node_name`, `ros2_topic_echo.topic`). Its precise statement is in REPORT.md, section 'What was built'. No code, plan or criterion changed; FREEZE.json hashes of the code are unaffected (this file's hash in FREEZE.json is the pre-run version).
