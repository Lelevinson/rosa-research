# Candidate counts for the improvement search: report

2026-11-18, Asia/Taipei. Offline, CPU only, saved traces only; nothing was run live. Frozen protocol: [PROTOCOL.md](PROTOCOL.md), SHA-256 `ddeb30a08e64f133ddcceacddebcfc7f15807f10e73d34ea6a6750dc1f8a24ac`, written and hashed before the script existed. Script `count_candidates.py` (frozen counts) and `posthoc_counts.py` (post-hoc, labelled below). Per model and per study tables: [TABLES.md](TABLES.md). Raw per-item files: `fires_a.jsonl`, `events_b.jsonl`, `needle_d.jsonl`, `results.json`, `posthoc.json`. Development evidence only (synthetic fixtures, four small models); nothing here is held-out, causal, or a novelty claim.

## Population and data check (B0)
1,832 episodes in 8 studies (pilot 576, round 1 320, round 2 352, fairness 160, ablation 200, name-fix 64, compaction 80, S0 80), 12,614 model requests, four models; 0 parse errors. The same tasks and seeds recur across studies and arms, so counts below are **not independent samples**. B0: 2 episodes (both round-2 SWEEP, qwen3.5 and gpt-oss) have a logged `supported_complete` true that scorer v2.0 re-scores false from the trace; they are excluded from (c) and (d) and kept in (a), (b), (e). No rule was changed for them.

## Measured

**(a) Name binding at input.** 406 fires in 8 studies and 4 models (bonsai 196, lfm3 132, qwen3.5 45, gpt-oss 33). Verdicts: **agree 315, differ 0, no later successful use 91** (bonsai 76 of its 196). Request distance from the fire to the model's next successful call on that name: median 2, mean 2.11 (agree fires: distance 1 in 123, 2 in 127, 3+ in 65). Frozen bar (>= 10 fires, >= 2 models, 0 differ): **met as written**.
Concentration (post hoc, from `fires_a.jsonl`): the fires come from **17 distinct (task, model) pairs and 8 tasks**; three stage-3 tasks (h4 203, u3 122, v2 59) give 384 of 406. Typical typed form: the node's base name taken from a `Node name:` field (`yarrow` for `/plant32/yarrow`).

**(b) Partial-match exposure.** 33 events in 32 episodes (lfm3 18, gpt-oss 10, bonsai 4, qwen3.5 1). The final answer names an exposed partial match in **9 events (9 episodes)**; in 7 events the partial match is part of the fixture truth (namespace listings such as `/plant32` and ambiguous-name tasks), in the others (e1h_abs tasks) it is a wrong answer: 2 lfm3 episodes named `/e1h/alder/pewter` or `/e1h/ember/mistral` for a node asked as `/alder/pewter` or `/ember/mistral` and were unsupported. In 19 events the answer names the typed, non-existent name (not separated into statements of absence versus errors); 19 of the 33 events are in supported episodes.

**(c) Finish tool.** FULL-type arms (pilot C1, round 1 C1, round 2 CONTROL, ablation FULL, compaction FULL; 416 episodes, of which 362 ended with an accepted `final_answer`, 35 with bare text that the scorer parsed, 19 with no answer object):

| ending | episodes | supported | rate |
|---|---:|---:|---:|
| `final_answer` | 362 | 317 | 87.6% |
| bare text (JSON recovered) | 35 | 29 | 82.9% |
| no answer (cap, backend error, timeout) | 19 | 0 | 0% |

By model, text endings: gpt-oss 29 episodes (26 supported), lfm3 5 (3), bonsai 1 (0), qwen3.5 0. Final-answer rates: qwen3.5 104/104, gpt-oss 65/70, lfm3 79/97, bonsai 69/91. Arms without a finish tool: ablation NO_FINISH 39 text endings (29 supported) and 1 no answer; fairness E0 73 text (60) and 7 none; E1 75 (65) and 5; S0 52 (40) and 28 none. The old round-1 bare-text nudge result, quoted from `decisions/2026-11-17-finish-gate-check.md` and **not recomputed**: C1+AG 4 nudged episodes, 4 supported (same outcome as their controls); C1+AG+LA 8 nudged, 6 supported; the owner's decision record notes it is bundled with the gate and is not a test of a finish-tool rule.

