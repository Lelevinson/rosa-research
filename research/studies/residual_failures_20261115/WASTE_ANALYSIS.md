# WASTE_ANALYSIS: where successful pilot episodes spend extra requests and tokens

Part B of the 2026-11-15 prompt. No model, no new runs, no held-out data, no new mechanism. Success = supported-complete under **scorer v2.0** ([decision](../../decisions/2026-11-15-scorer-v2.md)), 422 of the 576 valid pilot episodes. Pilot arms: A1 = stock ROSA executor, all 47 tools, Stage 3b prompt (**S0, the verbatim stock prompt, was never run**, so "stock ROSA" below means A1); C1 = our fixed loop; M0 = MetaTool on top of C1; the others are C1 plus one handler. Measured material comes from `waste.json` (made by `waste.py` from the traces); hand-read material is marked as such.

## Floors (analysis only; never used by any method)
Each task's floor is the number of requests of its verified minimal route including the request that submits the answer (depth + 1). Stage 3 tasks: u3 4, p3 4, h4 5, v2 3, from the hand-written minimal routes run with the real tools in Stage 3 (`stage3_fixture.py check`). E1h tasks: amb_1 3, amb_2 3, abs_1 2, abs_2 2, chg_1 3, chg_2 3, from `e1h_fixture.py check` (6 of 6 reproduced). Every task had a floor, so none was derived here. A floor can be beaten: three lfm3 M0 episodes on the changing-parameter tasks used 2 requests against 3 (requests below floor are negative excess in the sums). "Requests above floor" below is requests minus floor, per episode.

## 1. Measured: requests above the floor and tokens, per model and arm (supported-complete episodes only)
Flag columns count requests by simple rules, not by cause: **repeat** = every call of the request repeats an earlier successful call with identical arguments; **failed** = some call returned an error text (and the request is not a repeat); **off-route** = some call uses a tool outside the task's minimal route (and is neither of the above). A request can be a floor-route request and still be flagged (for example a failed attempt at a route call). These are counts of flagged requests, not a decomposition of the excess.

