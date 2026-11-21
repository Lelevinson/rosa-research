# Dead-end relation lookup, offline replay: result = class C (harm flag), not adopted

2026-11-18, Asia/Taipei. Frozen protocol [PROTOCOL.md](PROTOCOL.md) (SHA-256 `47914f4c405eff77a55e6ef5a8e9582b11c94d29759b84b5f33bf2f34f28d99d`), hashed before the script existed; script and tests hashed in `SCRIPT.sha256` before the first count. CPU only (`nice`), Ollama and the running GPU job not touched, no held-out files opened. Population: the 1,832 saved episodes of `candidate_counts_20261118` (not independent: tasks, seeds and fixtures recur). Development evidence only. Outputs: `results.json`, `fires.jsonl` (918 fires with their lines), `episodes.jsonl`. 8 unit tests pass.

## Top box
- **Result:** B1, B2, B3 are met as written, **B4 (harm) is not**: in both `ABS` tasks every fire produced a look-alike line (207 fires, 204 of 312 `ABS` episodes). Frozen class **C**: reported, not adopted, no live run.
- **What it changes:** nothing in the method. It closes this form of the candidate (whole-segment graph lines on every dead end) for this week.
- **What it cannot show:** whether a model would be misled; no model saw the lines. 160 of the 204 `ABS` episodes with a look-alike fire were supported in the recorded run (the models answered "absent" correctly without it).
- **System acts or model must adopt:** the system acts (appends lines); the model must still read them and choose, and that is untested.
- **Cost:** at most about 150 tokens per fire (600-character cap); counted over the requests that follow each fire (the lines stay in the history), 22,701 added tokens over the 241 FULL-type fires; plus a graph read (native ROS operations, not counted).

## Measured
FULL-type subset (the 12-tool loop, 416 episodes, 3,020 requests) and all 1,832 episodes. Dead-end classes over all fires: a (not found) 883, b (empty error) 61, c (empty) 2. `graph_has_it` fires (entity exists, e.g. a parameter was missing): 28 (3 FULL-type), no lines made.

| | FULL-type | all |
|---|---|---|
| episodes with a fire | 158 / 416 (38.0%) | 591 / 1,832 |
| fires (real) | 241 | 918 |
| fires with empty lines (nothing matched) | 50 | 168 |
| fires in tasks with a needed entity | 196 | 706 |
| covered (lines contain a needed entity) | 131 (66.8%) | 458 (64.9%) |
| covered-new (entity not seen earlier in the episode) | 72 (36.7%) | 244 (34.6%) |
| requests after the first dead end, sum / median | 1,154 / 5 | 4,037 / 4 |
| saved-max requests (upper bound) | 146 (4.8% of 3,020) | 558 |
| tokens added / tokens of saved-max requests | 22,701 / 1,294,151 | 90,606 / 4,938,679 |
| look-alike fires | 145 | 585 |
Truncation by the 10-line or 600-character cap never happened. Models with at least 5 episodes with a fire (FULL-type): bonsai 53, lfm3 63, qwen3.5 33, gpt-oss 9. Saved-max by model (FULL-type): bonsai 75, lfm3 55, gpt-oss 14, qwen3.5 2.

**Bars (as written):** B1 met (38.0% of episodes; 4 models with 5 or more). B2 met (64.9% covered, 458 covered fires, 4 models; covered-new 34.6% >= 25%). B3 met (4.8% >= 3%; tokens added far below tokens saved-max). **B4 not met** (see below). Top task share of covered fires: `h4` 37.3% (not above the 60% flag).

