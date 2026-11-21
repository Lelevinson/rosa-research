# Build round 1: answer gate and list arguments on the fixed loop (2026-11-15)

Development/pilot tasks only (80 cells = 10 tasks x 2 seeds x 4 models), local Ollama, scorer v2.0 frozen, 320 episodes (4 arms x 80 cells) in one runner. Protocol and success criteria were frozen before any run: [PROTOCOL.md](PROTOCOL.md), hashes in [FREEZE.json](FREEZE.json) and [FREEZE_REV2.json](FREEZE_REV2.json). Every episode is in [RESULTS_LOG.jsonl](RESULTS_LOG.jsonl) (phase `full`; the 8 smoke episodes are phase `smoke` and not counted). Two seeds: descriptive only, no significance claims.

| | |
|---|---|
| **Result** | Both add-ons meet their frozen criteria *literally*: answer gate 70 vs 67 supported (no cell lost to a wrong rejection); list arguments 435 vs 506 requests (-14%), 1.52M vs 2.00M tokens (-24%), supported 67 vs 67. |
| **What it changes** | Neither gain can be credited to its mechanism: none of the 4 cells the gate "won" had a gate firing, and 3 of them are control-side defects (one backend crash, two missed scripted changes); with the 4 cells that have any flagged episode removed, the gate arm is 66 vs 66, and the list savings come from the 76 episodes that never used a list. |
| **What it cannot show** | Causation, significance, or anything beyond these 10 tasks and 4 models. The identical-configuration noise floor is large (gate arm with no gate firing differs from the control by +21 requests and +257k tokens over 73 cells), so a 14 to 24 percent difference is only about 2 to 3 times that floor. |
| **Adoption** | Lists: 4 of 80 episodes (7 list calls, 1.7 items per call) in the list arm, 5 of 80 in the combined arm. Gate: rejections in 3 episodes, nudges in 4; 0 rejections of a supported answer; of 4 rejected answers, 3 were changed and none became supported. |
| **Cost** | Gate arm +35 requests, +796k tokens (+40%), mostly one bonsai episode (17 to 40 requests, no answer) and one lfm3 episode with no firing. List arm -71 requests, -471k tokens. |

## Read this first: validity and attribution
- **Offline pre-check (before any GPU run).** [precheck_gate.py](precheck_gate.py) replayed the 70 supported recorded fixed-loop answers: **0 false rejections**; on the 10 failed ones the gate would have rejected 3. Over all 422 supported episodes of every pilot arm: 0 false rejections ([precheck_all_arms.py](precheck_all_arms.py)). Live, the shadow gate in the control arm checked 74 final answers and would have rejected 3, none of them supported: **0 false rejections live as well**. (No rule change was needed.)
- **Control episodes with a validity defect** ([validity_round1.py](validity_round1.py), [validity_round1.json](validity_round1.json)): gpt-oss h4 seed 1 control is an Ollama backend crash on the first request (`llama-server ... CUDA error`, 1 request); gpt-oss e1h_chg_1 and e1h_chg_2 seed 1 control (and the list arm on chg_2) never received the scripted mid-episode change (no `scripted_change` event: the known missed-hook defect, as in the Forge report). A second backend crash hit the list arm (gpt-oss h4 seed 2). Primary tables keep every episode, labels unchanged. Sensitivity on the 76 cells without any flagged episode (supported / requests / tokens): fixed loop 66 / 481 / 1.93M; + answer gate 66 / 511 / 2.71M; + list arguments 65 / 415 / 1.48M; + both 66 / 445 / 1.58M.
- **Fresh control vs pilot.** Same cells: fresh fixed loop 67/80 supported, 506 requests; the pilot's 70/80, 486 requests. That 3-cell, 20-request gap is the order of magnitude of run-to-run noise.
- **Noise floor.** In the 73 cells where the gate never fired, the gate arm differs from the control only through sampling (the gate was in shadow mode in the control): +21 requests and +257k tokens (lfm3 +231k). Differences of that size are not evidence.
- **List rule (owner-confirmed 2026-11-16).** The assignment text said "single required argument", which read literally selects only `ros2_topic_echo`. The owner confirmed that the intended rule is the schema-based one stated precisely in the next section (`ros2_param_get`, `ros2_param_list`, `ros2_topic_echo`). The literal version was not run and will not be.
- **Runs.** The first full-run attempt stopped before any episode at the "before" oracle (`topic /plant32/upland_t: publishers/subscribers differ`); it was restarted in a new folder. Session qwen3.5:9b-e1h stopped at its final "after" oracle (`node not listed: /e1h/misc/marlin, dahlia`) after all 48 episodes had run; every unfiltered node list of that session (20 calls, last at episode 47) showed all 14 nodes, so the episodes are kept and the event is logged in [BUILD_LOG.md](BUILD_LOG.md). The remaining four sessions ran as a continuation (session filter added to the runner, FREEZE_REV2.json). No write command reached ROS; cleanup was verified after every session.

