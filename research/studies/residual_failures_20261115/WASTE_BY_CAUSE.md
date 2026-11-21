# WASTE_BY_CAUSE: where the above-floor requests of successful episodes go, by cause; reuse; name fixer

Read-only: existing pilot traces, frozen **scorer-v2.0**, no model, no ROS, no held-out data, no new mechanism. Supported-complete = scorer v2.0 (422 of 576 valid episodes); 130 of those 422 have excess <= 0 and get no attribution (the tables count the others). Floors as in [WASTE_ANALYSIS.md](WASTE_ANALYSIS.md). "Fixed loop" = arm C1; "stock executor" = arm A1 (47 tools, stock executor; S0, the verbatim stock prompt, was never run). Scripts: `waste_by_cause.py`, `by_cause_tables.py`, `reuse_h2.py`; data: `by_cause_v1.json`, `by_cause_v2.json`.

**Rules were written down first.** v1: `WASTE_BY_CAUSE_RULES.md` (sha256 `74044a0a...`). After the first hand check (below) the rules had three systematic faults, so I wrote v2 (`WASTE_BY_CAUSE_RULES_V2.md`, sha256 `2f6a2be5...`) before computing any v2 number. Both results are reported; the v2 numbers are the main ones. While computing v1 I also fixed a coding bug in rule (c1) (an expression that could never match) before looking at any table; v1 as reported is the fixed code, reproduced exactly on a rerun.

The method in two lines (details in the rules files): each request gets at most one cause tag by the first rule that matches, order e, d, b, c, f-off-route, a, f-other (v2); then the episode's excess E is spread over the tags (if tags W <= E the rest is (g) other; if W > E the tags are scaled by E/W because some tagged requests are part of the floor). Fractions are kept in the sums.

---
# PART 1, MEASURED: above-floor requests per cause (rules v2)

Causes: (a) independent calls issued one per request instead of batched, (b) wrong name form then recovered, (c) re-lookup of information already in an earlier result, (d) identical call repeated, (e) bad arguments rejected and retried, (f) wrong tool or pattern, (g) other. Last column = raw tagged requests per cause before scaling.

### Arm C1 (attributed above-floor requests per cause; raw tagged requests in the last column)
| model | episodes | with excess > 0 | above-floor requests (sum over those) | (a) batching | (b) name form | (c) re-lookup | (d) repeat | (e) bad args | (f) wrong tool/pattern | (g) other | raw tags a / b / c / d / e / f |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lfm3:1.7b | 17 | 10 | 40 | 13.3 | 6.9 | 7.6 | 1.4 | 1.9 | 8.9 | 0.0 | 19 / 8 / 10 / 4 / 2 / 15 |
| qwen3.5:9b | 20 | 11 | 23 | 7.3 | 4.0 | 4.7 | 1.5 | 0.0 | 4.5 | 1.0 | 12 / 4 / 5 / 5 / 0 / 10 |
| gpt-oss:20b | 20 | 16 | 41 | 14.8 | 1.8 | 0.0 | 3.0 | 5.1 | 12.3 | 4.0 | 20 / 2 / 0 / 5 / 7 / 17 |
| bonsai-2:4b | 13 | 9 | 53 | 24.0 | 2.9 | 3.7 | 11.8 | 0.0 | 10.6 | 0.0 | 26 / 3 / 4 / 14 / 0 / 14 |
| all four | 70 | 46 | 157 | 59.5 | 15.6 | 15.9 | 17.7 | 7.0 | 36.4 | 5.0 | 77 / 17 / 19 / 28 / 9 / 56 |

### Arm A1 (attributed above-floor requests per cause; raw tagged requests in the last column)
| model | episodes | with excess > 0 | above-floor requests (sum over those) | (a) batching | (b) name form | (c) re-lookup | (d) repeat | (e) bad args | (f) wrong tool/pattern | (g) other | raw tags a / b / c / d / e / f |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lfm3:1.7b | 15 | 13 | 45 | 14.1 | 12.8 | 4.9 | 2.4 | 0.0 | 9.7 | 1.0 | 20 / 15 / 7 / 4 / 0 / 16 |
| qwen3.5:9b | 19 | 10 | 23 | 7.3 | 2.0 | 3.0 | 4.8 | 0.0 | 5.9 | 0.0 | 10 / 2 / 3 / 9 / 0 / 12 |
| gpt-oss:20b | 7 | 3 | 3 | 1.5 | 0.0 | 0.0 | 1.5 | 0.0 | 0.0 | 0.0 | 3 / 0 / 0 / 3 / 0 / 0 |
| bonsai-2:4b | 6 | 5 | 11 | 3.3 | 0.0 | 2.7 | 0.7 | 0.0 | 4.3 | 0.0 | 4 / 0 / 3 / 1 / 0 / 6 |
| all four | 47 | 31 | 82 | 26.2 | 14.8 | 10.6 | 9.4 | 0.0 | 19.9 | 1.0 | 37 / 17 / 13 / 17 / 0 / 34 |

