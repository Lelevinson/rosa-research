S0 episodes logged: 80 of 80

| model | arm | episodes | supported-complete | LLM requests | tokens (in+out) | episodes with an abort/error |
|---|---|---:|---:|---:|---:|---:|
| lfm3:1.7b | stock ROSA, verbatim prompt (S0, this run) | 20 | 13 | 152 | 1280320 | 1 |
| lfm3:1.7b | fixed loop (build round 1 control) | 20 | 16 | 117 | 639889 | 0 |
| lfm3:1.7b | stock executor, deconflicted prompt (A1, pilot) | 20 | 15 | 135 | 1090427 | 2 |
| qwen3.5:9b | stock ROSA, verbatim prompt (S0, this run) | 20 | 16 | 120 | 851698 | 1 |
| qwen3.5:9b | fixed loop (build round 1 control) | 20 | 20 | 89 | 265853 | 0 |
| qwen3.5:9b | stock executor, deconflicted prompt (A1, pilot) | 20 | 19 | 86 | 563736 | 0 |
| gpt-oss:20b | stock ROSA, verbatim prompt (S0, this run) | 20 | 2 | 28 | 114512 | 18 |
| gpt-oss:20b | fixed loop (build round 1 control) | 20 | 16 | 116 | 293363 | 1 |
| gpt-oss:20b | stock executor, deconflicted prompt (A1, pilot) | 20 | 7 | 54 | 217813 | 11 |
| bonsai-2:4b | stock ROSA, verbatim prompt (S0, this run) | 20 | 9 | 180 | 1495780 | 4 |
| bonsai-2:4b | fixed loop (build round 1 control) | 20 | 15 | 184 | 796709 | 0 |
| bonsai-2:4b | stock executor, deconflicted prompt (A1, pilot) | 20 | 6 | 197 | 1409447 | 5 |
| all four | stock ROSA, verbatim prompt (S0, this run) | 80 | 40 | 480 | 3742310 | 24 |
| all four | fixed loop (build round 1 control) | 80 | 67 | 506 | 1995814 | 1 |
| all four | stock executor, deconflicted prompt (A1, pilot) | 80 | 47 | 472 | 3281423 | 18 |

Same-cell, S0 vs fixed loop (build round 1 control): both supported 37, only S0 3, only comparator 30, neither 10 (cells 80)

Same-cell, S0 vs stock executor, deconflicted prompt (A1, pilot): both supported 31, only S0 9, only comparator 16, neither 24 (cells 80)

S0 abort/error kinds: {'ResponseError': 3, 'validation error: request': 3, 'validation error: blacklist': 17, 'validation error: param_value': 1}

Per-cell (supported / requests): S0, fixed loop, A1

