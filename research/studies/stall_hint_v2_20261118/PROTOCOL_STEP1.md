# Stall hint v2, Step 1 (offline): protocol and pass bar, frozen before any new counting

2026-11-18, Asia/Taipei. Offline analysis only: no GPU, no ROS, no inference, no held-out files. This file is hashed (`PROTOCOL_STEP1.sha256`) before the Step 1 script is written or run. Source of the task: owner's overnight instruction (handoff `research/HANDOFF_CC_20261118.md`, "Overnight task: hint-only stall breaker v2").

## 0. Decision record (AGENTS.md preflight; labels per Section 12.1 of the research context)

- **Observed opportunity (F, from the recount, not re-derived here):** in 336 C1-type development episodes 66 (19.6%) contain a stall and 33.1% of their requests come after the first stall; bonsai-2:4b and lfm3:1.7b carry most of it (`decisions/2026-11-17-stall-opportunity-report.md`). This is exposure, not benefit.
- **Candidate vs control action difference (P):** control returns the tool result unchanged. Candidate returns the same result plus one appended hint text, only on a stall call. No tool is hidden, no argument is repaired, no extra LLM call. The model may still choose any action; the only difference is information in the observation.
- **Why the old design is not repeated:** the combined design failed its frozen safety bar because the second-stall *hide* could suppress a useful call (9 supported episodes). v2 has no hide, so that bar does not apply; a *misleading hint* is the new risk and is measured in B4 below.
- **Closest prior mechanisms (not novelty claims):** (1) pilot arm `C1+H2` in `small_model_harness_20261115/harness.py` (`h2_repair`, `candidates_for`, `append_hint`): unique-suffix repair, and for 2+ candidates an appended hint "Several full names end with X"; it fired on the first failed lookup of a name. (2) Round 1 answer gate "did you mean <full name>" (on `final_answer`). (3) Round 2 / v2 name rewrite (answer rewrite). (4) Pilot `FN` arm (Full name line). v2's incremental differences, all engineering choices and **unproven**: the trigger is a *stall* (repeat or second empty result), not the first failure; matching also covers substring matches and joined namespace+name names; the hint names the *kind* a seen name has (node, topic, service) and the offered tools that take that kind; it also fires on repeated list calls. It is not established that these differences matter; H2's own live result was within noise (`PILOT_REPORT.md`).
- **Known negative / caution (reported, not re-verified by me):** the owner reports that a plain "Repeated call" message did not stop loops earlier. So a hint without matching names carries no information and is counted separately (B5).
- **Fair evaluation and costs:** Step 1 is trace replay and cannot show that a model *follows* a hint; it can only show how often a hint with content would appear and whether that content agrees with what the recorded episode later did. Step 2 (live) is gated on this file's bar.
- **Smallest decision-changing next action and stop rule:** this offline count. If any bar below fails, stop, report, no live run.

## 1. Definitions (frozen)

**Population.** The same 1,248 development episodes and the same exclusions as `decisions/2026-11-17-stall-opportunity-protocol.md` and `2026-11-17-stall-episodes.jsonl` (pilot all valid arms, round 1 all arms, round 2 both arms). **Primary population for all bars: C1-type episodes (pilot `C1`, round-1 `C1`, round-2 `CONTROL`) of bonsai-2:4b and lfm3:1.7b**, because the loop that would receive the hint is the fixed loop and the weak models are tested first. Also reported (no bar): C1-type all four models; all arms all models (for the hint the 12-tool menu is assumed even where an older arm offered other tools). Fairness, ablation, name-fix and compaction runs are **not** included (different arms/fixtures; the recount population is kept for comparability); this is a stated limitation.

**Stall.** Exactly the recount rule (`decisions/2026-11-17-stall-recount.py`): rule (a) the call's tool and serialized result text equal an earlier call's tool and result text; rule (b) the second and subsequent empty/not-found result of the same tool since the last result that added a new full name to the ledger (task-text names seed the ledger; names include contiguous names and namespace+name joins); `final_answer` ignored; calls processed in logged order; union counted once. **Reproduction gate (B0):** my re-implementation must reproduce the recount's per-episode `stall_calls` for all 1,248 episodes exactly; else stop and explain.

**Fire.** One fire per stall call. The hint is appended to that call's result.

