# Derailment study: what comes before the first wasted request (2026-11-20)

Offline, CPU only, saved traces only. Protocol frozen first ([PROTOCOL.md](PROTOCOL.md), hashes in [FREEZE.json](FREEZE.json), commit 63ad6e1), script after ([derail.py](derail.py)). Numbers: [results.json](results.json), one row per episode: [derail_rows.jsonl](derail_rows.jsonl). Post hoc extras (labelled): [posthoc.py](posthoc.py), [posthoc.json](posthoc.json). Nothing was built or run on a model.

## Top box
- **Populations:** P1 = 288 loss-map episodes, P3 = 144 FULL-arm episodes of the list-values run (the frozen classifier applied unchanged, no row dropped). Pooled 432 episodes: **206 derailed (48%), 226 clean**. Derailment point (first format/repeat/name_guess request): median request 2, but **64 of 206 (31%) derail at request 1**.
- **"Waste after" is not "caused by".** 1,097 waste requests follow the 206 derailment points; 58% of them are in episodes that ended unsupported.
- **The three triggers with the most waste after them (pooled, primary category by the frozen precedence):**

| # | Trigger | Derailed episodes | Waste after (mean) | Ended unsupported ("never") | Derailment rate per context | Models (waste after) |
|---|---|---|---|---|---|---|
| 1 | **6 none** (clean short success, or task-only first request, in a task with no special class) | 64 (P1 41, P3 23) | **548** (8.6) | **21** | 10.4% (64/614); 13.1% for the underlying class (157/1,196) | bonsai 362, lfm3 100, gpt-oss 78, qwen 8 |
| 2 | **5 scripted change** (e1h_chg) | 45 (P1 30, P3 15) | 177 (3.9) | 8 | 37.5% (45/120) | bonsai 139, gpt-oss 15, qwen 12, lfm3 11 |
| 3 | **2 split name** (`Node name:` then `Node namespace:`, next call uses one field) | 45 (P1 30, P3 15) | 166 (3.7) | 7 | 100% by construction; **context-only 26% use a field, 38% derail** (45 and 67 of 175 split contexts) | bonsai 64, lfm3 57, qwen 27, gpt-oss 18 |

  (Category 4, absent/ambiguous task: 48 episodes, 155 waste, 1 never. Category 3 long result: 2 episodes but 49 waste, both never. Category 1 error result: 2 episodes.)
- **Which triggers end in "never recovered":** category 6 (21 of 64 = 33%) and category 3 (2 of 2). Category 2 recovers quickly in 33 of 45; category 4 almost never ends unsupported (1 of 48).
- **Models:** bonsai has 24 of the 40 "never" episodes (of 49 derailed), gpt-oss 8, lfm3 8, qwen3.5 0 (of 32 derailed).
- **Largest single cluster (post hoc, labelled):** the task-only context of request 1. 64 first-request derailments carry 459 of the 1,097 waste-after requests. gpt-oss: 39 of 108 episodes (36%) start with a rejected list-tool call (`blacklist: ""` is not an array), mean waste after 3.8, 2 never. bonsai: 13 first-request derailments, mean waste after 20.2, 9 never (6 are task v2, `service_info` on `cedar_reset`, the reverse-lookup task).
- **Possible fix to size later (not proposed, not built):** accept `blacklist: ""` as null in the list tools (the 39 gpt-oss first requests).
- **What it cannot show:** that any trigger causes the derailment; the labels are detectors.

## 1. Measured

### 1.1 Population and the derailment point
| | Episodes | Derailed | Clean | Supported (derailed / clean) | Derailment type: name_guess / format / repeat | At request 1 | Median index (range) | Waste after |
|---|---|---|---|---|---|---|---|---|
| P1 | 288 | 141 | 147 | 116 / 127 | 55 / 55 / 31 | 46 | 2 (1-22) | 646 |
| P3 | 144 | 65 | 79 | 50 / 73 | 24 / 27 / 14 | 18 | 2 (1-6) | 451 |
| Pooled | 432 | 206 | 226 | 166 / 200 | 79 / 82 / 45 | 64 | 2 (1-22) | 1,097 |

Per model (pooled, 108 episodes each): derailed bonsai 49, gpt-oss 69, lfm3 56, qwen3.5 32; unsupported bonsai 37, gpt-oss 9, lfm3 18, qwen3.5 2. Per task: `results.json` -> `POOLED.by_task`. Derailment rate is highest in e1h_chg_1/2 (23 and 22 of 24), h4 (21), u3 and v2 (16), nf_multi_1 (16); lowest in p3 (3), nf_exact and nf_abs/amb tasks (5-10).