Shares of the above-floor requests, all four models, v2: **fixed loop (C1, 157 requests):** (a) 38%, (f) 23%, (d) 11%, (c) 10%, (b) 10%, (e) 4%, (g) 3%. **Stock executor (A1, 82 requests):** (a) 32%, (f) 24%, (b) 18%, (c) 13%, (d) 11%, (e) 0%, (g) 1%. By model under C1: lfm3 (a) 13, (f) 9, (c) 8, (b) 7 of 40; qwen (a) 7, (c) 5, (f) 5, (b) 4 of 23; gpt-oss (a) 15, (f) 12, (e) 5, (g) 4 of 41; bonsai (a) 24, (d) 12, (f) 11, (c) 4 of 53. Under A1 the (e) share is zero because a rejected argument ends the stock episode (it cannot be an above-floor request in a *successful* episode), and (b) is larger for lfm3 (13 of 45).

Appendix, all arms (v2):

### Appendix: all arms, all four models pooled
| arm | episodes | with excess > 0 | above-floor requests (sum over those) | (a) batching | (b) name form | (c) re-lookup | (d) repeat | (e) bad args | (f) wrong tool/pattern | (g) other | raw tags a / b / c / d / e / f |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C1 | 70 | 46 | 157 | 59.5 | 15.6 | 15.9 | 17.7 | 7.0 | 36.4 | 5.0 | 77 / 17 / 19 / 28 / 9 / 56 |
| A1 | 47 | 31 | 82 | 26.2 | 14.8 | 10.6 | 9.4 | 0.0 | 19.9 | 1.0 | 37 / 17 / 13 / 17 / 0 / 34 |
| M0 | 69 | 55 | 224 | 76.4 | 26.4 | 18.0 | 22.5 | 15.6 | 55.2 | 10.0 | 96 / 28 / 20 / 31 / 19 / 73 |
| C1+FN | 67 | 41 | 114 | 47.6 | 5.9 | 12.5 | 14.7 | 7.7 | 24.7 | 1.0 | 57 / 8 / 15 / 23 / 10 / 43 |
| C1+H2 | 66 | 38 | 145 | 56.6 | 5.9 | 19.3 | 15.7 | 8.1 | 31.4 | 8.0 | 70 / 7 / 24 / 26 / 9 / 50 |
| C1+H1e | 68 | 46 | 125 | 45.6 | 15.5 | 9.2 | 17.9 | 6.0 | 26.7 | 4.0 | 60 / 19 / 10 / 29 / 8 / 45 |
| C1+H7 | 35 | 35 | 207 | 48.7 | 3.8 | 7.6 | 20.9 | 77.6 | 46.4 | 2.0 | 56 / 4 / 9 / 26 / 87 / 58 |

Appendix, v1 rules, arm C1 (for the record; v1 over-counts (a), see the check below):

### Arm C1 (attributed above-floor requests per cause; raw tagged requests in the last column)
| model | episodes | with excess > 0 | above-floor requests (sum over those) | (a) batching | (b) name form | (c) re-lookup | (d) repeat | (e) bad args | (f) wrong tool/pattern | (g) other | raw tags a / b / c / d / e / f |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lfm3:1.7b | 17 | 10 | 40 | 19.1 | 4.9 | 7.1 | 1.4 | 1.8 | 5.8 | 0.0 | 28 / 6 / 10 / 4 / 2 / 12 |
| qwen3.5:9b | 20 | 11 | 23 | 12.0 | 1.5 | 3.8 | 1.2 | 0.0 | 3.5 | 1.0 | 19 / 2 / 5 / 5 / 0 / 9 |
| gpt-oss:20b | 20 | 16 | 41 | 25.6 | 1.4 | 0.0 | 2.9 | 4.1 | 4.0 | 3.0 | 39 / 2 / 0 / 5 / 7 / 6 |
| bonsai-2:4b | 13 | 9 | 53 | 32.0 | 0.7 | 2.8 | 10.5 | 0.0 | 7.0 | 0.0 | 40 / 1 / 4 / 14 / 0 / 10 |
| all four | 70 | 46 | 157 | 88.8 | 8.4 | 13.8 | 15.9 | 5.9 | 20.2 | 4.0 | 126 / 11 / 19 / 28 / 9 / 37 |

