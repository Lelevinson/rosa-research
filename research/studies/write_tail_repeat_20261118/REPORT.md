# Write-tool attempts, tail cost, repeat loops: offline report

2026-11-18, Asia/Taipei. Frozen protocol [PROTOCOL.md](PROTOCOL.md) (SHA-256 `a60ded7c9da3ac4869d06cd0161c7194c0bdc59fb94c019869dd8481fcfb990f`), hashed before `count_wtr.py` existed. Population: the 1,832 saved episodes of `candidate_counts_20261118` (not independent samples: same tasks and seeds recur across arms). CPU only, nothing run. Tables: [TABLES.md](TABLES.md); raw: `results.json`, `attempts.jsonl` (76 rows with trace paths), `repeats.jsonl` (159 episodes). Development evidence only.

## Item 1. Write-tool attempts (measured)
**B1a met:** 76 attempts (63 `ros2_service_call`, 13 `ros2_param_set`), 61 in the fairness stock-executor arms (E0 54, E1 7). **B1b met: 0 of 76 have status `executed`.** Status of the 76: 49 `validation_text` (pydantic rejected the arguments, the tool body did not run; all in E0), 8 `no_result_validation` (the stock executor ended the episode on the validation error: S0 4, A1 4), 15 `guard_rejected` (the observation-only guard answered `Observation-only study: command rejected`: E0 5, E1 7, S0 3), 4 `not_available` (NO_MENU arm, tool not offered). So in these traces no write command reached ROS; the study's guard and the stock schema's own validation are what stopped them, not the models.
- **By arm (attempts / episodes with one):** S0 7/7 of 80 (bonsai 5, lfm3 1, qwen3.5 1); A1 4/4 of 80 (bonsai 3, lfm3 1); E0 54/7 of 80 (bonsai 51, qwen3.5 3); E1 7/3 of 80 (bonsai 7); ablation NO_MENU 4/1 of 40 (bonsai 4). **Per model, all 76:** bonsai 70, qwen3.5 4, lfm3 2, gpt-oss 0. 43 of E0's 49 validation errors are one pattern (a dict or string `request` the stock schema rejects), concentrated in a few bonsai episodes.
- **Method arms for comparison:** 20 arms that use the 12-tool menu (pilot C1 and its variants, round 1, round 2, ablation FULL and the four other ablation arms except NO_MENU, compaction, name-fix; 1,472 episodes) have **0 attempts** and no handler event naming a write tool. The menu does not offer write tools, so this says the models were never given the chance, not that they did not want to (NO_MENU, which offers the stock tools, drew 4 attempts from bonsai in 1 of 40 episodes).
- **What they would have changed (inference from arguments and the same environment's listings, not observed):** 4 attempts name an existing node and parameter and would have set a fixture parameter (`/e1h/willow mode idle` twice, `/e1h/quasar level 45`, `/e1h/basalt/zircon gain 100`); all four were `guard_rejected`. 15 attempts call `/plant32/cedar_reset`, a real `std_srvs/srv/Trigger` service in the stage-3 fixture (`headroom_diagnostic_20261112/stage3_graph.json`), an action-like decoy of the service task; none executed (20 attempts name `cedar_reset`: 7 guard-rejected, 6 validation text, 3 episode-ending validation, 4 not offered; 15 of the 20 are in an environment where the service exists). 48 attempts name a service or node that does not exist (invented, e.g. `ros2_info`, `describe_parameters`, a pseudo-node `/rosa` used to store an answer: it would have failed). No attempt targets a `set_parameters` service. My class "existing other service" in the protocol hides that all 15 are the one `cedar_reset` service; this note is post-hoc, the counts are as frozen.
- **Interpretation:** small models, mostly bonsai, do reach for write tools, mostly to do something the task did not ask (reset a decoy, write an answer into a parameter); under unguarded stock ROSA, 19 of the 76 would have reached a real fixture target (4 parameter sets and 15 `cedar_reset` calls) if their arguments had been valid. That is the case for the guarded action tool and for a central write guard; it is not evidence about action-task success.

## Item 2. Tail cost (measured)
Per episode, same 10 dev tasks x 4 models (80 cells per arm, seeds 1-2; ablation and compaction rows seed 1 only):
| arm | n | requests median / p90 / max | tokens median / p90 / max | cap endings | top-decile share of requests |
|---|---|---|---|---|---|
| ORIG (stock, s0) | 80 | 5 / 9 / 35 | 31.8k / 74k / 397k | 0 | 0.33 |
| E0 | 80 | 6 / 15 / 40 | 33.9k / 143k / 473k | 1 | 0.32 |
| E1 | 80 | 5 / 12 / 40 | 29.9k / 92k / 413k | 3 | 0.36 |
| A1 (extra) | 80 | 4 / 11 / 40 | 26.8k / 73k / 318k | 2 | 0.37 |
| FULL (pilot C1) | 80 | 4 / 10 / 40 | 10.6k / 39k / 157k | 1 | 0.32 |
| FULL (round 1 C1) | 80 | 4 / 12 / 40 | 10.4k / 50k / 341k | 1 | 0.36 |
| FULL (ablation) | 40 | 4 / 8 / 17 | 9.9k / 30k / 145k | 0 | 0.27 |
| FULL (compaction) | 40 | 4 / 8 / 23 | 10.7k / 33k / 252k | 0 | 0.27 |
Per model is in TABLES.md. The tail belongs to bonsai: in FULL (pilot) bonsai's p90 is 17 requests and 126k tokens against 8-9 requests and 23-35k for the other three; the cap endings of E0 (1), E1 (3), A1 (2), FULL (1 each in pilot and round 1) are all bonsai. Our method cuts the median tokens to about one third of the stock arms (10.6k vs 29.9-33.9k) and the p90 to 39k vs 74-143k, but not the request count at the median (4 vs 5-6) and not the 40-request cap in bonsai's worst episodes (max 40 in both pilot and round 1).
**Bar B2:** condition 1 (top decile carries >= 25% of an arm's requests) is met by every arm (0.27-0.37); condition 2 (>= 5 cap endings over >= 2 models) is **not met** by any arm (maximum 3 caps, one model). The bar as written is not met. The tail is real in tokens and in bonsai's request counts, but not in capped episodes.

## Item 3. Repeat loops (measured)
Check B3a: the support-presence rebuild agrees with the scorer's own on 1,816 of 1,832 episodes (99.1%), so the classification is usable. **159 episodes** have >= 2 identical successful repeats. First repeat class: **facts_present 82** (unsupported 51, of which 12 gave no answer), **facts_not_yet 77** (unsupported 45, no answer 31).
| group | facts_present: episodes / unsupported | facts_not_yet: episodes / unsupported |
|---|---|---|
| bonsai | 47 / 25 | 58 / 36 |
| lfm3 | 25 / 24 | 9 / 6 |
| qwen3.5 | 9 / 2 | 6 / 3 |
| gpt-oss | 1 / 0 | 4 / 0 |
| stock-executor arms (S0, A1, E0, E1) | 25 / 13 | 9 / 5 |
| menu arms | 57 / 38 | 68 / 40 |
Requests after the first repeat: median 8 (facts_present) vs 21 (facts_not_yet); sum 965 vs 1,601. **Bar B3 is met as written** (82 episodes over 4 models, 51 unsupported or without an answer).
- Reading with care: 24 of lfm3's 25 facts_present repeat episodes end unsupported, so for lfm3 "all facts present" does not mean the episode was about to succeed; those are mostly the D1 needle-missed episodes of the earlier count (answer wrong although the fact was in a result). A rule that stops repeating at that point would end such an episode earlier, but this count cannot say whether the answer would then be right: the 31 facts_present episodes that were supported (82 - 51) show repeats can also be harmless. "Present" is the scorer's text-presence test, not proof the model read it.
- The repeats cost requests: 965 requests follow a facts_present first repeat. That is a budget the idea could address; the mechanism (what a stop or hint does to a small model) is a hypothesis; stall hint v2, the closest prior mechanism, failed its frozen offline bar.

## Limits
Episodes are not independent; the earlier arms differ in prompt, executor and session; the write-attempt classes rest on fixture listings seen in traces (a service or node absent from every saved listing is called nonexistent); item 3's "facts present" is the scorer's presence rule; no new run, no recommendation beyond the bars.
