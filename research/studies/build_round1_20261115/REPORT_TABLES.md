Episodes logged (full): 320 of 320; per arm: C1 80, C1+AG 80, C1+LA 80, C1+AG+LA 80

## Per model and arm

| model | arm | episodes | supported-complete | LLM requests | tokens (in+out) | episodes with an abort/error |
|---|---|---:|---:|---:|---:|---:|
| lfm3:1.7b | fixed loop (fresh control) | 20 | 16 | 117 | 639889 | 0 |
| lfm3:1.7b | + answer gate | 20 | 17 | 138 | 998565 | 0 |
| lfm3:1.7b | + list arguments | 20 | 15 | 117 | 675714 | 1 |
| lfm3:1.7b | + both | 20 | 16 | 130 | 730713 | 1 |
| qwen3.5:9b | fixed loop (fresh control) | 20 | 20 | 89 | 265853 | 0 |
| qwen3.5:9b | + answer gate | 20 | 20 | 88 | 260746 | 0 |
| qwen3.5:9b | + list arguments | 20 | 20 | 91 | 259708 | 0 |
| qwen3.5:9b | + both | 20 | 20 | 92 | 267051 | 0 |
| gpt-oss:20b | fixed loop (fresh control) | 20 | 16 | 116 | 293363 | 1 |
| gpt-oss:20b | + answer gate | 20 | 19 | 99 | 211774 | 0 |
| gpt-oss:20b | + list arguments | 20 | 17 | 88 | 177573 | 2 |
| gpt-oss:20b | + both | 20 | 18 | 106 | 216876 | 1 |
| bonsai-2:4b | fixed loop (fresh control) | 20 | 15 | 184 | 796709 | 0 |
| bonsai-2:4b | + answer gate | 20 | 14 | 216 | 1320656 | 0 |
| bonsai-2:4b | + list arguments | 20 | 15 | 139 | 411635 | 0 |
| bonsai-2:4b | + both | 20 | 15 | 140 | 416017 | 0 |
| all four | fixed loop (fresh control) | 80 | 67 | 506 | 1995814 | 1 |
| all four | + answer gate | 80 | 70 | 541 | 2791741 | 0 |
| all four | + list arguments | 80 | 67 | 435 | 1524630 | 3 |
| all four | + both | 80 | 69 | 468 | 1630657 | 2 |

## Same-cell comparison with the fresh control (supported-complete)

| arm | both supported | only arm | only control | neither | requests arm-control | tokens arm-control |
|---|---:|---:|---:|---:|---:|---:|
| + answer gate | 66 | 4 | 1 | 9 | +35 | +795927 |
| + list arguments | 61 | 6 | 6 | 7 | -71 | -471184 |
| + both | 62 | 7 | 5 | 6 | -38 | -365157 |

## Answer gate firings (arms with the gate)

