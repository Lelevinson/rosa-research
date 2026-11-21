# Owner decisions of 2026-11-20/21 (idea search) and the studies behind them

Recorded 2026-11-21 (Asia/Taipei) by Claude Code from the owner's instruction file `2026-11-21_CC_CONTEXT_AND_TEAMMATES.md`. Wording of each decision is the owner's, as relayed; evidence lines are from the linked reports. **All evidence is development-set only (18 dev tasks, 4 models, saved or laptop runs); none is a held-out result.**

## Decisions
1. **Answer name fix (name-rewrite v2 on the final answer): ADOPTED into our method as a minor supporting part** (owner, 2026-11-20 19:33: adopt if tested and never negative).
   - Evidence (dev only): offline 2026-11-16 (+3 supported); live 2026-11-17 (54 -> 62 of 64); replay on fresh seeds 2026-11-20 (243 -> 252 of 288, 0 harm); the 1,832 saved episodes: 0 down, 19 up.
   - Limits: dev only; 7 of the 9 fresh-seed gains are in the designed nf_* tasks.
   - Handling: report rewritten answers as their own group; ablate it.
2. **`blacklist: ""` is treated as not given for optional array arguments** (decided 2026-11-20/21). An executor hygiene fix for ALL arms, like the lossless argument coercion of 2026-11-19; **not a method claim.** **Not yet implemented**: to be implemented in the exam-preparation step, not on the night of 2026-11-20/21. Sizing: 38 rejected calls in 38 of 432 P1+P3 episodes, all gpt-oss, saved-max 38 requests = 1.46% ([empty errors report](../studies/empty_errors_20261120/REPORT.md)).
3. **Not adopted / closed for this freeze:**
   - list values in `param_list` results: live class C by the frozen rule (supported 108 vs 123), post hoc class B; the drop is driven by the scorer crediting parameter facts only from `param_get` rows ([report](../studies/listval_live_20261120/REPORT.md));
   - input name binding: harm (absent entities made to look present; sizing FAIL-HARM) ([report](../studies/idea_search_20261120/claude_lane/REPORT.md));
   - reverse lookups in one call: size (saved-max 41 requests = 2.48%, bar 50), same report;
   - no-progress stop: harm in recover-after-failure and scripted-change runs, same report;
   - informative empty errors: one task only (v2 = 67% of the empty errors) and the replacement sentence would be false for lfm3's empty errors on names that exist ([report](../studies/empty_errors_20261120/REPORT.md)).
4. **Plan.** Codex independent proposals are the last idea input; a proposal must pass offline sizing by **Saturday 2026-11-21 12:00** or it does not enter; teammates' ideas are screened by the same rule; idea freeze Saturday midnight; the exam is Sunday 2026-11-22 on the lab computer.
5. **Exam-validity flag.** lfm3 got empty errors on names that exist (possibly transient ROS failures; 22 of its 26 empty errors in P1+P3, all in loss-map block_0003, seeds 7-8). **Check on the lab before the exam.** This is a hypothesis, not tested.

## Supporting measurements of 2026-11-20 (descriptive, dev only)
- [Loss map](../studies/loss_map_20261120/REPORT.md): 288 episodes, supported 243, 1,655 requests, 828 above the task floors.
- [Derailment study](../studies/derailment_20261120/REPORT.md): 206 of 432 episodes (P1+P3 FULL) have a first wasted request; 64 of them at request 1; trigger table, hand reading, post-hoc clusters (gpt-oss list-tool `blacklist: ""` rejection in 39 first requests; bonsai `service_info cedar_reset` on task v2).
- Not touched by these decisions: the lab, exam queue specs, production defaults.
