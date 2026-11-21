# Stage 3 tables (arm A0; 48 main episodes; pilot reported separately)

## Table 1. Per depth and model (supported-complete episodes only; denominators stated)

| model | depth | floor | episodes | supported-complete | requests per supported episode | excess (sum / floor sum) | excess share |
|---|---:|---:|---:|---:|---|---|---:|
| Qwen (qwen3.5:9b) | 2 | 3 | 8 | 8 | [4, 4, 4, 4, 5, 5, 19, 19] | 40 / 24 | 166.7% |
| Qwen (qwen3.5:9b) | 3 | 4 | 8 | 8 | [4, 4, 6, 6, 7, 7, 7, 7] | 16 / 32 | 50.0% |
| Qwen (qwen3.5:9b) | 4 | 5 | 8 | 8 | [7, 7, 8, 8, 8, 8, 10, 10] | 26 / 40 | 65.0% |
| **Qwen (qwen3.5:9b) all** | | | 24 | 24 | | 82 / 96 | **85.4%** |
| Luna (gpt-6-luna) | 2 | 3 | 8 | 8 | [3, 4, 4, 4, 4, 5, 5, 5] | 10 / 24 | 41.7% |
| Luna (gpt-6-luna) | 3 | 4 | 8 | 8 | [4, 4, 4, 4, 5, 6, 6, 6] | 7 / 32 | 21.9% |
| Luna (gpt-6-luna) | 4 | 5 | 8 | 7 | [5, 5, 6, 6, 6, 6, 7] | 6 / 35 | 17.1% |
| **Luna (gpt-6-luna) all** | | | 24 | 23 | | 23 / 91 | **25.3%** |

## Table 2. Per template and model (supported-complete)

| model | template | episodes | supported | excess / floor sum | share |
|---|---|---:|---:|---|---:|
| Qwen (qwen3.5:9b) | upstream | 6 | 6 | 18 / 24 | 75.0% |
| Qwen (qwen3.5:9b) | pointer | 6 | 6 | 6 / 24 | 25.0% |
| Qwen (qwen3.5:9b) | hub | 6 | 6 | 14 / 24 | 58.3% |
| Qwen (qwen3.5:9b) | service | 6 | 6 | 44 / 24 | 183.3% |
| Luna (gpt-6-luna) | upstream | 6 | 5 | 5 / 19 | 26.3% |
| Luna (gpt-6-luna) | pointer | 6 | 6 | 1 / 24 | 4.2% |
| Luna (gpt-6-luna) | hub | 6 | 6 | 9 / 24 | 37.5% |
| Luna (gpt-6-luna) | service | 6 | 6 | 8 / 24 | 33.3% |

## Table 3. Relabelled excess (supported-complete episodes with excess > 0)

Avoidable = RED + REC + LATE (stage already started, or stage-1 call issued after the first request) + NOARG (call outside the plan whose arguments are in the task text or absent). Per episode min(avoidable, excess) is used. Exploration = unneeded calls outside the plan whose arguments needed an earlier result (codebook JUDG); needed = the first request of each next dependency stage.

| model | excess requests | avoidable (frozen definition) | share | exploration (extra) | share avoidable + exploration | mostly avoidable (>50%)? |
|---|---:|---:|---:|---:|---:|---|
| Qwen (qwen3.5:9b) | 82 | 78 | 95% | 4 | 100% | yes |
| Luna (gpt-6-luna) | 23 | 23 | 100% | 0 | 100% | yes |

## Table 4. Largest excess episodes (trace lines are `model_end` lines)

