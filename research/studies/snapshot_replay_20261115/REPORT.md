# REPORT: structure-snapshot offline replay

Protocol and bar frozen before any number (`PROTOCOL.md`, `FREEZE.json`). Offline replay of 80 pilot C1 episodes (20 per model); development evidence on a synthetic fixture; no model, no GPU. The snapshot text was captured with the real ROSA read tools on the two fixtures (`snapshots.json`): Stage 3 fixture 19 nodes, E1h fixture 14 nodes.

## Variant A (node_list, topic_list, service_list, node_info of every node)
Snapshot size: 5627 tokens (Stage 3 fixture), 3908 tokens (E1h fixture), chars/4.

| model | episodes | requests | removable | removable % of all requests | % of non-final requests | input tokens of removed requests (sum) | snapshot tokens charged (sum) | net per episode, mean | net per episode, median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lfm3:1.7b | 20 | 105 | 41 | 39.0% | 48.2% | 171621 | 299980 | +6418 | +10880 |
| bonsai-2:4b | 20 | 189 | 107 | 56.6% | 62.9% | 422522 | 394392 | -1406 | +10726 |
| gpt-oss:20b | 20 | 105 | 32 | 30.5% | 37.6% | 53096 | 343750 | +14533 | +13974 |
| qwen3.5:9b | 20 | 87 | 28 | 32.2% | 41.8% | 70435 | 275282 | +10242 | +11726 |

**Bar for variant A:** (1) removable >= 25% for at least 2 of lfm3, bonsai, gpt-oss: models meeting it = ['lfm3:1.7b', 'bonsai-2:4b', 'gpt-oss:20b'] -> met. (2) mean net input tokens per episode <= 0 for each such model: lfm3:1.7b +6418, bonsai-2:4b -1406, gpt-oss:20b +14533 -> NOT met. **Variant A: FAIL.**