**(d) Needle missed.** `D1` (failed, an answer exists and is wrong, every support fact present by the scorer's rule): **159 episodes over all 4 models** (lfm3 76, bonsai 62, gpt-oss 14, qwen3.5 7) and 10 tasks; tasks v2 60, e1h_abs_1 35, e1h_abs_2 24, p3 15. Other categories: `D0` (no answer, facts present) 44 episodes; `S` (answer exact, fact not read) 19. Frozen bar (>= 5 episodes over >= 2 models): **met as written**.
The `long` subset (the result that supplies a fact is >= 8,000 characters, about 2,000 tokens by a 4-characters-per-token estimate): **3 episodes** (bonsai h4 twice, one with a 13,442-character result; bonsai nf_multi_2, 26,582 characters), so the long subset alone does **not** reach the bar.
Post hoc: in **64 of the 159** D1 episodes my text search found no result containing the fact (the scorer's rule also accepts a fact that is in the task text or is assembled from separate fields), so the strictly "fact seen in a result" count is **95**, of which 61 sit in results of 5,000-5,999 characters and 25 in results under 1,000 characters.

**(e) Open search (detector counts over all 1,832 episodes; examples with trace paths in `results.json` `e_examples`).**
1. **Repeated identical successful call** (same tool, same arguments as an earlier successful call): **1,779 calls = 14.1% of 12,614 requests**; 1,407 of them returned byte-identical text to the first call; 342 were in directly consecutive calls. By model: bonsai 1,302, lfm3 225, qwen3.5 150, gpt-oss 102. By tool: `ros2_service_info` 363, `ros2_topic_list` 353, `ros2_param_get` 341, `ros2_node_list` 323, `ros2_node_info` 259. Some repeats are legitimate in the scripted-change tasks (the state changes); I did not separate those.
2. Harness-rejected calls (invalid arguments, tool not available, finish-tool format): 659 (pilot 348, round 2 150, round 1 68).
3. Identical repeated **failed** call: 53.
4. No-answer endings: iteration cap 39 (pilot 14, round 2 15, round 1 5, fairness 4, compaction 1), backend `ResponseError` 26, XML-syntax parse errors 11 (these overlap with other endings).
5. Long results (>= 8,000 characters): 130 successful results; 458 later requests carry them in the history.
6. Write-tool attempts: 76 (fairness 61 under the stock executor, which offers write tools; S0 7; ablation 4; pilot 4). In the steady-loop arms they are blocked; this count says how often small models reach for writes, which matters for the action-tool work.
7. Re-read of the same entity written with and without the leading slash: 38.
8. Not counted anywhere above and not examined: serial single reads that could have been batched (known from the earlier FULL-arm map), and the ambiguous-suffix branch of the name-binding rule (a fire is not counted if two ledger names share the suffix).

## Interpretation (labelled; no recommendation beyond the frozen bars)
- Bars: (a) met, (d) met as written, the (d) long subset alone not met (3 of the 5 needed, 2 models). (b), (c), (e) have no bar.
- (a): the 0 contradictions are real in these traces, but the evidence behind them is 17 (task, model) pairs on three stage-3 tasks, so the bar passes on volume while the diversity is small. The count says nothing about colliding short names in other environments; the custodian's aggregate (0 of 76 held-out tasks need short-name resolution) is a separate fact I did not open and cannot reconcile here: this count shows that small models drop the slash in these dev tasks, not that held-out tasks contain the situation. The rule is exercised only by cases where the model's own retry succeeded within a median of 2 requests; offline replay cannot say how many requests an input fix would save, because the later successful call may be one the model would have made anyway.
- (b): small. The cases where a partial match is a wrong answer are 2 episodes in this dataset (both lfm3, absent-node tasks); whether showing partial matches helps or hurts cannot be read from episodes recorded without it.
- (c): in FULL-type arms the text ending is uncommon (35 of 416, mostly gpt-oss) and not clearly less supported (82.9% vs 87.6%, small counts); the ending class therefore does not by itself explain the -7 of the ablation. It shows no support gain from the old nudge (4 of 4 equal to control). The no-answer class (19) is where all unsupported FULL-type endings that are not wrong answers sit.
- (d): the bar is passed by wrong-hop or wrong-selection errors on tasks whose facts were seen (v2 and e1h_abs tasks, mostly lfm3 and bonsai), not by facts buried in long results (3 episodes). Reading `D1` as "the model overlooked a needle in a long result" is not supported by the long subset.
- (e): the repeated identical call is the largest pattern by volume and overlaps the stall line already closed (stall hint v2, failed its bar); the count here is a different measure (all repeats, all arms) and was not tested as a mechanism.

## Deviations, limits
- Operationalisation of "appeared in a successful result" in (d) follows the scorer's `support_missing` rule (also accepts the task text and assembled fields), as the protocol names the fixture-truth support list; the strict count (95) is post hoc.
- `posthoc_counts.py` and the post-hoc numbers (distinct pairs, concentration, strict D1, 5-6k bucket, repeat breakdown) were written after seeing the frozen counts; they are not part of any bar.
- Hand reading: I opened the 33 (b) events and the listed D1 issue strings, and checked fire examples by their typed/resolution pairs; I did not read full (e) traces, so (e) items are detector counts, not diagnosed causes.
- Not checked: teammate context (`rosa-contexts`); no overlap known. Same-task repetition across studies inflates every pooled count.

## Correction note (2026-11-19; the text above is left unchanged)
In the bars summary, "(d) long subset alone not met (3 of the 5 needed, 2 models)" states the bar (5 episodes over at least 2 models), not the observation. Observed: **3 episodes, 1 model (bonsai-2:4b)** (TABLES.md: "long (>= 8,000 chars) D1 3 over ['bonsai-2:4b']"). The conclusion is unchanged. See `../final_exam_draft_20261118/NUMBER_RECONCILIATION_20261119.md`.
