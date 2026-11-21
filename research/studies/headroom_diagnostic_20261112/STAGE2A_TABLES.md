# Stage 2a tables (offline replay; leave-one-task-out; A0 traces)

Training episodes available: 72 (each fold excludes the held-out task). Evaluation episodes: {'qwen': 12, 'luna': 12}.

## Qwen A0 (Stage 1a): per task (both repeats summed)

Removed = primary non-chained count (chained count in brackets). Candidate = requests with at least one candidate call; oracle-removable = every call is a candidate.

| task | requests | candidate requests | oracle removed | learned 0.5 removed | learned 0.7 removed | learned 0.9 removed | static top-1 removed |
|---|---:|---:|---:|---:|---:|---:|---:|
| t1 | 11 | 4 | 4 (4) | 0 (0) | 0 (0) | 0 (0) | 2 (2) |
| t2 | 12 | 2 | 2 (2) | 2 (2) | 2 (2) | 0 (0) | 2 (2) |
| t3 | 6 | 2 | 2 (2) | 2 (2) | 2 (2) | 0 (0) | 2 (2) |
| d1 | 12 | 2 | 2 (2) | 0 (0) | 0 (0) | 0 (0) | 0 (0) |
| d2 | 12 | 3 | 2 (3) | 2 (2) | 2 (2) | 0 (0) | 2 (2) |
| x1 | 10 | 2 | 2 (2) | 0 (0) | 0 (0) | 0 (0) | 2 (2) |
| **all** | 63 | 15 | 14 (15) | 6 (6) | 6 (6) | 0 (0) | 10 (10) |

Saving as a share of requests, with per-task spread (primary count):

| predictor | removed / requests | saving % | per-task saving % (t1..x1) | tasks contributing |
|---|---:|---:|---|---:|
| oracle | 14/63 | 22.2 | 36, 17, 33, 17, 17, 20 | 6 |
| learned 0.5 | 6/63 | 9.5 | 0, 17, 33, 0, 17, 0 | 3 |
| learned 0.7 | 6/63 | 9.5 | 0, 17, 33, 0, 17, 0 | 3 |
| learned 0.9 | 0/63 | 0.0 | 0, 0, 0, 0, 0, 0 | 0 |
| static top-1 | 10/63 | 15.9 | 18, 17, 33, 0, 17, 20 | 5 |

Cost side (primary trajectory; speculation fires after every actual request):

| predictor | speculative units | used by the model's next request | precision | extra native ops | extra input tokens (est.) | input tokens of removed requests | partial requests |
|---|---:|---:|---:|---:|---:|---:|---:|
| learned 0.5 | 60 | 20 | 33% | 40 | 35,871 | 36,145 | 4 |
| learned 0.7 | 48 | 20 | 42% | 28 | 31,332 | 36,145 | 4 |
| learned 0.9 | 0 | 0 | 0% | 0 | 0 | 0 | 0 |
| static top-1 | 111 | 33 | 30% | 78 | 51,015 | 60,407 | 3 |

## gpt-6-luna A0 (Stage 1c): per task (both repeats summed)

Removed = primary non-chained count (chained count in brackets). Candidate = requests with at least one candidate call; oracle-removable = every call is a candidate.

| task | requests | candidate requests | oracle removed | learned 0.5 removed | learned 0.7 removed | learned 0.9 removed | static top-1 removed |
|---|---:|---:|---:|---:|---:|---:|---:|
| t1 | 9 | 4 | 2 (3) | 0 (0) | 0 (0) | 0 (0) | 0 (0) |
| t2 | 9 | 2 | 2 (2) | 1 (1) | 1 (1) | 1 (1) | 1 (1) |
| t3 | 7 | 1 | 1 (1) | 1 (1) | 0 (0) | 0 (0) | 1 (1) |
| d1 | 8 | 1 | 1 (1) | 0 (0) | 0 (0) | 0 (0) | 0 (0) |
| d2 | 6 | 2 | 2 (2) | 0 (0) | 0 (0) | 0 (0) | 0 (0) |
| x1 | 6 | 2 | 2 (2) | 0 (0) | 0 (0) | 0 (0) | 0 (0) |
| **all** | 45 | 12 | 10 (11) | 2 (2) | 1 (1) | 1 (1) | 2 (2) |

