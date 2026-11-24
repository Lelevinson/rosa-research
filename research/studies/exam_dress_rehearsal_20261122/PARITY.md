# Part A: static parity of the exam arms and the dev arms (no model call)

Method: `parity_capture.py` builds each arm the way the dev runner builds it (`run_pilot.episode` -> `make_arm`, full dev task dict as context) and the way the exam worker builds it (`queue_bridge.episode`: `E1` -> `fair_arms.make_arm`, every EX arm -> `exam_arms.make_arm`, context = id + request only), wraps it in the pilot's `PilotROSA`, and dumps what the model and the executor see. It compares SHA-256 of the canonical JSON dumps (first 16 hex digits shown; full dumps in `parity_capture.json`). No ROS command was run (a probe that reached ROS would have raised). Dev M reference = ablation arm `FULL` (`ablation_arms.make_arm`) for prompt/menu/schemas/pre-check/finish, and the applied name-fix arm `NAMEFIX` (`namefix_arm.make_arm`, the arm behind the 54 -> 62 and replay evidence) for the name fix.

## EX-M versus dev M
| Item | Dev source + hash | Exam source + hash | Identical | Difference |
|---|---|---|---|---|
| System prompt messages (list) | `ablation_arms.make_arm("FULL")` -> `run_pilot.prompt_for("A1")` + finish line; `4a1c25793e5bff2e` | `exam_arms.make_arm("M")`; `4a1c25793e5bff2e` | yes | none |
| Rendered chat template for a sample request | `ae30f549e40e6289` | `ae30f549e40e6289` | yes | none |
| Registered (wrapped) tool list: 51 tools in order with descriptions, JSON schemas, tool class, error handlers | `813ba1ef68997af9` | `813ba1ef68997af9` | yes | none |
| The 13 schemas the model is actually offered (12 domain tools + `final_answer`) after the per-request filter (`visible_schemas`) | `ca70c744a9e32274` | `ca70c744a9e32274` | yes | none |
| Finish tool (`final_answer`) schema | inside the two hashes above | same | yes | none |
| Executor class and settings (PilotExecutor, 40 iterations, `handle_parsing_errors`) | `f936003e722316c6` | `f936003e722316c6` | yes | none |
| Errors-as-text and strict pre-check: text returned for malformed arguments, the 50 other registered tools, 2 probes each = 100 probes (102 probes in all, 2 on `final_answer` excluded because EX-M adds name-fix events there); about six probes per arm pass schema validation and reach the mocked native boundary, whose sentinel error is returned as text (zero ROS commands) | `c8b5ff86d5f56c5d` (after replacing the arm-name log label) | `c8b5ff86d5f56c5d` | yes | only the log label in the `handler` field (`FULL` / `NAMEFIX` / `M`) |
| `final_answer_tool` on 5 sample answers: text returned and accepted answer | `f8e2a27bf5368b44` (dev NAMEFIX and dev FULL) | `f8e2a27bf5368b44` | yes | none |
| Name-fix path: full event log of the same 5 samples versus dev NAMEFIX | `1b80861bf49651ef` | `a7ed987f80384926` | **no (log only)** | dev NAMEFIX (Round-1 control class) also writes a shadow-gate log event `gate_shadow` (`would_reject`, never acts). With that event dropped: `a7ed987f80384926` = `a7ed987f80384926`, identical. EX-M has no gate code at all. |
| Name-fix path versus dev FULL | `f9a9b6d849426580` | `a7ed987f80384926` | no, by design | EX-M adds `final_answer_original` and `namefix` log events and may rewrite the accepted answer. That is the method's name fix. |
| Name-fix code `namefix_rule.py` and its ledger `answer_gate.allowed_names` | `name_fix_applied_20261117/namefix_rule.py` `4f9312f3...`; `build_round1_20261115/answer_gate.py` `795e882b...` | same two files (module paths printed identical in both paths) | yes | none |
| Arm code | `ablation_arms.py` `cb1633d1...`, `harness.py` `62364091...` | `exam_arms.py` `d8ee1959...` (subclasses `AblationArm`) | n/a | `ExamArm` only adds the rewrite at `final_answer`, the `tool_outputs` ledger and the NO_ERRORTEXT branch (not used by EX-M) |

## E1 exam versus E1 of `fairness_errors_as_text_20261117`
| Item | Dev | Exam | Identical | Difference |
|---|---|---|---|---|
| Code | `fair_arms.make_arm`, `fair_arms.py` `af604ca5...` | the same function (`queue_bridge.episode` picks it for E1) | yes | none |
| Prompt messages | `7acbb0555cba9f40` | `7acbb0555cba9f40` | yes | none |
| Rendered template | `f0f0a9cecc64fb06` | `f0f0a9cecc64fb06` | yes | none |
| 47-tool menu (E1 registers and offers 47 tools): names, descriptions, schemas | `b4a9669471c93159` | `b4a9669471c93159` | yes | none |
| Bound schemas | `a095e67c4a29df79` | `a095e67c4a29df79` | yes | none |
| Executor (stock AgentExecutor, 40 iterations) | `2b9a28a607ac8adf` | `2b9a28a607ac8adf` | yes | none |
| Errors-as-text text for malformed arguments (47 tools x 2 probes = 94 probes, raw, no normalisation needed) | `7a94139abdb84420` | `7a94139abdb84420` | yes | none |

## Episode wrapper (read by eye, not hashed): `run_pilot.episode` versus `queue_bridge.episode`
Same: `pilot.build_chat_model(model, temperature, seed)` (ChatOllama, `num_ctx` 65536, `num_predict` 4096, 90 s client timeout), `ArmTracedModel`, `PilotROSA` (40 iterations), `guarded_native`, `ToolRecorder`, temperature 0.7 in the spec, episode timeout 900 s (queue default; the spec does not override it).
Different, none of them reaches the model or the tool menu: (1) the worker passes only `{id, request}` as the task (the dev dict also has `floor`/`depth`; only the unused plan arm H7 reads them: `harness.py` line 516); (2) `episode_start` carries no `prompt_sha256`, floor or depth; (3) no `effective_request` event; (4) fixtures are started and reset per episode by the custodian runtime, the dev sessions reused one fixture session per model and environment; (5) `FixtureRecorder` is a `ToolRecorder` subclass that only acts when the environment is `e3r2`; (6) the dev oracle wrapper `OracleWithRetry` is not part of the exam worker (the custodian runtime does its own checks, not readable here).

## Result
Prompt, menu, schemas, finish tool, executor and the errors-as-text / pre-check behaviour are byte-identical between the exam arms and the dev arms. The only differences are the arm-name label in the log, the extra log-only `gate_shadow` event in the dev name-fix arm, and the intended name-fix events of EX-M relative to dev FULL. No difference found in the checked prompt and tool interfaces changes what the model is offered or how the executor treats a malformed call. Not checked: the custodian's real fixture runtime and scorer adapter (folder not opened); runtime behaviour beyond the 5 sample answers and 2 probes per tool.


## Limits added after the independent review (Codex, CODEX_REVIEW.md section 1)
The capture injects sample tool outputs for the name-fix ledger, calls the finish handler directly and resets its state between samples: it does not exercise tool-result collection through the live loop, two consecutive invalid finish submissions or live ROS failures. The worker wrapper also feeds completed native observations to the fixture and, for the read-triggered family (`e3r2`), normalises tool results in `FixtureRecorder.on_tool_end`; that can change later tool results and is outside this static capture. The launcher's own ending and timeout handling (nonzero worker exit or missing ending file goes to the queue's failure and retry path) is not covered either. The statement above is therefore limited to the checked prompt and tool interfaces.
