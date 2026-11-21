## Stage 1a: A_orig vs A0 (qwen3.5:9b, 6 tasks x 2 repeats)

Oracle stable across snapshots: True. Supported-complete = exact fields AND support screen.

| arm | episodes | supported-complete | requests (all) | requests / supported ep | excess over floor (supported eps) | multi-call requests | max calls in one request | input tokens | output tokens | native ops | episode seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_orig | 12 | 9 | 74 | 6.56 | 31 over floor 28 | 0 | 1 | 511,985 | 8,162 | 68 | 806 |
| A0 | 12 | 10 | 63 | 5.10 | 19 over floor 32 | 18 | 4 | 424,475 | 7,403 | 85 | 766 |

### Matched pairs where both arms are supported-complete

| task | repeat | A_orig requests | A0 requests | A_orig - A0 |
|---|---:|---:|---:|---:|
| d1 | 0 | 6 | 6 | 0 |
| d1 | 1 | 6 | 6 | 0 |
| t1 | 1 | 9 | 5 | 4 |
| t2 | 0 | 6 | 6 | 0 |
| t2 | 1 | 7 | 6 | 1 |
| t3 | 0 | 3 | 3 | 0 |
| t3 | 1 | 4 | 3 | 1 |
| x1 | 0 | 9 | 5 | 4 |
| x1 | 1 | 9 | 5 | 4 |

Pairs: 9; mean saving 1.56; median 1; range 0 to 4; A0 fewer in 5, equal in 4, more in 0.

### Episodes not supported-complete (read these by hand)

| episode | exact | support missing | issues | requests | error |
|---|---|---|---|---:|---|
| 05-t1-A_orig-r0 | False | /rgb/0: background_r not read; /rgb/1: background_g not read; /rgb/2: background_b not read | /rgb/0: 255 != 37; /rgb/1: 255 != 83; /rgb/2: 255 != 129 | 5 | None |
| 07-d2-A0-r0 | False |  | /services//diag_demo/calculator/get_type_description: missing | 5 | None |
| 10-d2-A_orig-r0 | False |  | /services//diag_demo/calculator/get_type_description: missing | 5 | None |
| 20-d2-A0-r1 | False |  | /services//diag_demo/calculator/get_type_description: missing | 7 | None |
| 22-d2-A_orig-r1 | False |  | /services//diag_demo/calculator/get_type_description: missing | 5 | None |

### Every episode

| episode | arm | requests | floor | calls per request | supported-complete | native ops | seconds |
|---|---|---:|---:|---|---|---:|---:|
| 00-t2-A_orig-r0 | A_orig | 6 | 3 | [1, 1, 1, 1, 1, 0] | True | 4 | 61 |
| 01-t3-A0-r0 | A0 | 3 | 3 | [2, 1, 0] | True | 3 | 42 |
| 02-x1-A_orig-r0 | A_orig | 9 | 3 | [1, 1, 1, 1, 1, 1, 1, 1, 0] | True | 11 | 99 |
| 03-d1-A0-r0 | A0 | 6 | 3 | [1, 2, 1, 2, 1, 0] | True | 7 | 74 |
| 04-t1-A0-r0 | A0 | 6 | 4 | [2, 2, 1, 3, 1, 0] | True | 10 | 73 |
| 05-t1-A_orig-r0 | A_orig | 5 | 4 | [1, 1, 1, 1, 0] | False | 5 | 68 |
| 06-t3-A_orig-r0 | A_orig | 3 | 3 | [1, 1, 0] | True | 2 | 56 |
| 07-d2-A0-r0 | A0 | 5 | 4 | [1, 1, 1, 1, 0] | False | 6 | 44 |
| 08-d1-A_orig-r0 | A_orig | 6 | 3 | [1, 1, 1, 1, 1, 0] | True | 6 | 66 |
| 09-x1-A0-r0 | A0 | 5 | 3 | [2, 2, 4, 1, 0] | True | 12 | 101 |
| 10-d2-A_orig-r0 | A_orig | 5 | 4 | [1, 1, 1, 1, 0] | False | 4 | 74 |
| 11-t2-A0-r0 | A0 | 6 | 3 | [1, 1, 1, 1, 1, 0] | True | 4 | 55 |
| 12-t1-A0-r1 | A0 | 5 | 4 | [2, 2, 1, 3, 0] | True | 10 | 66 |
| 13-t3-A0-r1 | A0 | 3 | 3 | [2, 1, 0] | True | 3 | 35 |
| 14-t3-A_orig-r1 | A_orig | 4 | 3 | [1, 1, 1, 0] | True | 2 | 57 |
| 15-t2-A_orig-r1 | A_orig | 7 | 3 | [1, 1, 1, 1, 1, 1, 0] | True | 6 | 59 |
| 16-t1-A_orig-r1 | A_orig | 9 | 4 | [1, 1, 1, 1, 1, 1, 1, 1, 0] | True | 7 | 63 |
| 17-d1-A_orig-r1 | A_orig | 6 | 3 | [1, 1, 1, 1, 1, 0] | True | 6 | 56 |
| 18-x1-A_orig-r1 | A_orig | 9 | 3 | [1, 1, 1, 1, 1, 1, 1, 1, 0] | True | 11 | 73 |
| 19-x1-A0-r1 | A0 | 5 | 3 | [2, 2, 4, 1, 0] | True | 12 | 96 |
| 20-d2-A0-r1 | A0 | 7 | 4 | [1, 1, 1, 1, 1, 1, 0] | False | 7 | 58 |
| 21-t2-A0-r1 | A0 | 6 | 3 | [1, 1, 1, 1, 1, 0] | True | 4 | 49 |
| 22-d2-A_orig-r1 | A_orig | 5 | 4 | [1, 1, 1, 1, 0] | False | 4 | 73 |
| 23-d1-A0-r1 | A0 | 6 | 3 | [1, 2, 1, 2, 1, 0] | True | 7 | 73 |

