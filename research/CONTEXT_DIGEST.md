# Context digest

A short map of durable decisions, constraints and closed directions, each with its dated source. It is **not** the mandatory preflight: before a research proposal, algorithm, implementation or experiment, still read [AGENTS.md](../AGENTS.md) and canonical [context](ROSA_RESEARCH_CONTEXT.md) §§0–4, 12, 14. It does not replace any gate, and it is a summary, not evidence. Update only after a material state change. Each section carries a last-verified date: the day its links and claims were checked against the source, not the day the source was written.

## Objective and deadline (last verified 2026-11-13)
- Framework-level algorithmic or meaningfully incremental improvement of tool-calling efficiency in ROSA; supported, complete, safe answers are conditions; the LLM keeps semantic judgment. [context §0, §1](ROSA_RESEARCH_CONTEXT.md)
- Presentation 2026-12-02 (Taiwan). No main algorithm is selected; a NO-GO on one hypothesis is not proof that no opportunity exists. [context §0, §14.1](ROSA_RESEARCH_CONTEXT.md)

## Gates and rules (last verified 2026-11-13)
- Five-question gate before any recommendation; decision record (opportunity, mechanism, novelty, fair evaluation, smallest decision-changing action with stop rule). A material unknown means `BLOCKED / NOT YET JUSTIFIED`. [§12.2, §14.2](ROSA_RESEARCH_CONTEXT.md), [rules](RESEARCH_RULES.md)
- Labels: F measured, R reported, L literature, H hypothesis, P proposal. A trace entry or equal output is not proof of success. [§12.1](ROSA_RESEARCH_CONTEXT.md)
- Investigation, prototype, experiment, review and framework integration are separate authorizations; nothing enters `src/rosa/` without explicit approval. [AGENTS.md](../AGENTS.md), [START_HERE](START_HERE.md)
- Strong ordinary control must really batch, reuse and parameterize; the stock prompt forbids batching, so the control must replace it, with adoption shown. [§0, §14.2](ROSA_RESEARCH_CONTEXT.md)
- Do not change scenarios or criteria to improve results; report protocol revisions separately. Keep failures and negative evidence. [AGENTS.md](../AGENTS.md)

## Baseline facts (last verified 2026-11-14)
- Stock `prompts.py` tells the agent not to batch: a prompt prohibition, not an API limit; known before 2026-11-10, not a new discovery. [§0](ROSA_RESEARCH_CONTEXT.md)
- Baseline arms B and C also added a contradicting "use independent tool calls together", so their zero batching does not measure the model (F, 58 traces). [headroom Stage 0](studies/headroom_diagnostic_20261112/REPORT.md)
- Deconflicting the prompt cut requests 74 to 63 (−15%) on six tasks, with native operations +25%; call count held at 3 to 4 requests up to 32 entities. Development evidence only. [Stage 1](studies/headroom_diagnostic_20261112/REPORT_STAGE1.md)
- Strong model (gpt-6-luna) used 45 requests vs Qwen 63 on the same cells and still showed serial first requests in one of two `t2` repeats. [Stage 1c](studies/headroom_diagnostic_20261112/REPORT_STAGE1C.md)
- Stage 3 (generated fixture, 12 dependent tasks) found excess over the floor on arm A0: Qwen 85.4%, Luna 25.3%, 95–100% avoidable. Stage 3b removed the three discovery-first stock messages (arm A1): Qwen 49.0%, Luna 14.3%, support unchanged. Frozen rules: “room” over A0, then “weak-model room remains” over A1; synthetic, A0 and A1 in different sessions, method need not established. [Stage 3](studies/headroom_diagnostic_20261112/REPORT_STAGE3.md), [Stage 3b](studies/headroom_diagnostic_20261112/REPORT_STAGE3B.md)

## Released Forge comparison (last verified 2026-11-15)
- Owner-authorized 80-cell development pilot, common frozen scorer v2: Forge 55/80 supported, historical C1 70/80, A1 47/80; Forge 643 requests and 2,215,689 reported tokens (two calls lack usage). Matched per-model wire think:false; gpt-oss still emits raw thinking. Separate thinking-on smoke; no new method or held-out inference. [report](studies/forge_baseline_20261115/REPORT.md), [canonical §24](ROSA_RESEARCH_CONTEXT.md)
- Fixture validity: exact absolute-command watcher misses valid relative parameter reads in one Forge and two A1 changing-task cells; C1's 16 changes fired. Frozen failures retained, not corrected or excluded. No model-rerun replacements; nine fixture cleanups passed, one interrupted post-oracle unavailable. [event audit](studies/forge_baseline_20261115/FIXTURE_EVENT_AUDIT.json)

