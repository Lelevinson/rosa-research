# Independent check: matched pilot and Forge

2026-11-15. Offline re-score and trace inspection; no inference, ROS execution or installs. Four models × ten tasks × two seeds per arm. Pilot A1 is the stock executor with the A1 prompt; C1 is the fixed loop. Historical arms are not concurrent and A1 has a larger tool menu.

## Recomputed totals

Each score uses frozen scorer v2.0 (`c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9`). The pilot results log and Forge result ledger identify trace paths, assigned cells and excluded infrastructure attempts, not the scores or costs used here. Each trace was SHA-256 checked against its ledger, parsed independently, and scored against the original task JSON. Requests count `model_start`; tokens sum `model_end.usage`, including failed episodes. No summary JSON was used.

| Arm | Model | Cells | Supported | Requests | Input tokens | Output tokens |
|---|---|---:|---:|---:|---:|---:|
| A1 | lfm3:1.7b | 20 | 15 | 135 | 1,028,694 | 61,733 |
| A1 | qwen3.5:9b | 20 | 19 | 86 | 554,213 | 9,523 |
| A1 | gpt-oss:20b | 20 | 7 | 54 | 207,182 | 10,631 |
| A1 | bonsai-2:4b | 20 | 6 | 197 | 1,391,619 | 17,828 |
| A1 | All | 80 | 47 | 472 | 3,181,708 | 99,715 |
| C1 | lfm3:1.7b | 20 | 17 | 105 | 408,791 | 45,905 |
| C1 | qwen3.5:9b | 20 | 20 | 87 | 242,071 | 9,672 |
| C1 | gpt-oss:20b | 20 | 20 | 105 | 203,554 | 20,020 |
| C1 | bonsai-2:4b | 20 | 13 | 189 | 726,761 | 19,728 |
| C1 | All | 80 | 70 | 486 | 1,581,177 | 95,325 |
| Forge | lfm3:1.7b | 20 | 12 | 213 | 689,761 | 46,431 |
| Forge | qwen3.5:9b | 20 | 18 | 102 | 299,469 | 7,725 |
| Forge | gpt-oss:20b | 20 | 17 | 133 | 316,953 | 19,720 |
| Forge | bonsai-2:4b | 20 | 8 | 195 | 818,481 | 17,149 |
| Forge | All | 80 | 55 | 643 | 2,124,664 | 91,025 |

Total tokens: A1 3,281,423; C1 1,676,502; Forge 2,215,689. Forge has usage records for 641 of 643 starts, so its token count is a lower bound; A1 and C1 have a model-end usage record for each start. A recorded usage value is provider-reported, not an independent tokenization measurement.

These requested per-model support counts agree with the scorer decision and WASTE_ANALYSIS supported-episode counts; the full per-model counts and costs agree with Forge REPORT.md. WASTE_ANALYSIS token and request means are for supported episodes and its 44 matched-success pairs, so they have a different denominator from the all-80 costs here. No discrepancy in the comparable requested numbers was found. This check did not reproduce every waste flag or every other arm in those documents.

## All 25 Forge failures

Each row is an independent reading of the raw `episode_end` and scorer output. Links point to the original trace; s1/s2 is the seed. Causes are descriptive and need not be mutually exclusive. The changing-fixture missed trigger remains counted in the frozen denominator.

