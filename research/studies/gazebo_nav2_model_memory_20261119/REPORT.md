# Gazebo TurtleBot3 + Nav2 with each of the 4 models loaded: memory and failures

2026-11-19, Asia/Taipei, 11:06 finish (about 15 minutes). Diagnostic, no bars, no model quality measured; plan frozen in the docstring of [check.py](check.py) before the run; numbers in `results.json`, console in `run.log`. One stack at a time (headless Gazebo + Nav2 through `turtlebot3_nav2_smoke_20261116/stack.py`, ROS domain 219), GPU used by nothing else (RTX 4060 Laptop, 8,188 MiB; 15.6 GB RAM, 12 CPUs). Models loaded at num_ctx 65536 (the dev setting); one fixed ~4k-token prompt, 200 new tokens, temperature 0.

## Results (n = 1 per cell; a feasibility reading, not a benchmark)
| model | size / in VRAM (MiB) | GPU used: model alone | + stack | peak while decoding with stack and a navigation goal | decode tokens/s alone -> with stack + goal | goal | stack stop |
|---|---|---|---|---|---|---|---|
| lfm3:1.7b | 1,573 / 1,573 | 2,461 | 2,596 | 2,596 | 152.7 -> 143.8 | passed, 11.1 s | PASS, nothing left |
| bonsai-2:4b | 3,609 / 3,609 | 4,087 | 4,217 | 4,217 | 106.7 -> 88.2 | passed, 11.3 s | PASS |
| qwen3.5:9b | 8,340 / **5,375** | 6,383 | 6,512 | 6,512 | 12.1 -> 9.3 | passed, 12.4 s | PASS |
| gpt-oss:20b | 13,536 / **4,524** | 6,185 | 6,316 | 6,316 | 24.3 -> 16.2 | passed, 8.7 s | PASS |
- **Failures: none.** 4 of 4 navigation goals succeeded while the model decoded; 4 of 4 `stack.py stop` reported PASS with no owned process left; every model unloaded to 0 MiB; no Ollama error.
- **Memory:** the headless stack adds about 130 MiB of GPU memory; nothing came near the 8,188 MiB limit (largest: 6,512 MiB with qwen3.5). **qwen3.5:9b and gpt-oss:20b do not fit in VRAM** (5,375 of 8,340 and 4,524 of 13,536 MiB are resident; the rest runs from CPU RAM), which is why they are the slow models. Host RAM used with the stack 3.3 GB of 15.6 GB; load average about 4-5 on 12 CPUs.
- **Contention:** decode speed with Gazebo + Nav2 + a goal running was lower by 6% (lfm3), 17% (bonsai), 23% (qwen3.5) and 33% (gpt-oss) in this single measurement. This matters for any time limit on a Nav2 episode and for comparing episode times between machines. Prompt-processing speed is not reported: the repeated identical prompt hits Ollama's prompt cache, so those figures are not comparable.

## Limits
One run per model; Nav2 goal only (one 0.5 m goal), not a full episode with the model driving it; the Nav2 runner and the between-episode reset hook for the exam queue do not exist, so **cleanup between episodes was not tested here** (only start/stop cycles, 4 of them, all clean); `nvidia-smi` reports the whole GPU (baseline 0 MiB at start, so no other GPU user was present).

## Open search
- CPU-offloaded models: qwen3.5:9b (36% of its weights outside VRAM) and gpt-oss:20b (67% outside) at num_ctx 65536; the KV cache for 65,536 tokens is allocated at load, so the 8 GB card is already at 6.2-6.5 GB with the stack. A larger context or a second resident model would not fit (`results.json` A_loaded).
- Decode speed spread across the four models is 12.1 to 152.7 tokens/s; wall time of any queue is dominated by qwen3.5 and gpt-oss (consistent with the nudge run: gpt-oss 35 min and qwen3.5 31 min of 101 minutes of episode time).
- Headless Gazebo reads as GPU users in `/dev/dxg` (earlier smoke report); the measured stack footprint is 130 MiB, but CPU load rises to about 4-5.
