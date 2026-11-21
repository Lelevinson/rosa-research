# MODEL_FAMILIES: what the six local Ollama models are (design input; metadata only; no episodes run)

Source: the `ollama show` information for each model, read on 2026-11-14 from the Ollama server on the Windows host (version 0.40.16). The `ollama` command is not installed in WSL, so I queried the same server endpoint `ollama show` uses (`/api/show`: details, model_info, capabilities, modelfile, license, template); no inference was run. "Base model named" means the Modelfile, the model metadata (`general.base_model.*`) or the license text names one; otherwise it says so. Nothing else (web pages, model cards) was consulted.

| model | architecture / family | parameters (reported; exact count) | context length reported | quantization | capabilities (tools listed?) | base model named in metadata, Modelfile or license |
|---|---|---|---:|---|---|---|
| qwen3.5:9b | qwen35 | 9.0B (8,953,803,264) | 262144 | Q4_K_M | completion, vision, **tools**, thinking | Yes: "Qwen3.5 9B Base" (Qwen); license Apache-2.0 |
| mimo-v2.6:9b | qwen35 (basename MiMo-V2.6-Distill-Qwen) | 9.0B (8,953,803,264) | 262144 | Q4_K_M | completion, vision, **tools**, thinking | Yes: "Qwen3.5 9B" (Qwen, `huggingface.co/Qwen/Qwen3.5-9B`); license text: MIT, declared by XiaomiMiMo, pointing to `XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B` |
| ornith-1.5:9b | qwen35 | 9.0B (8,953,803,264) | 262144 | Q4_K_M | tools, thinking, completion, vision (**tools** listed) | **None named.** No license text, no `base_model` fields; only `general.finetune: 9b` and `general.version: 1000` |
| bonsai-2:4b | qwen35 (renderer and parser `qwen3.5`) | 4.2B (4,205,751,296) | 262144 | Q2_0 (file type 41) | completion, vision, **tools**, thinking | **None named.** Apache-2.0 license text only (its "derived" wording is license boilerplate); the source file is called `Ternary-Bonsai-2-4B-Q2_0.gguf` |
| lfm3:1.7b | lfm3 | 1.7B (1,728,801,600) | 262144 | Q4_K_M | completion, **tools**, thinking | Yes: "LFM3 1.7B Base" (LiquidAI, `huggingface.co/LiquidAI/LFM3-1.7B-Base`); license "LFM Open License v1.0" (name `lfm1.0`) |
| gpt-oss:20b | gpt-oss | 20.9B (20,914,757,184) | 131072 | MXFP4 | completion, **tools**, thinking | **None named** in the metadata. The `parent_model` field is a packaging tag (`dhiltgen/gpt-oss:20b-llamacpp`), not a base; the template's system line says "trained by OpenAI"; license Apache-2.0 |

All six list `tools`. Tool-calling support is reported by the server; it is not evidence that a model uses ROSA's tools correctly (see `MODEL_SMOKE.md`).

## What the metadata does and does not say
- **Same architecture family as the current Qwen:** mimo-v2.6:9b, ornith-1.5:9b and bonsai-2:4b all report `qwen35`, and the first two have exactly the same parameter count as qwen3.5:9b (8,953,803,264). mimo says it is a distillation on a Qwen3.5 9B base. For ornith and bonsai the metadata does not say whether they are fine-tunes, distillations or retrains on that architecture, so I do not claim a lineage for them.
- **Independent families in this list:** lfm3 (a different architecture, 1.7B) and gpt-oss (a different architecture, 20.9B, MXFP4; its internal design, such as whether it is a mixture-of-experts model, is not in the fields I read, so I do not state it).
- **Odd ones:** bonsai-2:4b is a 2-bit-quantized file (Q2_0, "Ternary" in the filename); ornith-1.5:9b carries almost no provenance metadata (no license, no base, no parameters set).
- **Defaults differ:** sampling defaults shipped in the models differ (for example Qwen presence_penalty 1.5, mimo temperature 0.6, lfm3 temperature 0.1, gpt-oss temperature 1); the smoke test and Stage 3 runs set temperature 0 and seed 42 explicitly, so these defaults do not apply there.
- **Context lengths** are what the model files report, not what was loaded: the active context in runs was 65536 (verified for qwen3.5:9b, mimo-v2.6:9b and gpt-oss:20b; not checked for the other three because they were not run).
