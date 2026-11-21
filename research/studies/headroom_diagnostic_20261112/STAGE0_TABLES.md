## Table 1. Requests, floor and excess (per corpus / model / arm)

`sup.` = episodes judged supported-complete by the earlier studies (reported, not re-scored here). Excess is shown for all episodes and for supported-complete episodes only; episodes below their floor are counted separately because the floor then does not describe a complete answer.

| corpus | model | arm | prompt | eps | sup. | requests | floor | excess | excess % | sup. requests | sup. floor | sup. excess | sup. excess % | alt-floor excess (sup.) | eps below floor |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | qwen3.5:9b | A | conflicted | 12 | 9 | 76 | 40 | 36 | 90% | 57 | 28 | 29 | 104% | 30 | 0 |
| baseline | qwen3.5:9b | B | conflicted | 12 | 10 | 80 | 40 | 40 | 100% | 68 | 32 | 36 | 112% | 38 | 0 |
| baseline | qwen3.5:9b | C | conflicted | 12 | 9 | 71 | 40 | 31 | 78% | 51 | 28 | 23 | 82% | 24 | 0 |
| coverage | gpt-6-luna | A | deconflicted | 2 | 2 | 8 | 7 | 1 | 14% | 8 | 7 | 1 | 14% | 1 | 0 |
| coverage | gpt-6-luna | B | deconflicted | 2 | 1 | 8 | 7 | 1 | 14% | 4 | 3 | 1 | 33% | 1 | 0 |
| coverage | gpt-6-luna | V | deconflicted | 1 | 1 | 4 | 4 | 0 | 0% | 4 | 4 | 0 | 0% | 0 | 0 |
| coverage | qwen3.5:9b | A | deconflicted | 2 | 2 | 12 | 7 | 5 | 71% | 12 | 7 | 5 | 71% | 5 | 0 |
| coverage | qwen3.5:9b | B | deconflicted | 2 | 1 | 11 | 7 | 4 | 57% | 4 | 3 | 1 | 33% | 1 | 0 |
| coverage | qwen3.5:9b | V | deconflicted | 1 | 0 | 4 | 4 | 0 | 0% | 0 | 0 | 0 | n/a | 0 | 0 |
| narration | qwen3.5:9b | A | deconflicted | 4 | 3 | 18 | 14 | 4 | 29% | 13 | 11 | 2 | 18% | 3 | 0 |
| narration | qwen3.5:9b | B | deconflicted | 4 | 2 | 17 | 14 | 3 | 21% | 8 | 7 | 1 | 14% | 2 | 0 |
| narration | qwen3.5:9b | C | deconflicted | 4 | 2 | 18 | 14 | 4 | 29% | 8 | 7 | 1 | 14% | 2 | 0 |
| **all** | | | | 58 | 42 | 327 | 198 | 129 | 65% | 237 | 137 | 100 | 73% | | |

## Table 2. Reason labels (all requests after the first) and headroom

Headroom = (DEP + RED) / labeled requests. 'DEP batch.' = DEP requests whose arguments were available at least one request earlier. 'designed REC' = recovery from the planted missing node in `d1_recovery` (inside the floor).

| corpus | model | arm | labeled | JUDG | DEP | REC | ORD | RED | FIN | UNCLEAR | headroom | DEP batch. | designed REC | own-call errors | headroom (supported eps) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | qwen3.5:9b | A | 64 | 16 | 22 | 0 | 0 | 14 | 12 | 0 | 56% | 21 | 0 | 0 | 58% |
| baseline | qwen3.5:9b | B | 68 | 13 | 23 | 6 | 0 | 12 | 12 | 2 | 51% | 20 | 0 | 5 | 53% |
| baseline | qwen3.5:9b | C | 59 | 15 | 18 | 4 | 0 | 10 | 12 | 0 | 47% | 16 | 0 | 2 | 52% |
| coverage | gpt-6-luna | A | 6 | 1 | 2 | 1 | 0 | 0 | 2 | 0 | 33% | 2 | 1 | 0 | 33% |
| coverage | gpt-6-luna | B | 6 | 1 | 3 | 0 | 0 | 0 | 2 | 0 | 50% | 2 | 0 | 0 | 33% |
| coverage | gpt-6-luna | V | 3 | 0 | 1 | 1 | 0 | 0 | 1 | 0 | 33% | 0 | 1 | 0 | 33% |
| coverage | qwen3.5:9b | A | 10 | 1 | 3 | 1 | 0 | 3 | 2 | 0 | 60% | 2 | 1 | 0 | 60% |
| coverage | qwen3.5:9b | B | 9 | 1 | 3 | 1 | 0 | 2 | 2 | 0 | 56% | 3 | 1 | 0 | 33% |
| coverage | qwen3.5:9b | V | 3 | 0 | 2 | 0 | 0 | 0 | 1 | 0 | 67% | 1 | 0 | 0 | n/a |
| narration | qwen3.5:9b | A | 14 | 3 | 6 | 1 | 0 | 0 | 4 | 0 | 43% | 4 | 1 | 0 | 40% |
| narration | qwen3.5:9b | B | 13 | 4 | 2 | 2 | 0 | 1 | 4 | 0 | 23% | 1 | 2 | 1 | 17% |
| narration | qwen3.5:9b | C | 14 | 4 | 4 | 2 | 0 | 0 | 4 | 0 | 29% | 2 | 2 | 1 | 17% |
| **all** | | | 269 | 59 | 89 | 19 | 0 | 42 | 58 | 2 | 49% | | | | |