| model | episode | task | requests / floor | label sequence (requests 2..n) | trace file |
|---|---|---|---|---|---|
| Qwen (qwen3.5:9b) | 20-v2-ollama-r0 | v2 | 19 / 3 | R2:RED R3:RED R4:RED R5:RED R6:RED R7:RED R8:RED R9:RED R10:RED R11:RED R12:RED R13:RED R14:RED R15:RED R16:RED R17:LATE R18:NEEDED R19:FIN | stage3_20261112T225309Z/20-v2-ollama-r0/trace.jsonl (lines 10..148) |
| Qwen (qwen3.5:9b) | 44-v2-ollama-r1 | v2 | 19 / 3 | R2:RED R3:RED R4:RED R5:RED R6:RED R7:RED R8:RED R9:RED R10:RED R11:RED R12:RED R13:RED R14:RED R15:RED R16:RED R17:LATE R18:NEEDED R19:FIN | stage3_20261112T225309Z/44-v2-ollama-r1/trace.jsonl (lines 10..148) |
| Qwen (qwen3.5:9b) | 17-u4-ollama-r0 | u4 | 10 / 5 | R2:LATE R3:NEEDED R4:NEEDED R5:EXPLORE R6:RED R7:NEEDED R8:RED R9:RED R10:FIN | stage3_20261112T225309Z/17-u4-ollama-r0/trace.jsonl (lines 10..58) |
| Qwen (qwen3.5:9b) | 47-u4-ollama-r1 | u4 | 10 / 5 | R2:LATE R3:NEEDED R4:NEEDED R5:EXPLORE R6:RED R7:NEEDED R8:RED R9:RED R10:FIN | stage3_20261112T225309Z/47-u4-ollama-r1/trace.jsonl (lines 10..58) |
| Qwen (qwen3.5:9b) | 09-v3-ollama-r0 | v3 | 7 / 4 | R2:LATE R3:NEEDED R4:LATE R5:LATE R6:NEEDED R7:FIN | stage3_20261112T225309Z/09-v3-ollama-r0/trace.jsonl (lines 10..64) |
| Luna (gpt-6-luna) | 16-v2-openai-r0 | v2 | 5 / 3 | R2:NOARG R3:LATE R4:NEEDED R5:FIN | stage3_20261112T225309Z/16-v2-openai-r0/trace.jsonl (lines 12..69) |
| Luna (gpt-6-luna) | 19-h3-openai-r0 | h3 | 6 / 4 | R2:NOARG R3:LATE R4:NEEDED R5:NEEDED R6:FIN | stage3_20261112T225309Z/19-h3-openai-r0/trace.jsonl (lines 12..48) |
| Luna (gpt-6-luna) | 27-h2-openai-r1 | h2 | 5 / 3 | R2:NOARG R3:LATE R4:NEEDED R5:FIN | stage3_20261112T225309Z/27-h2-openai-r1/trace.jsonl (lines 12..33) |
| Luna (gpt-6-luna) | 32-u4-openai-r1 | u4 | 7 / 5 | R2:LATE R3:NEEDED R4:NEEDED R5:RED R6:NEEDED R7:FIN | stage3_20261112T225309Z/32-u4-openai-r1/trace.jsonl (lines 16..51) |
| Luna (gpt-6-luna) | 37-v3-openai-r1 | v3 | 6 / 4 | R2:NOARG R3:LATE R4:NEEDED R5:NEEDED R6:FIN | stage3_20261112T225309Z/37-v3-openai-r1/trace.jsonl (lines 12..76) |

## Table 5. Costs and behaviour (all main episodes)

| model | requests | input tokens | output tokens | native ops | native failures | seconds | multi-call requests | capacity events |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Qwen (qwen3.5:9b) | 178 | 1,261,844 | 17,204 | 274 | 6 | 1683 | 10 | 0 |
| Luna (gpt-6-luna) | 124 | 632,987 | 5,846 | 306 | 0 | 668 | 16 | 0 |

## Failures read by hand

- 05-u4-openai-r0: exact=False, issues ['/upstream_gain: 28 != 59'], missing ['param /plant32/quill gain=59 not read'], requests 10 / floor 5.

## Pilot (4 Qwen episodes, reported separately, not in the 48)

- pilot-u2-ollama: requests 4 / floor 3, supported-complete True
- pilot-p3-ollama: requests 4 / floor 4, supported-complete True
- pilot-v4-ollama: requests 8 / floor 5, supported-complete True
- pilot-h3-ollama: requests 6 / floor 4, supported-complete True

## Sensitivity (not part of the frozen rule)

- Qwen without the two 15-repeat `v2` loop episodes (excess 16 each): 55.6% (50 / 90).
- Luna including its one failed episode (excess counted): 29.2%.
- Luna excess is 23 over a floor sum of 91: one request fewer would give 24.2% (threshold 25%); one more 26.4%.

## Frozen decision rules applied

- Supported-complete rates: Qwen 24/24 (100%), Luna 23/24 (96%); both interpretable (>= 50%) and >= 8 supported episodes: True.
- Mean excess share: Qwen 85.4%, Luna 25.3%.
- Clause 1 (Luna >= 25%): met; clause 2 (Qwen >= 40% while Luna < 25%): not met.
- Relabelled excess mostly avoidable (> 50%): Luna yes (23/23), Qwen yes (78/82).
- No room (both < 15%): no.
- **Branch: ROOM FOR A METHOD.**