### 1.2 Key table: trigger category x outcome (episodes / waste after)
Outcome rule (frozen): `never` = episode unsupported (includes capped); else `quick` if a productive request follows within 3, else `slow`. Supported counts per cell are in `results.json` (`key_category`).

| Category | P1 eps / waste / never | P3 eps / waste / never | Pooled eps | Pooled quick / slow / never | Pooled waste (mean) | Median derail index |
|---|---|---|---|---|---|---|
| 1 error result | 2 / 2 / 1 | 0 | 2 | 0 / 1 / 1 | 2 (1.0) | 5.5 |
| 2 split name | 30 / 121 / 5 | 15 / 45 / 2 | 45 | 33 / 5 / 7 | 166 (3.7) | 2 |
| 3 long result | 1 / 11 / 1 | 1 / 38 / 1 | 2 | 0 / 0 / 2 | 49 (24.5) | 3.5 |
| 4 absent or ambiguous task | 37 / 125 / 1 | 11 / 30 / 0 | 48 | 30 / 17 / 1 | 155 (3.2) | 1 (42 of 48 at request 1) |
| 5 scripted change | 30 / 81 / 4 | 15 / 96 / 4 | 45 | 33 / 4 / 8 | 177 (3.9) | 3 |
| 6 none | 41 / 306 / 13 | 23 / 242 / 8 | 64 | 16 / 27 / 21 | 548 (8.6) | 2 (17 at request 1) |

By model (pooled, episodes / waste / never): category 6: bonsai 22 / 362 / 12, gpt-oss 22 / 78 / 3, lfm3 12 / 100 / 6, qwen3.5 8 / 8 / 0. Category 5: bonsai 12 / 139 / 4, gpt-oss 12 / 15 / 4, lfm3 9 / 11 / 0, qwen3.5 12 / 12 / 0. Category 2: lfm3 22 / 57 / 0, bonsai 10 / 64 / 6, qwen3.5 10 / 27 / 0, gpt-oss 3 / 18 / 1. Category 4: gpt-oss 32 / 97 / 0 (mostly request-1 schema rejections, see 1.5), lfm3 10 / 44 / 0, bonsai 4 / 10 / 1, qwen3.5 2 / 4 / 0.

**Underlying category** (skip 4 and 5, descriptive): category 6 holds 157 of 206 derailments, 880 of 1,097 waste, 30 of the 40 never; 2 split = 45, 3 long = 2, 1 error = 2. The task classes 4 and 5 therefore take their episodes from the "none" group, not from the result-based groups.

### 1.3 Category 1: error texts after which the first waste came
Only **2** derailments have an error result in the previous request, both P1, both lfm3 (top 10 would be 2 rows):
1. `ros2_node_info | {"error": "Unable to find node '<N>'"}`: 1 episode, waste after 1, slow, `research/_artifacts/exam/lossmap/runs_all/block_0002/017-e1h_abs_1-FULL-lfm3_1.7b-s8/trace.jsonl`
2. `ros2_node_info | {"error": ""}`: 1 episode, waste after 1, never, `.../block_0003/026-nf_amb_1-FULL-lfm3_1.7b-s8/trace.jsonl`

This is structural, not a finding about errors: in this classifier a failed call to an unknown name IS the derailment (name_guess), and a failed read of a known name is rare. An error is the derailing request's own result, not its trigger. The error class of that own result is in 1.5.

### 1.4 Derailment rate per trigger context (hazard per context)
An exposure is a (episode, request k) context before the first derailment (all contexts of clean episodes); it derails if request k+1 is the derailment point. Pooled, primary category: cat 1 2/83 (2.4%; 61 of the exposures in clean episodes), cat 2 45/45, cat 3 2/13 (15%), cat 4 48/462 (10.4%), cat 5 45/120 (37.5%), cat 6 64/614 (10.4%). Underlying: 1 = 2.4%, 2 = 100%, 3 = 15.4%, 6 = 13.1% (157/1,196). P1 and P3 agree (cat 6 10.0% and 11.3%; cat 5 37.5% in both). Per model, category 6: bonsai 14.5%, gpt-oss 15.7%, lfm3 7.4%, qwen3.5 5.0%; category 4: gpt-oss 44.4% (the request-1 rejection), bonsai 2.6%, lfm3 9.3%, qwen3.5 1.6%.
- **Category 2 is 100% by construction**: the frozen definition includes "the next call uses one field", which is the derailment. The context-only version (post hoc, `posthoc.json` `B_*`): 175 contexts with a `Node name:`/`Node namespace:` pair before any derailment, in 161 episodes; the next request used a single field in 45 (26%, matches the 45 above), was a name_guess in 48 (27%), any derailment in 67 (38%). By model (contexts / name_guess next): lfm3 38 / 23 (61%), bonsai 46 / 12, qwen3.5 50 / 10, gpt-oss 41 / 3. So the pattern is real for lfm3, present for bonsai and qwen3.5, and mostly absent for gpt-oss.
- **Exposure counts are per context, not per episode.** Category 5 is high partly because most chg episodes re-read the same parameter by design; the classifier calls that a repeat (see 2).
- Error-class exposure rates (cat 1 sub-classes): not-found 1/52, empty 1/17, other 0/14. Too few for any conclusion.