### All supported-complete episodes (scorer v2.0)
| model | arm | supported episodes | mean requests | mean requests above floor | excess as % of floor | mean input tokens | mean output tokens | flagged requests: repeat / failed / off-route (sums) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| lfm3:1.7b | A1 | 15 | 6.2 | +3.00 | 94% | 40848 | 2096 | 2 / 20 / 21 |
| lfm3:1.7b | C1 | 17 | 5.5 | +2.35 | 75% | 22452 | 2216 | 4 / 14 / 19 |
| lfm3:1.7b | M0 | 18 | 5.7 | +2.50 | 79% | 23553 | 2269 | 5 / 12 / 19 |
| lfm3:1.7b | C1+FN | 16 | 4.1 | +0.94 | 29% | 11698 | 1575 | 4 / 7 / 9 |
| lfm3:1.7b | C1+H2 | 15 | 5.3 | +2.27 | 74% | 21489 | 2041 | 3 / 9 / 16 |
| lfm3:1.7b | C1+H1e | 18 | 4.5 | +1.28 | 40% | 12860 | 1921 | 5 / 10 / 13 |
| lfm3:1.7b | C1+H7 | 5 | 16.0 | +12.40 | 344% | 173927 | 10411 | 13 / 8 / 16 |
| qwen3.5:9b | A1 | 19 | 4.4 | +1.21 | 38% | 28270 | 492 | 8 / 7 / 11 |
| qwen3.5:9b | C1 | 20 | 4.3 | +1.15 | 36% | 12104 | 484 | 4 / 7 / 13 |
| qwen3.5:9b | M0 | 19 | 5.6 | +2.37 | 73% | 17400 | 533 | 4 / 8 / 24 |
| qwen3.5:9b | C1+FN | 20 | 4.2 | +1.00 | 31% | 11804 | 451 | 4 / 4 / 13 |
| qwen3.5:9b | C1+H2 | 20 | 4.0 | +0.85 | 27% | 11247 | 467 | 4 / 5 / 11 |
| qwen3.5:9b | C1+H1e | 20 | 4.2 | +0.95 | 30% | 11434 | 468 | 4 / 6 / 11 |
| qwen3.5:9b | C1+H7 | 11 | 8.4 | +5.18 | 163% | 21755 | 979 | 19 / 2 / 27 |
| gpt-oss:20b | A1 | 7 | 3.6 | +0.43 | 14% | 12318 | 737 | 3 / 0 / 0 |
| gpt-oss:20b | C1 | 20 | 5.2 | +2.05 | 64% | 10178 | 1001 | 5 / 4 / 17 |
| gpt-oss:20b | M0 | 18 | 6.1 | +2.83 | 88% | 13304 | 1006 | 3 / 7 / 27 |
| gpt-oss:20b | C1+FN | 18 | 4.9 | +1.67 | 51% | 9129 | 864 | 3 / 0 / 14 |
| gpt-oss:20b | C1+H2 | 18 | 5.1 | +1.72 | 52% | 9533 | 928 | 4 / 1 / 12 |
| gpt-oss:20b | C1+H1e | 17 | 4.7 | +1.59 | 51% | 8291 | 937 | 4 / 1 / 12 |
| gpt-oss:20b | C1+H7 | 13 | 8.0 | +4.85 | 154% | 15261 | 2160 | 9 / 3 / 32 |
| bonsai-2:4b | A1 | 6 | 4.8 | +1.83 | 61% | 28420 | 383 | 1 / 2 / 7 |
| bonsai-2:4b | C1 | 13 | 7.3 | +4.08 | 126% | 24209 | 436 | 8 / 15 / 11 |
| bonsai-2:4b | M0 | 14 | 9.0 | +5.71 | 174% | 31826 | 758 | 9 / 24 / 24 |
| bonsai-2:4b | C1+FN | 13 | 6.8 | +3.77 | 122% | 22087 | 451 | 6 / 12 / 13 |
| bonsai-2:4b | C1+H2 | 13 | 8.2 | +4.85 | 147% | 33377 | 522 | 8 / 11 / 21 |
| bonsai-2:4b | C1+H1e | 13 | 7.5 | +4.31 | 133% | 24627 | 477 | 9 / 18 / 10 |
| bonsai-2:4b | C1+H7 | 6 | 7.2 | +4.17 | 139% | 19530 | 1671 | 4 / 3 / 19 |

### Matched pairs: same model, task, seed, supported under both C1 and A1
| model | pairs | A1 requests above floor (sum) | C1 requests above floor (sum) | A1 input tokens (sum) | C1 input tokens (sum) |
|---|---:|---:|---:|---:|---:|
| lfm3:1.7b | 15 | 45 | 26 | 612721 | 233466 |
| qwen3.5:9b | 19 | 23 | 23 | 537128 | 233356 |
| gpt-oss:20b | 7 | 3 | 7 | 86229 | 44282 |
| bonsai-2:4b | 3 | 4 | 4 | 81945 | 31728 |
| all four | 44 | 75 | 60 | 1318023 | 542832 |

### Requests flagged by rule in C1 supported episodes (flags are per request and can overlap the floor route; not a decomposition of the excess)
| model | C1 excess requests (sum) | repeat of an earlier successful call | contains a failed call | uses a tool outside the minimal route |
|---|---:|---:|---:|---:|
| lfm3:1.7b | 40 | 4 | 14 | 19 |
| qwen3.5:9b | 23 | 4 | 7 | 13 |
| gpt-oss:20b | 41 | 5 | 4 | 17 |
| bonsai-2:4b | 53 | 8 | 15 | 11 |

