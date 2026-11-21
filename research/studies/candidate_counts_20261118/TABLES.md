# Tables (generated from results.json; protocol hash ddeb30a08e64f133)

## Population (episodes)
| study | bonsai-2:4b | lfm3:1.7b | qwen3.5:9b | gpt-oss:20b | all |
|---|---:|---:|---:|---:|---:|
| ablation | 50 | 50 | 50 | 50 | 200 |
| compaction | 20 | 20 | 20 | 20 | 80 |
| fairness | 40 | 40 | 40 | 40 | 160 |
| namefix | 16 | 16 | 16 | 16 | 64 |
| pilot | 144 | 144 | 144 | 144 | 576 |
| round1 | 80 | 80 | 80 | 80 | 320 |
| round2 | 88 | 88 | 88 | 88 | 352 |
| s0 | 20 | 20 | 20 | 20 | 80 |

## (a) Name-binding fires (not-found, no leading slash, unique whole-segment suffix of a clean-ledger name)
| study | bonsai-2:4b | lfm3:1.7b | qwen3.5:9b | gpt-oss:20b | all |
|---|---:|---:|---:|---:|---:|
| pilot | 77 | 26 | 8 | 9 | 120 |
| round1 | 19 | 24 | 8 | 6 | 57 |
| round2 | 46 | 56 | 22 | 14 | 138 |
| fairness | 8 | 6 | 2 | 3 | 19 |
| ablation | 23 | 7 | 5 | 1 | 36 |
| namefix | 8 | 5 | 0 | 0 | 13 |
| compaction | 13 | 7 | 0 | 0 | 20 |
| s0 | 2 | 1 | 0 | 0 | 3 |
| ALL STUDIES | 196 | 132 | 45 | 33 | 406 |

### (a) verdict by model (agree = the model's next successful call on that short name used the resolution; differ = a different entity; no_later_use = never used successfully)
| model | agree | differ | no_later_use |
|---|---:|---:|---:|
| bonsai-2:4b | 120 | 0 | 76 |
| lfm3:1.7b | 121 | 0 | 11 |
| qwen3.5:9b | 44 | 0 | 1 |
| gpt-oss:20b | 30 | 0 | 3 |

Request distance (fire to next successful call on that name), median 2, mean 2.11. Bar: {'fires_ge_10': True, 'models_ge_2': True, 'differ_zero': True, 'passes': True}.

## (b) Partial-match exposure events (list/pattern call, absolute name, no exact match, >= 1 partial match)
| study | bonsai-2:4b | lfm3:1.7b | qwen3.5:9b | gpt-oss:20b | all |
|---|---:|---:|---:|---:|---:|
| pilot | 4 | 1 | 0 | 2 | 7 |
| ALL STUDIES | 4 | 18 | 1 | 10 | 33 |
| round1 | 0 | 2 | 0 | 2 | 4 |
| round2 | 0 | 8 | 0 | 0 | 8 |
| fairness | 0 | 2 | 0 | 2 | 4 |
| ablation | 0 | 2 | 0 | 1 | 3 |
| namefix | 0 | 1 | 1 | 0 | 2 |
| compaction | 0 | 1 | 0 | 3 | 4 |
| s0 | 0 | 1 | 0 | 0 | 1 |

Events 33 in 32 episodes. Final answer names an exposed partial match: 9 events (supported episodes among all events: 19 of 33). Answer names the typed, non-existent name: 19 events. Partial match is part of the fixture truth: 7 events.

## (c) Finish tool: ending class and supported rate
### FULL-type arms (pilot C1, round1 C1, round2 CONTROL, ablation FULL, compaction FULL), by model
| model | ending | episodes | supported | rate |
|---|---|---:|---:|---:|
| bonsai-2:4b | final_answer | 91 | 69 | 0.7582 |
| bonsai-2:4b | none | 12 | 0 | 0.0 |
| bonsai-2:4b | text | 1 | 0 | 0.0 |
| lfm3:1.7b | text | 5 | 3 | 0.6 |
| lfm3:1.7b | final_answer | 97 | 79 | 0.8144 |
| lfm3:1.7b | none | 2 | 0 | 0.0 |
| qwen3.5:9b | final_answer | 104 | 104 | 1.0 |
| gpt-oss:20b | final_answer | 70 | 65 | 0.9286 |
| gpt-oss:20b | text | 29 | 26 | 0.8966 |
| gpt-oss:20b | none | 5 | 0 | 0.0 |
| ALL | text | 35 | 29 | 0.8286 |
| ALL | final_answer | 362 | 317 | 0.8757 |
| ALL | none | 19 | 0 | 0.0 |

