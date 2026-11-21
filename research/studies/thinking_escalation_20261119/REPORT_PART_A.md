# Thinking escalation, part A (FULL vs FULL+ESCALATE): class A by the frozen rule, no effect on supported answers

2026-11-19, Asia/Taipei (run 14:16-16:30, about 2 h 15 min). Frozen [PROTOCOL.md](PROTOCOL.md) (revision R1, SHA-256 `0e9fbdf6dc499a61aa1ec1285a8824d240cfd54de26f8b514697cb7e8a9d49a5`) and [AMENDMENT_A1.md](AMENDMENT_A1.md) (`72be5bc91c86b231f87b5d55a019fa2fa262e31ab52a2ff0520632a865a44f78`): **part A = FULL against ESCALATE, 160 episodes** (10 dev tasks x 4 models x seeds 1-2 x 2 arms), 8 fixture sessions with both arms and both seeds shuffled together (manifest `846d8222...`, checked by the queue before the first request). Run through the exam queue runner (`exam_queue/`, spec `thinking_partA_spec.json`); rows exported to `RESULTS_LOG.jsonl` (phase partA) and analysed by the frozen `analyze_think.py` (SHA-256 `7a97b646153bfb73...` after the amendment's edits; scorer v2.0 `c6b02716...`); numbers in `results.json`. 160 of 160 cells logged, 0 duplicates, 0 skipped, 0 infrastructure failures, 0 timeouts. **Part B (ALWAYS) has not been run**: the C0 headroom reading is not evaluated and nothing below uses ALWAYS. Development evidence only (synthetic fixtures, four small models); not a held-out result; not a novelty claim. Smoke before the run: 12 episodes, 122 checks (one session re-run after an oracle first-read flake that occurred before any episode).

## Top box
- **Result (frozen rule): class A.** Mechanism bar M met (pooled share of trigger events whose next request makes a progress call: FULL 29.2% -> ESCALATE 42.9%, +13.7 points, threshold 10; higher in 2 of the 2 evaluable models, lfm3 and bonsai); no harm flag; no cost flag. Frozen reading of class A: "eligible for consideration; a benefit in supported answers is claimed only if it exceeds the detectable difference".
- **Supported answers did not change: 66 against 65 of 80** (paired cells: both 59, FULL only 7, ESCALATE only 6, neither 8). The detectable difference with 80 cells is about 10 cells; this is far inside the noise.
- **Cost:** model requests 522 -> 451 (-13.6%); input + output tokens 2,144,441 -> 1,827,119 (-14.8%); output tokens 111,567 -> 118,163 (+5.9%); estimated thinking tokens 21,122 -> 74,560; wall time 2,842 s -> 2,895 s (+1.9%).
- **What it cannot show:** a benefit in answers; gpt-oss and qwen3.5 (5-18 events each, below the 15-event floor in one arm); anything about ALWAYS; causality beyond these 10 tasks, 2 seeds, one session set. The event-level bar compares event populations that differ between arms (below).

## Measured (80 episodes per arm)
| | FULL | ESCALATE |
|---|---|---|
| supported-complete | 66 | 65 |
| model requests | 522 | 451 |
| input / output tokens | 2,032,874 / 111,567 | 1,708,956 / 118,163 |
| thinking tokens (estimate) / reasoning text captured (characters) | 21,122 / 0 | 74,560 / 218,322 |
| wall seconds (sum of episodes) | 2,842 | 2,895 |
| cap endings / no-answer endings / backend errors / length-cut responses / timeouts | 1 / 3 / 1 / 1 / 0 | 1 / 6 / 1 / 1 / 0 |
| trigger events (fires) | 146 | 92 |
| fires by class: not found / empty / error / repeat | 52 / 48 / 26 / 20 | 52 / 19 / 10 / 11 |
| episodes with at least one fire (supported) | 40 (30) | 37 (28) |
| escalated requests (all with the override on) | 0 | 130 (bonsai 70, lfm3 35, gpt-oss 16, qwen3.5 9); 3 returned empty thinking |
| output tokens per request: escalated / not escalated | n/a | 474 (61,605 over 130) / 177 (56,558 over 320) |
Supported by model (FULL -> ESCALATE): lfm3 17 -> 16, qwen3.5 20 -> 19, gpt-oss 17 -> 18, bonsai 12 -> 12. Requests by model: bonsai 203 -> 158, lfm3 137 -> 113, qwen3.5 85 -> 90, gpt-oss 97 -> 90. Wall seconds by model: bonsai 462 -> 566, lfm3 644 -> 568, gpt-oss 916 -> 927, qwen3.5 820 -> 833.

## Per-fire outcomes (events with a next request: FULL 144, ESCALATE 91; identical definition in both arms)
| | FULL | ESCALATE |
|---|---|---|
| O1: the next request's first call differs from the triggering call | 85.4% | 80.2% |
| **O2: the next request contains a progress call (successful, not a repeat)** | **29.2%** | **42.9%** |
| O3: the next request calls final_answer | 11.8% | 13.2% |
By class (events, number with O2): error 26 (7) -> 10 (3); not found 51 (20) -> 51 (23); empty 47 (9) -> 19 (6); repeat 20 (6) -> 11 (7). By model O2: bonsai 22.1% (77 events) -> 37.3% (51), +15.2 points; lfm3 34.1% (44) -> 52.2% (23), +18.1; gpt-oss 44.4% (18) -> 45.5% (11) and qwen3.5 40% (5) -> 50% (6), both **not evaluable** under the frozen floor.

## Interpretation (labelled; hypotheses, not measurements)
1. **Measured:** after an error, not-found, empty result or repeat, lfm3 and bonsai more often make a progress call at the very next request when thinking is on for it. The bar's pooled gain is +13.7 points over small event counts (144 and 91); with only two evaluable models the "2 of 2" condition has no margin.
2. **The event populations differ between arms and this matters for reading O2.** ESCALATE has 37% fewer trigger events (92 against 146), almost all of the drop in the classes empty (48 -> 19) and error (26 -> 10), while not-found is identical (52 and 52). Because the arm changes what happens after the first trigger, later events are partly a downstream effect. H (not tested): thinking after a first dead end reduces follow-up dead ends, which would also explain the 13.6% fewer requests; the alternative that the O2 gain partly reflects which events remain cannot be excluded from these data.
3. **No benefit in answers is shown** (66/65). The efficiency numbers (requests -13.6%, tokens -14.8%) come mostly from bonsai (203 -> 158 requests) and lfm3 (137 -> 113); a few long bonsai episodes dominated the totals in every earlier study, so the totals are fragile (not checked here per episode).
4. **Cost of the mechanism:** escalated requests carry about 2.7 times the output tokens of ordinary ones (474 against 177 per request), but they are a minority (130 of 451 requests) and the saved requests also save input tokens (input -15.9%); wall time is +1.9% overall and +23% for bonsai (462 -> 566 s).
5. **gpt-oss:** its FULL arm is not thinking-off (see the level note); the estimated thinking share of its output tokens is 14,057 of 17,855 in FULL. ESCALATE moves it from the level `false` maps to, to `"high"`, a smaller contrast than off to on for the other models; only 11-18 events, not evaluable. The gpt-oss level probe was run afterwards: `false` matched `medium` in token counts, not `low` (see the level note).

## Limits and defects (reported, not patched)
- 10 development tasks, 2 seeds, one session set per arm pair; trajectories diverge from the first request; events are several per episode and not independent (bonsai FULL alone has 78 events).
- The class is decided by conventions (10 points, 2 models, 15-event floor), not significance tests; the floor leaves two models evaluable.
- **Notifications were silent during this run:** the monitor started before the runner had created its run folder and died on its first loop (no state file, no messages). Found after the run; **fixed** (monitor creates the folder, logs and survives loop errors, the launcher checks it after 12 s, a regression test was added) and verified by a restart. The run itself, its results and its rows were not affected.
- The thinking-token figures are estimates (output tokens minus the visible tokens); reasoning text is not stored when `reasoning=False`.
- Part B and the ALWAYS arm are not run; any later comparison with ALWAYS is cross-session (amendment A1).
- Teammate-context check (`rosa-contexts`) not done.

## Open search (patterns noticed that are not this study's target; counts over the 160 episodes, no filtering; paths under `research/_artifacts/exam/thinking_partA/runs_all/`)
- **gpt-oss on `h4`: no-answer endings in 3 of its 4 episodes** (FULL s2, ESCALATE s1 and s2): `block_0005/011-h4-FULL-gpt-oss_20b-s2`, `block_0005/007-h4-ESCALATE-gpt-oss_20b-s1`, `block_0005/010-h4-ESCALATE-gpt-oss_20b-s2`.
- **No-answer endings doubled, 3 -> 6, concentrated in lfm3 `v2`/`h4` (3) and gpt-oss `h4` (2) under ESCALATE** (+3, below the frozen flag of +5, cause not investigated): lfm3 `block_0001/000-v2-ESCALATE-lfm3_1.7b-s1`, `003-h4-ESCALATE`, `013-v2-ESCALATE`; bonsai `block_0007/007-v2-ESCALATE-bonsai-2_4b-s2`. FULL's three: lfm3 `block_0002/001-e1h_abs_2-FULL-lfm3_1.7b-s1`, gpt-oss `block_0005/011-h4-FULL`, bonsai `block_0008/011-e1h_chg_2-FULL-bonsai-2_4b-s2`.
- **Backend tool-call errors, 1 per arm** (lfm3 `h4` s1 ESCALATE; lfm3 `e1h_abs_2` s1 FULL) and **length-cut responses, 1 per arm** (lfm3 `v2`).
- **Cap endings, 1 per arm, both bonsai** (`e1h_chg_2` s2 FULL, `v2` s2 ESCALATE); the `e1h_chg_2` s2 bonsai poll loop is the same pattern as in the nudge study.
- **Hidden thinking in gpt-oss FULL:** about 79% of its output tokens (14,057 of 17,855) are estimated thinking although `reasoning=False`; not stored in the trace.
- **Empty thinking when escalated:** 3 of 130 escalated requests returned no reasoning text (all models that can think may return an empty thinking for a very short answer).
- **Event concentration:** FULL bonsai 78 of 146 events (11 episodes with events); ESCALATE bonsai 52 of 92.
- **Monitor race** (above): 0 notifications for 2 h 15 min of the run; found only by missing messages.

## Addendum 2026-11-19 (CPU-only follow-up; the text above is left unchanged)
Details in [FOLLOWUP_TOKENS_AND_NO_ANSWER_20261119.md](FOLLOWUP_TOKENS_AND_NO_ANSWER_20261119.md). (1) **The output tokens in the tables include thinking tokens** (usage equals Ollama's `eval_count`; across 127 escalated requests output tokens track thinking characters, correlation 0.997); the thinking-token row is a subset of the output tokens; no cost number changes. (2) The no-answer endings 3 -> 6: **three of ESCALATE's six had escalation active** (bonsai `v2` s2 cap during a trigger loop; lfm3 `v2` s2 thinking exhausted 4,096 tokens; gpt-oss `h4` s2 empty response, identical in FULL) **and three had escalation never active** (their FULL counterparts' request 1 already differed); two FULL no-answer cells finished in the ESCALATE arm. The 3 -> 6 is not shown to be an effect of escalation, but thinking runaway under sustained triggers is a visible cost. (3) **New:** request 1 (identical prompt, seed and settings) differs between the arms in 22 of 80 cells (gpt-oss 16 of 20, lfm3 4, qwen3.5 1, bonsai 1): gpt-oss runs are not reproducible even without treatment, so its arm contrast cannot be read.

**gpt-oss level probe (2026-11-19, after this report):** 64 requests, 8 per setting and prompt: `think: false` gave 216 / 53 output tokens (plain / tool prompt), `medium` 214 / 49, `low` 91 / 34, `high` 462 / 187, and thinking text was returned in every request including `false`. So in the FULL arm gpt-oss runs at a medium-like level, and ESCALATE's `high` is about twice that thinking, not off-to-on. Details: [NOTE_GPT_OSS_LEVELS_20261119.md](NOTE_GPT_OSS_LEVELS_20261119.md).