Reading the measured tables (what they show, not why):
- **A1 survivors are a selected subset.** A1 has only 7 (gpt-oss) and 6 (bonsai) supported episodes, because most A1 runs aborted on a tool exception (pilot report), so A1 rows for those two models are not comparable with their C1 rows; the matched-pair table (same model, task and seed supported under both) is the fair comparison.
- **On matched pairs, C1 saves tokens (-59%: 1.32M to 0.54M input tokens over 44 pairs) far more than requests (above-floor requests 75 to 60).** The token difference is mostly the tool list (47 tools in every A1 request against 13 in C1; in the Step B live check on one lfm3 task the whole episode took 47,195 input tokens over 7 requests with 47 tools and 16,368 over 5 requests with 13), not fewer model decisions. By model: lfm3 45 to 26 above-floor requests, qwen 23 to 23 (unchanged), gpt-oss 3 to 7 and bonsai 4 to 4 on 7 and 3 pairs.
- **Which model wastes how much under C1** (above floor as % of floor): gpt-oss 64%, qwen 36%, lfm3 75%, bonsai 126%. Handler arms differ from C1 by amounts that the pilot's noise floor does not let us read (identical-prompt pairs differ by 12 to 80 percent), so only the large gaps are worth looking at: **C1+H7 is the most wasteful arm for lfm3, qwen and gpt-oss** (above floor 154% to 344%; bonsai's H7 is 139%, below its M0 at 174%), and M0 is above C1 for qwen (73% against 36%), gpt-oss (88% against 64%) and bonsai (174% against 126%).
- The rule flags show that in C1 episodes of lfm3 and gpt-oss roughly half of the excess requests are ones that use a tool outside the minimal route (19 and 17 flagged requests for 40 and 41 excess), for bonsai failed calls dominate (15 of 53), and repeats are small everywhere (4, 4, 5, 8).

## 2. Hand-read: 15 of the most wasteful successful episodes (one reader, a reading and not a measurement)
Selection: for each model the highest requests-above-floor supported episodes, with at most a few from one arm and spread over arms (H7 cases are over-represented among the very top, so only three were taken). Bonsai's four top episodes (v2 seed 2, arms C1, C1+FN, C1+H2, C1+H1e) are the same trajectory at 28 above floor and 145,196 input tokens; one of them (C1) was read. "L" = trace line, "R" = request number (trace paths in `RESULTS_LOG.jsonl`; run ids given). Causes are written as read, not forced into fixed classes.