Excluding FIN (never avoidable): 211 non-final requests; (DEP+RED)/non-final = 62%.

## Table 3. Batching adoption

`multi` = requests that emitted 2+ calls. `missed` = single-call requests flagged batchable (every argument was available at least one request earlier, so a perfect batcher would have merged them). Adoption among opportunities = multi / (multi + missed). Baseline arms still carry the original 'never call multiple tools / do not batch' text in every arm; narration and coverage arms do not.

| corpus | model | arm | prompt | requests with calls | multi | missed | adoption among opportunities | eps with a multi-call request | `batch_reads` calls |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| baseline | qwen3.5:9b | A | conflicted | 64 | 0 | 36 | 0% | 0/12 | 0 |
| baseline | qwen3.5:9b | B | conflicted | 68 | 2 | 38 | 5% | 2/12 | 0 |
| baseline | qwen3.5:9b | C | conflicted | 59 | 2 | 31 | 6% | 2/12 | 0 |
| coverage | gpt-6-luna | A | deconflicted | 6 | 4 | 1 | 80% | 2/2 | 0 |
| coverage | gpt-6-luna | B | deconflicted | 6 | 2 | 2 | 50% | 2/2 | 0 |
| coverage | gpt-6-luna | V | deconflicted | 3 | 2 | 0 | 100% | 1/1 | 0 |
| coverage | qwen3.5:9b | A | deconflicted | 10 | 6 | 2 | 75% | 2/2 | 0 |
| coverage | qwen3.5:9b | B | deconflicted | 9 | 5 | 3 | 62% | 2/2 | 0 |
| coverage | qwen3.5:9b | V | deconflicted | 3 | 2 | 0 | 100% | 1/1 | 0 |
| narration | qwen3.5:9b | A | deconflicted | 14 | 4 | 3 | 57% | 3/4 | 0 |
| narration | qwen3.5:9b | B | deconflicted | 13 | 4 | 3 | 57% | 2/4 | 0 |
| narration | qwen3.5:9b | C | deconflicted | 14 | 4 | 4 | 50% | 2/4 | 0 |

## Table 4. Cost of all requests (descriptive)

| corpus | model | arm | requests | input tokens | output tokens | model seconds |
|---|---|---|---:|---:|---:|---:|
| baseline | qwen3.5:9b | A | 76 | 524,730 | 8,363 | 756 |
| baseline | qwen3.5:9b | B | 80 | 556,873 | 9,668 | 914 |
| baseline | qwen3.5:9b | C | 71 | 503,452 | 9,101 | 873 |
| coverage | gpt-6-luna | A | 8 | 14,370 | 575 | 37 |
| coverage | gpt-6-luna | B | 8 | 14,747 | 559 | 40 |
| coverage | gpt-6-luna | V | 4 | 7,816 | 282 | 19 |
| coverage | qwen3.5:9b | A | 12 | 39,882 | 1,839 | 71 |
| coverage | qwen3.5:9b | B | 11 | 36,386 | 1,348 | 54 |
| coverage | qwen3.5:9b | V | 4 | 11,676 | 514 | 20 |
| narration | qwen3.5:9b | A | 18 | 44,391 | 2,035 | 58 |
| narration | qwen3.5:9b | B | 17 | 42,631 | 1,278 | 40 |
| narration | qwen3.5:9b | C | 18 | 47,459 | 1,504 | 46 |

## Table 5. Ten most expensive avoidable requests (supported-complete episodes only)

