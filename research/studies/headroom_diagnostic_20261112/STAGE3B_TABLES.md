# Stage 3b tables (arm A1 vs the Stage 3 arm A0; supported-complete episodes; denominators stated)

## Table 1. Per depth and model

| model | depth | floor | A0 supported | A0 excess / floor sum | A0 share | A1 supported | A1 requests per supported episode | A1 excess / floor sum | A1 share |
|---|---:|---:|---:|---|---:|---:|---|---|---:|
| Qwen | 2 | 3 | 8/8 | 40 / 24 | 166.7% | 8/8 | [3, 3, 5, 5, 6, 6, 7, 7] | 18 / 24 | 75.0% |
| Qwen | 3 | 4 | 8/8 | 16 / 32 | 50.0% | 8/8 | [4, 4, 4, 5, 5, 6, 6, 7] | 9 / 32 | 28.1% |
| Qwen | 4 | 5 | 8/8 | 26 / 40 | 65.0% | 8/8 | [5, 5, 7, 7, 7, 8, 8, 13] | 20 / 40 | 50.0% |
| Qwen | **all** |  | 24/24 | 82 / 96 | 85.4% | 24/24 |  | 47 / 96 | 49.0% |
| Luna | 2 | 3 | 8/8 | 10 / 24 | 41.7% | 8/8 | [3, 3, 3, 3, 3, 4, 4, 4] | 3 / 24 | 12.5% |
| Luna | 3 | 4 | 8/8 | 7 / 32 | 21.9% | 8/8 | [4, 4, 4, 4, 4, 5, 5, 5] | 3 / 32 | 9.4% |
| Luna | 4 | 5 | 7/8 | 6 / 35 | 17.1% | 7/8 | [5, 5, 6, 6, 6, 7, 7] | 7 / 35 | 20.0% |
| Luna | **all** |  | 23/24 | 23 / 91 | 25.3% | 23/24 |  | 13 / 91 | 14.3% |

## Table 2. Per template (A1; A0 beside)

| model | template | A0 excess / floor | A0 share | A1 supported | A1 excess / floor | A1 share |
|---|---|---|---:|---:|---|---:|
| Qwen | upstream | 18 / 24 | 75.0% | 6 | 21 / 24 | 87.5% |
| Qwen | pointer | 6 / 24 | 25.0% | 6 | 0 / 24 | 0.0% |
| Qwen | hub | 14 / 24 | 58.3% | 6 | 12 / 24 | 50.0% |
| Qwen | service | 44 / 24 | 183.3% | 6 | 14 / 24 | 58.3% |
| Luna | upstream | 5 / 19 | 26.3% | 5 | 2 / 19 | 10.5% |
| Luna | pointer | 1 / 24 | 4.2% | 6 | 0 / 24 | 0.0% |
| Luna | hub | 9 / 24 | 37.5% | 6 | 5 / 24 | 20.8% |
| Luna | service | 8 / 24 | 33.3% | 6 | 6 / 24 | 25.0% |

## Table 3. A0 versus A1 paired by task, repeat and model (pairs where both are supported-complete)

| model | pairs | mean requests A0 - A1 | range | A1 fewer / equal / A1 more | supported-complete A0 -> A1 |
|---|---:|---:|---|---|---|
| Qwen | 24 | 1.46 | -3 to 13 | 12 / 9 / 3 | 24 -> 24 |
| Luna | 23 | 0.43 | -1 to 2 | 11 / 9 / 3 | 23 -> 23 |

## Table 4. Remaining excess by kind (supported episodes with excess > 0; label counts per request, not capped)

| model | arm | excess requests | RED (repeats) | REC (recovery after short names) | LATE (late stage calls) | NOARG (extra calls, args in task) | EXPLORE | avoidable share (capped per episode) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen | A0 | 82 | 50 | 8 | 18 | 2 | 4 | 95% |
| Qwen | A1 | 47 | 22 | 11 | 10 | 0 | 4 | 91% |
| Luna | A0 | 23 | 1 | 0 | 14 | 9 | 0 | 100% |
| Luna | A1 | 13 | 2 | 1 | 10 | 0 | 0 | 100% |

## Table 5. First request is a listing although the entity is named (non-service tasks, supported episodes)

