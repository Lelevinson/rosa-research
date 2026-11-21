# PROTOCOL_STAGE3C (frozen before any Stage 3c label)

Frozen: 2026-11-14. Source: the user-authorized addendum `ROSA_stage3c_offline_residual_addendum.md` (in the mirrored folder `Claude outputs/`). Changes after the first label go under "Revisions" at the bottom, never in place. Development evidence only: no novelty claim, no mechanism proposed, no method selected.

## 1. Question and limits
**Could a general, non-task-specific signal have prevented the excess requests that Stage 3b left under arm A1?** This is an upper bound from replay. A replay cannot show what the model would have done, so it cannot show that a method works. It only shows whether a method has anything to aim at.

- Saved traces only: `research/_artifacts/runs/headroom_diagnostic_20261112/stage3b_20261113T155721Z/`. No model runs, no Ollama or provider calls, no API key, no ROS fixture.
- New files only, in this study folder. `src/rosa/`, baselines, `AGENTS.md` and every Stage 0 to 3b file are not edited. The only existing files edited are the shared-state files the addendum names in Step 5 (STUDY_INDEX, ACTIVE_STATE, CONTEXT_DIGEST, DECISION_LEDGER).
- No hand-built semantic mapping (no table of names, task types or answers) may enter a *signal*. A signal may use only tool names and arguments, tool output text, the ROS graph as returned by earlier tool results, and the episode's request history. (The verified minimal-sequence plans from Stage 3 are used only to *label*, never as a signal.)
- Time cap 2 hours. An unreadable or missing trace is reported and the rest continues.

## 2. Unit of analysis (fixed here)
Excess is a count per episode, not a property of particular requests. To get request-level units I use the Stage 3 labeller already applied to A1 (`labels_3.json` in the run folder): the **excess requests** of an episode are its requests labelled RED, REC, LATE, NOARG or EXPLORE (not NEEDED, not FIN, not the first request). Stage 3b Table 4 shows these counts equal the excess totals: Qwen 22+11+10+0+4 = 47, Luna 2+1+10 = 13, over supported-complete episodes with excess > 0. The script asserts this equality per model and stops if it fails. Population: Qwen 47 and Luna 13 requests; they are the only items labelled.

Disclosure: the same analyst (Claude) already read these traces in Stage 3b, and the Stage 3b label counts above are known. The categories below come from the addendum, not from the traces.

## 3. Categories (frozen verbatim from the addendum)
Every excess request gets exactly one:
- **P1 Result enrichment.** An earlier tool result or error could have carried the missing fact, so this request (typically a lookup after a failed or short name) was unnecessary.
- **P2 Same-request batching.** The call's arguments were already known one or more requests earlier, and it could have been issued in the same request as an earlier call.
- **P3 Already-held value.** The request repeats a read whose successful result is already in the episode history, or happens after every requirement in the task text is satisfied.
- **P4 Not preventable by a non-semantic signal.** Needed judgment, a dependency on the preceding result, or no general signal fits.

For each P1 to P3 request also record **O** (an ordinary prompt sentence alone could plausibly have prevented it; write the sentence, one line, no task names) or **F** (the framework must act, for example alter tool output or block a call). Judge by the weakest sufficient control, not by convenience.

## 4. Labelling procedure
1. **Rule-based first pass** (`stage3c_label.py firstpass`), applied in this precedence per request k, using only the episode's own calls and results:
   - **P3** if every call in the request is an exact repeat (same tool, same arguments) of an earlier call that succeeded, or its elements (nodes/topics/parameters read) are all already in successful earlier results.
   - **P1** else if the previous request contained a failed call (error text or "not found") and this request is not an exact repeat: a lookup or corrected call after an error.
   - **P2** else if every string argument of every call appears in the task text or in tool results returned up to and including request k-2 (so the call could have joined request k-1 or earlier).
   - **P4** otherwise (its arguments first appear in the result of request k-1, or none of the above fits).
   - First-pass O/F: P3 -> O; P1 -> O if the corrected name already appeared in an earlier tool result, else F; P2 -> O. These are starting points only.
