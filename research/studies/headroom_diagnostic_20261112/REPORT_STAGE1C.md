# Stage 1c report: is the remaining Qwen excess a weak-model gap? (2026-11-13)

Development evidence only. Frozen plan `PROTOCOL_STAGE1C.md`; tables `STAGE1C_TABLES.md`, `STAGE1C_RELABEL.md`; raw traces under `research/_artifacts/runs/headroom_diagnostic_20261112/stage1c_20261112T211701Z/`. No mechanism is proposed and no novelty is claimed. Labels F = measured here.

## What ran
12 episodes of gpt-6-luna (arm A0, `parallel_tool_calls` true, no temperature or seed, explicit model name present in the live catalog, existing ChatGPT-plan OAuth path, no API key), the six baseline tasks × 2 repeats, same fixture and prompt change as Stage 1a. All 12 finished with no access, throttling, oracle or cleanup problem; the fixture was verified empty and the ROS daemon stopped. Stage 1 total: 54 episodes (cap 60). Revisions after first inference: none.

## Step 1: Qwen A0 relabel and floor check (F, offline)
Floors for `t2` and `d1` (3 each) were checked by hand against the real tool outputs and are achievable: `t2` node_info already lists the clear/reset servers with types, and `d1` verbose topic_info gives each endpoint's name and namespace, so full names assemble. No floor is corrected. In `d1`, `t2`, `t1` and `x1` the number of avoidable requests (RED, REC, or DEP whose arguments were already available) equals the excess in every episode, so none of that excess is dependency-driven. `d1` excess 3 = two recovery requests after short node names failed plus one repeat read; `t2` excess 3 = one serial `param_get`, one `param_list` the task did not need, one `set_debugging`. `d2` has one extra request that is a judgment (an extra `service_info`).

## Step 2: Luna versus Qwen A0 (F)
| task | floor | Qwen A0 requests | Luna requests | Luna supported-complete |
|---|---:|---|---|---|
| t1 | 4 | 6, 5 | 4, 5 | 2/2 |
| t2 | 3 | 6, 6 | 3, 6 | 2/2 |
| t3 | 3 | 3, 3 | 3, 4 | 2/2 |
| d1 | 3 | 6, 6 | 4, 4 | 2/2 |
| d2 | 4 | 5, 7 | 3, 3 | 0/2 as scored (both arms, same cause) |
| x1 | 3 | 5, 5 | 3, 3 | 2/2 |
Totals over 12 episodes: Luna 45 requests, 186,110 input tokens, 75 native operations, 10 supported-complete; Qwen A0 63, 424,475, 85, 10. `d2` as scored (primary): both Luna answers report only `add_two_ints` and omit `get_type_description`, as Qwen did; read by hand they are the same answer. Luna's 3 requests there are below the strict floor 4 because it over-fetched in parallel (the documented alt floor).
Luna's extra requests are the same kind as Qwen's. In `d1` it listed topics (and nodes) although the topic is named in the task, then read `topic_info` in a later request. In `t2` repeat 1 it issued `node_list`, `topic_list`, `service_list`, `service_info` and `param_get` one per request (lines 5, 12, 19, 26, 35 of `09-t2-A0-r1/trace.jsonl`), while repeat 0 reached the floor in 3 requests with 3 calls per request. The first request was multi-call in 6 of 6 repeat-0 episodes and 2 of 6 repeat-1 episodes; repeat 0 also ran first, so repeat and order are not separated.

## Decision rule (frozen)
- "Gap exists" (Luna ≤ floor+1 on `t2` and `d1` in both repeats while Qwen ≥ floor+3): **not met**; Luna `t2` repeat 1 is floor+3.
- "No gap" (Luna ≥ floor+2 on `t2` or `d1` in at least one repeat): **met on the literal wording** (`t2` repeat 1).
- The frozen wording "on `t2` or `d1` in at least one repeat per task" can also be read as requiring such a repeat for each of the two tasks; `d1` is floor+1 in both repeats, so under that reading the result is **inconclusive**. I did not change the rule; both readings are reported. 12 of 12 episodes were usable.
Reading in plain terms: the strong model does better than the weak one on `d1` (4 vs 6) and `x1` (3 vs 5) but is not free of the excess; it shows the same one-call-per-request pattern in one of its two `t2` episodes. The excess is therefore not only a weak-model gap.

## What the data cannot show
Two repeats per cell (Qwen at temperature 0 gives near-duplicate repeats, Luna samples at the provider); a repeat-versus-order effect cannot be separated; one strong model; six tasks that may be too easy; the `d2` scorer demand is inherited and unchanged.

## The one decision this points to
Whether the serial first request is worth studying as a property of the model's behaviour across repeats (what governs whether the first request batches) or set aside and the project metric moved to native operations and wall time, as Stage 1 already suggested.

## Revisions
None after the first Stage 1c inference. One ambiguity in the frozen decision-rule wording is disclosed above and was not edited.
