# Empty errors and empty-string arguments: offline sizing (2026-11-20)

Offline, CPU only, saved traces only; nothing built. Protocol frozen first ([PROTOCOL.md](PROTOCOL.md), [FREEZE.json](FREEZE.json), commit 1bd25e6), script after ([size_empty.py](size_empty.py)). Numbers: [results.json](results.json), [events.jsonl](events.jsonl), [m2_events.jsonl](m2_events.jsonl). Post hoc, labelled: [posthoc.py](posthoc.py), [posthoc.json](posthoc.json).

## Top box
**M1 (informative empty errors): the frozen recovery bar is met, the spread bar is not, the size bar is met as an upper bound, and the sample is 9 episodes of two models.** Read with the post hoc finding below before deciding a live test.
- **Recovery (key number, P1+P3 events):** after an empty error **8 of 79 (10.1%)** recovered within 5 requests; after non-empty not-found errors of the same tools **109 of 246 (44.3%)**. Gap **34.2 pp** (bar 15). Models with >= 5 empty errors: bonsai 53, lfm3 26 (bar 2: met). Requests to recovery: 1.62 (empty) vs 2.11. P1 alone 17.0% vs 49.1% (gap 32.1); P3 alone 0 of 32 (no not-found comparison on its tool).
- **Spread: "one task only".** 6 tools (met), but task v2 gives **67.1%** of the empty errors (53 of 79; bar: no task above 60%), all of them `ros2_service_info cedar_reset` by bonsai. Other tasks: nf_amb_1 9, nf_single_2 8, nf_exact 6, nf_single_1 2, nf_multi_2 1 (all lfm3). qwen3.5 and gpt-oss: 0 empty errors.
- **Size (upper bound):** requests after the first non-recovered empty error, per episode: **180 of 2,596 P1+P3 requests (6.9%, bar 3%)**; 7 episodes (P1 102 = 6.2%, 5 episodes; P3 78 = 8.3%, 2 episodes).
- **Sample reality check:** the 79 events come from **9 episodes** (P1 7, P3 2; 3 ended supported). Two bonsai v2 episodes alone give 40 of them. Per episode (first event only): 2 of 9 recovered vs 74 of 130 (56.9%) after not-found.
- **Post hoc (labelled): there are two different empty errors.** (a) bonsai `service_info` with the short name `cedar_reset`: 53 of 53 empty, while the absolute name always works (26 of 26 ok); the M1 sentence would be true here. (b) lfm3 in block_0003 (seeds 7-8): **22 of 26** empty errors are on names the model already had from the task or earlier results (a valid node or parameter, mixed with ok results for the same kind of call, plus `ROS_LOCALHOST_ONLY` warnings in sibling errors). The M1 sentence "no node named X was found" would be **false** there. Hand reading: 5 of 8 cases (a), 3 of 8 (b).
- **Adjusted comparison (post hoc):** same model and same task, expected recovery 20.1 vs observed 8 of 73: gap 16.5 pp. Task v2 alone: 1 of 53 (1.9%) after empty vs 7 of 56 (12.5%) after not-found, gap 10.6 pp (below 15). Without v2: 7 of 26 (26.9%) vs 102 of 190 (53.7%).
- **M2 (empty-string `blacklist`): 38 rejected calls in 38 episodes, P1+P3** (all gpt-oss; `ros2_node_list` 25, `ros2_topic_list` 9, `ros2_service_list` 4), saved-max **38 requests = 1.46%** of P1+P3 requests (the next request succeeds in 37 of 38; 1 never retried). P2: 113 events, saved-max 111 (0.88%). Other string values (`"None"`, `"null"`): 1 in P1+P3, 3 in P2 (out of scope).
- **What it cannot show:** that the replacement sentence changes behaviour; that bonsai would leave the cedar_reset loop; anything held-out.

## 1. Measured

