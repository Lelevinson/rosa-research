# Forge baseline: two-task smoke report

2026-11-15, Asia/Taipei. **Smoke stopped at 2 tasks × 1 model. Both answers are supported-complete under frozen scorer-v2.0. The full run has not started.** This is technical smoke evidence on a synthetic ROS fixture, with real local Ollama inference; it is not a validated matched comparison. Ollama returned thinking because the released Forge client omits `think:false`, unlike the pilot. This transport mismatch remains visible in the raw outputs and costs.

## Setup and exact scope

The owner's latest decisions supersede the initial [setup stop](SETUP_STOP.md). The [frozen smoke protocol](PROTOCOL_SMOKE.md) contains the pre-inference cell selection, settings and stop rules. The initial stop report retains the canonical five-question preflight, closest negative snapshot replay, source comparison and failed teammate-context fetch. No held-out E2/E3/E3b tasks were opened or run.

| Choice | Executed setting |
|---|---|
| Package and entrypoint | PyPI `forge-guardrails==0.10.1`; released `WorkflowRunner`. All 52 Forge Python sources verified against the installed wheel RECORD. No release source was edited. |
| Model/tasks | `lfm3:1.7b`; pilot Stage 3 `p3` seed 1, then `u3` seed 2, once each. |
| Tools | C1's 12 read tools, unchanged descriptions and Pydantic argument schemas, plus released `respond(message: str)` as terminal. C1's strict argument validator, error handlers, cache and planner were not imported into dispatch. |
| Shared safety setting | `ros2_param_set` and `ros2_service_call` excluded. Same pilot observation-only native-command guard; no guard rejection or write command reached ROS. This is not a Forge feature. |
| Workflow logic | `required_steps=[]`, no prerequisites; max_iterations 40. All other retry/error/rescue/replay/termination behavior is the release default. No custom per-task route or answer map. |
| System prompt | Eight exact C1 system messages, preserving order and message boundaries through the public `initial_messages` API, with only `final_answer` renamed to `respond`. Checked against actual historical C1 model requests. Full prompt and diff below. |
| Compaction | `TieredCompact(keep_recent=2)`, budget 65536. Callback logged compaction; **0 events across both episodes**. The smoke does not test compaction quality. |
| Ollama options | temperature 0.7, num_ctx 65536, num_predict 4096, assigned seed. All 14 actual requests audited. |
| Reasoning caveat | Client configured `think=False`, but released Forge sends no `think` field in that configuration. All 14 responses contain `thinking`; the historical pilot explicitly sent `think:false`. Keeping only the options-dictionary override therefore failed to match this additional Ollama setting. Costs include the returned thinking. No mid-smoke setting change or rerun concealed this mismatch. |
| Loaded context | Ollama `/api/ps` reports `context_length=65536`; snapshots retained for both attempts. The first was recovered after the bookkeeping crash/cleanup, not captured immediately at answer time. |
| Environment | Dedicated uv environment `/tmp/rosa-forge-env-20261115`, Python 3.12.3. ROSA/LangChain dependencies reused read-only from project `.venv`; project environment, dependency files and production code unchanged. Versions/import origins in `SMOKE_PROVENANCE.json`; isolated package inventory in `SETUP_PROVENANCE.json`. |
| Integration versions | LangChain 0.3.30, langchain-core 0.3.86, Pydantic 2.14.3 and httpx 0.28.1 as actually imported. Forge's isolated Pydantic is used when constructing tool schemas. This environment differs from executing C1 entirely in its own project interpreter. |
| ROS fixture | Unchanged Stage 3 fixture; ROS_DOMAIN_ID=220, ROS_LOCALHOST_ONLY=1. Owned fixture nodes launched with the pilot interpreter. Same oracle and readiness helpers. |
| Timeout | 900 seconds per episode; 90-second HTTP timeout, as in pilot. No episode timeout, crash or budget exhaustion. |
| Scoring | `scorer-v2.0`, SHA-256 `c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9`, verified before scoring. `respond` result is final text, processed by frozen last-object/unwrap and support rules. |
| Logging | Both attempts appended to `RESULTS_LOG.jsonl`, with raw trace hashes and paths. First row recovered offline after the logging failure; no inference repeated. Requests, raw responses, usage, tool/native events and final output retained. |

## Observed smoke results

| Task / seed | Supported-complete | LLM requests | Input tokens | Output tokens | Native operations | Compactions | Episode error |
|---|---:|---:|---:|---:|---:|---:|---|
| p3 / 1 | yes | 4 | 8,462 | 2,810 | 3 | 0 | none |
| u3 / 2 | yes | 10 | 26,936 | 12,139 | 9 | 0 | none |
| Total, lfm3:1.7b | **2/2** | **14** | **35,398** | **14,949** | **12** | **0** | 0 crashes, 0 timeouts |