| model | task | seed | S0 | fixed loop | A1 |
|---|---|---:|---|---|---|
| lfm3:1.7b | e1h_abs_1 | 1 | n / 6 | n / 4 | n / 6 |
| lfm3:1.7b | e1h_abs_1 | 2 | n / 9 | Y / 2 | Y / 3 |
| lfm3:1.7b | e1h_abs_2 | 1 | Y / 4 | Y / 5 | Y / 2 |
| lfm3:1.7b | e1h_abs_2 | 2 | n / 7 | Y / 2 | Y / 2 |
| lfm3:1.7b | e1h_amb_1 | 1 | Y / 8 | Y / 5 | Y / 14 |
| lfm3:1.7b | e1h_amb_1 | 2 | Y / 6 | Y / 5 | Y / 7 |
| lfm3:1.7b | e1h_amb_2 | 1 | Y / 6 | Y / 5 | Y / 6 |
| lfm3:1.7b | e1h_amb_2 | 2 | Y / 6 | Y / 5 | Y / 5 |
| lfm3:1.7b | e1h_chg_1 | 1 | Y / 6 | Y / 3 | Y / 4 |
| lfm3:1.7b | e1h_chg_1 | 2 | Y / 6 | Y / 3 | Y / 5 |
| lfm3:1.7b | e1h_chg_2 | 1 | Y / 8 | Y / 3 | Y / 5 |
| lfm3:1.7b | e1h_chg_2 | 2 | n / 4 | Y / 3 | Y / 4 |
| lfm3:1.7b | h4 | 1 | Y / 12 | Y / 7 | Y / 8 |
| lfm3:1.7b | h4 | 2 | Y / 10 | Y / 7 | Y / 11 |
| lfm3:1.7b | p3 | 1 | n / 4 | Y / 5 | n / 5 |
| lfm3:1.7b | p3 | 2 | n / 6 | n / 5 | n / 5 |
| lfm3:1.7b | u3 | 1 | Y / 7 | Y / 8 | Y / 9 |
| lfm3:1.7b | u3 | 2 | Y / 9 | Y / 8 | Y / 8 |
| lfm3:1.7b | v2 | 1 | n / 4 | n / 1 | n / 14 |
| lfm3:1.7b | v2 | 2 | Y / 24 | n / 31 | n / 12 |
| qwen3.5:9b | e1h_abs_1 | 1 | n / 7 | Y / 2 | Y / 2 |
| qwen3.5:9b | e1h_abs_1 | 2 | Y / 2 | Y / 2 | Y / 2 |
| qwen3.5:9b | e1h_abs_2 | 1 | Y / 2 | Y / 2 | Y / 2 |
| qwen3.5:9b | e1h_abs_2 | 2 | n / 6 | Y / 3 | Y / 2 |
| qwen3.5:9b | e1h_amb_1 | 1 | Y / 6 | Y / 5 | Y / 6 |
| qwen3.5:9b | e1h_amb_1 | 2 | Y / 7 | Y / 5 | Y / 5 |
| qwen3.5:9b | e1h_amb_2 | 1 | Y / 5 | Y / 4 | Y / 4 |
| qwen3.5:9b | e1h_amb_2 | 2 | Y / 7 | Y / 4 | Y / 5 |
| qwen3.5:9b | e1h_chg_1 | 1 | Y / 5 | Y / 4 | Y / 3 |
| qwen3.5:9b | e1h_chg_1 | 2 | n / 5 | Y / 3 | Y / 3 |
| qwen3.5:9b | e1h_chg_2 | 1 | Y / 4 | Y / 4 | Y / 3 |
| qwen3.5:9b | e1h_chg_2 | 2 | Y / 5 | Y / 4 | Y / 5 |
| qwen3.5:9b | h4 | 1 | Y / 13 | Y / 6 | Y / 5 |
| qwen3.5:9b | h4 | 2 | Y / 12 | Y / 12 | Y / 7 |
| qwen3.5:9b | p3 | 1 | Y / 5 | Y / 4 | n / 3 |
| qwen3.5:9b | p3 | 2 | Y / 4 | Y / 4 | Y / 4 |
| qwen3.5:9b | u3 | 1 | Y / 7 | Y / 4 | Y / 5 |
| qwen3.5:9b | u3 | 2 | Y / 7 | Y / 7 | Y / 9 |
| qwen3.5:9b | v2 | 1 | n / 6 | Y / 5 | Y / 4 |
| qwen3.5:9b | v2 | 2 | Y / 5 | Y / 5 | Y / 7 |
| gpt-oss:20b | e1h_abs_1 | 1 | n / 1 | Y / 2 | n / 1 |
| gpt-oss:20b | e1h_abs_1 | 2 | n / 1 | n / 4 | Y / 2 |
| gpt-oss:20b | e1h_abs_2 | 1 | n / 2 | Y / 3 | n / 1 |
| gpt-oss:20b | e1h_abs_2 | 2 | Y / 2 | Y / 3 | n / 1 |
| gpt-oss:20b | e1h_amb_1 | 1 | n / 1 | Y / 5 | n / 1 |
| gpt-oss:20b | e1h_amb_1 | 2 | n / 1 | Y / 6 | n / 1 |
| gpt-oss:20b | e1h_amb_2 | 1 | n / 1 | Y / 3 | Y / 3 |
| gpt-oss:20b | e1h_amb_2 | 2 | n / 2 | Y / 5 | n / 1 |
| gpt-oss:20b | e1h_chg_1 | 1 | n / 1 | n / 4 | Y / 4 |
| gpt-oss:20b | e1h_chg_1 | 2 | n / 2 | Y / 4 | Y / 4 |
| gpt-oss:20b | e1h_chg_2 | 1 | Y / 4 | n / 4 | Y / 4 |
| gpt-oss:20b | e1h_chg_2 | 2 | n / 1 | Y / 4 | n / 4 |
| gpt-oss:20b | h4 | 1 | n / 1 | n / 1 | n / 14 |
| gpt-oss:20b | h4 | 2 | n / 1 | Y / 16 | n / 1 |
| gpt-oss:20b | p3 | 1 | n / 2 | Y / 4 | Y / 4 |
| gpt-oss:20b | p3 | 2 | n / 1 | Y / 4 | Y / 4 |
| gpt-oss:20b | u3 | 1 | n / 1 | Y / 5 | n / 1 |
| gpt-oss:20b | u3 | 2 | n / 1 | Y / 6 | n / 1 |
| gpt-oss:20b | v2 | 1 | n / 1 | Y / 9 | n / 1 |
| gpt-oss:20b | v2 | 2 | n / 1 | Y / 24 | n / 1 |
| bonsai-2:4b | e1h_abs_1 | 1 | n / 21 | Y / 2 | n / 7 |
| bonsai-2:4b | e1h_abs_1 | 2 | n / 4 | Y / 3 | n / 12 |
| bonsai-2:4b | e1h_abs_2 | 1 | n / 4 | n / 2 | n / 2 |
| bonsai-2:4b | e1h_abs_2 | 2 | n / 4 | n / 5 | Y / 3 |
| bonsai-2:4b | e1h_amb_1 | 1 | Y / 9 | Y / 5 | Y / 5 |
| bonsai-2:4b | e1h_amb_1 | 2 | Y / 5 | Y / 5 | Y / 5 |
| bonsai-2:4b | e1h_amb_2 | 1 | Y / 7 | Y / 7 | n / 5 |
| bonsai-2:4b | e1h_amb_2 | 2 | Y / 7 | Y / 4 | Y / 5 |
| bonsai-2:4b | e1h_chg_1 | 1 | n / 5 | Y / 4 | n / 4 |
| bonsai-2:4b | e1h_chg_1 | 2 | Y / 5 | Y / 3 | n / 5 |
| bonsai-2:4b | e1h_chg_2 | 1 | Y / 4 | Y / 8 | n / 8 |
| bonsai-2:4b | e1h_chg_2 | 2 | n / 5 | n / 40 | Y / 7 |
| bonsai-2:4b | h4 | 1 | Y / 30 | n / 15 | n / 40 |
| bonsai-2:4b | h4 | 2 | n / 8 | Y / 16 | n / 1 |
| bonsai-2:4b | p3 | 1 | Y / 4 | Y / 4 | n / 4 |
| bonsai-2:4b | p3 | 2 | n / 5 | Y / 4 | Y / 4 |
| bonsai-2:4b | u3 | 1 | Y / 35 | Y / 5 | n / 6 |
| bonsai-2:4b | u3 | 2 | n / 7 | Y / 10 | n / 7 |
| bonsai-2:4b | v2 | 1 | n / 7 | n / 17 | n / 27 |
| bonsai-2:4b | v2 | 2 | n / 4 | Y / 25 | n / 40 |