### By group, study/arm (all models)
| group | study/arm | ending | episodes | supported |
|---|---|---|---:|---:|
| FULL-type | ablation/FULL | final_answer | 37 | 33 |
| FULL-type | ablation/FULL | text | 3 | 3 |
| FULL-type | compaction/FULL | final_answer | 37 | 31 |
| FULL-type | compaction/FULL | text | 2 | 1 |
| FULL-type | compaction/FULL | none | 1 | 0 |
| FULL-type | pilot/C1 | text | 7 | 5 |
| FULL-type | pilot/C1 | final_answer | 71 | 65 |
| FULL-type | pilot/C1 | none | 2 | 0 |
| FULL-type | round1/C1 | final_answer | 74 | 65 |
| FULL-type | round1/C1 | none | 3 | 0 |
| FULL-type | round1/C1 | text | 3 | 2 |
| FULL-type | round2/CONTROL | final_answer | 143 | 123 |
| FULL-type | round2/CONTROL | none | 13 | 0 |
| FULL-type | round2/CONTROL | text | 20 | 18 |
| no finish tool | ablation/NO_FINISH | text | 39 | 29 |
| no finish tool | ablation/NO_FINISH | none | 1 | 0 |
| no finish tool | fairness/E0 | text | 73 | 60 |
| no finish tool | fairness/E0 | none | 7 | 0 |
| no finish tool | fairness/E1 | text | 75 | 65 |
| no finish tool | fairness/E1 | none | 5 | 0 |
| no finish tool | s0/S0 | text | 52 | 40 |
| no finish tool | s0/S0 | none | 28 | 0 |
| other arms offering final_answer | ablation/NO_MENU | final_answer | 35 | 27 |
| other arms offering final_answer | ablation/NO_MENU | text | 4 | 3 |
| other arms offering final_answer | ablation/NO_MENU | none | 1 | 0 |
| other arms offering final_answer | ablation/NO_PRECHECK | final_answer | 38 | 35 |
| other arms offering final_answer | ablation/NO_PRECHECK | text | 2 | 2 |
| other arms offering final_answer | ablation/NO_SOFT_ERRORS | final_answer | 33 | 32 |
| other arms offering final_answer | ablation/NO_SOFT_ERRORS | none | 5 | 0 |
| other arms offering final_answer | ablation/NO_SOFT_ERRORS | text | 2 | 2 |
| other arms offering final_answer | compaction/COMPACT | final_answer | 36 | 31 |
| other arms offering final_answer | compaction/COMPACT | text | 3 | 2 |
| other arms offering final_answer | compaction/COMPACT | none | 1 | 0 |
| other arms offering final_answer | namefix/NAMEFIX | final_answer | 57 | 47 |
| other arms offering final_answer | namefix/NAMEFIX | text | 7 | 7 |
| other arms offering final_answer | pilot/A1 | none | 23 | 0 |
| other arms offering final_answer | pilot/A1 | text | 57 | 47 |
| other arms offering final_answer | pilot/C1+FN | final_answer | 70 | 61 |
| other arms offering final_answer | pilot/C1+FN | text | 8 | 6 |
| other arms offering final_answer | pilot/C1+FN | none | 2 | 0 |
| other arms offering final_answer | pilot/C1+H1e | final_answer | 64 | 59 |
| other arms offering final_answer | pilot/C1+H1e | text | 10 | 9 |
| other arms offering final_answer | pilot/C1+H1e | none | 6 | 0 |
| other arms offering final_answer | pilot/C1+H1n | final_answer | 13 | 0 |
| other arms offering final_answer | pilot/C1+H1n | text | 2 | 0 |
| other arms offering final_answer | pilot/C1+H1n | none | 1 | 0 |
| other arms offering final_answer | pilot/C1+H2 | final_answer | 75 | 66 |
| other arms offering final_answer | pilot/C1+H2 | none | 4 | 0 |
| other arms offering final_answer | pilot/C1+H2 | text | 1 | 0 |
| other arms offering final_answer | pilot/C1+H7 | final_answer | 58 | 32 |
| other arms offering final_answer | pilot/C1+H7 | none | 16 | 0 |
| other arms offering final_answer | pilot/C1+H7 | text | 6 | 3 |
| other arms offering final_answer | pilot/M0 | final_answer | 73 | 65 |
| other arms offering final_answer | pilot/M0 | text | 4 | 4 |
| other arms offering final_answer | pilot/M0 | none | 3 | 0 |
| other arms offering final_answer | round1/C1+AG | final_answer | 78 | 70 |
| other arms offering final_answer | round1/C1+AG | none | 2 | 0 |
| other arms offering final_answer | round1/C1+AG+LA | final_answer | 76 | 69 |
| other arms offering final_answer | round1/C1+AG+LA | none | 3 | 0 |
| other arms offering final_answer | round1/C1+AG+LA | text | 1 | 0 |
| other arms offering final_answer | round1/C1+LA | final_answer | 71 | 64 |
| other arms offering final_answer | round1/C1+LA | none | 4 | 0 |
| other arms offering final_answer | round1/C1+LA | text | 5 | 3 |
| other arms offering final_answer | round2/SWEEP | final_answer | 151 | 131 |
| other arms offering final_answer | round2/SWEEP | none | 8 | 0 |
| other arms offering final_answer | round2/SWEEP | text | 15 | 13 |