| # | episode (run id) | req / floor | cause (hand-read) |
|---|---|---|---|
| 1 | lfm3 `lfm3_repair-stage3/005-v2-C1+H7-s1` | 27 / 3 | R1 and R2 (L5, L12) called `service_list` before any plan, each refused and counted as an invalid plan until the fallback (L16); then name searches with service-name patterns on `node_list` (R4, R5, R11; L27 to L80) and a walk over the nodes one `node_info` per request, R14 to R26 (L97 to L185), 13 single calls that could have been one request. |
| 2 | lfm3 `stage3/034-v2-C1-s1` | 17 / 3 | Identical `service_info` for `/plant32/cedar_reset` at R2 (L12) and R7 (L47); the provider was searched with service-name patterns on `node_list` (R4, R5, R8, R13, R15; L26 to L106) and guessed as nodes `/plant32/cedar`, `/plant32/cedar_reset` (R10, R11; L68, L75) and a glob the tool rejected (R12 L82); only R16 (L110) asked `node_info` for all nodes in one call. |
| 3 | lfm3 `e1h/002-e1h_amb_1-A1-s1` | 14 / 3 | Seven failed lookups with short or wrong-form names (`sorrel`, `basalt/sorrel`, `basalt:sorrel`, `e1h/basalt/sorrel`; R1, R3 to R9, L4 to L56) although `node_list` at R2 (L14) already printed the full names; reads then one per request (R11 to R13, L64 to L76). |
| 4 | lfm3 `stage3/007-u3-M0-s2` | 12 / 4 | Started with `service_list` (R1 L5), a `topic_list` pattern for a topic named in the task (R2 L12), `node_info` with short name `yarrow` then `node_list` to recover (R4, R5; L26, L33), the same `node_info` for yarrow twice (R6 L40, R7 L47), and `node_list` before `node_info` for quill (R10 L68). |
| 5 | qwen `stage3/027-h4-C1+H7-s1` | 19 / 5 | The plan listed only `topic_info` (L5), so `node_info` and `node_list` were refused three times (R4, R5, R8; L26, L32, L51), with two replans and a refused `submit_plan` (R6, R9, R11) until the replan limit switched the gate off (L76); ten requests (R3 to R12) went to the gate, the work itself took R13 to R18. |
| 6 | qwen `stage3/037-u3-A1-s2` | 9 / 4 | `node_info` with short name `yarrow` (R2 L10) then `node_list` (R3); the same `node_info` for quill twice (R6 L34, R7 L40, identical result); an unneeded `read_log` with an invented directory (R8 L46) before answering. |
| 7 | qwen `e1h/031-e1h_amb_1-C1-s2` | 8 / 3 | After `node_info` of both nodes (R2) it listed parameters per node (R3, R4; L21, L28) although the names `mode` and `limit` are in the task, then read `mode` twice and `limit` in three separate requests (R5 to R7; L35, L42, L49). |
| 8 | qwen `stage3/042-h4-C1+FN-s2` | 10 / 5 | `param_list` for each of the three publishers (R4 to R6; L30, L37, L44) before `param_get`, each of the six calls in its own request (R4 to R9) although all six arguments were known after R3 (L27). |
| 9 | gpt-oss `stage3/021-h4-M0-s1` | 15 / 5 | A `supertool` planning request (R1 L5); `param_get` with short names `zephyr`, `dune`, `oasis` (R5 L36, R9 L63, R12 L84), each failing, each followed by a `node_list` to find the full name (R6 to R7, R10, R13; one `node_list` rejected for `blacklist: ""`, L46) although the full names were in the topic_info result (L33). |
| 10 | gpt-oss `stage3/054-h4-C1-s2` | 14 / 5 | `blacklist: ""` rejected (R1 L8) and retried (R2); `topic_list` and `node_list` calls for names already known (R2, R4, R5, R7; L11 to L50); `param_get` with `//plant32/dune` and `//plant32/oasis` failed (R10 L71, R12 L85) and retried with a single slash (R11, R13); the reads one per request (R9 to R13). |
| 11 | gpt-oss `stage3/004-h4-C1+H2-s2` | 12 / 5 | `topic_info` called with `topic` and `topic_name` instead of `topics` (R1, R2; L8, L14, both rejected); an unneeded `topic_list` (R5 L31); `topic_info` one topic per request (R6 to R8; L38, L45, L52) and `param_get` one per request (R9 to R11) instead of two batched requests. |
| 12 | gpt-oss `e1h/067-e1h_chg_2-C1+H7-s1` | 12 / 3 | Four `submit_plan` calls built steps with `tool`/`args` instead of `tools` (R1 to R4; L9, L17, L23, L29, the first two counted as invalid plans), a fifth refused (R5 L35): five requests before any read; then `param_get` with the wrong parameter name `meter_flow` (R7 L50, error text) and two `param_list` calls (R8, R11) to find `flow`. |
| 13 | bonsai `stage3/035-v2-C1-s2` | 31 / 3 | `service_info` with the short name `cedar_reset` returned an empty error six times in identical calls (R1, R3, R5, R7, R9, R30; L9, L23, L37, L51, L65, L212); `node_list` three times (R4, R8, R10); then one `node_info` per node for all 19 nodes (R11 to R29, L75 to L205), continuing through four more nodes after `wharf` at R25 (L173). |
| 14 | bonsai `stage3/013-h4-C1+H2-s2` | 22 / 5 | `topic_list` three times (R1, R5, R12; L5, L33, L121) and `node_list` twice (R3, R10); a `node_info` call that mixed topic names into the node list (R6 L40; H2 made no repair, L80); `param_list` before every `param_get` (R7, R9, R11, R16, R18, R20), two of them on a topic name used as a node (R9 L102, R11 L117, error); `topic_info` one topic per request (R13 to R15). |
| 15 | bonsai `e1h/023-e1h_abs_1-M0-s1` | 14 / 2 | The node list at R1 (L9) already showed that `/ember/mistral` was absent, but it went on with failed lookups of `ember/mistral`, `mistral`, `e1h/ember/mistral` (R2 to R4, R6, R8, R9, R12, R13), listed nodes twice more (R7, R11) and hit the regex-glob exception twice (L38, L74) before answering at R14. |

