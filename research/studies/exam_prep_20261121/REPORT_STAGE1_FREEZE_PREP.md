# Stage 1 freeze preparation (2026-11-21, afternoon): report

Run by Claude Code (Sonnet 5.5) on the laptop from `Claude outputs/2026-11-21_CC_STAGE1_FREEZE_PREP.md`. Authorisation: the owner's message (freeze scope, laptop queue order, Forge/MetaTool smoke gates on public dev tasks on the laptop GPU). **Nothing was hashed or frozen.** No lab, no held-out file, no push. Model use: 2 exam-arm smoke episodes and 6 Forge gate episodes (all development tasks; smoke labels, no scores used for any decision).

## Top box
| item (section 9d) | status |
|---|---|
| 9d-2 NO_ERRORTEXT arm | **done**: arm built, 9 unit tests, 1 dev smoke episode clean |
| 9d-3 name-fix shadow scoring | **done**: raw answer logged before the rewrite, both scores per episode, test on a saved trace where the rewrite flips the result |
| 9d-4 extra models and ending class | **done**: queue systems and spec tier for the 3 extra models; ending class `validation_abort` with tests |
| 9d-5 Forge smoke gate | **run, passes with 2 notes** (below); no queue adapter yet |
| 9d-5 MetaTool smoke gate | **not run: not runnable as released today** (reason below) |
| 9d-8 / 9d-9 freeze package draft | **drafted, not hashed**: spec generator, spec, digests, criteria text |
| 9d-1, 9d-6 | left to Codex; 9d-7 next week |

## 9d-2 NO_ERRORTEXT and the exam arms
New folder `research/studies/exam_arms_20261121/` (no frozen dev file edited: `harness.py` and `run_pilot.py` hashes recorded in five finished studies stay valid). `exam_arms.py`, class `ExamArm` on the dev `AblationArm`: **M** = dev FULL + name fix; **NO_MENU**, **NO_FINISH** = the dev ablations; **NO_ERRORTEXT** = soft errors and the strict pre-check both off (the dev arms NO_PRECHECK and NO_SOFT_ERRORS combined; stock pydantic validation, coercions logged, any validation or tool exception ends the episode as `HardToolError`). Runner adapter `run_exam.py` (hooks `run_worker`, `episode_row`, `episode`; 90 s HTTP, 900 s episode, pilot settings; development tasks only).
Tests (`exam_arms_20261121/tests/test_exam_arms.py`, 9, pass): M's prompt equals the dev FULL arm's; NO_ERRORTEXT offers the same menu, prompt and schemas as M; invalid arguments raise `HardToolError` with no pre-check event; a coercion (`count: "2"`) is logged and the coerced call runs; a tool exception ends the episode in NO_ERRORTEXT and is returned as text in M; write tools stay blocked.
**Dev smoke (qwen3.5:9b, seed 1, one episode of NO_ERRORTEXT on u3):** 4 requests, supported, no abort, 0 coercions. That shows the arm runs end to end; it says nothing about its effect (n = 1, no comparison).

## 9d-3 Name-fix shadow scoring
Finding: the existing `NameFixArm` (name_fix_applied_20261117) already logged `final_answer_original`, a `namefix` handler event and the rewritten `final_answer_accepted`, but it sits on the round-1 arm, not on the exam's M. `ExamArm.final_answer_tool` reuses the same rule (`namefix_rule.rewrite_answer`, v2) on M. `exam_arms.score_both(task, events)` scores one episode twice with scorer v2.0 (rewritten = accepted answer, raw = the original swapped in); `run_exam.episode_row` adds `supported_raw`, `exact_raw`, `answer_raw`, `name_fix_changed`. So "M" and "M without the name fix" come from the same requests; no separate arm.
Test on a saved trace (`tests/nf_single_2_lfm3_trace.jsonl`, lfm3, name_fix_applied_20261117): rewritten supported = True, raw supported = False. Scanning the dev log I also checked 8 rows where the original was unsupported and the rewrite made it supported: all 8 flip under scorer v2.0 in the same direction (not committed as a test). The ablation arms apply the rewrite too, so each differs from M in one component; NO_FINISH has no `final_answer` call and so no rewrite.
Smoke (nf_single_1, qwen3.5:9b, M): the original answer was logged, the rule changed nothing (raw = rewritten = supported).

