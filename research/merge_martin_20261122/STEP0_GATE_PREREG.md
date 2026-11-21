# Step 0 gate: GO / NO-GO on the possible saving (PRE-REGISTERED before measuring)

Written 2026-11-21 (Taipei) by Session B, before the measurement script was written or run.
Data: public dev rows only, `research/studies/action_dev_switch_20261118/RESULTS_LOG.jsonl` (his file, read only).
Labels: this concerns the new parameterized variant `rotate_verified(theta)`. **No M4/G1/D evidence is claimed for it.**
Open answers from Martin's message: L3 (identity check) and L4 (scorer counts a pose read inside the macro) are left as unresolved placeholders. They do not affect step 0. L3 blocks steps 2-3. L4 blocks step 6.

## Threshold (fixed now)
**T = 25% of model requests.**
Why this number, from published figures only (not from my measurement):
1. It equals the pre-registered "good signal" bar in MERGE_PLAN section 5.1 (matched-success requests at least 25% lower). A signal run cannot meet its own bar if the possible saving is below it.
2. His dev report calls a request difference of "about 21%" noise at 64 episodes per arm (`REPORT.md`, frozen reading rule). The signal design has 16 episodes per arm per model (8 tasks x 2 seeds). Scaled by sqrt(n): about 42% for one model, about 24% for three models. So 25% is also about the smallest saving a three-model signal run could tell from noise. Below 25%, a signal run cannot detect the effect.

## Quantity measured: upper bound U (the "possible saving")
Control rows: `phase == "full"`, `arm == "OFF"` (no state line; this matches the default `XM` setting, `ExecutorOptions.attach_post_action_state` off). `ON` rows are a sensitivity check only.
For each control episode i:
- `removable_i = min(verification_calls_i, requests_i - 1)`.
  `verification_calls` = pose reads after a goal was sent (the log's own definition, `REPORT.md` limits). The bundle would return that pose, so the model's own read request goes away. The `- 1` keeps at least the final answer request.
- `U = sum(removable_i) / sum(requests_i)`.
- Computed (a) for qwen3.5:9b alone (primary model), (b) pooled over the four models, (c) per model for information.
- Infrastructure rows (`infrastructure == true`) are excluded and counted.

Also reported, not used for the gate:
- **R (conservative):** same, but R2 episodes (task `R2`, where the position read is the answer's source) are counted as 0 removable.
- A per-model and per-task table, and the number of episodes with `removable_i > 0`.

## Rule
- **GO** if U (qwen3.5:9b) >= 25% **and** U (pooled) >= 25%.
- **NO-GO** otherwise. Then: stop, recommend option C (keep the methods separate), report to Martin. Steps 1 to 7 are not started.
- If GO but R < 25%, GO is kept (the gate is on U, the generous bound) and the gap is stated in the report.
- No change to T, the definition, or the control rows after seeing the numbers. A different reading is reported separately and labelled post hoc.