### What recurs in the 15 (counts of episodes where it appears; one episode can have several)
- **Independent calls issued one per request instead of batched:** 10 of 15 (1, 3, 5, 7, 8, 9, 10, 11, 13, 14).
- **Short or wrong-form name tried first, then recovered from the error:** 8 of 15 (1, 3, 4, 6, 9, 10, 13, 15).
- **Call with a bad argument, rejected, then retried:** 5 of 15 (5, 9, 10, 11, 12).
- **Searching with the wrong tool or pattern** (names of services or topics used as node-list patterns, glob patterns that raise exceptions): 5 of 15 (1, 2, 13, 14, 15).
- **Repeating an identical call whose result could not change:** 6 of 15 (2, 4, 6, 13, 14, 15).
- **Looking up something already in an earlier result** (listing parameters whose names the task states, listing nodes or topics again, finding full names that an earlier result printed): 8 of 15 (3, 4, 7, 8, 9, 10, 14, 15).
- **Waste caused by a handler's own gate** (H7 refusals and plan-schema errors): 3 of 15 (1, 5, 12); these exist only in the H7 arm.
- **Continuing after the answer was available:** 2 of 15 (13, 15).

## 3. Summary: where the extra requests and tokens go, fixed loop (C1) versus stock ROSA (A1)
| | C1 (fixed loop) | A1 (stock executor, 47 tools) |
|---|---|---|
| Requests above floor, matched pairs (44) | 60 | 75 (lfm3 45 to 26, qwen unchanged 23, gpt-oss 3 to 7, bonsai 4 to 4) |
| Input tokens, matched pairs | 0.54M | 1.32M (-59% for C1) |
| Main source of the token difference | 13-tool list in every request | 47-tool list in every request |
| Failures that end the episode | none (errors come back as text) | tool exceptions abort the episode (aborts 5, 11, 2, 0 of 20 for bonsai, gpt-oss, lfm3, qwen; pilot report) |
| Where excess requests go (hand-read, both arms) | serialized independent calls; short or wrong-form node names recovered after an error; unnecessary lookups of known information; wrong tool for the provider search | the same, plus recovery after aborts is impossible because the episode ends |

By model (C1, from the measured tables and the hand-read): **lfm3** wastes through name searches and node-by-node walks (75% above floor; 19 of 40 excess requests use an off-route tool); **qwen** wastes least (36%) and mostly through unbatched reads and extra `param_list` calls; **gpt-oss** wastes through short-name or malformed arguments that are rejected and retried and through unneeded lookups (64%); **bonsai** wastes most (126%) through repeated identical failing calls, lookups of everything, and long walks (a single v2 trajectory accounts for 28 of its excess requests in four arms).

## Limits
- Measured part: supported-complete episodes only (so a failure is not credited as "no waste"); floors from the pilot; flags are rule-based counts and the "off-route" flag depends on my route-tool lists (`harness.ROUTE_BY_ID` and E1h `route_tools`).
- Hand-read part: 15 episodes chosen for high waste, so they show what waste looks like, not how common each kind is; counts in "What recurs" are of this sample. One reader; no second review.
- Pilot noise is large (the pilot report's noise floor), so differences between handler arms smaller than the gaps stated above should not be read.
- S0 was not run; "stock ROSA" here is A1. Nothing here selects or proposes a mechanism; Forge's "reply with a tool call" rule and any other candidate are not implemented or tested.
