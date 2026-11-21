Episodes 400 (supported 343); fixed-loop requests 2430, tokens 9619344

### Proposal 1, V1 (two consecutive calls)

| model | episodes | episodes with a trigger | triggers | median group size | median sweep size | requests after first trigger (sum) | predicted saved requests | % of requests | saved tokens | extra tokens | extra tool runs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all four models | 400 | 22 | 31 | 19 | 14 | 144 | 93 | 3.8 | 746353 | 17590 | 250 |
| lfm3:1.7b | 100 | 4 | 5 | 19 | 17 | 16 | 3 | 0.5 | 46811 | 4384 | 69 |
| qwen3.5:9b | 100 | 5 | 7 | 19 | 17 | 17 | 8 | 1.8 | 43706 | 5880 | 80 |
| gpt-oss:20b | 100 | 4 | 7 | 19 | 2 | 28 | 18 | 3.5 | 84240 | 3776 | 18 |
| bonsai-2:4b | 100 | 9 | 12 | 19 | 14 | 83 | 64 | 7.4 | 571596 | 3551 | 83 |

### Proposal 1, V2 (one call, group of 2 to 4 names)

| model | episodes | episodes with a trigger | triggers | median group size | median sweep size | requests after first trigger (sum) | predicted saved requests | % of requests | saved tokens | extra tokens | extra tool runs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all four models | 400 | 88 | 159 | 2 | 1 | 313 | 18 | 0.7 | 55551 | 82912 | 179 |
| lfm3:1.7b | 100 | 26 | 56 | 2 | 1 | 71 | 2 | 0.3 | 6850 | 19246 | 63 |
| qwen3.5:9b | 100 | 15 | 26 | 2 | 1 | 57 | 6 | 1.3 | 16344 | 17456 | 30 |
| gpt-oss:20b | 100 | 21 | 31 | 2 | 1 | 85 | 7 | 1.4 | 19207 | 17152 | 31 |
| bonsai-2:4b | 100 | 26 | 46 | 2 | 1 | 100 | 3 | 0.3 | 13150 | 29059 | 55 |

### Proposal 2, stall breaker

| model | episodes | stalls rule (a) | stalls (a') | stalls (b) | episodes with a stall (a or b) | supported episodes with a stall | requests after first stall | second stalls | hides that remove a useful call (all) | in supported episodes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all four models | 400 | 331 | 253 | 206 | 46 | 27 | 1103 | 36 | 5 | 2 |
| lfm3:1.7b | 100 | 57 | 24 | 47 | 9 | 4 | 362 | 14 | 4 | 1 |
| qwen3.5:9b | 100 | 3 | 3 | 0 | 3 | 3 | 15 | 0 | 0 | 0 |
| gpt-oss:20b | 100 | 14 | 10 | 5 | 10 | 6 | 53 | 1 | 1 | 1 |
| bonsai-2:4b | 100 | 257 | 216 | 154 | 24 | 14 | 673 | 21 | 0 | 0 |

### Proposal 3, answer rewrite

| model | answers | unchanged | rewritten | would reject | supported before, rewritten | supported after rewrite | unsupported -> supported | supported -> unsupported | supported answers that would be rejected | rejects with a ledger next step |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all four models | 386 | 377 | 3 | 6 | 0 | 3 | 3 | 0 | 0 | 6 of 6 |
| lfm3:1.7b | 97 | 93 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 4 of 4 |
| qwen3.5:9b | 100 | 100 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 of 0 |
| gpt-oss:20b | 96 | 96 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 of 0 |
| bonsai-2:4b | 93 | 88 | 3 | 2 | 0 | 3 | 3 | 0 | 0 | 2 of 2 |

### Concentration (the 400 episodes are 80 cells run up to 5 times each)

- p1_v1: saved requests 93 in 11 distinct cells; in supported episodes 73, in unsupported 20; top 5 cells = 81 (87%): bonsai-2:4b v2 s2=45, gpt-oss:20b v2 s2=17, bonsai-2:4b v2 s1=11, qwen3.5:9b h4 s2=4, qwen3.5:9b v2 s1=4
  by task: {'v2': 79, 'h4': 10, 'u3': 4, 'p3': 0, 'e1h_amb_2': 0, 'e1h_abs_1': 0, 'e1h_abs_2': 0, 'e1h_chg_2': 0, 'e1h_chg_1': 0, 'e1h_amb_1': 0}
- p1_v2: saved requests 18 in 8 distinct cells; in supported episodes 17, in unsupported 1; top 5 cells = 15 (83%): qwen3.5:9b e1h_amb_1 s2=6, gpt-oss:20b h4 s1=4, lfm3:1.7b e1h_amb_1 s2=2, bonsai-2:4b e1h_amb_2 s1=2, gpt-oss:20b e1h_amb_1 s1=1
  by task: {'e1h_amb_1': 10, 'h4': 6, 'e1h_amb_2': 2, 'p3': 0, 'e1h_abs_1': 0, 'e1h_abs_2': 0, 'e1h_chg_2': 0, 'e1h_chg_1': 0, 'v2': 0, 'u3': 0}
- proposal 3: rewritten episodes 3 come from 1 distinct cell(s): [('bonsai-2:4b', 'h4', 1)]; would-reject episodes come from 3 cells
- proposal 2: supported episodes where hiding removes a useful call: 2 episodes in cells [('gpt-oss:20b', 'h4', 2), ('lfm3:1.7b', 'h4', 2)]
