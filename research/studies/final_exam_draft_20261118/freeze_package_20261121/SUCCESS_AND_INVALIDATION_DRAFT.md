# Stage 1 success criteria and invalidation rules (DRAFT text for the freeze; not hashed, not frozen)

Source: owner-approved answers 4 and 8 of [PROTOCOL_DRAFT.md](../PROTOCOL_DRAFT.md) section 9c (2026-11-21). The wording below is the text proposed for the freeze document; the freeze copies it unchanged or the owner edits it first.

## Primary claim (it can be wrong)
Population: held-out v2 (76 tasks), the 4 core models (lfm3:1.7b, qwen3.5:9b, gpt-oss:20b, bonsai-2:4b), seeds 1-3, systems EX-M (method M) and E1, all episodes assigned to a cell included (capped, failed and unscored episodes are not dropped). Estimation: cluster bootstrap over tasks (a task carries all its models and seeds), paired on the same (task, model, seed) cells, 95% intervals.
- **(a) Non-inferior correctness:** the lower 95% bound of supported-complete(M) minus supported-complete(E1) is **above -5 percentage points**. Supported-complete uses scorer v2.0 on the answer M actually submitted (the name-fix rewritten answer, reported with its raw-answer score next to it).
- **(b) Cheaper:** the upper 95% bound of the ratio (input + output tokens of M) / (input + output tokens of E1), totals over all assigned episodes, is **below 0.80**.
- **Both (a) and (b) must hold.** If either fails, the claim is reported as not supported, with the interval.
Reasons recorded with the owner's approval: 5 points is just above the detectable difference of about 4 points (draft section 7b, 76 tasks x 12 cells per task); 0.80 is a meaningful saving and is conservative against the development token ratio of 0.40 (draft section 7b, 10 development tasks, illustrative).
Everything else is secondary and labelled so: per-model rows, S0, F, ablations (EX-NO_MENU, EX-NO_FINISH, EX-NO_ERRORTEXT), the name fix scored both ways, extra models (llama3.1:8b, ministral-3:8b, granite4.2:8b; M and E1 only; descriptive), requests per supported completion, failure-class rows including `validation_abort`.

## Capped and invalidation
- **Capped** (for the "with / without capped" totals only) = iteration cap + backend parse error + timeout + no-answer ending, where a stock-executor validation abort (`validation_abort`) is counted as a no-answer ending and keeps its own row.
- **Invalidation classes** as in draft section 4: (a) pre-start reset or fixture failure, re-run once with both runs logged; (b) agent-caused unresolved motion (action tasks only, not Stage 1); (c) post-start oracle or simulator loss: unscored, stays in the denominator.
- **If more than 5% of a system's cells are class (a) or (c), that system's results are flagged in every table.** **If more than 10% of all cells are class (a) or (c), the exam is reported as compromised and is not used for the primary claim.**
- Run once: a cell that made a model request is never re-run. The two strata (lab, laptop) are reported separately and never pooled.
- Lab stratum pre-run gate (Monday; a gate on the machine, not a protocol change): container restarted with `--init` and `lab/check_integrity.sh` clean; transient-failure check of the menu read tools; headless Gazebo/Nav2 timing. If the gate fails the lab stratum does not start and the laptop stratum stands.
