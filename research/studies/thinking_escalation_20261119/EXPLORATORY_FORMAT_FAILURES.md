# EXPLORATORY: interface and format failures in the FULL-type loop (what schema-constrained decoding could remove)

2026-11-19, Asia/Taipei. **Exploratory offline count, requested by the owner after the thinking study was closed; no protocol, no bar, no frozen rule; CPU only, existing traces only** (script `exploratory_format_failures.py`, output `exploratory_format_failures.json`). Development evidence (synthetic fixtures, four small models). It counts events in traces; it does **not** show what a constrained decoder would do to a model's behaviour or answers.

**Question.** In the FULL-type arms (the 12-tool steady loop with soft errors, strict pre-check and a finish tool), how many episodes and requests are lost to failures of the interface or output format that schema-constrained decoding (a grammar that forces a valid tool name, valid JSON arguments of the declared types and a valid `final_answer` call) would make impossible?

**Populations (944 episodes, 6,089 requests).** P1 = the 416 FULL-type episodes of the candidate counts (pilot C1, round 1 C1, round 2 CONTROL, ablation FULL, compaction FULL); P2 = the later FULL arms: rendering FULL (144), finish-split FULL (80), repeat-finish nudge FULL (80), thinking part A FULL (80) and replication FULL (144). Episodes recur across studies (same tasks and seeds); they are not independent samples.

## Categories (defined here, applied to the traces)
- **A. Invalid arguments:** the strict pre-check rejected a call (`validation_error` handler event: field, expected type, received value). One rejected call = one lost request (the model has to re-issue it).
- **B. Invented or unavailable tool names:** `tool_not_offered`, a blocked write tool, or a "not a valid tool" result.
- **C. Tool calls written as plain text:** (i) the backend could not parse a tool call (`error parsing tool call: raw=...`, the model wrote prose where a call belongs), (ii) a response with no tool call whose text contains a call-like pattern (`tool_name(`, `"name": "tool_name"`, `<function`).
- **D. Answer written as text instead of `final_answer`:** the episode ended on a text reply with no accepted `final_answer`; split into text with a JSON object inside and text that was **supported** by scorer v2.0 (these episodes are **not** lost: the scorer extracts the object).
- **E. Backend parse errors:** `XML syntax error` or `error parsing tool call` (an episode-ending `ResponseError`); a `llama-server` crash is counted as a backend ending, not a format failure.
- **F. No-answer endings by cause:** iteration cap (loops, not format), backend error, empty message (no content, no tool call).
- **G. Not format, reported for contrast:** `error: multiple repeat at position 2`, an invalid regular expression in the `pattern` argument (a value error inside a string; a type/schema grammar does not forbid it).
**Requests lost** = distinct requests whose call was rejected (A), named an unavailable tool (B), was written as text or failed to parse (C, E) or returned an empty message. **Episodes touched** = episodes with any of A, B, C, E or an empty-message ending.

## Result, all 944 episodes, per model
| model | episodes | requests | invalid arguments: pre-check rejections (events / episodes) | invented or unavailable tool names | tool calls as plain text (parse errors) | XML syntax errors | empty-message endings | **requests lost** (A+B+C+E+empty; share of requests) | episodes touched (supported) | answer as text (episodes) | cap endings / backend-error endings | regex errors in `pattern` (events / episodes; not format) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lfm3:1.7b | 236 | 1,471 | 5 / 5 | 0 | 2 | 2 | 0 | **9** (0.6%) | 9 (5 supported) | 15 (12 with JSON, 7 supported) | 0 / 2 | 28 / 22 |
| qwen3.5:9b | 236 | 1,041 | 7 / 7 | 0 | 0 | 0 | 0 | **7** (0.7%) | 7 (7 supported) | 0 (0 with JSON, 0 supported) | 0 / 0 | 0 / 0 |
| gpt-oss:20b | 236 | 1,221 | 90 / 89 | 0 | 2 | 0 | 3 | **95** (7.8%) | 94 (80 supported) | 62 (62 with JSON, 51 supported) | 0 / 3 | 0 / 0 |
| bonsai-2:4b | 236 | 2,356 | 86 / 6 | 0 | 0 | 0 | 0 | **86** (3.7%) | 6 (1 supported) | 11 (8 with JSON, 5 supported) | 19 / 0 | 98 / 21 |
| **all models** | 944 | 6,089 | 188 / 107 | 0 | 4 | 2 | 3 | **197** (3.2%) | 116 (93 supported) | 88 (82 with JSON, 63 supported) | 19 / 5 | 126 / 43 |

