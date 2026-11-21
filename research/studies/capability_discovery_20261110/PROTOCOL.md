# Frozen evaluation protocol — 2026-11-10

Written before mechanism implementation or evaluation. This is a bounded prototype,
not an optimizer or a universal semantic-equivalence test.

## Mechanism and evidence boundary

Use existing LangChain tool metadata, input schemas, optional informative output
schemas, and passively collected structured observations. Match identical field
paths and JSON value types; do not translate names, units, arguments, or requests.
Metadata similarity can propose a pair but cannot validate it. Compare only
identical explicit argument objects in a collector-declared common snapshot.
Require at least 3 distinct argument contexts, at least 2 distinct values, and
no mismatch for empirical support. A later mismatch revokes support. Empirical
support is bounded to recorded observations and is NEVER semantic equivalence.
No inference from opaque CLI strings, acknowledgements, or unsuccessful results.
No LLM, paid API, dependency installation, ROS process, or arbitrary tool probes.
Only reviewed pure local fixture and calculation functions execute. Registry
inspection may import ROS modules but must never dispatch their operations.

## Frozen evaluations

1. Development fixtures: structured aggregate, projection, nested projection,
   unrelated same-shape tool, ambiguous description, renamed field, renamed
   argument, differing numeric type, missing/error results, constant values.
2. A separate extension module introduced only after the engine is frozen:
   at least 8 additional tools, including unseen valid overlaps, unrelated fields,
   misleading descriptions, same-valued different meanings, and delayed drift.
   This is a synthetic extension test, not an independently collected benchmark.
3. All unordered pairs within each registry are scored against semantic labels
   authored only in the evaluation harness. These labels are NEVER engine input.
   A true relation means at least one identical-path same-type information field
   has the same meaning and values over the fixture's intended domain. Report
   renamed fields/arguments as explicit unsupported positive cases too.
4. At least 3 matched inputs for support; disjoint contexts, insufficient/constant
   data, mismatches, stale/changed registrations, duplicate names, errors, opaque
   text, numeric type collisions, and input mutation are negative controls.
5. Inspect the real ROSA registry. Run a pure-calculation subset through normal
   `.invoke`, with diverse including coincident inputs. No native ROS/robot calls.
6. Measure pair-level proposal and empirical-support precision/recall, false
   empirical support, asserted equivalence count and abstention, fallback calls,
   discovery/observation time, extra tool dispatches, LLM calls, and scale at
   10/50/100 synthetic registrations. Include repeated timings (median/p95) and
   call counts. Costs are local overhead, not end-to-end ROSA speedups.

## Stop and decision gates

Do not tune thresholds/fixtures to erase failures. Preserve initial failures and
correct only implementation defects with a disclosed change log. A same-valued
different-meaning negative control must be reported even if it passes empirical
validation. Reject integration as a safe substituting optimizer if such false
support exists or ordinary ROSA lacks enough machine-readable contracts. A
passive diagnostic candidate graph can still be useful. No universal equivalence
claim, autonomous replacement, full optimizer, core changes, commits, or pushes.

## Reproduction

From repository root, use the existing `.venv/bin/python`. The final README/report
will give commands. Save raw pair decisions and costs as JSON, environment and
source fingerprints, and the complete test output. The extension will have its
own source hash and the engine freeze hash before it is evaluated.