Avoidable = RED, or DEP whose arguments were available at least one request earlier (batchable). Ranked by the input tokens the model re-read for that request (a proxy for what a merge or deletion would save). `trace:line` is the `model_end` line.

| # | episode | request | label | input tokens | trace:line | calls |
|---:|---|---:|---|---:|---|---|
| 1 | 08-x1-A-r0 (A) | 8/9 | RED | 8,437 | inputs/baseline/08-x1-A-r0/trace.jsonl:54 | set_debugging({"enable_debug_messages": false}) |
| 2 | 23-x1-A-r1 (A) | 8/9 | RED | 8,415 | inputs/baseline/23-x1-A-r1/trace.jsonl:54 | set_debugging({"enable_debug_messages": false}) |
| 3 | 08-x1-A-r0 (A) | 7/9 | DEP | 8,361 | inputs/baseline/08-x1-A-r0/trace.jsonl:48 | ros2_param_get({"node_name": "/diag_turtle/palette", "param_name": "use_sim_time"}) |
| 4 | 08-x1-A-r0 (A) | 6/9 | DEP | 8,287 | inputs/baseline/08-x1-A-r0/trace.jsonl:42 | ros2_param_get({"node_name": "/diag_demo/source", "param_name": "use_sim_time"}) |
| 5 | 08-x1-A-r0 (A) | 5/9 | DEP | 8,212 | inputs/baseline/08-x1-A-r0/trace.jsonl:36 | ros2_param_get({"node_name": "/diag_demo/listener", "param_name": "use_sim_time"}) |
| 6 | 08-x1-A-r0 (A) | 4/9 | DEP | 8,112 | inputs/baseline/08-x1-A-r0/trace.jsonl:30 | ros2_param_get({"node_name": "/diag_demo/calculator", "param_name": "use_sim_time"}) |
| 7 | 03-x1-C-r0 (C) | 4/5 | DEP | 7,937 | inputs/baseline/03-x1-C-r0/trace.jsonl:40 | ros2_topic_info({"topics": ["/diag_demo/chatter", "/diag_turtle/turtle1/pose"]}) |
| 8 | 33-x1-C-r1 (C) | 4/5 | DEP | 7,937 | inputs/baseline/33-x1-C-r1/trace.jsonl:40 | ros2_topic_info({"topics": ["/diag_demo/chatter", "/diag_turtle/turtle1/pose"]}) |
| 9 | 13-d1-C-r0 (C) | 7/8 | RED | 7,753 | inputs/baseline/13-d1-C-r0/trace.jsonl:44 | ros2_topic_info({"topics": ["/diag_demo/chatter"]}) |
| 10 | 19-d1-C-r1 (C) | 7/8 | RED | 7,753 | inputs/baseline/19-d1-C-r1/trace.jsonl:44 | ros2_topic_info({"topics": ["/diag_demo/chatter"]}) |

87 requests in supported-complete episodes are RED or batchable DEP (587,440 input tokens).

## Table 6. What the avoidable requests are (all episodes)

| mechanism | requests |
|---|---:|
| DEP batchable: independent call serialised (ros2_param_get) | 52 |
| RED: exact or subset repeat of an earlier successful read | 18 |
| RED: param_list although the parameter name is in the task | 14 |
| DEP batchable: independent call serialised (ros2_topic_info) | 10 |
| RED: no-information tool (set_debugging) | 10 |
| DEP batchable: independent call serialised (ros2_service_info) | 5 |
| DEP: failed call with mechanically assemblable full name | 5 |
| DEP batchable: independent call serialised (ros2_param_list) | 5 |
| DEP batchable: independent call serialised (ros2_node_info) | 1 |
| DEP batchable: independent call serialised (ros2_topic_list) | 1 |
| (not in headroom) REC unplanned, after an own-call error | 10 |

## Table 7. Per task: actual vs floor (supported-complete episodes)

| task | floor (strict / alt) | supported eps | mean requests | min | max |
|---|---|---:|---:|---:|---:|
| d1 | 3 / 3 | 6 | 7.2 | 6 | 9 |
| d1_recovery | 4 / 4 | 4 | 4.8 | 4 | 6 |
| d2 | 4 / 3 | 1 | 6.0 | 6 | 6 |
| t1 | 4 / 3 | 6 | 7.2 | 5 | 9 |
| t2 | 3 / 3 | 6 | 7.0 | 6 | 9 |
| t3 | 3 / 3 | 9 | 3.2 | 3 | 4 |
| x1 | 3 / 3 | 10 | 5.5 | 3 | 9 |