**Headline (all models):** **197 of 6,089 requests (3.2%) are lost to format failures** that constrained decoding would make impossible; **116 of 944 episodes (12.3%) contain at least one**, and 93 of those still end supported; **only 7 episodes (0.7%) end without an answer because of a format failure** (4 backend parse errors, 3 empty messages).
- **Invalid arguments are almost all of it:** 188 rejected calls in 107 episodes. Names: 0 (the menu restricts the names); plain-text or unparseable tool calls: 4; XML errors: 2.
- **By model, it is gpt-oss and, in a few loops, bonsai:** gpt-oss 90 rejected calls in 89 of its 236 episodes (38%), exactly 1 per episode in 88 of them, **7.8% of its requests**; 80 of those 89 episodes still ended supported (the cost is one request, not the answer). Bonsai 86 rejections in only 6 episodes (3.7% of its requests), **76 of them in 3 episodes that hit the 40-request cap** (36, 31 and 9 rejections, all in the name-fix environment, two of them `nf_multi` tasks, all unsupported): a loop of rejected calls, not a one-off. lfm3 5 and qwen3.5 7 rejections (under 1% of requests).
- **Answer as text (D): 88 episodes (9.3%)**, 82 with a JSON object inside, **63 supported (72%)**; mostly gpt-oss (62 of 88). A grammar for `final_answer` would change the format of these endings; the data do not show that they are failures.
- **Not format:** 126 regex errors in `pattern` (43 episodes, bonsai 98 and lfm3 28 events): a type grammar does not prevent them.
- **Not format either:** 19 iteration-cap endings (bonsai 19: loops); constrained decoding would stop the rejected calls inside some of those loops (3 episodes above) but nothing here shows the loop would end.

## The two populations separately
**P1, candidate counts (416 episodes):**
| model | episodes | requests | invalid arguments: pre-check rejections (events / episodes) | invented or unavailable tool names | tool calls as plain text (parse errors) | XML syntax errors | empty-message endings | **requests lost** (A+B+C+E+empty; share of requests) | episodes touched (supported) | answer as text (episodes) | cap endings / backend-error endings | regex errors in `pattern` (events / episodes; not format) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lfm3:1.7b | 104 | 750 | 2 / 2 | 0 | 1 | 0 | 0 | **3** (0.4%) | 3 (2 supported) | 7 (5 with JSON, 3 supported) | 0 / 0 | 16 / 12 |
| qwen3.5:9b | 104 | 502 | 0 / 0 | 0 | 0 | 0 | 0 | **0** (0.0%) | 0 (0 supported) | 0 (0 with JSON, 0 supported) | 0 / 0 | 0 / 0 |
| gpt-oss:20b | 104 | 583 | 37 / 36 | 0 | 2 | 0 | 2 | **41** (7.0%) | 40 (31 supported) | 29 (29 with JSON, 22 supported) | 0 / 3 | 0 / 0 |
| bonsai-2:4b | 104 | 1,185 | 2 / 1 | 0 | 0 | 0 | 0 | **2** (0.2%) | 1 (1 supported) | 3 (1 with JSON, 0 supported) | 10 / 0 | 62 / 12 |
| **all models** | 416 | 3,020 | 41 / 39 | 0 | 3 | 0 | 2 | **46** (1.5%) | 44 (34 supported) | 39 (35 with JSON, 25 supported) | 10 / 3 | 78 / 24 |

