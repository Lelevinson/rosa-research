# PROTOCOL_STAGE1C (frozen before any Stage 1c inference)

Frozen: 2026-11-13. Scope: development evidence only; no mechanism proposal, no novelty claim. Same rules as `PROTOCOL_STAGE1.md` (no edit to `src/rosa/`; the prompt change is the harness subclass `StageROSA`; no API key; strong model only through the existing ChatGPT-plan OAuth path; no unsupported temperature or seed). Revisions after the first inference are listed at the bottom, never edited into this text.

## Question
After deconflicting the prompt (arm A0), Qwen still uses about twice the floor on `t2` and `d1` (6 requests, floor 3). Does gpt-6-luna reach the floor on the same tasks, or is the excess dependency-driven for both?

## Step 1 (offline, done before this freeze)
Relabelled the 12 Stage 1a Qwen A0 episodes (`STAGE1C_RELABEL.md`, `manual_labels_1c.json`) and checked the floors by hand with the actual tool outputs: `t2` = node_list (+ service_list or node_info) | param_get use_sim_time (+ service_info or already in node_info) | final; node_info lists the clear/reset servers with types and the node name comes from node_list. `d1` = topic_info (verbose output gives Node name + Node namespace per endpoint, so full names assemble) | param_get per endpoint | final. Both floors of 3 are achievable; no floor is corrected. Excess of the other floors is unchanged.

## Step 2 design
- Model `gpt-6-luna`, explicit model name, read from the live catalog and recorded; `parallel_tool_calls` true; no temperature or seed; provider-managed context.
- Arm `A0` only, same prompt change, same harness subclass, full 47-tool stock registry, same observation-only guard, ten executor iterations, 240 s per episode.
- Tasks `t1 t2 t3 d1 d2 x1`, exact requests from `vendor/baseline_protocol.json`; same fixture, ROS domain 211 (localhost only), snapshots before, every 6 episodes and after.
- 6 tasks × 2 repeats = **12 episodes**, one pass; each repeat block shuffled with seed **20261113**, schedule saved in the run folder. Stage 1 total becomes 54 episodes (24 + 18 + 12), under the cap of 60. No second batch.
- Scoring unchanged: `vendor/baseline_audit.py` plus the support screen in `score_stage1.py` (including the `publisher`-role handling and flat-object reading already documented). `d2` is reported both as scored (the scorer demands `get_type_description` as a non-parameter service) and as read by hand; the scored result is the primary one.
- Stop rules: ChatGPT-plan access or throttling error, fixture cleanup failure, oracle mismatch, cap reached. Infrastructure losses may be replaced once under a new ID; model failures are never rerun. Fixture verified empty and ROS daemon stopped after the run.
- Metrics per task: floor, Qwen A0 requests, Luna requests, calls per request, supported-complete, native operations, tokens, seconds.

## Decision rule (frozen)
Compare Luna to Qwen A0 per task, requests versus floor, using the Stage 1a Qwen A0 episodes (t2: 6 and 6; d1: 6 and 6):
- **Gap exists:** Luna is at most floor+1 on both `t2` and `d1` in both repeats, while Qwen is at floor+3 or more on them.
- **No gap:** Luna is at floor+2 or more on `t2` or `d1` in at least one repeat per task.
- **Inconclusive:** anything else, or fewer than 10 usable episodes; state what would settle it.
Reading limits: Qwen A0 data are 2 near-duplicate repeats per task at temperature 0; Luna has provider-side sampling. Two repeats per cell cannot support more than the rule above.

## Revisions
(none yet)
