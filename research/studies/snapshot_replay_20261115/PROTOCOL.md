# PROTOCOL: structure-snapshot offline replay (frozen before any computation)

Frozen 2026-11-15. Owner instruction (this session). Offline replay on recorded pilot traces: **no model inference, no GPU, no API**. One deviation from "pure files": the snapshot text itself is captured once per fixture by running the real ROSA read tools on the two pilot fixtures (ROS domain 220; no model involved), so its size and content are real tool output and not my template. No edit to `src/rosa/`, pilot files, held-out sets (not opened). Development evidence on a synthetic fixture; no novelty claim; no method or live run is authorized by this study.

## Question
If a structure snapshot (node list, topic list, service list and every node's node_info, captured at episode start) were placed in the context, how many of the fixed-loop (C1) requests would no longer be needed, and does the snapshot cost more input tokens than the removed requests carried?

## Data
All C1-arm episodes of the four pilot models (lfm3:1.7b, qwen3.5:9b, gpt-oss:20b, bonsai-2:4b) in `research/studies/small_model_harness_20261115/RESULTS_LOG.jsonl` (valid rows only, exclusions in `INFRA_EXCLUDED.json`): 20 per model (10 tasks x seeds 1,2), raw traces from the path in each row. Unit: one request = one `model_start`/`model_end` pair with its tool calls.

## Snapshot (captured at episode start, structure only)
- Variant A: results of `ros2_node_list`, `ros2_topic_list`, `ros2_service_list` and `ros2_node_info` for every listed node, as the real tools return them (`json.dumps` of the result dict). Environment-specific (Stage 3 fixture /plant32 and E1h fixture /e1h), constant within an environment (structure does not change during an episode; the scripted parameter change does not alter structure).
- Variant B: variant A plus `ros2_param_list` for every node (parameter names only). No `ros2_param_get` values, no topic echo, no `ros2_topic_info`.
- Token estimate: characters / 4 (as in Stage 2a).

## Rule: a call is fully answered by the snapshot when
- `ros2_node_list`, `ros2_topic_list`, `ros2_service_list`: always (pattern/blacklist applied to the snapshot list).
- `ros2_node_info(nodes)`: every named node is a full node name in the snapshot, or the real call returned a not-found error and the name is absent from the snapshot's node list (the snapshot proves absence).
- `ros2_service_info(services)`: every service appears in some node's Service Servers entry in the snapshot (its type string is there), or the real call returned not-found and the name is absent from the service list.
- `ros2_param_list(node_name=...)` only in variant B, node in snapshot (pattern/blacklist applied locally); `ros2_param_list` without a node: variant B only.
- Never answered: `ros2_param_get`, `ros2_topic_info` (QoS and endpoint details are not in the snapshot; a secondary line also reports it as "derivable" for node names, labelled exploratory and not used for the bar), `ros2_topic_echo`, `ros2_doctor`, `roslog_list`, `read_log`, `supertool`, `final_answer`, any call that is not a ROS information call.
- A request is **removable** only if it has at least one tool call and every call is answered, and it contains no `final_answer`. Whole requests only, same as Stage 2a. Requests are judged independently (the snapshot is static; there is no predecessor dependence). Denominators: all requests of the model's C1 episodes (primary, as in Stage 2a) and, as a second line, non-final requests.

## Token accounting
- Added by the snapshot: snapshot tokens x (requests that still happen) = snapshot tokens x (requests - removable requests), per episode, because the snapshot is in the context from the first request.
- Saved: the recorded `input_tokens` of each removable request (as in Stage 2a).
- Net per episode = added - saved; reported as mean and median per model, plus per task. Snapshot tokens against the saved input tokens of removed requests are reported side by side. Not credited: the shorter inputs of later requests that would have carried fewer tool results (conservative, same as Stage 2a).

## Frozen bar (decided before any number exists; no reinterpretation)
Evaluated separately for variant A and variant B. A variant **PASSES** if (1) removable requests >= 25% of all requests for at least 2 of {lfm3:1.7b, bonsai-2:4b, gpt-oss:20b}, AND (2) mean net input tokens per episode <= 0 for each model that meets (1) (reported for all four models). Otherwise it FAILS. qwen3.5:9b is reported but is not one of the three bar models. Proceed only on a PASS and name the variant. A pass authorizes nothing by itself.

## Reporting
Per model and per task removable % (with counts), snapshot tokens vs removed-request input tokens, pass/fail against the bar. Plain statement of anything that makes the number optimistic or pessimistic.
