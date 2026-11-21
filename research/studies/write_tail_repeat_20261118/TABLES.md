# Tables (generated from results.json; protocol hash a60ded7c9da3...)

## Item 1. Write-tool attempts by arm and execution status

| arm | episodes in arm | episodes with an attempt | no_result_validation | validation_text | guard_rejected | not_available | executed | by model |
|---|---|---|---|---|---|---|---|---|
| ablation/NO_MENU | 40 | 1 | 0 | 0 | 0 | 4 | 0 | {'bonsai-2:4b': 4} |
| fairness/E0 | 80 | 7 | 0 | 49 | 5 | 0 | 0 | {'qwen3.5:9b': 3, 'bonsai-2:4b': 51} |
| fairness/E1 | 80 | 3 | 0 | 0 | 7 | 0 | 0 | {'bonsai-2:4b': 7} |
| pilot/A1 | 80 | 4 | 4 | 0 | 0 | 0 | 0 | {'lfm3:1.7b': 1, 'bonsai-2:4b': 3} |
| s0/S0 | 80 | 7 | 4 | 0 | 3 | 0 | 0 | {'lfm3:1.7b': 1, 'qwen3.5:9b': 1, 'bonsai-2:4b': 5} |

Would have changed (inference from arguments and fixture listings):

| arm | classes |
|---|---|
| ablation/NO_MENU | {'existing other service': 3, 'no such service': 1} |
| fairness/E0 | {'existing other service': 5, 'no such service': 42, 'no such node': 6, 'existing node, existing parameter': 1} |
| fairness/E1 | {'no such node': 1, 'existing other service': 5, 'existing node, existing parameter': 1} |
| pilot/A1 | {'existing other service': 1, 'no such service': 2, 'no such node': 1} |
| s0/S0 | {'existing node, existing parameter': 2, 'existing other service': 1, 'no such service': 3, 'no such node': 1} |

Arms with 0 attempts (episodes): ablation/FULL (40); ablation/NO_FINISH (40); ablation/NO_PRECHECK (40); ablation/NO_SOFT_ERRORS (40); compaction/COMPACT (40); compaction/FULL (40); namefix/NAMEFIX (64); pilot/C1 (80); pilot/C1+FN (80); pilot/C1+H1e (80); pilot/C1+H1n (16); pilot/C1+H2 (80); pilot/C1+H7 (80); pilot/M0 (80); round1/C1 (80); round1/C1+AG (80); round1/C1+AG+LA (80); round1/C1+LA (80); round2/CONTROL (176); round2/SWEEP (176).

## Item 2. Per-episode requests and tokens

| arm | n | requests median / p90 / max | tokens median / p90 / max | cap endings (>=40 requests) | top-decile share of requests | models with a cap |
|---|---|---|---|---|---|---|
| ORIG (s0 S0) | 80 | 5.0 / 9 / 35 | 31830 / 74110 / 397494 | 0 (0) | 0.327 | 0 |
| E0 | 80 | 6.0 / 15 / 40 | 33890 / 143373 / 473268 | 1 (1) | 0.317 | 1 |
| E1 | 80 | 5.0 / 12 / 40 | 29874 / 92265 / 413463 | 3 (3) | 0.364 | 1 |
| A1 (extra) | 80 | 4.0 / 11 / 40 | 26788 / 73062 / 318057 | 2 (2) | 0.367 | 1 |
| FULL (pilot C1) | 80 | 4.0 / 10 / 40 | 10647 / 39438 / 157012 | 1 (1) | 0.321 | 1 |
| FULL (round1 C1) | 80 | 4.0 / 12 / 40 | 10437 / 50127 / 341122 | 1 (1) | 0.364 | 1 |
| FULL (ablation) | 40 | 4.0 / 8 / 17 | 9946 / 30075 / 144942 | 0 (0) | 0.27 | 0 |
| FULL (compaction) | 40 | 4.0 / 8 / 23 | 10724 / 33018 / 252364 | 0 (0) | 0.266 | 0 |

Per model (requests median / p90 / max; tokens median / p90 / max; caps):

