# Argument-type errors and a lossless conversion, offline count: sparse for the method loop, concentrated in gpt-oss

2026-11-19, Asia/Taipei. Frozen protocol [PROTOCOL.md](PROTOCOL.md) (revision R1, SHA-256 `e379aa7edb8b5f033441bbc387bca9f17588c46204f278ac0008dfc36c4c4e1f`; first version `PROTOCOL_R0.md`, `d97edf002acfef3c6d8ccab40f3925b90b5cbfd882d7121e69e2b84e805a7786`; the one revision is dated and was made before any count, see its revision log). Script and tests hashed in `SCRIPT.sha256` before the count; one crash fix (a request without a response has no `usage`) was made before the first completed count. CPU only (`nice`); no Ollama, ROS or held-out files. Population: the 1,832 saved episodes of `candidate_counts_20261118` (not independent). Development evidence only; offline predictions, nothing was run with the conversion. 11 unit tests pass. Outputs: `results.json`, `events.jsonl` (380 events with original and converted arguments), `episodes.jsonl`, `posthoc_relaxed_retry.py/json`.

## Top box
- **Result (frozen bar):** **sparse**. In the menu arms of the FULL-type subset (the method loop, 416 episodes, 3,020 requests) there are 41 argument-type events in 39 episodes; 34 are fixable by K1-K6, all in **gpt-oss** (1 model, bar needed 2); saved-max requests 3 = 0.10% of requests (bar 1%). Verdict: an executor-level fix to be given to every arm equally; no live test proposed.
- **What it changes:** nothing in the method. It confirms the ChatGPT review's expectation that exposure may be sparse; the one place it is not sparse is gpt-oss.
- **What it cannot show:** whether a model would behave the same after a converted call returns a result; saved-max assumes it would not issue the retry. Not a measurement of any conversion.
- **System acts or model must adopt:** the system acts (silent conversion); the model sees only the normal result.
- **Cost:** none measurable offline (no tokens added; a string parse and schema re-check per call).

## Measured
| | all 1,832 | menu arms (1,512) | stock-executor arms (320) | FULL-type menu (416) |
|---|---|---|---|---|
| argument-type events (episodes) | 380 (249) | 265 (187) | 115 (62) | 41 (39) |
| fixable by K1-K6 (episodes) | 182 (177) | 138 (133) | 44 (44) | 34 (34) |
| write-tool events (never fixable) | 57 | 0 | 57 | 0 |
| saved-max requests (frozen definition) | 21 | 7 | 14 | 3 |
| tokens of those requests | 64,087 | 10,678 | 53,409 | 4,452 |
Fixable events by kind (all): K3 (empty string or null for an optional array) 158, K2 (scalar wrapped in an array) 17, K4 (numeric string to number) 7; K1, K5, K6 0. By tool: `ros2_node_list` 119, `ros2_topic_list` 28, `ros2_service_list` 27, `read_log` 7, `ros2_topic_info` 1. Per model (all arms): gpt-oss 245 events, 175 fixable, in 175 episodes; bonsai 101 events, 7 fixable; lfm3 22, 0; qwen3.5 12, 0. gpt-oss FULL-type: 34 of its 104 episodes (583 requests) have a fixable event, saved-max 3. Consequence in the menu arms: 260 of 265 events were rejected by the strict pre-check (the model retried); in stock arms 79 returned an error text and 36 have no recorded tool result (S0 21, A1 15; consistent with the stock executor stopping on the validation error, but not verified per event; the write-tail report found 8 such episode-ending cases among write-tool attempts); 26 of those 36 are fixable by the rule (what the answer would then be is unknown).
Not convertible (all 198 events): missing required field 170 (mostly `submit_plan` 28, `ros2_node_info` 26, `ros2_topic_info` 18, `final_answer` 6), an object where a string is expected 53 (E0 46, S0 4, A1 3: the stock `request` argument), a string where an object is expected 38, an array where a string is expected 5, and others.
**Post-hoc (not in the frozen protocol; labelled in `posthoc_relaxed_retry.py`):** the frozen retry definition requires the later call to equal the converted arguments exactly, but a model retrying a wrong optional field usually just omits it. With matching modulo empty arrays, empty strings and null: FULL-type menu 27 pure retry requests (0.89% of requests, 40,861 tokens, still only gpt-oss; for gpt-oss alone 27 of 583 requests = 4.6%); all arms 122 pure retry requests, 239,216 tokens. This is just under the 1% bar and still one model, so the frozen verdict does not change; it shows the frozen definition undercounts.