## 9d-4 Extra models and the ending class
`exam_queue/systems.py`: new ids `EX-M`, `EX-NO_MENU`, `EX-NO_FINISH`, `EX-NO_ERRORTEXT` (the legacy ids, including `M` used by the 2026-11-19 mini exam, keep their meaning). `queue_core.build_cells`: a tier may name its own `models` (default: the spec's core models). The extra-model tier of the draft spec lists llama3.1:8b, ministral-3:8b, granite4.2:8b with EX-M and E1 only. E1's runner takes the model name as a flag, so no new runner was needed; **not run for the extra models** (no episode of E1 or EX-M on them was made today).
**Ending class `validation_abort`** (`queue_core.ending_class`, `exam_tables.CLASSES/CAPPED`): an abort text containing `validation error for ` (pydantic) or `HardToolError` gets its own row and is counted with the no-answer endings in the capped totals. Test: the saved ministral-3:8b p3 abort text maps to it. Suite: the new tests (4 + 4) and the whole queue suite (45 tests, 214 s) pass.

## 9d-5 Forge smoke gate (released Forge, forge-guardrails 0.10.1, fresh isolated env `/tmp/rosa-forge-env-20261121`, installed from PyPI for this gate)
Setup: the pilot's `run_full.py` byte for byte (copied into `research/studies/forge_smoke_gate_20261121/` so that its append-only logs do not touch the frozen pilot folder), driver `gate_driver.py`; tasks u3, p3 (stage 3) and e1h_amb_1, models lfm3:1.7b and qwen3.5:9b, seed 1: 6 episodes, one session per (model, environment). Results rows: `RESULTS_MATCHED.jsonl` there; traces under `research/_artifacts/runs/forge_smoke_gate_20261121/` (run1 stopped before any episode because the queue tests were using the ROS domain, run2 and run3 are the data).

| model | task | requests | native ops | answer object | error |
|---|---|---:|---:|---|---|
| lfm3:1.7b | p3 | 4 | 3 | yes | none |
| lfm3:1.7b | u3 | 11 | 9 | yes | none (1 HTTP non-200 recovered) |
| lfm3:1.7b | e1h_amb_1 | 12 | 9 | yes (not supported) | `_ToolCallExhausted` after 3 failed attempts (unknown_tool) |
| qwen3.5:9b | p3 | 5 | 3 | yes | none |
| qwen3.5:9b | u3 | 5 | 4 | yes | none |
| qwen3.5:9b | e1h_amb_1 | 7 | 5 | **no answer object** | none |

Checklist of draft section 2b: (i) budget unit: Forge's own call budget of 40 including retries; requests and native operations are logged per episode, so both can be reported **(not equal to the ROSA arms' 40 requests; mapping stays "report both")**: pass. (ii) terminal `respond(message: str)` mapped by the frozen last-JSON-object extractor and scored by scorer v2.0: pass (5 of 6 episodes produced an object). (iii) tool set and prompts as documented in the pilot report `forge_baseline_20261115/REPORT.md` (12 read tools + `respond`, C1 system messages with `final_answer` renamed): not re-verified today. (iv) transport explicit: every request body has `think: false`, `num_ctx` 65536, `num_predict` 4096, seed 1, temperature 0.7 (checked in all 44 requests); gpt-oss was not part of this gate and the known `think: false` limitation stays. **(v) token accounting: NOTE, partial:** 43 of 44 requests carry usage; the one non-200 response (lfm3 u3) has none, so Forge's token totals are lower bounds (as in the pilot, 2 of 643). (vi) no write tool reached ROS: 0 write calls in 6 episodes and the runner's `write_reached_ros` guard did not fire: pass. **(vii) stop rule for infrastructure failures: NOTE:** the qwen3.5 stage-3 session stopped after its two episodes at the `after` oracle check ("node not listed" for four fixture nodes, a discovery flake); `run_full.py` has no oracle retry (the exam runners use `OracleWithRetry`, 5 s). A rule exists (the session stops), but an exam adapter must use the retried oracle and classify such a stop; the remaining cell was run as a continuation (run3).
**Gate result: Forge runs end to end under the unchanged released runner, with the two notes above.** Still missing: a queue adapter (`F` stays `runner=None`, its cells are refused) and the budget mapping text for the freeze. Six episodes say nothing about Forge's quality.

