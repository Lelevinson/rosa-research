# MODEL_SMOKE: do mimo-v2.6:9b and gpt-oss:20b work with ROSA? (design input, not a stage; 4 episodes, no decision rule)

Run: `research/_artifacts/runs/headroom_diagnostic_20261112/design_smoke_20261114T080333Z` (hash manifest `MANIFEST_DESIGN_SMOKE.sha256.json`; harness `design_inputs/run_smoke.py`). Local Ollama only (version 0.40.16, Windows host), no API key. Arm A1 (prompt hash identical to Stage 3b), Stage 3 fixture on ROS domain 217, observation-only guard, settings as Stage 3b for Qwen (temperature 0, seed 42, `num_ctx` 65536, `num_predict` 4096, 40 iterations, `reasoning=False`), nothing tuned per model. Oracle matched before and after, cleanup verified empty, no study error. One episode per model per task: **n = 1 per cell, so this shows whether the model works at all, not how well.**

## Offline capability check (`/api/show`)
| model | architecture / size / quantisation | capabilities reported | context length reported | active context (`/api/ps`, after first episode) | share in GPU memory |
|---|---|---|---|---|---|
| mimo-v2.6:9b | qwen35 (MiMo-V2.6-Distill-Qwen), 9.0B, Q4_K_M | completion, vision, tools, thinking | 262144 | 65536 | 5.6 of 8.7 GB |
| gpt-oss:20b | gpt-oss, 20.9B, MXFP4 | completion, tools, thinking | 131072 | 65536 | 4.7 of 14.2 GB |

## Episodes
| model | task | tool calls parse | requests | floor | supported-complete | harness error | several calls in one request | seconds | output tokens |
|---|---|---|---:|---:|---|---|---|---:|---:|
| mimo-v2.6:9b | p3 | yes | 3 | 4 | **no** (answered `setpoint` 694; the required node's setpoint is 873) | none | yes (request 2: `next_node` and `setpoint` of the same node) | 35 | 135 |
| mimo-v2.6:9b | u3 | yes | 4 | 4 | yes | none | yes (request 1: `topic_info` and `node_list`) | 14 | 134 |
| gpt-oss:20b | p3 | yes | 4 | 4 | yes | none | no (one call per request) | 95 | 373 |
| gpt-oss:20b | u3 | yes | 2 | 4 | **no** (no answer) | **yes**: `ros2_node_list` called with `blacklist: ''` (a string, the tool wants a list); schema validation raised and ended the episode | no | 27 | 661 |

## Notes from reading the traces
- mimo p3: after reading `quartz`'s `next_node` it asked for `beacon`'s `next_node` and `beacon`'s `setpoint` in one request, then answered with beacon's setpoint (694) instead of reading the last node's (`juniper`, 873). Its request count (3) is below the floor (4) because the answer was guessed, not derived. This is a wrong-node `setpoint` read, the same wrong value Qwen gave under A2 on p4; it is a different model from the same distilled family, so this is not independent evidence.
- mimo's architecture is `qwen35` at the same size and quantisation as `qwen3.5:9b`; it is a distillation on that base, so it is not an independent model family for generalisation claims.
- gpt-oss u3: the crash is a harness-level outcome: an invalid tool argument raises and aborts the whole episode (the same class as Qwen's A2 `ros2_service_call` dict argument). Under the Stage 3 rules a model failure is never rerun, so such an episode would count as a loss.
- gpt-oss reasoning: `reasoning=False` was accepted without an error, and no reasoning text appears in the saved messages, but its output tokens (373 and 661 over 4 and 2 short requests) exceed the visible text, so it probably still reasons internally; this was not measured further.
- gpt-oss is mostly in CPU memory (4.7 of 14.2 GB on the GPU) and was the slowest (95 s for p3, partly model load); mimo loaded 5.6 of 8.7 GB on the GPU.

## Verdicts (n = 1 per cell; nothing tuned)
- **mimo-v2.6:9b: usable with caveat.** Tool calls parse, the harness ran cleanly, and it batches independent calls without being told more than A1 says. Caveat: it speculated across a dependency on p3 and gave a wrong value (1 of 2 supported), and it is a distillation of the Qwen base already in use, so it adds little independence.
- **gpt-oss:20b: usable with caveat.** Tool calls parse and p3 was answered correctly at the floor with one call per request. Caveat: u3 aborted on a schema-invalid argument (blank string for a list), it is slow with 65536 context on this host, and reasoning could not be fully switched off; a main evaluation needs a decision about how aborts are counted before it starts.
