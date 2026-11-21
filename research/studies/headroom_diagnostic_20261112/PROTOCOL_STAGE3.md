# PROTOCOL_STAGE3 (frozen before any Stage 3 inference)

Frozen: 2026-11-13. Study-folder work only; no change to `src/rosa/`, baselines, `AGENTS.md`, Stage 0 to 2a files or the shared context files. Development evidence, no novelty claim, no selected algorithm, no method started. Revisions after the first inference go in the "Revisions" section at the bottom, never into this text. Unattended reading rule: ambiguities are resolved by the most reasonable reading, time-stamped in `STAGE3_LOG.md`.

## Question
On tasks whose steps depend on earlier results and whose per-task minimum is higher than in the six baseline tasks, do ordinary controls (the deconflicted prompt, arm A0) leave real excess over the minimum, for the weak model, the strong model, or both?

## Preflight record (context §14.2)
1. Opportunity (F/R): Stage 1c Step 1 showed the Qwen A0 excess on the six baseline tasks was entirely avoidable requests and the strong model still showed the same serialization in one of two repeats; dependency-driven requests were few. Whether deeper dependent tasks change that is unmeasured. 2. Mechanism: none. 3. Novelty: none claimed; this is a measurement of the strong ordinary control on harder tasks. 4. Fair evaluation: same prompt change, harness, model settings and scorer rules as Stage 1; the floor is computed from the generated graph and verified by a hand-written minimal sequence run against the real tools. 5. Decision-changing action: the gate below decides whether any method work is worth starting; stop rule in the decision rules. Closest negative studies: Stage 1c, Stage 2a (`REPORT_STAGE2A.md`), AutoTool iteration.

## Fixture and tasks (built and checked before this freeze)
- Seed 20261113 (`stage3_build.py`); 19 stock-`rclpy` nodes in namespace `/plant32` (`stage3_node.py`, `stage3_graph.json`); entity names, parameter values and message types generated from the seed; none reused from the baseline fixture.
- 12 tasks (`stage3_tasks.json`): four templates, depths 2, 3, 4: **u** upstream data-flow trace (topic to publisher to input topic to publisher to parameter), **p** parameter-pointer chain (a parameter names the next node), **h** hub neighbourhood with fan-out (inputs of a node, their publishers, their parameters; the depth-3 and depth-4 stages are three independent reads in one request), **v** service-provider route (node_list, node_info over all nodes, parameter reads; the discovery stage counts in the depth). All read-only.
- Depth = number of sequential observation stages; floor = depth + 1 (final answer); independent reads inside a stage are one stage. Floors 3, 4, 5.
- Floor verification (done, no model): `stage3_floorcheck_20261112T223728Z`: the oracle matched the generated graph (all parameters, publisher and subscriber endpoints, service owners); every task's hand-written minimal sequence ran with the real ROSA tools in exactly `depth` stages with every argument taken only from the task text and earlier stages, and the answer equalled the declared truth. All 12 floors are justified; none dropped.
- Ground truth is the declared graph, confirmed by the direct oracle read; runs abort on oracle mismatch. The evaluation-only oracle may retry a failed read up to 3 times (all attempts saved).

## Arms, models, settings
- Arm **A0** only: the single "CRITICAL - SEQUENTIAL TOOL EXECUTION" system message is replaced in place by "Independent tool calls whose arguments are already known may be made together in one response." via the study harness subclass (`StageROSA`); full 47-tool stock registry; observation-only guard; `src/rosa/` untouched; prompt lists and hashes saved in each trace.
- `qwen3.5:9b` at `http://172.30.80.1:11434`: temperature 0, seed 42, reasoning off, `num_ctx` 65536 (active context read from `/api/ps` after the first episode and must equal 65536), `num_predict` 4096, client timeout 90 s, executor max iterations 40, episode timeout 900 s.
- `gpt-6-luna` through the existing ChatGPT-plan OAuth path (`rosa-llm`), explicit model name read from the live catalog, `parallel_tool_calls` true, no temperature or seed, episode timeout 600 s, max iterations 40. No API key.
- ROS domain 214, localhost only, one fixture session for the whole run; oracle check before, after episodes 12, 24, 36 of the main run, and after; fixture stopped and verified empty and the daemon stopped at the end (and after any abort).