Per task (removable requests / all requests, over the models' episodes, then net tokens per episode mean over the four models):

| task | lfm3:1.7b | bonsai-2:4b | gpt-oss:20b | qwen3.5:9b | net tokens per episode (mean, 4 models) |
|---|---:|---:|---:|---:|---:|
| e1h_abs_1 | 2/4 (50%) | 3/5 (60%) | 2/6 (33%) | 2/4 (50%) | +2832 |
| e1h_abs_2 | 2/4 (50%) | 3/7 (43%) | 2/5 (40%) | 4/6 (67%) | +2787 |
| e1h_amb_1 | 4/13 (31%) | 2/10 (20%) | 2/10 (20%) | 3/13 (23%) | +14522 |
| e1h_amb_2 | 2/10 (20%) | 2/9 (22%) | 4/12 (33%) | 2/8 (25%) | +11888 |
| e1h_chg_1 | 0/6 (0%) | 0/7 (0%) | 0/8 (0%) | 0/6 (0%) | +13191 |
| e1h_chg_2 | 0/8 (0%) | 37/48 (77%) | 0/8 (0%) | 0/7 (0%) | +2011 |
| h4 | 5/16 (31%) | 8/25 (32%) | 6/24 (25%) | 6/16 (38%) | +31213 |
| p3 | 1/9 (11%) | 0/8 (0%) | 0/8 (0%) | 0/8 (0%) | +22274 |
| u3 | 9/15 (60%) | 16/22 (73%) | 4/10 (40%) | 3/9 (33%) | +3183 |
| v2 | 16/20 (80%) | 36/48 (75%) | 12/14 (86%) | 8/10 (80%) | -29434 |

## Variant B (A plus param_list names per node)
Snapshot size: 6073 tokens (Stage 3 fixture), 4218 tokens (E1h fixture), chars/4.

| model | episodes | requests | removable | removable % of all requests | % of non-final requests | input tokens of removed requests (sum) | snapshot tokens charged (sum) | net per episode, mean | net per episode, median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lfm3:1.7b | 20 | 105 | 47 | 44.8% | 55.3% | 188185 | 298446 | +5513 | +7177 |
| bonsai-2:4b | 20 | 189 | 114 | 60.3% | 67.1% | 450278 | 390558 | -2986 | +8538 |
| gpt-oss:20b | 20 | 105 | 32 | 30.5% | 37.6% | 53096 | 370995 | +15895 | +15262 |
| qwen3.5:9b | 20 | 87 | 33 | 37.9% | 49.3% | 87505 | 272301 | +9240 | +11305 |

**Bar for variant B:** (1) removable >= 25% for at least 2 of lfm3, bonsai, gpt-oss: models meeting it = ['lfm3:1.7b', 'bonsai-2:4b', 'gpt-oss:20b'] -> met. (2) mean net input tokens per episode <= 0 for each such model: lfm3:1.7b +5513, bonsai-2:4b -2986, gpt-oss:20b +15895 -> NOT met. **Variant B: FAIL.**

Per task (removable requests / all requests, over the models' episodes, then net tokens per episode mean over the four models):

| task | lfm3:1.7b | bonsai-2:4b | gpt-oss:20b | qwen3.5:9b | net tokens per episode (mean, 4 models) |
|---|---:|---:|---:|---:|---:|
| e1h_abs_1 | 2/4 (50%) | 3/5 (60%) | 2/6 (33%) | 2/4 (50%) | +3219 |
| e1h_abs_2 | 2/4 (50%) | 4/7 (57%) | 2/5 (40%) | 4/6 (67%) | +2392 |
| e1h_amb_1 | 7/13 (54%) | 4/10 (40%) | 2/10 (20%) | 6/13 (46%) | +9009 |
| e1h_amb_2 | 3/10 (30%) | 2/9 (22%) | 4/12 (33%) | 2/8 (25%) | +11981 |
| e1h_chg_1 | 0/6 (0%) | 0/7 (0%) | 0/8 (0%) | 0/6 (0%) | +14237 |
| e1h_chg_2 | 2/8 (25%) | 38/48 (79%) | 0/8 (0%) | 0/7 (0%) | +984 |
| h4 | 5/16 (31%) | 11/25 (44%) | 6/24 (25%) | 8/16 (50%) | +27074 |
| p3 | 1/9 (11%) | 0/8 (0%) | 0/8 (0%) | 0/8 (0%) | +24057 |
| u3 | 9/15 (60%) | 16/22 (73%) | 4/10 (40%) | 3/9 (33%) | +4520 |
| v2 | 16/20 (80%) | 36/48 (75%) | 12/14 (86%) | 8/10 (80%) | -28319 |

## Exploratory only (not used for the bar): ros2_topic_info counted as derivable from the snapshot

| model | removable % of all requests | net per episode, mean |
|---|---:|---:|
| lfm3:1.7b | 48.6% | +2356 |
| bonsai-2:4b | 61.9% | -5785 |
| gpt-oss:20b | 41.9% | +10179 |
| qwen3.5:9b | 43.7% | +6389 |

## Verdict against the frozen bar

- Variant A: **FAIL**
- Variant B: **FAIL**

## What makes the numbers optimistic or pessimistic
- Pessimistic: removed requests are credited only with their own recorded input tokens; the shorter inputs of later requests (they would no longer carry the removed tool results) are not credited. Not modeled: the model's behaviour with the snapshot in context (a different model run).
- Optimistic: requests judged independently, so a request that would only exist because an earlier removed request's result was needed is still counted as removable; calls that returned not-found errors for bare names count as answered by the snapshot's absence proof; the fixtures are small (19 and 14 nodes) and the snapshot grows with graph size; Stage 3 tasks are discovery-heavy by design.
- One analyst; chars/4 token estimate; C1 episodes only (20 per model, 2 seeds), whose request counts are noisy (pilot noise floor).

## Concentration (read with the bar)
Variant A, bonsai: the two most removable episodes (`e1h_chg_2` seed 2: 35 of 40 requests; `v2` seed 2: 24 of 31) hold 55% of its 107 removable requests and its negative mean net comes from them (net -92k and -77k tokens, both are looping episodes). Without those two episodes bonsai is at 40.7% removable with a mean net of +7,867 tokens per episode, i.e. the token condition would fail for every one of the three bar models. For lfm3 and gpt-oss the net is positive in 18 of 20 episodes. The only task where the snapshot pays off for all four models is `v2` (service lookup: node_list plus node_info of every node, 75 to 86% removable); on the parameter-chain tasks (`p3`, `e1h_chg_*`) almost nothing is removable because `ros2_param_get` values are not in a structure snapshot.

## How was the fixed loop's shorter tool list chosen?
It is one fixed list for every ROS task; nothing is chosen per task. It is the constant `DOMAIN_TOOLS` in `studies/small_model_harness_20261115/harness.py` (12 names: `ros2_node_list`, `ros2_topic_list`, `ros2_topic_echo`, `ros2_service_list`, `ros2_node_info`, `ros2_topic_info`, `ros2_param_list`, `ros2_param_get`, `ros2_service_info`, `ros2_doctor`, `roslog_list`, `read_log`) plus `final_answer`; `ros2_param_set` and `ros2_service_call` are hidden and also blocked at execution; the 30 calculation tools and the three system tools are hidden. It follows the owner's build document ("ROS 2 read tools + read_log; write tools hidden; calculation and system tools hidden"); the two judgments mine were counting `ros2_doctor` and `roslog_list` as read tools. It was written before any pilot episode and not changed afterwards (the only later C1-family change was the H7 prompt, which is a different arm). It was not tuned on results and no retrieval or per-task selection is involved (compare: the per-task plan in C1+H7 is made by the model, a different arm).
