# Fairness test: how much of the fixed loop's gain is "errors returned as text" alone? (2026-11-17)

Written for: the project owner. Protocol frozen before any episode ([PROTOCOL.md](PROTOCOL.md), hash `97ae760a...`, verified before and during the run; unchanged). 160 episodes (80 development cells x arms E0, E1), all 47 stock tools, the original ROSA executor; the only change is that a failed tool call (argument validation or tool exception) is returned to the model as a tool message. Scorer v2.0, Amendment 4 oracle, Ollama settings of the pilot. Tables: [TABLES.md](TABLES.md), `results.json`; rows in `RESULTS_LOG.jsonl` (phase `full`); runs under `research/_artifacts/runs/fairness_errors_as_text_20261117/full_*`. "Measured" and "interpretation" are marked.

| | |
|---|---|
| **Result (measured)** | **E1 (better prompt + errors as text) 65/80 supported; E0 (verbatim prompt + errors as text) 60/80.** Comparators: stock verbatim prompt 40, stock + better prompt 47, Forge 55, fixed loop 67 (round 1 control) / 70 (pilot). Frozen band for E1: **>= 62, "most of the gain is errors-as-text; the claim must shrink"**. |
| **What it changes (interpretation)** | Of the fixed loop's 20-cell gain over the stock executor with the same prompt (47 -> 67), errors-as-text alone recovers 18 (47 -> 65), inside the noise of the fixed loop's own 67 to 70. For gpt-oss (the model with 14 of the 27 extra cells over stock) it recovers all of it: 2 and 7 -> 18 of 20, against 16 for the fixed loop. The strict argument check, the 12-tool menu, the finish tool and the bare-text handling are therefore not shown to add supported answers on these cells; what remains is cost (below) and possibly bonsai. |
| **What it cannot show** | Which of those other parts matter for tokens or for bonsai (not isolated); anything on held-out tasks; whether the gap of 2 to 5 cells to the fixed loop is real (two seeds per cell, noise about +-3). The comparison columns come from other sessions. |
| **Adoption-free?** | The change is made by the system (the model has nothing to adopt), but the model has to use the returned text: it did in the episodes with returned errors (21 of the 31 episodes with one ended supported, section 3). |
| **Cost** | 160 episodes, about 3 hours of run time (including the oracle reads), no oracle failure, no stop; 4 episodes (all bonsai: E0 p3, E1 v2 x2 and h4) ended at the 40-request iteration limit with no answer (all unsupported; see the correction note). E1 used 4.23M tokens and 591 requests for 65 supported answers; the fixed loop 2.00M and 506 for 67 (see tokens below). |

**Correction note (2026-11-18):** the first version and TABLES.md said 0 iteration-limit episodes. The stock executor returns "Agent stopped due to max iterations." as the answer with no error, so the log's `aborts` list did not mark them (the same cause as the round-2 cap amendment, `decisions/2026-11-17-round2-cap-amendment.md`). Counted from the traces: 4 episodes, all bonsai and all already unsupported; no supported count, request or token figure changes.

## 1. Measured results
| arm | supported/80 | requests | tokens (in+out) | requests per supported | abort episodes | tool errors returned |
|---|---:|---:|---:|---:|---|---:|
| **E0** verbatim prompt + errors as text | **60** | 649 | 4,924,429 | 10.8 | 2 (backend/tool-call parse) | 66 |
| **E1** deconflicted prompt + errors as text | **65** | 591 | 4,230,199 | 9.1 | 1 (backend/tool-call parse) | 26 |
| S0 stock, verbatim (earlier run) | 40 | 480 | 3,742,310 | 12.0 | 24 | 0 |
| A1 stock, deconflicted (pilot, re-scored with scorer v2.0) | 47 | 472 | 3,281,423 | 10.0 | 18 | 0 |
| fixed loop, round 1 control | 67 | 506 | 1,995,814 | 7.6 | 1 | n/a |
Forge 55/80 and the pilot's fixed loop 70/80 are the figures given in the brief (Forge report); I did not recompute them.

Per model, supported out of 20 (E0 / E1 / S0 / A1 / fixed loop): lfm3 13 / 15 / 13 / 15 / 16; qwen3.5 18 / 20 / 16 / 19 / 20; **gpt-oss 18 / 18 / 2 / 7 / 16**; bonsai 11 / 12 / 9 / 6 / 15. Tokens per model are in TABLES.md (E1: lfm3 1.08M, qwen 0.79M, gpt-oss 0.56M, bonsai 1.80M; fixed loop 0.64M, 0.27M, 0.29M, 0.80M).