## Design
- **Pilot:** 4 Qwen episodes, one task per depth plus one fan-out task: `u2`, `p3`, `v4`, `h3`. Pilot episodes check harness plumbing (answer parsing, no truncation, scorer) and are reported separately; no task, scorer or threshold changes follow from pilot results. They count toward the cap.
- **Main run:** 12 tasks × 2 repeats × 2 models = 48 episodes, one pass. Each repeat block (the 24 task × model cells) is shuffled with seed **20261114**; schedule saved. Total with the pilot: 52 = the cap.
- Infrastructure losses (fixture died, Ollama or provider unreachable, oracle mismatch) may be replaced once under a new ID; the lost episode is kept and counted. Model failures are never rerun.

## Scoring (frozen)
- **Exact:** first JSON object in the final answer equals the task's declared answer (vendored `baseline_audit.first_object`, `canonical`, `differences`; extra fields and wrong types fail). **Support screen:** every requirement in the task's `support` list holds in the trace: `param` requires a successful `ros2_param_get` for that node and parameter returning that value; `text` requires the string in a successful tool result or the task text. **Supported-complete = exact AND support.** The baseline scorer's `get_type_description` requirement is not used.
- Episodes that fail are read by hand; verdicts recorded with trace lines.
- Per episode: requests, floor, excess = requests - floor, calls per request, multi-call requests, input and output tokens, native operations (`ros_start`), native failures, seconds, capacity events (`done_reason` length or provider length status, iteration cap, timeout, model error).

## Aggregation definitions (frozen)
- **Mean excess as a share of the floor** for a model = sum over its supported-complete episodes of (requests - floor) divided by the sum of floors of the same episodes. Denominators (episodes and floors) are reported. Also reported by depth.
- **Relabel of excess:** for every supported-complete episode with excess > 0, label every request after the first with the codebook (`CODEBOOK.md`), request by request, rule first pass plus manual review as in Stage 1c. **Avoidable** requests = RED, REC, or DEP whose arguments were available at least one request earlier; **needed** = JUDG, or DEP that depends on the preceding result. Excess is "mostly avoidable" for a model if, summed over those episodes, min(avoidable requests, excess) is more than 50% of the total excess.
- A model whose supported-complete rate is under 50% is reported by accuracy first; its excess is not interpretable and it cannot trigger "room"; the "no room" and "room" branches then require the other model's evidence as stated below.

## Decision rules (frozen; both models judged separately; supported-complete episodes only; denominators stated)
- **Room for a method:** mean excess is at least 25% of the floor for Luna, OR at least 40% for Qwen while Luna's is below 25% (a weak-model gap), AND the relabelled excess is mostly avoidable (not dependency-driven) for the model(s) that meet the threshold.
- **No room:** both models' mean excess is under 15% of the floor (both must be interpretable).
- **Inconclusive:** anything else, or fewer than 8 supported-complete episodes for a model; state what would settle it.
- If a model's supported-complete rate is under 50%, report accuracy first and say excess is not interpretable for it.
- No claim of novelty, success or a selected algorithm; no mechanism proposal.

## Stop and abort rules
ChatGPT-plan access or throttling error (the Qwen part may continue), Ollama unreachable, fixture cleanup failure, oracle mismatch, cap reached. Overall wall-clock limit 8 hours from 2026-11-13 06:32 Asia/Taipei (2026-11-12 22:32 UTC); fixture building was limited to 3 hours and took well under one. On any stop, clean up, verify the domain empty and stop the daemon, then report what exists.

## Reading limits
All tasks are synthetic and read-only on one generated fixture; depth is by design, not a measured property of real ROSA use (`STAGE3_USE_CASES.md`). Qwen at temperature 0 gives near-duplicate repeats; Luna samples at the provider. Two repeats per cell.

## Revisions
(none yet)
