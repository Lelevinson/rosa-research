# Exam preparation, batch 1 (2026-11-21): report

Run by Claude Code (Sonnet 5.5) on the laptop from `Claude outputs/2026-11-21_CC_EXAM_PREP_BATCH1.md`. Authorisation: the owner's message of 2026-11-21 (lab steps listed in the batch only). No model-scored episode was run, no held-out file was opened, nothing was pushed.

## Top box
| step | status |
|---|---|
| 1 `""` coercion | **NOT implemented, by the owner's decision** (see 1) |
| 2 lab restart with `--init` | **NOT DONE: the lab host was unreachable** (see 2) |
| 3 transient-failure check | **NOT DONE: needs the lab** (see 3) |
| 4 extra-model facts | done from the saved 2026-11-20 traces, no new run |
| 5 protocol draft revision 3 | done, not frozen |

## 1. `""` coercion
**Finding that changed the step.** The batch said to implement the fix "where the 2026-11-19 lossless argument coercion lives". That coercion does not live in any executor: it exists only as the function `convert()` in `research/studies/arg_type_retry_offline_20261119/arg_type_retry.py`, used to **count** fixable argument-type events offline (K1-K6; K3 is the empty string or null for an optional array). Nothing converts arguments during an episode. In the live arms every menu tool is a `PilotTool` (`small_model_harness_20261115/harness.py`), whose `_parse_input` runs the strict pre-check `strict_error` before pydantic, so `blacklist: ""` is rejected with a text for the model; the stock arms (S0, E1) leave it to pydantic. The hashes of `harness.py` and `run_pilot.py` are recorded in five finished studies' `FREEZE.json` files (canonical_render, finish_split, listval_live, loss_map, name_fix_applied).

**Decision (owner, 2026-11-21, asked after this finding):** do not implement the `""` fix in any arm. It stays a **known interface issue that affects all arms alike** (dev size: 38 of 432 episodes, all gpt-oss, at most 1.46% of requests; [empty errors report](../empty_errors_20261120/REPORT.md)). Consequences recorded: "argument coercion" is removed from the method component list; the exam report counts such calls per system and model and does not correct for them. No code changed in this step, so no unit tests were added.

