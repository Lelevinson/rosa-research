# REPORT_STAGE3D: arm A2 (six generic prompt sentences), Qwen only

Date: 2026-11-14. Protocol: [PROTOCOL_STAGE3D.md](PROTOCOL_STAGE3D.md) (frozen before any inference; no revisions). Tables: [STAGE3D_TABLES.md](STAGE3D_TABLES.md); residual labels: [STAGE3D_LABELS.md](STAGE3D_LABELS.md); log: [STAGE3D_LOG.md](STAGE3D_LOG.md). Run: `research/_artifacts/runs/headroom_diagnostic_20261112/stage3d_20261114T005613Z` (hash manifest `MANIFEST_STAGE3D.sha256.json`). Development evidence only; no mechanism, no novelty claim, no selected algorithm.

## Branch and numbers
**A2 Qwen supported-complete 20/24 (A1 24/24), so frozen rule 1 fires: correctness first, the excess is not interpretable, the rule stops here.** Excess over the floor on the 20 supported episodes is 30/80 = 37.5% (A1: 47/96 = 49.0%); on the same 20 task-repeat cells A1 had 41/80 = 51.2%. These excess figures are descriptive only. The sentences did not close the room and did not show a clean target either; they changed several behaviours and cost correctness.

## What happened (all 24 episodes ran; no infrastructure loss)
24 episodes, 24 clean exits, oracle matched before, after episode 12 and after episode 24, active context 65536 verified, cleanup verified empty, A2 hash `f98b3eac...` in every trace. Offline check: A2 is A1 plus exactly one message directly after A1's neutral line.

**The four failures (read by hand):**
- `08-v2-ollama-r0`, `20-v2-ollama-r1` (service task v2): after `service_info` and `node_list`, Qwen called `ros2_service_call` on `/plant32/cedar_reset` (an action tool, not requested) with `request: {}` as a dict; the tool schema rejected it ("Input should be a valid string"), the episode ended with an error and no answer. No tool result came back, so nothing was executed on the fixture; the oracle afterwards was clean. No A0 or A1 trace contains a `ros2_service_call` start (checked over all Stage 3 and Stage 3b traces).
- `03-p4-ollama-r0`, `22-p4-ollama-r1` (pointer task p4): Qwen followed the chain but read the setpoint of `/plant32/beacon` (the second node reached, 694) and answered with it; the required node is `/plant32/juniper` (873). It then re-read beacon's setpoint once before answering. Unsupported value, so not supported-complete.
- Cause is not established. Hypothesis (untested): sentence 5 ("stop and answer as soon as every requested field has a value") invites stopping once a `setpoint` has a value, even from the wrong node; I have no hypothesis for the service call. A single added message means no sentence can be credited individually.

## A1 versus A2 (Qwen, supported episodes)
- Paired by task and repeat, 20 pairs where both arms are supported-complete: mean requests A1 - A2 = 0.55, median 0.5, range -3 to 3; A2 fewer in 10, equal in 8, more in 2. Supported-complete 24/24 -> 20/24.
- Request kinds (Stage 3 labeller, per request, supported episodes with excess):

| | RED (repeats) | REC (recovery after short names) | LATE (serialised calls) | NOARG | EXPLORE |
|---|---:|---:|---:|---:|---:|
| A1 | 22 | 11 | 10 | 0 | 4 |
| A2 | 22 | 0 | 4 | 0 | 4 |

- Short-name recovery disappeared (11 -> 0) and serialised calls fell by more than half (10 -> 4). Repeats did not change in number (22 -> 22), although their shape did: A1's total includes one 5-repeat loop (`46-u4-ollama-r1`), while A2's are many short repeats (1 to 2 per episode, 20 in 14 episodes). The optional extra steps did not change either (EXPLORE 4 -> 4). Sentence 2 (do not repeat) had no visible effect on Qwen. Only sentence 1 addresses bare names, so its link to REC 11 -> 0 is plausible; this is not an ablation.

## Residual excess labelled with the Stage 3c categories (A2 excess is above 25%)
| | A1 (Stage 3c) | A2 |
|---|---:|---:|
| P1 result enrichment | 11 | 0 |
| P2 same-request batching | 12 | 6 |
| P3 already-held value | 20 | 20 (2 only by the "requirements satisfied" clause) |
| P4 not preventable by a non-semantic signal | 4 | 4 (all optional extra steps) |

Under the Stage 3c definitions the remaining 26 P2/P3 requests occurred with the matching sentence already in the prompt, so for Qwen at this wording the sentence demonstrably did not suffice: they are labelled F ("tested, A2 sentence did not suffice"), not O. This is a one-run, one-wording interpretation; a stronger wording was not tried and the frozen protocol forbids trying it here. Per item: [STAGE3D_LABELS.md](STAGE3D_LABELS.md).

## What this does and does not show
- It refutes part of the Stage 3c judgment: the O label for repeats (P3) was wrong for Qwen at this wording, and half of the batching items (P2) also survived. It supports the part about bare names (P1 gone).
- It does not show the excess is closed (rule 2) and does not trigger rule 3, because rule 1 fires first. Illustration only, not a result: had the four failed cells matched A1's excess on those cells (6 over a floor of 16), the share would be 36/96 = 37.5%, in the 25% to 40% band (rule 4), not below 25%.
- Correctness fell with a generic sentence block. That alone is a finding for any "ordinary prompt" claim on this model: the added message is not free.

## Limits (plainly)
- The six sentences were written from these same traces, so A2 is fitted to the development tasks by construction; any success would still have needed held-out tasks.
- Synthetic generated fixture, 12 tasks; Qwen at temperature 0 gives near-duplicate repeats (about 12 independent pairs, not 24); all four failures are two pairs of identical repeats.
- A1 ran on 2026-11-13 and A2 on 2026-11-14; local Qwen at temperature 0, a minor issue.
- One prompt, one shot, one model; no per-sentence ablation; the O/F relabelling is one analyst's interpretation; no independent review.

## Open questions
1. Is the correctness drop caused by sentence 5, by the block as a whole, or by chance on two tasks? Settling it needs an ablation with its own protocol; none is authorized.
2. Repeats (20) and optional steps (4) survive a sentence. Whether that makes them a framework target is a decision for you under the mandatory preflight; this report selects nothing.
3. A0, A1 and A2 ran in different sessions, and A1 changes three messages at once (open since Stage 3b).

No run, method or next stage is authorized by this report.