## Interpretation (labelled; hypotheses, not measurements)
1. The method loop's exposure is small for three of four models; it is a gpt-oss behaviour (`blacklist` passed as `""`, `"^$"` or `"None"`). For gpt-oss it is a few percent of requests, not negligible, so a plumbing fix is worth giving to every arm (including the stock executor) to keep the comparison fair rather than counting it as a method gain.
2. Nothing here supports a claim that the conversion improves correctness: in the menu arms every event was a pre-check rejection followed by a retry (the pre-check does not end episodes), and the 36 no-result events were all in stock-executor arms (S0 and A1), the arms the comparison would give the same fix.

## Limits and defects (reported, not patched)
- **K2 is lossless literally, not always by intent.** 17 K2 events include `blacklist: "^$"` and `blacklist: "None"` (example `small_model_harness_20261115/pilot_part2/gpt-oss_20b-e1h/017-e1h_abs_1-C1-gpt-oss_20b-s2/trace.jsonl`). Wrapping `"None"` as the one-element list `["None"]` would exclude names containing "None", which is not the model's evident meaning ("no blacklist"). K3 (`""` or null to `[]`) is the intent-preserving reading; K2 on such strings is a limit of the rule.
- **Retry definition too strict** (post-hoc section above). The frozen number is a lower bound; the post-hoc number is also an upper bound for the same reason (the model may have answered differently).
- The strict check judges every call against its request's schema, including stock-arm calls that pydantic might coerce silently; no event was classed `executed_by_stock`. 5 menu-group events returned an error text instead of a pre-check rejection (likely arms without the strict pre-check; not checked per event).
- Episodes recur across arms, tasks and seeds; the 1,832 are not independent. Tasks without a `model_end` (timeouts) are included as requests without a response.
- Teammate-context check (`rosa-contexts`) not done.

## Open search (patterns noticed that are not this study's target; counts over the 1,832 saved episodes, no filtering)
- **`final_answer` with invalid arguments:** 44 events (bonsai 29, lfm3 8, qwen3.5 6, gpt-oss 1); e.g. `small_model_harness_20261115/pilot/lfm3_1.7b-e1h/017-e1h_chg_2-C1+FN-lfm3_1.7b-s2/trace.jsonl`. 6 are a missing required field.
- **`submit_plan` (arm C1+H7) argument errors:** 29 events, all in that arm; 28 are a missing required field; e.g. `small_model_harness_20261115/pilot_repair/lfm3_repair-e1h/014-e1h_abs_2-C1+H7-lfm3_1.7b-s1/trace.jsonl`.
- **Write-tool calls with invalid arguments:** 57 events (bonsai 53, qwen3.5 3, lfm3 1), all in stock-executor arms (E0 mostly); e.g. `small_model_harness_20261115/pilot/lfm3_1.7b-stage3/020-v2-A1-lfm3_1.7b-s1/trace.jsonl`. Consistent with the write-tail report (none executed).
- **Stock executor, no recorded tool result after an invalid call:** 36 events (S0 21, A1 15); same example trace; whether each ended the episode was not checked.
- **Object where the stock schema expects a string (`request`):** 53 events (E0 46, S0 4, A1 3); not convertible by a lossless rule.
- **`read_log` with numeric strings:** 7 K4 events (bonsai NO_MENU arm), e.g. `steady_loop_ablation_20261117/full_20261117T104600Z/bonsai-2_4b-e1h/019-e1h_chg_2-NO_MENU-bonsai-2_4b-s1/trace.jsonl`; also a log filename passed with a leading slash in the same trace.
- **Concentration:** 175 of 458 gpt-oss episodes have a fixable argument-type event in some arm; 0 of 458 lfm3 and 0 of 458 qwen3.5. A single model's tool-call habit drives the whole count.
