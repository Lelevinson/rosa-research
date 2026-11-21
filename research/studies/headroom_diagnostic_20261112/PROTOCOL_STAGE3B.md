# PROTOCOL_STAGE3B (frozen before any Stage 3b inference)

Frozen: 2026-11-13. Study-folder work only; no change to `src/rosa/`, baselines, `AGENTS.md` or Stage 0 to 3 files (new files only: `run_stage3b.py`, this protocol, `STAGE3B_LOG.md`, report). No commit, push or merge. Strong model only through the existing ChatGPT-plan OAuth path; no API key. Development evidence, no novelty claim, no method. Revisions after the first inference go in the "Revisions" section at the bottom. Unattended reading rule as in Stage 3: ambiguities are resolved by the most reasonable reading and time-stamped in `STAGE3B_LOG.md`.

## Question
After removing the discovery-first instruction from the prompt (arm A1), how much excess over the floor remains for Qwen and Luna on the same 12 Stage 3 tasks, and what kinds of excess remain?

## Preflight record (context §14.2)
1. Opportunity (F): Stage 3 found excess over arm A0 (Qwen 85.4%, Luna 25.3% of the floor, 95 to 100% avoidable); about 12 of Luna's 17 supported non-service episodes opened with a listing although the entity was named. Whether a plain prompt change removes it is unmeasured. 2. Mechanism: none; the treatment is a prompt change in the study harness. 3. Novelty: none; this is the strongest ordinary control. 4. Fair evaluation: same tasks, floors, fixture, models, settings, scorer, labeller and codebook as Stage 3; only the system-prompt list differs. 5. Decision-changing action: the frozen rules below decide whether the room found in Stage 3 survives the ordinary control. Closest prior study: Stage 3 (`REPORT_STAGE3.md`).

## Arm A1 (frozen)
A0 (stock system prompts with the single sequential-execution message replaced by "Independent tool calls whose arguments are already known may be made together in one response.") plus: the three stock system messages that instruct the agent to check what is available or to list nodes and topics first are removed, and one neutral line is inserted at the position of the first of them:
> Use the task text and earlier tool results to decide which tool to call next; list entities only when you do not already know their names.

The discovery-first text is present in the prompt. Exact stock messages removed (`src/rosa/prompts.py`, indices 1, 3 and 4 of `system_prompts`):

**Stock message 1:**
> CRITICAL - TOOL USAGE REQUIREMENT: When a user asks you to perform an action involving ROS nodes, topics, or services, you MUST IMMEDIATELY use your tools to check what is available before responding. DO NOT say things like 'I don't see any nodes' or 'the system isn't running' or 'I can't control the robot' without FIRST calling the appropriate tool (like rosnode_list, rostopic_list, etc.) to verify the actual current state. Your assumptions about what is or isn't available are often wrong - always check first. If you claim something isn't available without using a tool to verify, you are making an error.

**Stock message 3:**
> WORKFLOW FOR ACTION REQUESTS: When a user asks you to perform a robotic action (move, draw, control, etc.), follow this workflow: 1. FIRST: Call rosnode_list() and rostopic_list() WITHOUT any parameters to see what's available.    Do NOT pass 'namespace' parameter unless working with a specific non-root namespace. 2. SECOND: If relevant nodes/topics exist, proceed with the action immediately. 3. THIRD: Only if the tools show nothing is available should you explain that to the user. Do NOT skip step 1. Do NOT describe what you 'would do if the system were running' - check if it IS running first.

**Stock message 4:**
> When asked to provide names of topics or nodes, first retrieve a list of available names using the appropriate tool or command. Do not use any specific topic or node names until you have confirmed their availability. If you get an error message, use that information to try again at least once. If you still can't get the information, let the user know. You should almost always start by getting a list of relevant nodes and topics.