## Strata (reported separately as requested)
| stratum (all arms) | episodes | with fire | fires | empty-line fires | covered / fires in tasks with a needed entity | saved-max | look-alike fires |
|---|---|---|---|---|---|---|---|
| `V2` | 220 | 102 | 301 | 158 | 102 / 301 (33.9%); covered-new 25 | 260 | 24 |
| `ABS` | 312 | 204 | 207 | 0 | no needed entity (the answer is "absent") | 0 | **207** |
| `OTHER` | 1,300 | 285 | 410 | 10 | 356 / 405 (87.9%); covered-new 219 | 298 | 354 |
- **`ABS`:** `e1h_abs_1` asks about `/ember/mistral`, `e1h_abs_2` about `/alder/pewter`; the graph has `/e1h/ember/mistral` and `/e1h/alder/pewter`. All fires are on the asked name (106 and 98 of the 207, plus 3 on variants) and every one yields `ember appears in: node /e1h/ember/mistral` style lines. In the recorded run, 85 of 106 (`abs_1`) and 75 of 98 (`abs_2`) of those episodes were supported, i.e. the correct answer is "absent" and the lines would point at a node that is not the asked one. Per model, episodes with such a fire: lfm3 75, qwen3.5 70, bonsai 58, gpt-oss 1. Which of the 204 would be misled is unknown.
- **`V2`:** the dead-end names are mostly `/plant32/cedar` (58) and `/cedar` (26), a segment that is not a whole segment of the service `/plant32/cedar_reset`; whole-segment matching returns nothing for 158 of 301 fires. Coverage is therefore low (33.9%) and saved-max is 260 requests over all arms (60 in the FULL-type subset).
- **`OTHER`:** high coverage (87.9%), mostly `h4` and `u3` (short names such as `/anvil` that resolve to `/plant32/anvil`).

## Interpretation (labelled; hypotheses, not measurements)
1. **The same line is a help and a harm.** Outside `ABS`, 373 fires also met the look-alike rule, and 319 of them are covered fires (a short name resolved to the needed full name). The look-alike rule is blind to whether the asked name is a mistaken short form or a deliberately absent absolute name; the lines cannot tell either. That is the mechanism-level reason the `ABS` flag is not an artefact of the rule: it is the same lookup. (H: a trigger that depends on the shape of the asked name could separate them; not tested, and it would be a different protocol.)
2. **B3 rests on an assumption.** 98 of the 146 FULL-type saved-max requests come from 14 episodes in which the covered entity never appeared in a later result, so the bound counts all remaining requests except the last. Without those episodes saved-max is 1.6% of requests, under the 3% bar. B3 is met as written, but it is the weakest of the three.
3. **The benefit is concentrated in the weak models and two tasks.** Saved-max (FULL-type): bonsai 75, lfm3 55; qwen3.5 2; by task `v2` 60, `h4` 57, `u3` 20. This is the same bonsai/lfm3 tail seen in every earlier study.
4. **Whole-segment matching misses `cedar` -> `cedar_reset`.** A substring rule would cover it and would also produce more look-alikes; I did not run it (post-hoc variants need a new protocol).

## Limits and defects (reported, not patched)
- Recorded traces only: models never saw the lines. "Covered" means the lines contain the entity, not that a model would use it; saved-max assumes it would.
- The `ABS` fixtures are built so that the asked name is a suffix of a real node; the harm is large by design. Whether real operators ask such questions is not measured here.
- Look-alike rule counts both help and harm outside `ABS` (interpretation 1); only the `ABS` count is used as the bar.
- The `graph_has_it` class was defined from entity existence; its 28 fires are not analysed further.
- Tasks, seeds and arms recur, so counts are not independent; the empty-line share for `V2` depends on the whole-segment rule fixed before the count.
- Teammate-context check (`rosa-contexts`) not done.

## Decision for the owner
Class C by the frozen rule: no live run is proposed. If you want a variant (for example a trigger conditioned on the form of the asked name, or only on names that appear in no listing), it needs its own protocol; I have not designed or run one.

## Correction note (2026-11-19; the text above is left unchanged)
Interpretation 1 says "Outside `ABS`, 373 fires also met the look-alike rule"; the strata table gives V2 24 + OTHER 354 = **378** look-alike fires outside the two `ABS` tasks. Both are right under different definitions: 378 excludes the two `ABS` tasks (`e1h_abs_1`, `e1h_abs_2`); 373 also excludes the task `nf_absent` (another absent-target task, stratum OTHER, 5 look-alike fires). 319 of the 373 are covered fires. No bar or class changes. See `../final_exam_draft_20261118/NUMBER_RECONCILIATION_20261119.md`.
