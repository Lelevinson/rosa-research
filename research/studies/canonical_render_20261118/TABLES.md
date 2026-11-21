# Tables (generated from results.json; protocol hash 60a48b797642cfc4)

Episodes 1832, menu-tool results 10747. Bars: {'lossless_violations': 0, 'lossless_bar_met': True, 'scorer_changes': 0, 'scorer_bar_met': True, 'score_failures': 0}. Not idempotent: 0.

## Parsed vs passed through, per tool
| tool | results | changed | leaves | share rendered | lines | key-value | header | bare | chars in rendered leaves | derived lines |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| read_log | 9 | 0 | 83 | 0.867 | 83 | 0.867 | 0.0 | 0.133 | 0.873 | 0 |
| ros2_doctor | 6 | 0 | 6 | 1.0 | 6 | 1.0 | 0.0 | 0.0 | 1.0 | 0 |
| ros2_node_info | 2298 | 1342 | 4403 | 0.778 | 61067 | 0.595 | 0.333 | 0.072 | 0.988 | 0 |
| ros2_node_list | 1609 | 0 | 15754 | 0.002 | 15805 | 0.002 | 0.0 | 0.998 | 0.006 | 0 |
| ros2_param_get | 2981 | 0 | 3093 | 0.951 | 3199 | 0.936 | 0.0 | 0.064 | 0.972 | 0 |
| ros2_param_list | 805 | 0 | 2791 | 0.001 | 2791 | 0.001 | 0.0 | 0.999 | 0.017 | 0 |
| ros2_service_info | 642 | 0 | 683 | 0.007 | 351 | 0.017 | 0.0 | 0.983 | 0.383 | 0 |
| ros2_service_list | 290 | 0 | 19420 | 0.0 | 19423 | 0.0 | 0.0 | 1.0 | 0.0 | 0 |
| ros2_topic_echo | 99 | 0 | 65 | 0.2 | 78 | 0.167 | 0.0 | 0.833 | 0.069 | 0 |
| ros2_topic_info | 1200 | 1123 | 1857 | 0.917 | 45325 | 0.934 | 0.063 | 0.004 | 0.996 | 2853 |
| ros2_topic_list | 792 | 0 | 5381 | 0.008 | 5393 | 0.008 | 0.0 | 0.992 | 0.023 | 0 |
| roslog_list | 16 | 0 | 3135 | 0.0 | 3135 | 0.0 | 0.0 | 1.0 | 0.0 | 0 |

All tools: leaves 56671, rendered 8235; results changed 2465 of 10747; derived lines 2853; R6 skips 0.

## Size (characters of the JSON text of each result)
Change per result: {'n': 10747, 'median': 0, 'mean': 4.99, 'min': -136, 'max': 1883}; larger 1122, equal 8282, smaller 1343; total 6092200 -> 6145881.

| tool | results | mean chars before | mean chars after | median change |
|---|---:|---:|---:|---:|
| read_log | 9 | 1015.2 | 1015.2 | 0 |
| ros2_doctor | 6 | 54 | 54 | 0.0 |
| ros2_node_info | 2298 | 1326.3 | 1315.8 | -6.0 |
| ros2_node_list | 1609 | 197.6 | 197.6 | 0 |
| ros2_param_get | 2981 | 44.8 | 44.8 | 0 |
| ros2_param_list | 805 | 94.9 | 94.9 | 0 |
| ros2_service_info | 642 | 53.1 | 53.1 | 0.0 |
| ros2_service_list | 290 | 2502.0 | 2502.0 | 0.0 |
| ros2_topic_echo | 99 | 44.1 | 44.1 | 0 |
| ros2_topic_info | 1200 | 1223.9 | 1288.6 | 55.0 |
| ros2_topic_list | 792 | 151.2 | 151.2 | 0.0 |
| roslog_list | 16 | 9671.1 | 9671.1 | 0.0 |

## Per-episode history effect (estimated input tokens = characters / 4 x later requests)
Per episode: {'n': 1832, 'median': 0.0, 'mean': 43.0, 'min': -548.0, 'max': 6693.8}; as % of logged input tokens: {'n': 1826, 'median': 0.0, 'mean': 0.11, 'min': -0.41, 'max': 3.05}. Total 78767 estimated tokens against 56675122 logged input tokens.

| group | episodes | estimated token change | logged input tokens | change % |
|---|---:|---:|---:|---:|
| model: bonsai-2:4b | 458 | 43296 | 23939300 | 0.18 |
| model: gpt-oss:20b | 458 | 11858 | 5883791 | 0.20 |
| model: lfm3:1.7b | 458 | 11794 | 18212454 | 0.06 |
| model: qwen3.5:9b | 458 | 11819 | 8639577 | 0.14 |
| study: ablation | 200 | 5850 | 4874156 | 0.12 |
| study: compaction | 80 | 1751 | 1967921 | 0.09 |
| study: fairness | 160 | 5288 | 8913925 | 0.06 |
| study: namefix | 64 | 5454 | 813204 | 0.67 |
| study: pilot | 576 | 19913 | 15882544 | 0.13 |
| study: round1 | 320 | 6579 | 7543392 | 0.09 |
| study: round2 | 352 | 32964 | 13034188 | 0.25 |
| study: s0 | 80 | 968 | 3645792 | 0.03 |

## Where the resolution of each name fire lives (item 5)
Fires 406: {'split_only': 231, 'contiguous_earlier': 145, 'task_text': 30}. Split-only fires whose rendered earlier results contain the full name as one string: 229. Relation of the typed name to the name field: {'typed_equals_name_field': 229, 'typed_differs_from_name_field': 2}.

| group | task text | contiguous earlier | split-only |
|---|---:|---:|---:|
| model: bonsai-2:4b | 24 | 108 | 64 |
| model: gpt-oss:20b | 0 | 0 | 33 |
| model: lfm3:1.7b | 6 | 34 | 92 |
| model: qwen3.5:9b | 0 | 3 | 42 |
| study: ablation | 5 | 17 | 14 |
| study: compaction | 7 | 4 | 9 |
| study: fairness | 6 | 2 | 11 |
| study: namefix | 1 | 1 | 11 |
| study: pilot | 4 | 43 | 73 |
| study: round1 | 0 | 30 | 27 |
| study: round2 | 7 | 46 | 85 |
| study: s0 | 0 | 2 | 1 |
