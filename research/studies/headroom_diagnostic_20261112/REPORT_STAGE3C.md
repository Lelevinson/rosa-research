# REPORT_STAGE3C: offline residual analysis of the Stage 3b (arm A1) excess

Date: 2026-11-14. Protocol: [PROTOCOL_STAGE3C.md](PROTOCOL_STAGE3C.md) (frozen before any label; two revisions listed there, both made before any count was computed). Tables and every labelled item with its trace line: [STAGE3C_TABLES.md](STAGE3C_TABLES.md). Development evidence only; no mechanism proposed, no novelty claim, no method selected.

## What was done
Saved Stage 3b traces only (`research/_artifacts/runs/headroom_diagnostic_20261112/stage3b_20261113T155721Z/`). No model call, no provider, no API key, no ROS fixture; no Stage 0 to 3b file and nothing in `src/rosa/` was edited. Population: the 60 excess requests of supported-complete A1 episodes with excess > 0 (Qwen 47, Luna 13), taken from the Stage 3 labeller (RED, REC, LATE, NOARG, EXPLORE). The script asserts the totals match Stage 3b Table 4, and all 60 traces were readable. Each item was labelled P1 to P4 and, for P1 to P3, O or F. Steps: rule-based first pass, then a **blind relabel of 15 random items before any other item was reviewed**, then manual review of all 60.

## Result (Qwen, the only model in the rule)
| | count |
|---|---:|
| P1 result enrichment | 11 |
| P2 same-request batching | 12 |
| P3 already-held value | 20 (2 only by the "requirements already satisfied" clause) |
| P4 not preventable by a non-semantic signal | 4 (all optional extra steps) |
| **Removable (P1+P2+P3, capped per episode)** | **43 of 47 (91.5%)** |
| of which O / F | 43 / 0 |

**Branch: prompt control, not a method.** Removable 43/47 is far above 19, and all 43 are O. Fragile: no (two largest episodes 11 of 43 = 26%; largest 7 of 43). Short form: *removable 43/47, 0 F, 43 O, fragile: no*. The next question the rule points to is an ordinary-prompt arm (A2), not a mechanism.

Luna (information only, not in the rule): removable 10 of 13, all P2 (a no-argument or named-entity lookup serialised behind the first request), all O; 3 P4 optional extra steps.

By template (Qwen): service 14 (10 P2, 4 P3), upstream 21 (5 P1, 2 P2, 12 P3, 2 P4), hub 12 (6 P1, 4 P3, 2 P4), pointer 0. By task and the full per-item list are in the tables. Largest episode by excess: `46-u4-ollama-r1`, 8 of 47 (17%); two largest 12 (26%).

## How firm is the branch? (read this before using it)
The count (43 of 47 removable) is firm under my labels. The **branch is not**, because it rests on one judgment: that all 43 are O, meaning an untested one-line prompt sentence would plausibly have prevented them (sentences are listed in the tables). The sensitivity table shows what happens if that judgment is wrong:
- All P3 treated as F: O is 23 of 43 (53%), same branch, barely.
- All P1 treated as F, or all P2 treated as F: still prompt control (74% and 72% O).
- **All P1 and P3 treated as F (only P2 stays O): O is 12 of 43 (28%) and the branch flips to "a target exists".**
- Without the two "requirements satisfied" P3 items: unchanged (41 removable, all O).

Reasons for caution about O: (1) A1 already contains a sentence that permits batching, and Qwen still has 12 P2 requests, so the permission did not work; a stronger imperative is plausible but untested. (2) 20 of the 43 are repeated identical reads at temperature 0, including a 5-repeat loop; whether a sentence stops such loops on this model is exactly what Stage 3b could not tell. (3) For P1 I judged O because the short-name recovery used a full name that could be built from "Node namespace" plus "Node name" in an earlier result; whether the model would follow a naming sentence is untested.

## What the data cannot show
- This is an upper bound from replay. A replay cannot tell what the model would have done instead; a removed request could be replaced by a different one, or the final answer could change.
- No signal was built or tested. "Removable" says a general signal has something to aim at, not that any signal works.
- The tasks are synthetic and from one generated fixture (12 tasks); Qwen's repeats are near-duplicates at temperature 0, so there are about 12 independent task pairs, not 24 (the per-template numbers rest on 1 to 4 tasks).
- O versus F is a plausibility judgment made by one analyst (Claude), not a measurement.
- 4 Qwen requests (and 3 Luna) are P4 optional extra steps (for example a parameter listing when the parameter name was in the task text). A generic sentence might discourage them, but that needs semantics, so they stay P4.
- The two "requirements satisfied" P3 items can only be recognised by reading the task, so a non-semantic signal could not find them; the branch is unchanged without them.

## Agreement check
- Blind relabel of 15 random items (seed 20261116; first-pass and Stage 3 labels hidden): category 15/15, category plus O/F 15/15. The same analyst made both sets of labels, so this shows consistency over time and from the sheet alone, not independent agreement.
- Rule-based first pass vs final manual (all 60): category 38/60 (63%), category plus O/F 35/60 (58%). The first pass was too lenient for P2 (it treated a name present in an early node list as "known earlier", although which node to query depends on the previous result); 14 first-pass P4 items became P2 and 4 became P1 on review (PROTOCOL_STAGE3C revision 2). The first pass is not a usable labeller on its own.

## Open questions
1. Is an ordinary-prompt arm (A2: A1 plus the O sentences, same 12 tasks, same seeds) worth running? The rule points to it; it needs the mandatory preflight and your authorization. It would also test the main weakness above (do repeats and short-name recovery respond to a sentence?).
2. If the repeats and short-name recovery do not respond to sentences, the P1/P3 items become F, and the "all P1 and P3 as F" row says a target would then exist. That is the pre-registered way the branch could flip.
3. A0 and A1 ran in different sessions, and A1 changed three messages at once (still open from Stage 3b).

No run, method or next stage is authorized by this report.