| Model | Task / seed | Observed failure | Trace |
|---|---|---|---|
| lfm3:1.7b | h4 / 1 | Malformed answer keys and extra gain | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/lfm3_1.7b-stage3/002-h4-Forge-s1/trace.jsonl#L103) |
| lfm3:1.7b | p3 / 1 | Wrong or unsupported answer: /first: '/plant32/quartz' != '/plant32/beacon'; /second: '/plant32/beacon' != '/plant32/juniper' | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/lfm3_1.7b-stage3/003-p3-Forge-s1/trace.jsonl#L68) |
| lfm3:1.7b | u3 / 1 | Short node names in answer | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/lfm3_1.7b-stage3/007-u3-Forge-s1/trace.jsonl#L108) |
| lfm3:1.7b | e1h_abs_1 / 2 | Wrong decoy node reported present | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/lfm3_1.7b-e1h/013-e1h_abs_1-Forge-s2/trace.jsonl#L54) |
| lfm3:1.7b | e1h_amb_1 / 2 | No answer: iteration cap | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/lfm3_1.7b-e1h/014-e1h_amb_1-Forge-s2/trace.jsonl#L367) |
| lfm3:1.7b | e1h_abs_1 / 1 | Wrong decoy node reported present | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/lfm3_1.7b-e1h/015-e1h_abs_1-Forge-s1/trace.jsonl#L73) |
| lfm3:1.7b | e1h_abs_2 / 1 | Wrong decoy node reported present | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/lfm3_1.7b-e1h/016-e1h_abs_2-Forge-s1/trace.jsonl#L78) |
| lfm3:1.7b | e1h_abs_2 / 2 | Wrong decoy node reported present | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/lfm3_1.7b-e1h/017-e1h_abs_2-Forge-s2/trace.jsonl#L63) |
| qwen3.5:9b | v2 / 1 | Wrong or unsupported answer: /node: '/plant32/quill' != '/plant32/wharf' | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/qwen3.5_9b-stage3/023-v2-Forge-s1/trace.jsonl#L27) |
| qwen3.5:9b | e1h_amb_1 / 1 | Malformed JSON: unquoted keys | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/qwen3.5_9b-e1h/036-e1h_amb_1-Forge-s1/trace.jsonl#L57) |
| gpt-oss:20b | h4 / 2 | Malformed outer JSON; extractor selects inner gains | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/gpt-oss_20b-stage3/045-h4-Forge-s2/trace.jsonl#L126) |
| gpt-oss:20b | e1h_chg_1 / 2 | Final 30; scripted change missed on relative-name read | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/gpt-oss_20b-e1h/050-e1h_chg_1-Forge-s2/trace.jsonl#L36) |
| gpt-oss:20b | e1h_abs_1 / 2 | Wrong decoy node reported present | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/gpt-oss_20b-e1h/056-e1h_abs_1-Forge-s2/trace.jsonl#L36) |
| bonsai-2:4b | h4 / 2 | Wrong or unsupported answer: /gains//plant32/dune: missing; /gains//plant32/oasis: 59 != 89 | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/bonsai-2_4b-stage3/060-h4-Forge-s2/trace.jsonl#L180) |
| bonsai-2:4b | u3 / 2 | Wrong or unsupported answer: /upstream: '/plant32/harbor_t' != '/plant32/quill' | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/bonsai-2_4b-stage3/061-u3-Forge-s2/trace.jsonl#L333) |
| bonsai-2:4b | v2 / 1 | Wrong or unsupported answer: /node: '/plant32/cedar' != '/plant32/wharf'; /type: 'string' != 'std_srvs/srv/Trigger' | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/bonsai-2_4b-stage3/062-v2-Forge-s1/trace.jsonl#L108) |
| bonsai-2:4b | h4 / 1 | Wrong or unsupported answer: /gains//plant32/oasis: missing; /gains//plant32/zephyr: 92 != 74 | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/bonsai-2_4b-stage3/063-h4-Forge-s1/trace.jsonl#L285) |
| bonsai-2:4b | p3 / 2 | Wrong or unsupported answer: /setpoint: 694 != 873 | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/bonsai-2_4b-stage3/065-p3-Forge-s2/trace.jsonl#L37) |
| bonsai-2:4b | v2 / 2 | Wrong or unsupported answer: /node: '/plant32/cedar_reset' != '/plant32/wharf' | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/bonsai-2_4b-stage3/067-v2-Forge-s2/trace.jsonl#L189) |
| bonsai-2:4b | e1h_abs_1 / 2 | Wrong decoy node reported present | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/bonsai-2_4b-e1h/069-e1h_abs_1-Forge-s2/trace.jsonl#L45) |
| bonsai-2:4b | e1h_abs_1 / 1 | Wrong decoy node reported present | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/bonsai-2_4b-e1h/070-e1h_abs_1-Forge-s1/trace.jsonl#L45) |
| bonsai-2:4b | e1h_abs_2 / 1 | Wrong decoy node reported present | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/bonsai-2_4b-e1h/072-e1h_abs_2-Forge-s1/trace.jsonl#L45) |
| bonsai-2:4b | e1h_chg_2 / 1 | Wrong or unsupported answer: /meter_flow: 0 != 725 | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/bonsai-2_4b-e1h/075-e1h_chg_2-Forge-s1/trace.jsonl#L97) |
| bonsai-2:4b | e1h_abs_2 / 2 | Wrong decoy node reported present | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/bonsai-2_4b-e1h/076-e1h_abs_2-Forge-s2/trace.jsonl#L45) |
| bonsai-2:4b | e1h_chg_2 / 2 | No answer: iteration cap | [trace](../../_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z-resume1/bonsai-2_4b-e1h/078-e1h_chg_2-Forge-s2/trace.jsonl#L372) |

### Format and causal interpretation

Two of 25 failures are malformed JSON strings that prevent the frozen extractor from obtaining the intended full object: Qwen `e1h_amb_1` seed 1 (unquoted keys) and gpt-oss `h4` seed 2 (malformed outer object). Both were submitted through `respond.message`, whose schema accepts a string; its successful terminal call preserved the malformed text. In both cases the raw terminal text contains the expected facts. The lfm3 h4 leading-space keys and lfm3 u3 short node values are additional answer-content/field-format errors in syntactically valid JSON, but are not JSON serialization failures.

**Causality is not identified:** 2/25 observed malformed-JSON failures are compatible with the string interface allowing malformed content through; 0/25 can be proven from these traces alone to have been caused by choosing a string instead of a typed object. There is no matched intervention that isolates the finish schema, and C1 and Forge differ in other ways. No score has been repaired or overridden.

The unchanged frozen scoring rule expects the post-change value even for the Forge gpt-oss changing episode where the scripted hook did not fire; the trace instead returned the last observed value 30. Treat this as fixture validity evidence, not proof of stale caching. These results describe synthetic development tasks; they do not establish statistical significance or generalization.
