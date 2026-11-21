# Independent recount — 2026-11-14

**recount disagrees** with the literal written support screen; assembling ROS endpoint namespace/name pairs reproduces every reported headline total. No inference, API, fixture or previous scorer was used. All 72 raw traces were readable and complete. Current task definitions match both runs' frozen task files byte for byte.

| Arm / model | Reported supported | Literal recount supported | Reported excess/floor | Literal recount excess/floor | With endpoint FQN assembly |
|---|---:|---:|---|---|---|
| A1 Qwen | 24/24 | 23/24 | 47/96 (49.0%) | 47/92 (51.1%) | 24/24; 47/96 |
| A1 Luna | 23/24 | 20/24 | 13/91 (14.3%) | 13/80 (16.3%) | 23/24; 13/91 |
| A2 Qwen | 20/24 | 14/24 | 30/80 (37.5%) | 22/58 (37.9%) | 20/24; 30/80 |

The protocol says a `text` requirement needs its string in a successful result or task text. ROS topic-info results often contain `Node name: quill` and `Node namespace: /plant32` separately, rather than `/plant32/quill`. The literal screen rejects these; this is a protocol/specification discrepancy, **not evidence that correct FQN assembly is scientifically unsupported**. The separately labelled sensitivity permits only that assembly and changes nothing else.

Every additional literal support rejection (paths are episode directories under the two run roots in `INPUT_SHA256.json`):

- A1: `08-u3-ollama-r0`, `24-u3-openai-r1`: `/plant32/quill` absent literally; `12-u2-openai-r0`: `/plant32/yarrow` absent literally; `34-h3-openai-r1`: `/plant32/zephyr`, `/plant32/dune`, `/plant32/oasis` absent literally.
- A2: `00-h3-ollama-r0`, `19-h3-ollama-r1`: the same three hub publishers absent literally; `04-u3-ollama-r0`, `14-u3-ollama-r1`: `/plant32/quill` absent literally; `10-u2-ollama-r0`, `23-u2-ollama-r1`: `/plant32/yarrow` absent literally.
- A1 Luna `19-u4-openai-r0` fails under both readings: final `upstream_gain` is 28, declared 59; its successful gain read was from `/plant32/gantry`, not the required `/plant32/quill`.

| Arm/model/depth | Supported / all (literal) | Requests on supported | Excess/floor |
|---|---:|---:|---|
| A1 Qwen / 2 | 8/8 | 42 | 18/24 |
| A1 Qwen / 3 | 7/8 | 37 | 9/28 |
| A1 Qwen / 4 | 8/8 | 60 | 20/40 |
| A1 Luna / 2 | 7/8 | 24 | 3/21 |
| A1 Luna / 3 | 6/8 | 27 | 3/24 |
| A1 Luna / 4 | 7/8 | 42 | 7/35 |
| A2 Qwen / 2 | 4/8 | 14 | 2/12 |
| A2 Qwen / 3 | 4/8 | 18 | 2/16 |
| A2 Qwen / 4 | 6/8 | 48 | 18/30 |

Repeat definition: count a model request once if it issues any identical tool name and parsed arguments whose earlier-request result succeeded; dict key order ignored, list order preserved; subset calls and failures do not qualify. All episodes: A1 Qwen **18**, A2 Qwen **20**. On the reported supported cohort (endpoint-assembly sensitivity): **18 and 18**, beside the reported labeller's **22 and 22**. On the literal supported cohorts: **18 and 10**. A1 Luna: 0 under either cohort. Gap: the strict duplicate definition excludes broader redundancy such as subset reads and unnecessary parameter listing; the old request labels were not inspected, so attribution of the four-request gaps is not independently established.

Four specified A2 failures, observed without causal speculation (line numbers refer to each `trace.jsonl`):

- `08-v2-ollama-r0`: lines 17–19 attempt `ros2_service_call` with dict `request={}`; schema requires a string; tool error, no answer, no native service-call execution.
- `20-v2-ollama-r1`: lines 17–19 show the same dict-request validation failure and no answer.
- `03-p4-ollama-r0`: line 40 final setpoint 694, declared 873; lines 29–38 read/re-read `/plant32/beacon`'s setpoint, not `/plant32/juniper`'s.
- `22-p4-ollama-r1`: final setpoint 694, declared 873 (line 41); lines 29–38 read/re-read `/plant32/beacon`'s setpoint, not required `/plant32/juniper`'s.

Reproduction: `UV_CACHE_DIR=/tmp/rosa-recount-uv-cache uv run --no-sync python research/studies/independent_check_20261114/recount.py`. `main()` reads only protocol task definitions and raw traces, `recount()` scores and links support/repeats to trace lines, then aggregates by arm/model/depth. `endpoint_sensitivity.py` independently adds only endpoint-name assembly. Outputs use exclusive creation; preserve existing output and select new names for another recount. `episode_recount.json`, `aggregate_recount.json`, and `INPUT_SHA256.json` contain all per-episode counts, verdicts, evidence references and input hashes. Offline checks: 48+24 episodes, one start/end each, prompt/task arm and floor consistency, task-text equality, and balanced tool callbacks passed. These checks validate recount integrity, not historical live-fixture truth or generalization.

Independence limitation: the same batched tool call that first retrieved the requested addendum also opened `design_inputs/REPEAT_RATE_MODELS.md`, which the addendum forbids; that restriction was not known when the call was issued. Its existing repeat-count claims were therefore seen before this implementation; repeat-count blinding was compromised. Further restricted reading stopped once the restriction became known. No earlier scorer, labels, Stage 3c/3d label files or proposed method specification was opened. Required context summaries and the explicitly allowed A2 protocol expose historical results and ordinary prompt wording. This is an independently implemented recount, not a blind review. No claim of novelty or algorithm selection.

Part 1 completed before Part 2. Existing files and mirrors remain untouched; no commit/push/merge.