- + answer gate: rejections 5 in 3 episodes; nudges 4 in 4 episodes; accepted after limit 2; answer changed after a rejection 3 of 4
  - lfm3:1.7b v2 s2: rejected {"node": "/plant32/cedar", "type": "std_srvs/srv/Trigger"} rules ['never_seen']; final supported False; control supported False; lfm3_1.7b-stage3/031-v2-C1+AG-lfm3_1.7b-s2
  - lfm3:1.7b v2 s2: rejected {"node": "/plant32/cedar", "type": "std_srsv/srv/Trigger"} rules ['never_seen']; final supported False; control supported False; lfm3_1.7b-stage3/031-v2-C1+AG-lfm3_1.7b-s2
  - bonsai-2:4b v2 s1: rejected {"node": "/plant32/cedar", "type": "std_srvs/srv/Trigger"} rules ['never_seen']; final supported False; control supported False; bonsai-2_4b-stage3/007-v2-C1+AG-bonsai-2_4b-s1
  - bonsai-2:4b h4 s1: rejected {"gains": {"dune": 65, "oasis": 89, "zephyr": 74}, "node": "/plant32/anvil", "publishers": {"/plant32/courier_t": "zephyr", "/plant32/fjord_ rules ['unique_suffix_bare', 'unique_suffix_bare', 'unique_suffix_bare', 'unique_suffix_bare', 'unique_suffix_bare', 'unique_suffix_bare']; final supported False; control supported False; bonsai-2_4b-stage3/009-h4-C1+AG-bonsai-2_4b-s1
  - bonsai-2:4b h4 s1: rejected {"gains": {"dune": 65, "oasis": 89, "zephyr": 74}, "node": "/plant32/anvil", "publishers": {"/plant32/courier_t": "/plant32/zephyr", "/plant rules ['unique_suffix_bare', 'unique_suffix_bare', 'unique_suffix_bare']; final supported False; control supported False; bonsai-2_4b-stage3/009-h4-C1+AG-bonsai-2_4b-s1
  - nudge 1: lfm3:1.7b e1h_chg_1 s1; final supported True; control supported True; lfm3_1.7b-e1h/003-e1h_chg_1-C1+AG-lfm3_1.7b-s1
  - nudge 1: gpt-oss:20b v2 s2; final supported True; control supported True; gpt-oss_20b-stage3/015-v2-C1+AG-gpt-oss_20b-s2
  - nudge 1: gpt-oss:20b e1h_amb_2 s2; final supported True; control supported True; gpt-oss_20b-e1h/018-e1h_amb_2-C1+AG-gpt-oss_20b-s2
  - nudge 1: gpt-oss:20b e1h_amb_1 s2; final supported True; control supported True; gpt-oss_20b-e1h/033-e1h_amb_1-C1+AG-gpt-oss_20b-s2
- + both: rejections 2 in 1 episodes; nudges 9 in 8 episodes; accepted after limit 1; answer changed after a rejection 0 of 2
  - lfm3:1.7b v2 s1: rejected {"node": "/plant32/cedar", "type": "std_srvs/srv/Trigger"} rules ['never_seen']; final supported False; control supported False; lfm3_1.7b-stage3/019-v2-C1+AG+LA-lfm3_1.7b-s1
  - lfm3:1.7b v2 s1: rejected {"node": "/plant32/cedar", "type": "std_srvs/srv/Trigger"} rules ['never_seen']; final supported False; control supported False; lfm3_1.7b-stage3/019-v2-C1+AG+LA-lfm3_1.7b-s1
  - nudge 1: lfm3:1.7b v2 s2; final supported True; control supported False; lfm3_1.7b-stage3/000-v2-C1+AG+LA-lfm3_1.7b-s2
  - nudge 1: lfm3:1.7b p3 s2; final supported False; control supported False; lfm3_1.7b-stage3/009-p3-C1+AG+LA-lfm3_1.7b-s2
  - nudge 1: gpt-oss:20b p3 s2; final supported True; control supported True; gpt-oss_20b-stage3/004-p3-C1+AG+LA-gpt-oss_20b-s2
  - nudge 1: gpt-oss:20b u3 s2; final supported True; control supported True; gpt-oss_20b-stage3/018-u3-C1+AG+LA-gpt-oss_20b-s2
  - nudge 1: gpt-oss:20b v2 s1; final supported True; control supported True; gpt-oss_20b-stage3/027-v2-C1+AG+LA-gpt-oss_20b-s1
  - nudge 1: gpt-oss:20b e1h_abs_2 s2; final supported True; control supported True; gpt-oss_20b-e1h/011-e1h_abs_2-C1+AG+LA-gpt-oss_20b-s2
  - nudge 1: gpt-oss:20b e1h_abs_1 s2; final supported False; control supported False; gpt-oss_20b-e1h/044-e1h_abs_1-C1+AG+LA-gpt-oss_20b-s2
  - nudge 2: gpt-oss:20b e1h_abs_1 s2; final supported False; control supported False; gpt-oss_20b-e1h/044-e1h_abs_1-C1+AG+LA-gpt-oss_20b-s2
  - nudge 1: bonsai-2:4b u3 s2; final supported True; control supported True; bonsai-2_4b-stage3/014-u3-C1+AG+LA-bonsai-2_4b-s2

Shadow gate in arms without it (would it have rejected?):
- fixed loop (fresh control): 74 final answers checked, would reject 3; of those supported-complete (= false rejections) 0
  - lfm3:1.7b v2 s2 supported False rules ['never_seen'] {"node": "/plant32/cedar", "type": "std_srvs/srv/Trigger"}
  - bonsai-2:4b h4 s1 supported False rules ['unique_suffix_bare', 'unique_suffix_bare', 'unique_suffix_bare', 'unique_suffix_bare', 'unique_suffix_bare', 'unique_suffix_bare'] {"gains": {"dune": 65, "oasis": 89, "zephyr": 74}, "node": "/plant32/anvil", "publishers": {"/plant32/courier_t": "zephy
  - bonsai-2:4b v2 s1 supported False rules ['never_seen'] {"node": "/plant32/cedar", "type": "std_srvs/srv/Trigger"}
- + list arguments: 71 final answers checked, would reject 1; of those supported-complete (= false rejections) 0
  - lfm3:1.7b v2 s1 supported False rules ['never_seen'] {"node": "/plant32/cedar", "type": "srv"}

Numbers log-only: 0 final answers contained an integer not seen in a tool result or the task: []

## List-argument adoption

| arm | episodes | episodes with a list call | tool calls | list calls | items per list call | requests/episode | tokens/episode |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed loop (fresh control) | 80 | 0 | 540 | 0 | - | 6.33 | 24948 |
| + answer gate | 80 | 0 | 573 | 0 | - | 6.76 | 34897 |
| + list arguments | 80 | 4 | 474 | 7 | 1.71 | 5.44 | 19058 |
| + both | 80 | 5 | 497 | 6 | 2.00 | 5.85 | 20383 |

## Per-cell table (supported / requests): control, gate, lists, both

| model | task | seed | C1 | C1+AG | C1+LA | C1+AG+LA |
|---|---|---:|---|---|---|---|
| lfm3:1.7b | e1h_abs_1 | 1 | n / 4 | Y / 2 | Y / 2 | Y / 2 |
| lfm3:1.7b | e1h_abs_1 | 2 | Y / 2 | Y / 2 | Y / 2 | Y / 2 |
| lfm3:1.7b | e1h_abs_2 | 1 | Y / 5 | Y / 2 | Y / 3 | Y / 3 |
| lfm3:1.7b | e1h_abs_2 | 2 | Y / 2 | Y / 2 | Y / 2 | Y / 2 |
| lfm3:1.7b | e1h_amb_1 | 1 | Y / 5 | Y / 5 | Y / 7 | Y / 7 |
| lfm3:1.7b | e1h_amb_1 | 2 | Y / 5 | Y / 5 | Y / 6 | Y / 6 |
| lfm3:1.7b | e1h_amb_2 | 1 | Y / 5 | Y / 5 | Y / 5 | Y / 5 |
| lfm3:1.7b | e1h_amb_2 | 2 | Y / 5 | Y / 5 | Y / 4 | Y / 4 |
| lfm3:1.7b | e1h_chg_1 | 1 | Y / 3 | Y / 3 | n / 2 | Y / 3 |
| lfm3:1.7b | e1h_chg_1 | 2 | Y / 3 | Y / 3 | Y / 3 | Y / 3 |
| lfm3:1.7b | e1h_chg_2 | 1 | Y / 3 | Y / 3 | Y / 3 | Y / 2 |
| lfm3:1.7b | e1h_chg_2 | 2 | Y / 3 | Y / 3 | Y / 5 | Y / 5 |
| lfm3:1.7b | h4 | 1 | Y / 7 | Y / 7 | Y / 10 | Y / 10 |
| lfm3:1.7b | h4 | 2 | Y / 7 | Y / 7 | n / 9 | n / 9 |
| lfm3:1.7b | p3 | 1 | Y / 5 | Y / 5 | Y / 4 | n / 5 |
| lfm3:1.7b | p3 | 2 | n / 5 | n / 3 | n / 4 | n / 5 |
| lfm3:1.7b | u3 | 1 | Y / 8 | Y / 10 | Y / 7 | Y / 7 |
| lfm3:1.7b | u3 | 2 | Y / 8 | Y / 7 | Y / 8 | Y / 8 |
| lfm3:1.7b | v2 | 1 | n / 1 | n / 23 | n / 26 | n / 24 |
| lfm3:1.7b | v2 | 2 | n / 31 | n / 36 | n / 5 | Y / 18 |
| qwen3.5:9b | e1h_abs_1 | 1 | Y / 2 | Y / 2 | Y / 4 | Y / 3 |
| qwen3.5:9b | e1h_abs_1 | 2 | Y / 2 | Y / 2 | Y / 2 | Y / 2 |
| qwen3.5:9b | e1h_abs_2 | 1 | Y / 2 | Y / 2 | Y / 2 | Y / 2 |
| qwen3.5:9b | e1h_abs_2 | 2 | Y / 3 | Y / 3 | Y / 2 | Y / 2 |
| qwen3.5:9b | e1h_amb_1 | 1 | Y / 5 | Y / 5 | Y / 5 | Y / 5 |
| qwen3.5:9b | e1h_amb_1 | 2 | Y / 5 | Y / 5 | Y / 7 | Y / 7 |
| qwen3.5:9b | e1h_amb_2 | 1 | Y / 4 | Y / 4 | Y / 5 | Y / 5 |
| qwen3.5:9b | e1h_amb_2 | 2 | Y / 4 | Y / 4 | Y / 4 | Y / 4 |
| qwen3.5:9b | e1h_chg_1 | 1 | Y / 4 | Y / 4 | Y / 3 | Y / 4 |
| qwen3.5:9b | e1h_chg_1 | 2 | Y / 3 | Y / 3 | Y / 3 | Y / 4 |
| qwen3.5:9b | e1h_chg_2 | 1 | Y / 4 | Y / 4 | Y / 4 | Y / 4 |
| qwen3.5:9b | e1h_chg_2 | 2 | Y / 4 | Y / 4 | Y / 4 | Y / 4 |
| qwen3.5:9b | h4 | 1 | Y / 6 | Y / 5 | Y / 7 | Y / 7 |
| qwen3.5:9b | h4 | 2 | Y / 12 | Y / 12 | Y / 5 | Y / 5 |
| qwen3.5:9b | p3 | 1 | Y / 4 | Y / 4 | Y / 4 | Y / 4 |
| qwen3.5:9b | p3 | 2 | Y / 4 | Y / 4 | Y / 5 | Y / 4 |
| qwen3.5:9b | u3 | 1 | Y / 4 | Y / 4 | Y / 7 | Y / 7 |
| qwen3.5:9b | u3 | 2 | Y / 7 | Y / 7 | Y / 5 | Y / 5 |
| qwen3.5:9b | v2 | 1 | Y / 5 | Y / 5 | Y / 9 | Y / 9 |
| qwen3.5:9b | v2 | 2 | Y / 5 | Y / 5 | Y / 4 | Y / 5 |
| gpt-oss:20b | e1h_abs_1 | 1 | Y / 2 | Y / 2 | Y / 3 | Y / 3 |
| gpt-oss:20b | e1h_abs_1 | 2 | n / 4 | n / 5 | Y / 3 | n / 7 |
| gpt-oss:20b | e1h_abs_2 | 1 | Y / 3 | Y / 3 | Y / 3 | Y / 4 |
| gpt-oss:20b | e1h_abs_2 | 2 | Y / 3 | Y / 2 | Y / 2 | Y / 5 |
| gpt-oss:20b | e1h_amb_1 | 1 | Y / 5 | Y / 6 | Y / 8 | Y / 6 |
| gpt-oss:20b | e1h_amb_1 | 2 | Y / 6 | Y / 5 | Y / 5 | Y / 7 |
| gpt-oss:20b | e1h_amb_2 | 1 | Y / 3 | Y / 3 | Y / 4 | Y / 3 |
| gpt-oss:20b | e1h_amb_2 | 2 | Y / 5 | Y / 7 | Y / 5 | Y / 5 |
| gpt-oss:20b | e1h_chg_1 | 1 | n / 4 | Y / 4 | Y / 4 | Y / 4 |
| gpt-oss:20b | e1h_chg_1 | 2 | Y / 4 | Y / 4 | Y / 4 | Y / 4 |
| gpt-oss:20b | e1h_chg_2 | 1 | n / 4 | Y / 4 | n / 4 | Y / 4 |
| gpt-oss:20b | e1h_chg_2 | 2 | Y / 4 | Y / 4 | Y / 4 | Y / 4 |
| gpt-oss:20b | h4 | 1 | n / 1 | Y / 13 | Y / 11 | Y / 5 |
| gpt-oss:20b | h4 | 2 | Y / 16 | Y / 9 | n / 1 | n / 10 |
| gpt-oss:20b | p3 | 1 | Y / 4 | Y / 4 | Y / 4 | Y / 4 |
| gpt-oss:20b | p3 | 2 | Y / 4 | Y / 4 | Y / 4 | Y / 5 |
| gpt-oss:20b | u3 | 1 | Y / 5 | Y / 4 | Y / 6 | Y / 4 |
| gpt-oss:20b | u3 | 2 | Y / 6 | Y / 4 | n / 2 | Y / 9 |
| gpt-oss:20b | v2 | 1 | Y / 9 | Y / 5 | Y / 6 | Y / 7 |
| gpt-oss:20b | v2 | 2 | Y / 24 | Y / 7 | Y / 5 | Y / 6 |
| bonsai-2:4b | e1h_abs_1 | 1 | Y / 2 | Y / 2 | Y / 2 | Y / 2 |
| bonsai-2:4b | e1h_abs_1 | 2 | Y / 3 | Y / 3 | Y / 3 | Y / 3 |
| bonsai-2:4b | e1h_abs_2 | 1 | n / 2 | n / 2 | n / 2 | n / 2 |
| bonsai-2:4b | e1h_abs_2 | 2 | n / 5 | n / 5 | n / 4 | n / 4 |
| bonsai-2:4b | e1h_amb_1 | 1 | Y / 5 | Y / 5 | Y / 5 | Y / 5 |
| bonsai-2:4b | e1h_amb_1 | 2 | Y / 5 | Y / 5 | Y / 5 | Y / 5 |
| bonsai-2:4b | e1h_amb_2 | 1 | Y / 7 | Y / 7 | Y / 5 | Y / 5 |
| bonsai-2:4b | e1h_amb_2 | 2 | Y / 4 | Y / 4 | Y / 4 | Y / 4 |
| bonsai-2:4b | e1h_chg_1 | 1 | Y / 4 | Y / 4 | Y / 4 | Y / 4 |
| bonsai-2:4b | e1h_chg_1 | 2 | Y / 3 | Y / 3 | Y / 3 | Y / 3 |
| bonsai-2:4b | e1h_chg_2 | 1 | Y / 8 | Y / 8 | Y / 7 | Y / 7 |
| bonsai-2:4b | e1h_chg_2 | 2 | n / 40 | n / 40 | Y / 11 | Y / 11 |
| bonsai-2:4b | h4 | 1 | n / 15 | n / 17 | Y / 7 | Y / 7 |
| bonsai-2:4b | h4 | 2 | Y / 16 | n / 17 | Y / 12 | Y / 12 |
| bonsai-2:4b | p3 | 1 | Y / 4 | Y / 4 | n / 3 | n / 3 |
| bonsai-2:4b | p3 | 2 | Y / 4 | Y / 4 | Y / 4 | Y / 4 |
| bonsai-2:4b | u3 | 1 | Y / 5 | Y / 5 | Y / 5 | Y / 5 |
| bonsai-2:4b | u3 | 2 | Y / 10 | Y / 10 | Y / 10 | Y / 11 |
| bonsai-2:4b | v2 | 1 | n / 17 | n / 40 | n / 3 | n / 3 |
| bonsai-2:4b | v2 | 2 | Y / 25 | Y / 31 | n / 40 | n / 40 |