Total tokens: **50,347**, summing prompt and generation tokens across all requests. Counts cover unsuccessful/redundant reads as well as successful reads; fixture setup/oracle reads are outside episode-native-operation totals and preserved separately. `p3` took 29.78 seconds and `u3` 83.57 seconds. Time is descriptive, not a goal metric.

The final session's before/after oracle checks both passed with zero mismatches. All three sessions verified fixture cleanup with no remaining owned nodes. The first completed episode's post-oracle remains unavailable, as documented below. Both loaded-context snapshots identify the same model digest `b36a103fe2f8fbe9df2ceec88b9cfdf842dc04aaabe2b4677d1acf8e16570b5d` and context length 65536.

Historical same-cell comparison below uses original saved pilot traces, hash-verified and rescored offline with scorer v2, rather than fresh control runs. Historical counts and sources are in `HISTORICAL_COMPARISON.json`. A1 is the stock executor with the deconflicted A1 prompt, **not** the unmodified original ROSA prompt; no original-prompt S0 pilot result exists for these cells.

| Arm / provenance | Supported-complete / assigned cells | LLM requests | Input tokens | Output tokens |
|---|---:|---:|---:|---:|
| Historical A1, same tasks/seeds | 1/2 | 13 | 78,889 | 3,532 |
| Historical C1, same tasks/seeds | 1/2 | 12 | 32,095 | 5,074 |
| Forge smoke, this execution | 2/2 | 14 | 35,398 | 14,949 |

These two-cell totals do not rank the systems. In particular, reasoning-mode mismatch, different session, stochastic generation and small selected development sample prevent attribution of the correctness difference to Forge. Full-pilot four-model tables and 3–5 failure analyses require the later full run, which was explicitly not started.

## Hand-read traces

- **p3 disagreement:** Forge `smoke_20261115T084850Z-fixture-retry1/000-p3-Forge-s1/trace.jsonl` reads quartz.next_node at L7–10, beacon.next_node at L16–19, and juniper.setpoint at L25–28. The terminal call at L33 places the correct JSON inside `respond.message`, and L35 records the returned answer. Historical C1 `pilot/lfm3_1.7b-stage3/012-p3-C1-lfm3_1.7b-s1/trace.jsonl` L33 reports `first=quartz, second=beacon` despite the correct reads. Forge succeeds and historical C1 fails on this cell; the thinking difference prevents a method-level explanation.
- **u3 recovery and waste:** Forge `smoke_20261115T084850Z-remaining1/001-u3-Forge-s2/trace.jsonl` calls node_info with short `yarrow` at L33–37 and receives an unable-to-find result. It discovers the absolute name at L42–46, then reads yarrow at L51–55. A node-name search for `harbor` at L60–64 returns no nodes; topic_info at L69–73 obtains the upstream publisher, and quill node_info at L78–82 confirms it. L87 submits the correct JSON through `respond`; L89 records the answer. The result is supported, but the episode uses 10 requests versus historical C1's 7 on this cell. It does not establish an efficiency gain.

There are no unsupported Forge episodes in this two-attempt sample. No failure examples were invented to meet the full-run request for 3–5 failures. A returned error dictionary is ordinary tool output for the release; no additional C1 recovery rule was applied.

## Transport verification and remaining mismatch

`PilotOptionsClient` overrides **only `_build_options`**; inherited `OllamaClient.send` is unchanged. `TRANSPORT_CHECK.json` records a mock HTTP comparison: identical tool schemas, messages, parsed result and request fields except `options`. Each real `model_start` also stores both the actual and reconstructed released request, with `changed_fields=["options"]`. `SMOKE_AUDIT.json` independently checks every actual request, exact system messages, source stability and the returned thinking.

This proves the wrapper's narrow scope; it does **not** prove all pilot transport settings matched. I missed the distinction between configuring Forge `think=False` and sending Ollama `think:false`. Explicitly sending that false flag would change a transport field outside `options`; under the owner's general rule that is a transport correction, not a Forge-logic change. No correction or extra inference was performed after the two attempts. The report therefore does not mark the arm ready for a matched full comparison.

## Setup failures, recovery and evidence ownership