| model | A0 | A1 |
|---|---|---|
| Qwen | 8 / 18 | 0 / 18 |
| Luna | 12 / 17 | 5 / 17 |

## Table 6. Largest excess episodes under A1 (trace lines are `model_end` lines)

| model | episode | task | requests / floor | label sequence | trace |
|---|---|---|---|---|---|
| Qwen | 46-u4-ollama-r1 | u4 | 13 / 5 | R2:NEEDED R3:NEEDED R4:EXPLORE R5:RED R6:NEEDED R7:EXPLORE R8:RED R9:RED R10:RED R11:RED R12:RED R13:FIN | stage3b_20261113T155721Z/46-u4-ollama-r1/trace.jsonl (lines 10..76) |
| Qwen | 22-u2-ollama-r0 | u2 | 7 / 3 | R2:NEEDED R3:REC R4:REC R5:RED R6:RED R7:FIN | stage3b_20261113T155721Z/22-u2-ollama-r0/trace.jsonl (lines 10..40) |
| Qwen | 38-u2-ollama-r1 | u2 | 7 / 3 | R2:NEEDED R3:REC R4:REC R5:RED R6:RED R7:FIN | stage3b_20261113T155721Z/38-u2-ollama-r1/trace.jsonl (lines 10..40) |
| Qwen | 11-v4-ollama-r0 | v4 | 8 / 5 | R2:LATE R3:NEEDED R4:LATE R5:LATE R6:NEEDED R7:NEEDED R8:FIN | stage3b_20261113T155721Z/11-v4-ollama-r0/trace.jsonl (lines 10..70) |
| Luna | 01-h4-openai-r0 | h4 | 7 / 5 | R2:LATE R3:NEEDED R4:NEEDED R5:RED R6:NEEDED R7:FIN | stage3b_20261113T155721Z/01-h4-openai-r0/trace.jsonl (lines 12..71) |
| Luna | 41-h4-openai-r1 | h4 | 7 / 5 | R2:LATE R3:NEEDED R4:NEEDED R5:REC R6:NEEDED R7:FIN | stage3b_20261113T155721Z/41-h4-openai-r1/trace.jsonl (lines 12..79) |
| Luna | 00-v3-openai-r0 | v3 | 5 / 4 | R2:LATE R3:NEEDED R4:NEEDED R5:FIN | stage3b_20261113T155721Z/00-v3-openai-r0/trace.jsonl (lines 12..73) |
| Luna | 07-v4-openai-r0 | v4 | 6 / 5 | R2:LATE R3:NEEDED R4:NEEDED R5:NEEDED R6:FIN | stage3b_20261113T155721Z/07-v4-openai-r0/trace.jsonl (lines 12..76) |

## Failures read by hand (A1)

- 19-u4-openai-r0: exact=False, issues ['/upstream_gain: 28 != 59'], missing ['param /plant32/quill gain=59 not read'], requests 12 / floor 5.

## Costs and behaviour (all 48 episodes per arm)

| model | arm | requests | input tokens | native ops | native failures | seconds | multi-call requests |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen | A0 | 178 | 1,261,844 | 274 | 6 | 1683 | 10 |
| Qwen | A1 | 143 | 975,552 | 231 | 7 | 1607 | 4 |
| Luna | A0 | 124 | 632,987 | 306 | 0 | 668 | 16 |
| Luna | A1 | 116 | 518,117 | 241 | 3 | 674 | 12 |

## Sensitivity (not part of the frozen rule)

- Qwen A1 with every episode that has 10 or more RED requests removed (0 episode(s): []): 49.0% (47 / 96).
- Luna A1 excess is 13 over a floor sum of 91: one request more would give 15.4% (threshold for the closing rule 15%, for room 25%).

## Frozen decision rules applied

- A0 (Stage 3): Luna 25.3% (23/91), Qwen 85.4% (82/96).
- A1: supported-complete Qwen 24/24, Luna 23/24; both interpretable: True. Mean excess share: Qwen 49.0% (47/96), Luna 14.3% (13/91).
- 1. closes (Luna < 15% and Qwen < 25%): no. 2. Luna >= 25%: no. 3. Luna < 25% and Qwen >= 40%: yes.
- **Branch: WEAK-MODEL ROOM REMAINS.**