Round-1 bare-text nudge result is quoted in the report from `decisions/2026-11-17-finish-gate-check.md`, not recomputed.

## (d) D1 needle-missed episodes (failed, answer wrong, every support fact present by the scorer's rule)
| study | bonsai-2:4b | lfm3:1.7b | qwen3.5:9b | gpt-oss:20b | all |
|---|---:|---:|---:|---:|---:|
| pilot | 16 | 18 | 3 | 4 | 41 |
| ALL STUDIES | 62 | 76 | 7 | 14 | 159 |
| round1 | 9 | 11 | 0 | 3 | 23 |
| round2 | 10 | 20 | 0 | 2 | 32 |
| fairness | 8 | 10 | 1 | 1 | 20 |
| ablation | 6 | 7 | 1 | 2 | 16 |
| namefix | 6 | 2 | 1 | 1 | 10 |
| compaction | 3 | 4 | 0 | 1 | 8 |
| s0 | 4 | 4 | 1 | 0 | 9 |

D1 159 episodes, 28 distinct (task, model) pairs, models ['bonsai-2:4b', 'gpt-oss:20b', 'lfm3:1.7b', 'qwen3.5:9b']; D0 (no answer, facts present) 44; S (answer exact, fact not read) 19; long (>= 8,000 chars) D1 3 over ['bonsai-2:4b']. Bar: {'episodes_ge_5': True, 'models_ge_2': True, 'passes': True}; long subset alone reaches bar: False.

## (e) Detector counts (all arms; per study, all models)
| detector | ablation | compaction | fairness | namefix | pilot | round1 | round2 | s0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| backend_error_ResponseError | 1 | 0 | 3 | 0 | 11 | 6 | 2 | 3 |
| backend_error_XML_syntax | 1 | 0 | 2 | 0 | 4 | 2 | 0 | 2 |
| harness_rejected_call | 39 | 18 | 0 | 36 | 348 | 68 | 150 | 0 |
| identical_repeated_failed_call | 0 | 7 | 11 | 0 | 23 | 4 | 3 | 5 |
| identical_repeated_ok_call | 97 | 49 | 225 | 1 | 588 | 260 | 528 | 31 |
| long_result | 13 | 5 | 8 | 1 | 33 | 19 | 48 | 3 |
| max_iterations_ending | 0 | 1 | 4 | 0 | 14 | 5 | 15 | 0 |
| mid_text_only_request | 0 | 0 | 0 | 0 | 0 | 13 | 0 | 0 |
| requests_after_long_result | 37 | 23 | 39 | 5 | 121 | 86 | 143 | 4 |
| reread_slash_variant | 2 | 3 | 10 | 0 | 2 | 2 | 16 | 3 |
| tool_not_offered | 0 | 0 | 0 | 0 | 167 | 0 | 0 | 0 |
| write_tool_attempt | 4 | 0 | 61 | 0 | 4 | 0 | 0 | 7 |

Examples (first three traces per detector) are in results.json `e_examples`.

## B0 disagreements (excluded from (c) and (d))

- full_resume2_20261116T132848Z/qwen3.5_9b-stage3/003-h4-SWEEP-qwen3.5_9b-s6: ['supported logged True vs re-scored False']
- full_resume2_20261116T132848Z/gpt-oss_20b-stage3/021-h4-SWEEP-gpt-oss_20b-s5: ['supported logged True vs re-scored False']
