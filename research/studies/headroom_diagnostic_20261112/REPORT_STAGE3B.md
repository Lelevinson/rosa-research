# Stage 3b report: the strongest ordinary control on the Stage 3 tasks (2026-11-13)

Development evidence on the synthetic Stage 3 fixture; no novelty claim, no method. Frozen plan `PROTOCOL_STAGE3B.md`; tables `STAGE3B_TABLES.md`; log `STAGE3B_LOG.md`; raw traces `research/_artifacts/runs/headroom_diagnostic_20261112/stage3b_20261113T155721Z/` (hashes in `MANIFEST_STAGE3B.sha256.json`). Tasks, fixture, floors, scorer, codebook and labeller are the Stage 3 ones, unchanged.

## What ran
Arm A1 = A0 with the three stock discovery-first system messages removed and one neutral line inserted (stock messages 1, 3 and 4: "TOOL USAGE REQUIREMENT ... check what is available", "WORKFLOW ... FIRST: Call rosnode_list() and rostopic_list()", and "first retrieve a list ... almost always start by getting a list"; quoted in the protocol; the discovery-first text was in the prompt). 48 episodes (12 tasks × 2 repeats × qwen3.5:9b and gpt-6-luna), ROS domain 215, no pilot, no infrastructure loss, no truncation, timeout, access or provider problem; Qwen active context 65,536 verified; oracle checks before and after episodes 12, 24 and 36 were clean. Infrastructure event: the closeout oracle reported 3 nodes (`juniper`, `mantle`, `yonder`) as not listed in one un-retried `ros2 node list`, while all 24 direct parameter reads and all 19 topic endpoint checks matched and cleanup was verified; it came after the last episode, so no episode was lost, and it was not rerun (same class as the Stage 1a closeout flake).

## Results (supported-complete episodes; excess = requests - floor)
| model | depth | A0 excess / floor sum | A0 share | A1 supported | A1 excess / floor sum | A1 share |
|---|---|---|---:|---:|---|---:|
| Qwen | 2 | 40 / 24 | 167% | 8/8 | 18 / 24 | 75% |
| Qwen | 3 | 16 / 32 | 50% | 8/8 | 9 / 32 | 28% |
| Qwen | 4 | 26 / 40 | 65% | 8/8 | 20 / 40 | 50% |
| **Qwen all** | | 82 / 96 | **85.4%** | 24/24 | 47 / 96 | **49.0%** |
| Luna | 2 | 10 / 24 | 42% | 8/8 | 3 / 24 | 12.5% |
| Luna | 3 | 7 / 32 | 22% | 8/8 | 3 / 32 | 9.4% |
| Luna | 4 | 6 / 35 | 17% | 7/8 | 7 / 35 | 20.0% |
| **Luna all** | | 23 / 91 | **25.3%** | 23/24 | 13 / 91 | **14.3%** |
Paired A0 versus A1 by task, repeat and model (both supported-complete): Qwen 24 pairs, mean 1.46 fewer requests under A1, range -3 to 13, A1 fewer in 12, equal in 9, more in 3; Luna 23 pairs, mean 0.43 fewer, range -1 to 2, fewer in 11, equal in 9, more in 3. Supported-complete counts did not change (Qwen 24 to 24, Luna 23 to 23). Requests, input tokens and native operations fell (Qwen 178 to 143, 1.26M to 0.98M, 274 to 231; Luna 124 to 116, 633k to 518k, 306 to 241). The opening-listing habit on named entities fell from 8/18 to 0/18 for Qwen and 12/17 to 5/17 for Luna. Luna's one failure (`19-u4-openai-r0`, lines 26 to 82) walked past the right node up the whole upstream pipeline and reported `gantry`'s gain 28 instead of `quill`'s 59, the same wrong value as under A0 (`05-u4-openai-r0`): a stopping error, not a discovery effect.

## Remaining excess by kind (labels per request, same labeller)
- **Qwen (47 excess requests; avoidable share 91%):** 22 repeats, 11 recovery after short node names, 10 late stage calls, 4 unneeded exploration. Example: `22-u2-ollama-r0` and `38-u2-ollama-r1` (7 requests, floor 3): `param_get` with the short name `yarrow` fails (line 10), then `node_list` (line 16), the full-name read (line 22), and two repeated reads (lines 28 and 34). `46-u4-ollama-r1` (13 requests, floor 5, lines 10 to 76) has 2 exploration and 6 repeat requests. The two `service_info` loop episodes of Stage 3 did not recur (no episode has 10 or more repeat requests, so the sensitivity run removes nothing). Qwen got worse on the upstream template (21/24 versus 18/24 excess) and better on pointer (0/24 versus 6/24) and service (14/24 versus 44/24).
- **Luna (13 excess requests; 100% avoidable):** 10 late stage calls, 2 repeats, 1 recovery. In 11 episodes with excess, the first request was `service_info` on the named service in 6, `node_list` in 4, `topic_info` in 1: a call that is not a planned stage, with the planned stage-1 call after it (for example `00-v3-openai-r0` request 2; `01-h4-openai-r0` lines 12 to 71, which also has a repeated `param_list` request).

## Which branch applies
**Weak-model room remains** (frozen rule 3: Luna 14.3% is under 25%, Qwen 49.0% is at or above 40%). In plain words: on these tasks the ordinary prompt change removes most of the strong model's excess (25.3% to 14.3%, just under the 15% line that would count as closed for Luna) and about half of the weak model's (85.4% to 49.0%), leaving a weak-model gap made of repeated reads and recovery after short node names. Rule 1 ("closes") fails only because Qwen is above 25%. Luna's 14.3% is within one request of 15% (one more request would give 15.4%).

## What the data cannot show
- A0 ran on 2026-11-12 and A1 on 2026-11-13: different sessions, and Luna samples at the provider, so part of the Luna difference may be run-to-run variation; no A0 re-run was done.
- A1 removes three messages at once, so the result cannot say which one matters. Message 4 also carried "if you get an error, try again once" and "do not use a name until its availability is confirmed"; the rise in short-name recovery for Qwen (11 versus 8 requests) may relate to that (H, untested).
- Synthetic fixture, 12 tasks, two repeats; Qwen repeats are near-duplicates (temperature 0 with seed 42), though under A1 10 of the 12 task pairs were identical and two differed (`u3` 4 versus 7 requests, `u4` 7 versus 13).
- Not tested: any other prompt control, the effect on real ROSA use, or whether a method would beat A1.

## The one decision this points to
For the strong model the ordinary control already leaves little (14.3%, nearly all a first-request habit). The remaining room is a weak-model one (repeats, recovery after short names). The decision is whether the project's target is that weak-model residual, which is a different question from the one Stage 3 asked. No mechanism is proposed here.

## Revisions
No change to the frozen protocol, tasks, scorer or labeller after the first inference. The closeout oracle flake is described above. The frozen sensitivity rule (remove episodes with 10 or more repeat requests) matched no episode.

## Open questions (unattended run)
1. Luna's A1 share (14.3%) is on the edge of the 15% line; one request would change which rule-1 side it falls on. 2. `STUDY_INDEX.md` still describes the study "through Stage 3"; it needs a Stage 3b mention, which this addendum did not authorize. 3. The closeout listing flake was not rerun.
