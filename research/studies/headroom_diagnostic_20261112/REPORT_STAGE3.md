# Stage 3 report: do ordinary controls leave excess on deeper dependent tasks? (2026-11-13)

Development evidence on a synthetic read-only fixture; no novelty claim, no method selected or started. Frozen plan `PROTOCOL_STAGE3.md`; tables `STAGE3_TABLES.md`; log `STAGE3_LOG.md`; task grounding `STAGE3_USE_CASES.md`; raw traces `research/_artifacts/runs/headroom_diagnostic_20261112/stage3_20261112T225309Z/` (hashes in `MANIFEST_STAGE3.sha256.json`).

## What ran
12 tasks (4 templates: upstream trace, parameter-pointer chain, hub with fan-out, service-provider route; depths 2, 3, 4; floors 3, 4, 5) on a generated fixture of 19 stock-rclpy nodes (seed 20261113). Floors were verified by running each task's hand-written minimal stage sequence against the real tools (all 12 correct, `stage3_floorcheck_20261112T223728Z`). Arm A0 only. 48 main episodes (12 tasks × 2 repeats × 2 models: qwen3.5:9b and gpt-6-luna) plus the 4-episode Qwen pilot, 52 total (the cap). No infrastructure loss, no truncation, iteration cap, timeout, access or provider problem; six oracle checks agreed with the generated graph; fixture stopped, domain verified empty, daemon stopped. Wall time about 1 h 20 min.

## Results (supported-complete episodes; excess = requests - floor)
| model | depth 2 (floor 3) | depth 3 (floor 4) | depth 4 (floor 5) | all |
|---|---|---|---|---|
| Qwen: supported / episodes | 8/8 | 8/8 | 8/8 | 24/24 |
| Qwen: excess / floor sum | 40 / 24 = 167% | 16 / 32 = 50% | 26 / 40 = 65% | **82 / 96 = 85.4%** |
| Luna: supported / episodes | 8/8 | 8/8 | 7/8 | 23/24 |
| Luna: excess / floor sum | 10 / 24 = 42% | 7 / 32 = 22% | 6 / 35 = 17% | **23 / 91 = 25.3%** |
Qwen's depth-2 figure is dominated by two identical episodes (`20-v2-ollama-r0`, `44-v2-ollama-r1`) that repeat the same `service_info` call 15 times (trace lines 10 to 94) before listing nodes: 16 excess requests each; temperature 0 makes the two repeats the same behaviour. Without them Qwen is 55.6% (50 / 90). Luna's one failure (`05-u4-openai-r0`, 10 requests) reported a wrong `upstream_gain` (28, true 59) and is excluded from the denominators; including its excess would give 29.2%.

## Relabelled excess (codebook, request by request, from each task's verified minimal stages)
- **Luna: 23 of 23 excess requests are avoidable.** Requests carrying an avoidable label total 26 (15 stage-1 calls issued after an unneeded opening discovery listing, for example `16-v2-openai-r0` request 3, line 19, and `27-h2-openai-r1` requests 2 and 3, lines 12 and 19; 10 extra calls whose arguments were in the task text or absent; 1 repeat); counted per episode and capped at that episode's excess they account for all 23. In 12 of Luna's 17 supported non-service episodes the first request was a node, topic or service listing although the entity is named in the task; in the 6 service-route episodes that listing is a needed stage. No excess request was dependency-driven.
- **Qwen: 78 of 82 are avoidable** (50 repeats, 8 recovery requests after short node names failed, 18 late stage calls, 2 extra calls), 4 are unneeded exploration that needed an earlier result (for example `17-u4-ollama-r0` request 5, line 28). The u4 episodes also repeat the final `param_get` twice (requests 8 and 9).
- The remaining requests in every episode are the dependency stages themselves; the data show no excess caused by the dependency chain.

## Which frozen rule branch applies
**Room for a method**, by the frozen rule: Luna's mean excess is 25.3%, at or above 25%, and the relabelled excess is mostly avoidable (100%). In plain words: on tasks whose steps depend on earlier results, the deconflicted prompt still leaves real excess over the minimum for both models, and nearly all of it is avoidable rather than forced by dependencies.
Robustness: Luna's value is on the threshold edge (one request fewer would give 24.2%). Had it been below 25%, the weak-model clause would apply instead (Qwen at or above 40% while Luna below 25%; Qwen is 85.4%, or 55.6% without its loop episodes, with 95% avoidable), which gives the same branch.

## What the data cannot show
- That a method is needed. Only arm A0 was run: the stock prompt still contains the discovery-first messages ("check what is available", "FIRST: call rosnode_list and rostopic_list"), and much of the avoidable excess is that opening listing and its follow-ups (H, untested). Whether a plain prompt change removes it was not measured, so the room is over A0, not over the best ordinary control.
- Anything about real ROSA use: the tasks and depths are synthetic by design (`STAGE3_USE_CASES.md`: no usage statistics exist in the repository).
- Qwen's repeats are near-duplicates (temperature 0), so Qwen's 24 episodes carry about 12 independent behaviours; Luna has two repeats per task. One strong model, one weak model, one generated fixture; Luna's share is on the threshold.
- Native-operation and wall-time effects were not rules here (Luna 306 native operations in 124 requests; Qwen 274 in 178).

## Revisions
No change to the frozen protocol, tasks, scorer or thresholds after the first inference. Analysis-stage corrections, all after seeing results and disclosed: (1) a first lexical "arguments available earlier" labeller was replaced by one based on the verified minimal stages, because it counted chain steps as batchable whenever an earlier listing had printed their names; (2) the stage labeller was then corrected for identical repeated calls and for re-issuing a failed stage (both affect label type, not request counts). Readings chosen unattended are in `STAGE3_LOG.md`.

## The one decision this points to
Whether the avoidable excess is already closed by an ordinary prompt control (not yet measured) or needs a method. That is a separate, authorized-only step; no mechanism is proposed here.

## Open questions (unattended run)
1. The frozen branch is "room for a method", but the room is measured over arm A0, not over the best ordinary prompt; the shared state files still describe Stage 3 as in progress and must be updated by the separate maintenance step.
2. "Mean excess" uses supported-complete episodes only (as frozen); with Luna's failed episode included the share is 29.2%.
3. Which of Qwen's two loop episodes to treat as independent was not decided; both are in the numbers above.