## Stage 1b: width probe (A0 only, floor = 3 requests at every N)

| provider | N | episode | value coverage supported / N | `clocks` key present | requests | calls per request | all N in one request | input tokens | output tokens | native ops | native failures | native timeouts | seconds | capacity events |
|---|---:|---|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| ollama | 4 | pilot | 4/4 | True | 4 | [1, 4, 1, 0] | True | 24,477 | 493 | 6 | 0 | 0 | 53 | - |
| ollama | 4 | r0 | 4/4 | True | 4 | [1, 4, 1, 0] | True | 24,477 | 493 | 6 | 0 | 0 | 52 | - |
| ollama | 4 | r1 | 4/4 | True | 4 | [1, 4, 1, 0] | True | 24,477 | 493 | 6 | 0 | 0 | 51 | - |
| ollama | 8 | r0 | 8/8 | True | 4 | [1, 8, 1, 0] | True | 25,099 | 818 | 10 | 0 | 0 | 84 | - |
| ollama | 8 | r1 | 8/8 | True | 4 | [1, 8, 1, 0] | True | 25,099 | 818 | 10 | 0 | 0 | 89 | - |
| ollama | 16 | r0 | 16/16 | True | 4 | [1, 16, 1, 0] | True | 26,373 | 1,400 | 17 | 0 | 0 | 159 | - |
| ollama | 16 | r1 | 16/16 | True | 4 | [1, 16, 1, 0] | True | 26,373 | 1,400 | 17 | 0 | 0 | 155 | - |
| ollama | 32 | r0 | 32/32 | False | 4 | [1, 32, 1, 0] | True | 28,942 | 2,411 | 34 | 0 | 0 | 297 | - |
| ollama | 32 | r1 | 32/32 | False | 4 | [1, 32, 1, 0] | True | 29,228 | 2,766 | 34 | 1 | 0 | 324 | - |
| openai | 4 | pilot | 4/4 | True | 3 | [1, 4, 0] | True | 11,365 | 186 | 5 | 0 | 0 | 25 | - |
| openai | 4 | r0 | 4/4 | True | 3 | [1, 4, 0] | True | 11,387 | 197 | 5 | 0 | 0 | 26 | - |
| openai | 4 | r1 | 4/4 | True | 3 | [1, 4, 0] | True | 11,385 | 196 | 5 | 0 | 0 | 22 | - |
| openai | 8 | r0 | 8/8 | True | 3 | [1, 8, 0] | True | 11,629 | 332 | 9 | 0 | 0 | 30 | - |
| openai | 8 | r1 | 8/8 | True | 3 | [1, 8, 0] | True | 11,639 | 337 | 9 | 0 | 0 | 37 | - |
| openai | 16 | r0 | 16/16 | True | 3 | [1, 16, 0] | True | 12,121 | 606 | 17 | 0 | 0 | 60 | - |
| openai | 16 | r1 | 16/16 | True | 3 | [1, 16, 0] | True | 12,141 | 616 | 17 | 0 | 0 | 62 | - |
| openai | 32 | r0 | 32/32 | True | 3 | [1, 32, 0] | True | 13,151 | 1,177 | 33 | 0 | 0 | 107 | - |
| openai | 32 | r1 | 32/32 | True | 3 | [1, 32, 0] | True | 13,129 | 1,166 | 33 | 0 | 0 | 94 | - |

### Decision rules at N=32

- ollama: N=32 episodes [('r0', 32, 4), ('r1', 32, 4)] -> ordinary prompt holds; `clocks` key present in 0/2.
- openai: N=32 episodes [('r0', 32, 3), ('r1', 32, 3)] -> ordinary prompt holds; `clocks` key present in 2/2.