## 9d-5 MetaTool smoke gate
**Not run; "not runnable as released" as of 2026-11-21, with this reason.** Located: arXiv 2609.13335, "Bridging Thought and Action: Taming Long-Horizon Instability in Open-Source LLM Agents with a MetaTool-Enhanced ROS Framework" (Mahmud et al., submitted 11 Sep 2026; read from its arXiv abstract and HTML pages, **reported, not independently verified**). The only release is footnote 1 of Section IV-B: an **anonymized review-site link** to a simulation and execution pipeline (not a permanent repository); the paper describes the MetaTool as a prompt-induced pseudo-code plan stored in the ROSA scratchpad with a logic-layer constraint, not as an installable package; its experiments use the Groq API with GPT-OSS-120B (hardware trials) and other large models; no framework version is stated. I did **not** download or run the linked code (unvetted third-party code, an anonymous host, no approval for that step). The pilot's own arm M0 (`supertool` plan-first prompt) is our approximation of the idea, **not** "as released". Decision for the owner: whether to retrieve the anonymized code (and in which sandbox) before the freeze, or to report "not runnable as released" with this reason.

## 9d-8 / 9d-9 Freeze package draft (`final_exam_draft_20261118/freeze_package_20261121/`, not hashed)
`make_exam_spec.py` (generator, `write` and `counts`), `exam_spec_stage1_DRAFT.json` (4 tiers in the owner's order, seeds 1-3, master seed 20261122 as a draft value, pool from the custodian's file named by `ROSA_HELDOUT_V2_TASKS`), `MODEL_DIGESTS_DRAFT.json` (laptop Ollama digests of the 7 models; the 4 core digests equal those of the dev ablation's `FREEZE.json`), `SUCCESS_AND_INVALIDATION_DRAFT.md` (draft section 9c items 4 and 8), `README.md`. Counts with 76 synthetic task ids: tier 1 1,824; tier 2 1,824; tier 3 2,736; tier 4 1,368; total 7,752 = 6,384 core + 1,368 extras (test passes).

## Open search (unfiltered)
- **Held-out adapter missing:** `run_exam.py` scores development tasks only (`T.TASKS`); a held-out task id raises `KeyError`. Until Codex's adapter exists the exam arms cannot score a held-out cell.
- **Session grouping:** the draft spec uses the queue's generic cell order; the dev studies grouped cells in one fixture session per (model, environment). Whether the held-out environments need per-session fixtures is not decided.
- **Tier 2 contains F** without a runner: those 1,824 cells would be refused; the owner may want F as a separate later tier.
- **Name-fix reporting on the ablations:** every arm with a final tool also rewrites, so "M without name fix" exists only for M (from the shadow score); the ablations are scored on the rewritten answer.
- **Forge lfm3 e1h_amb_1:** ended by `unknown_tool` retries (3 failed attempts), and qwen3.5 e1h_amb_1 ended with no answer object and no error; neither was read further. One lfm3 u3 request returned a non-200 response.
- **Queue tests send ntfy "test" messages** through a temporary config (the log shows "topic already exists"); I did not check whether the phone received any.
- **ntfy helper has fixed templates only;** status messages are sent with `send_ntfy` and a fixed text.
- **`/tmp/rosa-forge-env-20261121`** is outside the repository and will vanish on reboot, as the 2026-11-15 one did; its provenance is the pinned version (0.10.1) and this report.
- Not checked: Forge on gpt-oss and bonsai; the E1 or EX-M arms on the three extra models; the laptop GPU contention state during the gate (`gpu_state` was not recorded for these gate episodes).
