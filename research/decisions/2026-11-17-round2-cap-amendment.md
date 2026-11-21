# Amendment: round-2 iteration-cap endings

2026-11-17, Asia/Taipei. This dated amendment supplements the unchanged [round-2 report](../studies/build_round2_20261116/REPORT.md), [analysis](../studies/build_round2_20261116/ANALYSIS.json), and [protocol](../studies/build_round2_20261116/PROTOCOL.md). It does not delete or recalculate any original result. **The 15 cap endings correct a whole-arm descriptive count; they do not change the frozen sweep or rewrite bars, or the reported 14% token figure.**

## What was checked

Using the 352 non-smoke, non-oracle-excluded full-run episode paths from the [development stall recount](2026-11-17-stall-episodes.jsonl), read every `episode_end` and join by exact trace path to the original `ANALYSIS.json` first-fire event list and `RESULTS_LOG.jsonl`. There are **15** explicit `Agent stopped due to max iterations.` endings, all with 40 recorded model responses: **8 CONTROL and 7 SWEEP**, all retained in their arm denominators. None of the 15 appears in the first-fire event set (17 CONTROL and 20 SWEEP). The report's statement that there were zero caps in both whole arms is therefore wrong. Its first-fire table's zero cap count is correct for that narrower set.

The log rows' `aborts` lists contain no literal `iteration limit` for those 15; [`analyze_round2.py`](../studies/build_round2_20261116/analyze_round2.py) checks that marker for `hit_cap`. In these traces the executor instead returned the max-iterations text as `episode_end.answer` with no recorded error. This explains the missed whole-arm count; no failure is inferred from a mere 40 responses without the explicit ending. Raw paths are available through the per-episode file; no held-out evidence is involved.

## Frozen bars and 14% figure

- **V-a, V-b, V-c:** unchanged. Payload identity was a unit check; counts and model membership of the 17/20 first-fire episodes are unchanged.
- **P1, P2, P3:** unchanged, because no capped episode is in either first-fire set. The same 17 CONTROL events sum to 573,105 tokens after firing, mean **33,712.06**; the 20 SWEEP events sum to 577,650, mean **28,882.50**. The relative mean reduction is **14.33%**, reported as approximately 14%. These are post-first-fire tokens per event, not whole-episode or paired savings.
- **P4:** unchanged. No capped episode fired in SWEEP, so the set of fired unsupported episodes requiring hand review remains the same two. This reuses the original hand judgments; it is not a new independent harm review.
- **Shadow rewrite bar:** unchanged as originally written, but its safety interpretation is limited. Of 296 screened answer objects, only **2 answers were actually rewritten**; both were originally unsupported. Thus the denominator for rewrite exposure is 2 and for originally supported answers actually rewritten it is 0. Cap-stop text is not a new submitted answer object, and no rewriting or support flag was recomputed.

The original frozen sweep verdict remains a literal **PASS** under those event-level rules. It does not establish whole-episode savings, equivalence across models, or held-out efficacy. The corrected 15 cap endings are a material whole-population limitation, especially for the models and tasks where they occurred; include them in all-episode cost and outcome tables. See the separate [whole-cost analysis](2026-11-17-list-sweep-whole-cost.md). No inference, ROS, or GPU work was run for this amendment.
