# FAILURE_CATEGORIZATION: existing traces mapped to the rows of the failure taxonomy map (read-only; no runs, no code changes)

Rows are those of `2026-11-14-failure-taxonomy-map.md` (row 1 repeated calls, 2 incorrect argument values, 3 argument types, 4 missing argument names, 5 hallucinated tool names, 6 wrong or unneeded tool, 7 tool exceptions crash the episode, 8 repeating a failed call, 9 serialized calls, 10 insufficient calls or premature stop, 11 unsupported or guessed answer values, 12 invalid output format, 13 wrong semantic source or misinterpretation, 14 answering in prose without executing, 15 context forgetting). Traces: `research/_artifacts/runs/headroom_diagnostic_20261112/`; "line" is the trace line (a `model_end` line unless stated); "R" is the request number. One primary row per item, secondary rows noted. One analyst (Claude) read every item; the categorization is a reading of the traces, not a measurement.

## 1. lfm3:1.7b: its unsupported episodes (14 of 24; 13 wrong answers plus 1 abort)
Run folder `repeat_rate_20261114T100614Z/lfm3_1.7b/`. The user-visible "13" is the 13 episodes that ended with an answer that failed the frozen scorer; the 14th unsupported episode is an abort (row 7, below).

| primary row | count of the 13 | episodes | one example (trace line) |
|---|---:|---|---|
| 12 invalid output format | **8** (6 + 2) | 6: 07-u2-r0, 19-u2-r1, 08-u3-r0, 18-u3-r1, 13-h4-r1, 22-h2-r1. 2: 11-v3-r0, 12-v3-r1 | 6 episodes: final request `07-u2-ollama-r0` line 40 contains 3 JSON objects in prose; the last one, `{"node": "/plant32/yarrow", "gain": 50}`, equals the expected answer, but the frozen scorer reads the first object (`{"gain": "Integer value is: 50"}` quoted from a tool result). 2 episodes: `11-v3-ollama-r0` line 34 ends with `done_reason: length` (4096 output tokens spent deliberating, no answer); secondary rows 13 and 10 |
| 13 wrong semantic source or misinterpretation | **4** | 02-p3-r0, 09-p4-r0, 14-p4-r1, 17-p3-r1 | `09-p4-ollama-r0` line 40 (R7) reads `/plant32/beacon`'s setpoint (694) after the chain (lattice, quartz, beacon, juniper); the final request at line 46 answers `first=/plant32/lattice, second=quartz, third=beacon`, counting the start node as the first hop (off by one). Secondary row 10: `juniper`'s setpoint (873) is never read |
| 11 unsupported or guessed answer value | **1** | 00-v2-r0 | `00-v2-ollama-r0` line 88 (R15): "we can safely assume node name is `/plant32/cedar`" and answers `{"node": "/plant32/cedar", ...}`; that node never appears in a tool result. Secondary rows 13 (treats the service name as a node name) and 2 |
| (14th unsupported episode) 7 tool exception | 1 | 15-v2-r1 | `15-v2-ollama-r1` request at line 70 (R12): `ros2_node_list` with `pattern='*cedar*'` raised `re.error: multiple repeat at position 2` and ended the episode (secondary rows 2 and 13) |

Facts that matter for reading row 12: in 6 of the 13, the **last** JSON object of the answer equals the expected answer (checked by parsing top-level objects); the frozen scorer (vendored `baseline_audit.first_object`) takes the first object, which in these answers is an object quoted from a tool result or a short-name draft. Support screen: no missing support in those six. This does not change any frozen result in this study (lfm3 has 0 identical repeats in all 24 episodes, so its R is 0% under either reading), and I did not rescore. In the other 7 no top-level object equals the expected answer (rows 13, 11 and the two length stops).