2. **Blind agreement check, before the full review.** 15 requests are drawn at random (seed 20261116, from the 60 excess requests of both models, drawn by `stage3c_label.py blindsheet`). The sheet shows the task text, the episode's calls and result excerpts up to and including the request, and **no first-pass label and no Stage 3 label**. I label these 15 from the sheet alone and save them (`blind_labels_3c.json`) **before** reading any other item.
3. **Manual review of every one of the 60 items** with the trace file and `model_end` line cited (as in Table 6 of `STAGE3B_TABLES.md`). Manual review is the final label. Each manual change to the first pass is listed with the reason.
4. **Agreement** is reported twice: blind relabel vs final manual label, and first pass vs final label, each on category and on O/F, with the full disagreement list.
5. For O items, the one-line sentence is written (generic, no task names, and different from the sentence A1 already contains). Because A1 already says independent calls whose arguments are known may be made together, a P2 item is O only if a *stronger or more specific* sentence plausibly prevents it; this is recorded as plausibility, not as a result.

## 5. Counts and frozen decision rule
Reported separately for Qwen (47) and Luna (13): counts per category; O vs F inside P1 to P3; counts by template (u, p, h, v) and by task; the share of the *total* excess from the largest episode and from the two largest.

**Removable** = P1 + P2 + P3 per episode, capped at that episode's excess. If the cap binds, requests are dropped F first (the choice that favours the prompt-control branch); the opposite order is reported as a sensitivity.

Decision, applied to Qwen only (Luna is for information and does not enter):
- **Stop method work** if removable < 19 of 47 (< 40%).
- **Prompt control, not a method** if removable >= 19 and more than half of removable are O. The next question would then be an ordinary-prompt arm (A2), not a mechanism.
- **A target exists** if removable >= 19 and at least half of removable are F. No mechanism is chosen by this result.
- **Fragile**: the two largest episodes (by removable) make up more than 40% of removable. Stated in the report whichever branch applies.

## 6. Report
`REPORT_STAGE3C.md`: what was done, the table of counts, the branch, what the data cannot show, open questions, and the plain limit: an upper bound from replay; the effect of any signal on the model is untested; the tasks are synthetic; Qwen's repeats are near-duplicates at temperature 0 (about 12 independent task pairs, not 24).

## 7. Shared state (Step 5 of the addendum)
One headroom-row update for Stages 3b and 3c in `STUDY_INDEX.md`; short updates to `ACTIVE_STATE.md` and the open-item text of `CONTEXT_DIGEST.md`; one row in `DECISION_LEDGER.md`; `rosa-context-sync` run once after all edits. No commit, push or merge.

## Revisions
1. (2026-11-14, after the 15 blind labels were saved, before any other item was reviewed.) The P3 clause "after every requirement in the task text is satisfied" can only be judged by reading the task semantically, not by a non-semantic signal. Categories and decision rule are unchanged, but every P3 item gets a flag `sat` (True if it is P3 only by that clause, not by being a repeat) and the report adds a sensitivity: removable counts with and without `sat` items, and the decision branch under each. The frozen headline uses the addendum definition (sat items count).
2. (2026-11-14, during the manual review, before any count was computed.) The rule-based first-pass P2 test ("every string argument appears in the task text or in results up to request k-2") is too lenient: a node name that appears in an early node list does not mean the call could have been issued then, because *which* node to query can depend on the previous result (for example the publishers returned by a topic lookup). The manual label treats such a call as a dependency on the preceding result (P4). The first-pass code is kept unchanged and its disagreements with the manual labels are reported. No category, decision rule or population changed. Manual labels additionally carry `p4_unneeded` (True when a P4 call was not required by the task at all, i.e. an optional extra step); this is reported as a sensitivity only and never enters the frozen rule.
3. (same time) Final O/F convention for sensitivity reporting: the headline uses the manual O/F as written. The report also gives the branch under stricter readings (all P3 repeats treated as F; all P1 treated as F; both), because O means only "an untested sentence plausibly helps".
