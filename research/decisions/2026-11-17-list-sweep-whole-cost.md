# Sweep completion: whole-episode development cost

2026-11-17. **Interpretation: the total model-cost difference is within observed development variation; the live sweep did more native work and was slower in these runs.** CONTROL and SWEEP each have 176 episodes; same task/model/seed cells do not imply identical model trajectories. The original round-2 report explicitly treats whole-arm totals as descriptive. It did not establish that the observed −41 model requests were caused by sweep. No GPU, inference, or ROS job was run for this recount.

## Whole-arm totals

Count all primary, non-smoke, non-oracle-excluded rows in [`RESULTS_LOG.jsonl`](../studies/build_round2_20261116/RESULTS_LOG.jsonl), including failed and capped episodes. Costs are raw recorded usage/operations, not only after the first firing. `native_ops` is the logger's native operation count; wall time is the sum of episode durations, not elapsed campaign time or GPU utilization.

| Measure | CONTROL | SWEEP | SWEEP difference |
|---|---:|---:|---:|
| Episodes | 176 | 176 | — |
| Supported-complete, scorer v2 | 141 | 146 | +5 |
| Model requests | 1,599 | 1,558 | −41 (−2.6%) |
| Input tokens | 6,573,237 | 6,460,951 | −112,286 (−1.7%) |
| Output tokens | 332,046 | 346,276 | +14,230 (+4.3%) |
| All tokens | 6,905,283 | 6,807,227 | −98,056 (−1.4%) |
| Native operations | 1,964 | 2,117 | +153 (+7.8%) |
| Sum of episode wall seconds | 8,341.36 | 8,966.44 | +625.08 (+7.5%) |
| Explicit max-iteration endings | 8 | 7 | −1 |

The 15 cap endings were kept in all these totals. The [dated cap amendment](2026-11-17-round2-cap-amendment.md) explains why the old report's zero whole-arm cap count was wrong and why none of its first-fire bars changed. Backend errors and the missed scripted change also remain in the original denominators; do not interpret a saved request as successful work without its outcome.

## Extra reads and tool-result size

The live arm recorded **22** `sweep_fire` events, including later firings in already-triggered episodes, and **238** system-initiated extra tool runs across them. The original report's **220** describes the 20 *first-fire* events; both counts are correct for their different denominators. These are tool invocations, not necessarily one underlying native operation each. Their logged attached-result sizes sum to **102,761 characters**, or **25,692 estimated tokens** using the implementation's characters/4 convention; this excludes any over-budget result that was executed but not attached. The extra tool-run count includes such executed work. Reported per-event token estimates are rounded; they are not the model's actual tokenization.

For a whole-arm size proxy, serialize each recorded non-finish `tool_end.output` as its text or JSON with UTF-8 encoding and count bytes. CONTROL: **1,508 outputs, 949,484 bytes**, median 71 and maximum 16,607 bytes. SWEEP: **1,468 outputs, 976,487 bytes**, median 69 and maximum 16,607 bytes. The result stream in SWEEP contains attached sweep results; the total is not an exact wire-size or tokenizer measurement, and its denominator differs because the arms made different numbers of calls. Tool output may recur in several later model requests, already counted in reported input tokens: do not add the byte proxy or estimated extra-result tokens to model usage a second time.

## Cost per supported answer

Denominator is all supported-complete answers within each entire arm; numerators include the cost of unsupported and cap-ending episodes. This ratio is descriptive and does not pair successful cases.

| Measure per supported answer | CONTROL (141) | SWEEP (146) |
|---|---:|---:|
| Model requests | 11.34 | 10.67 |
| Input tokens | 46,619 | 44,253 |
| Output tokens | 2,355 | 2,372 |
| Native operations | 13.93 | 14.50 |
| Episode wall seconds | 59.16 | 61.41 |

The apparent model-token saving is small compared with previously observed sampling effects, while native operations and wall time move the other way. Round 1's apparent request/token savings were not attributable to list use, and its control and pilot differed even with the same cells. Round 2 deliberately enriched two likely-firing tasks and trajectories can diverge before a trigger. The defensible conclusion is **no demonstrated whole-episode cost advantage**, not that the sweep is always more expensive or ineffective. No claim of statistical significance or held-out performance follows.
