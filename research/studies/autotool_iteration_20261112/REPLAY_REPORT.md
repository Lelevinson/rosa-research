# Frozen historical replay results

All numbers below are corrected file-only shadow measurements. The authoritative
JSON and per-boundary predictions are in evidence results/. No inference, tool
execution, causal savings or fresh held-out task performance is measured.

| Split | Episodes | Initial decisions | Continuation boundaries | Actual normal STOP | Unknown/truncated | Read-interface upper bound |
|---|---:|---:|---:|---:|---:|---:|
| Train, turtle-only |18|18|90|18|0|64|
| Development, demo-only |12|12|69|12|0|57|
| Historical mixed validation |6|6|32|6|0|24|
| Temporal transport validation |22|22|78|19|6|53|
| Total |58|58|269|55|6|198|

There are327 recorded model decisions, including28 multicall continuation
boundaries. The unconstrained noninitial tool-bearing bound is208, falling to198
when set_debugging/non-read groups are excluded. This is a purely structural
ceiling, not198 useful/authorized bypasses. It does not prove every initial
decision is inherently unavoidable, only that this continuation policy does not
replace it. Final-answer inference is always retained. Missing model-start/end
pairs:0. Six length-terminated model messages remain UNKNOWN, including three
with tool calls; all remain in denominators.

Raw proposals below include low-confidence/rejected predictions, not admissions.
An argument match requires complete canonical grouped tool+arguments; STOP is
counted separately in interpretation. Rejected missing arguments are never a hit.

| Policy | Mixed proposals/32 | Mixed name hits | Mixed exact action incl STOP | Temporal proposals/78 | Temporal exact incl STOP |
|---|---:|---:|---:|---:|---:|
| Ngram k1 |28|14|2|42|5|
| Ngram k2 |14|5|1|13|0|
| Conditional k1 |16|9|2|0|0|
| Conditional backoff |16|9|2|0|0|
| Constrained parent |23|13|2|27|0|
| Candidate combined |16|9|2|0|0|

Candidate: train68 proposals/90,50 name hits,10 exact; development22/69,9 name
hits,0 exact; mixed16/32,9 name hits,2 exact. **All12 candidate exact matches
are STOP; no complete tool+arguments match in any split.** In mixed validation,
14/16 proposals have missing/ambiguous binding. The two exact STOP examples are
inputs/baseline/08-x1-A-r0/trace.jsonl:58 and23-x1-A-r1/trace.jsonl:58, after
set_debugging. These are behavioral final boundaries, not useful read bypasses.
Candidate temporal support is zero because registry and receipt-shape fingerprints
change. That is a limitation of this conservative implementation, not evidence
that no transferable signal can exist. No threshold was retuned to rescue it.

Fixed C and candidate differ in10 raw boundary proposals, all confined to training;
the equal-capability C_backoff and candidate differ in zero full prediction
objects on all269 boundaries. Both have zero policy admissions. Shadow execution
is disabled independently, so zero executions is not an empirical safety result.
Constrained parent is not full AutoTool and cannot support a parent-performance
claim. On temporal data, k1 makes five false continuation proposals when the real
model stops; k2 and constrained parent each make six. These rejected proposals
illustrate why raw next-name accuracy is insufficient.

Single-removal ablations retain the same backoff, templates and hard safety
filter: remove outcome feature, development complete-action/provenance-risk
calibration, or net-benefit gate. Results are fully logged in summary.json.
None can admit a real action without missing need/authorization information.
They establish no beneficial incremental decision or cost frontier.

Measured candidate fitting plus development calibration is approximately0.06s,
and all269 predictions total approximately0.07s on this host. Exact perf_counter
measurements for every method/boundary are stored. Parsing, historical copying,
literature downloads, unavailable parent embeddings and an unexecuted ROSA run
are not included in those figures. This measurement is overhead only; no model
latency or token saving can be subtracted from it. Comparisons across reports
retain their distinct provider/context settings.

Leakage protections: hashes verified before parsing; episode/family/time split;
state deep-frozen at current model_start; no next output or evaluator truth passed
to prediction; no online validation learning; invalid/truncated messages are
UNKNOWN; parallel calls remain one group. Historical tasks are reused development
material, including temporal validation. Counts do not have independent-binomial
task-risk interpretation. Pre-audit results remain invalidated, not silently replaced.