### 1.5 The derailing request's own result (post hoc, labelled, not the trigger)
69 not-found (name_guess; bonsai 18, lfm3 35, qwen 12, gpt-oss 4), 44 repeat with no failed call (gpt-oss 12, lfm3 13, qwen 12, bonsai 7), 26 `Invalid arguments for ros2_node_list` (gpt-oss, 25 at request 1), 20 format with no failed call (a request with no rejected call, in the classifier's rule a request without tool calls: gpt-oss 11, bonsai 8, lfm3 1), 11 `final_answer` validation (qwen3.5 8: answer fields given at top level), 9 regex errors in the `pattern`/`blacklist` argument of list tools (bonsai 5, lfm3 4), 9 `ros2_topic_list` and 5 `ros2_service_list` validation (gpt-oss), 5 empty `{"error": ""}` (bonsai 4 at request 1), 7 other. **First-request derailments by model:** gpt-oss 39 (all validation of a list-tool argument), bonsai 13, lfm3 10, qwen3.5 2. Hazard of a request-1 derailment per episode: gpt-oss 36%, bonsai 12%, lfm3 9%, qwen3.5 2%.

### 1.6 Hand reading (10 derailment points, pooled, seed 20261120, stratified 3/3/2/2 by sorted model)
| # | Episode | Assigned | My reading |
|---|---|---|---|
| 1 | bonsai e1h_chg_1 s8 (`.../block_0011/021-...-bonsai-2_4b-s8`), repeat of `param_get quasar level` at request 2 | 5 | Category right. But the repeat returned a **changed** value (30 -> 45): a legitimate re-read after the scripted change, so the derailment label is doubtful. |
| 2 | bonsai nf_multi_1 s6, `param_list lathe` after `topic_info` showing `Node name: lathe` | 2 | Right. |
| 3 | bonsai nf_multi_1 s8, `param_list zenith/xylem/mortar` after the same result | 2 | Right (the result lists several nodes; the model used bare names). |
| 4 | gpt-oss nf_absent s10 (P3), request 1 `node_list` with `blacklist: ""` rejected | 4 | Right by rule, **not explanatory**: the cause is a schema error on the first call; the task class is irrelevant. |
| 5 | gpt-oss e1h_abs_2 s6, same rejection | 4 | Same as 4. |
| 6 | gpt-oss e1h_amb_1 s6, same rejection | 4 | Same as 4. |
| 7 | lfm3 nf_single_1 s9 (P3), `node_info bobbin` after `topic_info` with `Node name: bobbin` | 2 | Right. |
| 8 | lfm3 v2 s6, `node_list pattern '*cedar*'` rejected (regex error) after a 5,039-character service list | 3 | Right by rule, **not explanatory**: the error is a glob typed as a regex; the long result is incidental. |
| 9 | qwen3.5 nf_single_1 s6, `final_answer` without the `answer` wrapper after a split result, where the model had joined the fields correctly (`/nf/lantern/bobbin`) | 6 | Right (no split misuse); the trigger is uninformative, the cause is the answer schema. |
| 10 | qwen3.5 u3 s10 (P3), `node_info yarrow` after `topic_info` with `Node name: yarrow`, `Node namespace: /plant32` | 2 | Right. |

6 of 10 assignments are right and explanatory (1 with a doubtful derailment label), 4 are right by rule but the real trigger is an argument-format error that no category names (3 of them at request 1). Assignments were not changed in the numbers.

## 2. Interpretation (limited to what was measured)
- The frozen trigger list explains the name-splitting pattern well (category 2: the same `Node name:`/`Node namespace:` result is followed by a name_guess in 27% of contexts, 61% for lfm3) and says little about the rest. 157 of 206 derailments fall in the underlying "none" group, and category 6 plus its first-request part (64 episodes at request 1) holds the biggest and most unrecoverable excess. Part of what the "none" label hides is an **argument-format error on the first call** (gpt-oss list tools, bonsai/lfm3 regex patterns) and **a name guess from the task text alone** (bonsai on v2: `service_info cedar_reset`, empty error, never recovered in 6 of 6 bonsai v2 episodes in these data).
- Derailments after a long result are rare (2) but both did not recover; n is too small to rank.
- Errors do not precede the first waste; they ARE the first waste. A mechanism acting on errors therefore acts after the derailment, where the earlier sizing found recovery runs harmed (C4). The trigger table does not contradict that: after the derailment, 166 of 206 episodes still ended supported.
- Waste after the first derailment is concentrated: 21 + 8 + 7 never-episodes in the three top categories, bonsai 24 of 40. For gpt-oss the dominant derailment (36% of episodes) is cheap (3.8 waste, 2 never); for bonsai a first-request derailment is expensive (20.2, 9 never).
- **e1h_chg repeats may not be waste.** In the scripted-change tasks the classifier counts a re-read after the change (a `repeat`) as waste, 39 of the 45 category-5 derailments. In hand reading #1 the value had changed. So category 5's 177 waste-after requests are an upper bound on real waste. Its 8 never-episodes are 4 bonsai name_guess runs (17, 14, 40, 40 waste) and 4 gpt-oss repeat runs (1-2 waste).
- Not shown: causation, any effect of removing a trigger, held-out behaviour.

## 3. Limits and deviations
- The classifier is a detector (see `loss_map_20261120/CLASSIFIER_NOTES.md`). Outcome `never` uses the scorer's supported/unsupported, so an episode that returned to productive requests quickly but ended wrong counts as never (the distance d to the first productive request is in `derail_rows.jsonl`).
- Waste after is every waste-typed request from the derailment on, not only those caused by it.
- Exposure rates are per context and not independent (contexts within an episode).
- P1 and P3 share tasks and models; they are not two independent samples.
- Deviations: (1) the frozen category 2 rate is tautological (shown above, with a post hoc context-only version); (2) category 1 is empty by construction (shown above); (3) section 1.5, the split-context rate, the first-request by model tables and the v2 note are post hoc and labelled; they replace nothing. No protocol text was edited after the freeze.

## 4. Open search (unfiltered, counts and trace paths)
- **gpt-oss list-tool argument schema:** 26 `node_list`, 9 `topic_list`, 5 `service_list` rejections, 39 of them at request 1; `research/_artifacts/exam/lossmap/runs_all/block_0008/016-e1h_abs_2-FULL-gpt-oss_20b-s6/trace.jsonl` and `.../listval/runs_all/block_0009/004-nf_absent-FULL-gpt-oss_20b-s10/trace.jsonl`.
- **bonsai v2:** 6 derailed episodes, 196 waste-after requests, all never; first request `service_info cedar_reset` -> `{"error": ""}`; cap-length (40) runs: `.../lossmap/runs_all/block_0010/007-v2-FULL-bonsai-2_4b-s7/trace.jsonl`, `.../listval/runs_all/block_0010/003-v2-FULL-bonsai-2_4b-s9/trace.jsonl`, `.../block_0010/004-v2-FULL-bonsai-2_4b-s10/trace.jsonl`. This is the reverse-lookup relation of the earlier C2 sizing, now seen at the first request.
- **Largest other never-episodes:** lfm3 nf_exact s7 (39 waste, repeat at request 2, `.../lossmap/runs_all/block_0003/007-nf_exact-FULL-lfm3_1.7b-s7/trace.jsonl`); bonsai nf_multi_2 s9 (36, format at request 5), bonsai nf_single_2 s5 (34).
- **20 `format` derailments with no tool call at all** (bonsai 8, gpt-oss 11, lfm3 1), all later than request 1.
- **qwen3.5 `final_answer` shape error** (8 of its 32 derailments): fields given at the top level without `answer`.
- **Derailment index vs cost:** request 1: 64 episodes, mean waste after 7.2, 11 unsupported; index 2-3: 117, 3.7, 17; index >= 4: 25, 8.1, 12 unsupported (late derailments end unsupported in 48%).
- Not checked: whether episodes that did not derail owe it to a different first call (a clean episode is defined by labels only).

## 5. Reproduce
`PYTHONDONTWRITEBYTECODE=1 nice uv run python research/studies/derailment_20261120/derail.py` then `posthoc.py` (asserts the frozen hashes).