## What was built
**Answer gate** ([answer_gate.py](answer_gate.py), wired in [round1_harness.py](round1_harness.py): `Round1Arm.final_answer_tool`, `Round1Model._generate`). No LLM call of its own.
1. Bare-text finish: a response with no tool call gets one corrective message; at most 2 per episode, then the text is accepted. Bare-text nudge adopted from Forge (credit).
2. Name check on `final_answer`: a string value (or nested key) is a graph name if it is a valid absolute ROS name (`/` + tokens of `[A-Za-z0-9_]`). Allowed = names in successful tool results of the episode (failed calls and failed items of a list result excluded, so an echoed wrong name does not count) plus names in the task text. Exact: pass. Trailing part of exactly one allowed name: reject with "did you mean". Else reject "never appeared in a tool result or the task". A value without a leading slash is rejected only when it is the trailing part of exactly one allowed full name.
3. Key check: the task text is parsed by one rule (sentences with "keys", items split on commas/"and", parentheses dropped; conditional tasks give alternative sets). It parses all 10 pilot tasks (unit-tested); missing keys reject, extra keys do not.
4. Numbers: log only; no integer in any final answer was unseen (0 logged).
5. At most 2 rejections per episode, then accept. Every firing is logged (`gate_reject`, `gate_followup`, `bare_text_nudge`, `gate_accepted_after_limit`, shadow `gate_shadow`).