## 2. lfm3:1.7b: its 9 REC requests (supported episodes with excess)
| primary row | count | requests | example |
|---|---:|---|---|
| 2 incorrect argument values (bare name, then full name) | **7** | 06-h2-r0 R4; 04-h4-r0 R6; 05-h3-r0 R5; 16-h3-r1 R5; 21-u4-r1 R4, R5, R8 | `06-h2-ollama-r0`: R3 line 16 `node_info(['anvil'])` -> "Unable to find node 'anvil'"; R4 line 22 `node_info(['/plant32/anvil'])` succeeds. In 04-h4, 05-h3 and 16-h3 the recovery runs through a `node_list` first (line 28, 22, 22) and the REC request is the later full-name `node_info` |
| 13 wrong semantic source (service name used as a node name) | **2** | 03-v4-r0 R8; 23-v4-r1 R8 | `03-v4-ollama-r0`: R7 line 40 `param_list('/plant32/cedar')` -> "Node not found"; R8 line 46 recovers with `node_info('/plant32/wharf')`. `23-v4-ollama-r1`: R7 line 40 `node_info('/plant32/cedar_reset')` -> not found; R8 line 46 `param_list({})`. Secondary row 2 |

## 3. ornith-1.5:9b: its 4 REC requests
All four are row 2 (bare node name, then full name): `04-h4-ollama-r0` R3 line 20, `05-h3-ollama-r0` R3 line 16, `13-h4-ollama-r1` R3 line 20, `16-h3-ollama-r1` R3 line 16, each preceded by `node_info(['anvil'])` -> "Unable to find node 'anvil'" (R2, line 10). Example: `05-h3-ollama-r0` R2 line 10 fails, R3 line 16 re-issues with `/plant32/anvil` together with a `node_list(pattern='anvil')`. Count: row 2 = 4 of 4.

## 4. Qwen A0 `service_info` loop (`stage3_20261112T225309Z/20-v2-ollama-r0` and `44-v2-ollama-r1`)
**It repeats a successful call**, so it is row 1, not row 8. Each episode makes 16 identical `ros2_service_info(['/plant32/cedar_reset'])` requests (R1 to R16, trace lines 4 to 94): 15 repeats of R1, whose result `{'/plant32/cedar_reset': 'std_srvs/srv/Trigger\n'}` is a success every time (no error text in any of the 16 results). Then `node_list` (R17), `node_info` (R18) and the answer (R19). Row 8 (repeating a **failed** call) does not occur there. Over all 192 episodes of Stage 3, 3b, 3d and the repeat-rate run, identical calls re-issued when every earlier identical call had failed: **0** (identical calls re-issued after a success, counted per call: Qwen A0 50, A1 18, A2 24, Luna A0 1, Luna A1 0, gpt-oss 2, lfm3 0, ornith 4).

## 5. Rows 5 and 14 across all models (192 episodes: Qwen A0, A1, A2; Luna A0, A1; gpt-oss, lfm3, ornith; 24 each)
| model / arm | row 5 hallucinated tool names | row 14 answer with zero tool calls | answered with values no tool result supports (related to row 11) |
|---|---:|---:|---:|
| Qwen A0, A1 | 0, 0 | 0, 0 | 0, 0 |
| Qwen A2 | 0 | 0 | 2 (`03-p4`, `22-p4`: setpoint 873 not read) |
| Luna A0, A1 | 0, 0 | 0, 0 | 1, 1 (`05-u4-openai-r0`, `19-u4-openai-r0`: `quill` gain 59 not read) |
| gpt-oss:20b | 0 | 0 | 1 (`17-p3-ollama-r1`: `quartz` next_node not read) |
| lfm3:1.7b | 0 | 0 | 6 |
| ornith-1.5:9b | 0 | 0 | 2 |

Row 5: every tool name in every model request is one of the 47 registered tools; there are no `invalid_tool_calls` events. Row 14, strictly: no episode answered without executing a tool call. Closest cases (not counted as row 14): `lfm3` `11-v3-ollama-r0` line 34 and `12-v3-ollama-r1` line 34, where the model spent its last request (4096 tokens, length stop) writing prose about the node list instead of the next tool call; they produced no answer. Every lfm3 final answer is long reasoning prose that ends in JSON, which is the row 12 pattern above.

## Limits
Counts come from the saved traces of the runs named above only; one analyst; the frozen scorer was not changed and nothing was rescored; the "last object equals expected" check is a parsing check on top-level `{...}` objects and is descriptive. Row 12 counts reflect how our harness reads answers (`first_object`), so part of that row is a scorer convention, not a model error; I did not decide which. The taxonomy rows 3, 4 and 6 for gpt-oss and ornith aborts are not part of this request and were not recounted here.
