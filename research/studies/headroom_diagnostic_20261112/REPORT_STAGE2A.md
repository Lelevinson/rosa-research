# Stage 2a report: offline replay of learned speculative result expansion (2026-11-13)

Offline replay on recorded traces: no inference, API, fixture or repository edit. Frozen plan `PROTOCOL_STAGE2A.md`; every number in `replay_stage2a.json`, tables in `STAGE2A_TABLES.md`, code `replay_stage2a.py` and `summarize_stage2a.py`. Development evidence, no novelty claim, no selected algorithm. A replay shows which requests would have been covered; it does not show answer support, latency, or that the model would act the same with extra results appended.

## Result: the frozen kill bar fires
Evaluated at tau 0.7 on Qwen A0 (63 requests), leave-one-task-out:
- **(a) under 10% saving: fires.** Learned removes 6 of 63 = 9.5% (one more request would have been 11.1%, so this one is close).
- **(b) does not beat static top-1: fires.** Learned 6 versus static top-1 10 (15.9%). At tau 0.5 learned is still 6; at 0.9 it is 0. It never beats the static rule at any tau.
- (c) one task only: does not fire (t2, t3, d2 contribute).
The direction is stopped under the bar. 0.5 and 0.9 are reported and do not change that.

## Numbers (primary non-chained count; chained count is within one request of it)
| | requests | oracle | learned 0.5 | learned 0.7 | learned 0.9 | static top-1 |
|---|---:|---:|---:|---:|---:|---:|
| Qwen A0 removed | 63 | 14 (22%) | 6 (9.5%) | 6 (9.5%) | 0 | 10 (15.9%) |
| Luna A0 removed | 45 | 10 (22%) | 2 (4.4%) | 1 (2.2%) | 1 | 2 (4.4%) |
Per-task saving at 0.7 for Qwen (t1, t2, t3, d1, d2, x1): 0, 17, 33, 0, 17, 0 %. All 6 removals are one request type: `node_info` over all nodes right after `node_list`, in t2, t3 and d2 (one per episode). Static top-1 also removes the t1 and x1 requests; the learned predictor misses them because the pairs that matter there (`topic_list -> topic_info` was 5 of 13 in the x1 fold; `param_list -> param_get` 8 of 28) are task-specific once the held-out task is excluded, so they fall below every tau. Oracle: 14 of 63 requests are fully candidate in every task, so the ceiling on these traces is about 22% for both models.

## Cost side (Qwen / Luna)
| predictor | speculative units | used by the model's next request | precision | extra native ops | est. extra input tokens | input tokens of removed requests |
|---|---:|---:|---:|---:|---:|---:|
| learned 0.7, Qwen | 48 | 20 | 42% | 28 | 31,332 | 36,145 |
| static top-1, Qwen | 111 | 33 | 30% | 78 | 51,015 | 60,407 |
| learned 0.7, Luna | 188 | 11 | 6% | 177 | 37,928 | 4,207 |
| static top-1, Luna | 313 | 22 | 7% | 291 | 72,470 | 8,092 |
For Qwen at 0.7 the estimated extra input tokens roughly equal the tokens of the removed requests (net near zero) while adding 28 native operations (Qwen A0 used 85 in total). For Luna precision is 6% and the extra native operations (177) exceed the 75 it used in total; Luna already batches, so the replay offers it almost nothing. Token estimates are crude (median characters per unit of each tool divided by 4, times the requests remaining).

## Where the learned predictor does not beat the static rule
In every comparison here. The static rule is the hand-written enrichment a developer could add ("after node_list also read node_info for all nodes, after topic_list also read topic_info, and so on"); it removed more requests than the learned predictor at every tau on Qwen (10 against 6, 6 and 0) and at least as many on Luna (2 against 2, 1 and 1; tied at tau 0.5), at a higher native cost.

## Closest prior mechanism
This is the AutoTool-family situation again: a frequency table of tool pairs plus argument association adds nothing over an ordinary fixed rule using the same information (`studies/autotool_iteration_20261112/`). The new part tested here, building follow-up arguments from learned result-field bindings, did not change that.

## What the data cannot show
The training set is 72 episodes from one fixture and two models, with six task types and leave-one-task-out folds, so task-specific pairs are by construction not learnable; a larger or different workload could differ. The replay counts only whole requests whose every call is a candidate; partial coverage (4 requests at 0.7 for Qwen) removes nothing. No live run, answer-support or latency check. Token figures are estimates.

## The one decision this points to
Close the learned speculative-expansion branch (the frozen bar says stop). The part that did remove requests is a fixed one-line enrichment already covered by ordinary engineering; whether that is worth doing is a separate engineering choice that the data do not decide.

## Revisions
None after the first computation. One pre-computation clarification (made before any replay number existed): the binding-signature rule was tightened to `field` / `carry` / environment-free `const` so the predictor cannot memorise fixture names (`PROTOCOL_STAGE2A.md`).