**List arguments** ([list_args.py](list_args.py)). **The rule (one rule, derived only from each tool's own schema and docstring; owner-confirmed).** For every tool in the fixed loop's read menu (the 12 `DOMAIN_TOOLS`), an argument `a` accepts one name or a list of names if and only if: (1) its JSON-schema type is `string` or `string-or-null` (so arguments that are already arrays, such as `nodes`, `topics`, `services`, are excluded), and (2) the tool's docstring line `:param a:` contains the whole word `name` and one of the whole words `node`, `topic`, `service` (singular; "list of nodes" does not match). If a tool has several such arguments only the first is extended (none does). Every other argument of the call is shared by all items. Resulting tools, checked by unit test against the real schemas: `ros2_param_get.node_name` (`param_name` shared), `ros2_param_list.node_name` (`pattern`, `blacklist` shared), `ros2_topic_echo.topic` (`count`, `return_echoes`, `delay`, `timeout` shared). Not extended, because already array-typed: `ros2_node_info`, `ros2_topic_info`, `ros2_service_info`. Not extended, because no argument satisfies (2): `ros2_param_get.param_name`, the list tools' `pattern`, `read_log`, `roslog_list`, `ros2_doctor`. Execution: 1 to 20 items; the original tool runs once per distinct item (duplicates dropped, order kept); one combined dict keyed by name in input order; an item failure stays inside its own entry; nothing truncated; an empty list or more than 20 items is rejected before anything runs. Schema and description change only for the extended argument (type string-or-array, one added sentence). Scoring: [score_round1.py](score_round1.py) = scorer v2.0 plus an expansion of each list call into per-item rows (equal to scorer v2.0 on all recorded pilot traces without lists, unit-tested). 26 unit tests: [tests/test_round1.py](tests/test_round1.py).

## Per model and arm
| model | arm | episodes | supported-complete | LLM requests | tokens (in+out) | episodes with an abort/error |
|---|---|---:|---:|---:|---:|---:|
| lfm3:1.7b | fixed loop (fresh control) | 20 | 16 | 117 | 639889 | 0 |
| lfm3:1.7b | + answer gate | 20 | 17 | 138 | 998565 | 0 |
| lfm3:1.7b | + list arguments | 20 | 15 | 117 | 675714 | 1 |
| lfm3:1.7b | + both | 20 | 16 | 130 | 730713 | 1 |
| qwen3.5:9b | fixed loop (fresh control) | 20 | 20 | 89 | 265853 | 0 |
| qwen3.5:9b | + answer gate | 20 | 20 | 88 | 260746 | 0 |
| qwen3.5:9b | + list arguments | 20 | 20 | 91 | 259708 | 0 |
| qwen3.5:9b | + both | 20 | 20 | 92 | 267051 | 0 |
| gpt-oss:20b | fixed loop (fresh control) | 20 | 16 | 116 | 293363 | 1 |
| gpt-oss:20b | + answer gate | 20 | 19 | 99 | 211774 | 0 |
| gpt-oss:20b | + list arguments | 20 | 17 | 88 | 177573 | 2 |
| gpt-oss:20b | + both | 20 | 18 | 106 | 216876 | 1 |
| bonsai-2:4b | fixed loop (fresh control) | 20 | 15 | 184 | 796709 | 0 |
| bonsai-2:4b | + answer gate | 20 | 14 | 216 | 1320656 | 0 |
| bonsai-2:4b | + list arguments | 20 | 15 | 139 | 411635 | 0 |
| bonsai-2:4b | + both | 20 | 15 | 140 | 416017 | 0 |
| all four | fixed loop (fresh control) | 80 | 67 | 506 | 1995814 | 1 |
| all four | + answer gate | 80 | 70 | 541 | 2791741 | 0 |
| all four | + list arguments | 80 | 67 | 435 | 1524630 | 3 |
| all four | + both | 80 | 69 | 468 | 1630657 | 2 |

(supported-complete = scorer v2.0; "episodes with an abort/error" counts recorded errors including the backend crashes above.)

## Same-cell comparison with the fresh control
| arm | both supported | only arm | only control | neither | requests arm-control | tokens arm-control |
|---|---:|---:|---:|---:|---:|---:|
| + answer gate | 66 | 4 | 1 | 9 | +35 | +795927 |
| + list arguments | 61 | 6 | 6 | 7 | -71 | -471184 |
| + both | 62 | 7 | 5 | 6 | -38 | -365157 |

Per-cell table (supported / requests for all four arms) in [REPORT_TABLES.md](REPORT_TABLES.md). Criteria status (frozen beforehand): *gate helps* needs more supported than control and no cell lost to a wrong rejection: 70 > 67 and the one lost cell (bonsai h4 seed 2, 16 to 17 requests) had no gate firing: **met literally, not attributable** (above). *Lists help* needs fewer requests, fewer tokens and supported not lower: -71, -471k, 67 = 67: **met literally, not attributable** (below).

## Answer gate firings and effect
- Gate arm: 5 rejections in 3 episodes (lfm3 v2 seed 2 twice, bonsai v2 seed 1, bonsai h4 seed 1 twice); 4 bare-text nudges in 4 episodes; 2 answers accepted after the 2-rejection limit. The answer changed after 3 of 4 rejections. **Supported after a firing: 0 of 3 rejected episodes; the 4 nudge episodes ended with the same support as the control.**
- Combined arm: 2 rejections in 1 episode (lfm3 v2 seed 1, answer unchanged), 9 nudges in 8 episodes (one gpt-oss e1h_abs_1 episode nudged twice, still unsupported).
- False rejections: **0** (live shadow check in the control and list arms: 74 + 71 final answers, 3 and 1 would-reject, all unsupported).
- Every rejected answer was genuinely unsupported (invented node `/plant32/cedar` for the service provider, bare names in a full-name field), so the checks are accurate, but the model's reaction did not turn them into correct answers in this sample. Cost of one firing can be large (bonsai v2 seed 1).

## List-argument adoption
| arm | episodes | episodes with a list call | tool calls | list calls | items per list call | requests/episode | tokens/episode |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed loop (fresh control) | 80 | 0 | 540 | 0 | - | 6.33 | 24948 |
| + answer gate | 80 | 0 | 573 | 0 | - | 6.76 | 34897 |
| + list arguments | 80 | 4 | 474 | 7 | 1.71 | 5.44 | 19058 |
| + both | 80 | 5 | 497 | 6 | 2.00 | 5.85 | 20383 |

The list arm shows -85 requests and -527k tokens in the 76 episodes **without** a list call and +14 requests, +56k tokens in the 4 episodes that used one (combined arm: -48 / -404k without, +10 / +39k with). The savings therefore do not come from lists; the likeliest sources are the description/schema change affecting how the model batches ordinary parallel calls, and sampling noise (hypothesis, not tested here: needs the same arm with the schema change but no list type, or more seeds).

## Five hand-read episodes (paths relative to `research/_artifacts/runs/build_round1_20261115/full_20261115T120449Z/` for lfm3, qwen and `full_resume1_*` for gpt-oss, bonsai; viewer: [view_episode.py](view_episode.py))
1. **lfm3 v2 seed 2, fixed loop + both: nudge, then supported (control 31 requests unsupported).** `lfm3_1.7b-stage3/000-v2-C1+AG+LA-lfm3_1.7b-s2/trace.jsonl`: after the failed lookups the model answers in text without a call (L80, REQ11), `bare_text_nudge` at L81, it continues with `ros2_node_list` (L84) and finally reads node info for all nodes and submits `/plant32/wharf` at L163 (18 requests). The control (`001-v2-C1-lfm3_1.7b-s2`) used 31 requests and failed, but nothing shows the nudge caused the difference: the same arm without the nudge path was never run on this seed.
2. **bonsai v2 seed 1, fixed loop + answer gate: rejection leads to a longer, answerless episode.** `bonsai-2_4b-stage3/007-v2-C1+AG-bonsai-2_4b-s1/trace.jsonl`: REQ17 answers `/plant32/cedar` (L118); `gate_reject` L120 "never appeared in a tool result"; the model checks it (`ros2_node_info`, L124, "Unable to find node") and keeps searching node by node until the 40-request cap at L282, **no answer**. The control (`018-v2-C1-bonsai-2_4b-s1`) submitted the same wrong answer at 17 requests. Both unsupported; the gate made it +23 requests and removed even the wrong answer.
3. **bonsai h4 seed 1, gate: correct detection, not repaired.** `bonsai-2_4b-stage3/009-h4-C1+AG-bonsai-2_4b-s1/trace.jsonl`: first answer has bare keys/values `dune`, `oasis`, `zephyr`; `gate_reject` L105 "did you mean '/plant32/dune'..."; `gate_followup` L111 changed=true (publishers now full names, `gains` keys still bare); second `gate_reject` L112 (same hint for the `gains` keys); `gate_followup` L118 changed=false; accepted after the limit at L119 and scored unsupported (`gains//plant32/dune` missing). The gate pointed at exactly the scorer's failure; the model fixed half of it.
4. **gpt-oss h4 seed 1, list arguments: list use, but the control is a crash.** `gpt-oss_20b-stage3/024-h4-C1+LA-gpt-oss_20b-s1/trace.jsonl`: single-item list calls to `ros2_param_list` (L31, L47: `node_name: ["/plant32/zephyr"]`, `list_call` items 1, L36) then the answer (11 requests, supported). The control (`001-h4-C1-gpt-oss_20b-s1`) is the `llama-server ... CUDA error` backend crash after 1 request, so this is not a list effect.
5. **lfm3 h4 seed 1, list arguments: real batch of three, more requests overall.** `lfm3_1.7b-stage3/026-h4-C1+LA-lfm3_1.7b-s1/trace.jsonl`: REQ8 (L61) one `ros2_param_get` with `node_name: ["zephyr","dune","oasis"]` (bare names, `list_call` items 3, L72), REQ9 (L76) repeats it with full names and gets the three gains in one request. Supported in 10 requests; the control needed 7. The batch form worked as designed; the bare-name failure it inherited cost one more request.

## Limits
Two seeds and four models: per-cell outcomes flip freely (list arm 6 cells won, 6 lost versus the control, none because of a list call except possibly the cells above). The control itself differs from the pilot by 3 supported cells. Missed-hook and backend-crash episodes are in the primary tables (sensitivity table above). No held-out set was opened; nothing here is a novelty or significance claim. Related papers to compare later (unverified): LLM-Tool Compiler 2405.17438, AgentLTL 2607.02599, Entity Binding Failures 2606.30531.

## Decision for the owner (not made by this report)
Whether to keep either add-on as a paper claim, run the schema-change-without-list-type control, and add seeds, since the main result of this round is that the observed gains are not explained by the mechanisms.
