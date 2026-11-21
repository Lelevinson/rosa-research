# Per-request thinking toggle: feasibility (step 1), 2026-11-19

Measured with `think_probe.py` (this folder) on the Ollama host (`/api/chat`, `stream: false`, temperature 0.7, seed 1, one request per setting, `num_predict` 1500, same two-sentence prompt, no tool needed). **n = 1 per setting; this shows what the API accepts and returns, not average behaviour.** Models were unloaded afterwards (`/api/ps` empty). Installed client: `langchain-ollama 0.3.10`, `ollama 0.6.3`.

| model | `/api/show` capabilities | `think=false` | `think=true` | response separation | output tokens (false -> true) | per-request toggle |
|---|---|---|---|---|---|---|
| `lfm3:1.7b` | completion, tools, thinking | no thinking | thinking (1,281 chars) | `message.thinking` separate from `message.content`; no `<think>` in content | 45 -> 349 | **yes** |
| `qwen3.5:9b` | completion, vision, tools, thinking | no thinking | thinking (4,562 chars) | same | 51 -> 1,230 | **yes** |
| `bonsai-2:4b` | completion, vision, tools, thinking | no thinking | thinking (3,891 chars) | same | 39 -> 1,175 | **yes** |
| `gpt-oss:20b` | completion, tools, thinking | **still thinks** (783 chars, 227 tokens) | thinking = medium (1,079 chars, 297 tokens) | same | 227 -> 297; `"low"` 91 (179 chars), `"medium"` 297, `"high"` 725 (3,161 chars) | **levels only (low / medium / high); it cannot be turned off** |
Unset (`null`): lfm3, qwen3.5, bonsai think (the API default is thinking on); gpt-oss = medium. The harness passes `reasoning=False` everywhere (`run_pilot.py:49`), so for gpt-oss the existing "thinking off" arms are not off (see below).
- **Tool turn:** with a tool schema attached and `think=true`, all four answered in text (no tool call was needed by the prompt), thinking still separate; this does not test tool-call behaviour under thinking in a real loop.
- **Thinking tokens are not reported separately.** Ollama gives `eval_count` (thinking + answer together) and the `thinking` text; thinking tokens can only be estimated (for example `eval_count` minus the tokens of the visible content and tool call, or characters / 4). A study that reports "thinking tokens separately" must state it is an estimate.
- **Harness path:** `ChatOllama(reasoning=...)` accepts a bool or a string and the installed class documents a per-invoke `reasoning=` keyword (`chat_models.py` lines 464-470); the reasoning text arrives in `additional_kwargs["reasoning_content"]`. Whether the pilot agent loop can pass a different value on each request is not yet verified here (the arm's `visible_schemas` hook runs once per request and is the candidate place); to be tested in the protocol's smoke.
- **gpt-oss is already thinking in the saved runs (measured from traces, not from the probe):** in a FULL episode trace (`research/_artifacts/runs/repeat_finish_nudge_20261118/full_20261118/gpt-oss_20b-e1h/...FULL...s1`) one request that returned a single tool call and empty content cost 277 output tokens (`eval_count` 277) while `additional_kwargs` was empty, i.e. about 240 tokens of thinking that the trace does not store. Median output tokens per request in 4 FULL traces per model: gpt-oss 192.5, lfm3 186, qwen3.5 98.

## Result for step 2's gate
Per-request toggling exists for 3 of the 4 models as on/off (lfm3, qwen3.5, bonsai) and for gpt-oss as a level (cannot go below "low" / its default). The owner's gate ("at least 2 models support it") is met. The arm "thinking off" cannot be literally off for gpt-oss; the protocol must say so and define gpt-oss's base and escalated levels explicitly.

## Open search (not the target of this note)
- gpt-oss hidden thinking in every saved run: all gpt-oss episodes ran with `reasoning=False`, which Ollama does not honour for this model; their output-token totals include unrecorded thinking (the probe shows 227 tokens for a one-sentence answer with `false`). Example: `gpt-oss_20b-e1h/` FULL trace above; 80 gpt-oss episodes in the nudge run alone.
- Default-on thinking: any code path that leaves `reasoning` unset would make lfm3, qwen3.5 and bonsai think (output tokens 8-30x in the probe); the harness sets `False` at `run_pilot.py:49`, `run_stage1.py` uses `reasoning=False` at line 115; other runners were not audited.
- qwen3.5 with thinking took 34.8 s for the one-sentence prompt (vs 11.1 s without) in the probe: wall-time cost of an always-on arm will be dominated by qwen3.5 and gpt-oss "high".