## 2. Lab container restart with `--init`
**Not done.** Before touching anything I tried a read-only state check (container list, GPU processes, Ollama ports) over `ssh <LAB_USER>@<LAB_HOST>`. Result, three attempts: `Connection timed out` on port 22, and `ping` 100% loss, while the laptop's internet worked (ping to 8.8.8.8 answered, 14 ms). Because the state of the teammate's container (`<OTHER_CONTAINER>`) and Ollama (port 11439) could not be read, nothing was stopped, removed or started. I did not retry by other routes. The old and new `docker run` commands were therefore not recorded and `lab/check_integrity.sh` was not run.
For the person who runs it: the current start command is in `lab/run_container.sh` (`start` subcommand: `--network host`, `ROS_DOMAIN_ID=220`, `ROS_LOCALHOST_ONLY=1`, our mounts and env). It has **no `--init` flag today**; the batch asks to add it (the container's PID 1 is `sleep infinity`, which does not reap orphaned children, hence the zombie warning). `DRY_RUN=1 bash lab/run_container.sh start` prints the command first. Cause of the timeout is unknown (lab network, power, a changed address, or a laptop-side network route); it is not diagnosed.

## 3. Transient-failure check (model-free)
**Not done**, it needs the lab container with the dev fixtures. Still open. The plan in the batch (200 direct calls each of `ros2_node_info`, `ros2_param_list`, `ros2_param_get`, `ros2_service_info` on known-existing names, then again with headless Gazebo/Nav2) is unchanged. No cause for the lfm3 empty errors is claimed here.

## 4. Extra-model eligibility facts (saved lab traces of the 2026-11-20 interface check; no new run)
Source: `final_exam_draft_20261118/lab_results_20261120/interface_check/summary.json` and the session traces in `research/_artifacts/lab_20261120/interface_check_session/session/*/trace.jsonl` (`model_end` messages). Design: tasks p3 and u3, arm A1 (stock executor, no finish tool), seed 1, one episode per task and model, temperature 0.7. Outcomes were **not scored and are not used for selection**.

| model | structured tool calls | answers produced | VRAM residency | blocking defect (as observed, n = 2 episodes) |
|---|---|---|---|---|
| gemma4:e4b | **yes**: 4 `tool_calls` in 4 tool-calling requests, 0 invalid, none as text | **none**: in both episodes the last request returned empty text (`eval_count` 1, `done_reason` stop) after 2 tool calls | Ollama `/api/ps` 393 MiB, but its runner holds 5,918 MiB on the GPU: `/api/ps` is unusable, residency must come from `nvidia-smi` | empty final answer 2 of 2 (on 2026-11-15 on the laptop it answered p3, so behaviour is not stable); residency not measurable from Ollama |
| granite4.2:8b | **yes**: 11 calls, 0 invalid | yes: JSON text, 74 and 118 chars (fenced in one) | 15,793 / 14,346 MiB = **90.8% in VRAM** at `num_ctx` 65536 | 9% outside VRAM, so speed and contention rules are affected; no tool-call defect seen |
| llama3.1:8b | **yes**: 4 calls, 0 invalid (3 calls in one request once) | text, 137 and 206 chars; the p3 text says the tool returned an error and gives no answer, so the answer's content was not judged here | 12,775 / 12,775 (100%) | none in tool calling; one `ros2_param_get` call returned `Node not found` (the answer text was not scored) |
| ministral-3:8b | **yes**: 6 calls, 0 invalid | u3: text 304 chars (JSON in a fence); **p3: none**, episode aborted at request 1 | 13,610 / 13,610 (100%) | **validation abort on p3** (error below) |

**ministral-3:8b error text (p3, trace `007-p3-A1-ministral-3_8b-s1`, event `tool_error`):** the model called `ros2_node_list` with `{"blacklist": {}, "pattern": "plant32/quartz"}`; the stock arm returned
`1 validation error for ros2_node_list` / `blacklist` / `Input should be a valid list [type=list_type, input_value={}, input_type=dict]`
and the episode ended there. This is the A1 arm's stock executor aborting; under the method arm (soft errors) the rejection would come back as text, so whether ministral would continue is **untested**. Note the wrong value is `{}` (an object), not `""`, so the `""` rule of step 1 would not cover it either.

Limits: 2 episodes per model on one machine; "structured tool calls yes" means LangChain parsed non-empty `tool_calls` from the model's response in those episodes, not that the calls were correct; llama3.1's text answers were not read for correctness. No new run was needed to answer the questions, so none was made.

## 5. Exam protocol draft: revision 3
[PROTOCOL_DRAFT.md](../final_exam_draft_20261118/PROTOCOL_DRAFT.md) (revision 2 kept as `PROTOCOL_DRAFT_v2_20261119.md`). Added: **2c** method components = short tool menu + structured finish tool + errors-as-text + answer name fix (rewritten answers reported as their own group; ablation arm without the name fix), with the explicit correction that argument coercion is not a component and not implemented, plus the `""` issue as a known equal-for-all-arms interface issue; **2d** two-stage action plan (question-task exam first; turtlesim held-out action exam next week; Gazebo live demo separate), marked **pending confirmation**, with sections 4 and 9 still describing the older single-exam wording until confirmed; **9b** list of 12 items still open before a freeze (including steps 2 and 3 of this batch). Nothing is frozen, hashed or authorised.

## Open search (unfiltered)
- **Unverified detail in the draft:** how the runner would switch the name fix off for the ablation arm, and whether the rewrite is still shadow-logged in that arm, was not checked (stated as unverified in 2c).
- **Method list vs ablation list:** the dev ablation arms (`NO_MENU`, `NO_FINISH`, `NO_SOFT_ERRORS`, `NO_PRECHECK`) include a pre-check component that the batch's method list does not name; the draft keeps "strict pre-check" inside item (3) of the loop. The owner may want it listed separately.
- **`--init` is absent today** from `run_container.sh`; no zombie count is known because the lab check could not run.
- **A broad recursive `grep -r` over the repository was refused by the permission classifier** at the start of this session; I switched to `git grep` and targeted paths, and never opened `research/.local/`. No held-out custodian file was read.
- **gemma4's empty final text** appeared in both episodes with `eval_count` 1: possibly an Ollama or template effect rather than model behaviour; not investigated.
- Not diagnosed: why the lab host timed out. Counts and trace paths for step 4 are listed above; no other patterns were searched in those traces.
