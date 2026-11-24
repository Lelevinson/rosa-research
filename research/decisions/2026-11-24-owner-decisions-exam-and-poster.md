# Owner decisions on the exam, the poster and the paper (Nov 22-24, 2026)

Recorded 2026-11-24 (Asia/Taipei) by Claude Code from the owner's statements of 22-24 November. These are owner decisions, not findings; where a decision rests on a measurement, the measurement is linked and no result is implied. No Stage 1, Stage 2 or Stage 3 result had been looked at when this note was written. Written for teammates who start the poster and the paper: it says what the evaluation is, what the demo is, who does what, and what the lab runs in which order.

## 1. What the paper evaluates, and what the demo is
- **Paper and evaluation = method M only.** The numbers in the paper and on the poster come from method M (short tool menu, structured finish tool, errors as text, answer name fix; one-page record: [METHOD_SUMMARY.md](../METHOD_SUMMARY.md)) against the baselines of the frozen exam protocol ([protocol draft](../studies/final_exam_draft_20261118/PROTOCOL_DRAFT.md)).
- **Martin's merged system is a live demo only.** The merged system (method M plus his bounded macro, a UR5e arm, Gazebo) is shown live. It carries **no numbers** in the paper or on the poster. Describe it as a **simulation demo**; never as "real-life testing" or "real-robot testing" (everything runs in simulation).
- **Method name: not decided.** Use "method M" (or "the method") until the owner names it. Avoid names that look like TRIM or AgenTRIM, to stay clear of existing work with similar names.

## 2. Team roles
- One teammate builds the live demo.
- One teammate writes the paper's **result-independent parts** (background, related work, method description, protocol description, limitations as far as they do not depend on results).
- The owner runs the exam, looks at results only under the rule in section 6, prints the result tables and pastes them into the poster.

## 3. Poster
- **Deadline: Friday 27 November 2026, 16:00.**
- The **results area stays as fixed boxes** (empty frames with the final size); the printed results are pasted in later. The owner prints them. Nothing result-dependent is written into the poster text.
- The exhibition shows the **four core models everywhere** (lfm3:1.7b, qwen3.5:9b, gpt-oss:20b, bonsai-2:4b). **Extra models** (Stage 1 tier 4; the extras of Stage 2 and Stage 3) run after the exhibition and enter the paper, not the poster.

## 4. Lab and laptop priority
Order on the lab: **(1) Stage 1 tier 1**; **(2) Stage 2 when it is frozen** (Stage 1 is paused for it); **(3) Stage 1 tier 2 and tier 3 ablations**; **(4) Stage 3 if the owner says go** (decision Wednesday 25 November 18:00; it is not built before that); **(5) tier 4 later.**
The **laptop stops after Stage 1 tier 1** and is the backup stratum; lab and laptop results are never pooled. Stage 2 cell count (336, two seeds) is provisional until the timing episodes; a third seed only if time allows ([Stage 2 protocol draft](../studies/stage2_protocol_20261124/PROTOCOL_STAGE2_DRAFT.md), [runbook](../studies/stage2_protocol_20261124/RUNBOOK_TIMING_LIVE_CHECK_FREEZE.md)).

## 5. Rule decisions that apply to every look at the data
- **D1: seed checkpoints are integrity-only.** A comparison is computed only on a **complete tier**; an interim look prints counts and integrity checks, never an outcome.
- **Quarantine rule** of [2026-11-23](2026-11-23-stage1-quarantined-cells.md): paired exclusion is primary, the worst case for M is the sensitivity, skipped cells are reported per system, model and cause for each machine. It applies to Stage 2 in the same way.
- Both rules are implemented in the analysis scripts ([Stage 1 revision 3](../studies/analysis_rev3_20261124/analysis_rev3.py), [Stage 2](../studies/stage2_analysis_20261124/analysis_stage2.py)); neither has been run on real rows.

## 6. Who may look at results
**Results are looked at only with explicit owner approval.** The analysis commands refuse to compute a comparison without the approval flag. Counts-only status checks are allowed at any time. Teammates do not open held-out or custodian material; they work from the public documents and the printed results the owner pastes.

## What this note does not decide
The method name; the Stage 3 go or no-go (Wednesday 18:00); the final Stage 2 seed count; the wording of any claim, which waits for the frozen analysis gate.