**Hint content (built only from the episode's own record before that call).**
- Ledger L = full names in the task text and in successful earlier results (contiguous names, joins, `nodes` list), as in the recount. Each name has a *kind set* from provenance: names in a `ros2_node_list` result or a join -> node; `ros2_topic_list` items -> topic; `ros2_service_list` items -> service; keys of a successful `ros2_node_info`/`ros2_topic_info`/`ros2_service_info` result -> node/topic/service; names under `Subscribers:`/`Publishers:` headings of a node-info result -> topic; under `Service Servers:`/`Service Clients:` -> service; otherwise kind unknown (shown without tool advice).
- Query: for each string given to an entity argument (`nodes`, `topics`, `services`, `node_name`, `topic`) or to a `pattern` argument, `q` = the last path segment after removing regex metacharacters (`^ $ . * + ? ( ) [ ] { } | \`); ignore `q` shorter than 3 characters.
- Matches M (from L, at most 5 shown, order: T1, T2, T3, then alphabetical): **T1** the typed name equals a ledger name; **T2** the typed string is the trailing whole path segments of exactly the ledger names that end with it (name-fix suffix rule), other than itself; **T3** `q` is a substring of the final segment of a ledger name, or that final segment (3+ characters) is a substring of `q`, not already in T1/T2.
- Tools suggested S: from the kinds of names in M, the offered tools that take that kind: node -> `ros2_node_info`, `ros2_param_list`, `ros2_param_get`; topic -> `ros2_topic_info`, `ros2_topic_echo`; service -> `ros2_service_info`. Tools that take no name (lists) are never suggested.
- **Informative fire:** M contains at least one T2 or T3 name (a full name different from what the model typed). **T1-only fire:** M contains only the typed name itself. **Empty fire:** no entity/pattern query or no match.
- **Kind-mismatch fire** (reported inside informative fires): the stalled tool takes kind K but every matched name has a known kind other than K.

**Needed next step (hindsight, from the recorded episode, no oracle).** For a fire at request r, P = the first call in a *later* request (> r) that is `ok`, carries an entity argument, and returns a nonempty result text never returned before by that tool in the episode. P may be absent (episode ended or no such call). *Pointed* = entity(P) is in the shown M **and** tool(P) is in S (if M has only unknown kinds, S is empty and *pointed-by-name* is reported instead; the bar uses the strict version unless stated). *Immediate* = P is in request r+1; *delayed* = P is in request >= r+2. The recorded trajectories had no hint, so this is agreement between the content and what the same session later did, not evidence that the model would follow the hint or that P was necessary.

**Supported episode.** Scorer v2 flag exactly as in the recount file (`supported`).

## 2. Pass bar (all must hold on the primary population; fixed now, not adjusted after counts)

| id | statement | reason |
|---|---|---|
| B0 | Reproduction: `stall_calls` equal to the recount for every one of 1,248 episodes. | A different stall definition would make every later number meaningless. |
| B1 | At least 10% of primary-population episodes have at least one **informative** fire. | Same pragmatic screening level as the earlier recount: below it a small live run has too little exposure (about 8 of 80 episodes per model-arm). |
| B2 | At least 50% of informative fires **in supported primary episodes that have a P** are *pointed* (strict: entity and tool). Denominator: first informative fire per such episode. | A hint whose content agrees with the later successful step less than half the time is more likely to distract than help. |
| B3 | Among the B2 pointed fires, at least 30% are *delayed* (P at r+2 or later). | If the model took that step in the next request anyway, the hint cannot change the action. |
| B4 | Among the B2 denominator, at most 25% are *contradicted*: the hint has matched names and a suggested tool set, but neither entity(P) is in M nor tool(P) in S. | Offline proxy for the misleading-hint risk (the new risk replacing the old hide). A divergent later path is not proof of harm. |
| B5 | At least 50% of all fires in the primary population are informative. | Empty or T1-only fires carry no new content; a plain repeat message is the known-failing pattern. |

**Outcome rule.** All of B0-B5 hold -> PASS (Step 2 may be written and frozen). Any fails -> FAIL, stop, no live run. If B2-B4 have fewer than 15 episodes in their denominator -> INCONCLUSIVE, treated as FAIL for the authorization to run live (no live run), and reported as such.

## 3. What will be reported (measured vs interpretation)

Counts of fires and their types per group/model; 20 sample hint texts (first of each type, fixed order, no cherry-picking); B0-B5 values; the same table on the two secondary populations (no bar); the cases where P exists but the hint is contradicted, listed by episode. Interpretation limits: development fixtures (synthetic, 4 models), repeated tasks/seeds are not independent, hindsight agreement is not a causal test, enriched round-2 extra seeds inflate pooled rates (round-2 CONTROL seeds 1-2 and extra seeds are shown separately).