### 1.1 M1 recovery (events = erroring requests; window 5 requests; definitions in the protocol)
| Population | Empty errors: events / recovered | Not-found (same tools): events / recovered | Gap (pp) |
|---|---|---|---|
| P1 | 47 / 8 (17.0%) | 159 / 78 (49.1%) | 32.1 |
| P3 | 32 / 0 (0%) | 0 (service_info has no not-found form) | n.a. |
| **P1+P3** | **79 / 8 (10.1%)** | **246 / 109 (44.3%)** | **34.2** |
| P2 (not independent) | 322 / 19 (5.9%); 94% task v2, bonsai 310 | none on service_info | n.a. |

Censored events (fewer than 5 requests left, not recovered): 15 empty, 62 not-found (P1+P3). First event per episode (secondary): 2 of 9 (22.2%) vs 74 of 130 (56.9%).

By model (P1+P3): bonsai 1 of 53 (1.9%) vs 35 of 118 (29.7%), gap 27.8; lfm3 7 of 26 (26.9%) vs 50 of 86 (58.1%), gap 31.2; qwen3.5 0 empty (29 not-found events, 41.4%); gpt-oss 0 empty (13 not-found, 92.3%).

By tool (P1+P3, empty vs not-found events / recovery): `service_info` 53 (1.9%) vs 0; `node_info` 11 (63.6%) vs 199 (38.2%) (empty recovers **better**); `param_list` 7 (0%) vs 19 (73.7%); `param_get` 5 (0%) vs 18 (83.3%); `topic_info` 2 (0%) vs 10 (40%); `topic_echo` 1 (0%) vs 0.

By task (empty, events / recovered): v2 53 / 1, nf_amb_1 9 / 0, nf_single_2 8 / 6, nf_exact 6 / 0, nf_single_1 2 / 0, nf_multi_2 1 / 1. Not-found recovery by task varies from 0-6% (e1h_abs, nf_absent), 12.5% (v2) to 100% (h4, e1h_amb, several nf tasks): **the recovery rate depends strongly on the task**, so the pooled gap is confounded.

### 1.2 Spread and size
6 tools, 2 models (bonsai 53, lfm3 26), 6 tasks, max task share 67.1% (v2), 9 episodes. Size as in the top box. Clustering (post hoc): 54 of 79 empty events repeat an earlier empty call of the same tool and argument in the same episode; episodes with most events: bonsai v2 s7 20, bonsai v2 s10 20, bonsai v2 s9 12, lfm3 nf_amb_1 s8 9, lfm3 nf_single_2 s7 8, lfm3 nf_exact s8 6. Events are therefore far from independent.

### 1.3 M2 detail
| | P1 | P3 | P1+P3 | P2 |
|---|---|---|---|---|
| Rejected calls with `""` for `blacklist` | 25 | 13 | 38 | 113 |
| Saved-max requests (upper bound) | 26 | 12 | 38 (1.46%) | 111 (0.88%) |
| Never retried | 0 | 1 | 1 | 4 |

All gpt-oss; spread over 12 tasks (e1h_abs_2 5, e1h_amb_1 6, nf_absent 6, h4 5, e1h_abs_1 4, v2 4, others 1-2 each). The saved-max counts the request(s) between the rejection and the next successful call of the same tool; with the coercion the call would have succeeded in the rejected request.

### 1.4 Hand reading (8 empty-error events, seed 20261120, 2 per model in sorted order, bonsai 2, lfm3 2, and shortfalls drawn from the pool because qwen3.5 and gpt-oss have none; bonsai 4 and lfm3 4 in the end)
| # | Event | Reading |
|---|---|---|
| 1 | bonsai v2 s10 (P3), request 32: `service_info cedar_reset`, alternating with `node_list pattern .*cedar.*` -> `{"nodes": []}` | Short service name; the sentence would be true. The model keeps repeating the same two calls. |
| 2 | bonsai v2 s7 (P1), request 10: same call, between regex errors `*reset$` | Same. |
| 3 | lfm3 nf_amb_1 s8 (P1), request 16: `param_list /nf/dynamo/eclipse` | **Valid node** (named in the task); empty error with other `[WARN] ROS_LOCALHOST_ONLY` errors around; the sentence would be false. |
| 4 | lfm3 nf_amb_1 s8, request 10: `param_list /nf/ivory/eclipse` | Same as 3. |
| 5 | bonsai v2 s10, request 1: first call `service_info cedar_reset`, then `node_info cedar_reset` -> "Unable to find node" | Short name; true. |
| 6 | bonsai v2 s9 (P3), request 14 | Short name; true. |
| 7 | lfm3 nf_single_2 s7 (P1), request 14: `node_info /nf/lantern/bobbin` | **Valid node** (appears in earlier results); the same kind of call succeeds on neighbours; the sentence would be false; the model recovered. |
| 8 | bonsai v2 s10, request 36 | Short name; true; loop. |

