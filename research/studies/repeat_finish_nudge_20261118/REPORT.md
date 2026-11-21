# Repeat-finish nudge, live development run: class B (no event-level effect seen), nudge fired in 9 episodes

2026-11-18/19, Asia/Taipei. Frozen protocol [PROTOCOL.md](PROTOCOL.md) (SHA-256 `783b41442a7ed58754ff03a8728b16f7a00ff286a245c89b53041fcbb2029434`), hashed before any code; code, scorer v2.0 (`c6b02716...`), fixtures and model digests in `FREEZE.json`; analysis by the frozen `analyze_nudge.py`. Smoke (4 episodes, 22 checks pass, 0 fires) preceded the full run. Full run: 160 episodes (10 dev tasks x 4 models x seeds 1-2 x FULL / NUDGE), 8 sessions, 160 attempts with return code 0, no timeouts, no infrastructure-failed cell (0 episodes with 0 requests), about 101 minutes of episode time. GPU idle afterwards (Ollama `/api/ps` empty). Development evidence only; one seed pair; not a held-out result. Outputs: `results.json` (with per-episode rows), `RESULTS_LOG.jsonl`. Raw traces: `research/_artifacts/runs/repeat_finish_nudge_20261118/full_20261118/` (not mirrored).

## Top box
- **Result (frozen rule):** event bar **not met**; no harm flag; **class B** ("no evidence of an event-level effect in these cells"). Requests after the first identical repeat: FULL 91, NUDGE 128 (+41%, the wrong direction); only bonsai was evaluable (FULL 72, NUDGE 111).
- **What it changes:** nothing in the method; the finish-nudge family stops for this week per the protocol's stop rule.
- **What it cannot show:** 11 (FULL) and 9 (NUDGE) episodes had a first identical repeat; the nudge fired in 9 episodes (16 fires). These sums are driven by a few long bonsai trajectories that diverge before the repeat; the power note anticipated this. Class B means "not seen", not "no effect".
- **System acts or model must adopt:** the system appends one line; the model must act on it. In 8 of the 9 fired episodes the next request was not a `final_answer`.
- **Cost:** NUDGE used 1,862,000 tokens against 1,544,905 (+20.5%) and 514 requests against 475 (+8.2%), mostly bonsai trajectories.

## Measured
| | FULL | NUDGE |
|---|---|---|
| supported-complete / 80 | 67 | 67 |
| requests / tokens | 475 / 1,544,905 | 514 / 1,862,000 |
| cap endings / no-answer endings | 1 / 2 | 1 / 2 |
| episodes with a first identical repeat | 11 | 9 |
| identical repeats (all) / nudge fires | 41 / 0 | 42 / 16 (9 episodes) |
| R (requests after first repeat) | 91 | 128 |
| next request after the first repeat is `final_answer` | 2 of 11 | 2 of 9 |
| supported by model (lfm3, qwen3.5, gpt-oss, bonsai) | 17, 20, 14, 16 | 16, 20, 17, 14 |
R per model, FULL vs NUDGE: bonsai 72 vs 111; gpt-oss 7 vs 1 and lfm3 12 vs 16 (both below the 20-request evaluability floor); qwen3.5 0 vs 0 (it never repeated an identical call). Paired cells (task, model, seed): both supported 63, FULL only 4, NUDGE only 4, neither 9.
- **Facts split of first repeats** (class by scorer-presence before the repeat): FULL facts_present 4 (2 supported), facts_not_yet 7 (4 supported); NUDGE facts_present 3 (1 supported), facts_not_yet 6 (1 supported). The 82-episode target of the offline count (facts_present repeats) appeared in 4 + 3 episodes here.
- **Fired episodes (9):** lfm3 `v2` s1 (facts_present, R 15), lfm3 `e1h_chg_1` s1 (not_yet, answered next request, unsupported), gpt-oss `e1h_chg_1` s2 (not_yet, answered next request, unsupported), bonsai `h4` s2 (R 19, supported), bonsai `h4` s1 (R 31, unsupported), bonsai `u3` s2 (facts_present, R 5, supported), bonsai `v2` s1 (facts_present, R 4, unsupported), bonsai `v2` s2 (R 18, unsupported), bonsai `e1h_chg_2` s2 (19 identical repeats, R 34, unsupported). **After a fire, the next request was `final_answer` in 2 of 9, both in the scripted-change task `e1h_chg_1`, both unsupported; in the 7 other fired episodes it was not, in the 3 facts_present fired episodes (lfm3 `v2`, bonsai `u3`, bonsai `v2`) it was not either.**

