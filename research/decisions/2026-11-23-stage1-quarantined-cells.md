# Owner decision on quarantined Stage 1 cells

Recorded on 2026-11-23, Asia/Taipei, before any Stage 1 result look. Applies to the Method M (EX-M) versus E1 comparison within each machine's separate Stage 1 run.

1. **Primary analysis — paired exclusion.** A pair consists of the M and E1 cells for the same task, model, and seed. If either cell is quarantined, remove both cells from the primary comparison and its denominator. Count an affected pair once even if both cells are quarantined.
2. **Sensitivity analysis — worst case for M.** For the binary task outcome, assign failure to each quarantined M cell and success to each quarantined E1 cell. Retain the observed outcome of any completed counterpart. When both cells in a pair are quarantined, assign failure to M and success to E1.
3. **Required reporting.** Always report quarantine cell counts by system × model and cause class, separately for laptop and lab. Show the number of pairs excluded and the denominator used for the primary comparison.

This records the owner decision required by [Rev 2, item 2, rule 4](../studies/exam_dress_rehearsal_20261122/REV2_FREEZE_DRAFT.md#item-2-crash-re-run-rule-final-text-d2-and-d3-applied-implemented-in-queue_core_rev2py). The current analysis gate still requires a complete tier. This documentation change does not execute analysis or alter the frozen runner, scoring code, or existing run records.