**P2, later FULL arms (528 episodes):**
| model | episodes | requests | invalid arguments: pre-check rejections (events / episodes) | invented or unavailable tool names | tool calls as plain text (parse errors) | XML syntax errors | empty-message endings | **requests lost** (A+B+C+E+empty; share of requests) | episodes touched (supported) | answer as text (episodes) | cap endings / backend-error endings | regex errors in `pattern` (events / episodes; not format) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lfm3:1.7b | 132 | 721 | 3 / 3 | 0 | 1 | 2 | 0 | **6** (0.8%) | 6 (3 supported) | 8 (7 with JSON, 4 supported) | 0 / 2 | 12 / 10 |
| qwen3.5:9b | 132 | 539 | 7 / 7 | 0 | 0 | 0 | 0 | **7** (1.3%) | 7 (7 supported) | 0 (0 with JSON, 0 supported) | 0 / 0 | 0 / 0 |
| gpt-oss:20b | 132 | 638 | 53 / 53 | 0 | 0 | 0 | 1 | **54** (8.5%) | 54 (49 supported) | 33 (33 with JSON, 29 supported) | 0 / 0 | 0 / 0 |
| bonsai-2:4b | 132 | 1,171 | 84 / 5 | 0 | 0 | 0 | 0 | **84** (7.2%) | 5 (0 supported) | 8 (7 with JSON, 5 supported) | 9 / 0 | 36 / 9 |
| **all models** | 528 | 3,069 | 147 / 68 | 0 | 1 | 2 | 1 | **151** (4.9%) | 72 (59 supported) | 49 (47 with JSON, 38 supported) | 9 / 2 | 48 / 19 |
P2 has more rejections (147 events in 68 episodes against 41 in 39 in P1) because it contains the name-fix tasks (bonsai loops) and the thinking study's gpt-oss episodes.

## Reading (labelled)
- **Measured:** the ceiling of what a format guarantee could remove from these traces is small in requests (3.2% overall; 7.8% for gpt-oss; under 1% for lfm3 and qwen3.5) and very small in lost episodes (0.7%). It is concentrated: one model (gpt-oss, one rejected call per affected episode) and three bonsai loops.
- **Not measured:** whether constrained decoding would change which tool or which values a small model chooses (it can degrade or improve quality), its latency, the additional cost of grammar compilation, or whether the 3 bonsai loops would end. The count is an upper bound on one kind of waste, not an expected saving; an interface fix inside the harness (the lossless argument conversions of `arg_type_retry_offline_20261119`, which found the same gpt-oss pattern, mostly `blacklist` passed as an empty string) is a cheaper partial route to the same requests (post-hoc relaxed count there: 27 requests in the menu arms of that population).
- **For scale:** in the dead-end replay 4,037 of 12,640 requests (32%) came after a first dead end (a much larger pool of waste, though not all of it avoidable), and the full 48-tool menu multiplied tokens by 2.55 in the ablation (schema cost). Format failures are a minor, concentrated cost next to those; this comparison is only a scale, the populations and definitions differ.

## Limits
Exploratory; categories defined after looking at which signals exist in the traces (pre-check events, backend errors, tool exceptions); event detection depends on what the harness logs (the plain-text tool-call detector finds almost nothing because Ollama's parser turns those into backend errors, which are counted under C and E); "request lost" assumes each rejected call costs exactly one request; episodes recur across studies; FULL-type arms differ slightly between studies; no model-by-task breakdown; the answer-as-text count says nothing about answer quality beyond the scorer's supported flag. Teammate-context check not done.

## Open search (other patterns noticed in the traces while counting; counts over the 944 episodes; no filtering)
- **Rejection loops that end at the cap (bonsai, name-fix `nf_multi`):** 36, 31 and 9 consecutive pre-check rejections in capped episodes: `research/_artifacts/exam/thinking_replA2/runs_all/block_0012/014-nf_multi_*-FULL-bonsai-2_4b-*` and `004-nf_multi_*`, and `research/_artifacts/runs/canonical_render_20261118/full_20261118T031216Z/bonsai-2_4b-namefix/01*`.
- **gpt-oss `pattern`/`blacklist` habit:** 88 of 89 affected gpt-oss episodes have exactly one rejected call (an empty-string or string list argument); 80 of the 89 end supported: a single wasted request almost everywhere.
- **Regex errors in `pattern` (`multiple repeat at position 2`):** 126 events in 43 episodes, bonsai 98 (21 episodes) and lfm3 28 (22 episodes), a failure class no type grammar covers.
- **Empty-message endings:** 3 episodes (gpt-oss) end on a response with no content and no tool call (14-15 tokens), the same empty-response pattern seen in the thinking study's no-answer episodes.
- **Backend `llama-server` crash:** 1 episode in P1 ended on `llama-server process has terminated` (an infrastructure failure inside the model server, not a model failure).
- **Text endings supported in 72%** and mostly gpt-oss: for this model the structured finish is routinely not used, yet the scorer recovers the answer.