## Scripted-change stratum (the named risk)
CHG (`e1h_chg_1`, `e1h_chg_2`, 16 episodes per arm): supported 13 / 13; requests 100 / 99; first-repeat episodes 3 / 3; fires in NUDGE 4. **CHG early answers (next request after the first repeat is `final_answer`, unsupported): FULL 2 (gpt-oss `e1h_chg_1` s2, gpt-oss `e1h_chg_2` s2), NUDGE 2 (lfm3 `e1h_chg_1` s1, gpt-oss `e1h_chg_1` s2): equal, no harm flag.** Reading with care: the gpt-oss `e1h_chg_1` s2 early answer occurs in both arms (it is the model, not the line); the lfm3 `e1h_chg_1` s1 cell is the named mechanism: the nudge fired at request 2, the next request answered `final_level: 30` (the value before the scripted change), unsupported, whereas FULL on the same cell answered correctly (3 requests, 45). Trajectories diverge at request 1-2, so this is one illustrative case, not a paired effect.

## Interpretation (labelled; hypotheses, not measurements)
1. The line did not shorten the loops it was aimed at: the long loops are bonsai, which kept repeating after the 2 fires (bonsai `e1h_chg_2` s2: 19 identical repeats with the line vs 29 without; both capped at 40 requests). H: a one-line text note does not change what bonsai-2:4b does inside a tool-argument loop; not tested beyond these cells.
2. The strong models rarely repeat (qwen3.5 0, gpt-oss 4 and 1 episodes), so the nudge has almost nothing to act on where it would be safe, and acts mainly on the weak models that cannot use it.
3. The one live case of the named risk (lfm3 `e1h_chg_1` s1) is a premature stale answer.

## Limits and defects (reported, not patched)
- Fire counts were at the low end of the protocol's power note (9 fired episodes, 16 fires). An effect on larger samples cannot be excluded.
- Trajectories diverge before the first repeat; `R` mixes treatment and trajectory differences. One seed pair.
- The identical-result trigger is stricter than the offline count's identical-arguments repeat (159 offline episodes), so fewer episodes qualified than the offline population suggested.
- Known validity defect carried unchanged (`e1h_chg_*` hook misses on a name without a leading slash): not isolated here.
- Teammate-context check (`rosa-contexts`) not done.

## Open search (patterns noticed that are not this study's target; counts from the 160 full-run episodes, no filtering)
- **Non-converging search loop (bonsai `e1h_chg_2` s2), both arms:** 41 tool calls each, 40-request cap endings; `ros2_topic_list` repeated with variant `pattern` values (NUDGE: `'thistle'` 17, `'*thistle*'` 15; FULL: `'thistle'` 16, `'/e1h/thistle'` 13). `bonsai-2_4b-e1h/006-e1h_chg_2-NUDGE-bonsai-2_4b-s2/trace.jsonl`, `bonsai-2_4b-e1h/010-e1h_chg_2-FULL-bonsai-2_4b-s2/trace.jsonl` (under the run folder).
- **Backend tool-call parse error `error: multiple repeat at position 2`:** 24 tool exceptions in 7 episodes (FULL 5 in 3 episodes, NUDGE 19 in 4; 16 of the NUDGE ones are the loop above, 3 of the FULL ones). Others: `lfm3_1.7b-stage3/004-v2-FULL-lfm3_1.7b-s1`, `lfm3_1.7b-stage3/010-v2-FULL-lfm3_1.7b-s2`, `lfm3_1.7b-stage3/013-v2-NUDGE-lfm3_1.7b-s1`, `gpt-oss_20b-e1h/014-e1h_abs_1-NUDGE-gpt-oss_20b-s1`, `bonsai-2_4b-stage3/004-h4-NUDGE-bonsai-2_4b-s1`.
- **Strict pre-check rejections:** 18 episodes (FULL 11 rejections, NUDGE 7), gpt-oss 16 episodes and lfm3 2; e.g. `gpt-oss_20b-stage3/001-h4-FULL-gpt-oss_20b-s2/trace.jsonl`, `lfm3_1.7b-stage3/008-u3-FULL-lfm3_1.7b-s2`.
- **Stale value answered on `e1h_chg_1` (`final_level` equal to the pre-change `first_level`):** 3 episodes (FULL gpt-oss s2; NUDGE gpt-oss s2, NUDGE lfm3 s1). `gpt-oss_20b-e1h/017-e1h_chg_1-NUDGE-gpt-oss_20b-s2`, `lfm3_1.7b-e1h/019-e1h_chg_1-NUDGE-lfm3_1.7b-s1`.
- **Unsupported episodes:** 26 of 160 (bonsai 10, gpt-oss 9, lfm3 7, qwen3.5 0); by task `v2` 7, `e1h_abs_2` 5, `p3` 3, `e1h_chg_1` 3, `e1h_abs_1` 3.
- **Requests concentrated in bonsai:** the 5 longest episodes (40, 40, 38, 32, 26 requests) are all bonsai; qwen3.5 uses 86 requests (FULL) and 83 (NUDGE) in total, bonsai 172 and 211.
- **Write attempts:** 0 blocked write calls, 0 tool-not-offered, 0 extra-tool calls in all 160 episodes.
- **Wall time:** gpt-oss 35 min, qwen3.5 31 min, lfm3 19 min, bonsai 16 min of the 101 minutes (qwen3.5 and gpt-oss are slow per episode, bonsai long per request count).