1. Initial session `smoke_20261115T084850Z` launched fixture `python3` from the minimal Forge environment. All 19 nodes exited because PyYAML was unavailable. Readiness failed, cleanup verified no remaining fixture nodes, and no model request ran. Corrected only fixture interpreter selection to the existing pilot `.venv/bin/python`; original logs/source snapshot retained.
2. Session `smoke_20261115T084850Z-fixture-retry1` passed its pre-oracle and ran `p3` once. Result logging then failed because a relative directory was passed to `Path.relative_to` with an absolute root. The raw answer/trace survived and cleanup succeeded. Fixed result-path resolution and recovered the same row offline. Its post-oracle was not executed because of that parent-process error; no after-state result is reconstructed.
3. Session `smoke_20261115T084850Z-remaining1` selects only the previously unattempted `u3`, with a new pre-oracle and after-oracle. Neither task's client, prompt, registry, callable dispatch or episode implementation changed across these two task attempts; an AST comparison records that in `SMOKE_AUDIT.json`. Exactly two model episodes ran, with zero replacements.

Raw evidence root: `research/_artifacts/runs/forge_baseline_20261115/`. Each session has frozen protocol/source hashes, copied driver, prompt files, plan, setup/worker logs and original outputs. Failed sessions remain alongside successful outputs. The initial [SETUP_STOP.md](SETUP_STOP.md) and `SETUP_PROVENANCE.json` remain historical records. No commits, pushes, merges, baseline edits or shared-infrastructure changes were made.

## Execution flow and reproduction

`run_smoke.py:prompts` obtains C1's prompt and performs the name substitution. `available_tools` selects the ordinary registry; `traced_callable` logs and calls each original tool function, allowing exceptions to reach Forge. `PilotOptionsClient._build_options` sets the approved options. `episode` constructs the released workflow, registers `respond`, attaches observational HTTP/message/compaction hooks and calls `WorkflowRunner.run`. `session` owns fixture/oracle/context/cleanup checks; `append_result` invokes the frozen scorer and appends the durable row. The `remaining` mode skips the already-completed first cell solely for recovery; it adds no model cells.

Commands were run with `uv run --no-project --python /tmp/rosa-forge-env-20261115/bin/python python research/studies/forge_baseline_20261115/run_smoke.py`, using modes `session` for the first two session directories and `remaining` for the last, with ROS_DOMAIN_ID=220, ROS_LOCALHOST_ONLY=1, ROS_HOME=/tmp/rosa-forge-ros-home, ROS_LOG_DIR=/tmp/rosa-forge-ros-logs and UV_CACHE_DIR=/tmp/rosa-forge-uv-cache. Source revision and package inventory are in provenance. Reproduction would be a new run, not authorized by this completed smoke.

## Exact system prompt and diff

The following blocks are the eight separate system messages sent to Forge, in order. The unchanged pilot task text follows as its own user message. `Workflow.system_prompt_template` is unused because the public initial-message API preserves the original boundaries.

System message 1:

```text
Your are ROSA (Robot Operating System Agent), an AI agent that can use ROS tools to answer questions about robotics systems. You have a subset of the ROS tools available to you, and you can use them to interact with the robotic system you are integrated with. Your responses should be grounded in real-time information whenever possible using the tools available to you.
```

System message 2:

```text
Use the task text and earlier tool results to decide which tool to call next; list entities only when you do not already know their names.
```

System message 3:

```text
Independent tool calls whose arguments are already known may be made together in one response.
```

System message 4:

```text
You may use rosparams to store information between interactions. However, if you are using rosparams to store your own memory, you must use the /rosa namespace to avoid conflicts with other ROS nodes. e.g. to store a value in the 'foo' parameter, use the key '/rosa/foo'.
```

System message 5:

```text
When providing a directory/path to a tool, you must always look for the correct path using your tools. When reading files, you must make sure that the file size is not too large to read. This is especially important when reading multiple files. A file is too large to read completely if its size is greater than 32KB. Avoid specifying a line range unless the user has requested it or the file is too large to read.
```

System message 6:

```text
You must use your math tools to perform calculations, especially for angles, distances, coordinates, and geometric computations. Failing to do this may result in incorrect commands or system failures. You must never perform calculations manually in your reasoning - always use the provided calculation tools to ensure accuracy. This is critical for robotics operations where precision matters.
```

System message 7:

```text
When you see <ROSA_INSTRUCTIONS> tags, you must follow the instructions inside of them. These instructions are instructions for how to use ROS tools to complete a task. You must follow these instructions IN ALL CASES. 
```

System message 8:

```text
When you have the answer, call the respond tool with the answer as a JSON object, using exactly the keys the task asks for. Do not write the answer as plain text.
```

The complete prompt diff is:

```diff
--- C1
+++ Forge
@@ -29,6 +29,6 @@
   ],
   [
     "system",
-    "When you have the answer, call the final_answer tool with the answer as a JSON object, using exactly the keys the task asks for. Do not write the answer as plain text."
+    "When you have the answer, call the respond tool with the answer as a JSON object, using exactly the keys the task asks for. Do not write the answer as plain text."
   ]
 ]
```
