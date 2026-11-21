# REPEAT_RATE_MODELS: is the repeat problem general or Qwen-specific? (one measurement, not a stage, not a method)

Addendum: `ROSA_repeat_rate_three_models_addendum.md` (frozen before any run; implementation choices in `REPEAT_RATE_FREEZE.md`). Run: `research/_artifacts/runs/headroom_diagnostic_20261112/repeat_rate_20261114T100614Z` (hash manifest `MANIFEST_REPEAT_RATE.sha256.json`), 72 episodes, all ran; oracle matched before and after each model; cleanup verified empty; no time cap reached. Same Ollama server and harness as `run_smoke.py` (`run_repeat_rate.py`), arm A1 (prompt hash equals Stage 3b), the 12 Stage 3 tasks x 2 repeats per model, Stage 3b Qwen settings (temperature 0, seed 42, `num_ctx` 65536 verified from `/api/ps` for all three, `num_predict` 4096, `reasoning=False`). Counting script: `count_repeats.py` (the Qwen reference row is computed by the same script from the Stage 3b traces and reproduces the hand count: 10 of 24 episodes, 6 of 12 tasks).

## Table
| model | role in rule | supported-complete / 24 | R: supported episodes with an identical successful repeat | distinct tasks with a repeat | identical repeat requests / floor sum | excess share | RED / REC / LATE / NOARG / EXPLORE | harness aborts | requests with more than one call |
|---|---|---:|---|---:|---|---|---|---:|---|
| gpt-oss:20b | independent | 6 | 0 of 6 = **0%** | 0 | 0 / 20 | 0 / 20 = 0% | 0 / 0 / 0 / 0 / 0 | 17 | 0 / 55 (0%) |
| lfm3:1.7b | independent | 10 | 0 of 10 = **0%** | 0 | 0 / 42 | 35 / 42 = 83.3% | 11 / 9 / 10 / 5 / 2 | 1 | 3 / 183 (1.6%) |
| ornith-1.5:9b | reported, not in rule | 14 | 4 of 14 = 28.6% | 2 (p2, u2) | 4 / 50 | 18 / 50 = 36.0% | 4 / 4 / 4 / 2 / 4 | 6 | 16 / 112 (14.3%) |
| qwen3.5:9b A1 (reference, Stage 3b) | reference | 24 | 10 of 24 = 41.7% | 6 (h2, h4, u2, u3, u4, v2) | 18 / 96 | 47 / 96 = 49.0% | 22 / 11 / 10 / 0 / 4 | 0 | 4 / 143 (2.8%) |

R, repeat counts, floor sum and excess are over supported-complete episodes; aborts and the multi-call share are over all 24 episodes (aborts = episodes ending in an error or without an answer). Codebook labels are per request (not capped) in supported episodes with excess, so RED can exceed the identical-repeat count (RED also covers `param_list` on a node when the parameter name is in the task, and subset repeats).

## Outcome under the frozen rule: QWEN-SPECIFIC
- A model qualifies with at least 8 supported-complete episodes. **lfm3:1.7b qualifies (10); gpt-oss:20b does not (6).**
- Rule 1 (GENERAL: a qualifying independent model with R >= 25% from >= 3 tasks): no; the one qualifying model has R = 0%.
- Rule 2 (QWEN-SPECIFIC: every qualifying independent model has R < 10%): yes; lfm3 has R = 0% (0 of 10).
- Rule 3 (INCONCLUSIVE) is not reached, because one independent model qualifies.
- Under the decision made in the addendum, the repeat branch is closed as the main target and the next target is chosen from the per-model excess breakdown above; no new measurement run.

## How firm that is (read before using it)
- It rests on **one** qualifying model. lfm3 reached 10 supported episodes only by failing 13 of 24 (wrong answers), so its supported episodes are the easy ones and cover 6 tasks (h2, h3, h4, p2, u4, v4); a model that mostly fails cannot show a repeat in episodes it completes. Across all 24 lfm3 episodes (supported or not) there are 0 identical successful repeats.
- gpt-oss:20b lost 17 of 24 episodes to harness aborts, all schema-validation errors on arguments it sent (a blank string where the tool wants a list, a missing required `topics` or `node_name`), so it produced almost no data for the rule; across all 24 gpt-oss episodes there are 2 repeat requests in 1 episode. Had it qualified at R < 10% the outcome would not change; had its aborted episodes been completed, the answer is unknown.
- ornith-1.5:9b is not in the rule. It shares Qwen's architecture (`qwen35`) and repeats in 4 of 14 supported episodes (28.6%, 2 tasks); the addendum's reading is that this speaks to architecture versus weights. With 4 episodes from 2 tasks and no known lineage for ornith (`MODEL_FAMILIES.md`), the data cannot separate architecture from shared training lineage.
- Per-model excess breakdown (for choosing the next target, per the addendum): gpt-oss none in 6 supported episodes; lfm3 83.3% over the floor, mixed (repeat-like RED 11, recovery after errors REC 9, serial late calls LATE 10, extra no-argument calls NOARG 5, EXPLORE 2); ornith 36.0%, spread evenly across all five kinds; Qwen 49.0%, dominated by RED (22) and REC (11). I did not pick a target.

## Settings and anything not set identically
- The `reasoning=False` flag was sent to every model as in the smoke test. Whether each model honoured it is not known: gpt-oss reasons internally (the addendum notes it), and no model was checked for hidden reasoning. lfm3 had 2 episodes with a length stop at 4096 output tokens.
- `/api/ps` reported context 65536 for all three (lfm3 shared the GPU with a still-loaded gpt-oss for part of its run; this does not change the context).
- Harness aborts (logged, counted as not supported, no retries, no argument fixes): gpt-oss 17 (schema validation on `blacklist`, `topics`, `node_name`); lfm3 1 (a glob passed as a regular expression to `ros2_node_list`, `re.error`); ornith 6 (4 `StatisticsError` from the stock `mean` math tool called on one number, 2 `ros2_service_call` with a dict request rejected by the schema, the same class as Qwen under A2).
- The Stage 3 labeller (`stage3_labels.py`) raises on a null argument (gpt-oss), so the labels were produced by `design_inputs/review_robust.py`, which runs the unchanged `stage3_review.py` with one guard (a call with a null argument counts as outside the plan). On the lfm3 and ornith runs it produced byte-identical labels to the unguarded script.

## Limits (as required)
Synthetic fixture. At temperature 0 the two repeats are near-duplicates, so there are about 12 independent units per model (gpt-oss 6 supported episodes, lfm3 10). One labeller. gpt-oss reasons internally, but the metric counts requests, not tokens. The identical-repeat definition is strict (same name and parsed arguments, earlier request, earlier success), so it is lower than the `REPEATS_READING.md` counts that also included subset repeats.