Saving as a share of requests, with per-task spread (primary count):

| predictor | removed / requests | saving % | per-task saving % (t1..x1) | tasks contributing |
|---|---:|---:|---|---:|
| oracle | 10/45 | 22.2 | 22, 22, 14, 12, 33, 33 | 6 |
| learned 0.5 | 2/45 | 4.4 | 0, 11, 14, 0, 0, 0 | 2 |
| learned 0.7 | 1/45 | 2.2 | 0, 11, 0, 0, 0, 0 | 1 |
| learned 0.9 | 1/45 | 2.2 | 0, 11, 0, 0, 0, 0 | 1 |
| static top-1 | 2/45 | 4.4 | 0, 11, 14, 0, 0, 0 | 2 |

Cost side (primary trajectory; speculation fires after every actual request):

| predictor | speculative units | used by the model's next request | precision | extra native ops | extra input tokens (est.) | input tokens of removed requests | partial requests |
|---|---:|---:|---:|---:|---:|---:|---:|
| learned 0.5 | 230 | 16 | 7% | 214 | 54,526 | 8,092 | 6 |
| learned 0.7 | 188 | 11 | 6% | 177 | 37,928 | 4,207 | 5 |
| learned 0.9 | 144 | 6 | 4% | 138 | 4,338 | 4,207 | 3 |
| static top-1 | 313 | 22 | 7% | 291 | 72,470 | 8,092 | 9 |

## Kill bar (frozen; evaluated at tau 0.7 on Qwen A0, 63 requests)

- (a) saving under 10% of requests: learned removes 6 of 63 = 9.5% -> **FIRES**.
- (b) learned does not beat static top-1: learned 6 vs static 10 -> **FIRES**.
- (c) all removals from one task: tasks with removals ['t2', 't3', 'd2'] -> **does not fire** (two tasks would be reported prominently, not auto-stop).
- Direction stopped: **YES**. At tau 0.5 learned removes 6, at 0.9 0 (reported, do not rescue a failure at 0.7).

## Pair table examples (training counts, per fold, top pairs)

- held out t1: node_list->('ros2_node_info', (('nodes', 'field:node_list.nodes'),)) 42/55; service_list->('ros2_service_info', (('services', 'field:service_list.serv 6/6; topic_info->('ros2_node_info', (('nodes', 'field:topic_info.endpoint_nod 5/35
- held out t2: node_list->('ros2_node_info', (('nodes', 'field:node_list.nodes'),)) 44/54; node_info->('ros2_topic_info', (('topics', 'field:node_info.publishers' 9/59; topic_list->('ros2_topic_info', (('topics', 'field:topic_list.topics'),) 9/15
- held out t3: node_list->('ros2_node_info', (('nodes', 'field:node_list.nodes'),)) 42/55; node_info->('ros2_topic_info', (('topics', 'field:node_info.publishers' 9/58; param_list->('ros2_param_get', (('node_name', 'carry:node_name'), ('para 8/28
- held out d1: node_list->('ros2_node_info', (('nodes', 'field:node_list.nodes'),)) 53/61; node_info->('ros2_topic_info', (('topics', 'field:node_info.publishers' 9/61; topic_list->('ros2_topic_info', (('topics', 'field:topic_list.topics'),) 9/15
- held out d2: node_list->('ros2_node_info', (('nodes', 'field:node_list.nodes'),)) 41/55; node_info->('ros2_topic_info', (('topics', 'field:node_info.publishers' 9/60; topic_list->('ros2_topic_info', (('topics', 'field:topic_list.topics'),) 9/16
- held out x1: node_list->('ros2_node_info', (('nodes', 'field:node_list.nodes'),)) 43/55; param_list->('ros2_param_get', (('node_name', 'carry:node_name'), ('para 8/28; node_info->('ros2_topic_info', (('topics', 'field:node_info.publishers' 6/62