- **ORIG (s0 S0)**: bonsai-2:4b 5.0/21/35, 31984/171394/397494, cap 0; gpt-oss:20b 1.0/2/4, 4761/8167/15838, cap 0; lfm3:1.7b 6.0/10/24, 39598/81259/344790, cap 0; qwen3.5:9b 5.5/7/13, 39015/50637/111945, cap 0
- **E0**: bonsai-2:4b 7.5/25/40, 48246/234748/473268, cap 1; gpt-oss:20b 6.0/7/29, 24930/54116/229379, cap 0; lfm3:1.7b 6.0/11/15, 36121/95934/212146, cap 0; qwen3.5:9b 6.0/8/12, 42605/56751/119190, cap 0
- **E1**: bonsai-2:4b 7.0/40/40, 43894/269686/398265, cap 3; gpt-oss:20b 4.5/8/29, 16611/33974/181631, cap 0; lfm3:1.7b 5.5/7/23, 35842/51433/413463, cap 0; qwen3.5:9b 5.0/8/17, 29888/60130/192339, cap 0
- **A1 (extra)**: bonsai-2:4b 5.0/27/40, 30402/269686/318057, cap 2; gpt-oss:20b 1.0/4/14, 3820/14553/73062, cap 0; lfm3:1.7b 5.5/12/14, 34698/105350/228883, cap 0; qwen3.5:9b 4.0/7/9, 26185/52396/65767, cap 0
- **FULL (pilot C1)**: bonsai-2:4b 5.0/17/40, 12080/125702/146302, cap 1; gpt-oss:20b 4.0/9/14, 6856/25133/39438, cap 0; lfm3:1.7b 4.5/8/17, 12230/35182/157012, cap 0; qwen3.5:9b 4.0/8/8, 9856/23323/28812, cap 0
- **FULL (round1 C1)**: bonsai-2:4b 5.0/17/40, 12069/124983/160465, cap 1; gpt-oss:20b 4.0/9/24, 6543/23518/103857, cap 0; lfm3:1.7b 5.0/8/31, 13979/35328/341122, cap 0; qwen3.5:9b 4.0/6/12, 9842/22381/50127, cap 0
- **FULL (ablation)**: bonsai-2:4b 4.5/14/17, 11426/62800/125981, cap 0; gpt-oss:20b 4.0/8/10, 6712/19446/28782, cap 0; lfm3:1.7b 6.0/8/16, 17900/34488/144942, cap 0; qwen3.5:9b 4.0/5/5, 9896/17263/20868, cap 0
- **FULL (compaction)**: bonsai-2:4b 5.0/12/12, 13184/62643/73158, cap 0; gpt-oss:20b 4.0/7/7, 6779/15189/16416, cap 0; lfm3:1.7b 5.5/8/23, 18653/36075/252364, cap 0; qwen3.5:9b 4.0/6/6, 9881/18621/22106, cap 0

## Item 3. Repeat loops (episodes with >= 2 identical successful repeats)

Rebuild check B3a: {'agree': 1816, 'total': 1832, 'share': 0.9913}. Episodes of interest: 159.

| group | facts_present: episodes / unsupported / no answer / requests after first repeat (median) | facts_not_yet: episodes / unsupported / no answer / requests after (median) |
|---|---|---|
| pooled | 82 / 51 / 12 / 8.0 | 77 / 45 / 31 / 21 |
| bonsai-2:4b | 47 / 25 / 10 / 7 | 58 / 36 / 29 / 30.0 |
| gpt-oss:20b | 1 / 0 / 0 / 25 | 4 / 0 / 0 / 5.5 |
| lfm3:1.7b | 25 / 24 / 2 / 12 | 9 / 6 / 1 / 8 |
| qwen3.5:9b | 9 / 2 / 0 / 3 | 6 / 3 / 1 / 6.0 |
| stock-executor arms | 25 / 13 / 6 / 5 | 9 / 5 / 5 / 8 |
| menu arms | 57 / 38 / 6 / 8 | 68 / 40 / 26 / 21.5 |

Bar B3 inputs: {'facts_present_episodes': 82, 'models': 4, 'unsupported_or_no_answer': 51}