## 2. Interpretation (limited to what was measured)
- On the frozen definitions, recovery after an empty error is much worse than after a non-empty not-found error. Most of that difference sits in one place: bonsai on one task (v2, short service name), where the not-found control is also poor (12.5%) and the gap is 10.6 pp. The cross-task gap is partly a task effect.
- The empty errors that are not bonsai v2 come from lfm3 in one block of the run (seeds 7-8) and mostly name **valid** entities. They look like transient failures of the parameter or node service, not a name problem. The M1 sentence is wrong for those; it could push a model to abandon a valid node. A text that says "no node named X was found" is only true when the typed name is not a real name; the executor cannot tell a transient failure from a wrong name from the empty text alone.
- The measured case for M1 as defined is therefore narrower than the bars suggest: a defect for a short service name on one task by one model. A different sentence for that case (a short service name: "service names are absolute, `/ns/name`") was not sized here and is not proposed.
- M2 is small (1.46% saved-max, one model) and lossless; as the prompt said, it is an executor fix for all arms, report only.
- Not shown: any behaviour change from either mechanism, effects on qwen3.5 or gpt-oss (no empty errors), held-out behaviour.

## 3. Limits and deviations
- 9 episodes, two models, clustered events; the 5-request window is cut by the episode end in 15 + 62 events; recovery counts any successful call on a different entity of the same kind, which can include an unrelated entity. The "ledger-known" test is the classifier's name ledger, not fixture truth.
- Not-found comparison group: tools that produced an empty error in P1+P3; `service_info` has no not-found text at all in these data, so the key comparison is not like-for-like for the dominant case.
- Post hoc analyses (A-D in `posthoc.py`) are labelled and replace nothing. No protocol text changed after the freeze.
- The hand-read quota text said "2 per model"; qwen3.5 and gpt-oss have no empty errors, so the pool filled the rest (bonsai 4, lfm3 4).

## 4. Open search (counts, trace paths)
- **bonsai v2 loop:** 53 calls `service_info cedar_reset`, each empty; the absolute name `/plant32/cedar_reset` never typed by bonsai, while the 26 calls with an absolute name (other models and tasks) all succeed. Traces: `research/_artifacts/exam/lossmap/runs_all/block_0010/007-v2-FULL-bonsai-2_4b-s7/trace.jsonl`, `.../listval/runs_all/block_0010/004-v2-FULL-bonsai-2_4b-s10/trace.jsonl`, `.../block_0010/003-v2-FULL-bonsai-2_4b-s9/trace.jsonl`.
- **lfm3 block_0003 transient empty and `ROS_LOCALHOST_ONLY` errors:** `.../lossmap/runs_all/block_0003/026-nf_amb_1-FULL-lfm3_1.7b-s8/trace.jsonl` (errors with the `[WARN] ... ROS_LOCALHOST_ONLY is deprecated` text inside the `error` field), `.../block_0003/027-nf_single_2-FULL-lfm3_1.7b-s7/trace.jsonl`. Not investigated further (an environment effect is a hypothesis, not tested).
- **Regex errors in the same loop:** bonsai passes `*cedar*`, `*reset$` as `pattern` (glob typed as regex, `multiple repeat`), seen in 3 of the hand-read traces.
- **Different not-found rates by task** (0-6% in absent-entity tasks vs ~100% in several nf tasks) are expected from the task design (the entity does not exist) and are not a defect.

## 5. Reproduce
`PYTHONDONTWRITEBYTECODE=1 nice uv run python research/studies/empty_errors_20261120/size_empty.py`, then `posthoc.py` (asserts the frozen hashes).