Same-cell (80 cells): E1 vs A1 stock: both 47, only E1 18, only A1 0, neither 15. E0 vs S0: both 36, only E0 24, only S0 4. E1 vs fixed loop: both 59, only E1 6, only fixed loop 8, neither 7. E1 vs E0: both 55, only E1 10, only E0 5, neither 10.

Aborts: the stock arms ended 24 (S0) and 18 (A1) episodes on tool-argument errors (mostly the `blacklist` argument of the list tools). With errors as text, **no episode ended on a tool error**: the 3 aborts left (E0 2, E1 1) are backend errors (`ResponseError`: an XML tool-call syntax error from lfm3 and from bonsai, a malformed tool-call JSON from gpt-oss), which are not tool errors and end the episode as before by design. Returned errors: E0 66 (61 validation, 5 tool exceptions) in 18 episodes (13 supported), E1 26 (18 and 8) in 13 episodes (8 supported). Most frequent: `ros2_service_call` `request` validation (43 of E0's 66, a write tool that the study guard blocks anyway), `blacklist` validation of the list tools, `multiple repeat at position 2` (a regular-expression error from a pattern argument, 10 returned in total), `nodes` field missing for `ros2_node_info` (7, E1).

## 2. Reading against the frozen bands
**Measured:** E1 = 65. **Band (frozen before the run): E1 >= 62.** **Interpretation:** the main part of what separates the fixed loop from the stock executor on these cells is returning errors as text. The claim that the fixed loop's specific design (argument pre-check, short menu, finish tool) lifts supported answers must shrink to what remains: 2 cells vs the round 1 control (65 vs 67, same-cell 6 vs 8, which is noise), 5 vs the pilot's 70.
- **Prompt effect with errors as text:** E1 minus E0 = +5 cells (same-cell 10 vs 5), about the noise level; E0 alone is 60, so errors-as-text without the better prompt already recovers 20 of the 27 cells between stock (40) and the fixed loop (67). I cannot separate the prompt from sampling at this size.
- **Where the other parts may still matter (hypotheses, not tested):** bonsai (12 vs 15 supported, 19.4 vs 12.3 requests per supported answer, more requests: the small model benefits from a 12-tool menu), and cost: E1 used 2.1x the tokens of the fixed loop (4.23M vs 2.00M) and about 17% more requests (591 vs 506), consistent with the 47-tool schema being sent in every request. These are the places where the proposed ablations would look.

## 3. Unexpected or notable
- gpt-oss reached 18/20 under both arms (stock S0 2/20, A1 7/20): its whole stock failure was the aborts on tool-argument errors.
- The returned error messages are the raw pydantic/tool texts and were enough for the models: **21 of the 31 episodes that got a returned error ended supported** (E0 13 of 18, E1 8 of 13).
- One E0 episode (`e1h_chg_2`) never received its scripted change (the known hook defect, kept as is; unsupported). No backend crash, no oracle failure in 24 oracle reads, and 4 episodes at the 40-request iteration limit (E0 1, E1 3, all bonsai, all unsupported) (Amendment 4 read).
- Bookkeeping: the first smoke was started before the owner's go and stopped; its folder was archived and the full test restarted from zero (RUN_NOTES.md). A run-id collision between smoke and full rows was found in the smoke and fixed in `run_fair.py` (bookkeeping only).

## 4. Proposed ablations (not run)
Both on the same 80 cells, both arms of the fixed loop from round 1 with one thing changed, same oracle and rules; each about 1.5 hours (fixed loop episodes are short).
1. **Fixed loop with the 47-tool menu** (instead of 12 tools). Question: how much of the token gap (2.1x) and of bonsai's gap comes from the short menu. Bar to freeze: supported change of at least 4 cells or a token change of at least 25% against the round 1 control (67, 2.00M).
2. **Fixed loop without the argument pre-check** (schema errors come back as the plain pydantic text, as in E1). Question: whether the pre-check adds anything over the stock schema errors. Bar: supported change of at least 4 cells or requests change of at least 15%.
With two seeds the supported counts cannot resolve differences below about 3 to 4 cells; if either ablation is run for the supported-count question, adding seeds 3 and 4 (80 more cells per arm) is advisable.

## 5. Limits
Development tasks, four small models, two seeds per cell, one fixture style; arms E0/E1 vs S0/A1/fixed loop are different sessions (noise about +-3 cells); one prompt pair; the error text is the stock text. Nothing here is a novelty or significance claim.