# PART 1b, HAND-READ: how accurate are the rules (10 random tags each)

For each rule version, 10 tagged requests were drawn at random from supported C1 and A1 episodes with excess > 0 (v1 seed 20261115 from 337 tags; v2 seed 20261116 from 299 tags) and judged by me against the trace. This is an estimate on 10 items each, by one reader, not a measurement.

**v1: 1 of 10 right.** Wrong: #1, #3 (recovery `node_list` after a failed bare name tagged (a), true cause (b)); #4 (a lookup of information already in a result, tagged (a)); #5 (a needed request tagged (a)); #6 (a wrong-name-form service lookup, with an empty error, tagged (f)); #7, #8, #10 (needed requests whose arguments appeared in a big list result, tagged (a)); #9 (a wrong-tool `topic_echo` tagged (a)). Right: #2 (`topic_echo` of a parameter name, (f)). The faults: "known" counted any name that appears in a list result; plain recovery lists and silent empty errors were missed; the priority put (a) before (f).

**v2: 6 of 10 right.**
| # | request | tag | verdict | note |
|---|---|---|---|---|
| 1 | qwen `v2-C1-s1` R4 | (a) | right | `node_info` of the second half of the nodes, batchable with R3 (L19, L44) |
| 2 | gpt-oss `h4-C1-s2` R3 | (a) | wrong | R3 is the first needed request; the waste is R1 and R2 (a rejected call and a pattern list, L5 to L15) |
| 3 | lfm3 `e1h_amb_1-C1-s2` R7 | (a) | right | the cobalt node's `mode` read separately after the basalt reads (L35 to L49) |
| 4 | lfm3 `v2-C1-s1` R5 | (a) | wrong | a second wrong `node_list` pattern (`cedar_reset`) after an empty one (`cedar`); the cause is the wrong search, not batching (L26, L33) |
| 5 | lfm3 `v2-C1-s1` R2 | (f) | wrong | `service_info` is not on my route list but it returned the needed type (L12); not clearly waste |
| 6 | lfm3 `e1h_amb_1-C1-s1` R3 | (c) | right | `param_list` for both nodes although the task names `mode` and `limit` (L21) |
| 7 | gpt-oss `h4-C1-s1` R6 | (a) | right | `topic_info` for the third topic alone, after one-topic requests R4 and R5 (L26 to L40) |
| 8 | qwen `u3-A1-s2` R2 | (b) | right | `node_info("yarrow")` fails, recovered by `node_list` at R3 (L10, L16) |
| 9 | bonsai `h4-C1-s2` R6 | (f) | wrong | `/zephyr`, `/dune`, `/oasis` are namespace-less absolute names; the cause is a wrong name form, (b) (L44) |
| 10 | gpt-oss `v2-C1-s2` R1 | (f) | right | `service_list` with the service name as pattern, off the minimal route (L5) |

