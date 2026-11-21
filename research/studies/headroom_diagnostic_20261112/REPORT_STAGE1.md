# Stage 1 report: prompt fix (1a) and width probe (1b), 2026-11-12

Development evidence only (tasks reused from the baseline; one fixture, two models, one session). Tables: `STAGE1_TABLES.md`; frozen plan and disclosed revisions: `PROTOCOL_STAGE1.md`; raw traces and hashes: `research/_artifacts/runs/headroom_diagnostic_20261112/`. Labels: F = measured here. No claim of novelty, success or a selected algorithm.

## What ran
42 episodes: 1a 24 (qwen3.5:9b, 6 tasks × 2 arms × 2 repeats, active context 65,536 verified); 1b 18 (9 Qwen, 9 gpt-6-luna via the existing ChatGPT-plan OAuth path, N = 4, 8, 16, 32). No API key. Fixtures were stopped and checked empty, and the ROS daemon stopped, after every run.
Infrastructure events (all disclosed in the protocol): 1a aborted after 6 episodes on a node-list flake in an evaluation snapshot and was resumed on the same seeded schedule; 1b stopped at N=32 because `ros2 node list` never showed a live node, `/scale/n28`, so the N=32 cell ran as a separate continuation (where all 32 were listed); one scorer clarification was made after seeing 1b results.

## 1a: does deconflicting the prompt save requests? (F)
| | A_orig (stock) | A0 (prompt deconflicted) |
|---|---:|---:|
| supported-complete episodes | 9 / 12 | 10 / 12 |
| all model requests | 74 | 63 (−15%) |
| requests per supported episode | 6.56 | 5.10 |
| excess over the Stage 0 floor (supported episodes) | 31 over 28 (111%) | 19 over 32 (59%) |
| requests with 2+ calls | 0 | 18 of 63 |
| input tokens | 511,985 | 424,475 (−17%) |
| native ROS operations | 68 | 85 (+25%) |
Matched pairs where both arms are supported (9): mean saving 1.56 requests, median 1, range 0 to 4; A0 fewer in 5, equal in 4, more in 0. The saving is concentrated in `x1` and `t1` (9 → 5 requests); `t2`, `d1`, `t3` change by 0 or 1. Where batching is permitted, Qwen sometimes still issues one call per request (for example `t2`: 6 requests in both arms).
Failures, read by hand: the four `d2` failures (both arms) report only `add_two_ints` and omit `get_type_description`, which the unchanged baseline scorer counts as a non-parameter service; the same scorer failed `d2` in the baseline. One A_orig `t1` answer used the colour-sensor 255s instead of the configured 37/83/129 (wrong source). Support did not fall.
Limits: temperature 0 and one seed make repeats near-duplicates, so there are about 6 independent pairs, not 12; no significance test. The extra native operations come from the extra exploratory calls that batching allowed, so fewer requests is not fewer reads.

## 1b: what happens as the number of entities grows? (F)
Floor is 3 requests at every N (`ros2_param_get` takes one node, so N parallel calls in one request).
| N | 4 | 8 | 16 | 32 |
|---|---|---|---|---|
| gpt-6-luna requests / value coverage | 3 / 4 | 3 / 8 | 3 / 16 | 3 / 32 (both repeats) |
| Qwen requests / value coverage | 4 / 4 | 4 / 8 | 4 / 16 | 4 / 32 (both repeats) |
| Qwen wall seconds | 52 | 87 | 157 | 297 and 324 |
Both models issued all N reads in a single request at every N. Luna stayed at the floor; Qwen at floor+1 (one extra single-call request). No length, iteration-cap, timeout or provider event occurred. Qwen output tokens grew with N (493 → 2,766) and wall time about 6× from N=4 to N=32, because the CLI reads run one after another (about 1 operation per node).
Two defects at N=32: both Qwen answers put the nodes at top level instead of under the requested `clocks` key (format failure, values correct; 0 of 2 compliant), and the r0 answer ended with a wrong remark about "even indices" (r1 not checked for extra remarks). Luna's two answers were compliant.
Decision rule (section 6): both models reach full value coverage with requests ≤ floor+1 at N=32, so **the ordinary deconflicted prompt holds for call count at this width**. Caveat: the `clocks`-key failure means "full coverage" holds for values, not for the requested schema, for Qwen.

## What the data cannot show
Anything beyond these two stages' tasks: identical-node, read-only, one parameter; the fixture has no heterogeneity or dependencies between entities. Qwen repeats are near-duplicates (temperature 0). The N=32 listing flake shows the discovery CLI can omit a live node at this width; in the first N=32 attempt `n28` never appeared in 8 listings, and in the run that was scored it did. A model relying on a list would then miss it; that effect is therefore not excluded, only not observed in the scored runs. One strong model, one weak model. Wall time at N=32 is dominated by sequential CLI calls, which prompt changes do not touch.

## The one decision this points to
The prompt fix removes most of the request excess that comes from serial calls (1a, −15% requests) and keeps call count at the floor out to 32 entities (1b). What is left is mixed: single-call serial turns in `t2`/`d1`, unneeded `param_list` and repeat reads, and native-operation and wall-time growth with N. Decision for you: keep call count as the metric and accept the prompt fix as the answer, or move the question to native operations and wall time (not requests) and to format reliability at width. No mechanism is proposed here.
