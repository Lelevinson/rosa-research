# Finish gate: development-trace check and decision

2026-11-17, Asia/Taipei. **Recommendation: leave the steady C1 loop unchanged.** Of 33 episodes ending in bare text with no `final_answer` call, **25/33 were already supported-complete** under frozen scorer v2.0. Forcing one retry and then marking the episode incomplete could discard valid answers. The existing round-1 nudge did not establish a support gain on its firing cases. This does not show a bounded gate cannot help in another setting.

## What was counted

Read-only CPU recount of the 336 primary C1-type development episodes already identified in [the stall census](2026-11-17-stall-episodes.jsonl): pilot C1 80, round-1 C1 80, and round-2 CONTROL 176. The latter has extra seeds on selected tasks, so pooled percentages are not an independent random sample. For each trace, count a bare-text ending only if the final model response has nonempty text and no tool/invalid-tool calls, the episode returns exactly that text without an error, and there was no `final_answer` tool call anywhere in the episode. Cap-stop messages and backend aborts are not bare model answers. The supported flag is frozen scorer v2; unsupported includes incomplete, wrong, or unsupported, not just formatting failures. All original rows, including known missed-trigger cases, retain their existing flags.

| Model | C1-type episodes | Bare text, no finish call | Of these unsupported/incomplete | Supported |
|---|---:|---:|---:|---:|
| bonsai-2:4b | 84 | 2 | 2 | 0 |
| gpt-oss:20b | 84 | 25 | 2 | 23 |
| lfm3:1.7b | 84 | 6 | 4 | 2 |
| qwen3.5:9b | 84 | 0 | 0 | 0 |
| **Total** | **336** | **33** | **8** | **25** |

By cohort: pilot 8 bare endings / 3 unsupported; round 1 4 / 2; round 2 CONTROL 21 / 3. This is not all episodes without a finish call: cap stops, parser failures and other aborts have different causes and must not be counted as bare answers. A no-finish answer can contain a complete JSON object; the frozen scorer's free-text extraction can correctly support it.

## Round-1 nudge: actual behavior

[`Round1Model._generate`](../studies/build_round1_20261115/round1_harness.py) and the [round-1 report](../studies/build_round1_20261115/REPORT.md) show that a no-tool response gets a corrective message, at most **two** nudges per episode; thereafter the text is accepted. This was bundled with the answer gate, not a test of the new proposed one-message/incomplete rule. Recounting handler events in the 160 primary gate-containing arm traces:

| Arm | Episodes | Nudge events | Nudged episodes | Nudged episodes supported | Nudged episodes unsupported |
|---|---:|---:|---:|---:|---:|
| C1 + answer gate | 80 | 4 | 4 | 4 | 0 |
| C1 + answer gate + list arguments | 80 | 9 | 8 | 6 | 2 |

In the gate-only arm, all four nudged episodes had the same support outcome as their same-cell control, as the report records. The combined arm is not a nudge-only control, and equal seeds did not make trajectories identical. These numbers do not prove the first response was correct, that a retry caused the final result, or that the proposed one-retry cutoff would match the old two-nudge policy. They do show that a gate would affect already-scored-success cases and would change the system under ablation.

## Consequence

Keep the existing base and the four ablation changes in the [updated ablation protocol](2026-11-17-steady-loop-ablation-protocol.md). No new finish gate is added. Separately report bare text, finish calls and cap endings in the ablation; retain any valid bare JSON answer under scorer v2. A future gate would require its own frozen rule and matched evaluation before inclusion, not a silent rewrite of C1.
