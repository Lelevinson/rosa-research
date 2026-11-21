# Thinking escalation, replication (amendment A2): the mechanism effect does not replicate on the 18-task set (class B), it does on the 10 shared tasks; no effect on supported answers; the cap removes most runaway

2026-11-19, Asia/Taipei (run 17:56-23:05, about 5 h 9 min). Frozen [PROTOCOL.md](PROTOCOL.md) (`0e9fbdf6...`), [AMENDMENT_A1.md](AMENDMENT_A1.md) (`72be5bc9...`) and [AMENDMENT_A2.md](AMENDMENT_A2.md) (`8a4ee917...`, recorded 17:01, before any A2 episode). **432 episodes** (18 tasks x 4 models x new seeds 3-4 x FULL / ESCALATE / ESCALATE_CAPPED), 12 sessions with the three arms shuffled together, run through the exam queue with the frozen plan (manifest `5c6fe2e6...` checked before the first request); 432 of 432 logged, 0 duplicates, 0 skipped, 0 infrastructure failures, 0 timeouts; smoke first (6 episodes, 65 checks). Analysis: the frozen `analyze_replication.py` (SHA-256 `e14a6c03da153bae...`, hashed before the first episode) on the part A rows plus these; numbers in `results_replication.json`, tables in `REPLICATION_TABLES.md`. Part B (ALWAYS) was **not** started (the hold condition would be met, the run finished at 23:05; waiting for the owner's go). Development evidence only; not a held-out result.

## Top box
- **R1, the replication (ESCALATE against FULL, 18 tasks, seeds 3-4, 144 cells per arm): class B by the frozen rule.** The pooled share of trigger events whose next request makes a progress call (O2) went from 23.9% to 26.6% (+2.7 points; the bar is +10). No harm flag, no cost flag. **Part A's mechanism result is not reproduced on this task set.**
- **R2, the 10 shared tasks with part A added (seeds 1-4, 160 cells per arm): class A**: O2 27.3% -> 39.0% (+11.7 points), higher in bonsai, lfm3 and gpt-oss (qwen3.5 not evaluable). It rests on part A: the interval of the O2 difference is [-1.8, +39.9] points over 10 tasks.
- **Supported answers: no effect in any reading** (R1 125 against 125 of 144; R2 139 against 137 of 160).
- **Cost is not consistent:** requests -13.6% in part A, +6.2% in the replication (R1), -5.3% in R2; every task-clustered interval of the request and token ratios contains 1. Estimated thinking tokens rise 3-5 times (R1 26,170 -> 126,744); episode wall time +24.6% (R1) and +14.0% (R2).
- **Design check (descriptive): the cap works as intended.** ESCALATE_CAPPED against ESCALATE: runaway episodes 7 -> 1, escalated requests 327 -> 159, estimated thinking tokens 126,744 -> 73,363 (-42%), iteration-cap endings 3 -> 0, no-answer endings 4 -> 1, requests 855 -> 749, in+out tokens -14.9%, with supported 125 -> 123 (noise).
- **gpt-oss is reported but its arm contrasts are not interpretable** (part A: request 1 differed between identical arms in 16 of 20 cells); a pooled version without it is below.

## Measured, frozen readings (episodes per arm in brackets)
| | R1 FULL (144) | R1 ESCALATE (144) | R2 FULL (160) | R2 ESCALATE (160) |
|---|---|---|---|---|
| supported-complete | 125 | 125 | 139 | 137 |
| paired cells: both / FULL only / ESCALATE only / neither | 121 / 4 / 4 / 15 | | 129 / 10 / 8 / 13 | |
| model requests | 805 | 855 | 1,005 | 952 |
| input / output tokens | 3,250,447 / 138,831 | 3,031,403 / 217,374 | 3,525,670 / 199,561 | 3,261,564 / 260,159 |
| thinking tokens (estimate) | 26,170 | 126,744 | 37,697 | 160,843 |
| wall seconds (sum of episodes) | 4,100 | 5,109 | 5,383 | 6,139 |
| cap endings / no-answer / length cuts / backend errors | 4 / 4 / 1 / 0 | 3 / 4 / 2 / 0 | 3 / 5 / 2 / 1 | 2 / 8 / 3 / 1 |
| trigger events with a next request | 230 | 259 | 278 | 218 |
| **O2 (progress call at the next request)** | **23.9%** | **26.6%** | **27.3%** | **39.0%** |
| escalated requests | 0 | 327 | 0 | 303 |
**Task-clustered 95% intervals (bootstrap over tasks, 5,000 draws):** R1 (18 tasks): supported difference 0.0 [-2.8, +2.8] points; request ratio 1.062 [0.958, 1.152]; token ratio 0.959 [0.818, 1.196]; O2 difference +2.7 [-8.8, +17.3]. R2 (10 tasks): supported -1.25 [-7.5, +5.0]; request ratio 0.947 [0.800, 1.073]; token ratio 0.945 [0.691, 1.118]; O2 +11.7 [-1.8, +39.9].
**Per model (O2 FULL -> ESCALATE, events FULL/ESCALATE):** R1: bonsai +4.7 points (161/137); lfm3 **-23.5** (32/79, not higher); qwen3.5 14/16 events, not evaluable; gpt-oss +17.6 (23/27, **not interpretable**). R2: bonsai +12.9 (166/117); lfm3 +2.2 (70/58); gpt-oss +14.7 (29/27, not interpretable); qwen3.5 13/16, not evaluable. **Without gpt-oss:** R1 class B (+0.8 points), R2 class A (+10.7).
**Supported by model, R1 (FULL -> ESCALATE -> CAPPED):** bonsai 23 -> 26 -> 24; gpt-oss 36 -> 36 -> 35; lfm3 30 -> 27 -> 28; qwen3.5 36 -> 36 -> 36.

## Design check: ESCALATE_CAPPED against ESCALATE (replication, descriptive, no class)
| | ESCALATE | ESCALATE_CAPPED |
|---|---|---|
| supported | 125 | 123 |
| requests / in+out tokens | 855 / 3,248,777 | 749 / 2,765,760 |
| escalated requests / estimated thinking tokens | 327 / 126,744 | 159 / 73,363 |
| runaway episodes (>= 10 requests with thinking on, or a length cut while on) | 7 | 1 |
| episodes where the cap was reached | n/a | 7 |
| cap (iteration) endings / no-answer / length cuts | 3 / 4 / 2 | 0 / 1 / 1 |
| wall seconds | 5,109 | 4,748 |
By model, runaway: lfm3 3 -> 0, bonsai 4 -> 1, qwen3.5 0 -> 0, gpt-oss 0 -> 0 (not interpretable). The cap was reached in only 7 of 144 episodes (lfm3 4, bonsai 3).

## Exploratory cuts (NOT frozen; added after seeing the results to understand R1 against part A; labelled as such)
- **Replication on the 10 shared tasks alone (seeds 3-4):** O2 25.4% -> 36.2% (+10.8 points; part A: +13.7), supported 73 -> 72, requests 483 -> 501, wall 2,540 -> 3,243 s. **The mechanism effect reproduces on the same tasks with new seeds.**
- **The 8 name-fix tasks alone (seeds 3-4):** O2 21.9% -> 17.4% (-4.5 points), trigger events 96 -> 132, supported 52 -> 53, requests 322 -> 354. **These tasks produce the R1 miss.** lfm3 on them: events 6 -> 44, requests 61 -> 104.
- **One episode dominates lfm3's name-fix events:** lfm3 `nf_multi_2` seed 4 under ESCALATE has **37 trigger events in 40 requests (iteration cap)**, 37 of the 44. Without that single episode R1's pooled O2 gain is **+6.6 points** (still below the bar of 10, so R1 stays class B, but the value moves from +2.7).
- **ESCALATE_CAPPED against FULL:** supported 123 against 125, requests 749 against 805 (-7.0%), in+out tokens 2,765,760 against 3,389,278 (-18.4%), O2 34.4% against 23.9%, estimated thinking tokens 73,363 against 26,170, trigger events 160 against 230.

## Interpretation (labelled; hypotheses, not measurements)
1. **The event-level effect is real on the original task family and absent on the name-fix family** (exploratory cut). H (untested): on name-fix tasks the dead ends are tied to name guessing and a thinking window re-arms on every one, so lfm3 can enter long trigger loops (37 events in one episode); the effect may depend on what kind of dead end triggers it. The frozen R1 verdict is B; R2 (A) is pulled up by part A and the shared-task replication; the honest summary is "reproduces on the same tasks, not shown to generalise to the new tasks".
2. **No claim about answers is supported:** supported answers are equal or within noise in every cut (the detectable difference with 144-160 cells per arm is about 8 cells).
3. **Efficiency is not established:** the sign of the request effect changed between part A (-13.6%) and the replication (+6.2%); intervals contain 1; the cost that is reliable is the thinking tokens (3-5 times) and wall time (+14% to +25%).
4. **The cap is a sound design choice** on this evidence: it removes most runaway episodes and 42% of the thinking tokens without a visible loss in supported answers; it is reached rarely (7 of 144 episodes). The comparison is descriptive and the cell counts are small.
5. gpt-oss: not interpretable (non-reproducible request 1, its `false` level is medium-like and unrecorded, only 23-29 events per arm).

## Limits (reported, not patched)
- One replication (seeds 3-4); trajectories diverge from the first request, more for gpt-oss and sometimes lfm3, so pairing is descriptive. The class bars are conventions; with two to three evaluable models a single model decides the "2 models" condition.
- The name-fix tasks were new to this study and are scored by scorer v2.0 without the name-fix rule; the arms differ only in the thinking setting.
- Events are several per episode and not independent; one episode can contribute 37 of a model's events (above); the O2 outcome compares event populations that differ between arms (ESCALATE_CAPPED has 160 events, ESCALATE 259, FULL 230).
- The thinking-token figures are estimates (output minus visible tokens); output tokens in the tables already include thinking (see the part A follow-up).
- The exploratory cuts were chosen after the results; they are explanations to test, not findings.
- Part B not run; nothing here uses ALWAYS. Teammate-context check (`rosa-contexts`) not done.

## Open search (patterns noticed that are not this study's target; counts over the 432 episodes; paths under `research/_artifacts/exam/thinking_replA2/runs_all/`; no filtering)
- **Runaway thinking under ESCALATE: 7 episodes** (lfm3 `block_0001/015-v2-ESCALATE-lfm3_1.7b-s3` 14 escalated requests, `018-v2-ESCALATE` 7 with a length cut, `block_0003/028-nf_multi_2-ESCALATE-lfm3_1.7b-s4` 37; bonsai `block_0010/015-v2-ESCALATE-bonsai-2_4b-s3` 13, `019-v2-ESCALATE` 36, `block_0012/013-nf_multi_2-ESCALATE` 36, `044-nf_multi_1-ESCALATE` 26). The one CAPPED runaway: bonsai `block_0010/007-v2-ESCALATE_CAPPED-bonsai-2_4b-s3` (length cut).
- **Iteration-cap endings:** FULL 4 (all bonsai: `v2` s3, `e1h_chg_2` s3, `nf_multi_2` s3 and s4), ESCALATE 3 (lfm3 `nf_multi_2` s4, bonsai `v2` s4, bonsai `nf_multi_2` s4), CAPPED 0. **No-answer endings:** FULL 4 (all bonsai, the four caps), ESCALATE 4 (lfm3 `v2` s4, lfm3 `nf_multi_2` s4, bonsai `v2` s4, bonsai `nf_multi_2` s4), CAPPED 1 (bonsai `v2` s3, length cut).
- **Backend tool-call errors: 0 in all 432 episodes** (part A had 2); length cuts FULL 1 (lfm3 `v2`), ESCALATE 2 (lfm3 `v2`), CAPPED 1 (bonsai `v2`).
- **Bonsai FULL carries 165 of FULL's 234 trigger events** (71%); lfm3 ESCALATE has 80 against 32 in FULL; ESCALATE_CAPPED cut bonsai's events to 58 (from 139 in ESCALATE).
- **Tasks that stay unsupported in every arm:** `nf_single_1` 3 of 8 cells in each arm, `nf_exact` 2, `nf_single_2` 2, `v2` 4 / 4 / 3 (FULL / ESCALATE / CAPPED), `nf_absent` 1: failures that do not depend on the arm (name-fix tasks account for 12 of FULL's 19 unsupported cells).
- **Escalated requests that returned no thinking text:** not counted per request in this analysis (part A: 3 of 130).
- **Queue and monitor ran without incident** for 5 hours 9 minutes: 0 restarts, 0 quarantined groups, the "finished" message was sent at 23:05.
