# PROTOCOL_STAGE3D (frozen before any Stage 3d inference)

Frozen: 2026-11-14. Source: the user-authorized addendum `ROSA_stage3d_A2_prompt_control_addendum.md` (mirrored folder `Claude outputs/`). New files only (`run_stage3d.py`, this protocol, `STAGE3D_LOG.md`, `STAGE3D_TABLES.md`, `REPORT_STAGE3D.md`, `summarize_stage3d.py`); `src/rosa/`, baselines, `AGENTS.md` and every Stage 0 to 3c file stay untouched. Qwen only, local Ollama, no API key, no paid service. No commit, push or merge. Development evidence, no novelty claim, no mechanism, no selected algorithm. Revisions after the first inference go under "Revisions", never in place. Ambiguities are resolved by the most reasonable reading and time-stamped in `STAGE3D_LOG.md`.

## Question (one only)
Stage 3c judged that 43 of Qwen's 47 leftover A1 requests could be prevented by generic one-line prompt sentences; that is an untested plausibility judgment by one analyst. **Do the sentences actually reduce Qwen's excess over the floor?**

## Preflight record (context section 14.2)
1. Opportunity (F): Stage 3b left Qwen at 47/96 = 49.0% excess under A1; Stage 3c labelled 43 of the 47 removable and judged them O (prompt sentence could plausibly prevent them). 2. Mechanism: none; an ordinary-control arm. 3. Novelty: none claimed. 4. Fair evaluation: same tasks, fixture, scorer, floors, labeller, model settings and prompt base as A1; only one added system message. 5. Decision-changing action: the frozen rule below decides whether method work on this benchmark stops, a target exists, or the result is inconclusive. Closest prior studies: Stage 3b and Stage 3c (`REPORT_STAGE3B.md`, `REPORT_STAGE3C.md`); closest negative result: Stage 2a (learned expansion killed by its bar).

## Arm A2 (frozen)
A1 exactly as in Stage 3b (hash `7acbb0555cba9f406f4915e6d96da1d69bfdf7360d48c2d37c40e4232954a209`, 7 messages), plus **one** additional system message placed directly after A1's neutral line, containing these six sentences verbatim, in this order, and nothing else (joined by single spaces):

1. Build full node names as namespace plus name from earlier results; never pass a bare name.
2. Do not repeat a call whose successful result is already in the conversation.
3. Issue every call whose arguments you already know in the same response.
4. Make lookups that need no arguments in the same response as your first lookup.
5. Stop and answer as soon as every requested field has a value from a tool result.
6. When you must inspect many known entities, request them all in one response.

One shot. The wording is fixed now; no rewriting, reordering, strengthening or adding of sentences after any result. Implemented only in the harness subclass `A2ROSA._get_prompts` in `run_stage3d.py` (as `A1ROSA` did). Each trace stores the full prompt list actually sent and its hash. Offline check (`run_stage3d.py check`, run before this freeze): A2 has 8 messages; removing the new message gives A1 exactly (same order and text); the new message sits directly after A1's neutral line; the registry is unchanged (47 tools). **A2 sha256 `f98b3eac956d0c87ce9a2efdcf83ba992822334bbbc99214df5c50dc14e5758d`.**

## Design
- Model: `qwen3.5:9b` at the Stage 3b endpoint; temperature 0, seed 42, reasoning off, `num_ctx` 65536 (verified from `/api/ps` after the first episode), `num_predict` 4096, client timeout 90 s, max iterations 40, episode timeout 900 s, as in Stage 3b. Luna is not run.
- The 12 Stage 3 tasks (`stage3_tasks.json`), floors depth + 1 (3, 4, 5), the same generated fixture builder and seed (20261113, 19 nodes in `/plant32`), 2 repeats each = **24 episodes**, one pass, no pilot. Schedule: each repeat block of 12 shuffled with seed **20261117** (saved in the run folder). ROS domain **216**, localhost only. Oracle checks before, after episode 12 and after episode 24 (evaluation-only reads retry up to 3 times; the agent's reads never retry). Fixture stopped, domain verified empty and daemon stopped at the end and after any abort.
- Scorer, floors, codebook and labeller as Stages 3 and 3b (`score_stage3.py`, `stage3_labels.py`, `stage3_review.py`): supported-complete = exact answer AND support screen; excess = requests - floor; excess share = sum(excess) / sum(floor) over supported-complete episodes.
- An episode lost to infrastructure failure (fixture died, Ollama unreachable, oracle mismatch) may be replaced once under a new ID; the lost one is kept and counted; model failures are never rerun.
- Stop and report on: Ollama unreachable, fixture cleanup failure, oracle mismatch, 24 episodes done. Wall-clock cap 2 hours from launch. A1 numbers come from Stage 3b (run on 2026-11-13; A2 runs on a later day; minor for local Qwen at temperature 0).

## Decision rule (frozen; supported-complete episodes only; denominators stated; A1 reference: Qwen 47/96 = 49.0%, supported 24/24)
1. **Correctness first.** If fewer than 22 of 24 A2 episodes are supported-complete, report accuracy first: the sentences cost correctness and the excess is not interpretable; stop the rule here.
2. **Sentences close it:** Qwen A2 excess is **under 25%** of the floor. An ordinary prompt control removes the weak-model room on this benchmark; method work on it stops.
3. **A target exists:** Qwen A2 excess is **40% or more**. The weak-model residual survives a generic sentence control.
4. **Inconclusive:** 25% up to 40%. Report which categories survive; no method decision.

## Report contents
Branch and numbers first (for example "A2 Qwen excess 22/96 = 22.9%, supported 24/24, rule 2"). Then: A1 versus A2 paired by task and repeat (mean request difference, range, signs) among pairs where both arms are supported-complete, and supported-complete counts; counts of RED, REC, LATE, NOARG and EXPLORE requests in A1 versus A2 (labels per request, not capped), to see which sentences changed which behaviour; if A2 excess is 25% or more, the remaining excess labelled with the Stage 3c categories P1 to P4 and O/F under the Stage 3c definitions. Limits stated plainly: the six sentences were written from these same traces, so A2 is fitted to the development tasks by construction and any success still needs held-out tasks; synthetic fixture; Qwen's repeats are near-duplicates at temperature 0 (about 12 independent pairs); A1 and A2 ran on different days. No mechanism, no novelty claim, no selected algorithm.

## Provenance
Per run: git HEAD, branch, status, source freeze with hashes (harness, vendored files, `src/rosa`, `uv.lock`), package versions, prompt lists and hashes, model settings and active context, ROS distro and domain, fixture commands, seeds, schedule, per-episode trace and answer, oracle snapshots. Raw traces under `research/_artifacts/runs/headroom_diagnostic_20261112/`; no credentials.

## Revisions
(none yet)
