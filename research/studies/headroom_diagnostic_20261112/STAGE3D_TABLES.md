# Stage 3d tables (arm A2 vs A1; Qwen only; supported-complete episodes; denominators stated)

## Headline

- A2 Qwen: supported-complete **20/24** (A1 24/24); excess over the floor on supported episodes **30/80 = 37.5%** (A1 47/96 = 49.0%).
- Frozen rule: **rule 1: correctness first (fewer than 22 of 24 supported-complete); excess not interpretable; rule stops here**.
- The A2 share is computed over only the supported episodes and is descriptive here; with rule 1 firing it is not interpretable as a result for the sentences.

## Table 1. Per depth

| depth | floor | A1 supported | A1 excess / floor sum | A1 share | A2 supported | A2 excess / floor sum | A2 share |
|---|---:|---:|---|---:|---:|---|---:|
| 2 | 3 | 8/8 | 18 / 24 | 75.0% | 6/8 | 4 / 18 | 22.2% |
| 3 | 4 | 8/8 | 9 / 32 | 28.1% | 8/8 | 8 / 32 | 25.0% |
| 4 | 5 | 8/8 | 20 / 40 | 50.0% | 6/8 | 18 / 30 | 60.0% |
| **all** |  | 24/24 | 47 / 96 | 49.0% | 20/24 | 30 / 80 | 37.5% |

## Table 2. Per template

| template | A1 supported | A1 excess / floor | A1 share | A2 supported | A2 excess / floor | A2 share |
|---|---:|---|---:|---:|---|---:|
| upstream | 6/6 | 21 / 24 | 87.5% | 6/6 | 16 / 24 | 66.7% |
| pointer | 6/6 | 0 / 24 | 0.0% | 4/6 | 0 / 14 | 0.0% |
| hub | 6/6 | 12 / 24 | 50.0% | 6/6 | 8 / 24 | 33.3% |
| service | 6/6 | 14 / 24 | 58.3% | 4/6 | 6 / 18 | 33.3% |

## Table 3. A1 versus A2 paired by task and repeat (pairs where both arms are supported-complete)

Pairs: 20. Mean requests A1 - A2: 0.55; median 0.5; range -3 to 3; A2 fewer in 10, equal in 8, A2 more in 2.

| task | repeat | A1 requests | A2 requests | A1 - A2 |
|---|---:|---:|---:|---:|
| h2 | 0 | 5 | 4 | 1 |
| h2 | 1 | 5 | 4 | 1 |
| h3 | 0 | 6 | 5 | 1 |
| h3 | 1 | 6 | 5 | 1 |
| h4 | 0 | 7 | 7 | 0 |
| h4 | 1 | 7 | 7 | 0 |
| p2 | 0 | 3 | 3 | 0 |
| p2 | 1 | 3 | 3 | 0 |
| p3 | 0 | 4 | 4 | 0 |
| p3 | 1 | 4 | 4 | 0 |
| u2 | 0 | 7 | 4 | 3 |
| u2 | 1 | 7 | 4 | 3 |
| u3 | 0 | 4 | 6 | -2 |
| u3 | 1 | 7 | 6 | 1 |
| u4 | 0 | 7 | 10 | -3 |
| u4 | 1 | 13 | 10 | 3 |
| v3 | 0 | 5 | 5 | 0 |
| v3 | 1 | 5 | 5 | 0 |
| v4 | 0 | 8 | 7 | 1 |
| v4 | 1 | 8 | 7 | 1 |

Same 20 task-repeat cells (supported in both arms): A1 excess 41/80 = 51.2%, A2 30/80 = 37.5%. The four cells lost in A2 are v2 r0, v2 r1, p4 r0, p4 r1; A1 excess on those four cells was 6 over floor 16.

## Table 4. Request kinds in supported episodes with excess > 0 (labels per request, not capped; Stage 3 labeller)

| arm | excess requests (capped, = excess) | RED | REC | LATE | NOARG | EXPLORE |
|---|---:|---:|---:|---:|---:|---:|
| A1 | 47 | 22 | 11 | 10 | 0 | 4 |
| A2 | 30 | 22 | 0 | 4 | 0 | 4 |