Reading: the addendum names "check what is available or list nodes and topics first"; messages 1 and 3 do so explicitly, and message 4 also does ("first retrieve a list ... almost always start by getting a list"), so all three are removed. Side effect: message 4 also contained "If you get an error message ... try again at least once" and "Do not use any specific topic or node names until you have confirmed their availability"; both go with it. Implemented only in the harness subclass `A1ROSA._get_prompts` (`run_stage3b.py`); each trace stores the prompt list actually sent and its hash. Offline check: A0 hash `7963b35c3a2a1efd09ab8eebf7b700b3104dada214f4a940aa92b1bd0a1b5bfc` (identical to Stage 1 to 3), A1 hash `7acbb0555cba9f406f4915e6d96da1d69bfdf7360d48c2d37c40e4232954a209`; 9 messages become 7; registry unchanged (47 tools).

## Design
- The 12 Stage 3 tasks, exact requests from `stage3_tasks.json`, floors depth + 1 (3, 4, 5), the same generated fixture (seed 20261113, 19 stock-rclpy nodes in `/plant32`), unchanged.
- 12 tasks × 2 repeats × 2 models = **48 episodes**, one pass, shuffled per repeat block with the new seed **20261115** (saved in the run folder). No pilot (harness plumbing unchanged). Cap 48; an episode lost to infrastructure failure (fixture died, Ollama or provider unreachable, oracle mismatch) may be replaced once under a new ID, the lost one kept and counted; model failures are never rerun. No A0 re-run: A1 is compared with the Stage 3 A0 numbers from 2026-11-12 (different session and time; temperature 0 with seed 42 makes this a minor issue for Qwen, a larger one for Luna).
- Models and settings as Stage 3: `qwen3.5:9b` (temperature 0, seed 42, reasoning off, `num_ctx` 65536 verified from `/api/ps`, `num_predict` 4096, client timeout 90 s, max iterations 40, episode timeout 900 s); `gpt-6-luna` through the ChatGPT-plan OAuth path (explicit model, `parallel_tool_calls` true, no temperature or seed, episode timeout 600 s, max iterations 40).
- ROS domain **215**, localhost only; oracle check before, after episodes 12, 24, 36, and after (3 retries for evaluation-only reads); fixture stopped, domain verified empty and daemon stopped at the end and after any abort.
- Scoring, labelling and aggregation unchanged from Stage 3: exact (`first_object`, `canonical`, `differences` against the declared answer) AND support screen = supported-complete; excess = requests - floor; mean excess share = sum(excess) / sum(floor) over supported-complete episodes; relabel with the stage-based labeller (`stage3_labels.py`: RED, REC, LATE, NOARG, EXPLORE, NEEDED, FIN) for episodes with excess > 0, avoidable = RED + REC + LATE + NOARG.
- Stop rules: ChatGPT-plan access or throttling error (the Qwen part may continue), Ollama unreachable, fixture cleanup failure, oracle mismatch, cap reached. Overall wall-clock limit 8 hours from the start of Stage 3b; on any stop, clean up, verify and report what exists.

## Decision rules (frozen; supported-complete episodes only; denominators stated; compared with the Stage 3 A0 numbers: Luna 25.3% = 23/91, Qwen 85.4% = 82/96)
Each model must be interpretable (supported-complete rate at least 50% and at least 8 supported-complete episodes); otherwise the branch is inconclusive and accuracy is reported first. Evaluated in this order:
1. **Ordinary control closes it:** Luna's mean excess is under 15% of the floor AND Qwen's is under 25%.
2. **Room remains for Luna:** Luna's mean excess is at least 25%. Report which request kinds remain.
3. **Weak-model room remains:** Luna under 25% and Qwen at least 40%. Report separately, as sensitivity and not as the rule, Qwen's excess with every episode that has 10 or more RED requests removed (the Stage 3 `service_info` loop episodes), and which remaining excess is repeats, recovery after short names, late stage calls or exploration.
4. **Inconclusive:** anything else; state what would settle it.
Also reported: A0 versus A1 paired by task, repeat and model among pairs where both arms are supported-complete (mean request difference A0 minus A1, range, signs), the change in supported-complete counts, and the number of episodes whose first request is a listing although the entity is named.

## Reading limits
Same synthetic read-only fixture; Qwen at temperature 0 gives near-duplicate repeats; Luna samples at the provider and A0 ran in a different session; A1 changes four prompt messages at once, so a result cannot say which of them matters; no claim about real ROSA use.

## Revisions
(none yet)
