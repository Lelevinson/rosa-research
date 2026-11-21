# MODEL_CHECK (Step A), 2026-11-15

Run: `research/_artifacts/runs/small_model_harness_20261115/stepA/` (not tracked; compact copy of per-episode numbers below). 10 models, Stage 3 tasks p3 (floor 4) and u3 (floor 4), arm A1 (hash `7acbb0555cba...`), one episode per task per model (my reading of "two episodes each"), seed 1, temperature 0.7, num_ctx 65536 (verified from `/api/ps` for every model that loaded), num_predict 4096, max iterations 40, ROS domain 220, shuffle seed 20261201. Oracle matched before and after; fixture cleaned up. Scoring: Stage 3 strict support rule, answer = last complete JSON object (`pilot_score.py`). Two episodes per model say nothing about rates; verdicts only say whether a model can run through the harness.

`/api/show` facts are in `model_check/api_show.json`: all 10 models list `tools` in capabilities, **including granite4.2:8b**, so granite4.1 is not needed.

| model | arch / size | context | tools | p3 | u3 | verdict and why |
|---|---|---:|:-:|---|---|---|
| lfm3:1.7b | lfm3 1.7B | 262144 | yes | wrong (reports the start node as `first`), 5 req | supported, 7 req, 3664 output tokens | usable with caveat: answers are long prose ending in JSON (read only by the last-object rule); weak at chain tasks |
| bonsai-2:4b | qwen35 4.2B Q2_0 | 262144 | yes | **abort** (called `ros2_param_set` with a list, schema validation error ended the episode) | **abort** (called `ros2_service_call` with an object `request`) | usable with caveat: both failures are stock-executor aborts after it had gathered the facts, plus unrequested write-tool calls (blocked by the study guard before ROS) |
| nemotron-3-nano:4b | nemotron_h 4.0B | 262144 | yes | no answer: replied with the string `/plant32/quartz/next_node`, 0 tool calls | empty-string JSON, 0 tool calls | not usable: answers without calling any tool in 2 of 2 episodes (taxonomy row 14) |
| gemma4:e4b | gemma4 7.5B | 131072 | yes | supported, 5 req | stopped after 2 req with `input_topic: null` | usable with caveat: premature stop once |
| ministral-3:8b | mistral3 8.9B | 262144 | yes | **abort** at request 1 (`ros2_node_list` with `blacklist: {}`, validation error) | supported, 4 req (floor) | usable with caveat: stock abort on an invalid argument |
| granite4.2:8b | granite 8.8B | 131072 | **yes** | wrong (start node reported as `first`), 4 req | supported, 11 req (floor 4) | usable: tools present; wasteful on u3 |
| qwen3.5:9b | qwen35 9.0B | 262144 | yes | wrong (read the setpoint one hop early, 694), 3 req | supported, 7 req | usable |
| ornith-1.5:9b | qwen35 9.0B | 262144 | yes | supported, 4 req (floor) | supported, 4 req (floor) | usable |
| mimo-v2.6:9b | qwen35 9.0B | 262144 | yes | wrong (same early stop, 694), 3 req | supported, 4 req (floor) | usable |
| gpt-oss:20b | gpt-oss 20.9B MXFP4 | 131072 | yes | model error | model error | **not usable at present (host fault, not a model verdict)**: `llama-server process has terminated: exit status 0xc0000409 ... CUDA error: shared object initialization failed`, also for a 20-token prompt via `/api/generate`, at num_ctx 4096/16384/65536, with and without reasoning. It ran in earlier Stage 3-era smoke episodes (MODEL_SMOKE.md), so something changed on the Windows host (Ollama 0.40.16). I cannot repair the host; retry before Step D |

Supported-complete: 6 of 20 episodes overall under the strict rule, 0 of 4 for the two models that never loaded or never called a tool.

## Models added to the pilot besides lfm3:1.7b, qwen3.5:9b and gpt-oss:20b (my judgment)
- **bonsai-2:4b** added: both of its Step A failures were stock-executor aborts (argument validation on write tools), i.e. the harness-level failure class this study asks about; 4B and Q2_0 quantised, so it extends the size range downwards.
- ministral-3:8b not added: one abort and one floor-level success also qualifies, but the 10-hour wall-time cap does not allow a fifth model (see PILOT_LOG for the cost estimate). It is the first candidate if time remains.
- nemotron-3-nano:4b not added (answers without tools); granite, gemma, ornith, mimo not added (no S0-style-only failure pattern).
- gpt-oss:20b stays in the plan only if the host fault is gone before Step D.