Known faults left in v2: the (a) rule can tag a request that is needed because of an unrelated unnecessary request before it (#2); a namespace-less absolute name such as `/zephyr` goes to (f) instead of (b) (#9); (f) off-route is only as good as my route lists (#5). Of the (a) tags in this sample 3 of 5 were right; so (a), the largest category, is an upper estimate, and a share of it belongs to (c), (f) or "needed".

# PART 2, MEASURED: do H1e / H1n reuse events save LLM requests?

Counted from the `reuse`, `reuse_blocked` and request structure in the traces (all valid episodes, not only supported ones). Hypothesis tested: *a cache cannot reduce LLM requests because the model still spends a request issuing the call.*

| | H1e (event-aware, 80 episodes) | H1n (naive, 16 changing-parameter episodes) |
|---|---:|---:|
| episodes where reuse fired | 2 | 16 |
| reuse events (= tool executions replaced by an earlier result) | 3 | 51 |
| events in a request made up only of reused calls | 3 | 50 (1 request mixed reused and new calls) |
| reuse blocked by a parameter event | 15 | 0 |
| LLM requests, same cells vs C1 | 482 vs 486 (80 cells; fewer in 15, more in 12, equal 53) | 96 vs 98 (16 cells; fewer in 1, equal 15) |
| native ROS operations, same cells vs C1 | 536 vs 556 | 41 vs 94 |

What the traces show: in all 54 events the model had already issued the call in its own request; the cache only replaced the native execution behind it. No request disappeared in any event. H1n's native-operation drop (94 to 41) comes mostly from one looping bonsai episode (`e1h_chg_2` seed 2): 36 requests were repeats of the same `topic_list` call, each answered from the cache with the note "Repeated call: returning the result of step 3", and the episode still ran all 40 requests (C1 same cell: 40), so the note did not stop the loop. The two bonsai H1e events sit in a 40-request episode (`stage3/018-h4`, C1 same cell 14 requests), which is also a loop that reuse did not break. The same-cell request differences (H1e -4, H1n -2) are inside the pilot's noise floor and the reuse events do not explain them (3 events in 80 episodes).
**Result (measured plus inference): the hypothesis holds in these data.** Each reuse saved a tool execution (54 in total, 36 of them in one loop) and no LLM request; this follows from where the cache sits (behind the call the model has already decided to make) and is confirmed event by event. A saving of LLM requests would need a policy that changes whether the model issues the call, not a cache behind it. That is an inference about design, not something this pilot tested.

# PART 3, MEASURED: the name fixer (H2)

Counted from `h2_repair` and `h2_no_repair` events and the following tool results; 80 H2 episodes (20 per model).
- **Fired:** 17 repairs in 13 requests, in 10 of 80 episodes (lfm3 4 episodes, qwen 2, bonsai 4, gpt-oss 0). 27 further decisions made no repair (zero or several matching full names).
- **Succeeded:** the repaired call's result was not an error in **16 of 17** repairs. By task relevance (the heuristic of the pilot report) 15 of 17 resolved to a node or entity the task needs; 1 was harmful (`e1h_abs_1` seed 2: `/ember/mistral`, not running, was repaired to the running `/e1h/ember/mistral`, episode unsupported while C1 on that cell was supported); 1 repaired a topic name used as a service (`reef_t` to `/plant32/reef_t` in `service_info`), which still failed.
- **Answers on the 10 repaired cells:** supported with H2 in 7, with C1 on the same cell in 9 (H2 lost lfm3 `h4` seed 1 and the bonsai `abs_1` case; bonsai `h4` seed 1 was unsupported in both).
- **Requests versus C1 on the same cells:** on the 10 cells where H2 repaired: 91 versus 105 (per cell 0, -1, -4, -2, -2, -3, +2, 0, -4, 0). On the 70 cells where it did not fire: 387 versus 381 (+6). All 80 cells: 478 versus 486. So the apparent saving on repaired cells (-14) is the same size as the difference H2 shows where it never acted (+6 in the other direction), i.e. inside noise.
- **Counterfactual (inference, not measured):** each of the 13 requests that contained a repair would have returned an error under C1, so the fixed loop needs at least one more request there (recovery); an upper bound of about 13 requests over 80 episodes (0.16 per episode), minus the harmful case, against 486 requests in total (about 3%). The measured same-cell figure (-14 on those cells, -8 overall) is consistent with that order but cannot confirm it.

# Limits
- Attribution rules v2 are about 60% accurate on 10 hand-checked items; the large (a) share is an upper estimate. Per-cause numbers should not be quoted to the decimal; the order of causes (batching, wrong tool or pattern, then repeats, re-lookups and name form) is more trustworthy than the shares.
- Supported episodes only: failed episodes' waste is not included. Fractions come from scaling when tags exceed the excess.
- Reuse and H2 cell comparisons include the pilot's run-to-run noise (identical-config pairs differ in 12 to 80 percent of cases); the event counts are exact, the request differences are not evidence of an effect.
- One reader, one analyst; no second review; S0 not run.
