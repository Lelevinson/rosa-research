# Turtlesim dev action tasks: post-action-state switch OFF vs ON

2026-11-18, Asia/Taipei. Frozen protocol [PROTOCOL.md](PROTOCOL.md) (SHA-256 `5f899cbe3ce3e549ba23767ee146b24b2831bbe3e9440fc2598f253dd6ff050b`); code frozen by hash (`FREEZE.json`, checked at run start); analysis `analyze_action.py` applied the reading rule. Smoke (6 episodes, qwen3.5:9b) clean. Full run 19:36-20:04, 128 episodes (8 authored dev/targeted tasks x 4 models x seeds 1-2 x OFF/ON), 0 infrastructure failures, 0 locked executors, turtle still and no leftover `turtlesim_node` in every episode. **Development / targeted evidence only: tasks authored with knowledge of the method, turtlesim, not blind, not held-out.** Rows: `RESULTS_LOG.jsonl`; numbers: `results.json`; traces: `research/_artifacts/runs/action_dev_switch_20261118/full_20261118T113619Z/`.

## Measured (64 episodes per arm)
| | OFF | ON |
|---|---|---|
| success (independent ground-truth judge, as frozen) | 45 | 47 |
| model requests | 216 | 203 |
| input + output tokens | 133,544 | 128,139 |
| verification calls (pose read after a goal was sent) | 54 (0.84 per episode) | 42 (0.66 per episode) |
| rotate calls / goals sent | 94 / 86 | 95 / 86 |
| capped or backend-error endings | 1 | 1 |
Paired cells (task, model, seed): both succeed 42, OFF only 3, ON only 5, neither 14.
By model (success, requests, verification calls; OFF -> ON): lfm3 12 -> 12, 56 -> 53, 14 -> 13; qwen3.5 15 -> 15, 56 -> 55, 14 -> 13; gpt-oss 3 -> 5, 55 -> 54, 13 -> 12; bonsai 15 -> 15, 49 -> 41, 13 -> 4.
By kind (success, requests, verification; OFF -> ON): single 17 -> 18, 76 -> 71, 22 -> 17; act-then-read 13 -> 13, 50 -> 47, 10 -> 9; two-step 15 -> 16, 90 -> 85, 22 -> 16. On the heading-only tasks (S1-S3, M1-M3) verification per episode 0.92 -> 0.69. R2, where the position had to be read under OFF, is 8 -> 8 verification calls: models read the pose even with the line present.
Guard behaviour: every rotate that was sent succeeded (86 SUCCEEDED in each arm); 8 + 8 REJECTED for theta 4.0 (S3, the range trap; all recovered with the equivalent heading), 1 REJECTED in ON for a non-number.

## Frozen reading rule
Verification drop 22% (bar 25%) with all four models lower, but 9 of the 12 saved calls are bonsai's (13 -> 4); requests drop 6% (bar 10%); tokens -4%. Signal V not met, signal E not met, no harm flag. **Class B: no evidence of an effect in these cells.** A difference of this size is far inside the noise (about 9 cells of success, about 21% in requests).

## Judge limitation and a labelled post-hoc re-judge
The frozen judge accepts an answer object or a JSON string of one; it does **not** unwrap `{"answer": {...}}`. gpt-oss ended 34 of its 64 episodes with a text reply of that wrapped form, so 28 of its 32 failures (3/16 OFF, 5/16 ON) are format artefacts: its true headings were right. I did not patch the judge. Post-hoc (`posthoc_unwrap.py`, not the reported result): unwrapping one `{"answer": ...}` layer, with the frozen judge otherwise unchanged, changes 24 rows and gives **58 of 64 in both arms** (gpt-oss 16/16 in both arms; lfm3 12/12; qwen3.5 15/15; bonsai 15/15). The remaining 6 failures per arm are lfm3 (turtle did not turn, or stopped at 1.488: 8 episodes of both arms) and 2 qwen3.5 cases. The class does not change either way. This is a defect in my judge for this loop's text endings, to fix before any later run (a revision, not a patch of this result).

## Interpretation (labelled)
- Attaching the robot's own state to the result did not measurably change success, requests or tokens here; verification reads fell by about a fifth, mostly through bonsai. Whether that is an effect or noise cannot be told from 64 episodes per arm, and the tasks are the ones built so the line carries information.
- The guard and executor behaved as designed under four small models: no write outside the typed tool, no goal beyond the budget, no lock, and the out-of-range request (S3) was rejected before any motion in all 16 episodes.
- Not shown: any benefit on tasks where the state is not needed; Nav2/TurtleBot3 behaviour (lifecycle, TF, partial cancels); blind task design; original ROSA on action tasks.

## Limits
8 authored tasks, 4 models, 2 seeds, one simulator; Ollama sampling not guaranteed reproducible; trajectories diverge so pairing is descriptive; the judge defect above; verification is defined as a pose read after a goal was sent, so the required read in R2 counts.

## Correction note (2026-11-19; the text above is left unchanged)
Recounted from `RESULTS_LOG.jsonl` (128 episodes, 32 per model, 16 per model and arm; see `../final_exam_draft_20261118/NUMBER_RECONCILIATION_20261119.md`). In "Judge limitation and a labelled post-hoc re-judge": "gpt-oss ended 34 of its 64 episodes with a text reply of that wrapped form, so 28 of its 32 failures (3/16 OFF, 5/16 ON) are format artefacts" is wrong. Correct: gpt-oss has 32 episodes; **24 of them (13 of 16 OFF, 11 of 16 ON) ended with the `{"answer": {...}}` wrapper, and its frozen failures are 13 OFF + 11 ON = 24, i.e. 24 of 24 are format artefacts**. The 24 rows changed by unwrapping are all gpt-oss rows (failure to success), which is what gives 45 + 13 = 58 and 47 + 11 = 58 of 64. "The remaining 6 failures per arm are lfm3 (8 episodes of both arms) and 2 qwen3.5 cases" omitted bonsai: remaining failures are lfm3 4 + 4, qwen3.5 1 + 1, bonsai 1 + 1 (12 in all). The frozen results, the reading rule and the class (B) are unchanged.