(A2 label total may differ from the capped excess sum because failed episodes are excluded and labels are not capped per episode.)

## Table 5. Episodes not supported-complete in A2 (read by hand)

| episode | task | requests | exact | issues | support missing | error |
|---|---|---:|---|---|---|---|
| 03-p4-ollama-r0 | p4 | 5 | False | /setpoint: 694 != 873 | param /plant32/juniper setpoint=873 not read | None |
| 08-v2-ollama-r0 | v2 | 3 | False | : expected object |  | 1 validation error for ros2_service_call request   Input should be a v |
| 20-v2-ollama-r1 | v2 | 3 | False | : expected object |  | 1 validation error for ros2_service_call request   Input should be a v |
| 22-p4-ollama-r1 | p4 | 5 | False | /setpoint: 694 != 873 | param /plant32/juniper setpoint=873 not read | None |

## Table 6. Every A2 episode

| episode | task | floor | requests | excess | supported-complete | calls per request |
|---|---|---:|---:|---:|---|---|
| 00-h3-ollama-r0 | h3 | 4 | 5 | 1 | True | [1, 1, 1, 1, 0] |
| 01-v3-ollama-r0 | v3 | 4 | 5 | 1 | True | [1, 1, 1, 1, 0] |
| 02-p3-ollama-r0 | p3 | 4 | 4 | 0 | True | [1, 1, 1, 0] |
| 03-p4-ollama-r0 | p4 | 5 | 5 | 0 | False | [2, 2, 2, 1, 0] |
| 04-u3-ollama-r0 | u3 | 4 | 6 | 2 | True | [1, 1, 1, 1, 1, 0] |
| 05-h2-ollama-r0 | h2 | 3 | 4 | 1 | True | [1, 1, 1, 0] |
| 06-v4-ollama-r0 | v4 | 5 | 7 | 2 | True | [1, 1, 1, 1, 1, 1, 0] |
| 07-h4-ollama-r0 | h4 | 5 | 7 | 2 | True | [1, 1, 1, 3, 3, 3, 0] |
| 08-v2-ollama-r0 | v2 | 3 | 3 | 0 | False | [1, 1, 1] |
| 09-p2-ollama-r0 | p2 | 3 | 3 | 0 | True | [1, 1, 0] |
| 10-u2-ollama-r0 | u2 | 3 | 4 | 1 | True | [1, 1, 1, 0] |
| 11-u4-ollama-r0 | u4 | 5 | 10 | 5 | True | [1, 1, 1, 1, 1, 1, 1, 1, 1, 0] |
| 12-u4-ollama-r1 | u4 | 5 | 10 | 5 | True | [1, 1, 1, 1, 1, 1, 1, 1, 1, 0] |
| 13-h2-ollama-r1 | h2 | 3 | 4 | 1 | True | [1, 1, 1, 0] |
| 14-u3-ollama-r1 | u3 | 4 | 6 | 2 | True | [1, 1, 1, 1, 1, 0] |
| 15-p2-ollama-r1 | p2 | 3 | 3 | 0 | True | [1, 1, 0] |
| 16-h4-ollama-r1 | h4 | 5 | 7 | 2 | True | [1, 1, 1, 3, 3, 3, 0] |
| 17-v4-ollama-r1 | v4 | 5 | 7 | 2 | True | [1, 1, 1, 1, 1, 1, 0] |
| 18-v3-ollama-r1 | v3 | 4 | 5 | 1 | True | [1, 1, 1, 1, 0] |
| 19-h3-ollama-r1 | h3 | 4 | 5 | 1 | True | [1, 1, 1, 1, 0] |
| 20-v2-ollama-r1 | v2 | 3 | 3 | 0 | False | [1, 1, 1] |
| 21-p3-ollama-r1 | p3 | 4 | 4 | 0 | True | [1, 1, 1, 0] |
| 22-p4-ollama-r1 | p4 | 5 | 5 | 0 | False | [2, 2, 2, 1, 0] |
| 23-u2-ollama-r1 | u2 | 3 | 4 | 1 | True | [1, 1, 1, 0] |