## Closed or negative directions (last verified 2026-11-13)

Scoped failures, not impossibility proofs; do not relabel and restart them.
- **Learned speculative result expansion:** kill bar fired (9.5% saving; static top-1 15.9%), 2026-11-13. [Stage 2a](studies/headroom_diagnostic_20261112/REPORT_STAGE2A.md)
- **AutoTool family:** 0 complete matches over 269 boundaries; ties equal-feature ordinary backoff; live admission blocked, 2026-11-12. [blocker](studies/autotool_iteration_20261112/BLOCKER_AND_NEXT_DECISION.md), [review](studies/autotool_iteration_20261112/INDEPENDENT_REVIEW.md)
- **Terse narration arms** lost supported fields, 2026-11-11. [report](studies/action_narration_20261111/REPORT.md)
- **Native read:** transport engineering benefit; no adaptive promotion, 2026-11-11. [report](studies/native_read_investigation_20261111/REPORT.md)
- **GPT coverage:** 92/92 fields but 7/10 strict completion, 2026-11-11. [report](studies/gpt_coverage_investigation_20261111/REPORT.md)
- **CPAW:** rejected as main algorithm; 0/47 default eligibility in an isolated synthetic study, 2026-11-10. [report](studies/cpaw_prototype_20261110/REPORT.md), [context §14.1](ROSA_RESEARCH_CONTEXT.md)
- **Capability discovery:** observer only, no equivalence authority, 2026-11-10. [report](studies/capability_discovery_20261110/REPORT.md)
- **Earlier explorations** (JTVR, tool-menu retrieval, structured `$ref` planner, CodeAct subset, graph controllers, evidence packing and others): scoped gaps. [context §0](ROSA_RESEARCH_CONTEXT.md)
- **Rounds R5–R28:** conditional gains at most; strong ordinary controls often tie; none promoted. [index](STUDY_INDEX.md)
- **Martin bounded macros:** teammate reference, not our contribution. [context §14.1](ROSA_RESEARCH_CONTEXT.md)

## Known evidence gaps (last verified 2026-11-14)
- Original 64 structured-dependency traces are missing; the reconstructed ZIP is not original evidence. [inventory](studies/autotool_iteration_20261112/HISTORY_AND_SOURCE_INVENTORY.md)
- Mission C report not found; some archive and `previous` paths exist only outside this checkout. [index](STUDY_INDEX.md)
- Headroom Stage 2a and Stage 1c have no independent review recorded; Stage 1 hash manifest covers Stage 1 only. [index row](STUDY_INDEX.md)
- Stage 3 has no independent review, uses one generated fixture, and tests only A0; it does not establish method need over the strongest ordinary prompt. [Stage 3](studies/headroom_diagnostic_20261112/REPORT_STAGE3.md)

## Open (no authorization; last verified 2026-11-14)
- **Stages 3, 3b, 3c and 3d are complete.** Stage 3d ran Qwen with six generic prompt sentences (A2): supported 20/24 vs 24/24, so the frozen rule stops at correctness; bare-name recovery gone, repeats unchanged (22 -> 22), two unrequested service-call attempts and two wrong setpoints. [Stage 3d](studies/headroom_diagnostic_20261112/REPORT_STAGE3D.md). Stage 3c (offline replay, no model run) found 43 of Qwen's 47 A1 excess requests removable and judged preventable by an ordinary prompt sentence (untested); frozen branch “prompt control, not a method”, which flips if repeats and short-name recovery turn out not to respond to a sentence. [Stage 3c](studies/headroom_diagnostic_20261112/REPORT_STAGE3C.md). After the strongest ordinary prompt control tried (A1) the weak model still shows repeats and recovery after short node names (49.0% excess) while the strong model is at 14.3%. Whether that weak-model residual is the target is undecided; no method or next stage is authorized. [ACTIVE_STATE](ACTIVE_STATE.md), [Stage 3b report](studies/headroom_diagnostic_20261112/REPORT_STAGE3B.md)
- A natural, non-synthetic witness that would reopen AutoTool-style admission. [blocker](studies/autotool_iteration_20261112/BLOCKER_AND_NEXT_DECISION.md)

## Sync and storage (last verified 2026-11-13)
- All of `research/` is currently ignored by a local Git exclude rule (checked 2026-11-13), so Git neither tracks nor shares these files and `git diff` shows no changes to them. The mirror to Claude Desktop is one-way and manual. [START_HERE](START_HERE.md)
- Do not delete evidence or backups without verified independent recoverability; same-filesystem copies are not disaster recovery. [START_HERE](START_HERE.md)
