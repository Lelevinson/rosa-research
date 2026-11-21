## Table: floor, Qwen A0 vs gpt-6-luna A0 (requests per repeat r0, r1)

| task | floor | Qwen requests | Luna requests | Luna calls per request | Luna supported-complete | Qwen supported-complete | Luna native ops | Qwen native ops | Luna seconds | Qwen seconds |
|---|---:|---|---|---|---|---|---|---|---|---|
| t1 | 4 | [6, 5] | [4, 5] | [[2, 3, 3, 0], [1, 1, 3, 3, 0]] | [True, True] | [True, True] | [8, 8] | [10, 10] | [27, 29] | [73, 66] |
| t2 | 3 | [6, 6] | [3, 6] | [[3, 3, 0], [1, 1, 1, 1, 1, 0]] | [True, True] | [True, True] | [7, 6] | [4, 4] | [17, 22] | [55, 49] |
| t3 | 3 | [3, 3] | [3, 4] | [[2, 2, 0], [1, 1, 1, 0]] | [True, True] | [True, True] | [6, 3] | [3, 3] | [14, 15] | [42, 35] |
| d1 | 3 | [6, 6] | [4, 4] | [[2, 1, 2, 0], [1, 1, 2, 0]] | [True, True] | [True, True] | [5, 4] | [7, 7] | [22, 19] | [74, 73] |
| d2 | 4 | [5, 7] | [3, 3] | [[3, 3, 0], [3, 3, 0]] | [False, False] | [False, False] | [6, 6] | [6, 7] | [15, 16] | [44, 58] |
| x1 | 3 | [5, 5] | [3, 3] | [[2, 5, 0], [2, 5, 0]] | [True, True] | [True, True] | [8, 8] | [12, 12] | [26, 25] | [101, 96] |

Totals over 12 episodes each: Luna 45 requests, 186,110 input tokens, 75 native ops, 10 supported-complete; Qwen A0 63 requests, 424,475 input tokens, 85 native ops, 10 supported-complete.

`d2` as scored: Luna 0/2 (same missing `get_type_description` as every earlier d2 episode); read by hand both Luna answers report the same one service as Qwen did. Luna used 3 requests, below the strict floor 4, by over-fetching in parallel (the documented alt floor 3). Scored result is the primary one.

## Decision rule

Luna excess over floor: t2 [0, 3], d1 [1, 1]. Qwen A0 excess: t2 [3, 3], d1 [3, 3].
- Gap exists (Luna <= floor+1 on both tasks in both repeats): NO (t2 repeat 1 is floor+3).
- No gap (Luna >= floor+2 on t2 or d1 in at least one repeat): YES on the literal reading (t2 r1 = floor+3); under the stricter reading that each of t2 and d1 needs such a repeat it would NOT hold (d1 is floor+1 in both), and the result would fall in Inconclusive.
- Usable episodes: 12 of 12.
