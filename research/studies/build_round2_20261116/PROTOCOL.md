# Build round 2 protocol: sweep completion (live) + answer rewrite (shadow). FROZEN 2026-11-16 before any code of this round and before any episode.

Source: `Claude outputs/2026-11-16_PROMPT_CLAUDECODE_round2_sweep_live.md` (context mirror), build brief copied verbatim in section 9. Development tasks only. No held-out data. Scorer v2.0 untouched (sha256 `c6b02716...`). `uv` only. Local commits only; no pushes. No prompt, tool schema or tool description is changed. A rule is never patched after results are seen; a rule that cannot be implemented as written stops the run and is reported.

Owner decisions (2026-11-16): run the sweep completion live test as designed (two arms, about 350 episodes); answer rewrite in SHADOW only (both arms; never-seen names are counted, not rejected); stall breaker parked; the "stock executor + fixed prompt + errors as text" arm and the fixed-loop ablation are NOT run in this job.

## 1. Preflight decision record (AGENTS.md "Mandatory research context and preflight"; context Sections 0-4, 12, 14 and the closest negative evidence read)
1. Observed opportunity and evidence: offline replay of 400 recorded fixed-loop episodes (`offline_replay_20261116/REPORT.md`): the two-call trigger fires in 22 episodes, predicted 93 saved requests (3.8% of requests), 87% of the saving in 5 cells, 79 of 93 on task `v2`. Prediction from traces only (label R/F-offline); it assumes the model stops once the sweep result is in context.
2. Candidate vs control action difference: CONTROL leaves the model to read the remaining names one by one; SWEEP reads them for the model at the first moment a two-call same-tool pattern appears. Different action on the same trace: yes (the extra result appears at request k).
3. Closest prior mechanisms (not judged here; related papers to compare later, unverified): list arguments of build round 1 (adoption 4 of 80, savings not attributable to the mechanism), reuse caches H1e/H1n (54 reuse events saved no model requests), LLM-Tool Compiler 2405.17438 (fused tools). Round 1 add-ons never changed the model's batching; this mechanism acts without the model's cooperation.
4. Fair evaluation and costs: same runner, same models/settings, CONTROL = identical loop with the trigger in shadow. Costs counted: extra tool runs, real extra result tokens, requests and tokens after the first firing, supported answers (scorer v2.0).
5. Smallest decision-changing next action and stop rule: this run. A PASS only justifies a later held-out design; FAIL/NOT SHOWN/INCONCLUSIVE are reported as they are. Stop rules in section 7. Risk: the pass bars are on development tasks, four models, and the enriched tasks are chosen from the same traces that motivated the trigger (selection of the opportunity, see section 3).

## 2. What is tested
| arm | what it is |
|---|---|
| CONTROL | fixed loop (build round 1 arm C1, unchanged) + sweep in SHADOW (same trigger code, logs `sweep_shadow`, takes no action) + answer rewrite in SHADOW |
| SWEEP | fixed loop + sweep LIVE + answer rewrite in SHADOW |
Both arms run through one class (`round2_harness.Round2Arm`) so they differ only by the flag that turns the sweep action on. The round 1 answer gate and bare-text nudge are OFF in both arms (the arm is built as C1; gate in shadow logging only, as in the round 1 control). No rejection, nudge or gate message is sent in either arm.

## 3. STEP 1: V1 trigger counts (computed from `offline_replay_20261116/results.json` by running the replay's own V1 code; totals checked: 31 triggers, 22 episodes, replay protocol sha `4056dc029318c174...`). Full numbers: `V1_COUNTS.json` (script `v1_counts.py`).
- Triggers per task: h4 11, v2 19, u3 1 (all other tasks 0). Episodes with a trigger: h4 8, v2 13, u3 1.
- Triggers per model: lfm3:1.7b 5, qwen3.5:9b 7, gpt-oss:20b 7, bonsai-2:4b 12.
- Triggers per tool: ros2_node_info 18, ros2_param_get 7, ros2_param_list 3, ros2_service_info 2, ros2_topic_info 1, ros2_topic_echo 0.
- Triggers on ros2_topic_echo: 0, so the stop condition "any V1 trigger on ros2_topic_echo" is not hit.
- Enriched tasks = every development task with at least one V1 trigger = **h4, u3, v2**. Other development tasks: p3, e1h_amb_1, e1h_amb_2, e1h_abs_1, e1h_abs_2, e1h_chg_1, e1h_chg_2.
- Selection caveat (recorded now): the enriched tasks were selected because the recorded traces triggered; the first-fire rate of this run is therefore not an estimate of the rate on other tasks.

## 4. STEP 2: sweep completion, rules as implemented (brief wording first, interpretation where the brief leaves a detail open)
Request index k = the model request that produced the call (the harness's request counter, same as `model_end` count in traces).
- Trigger (checked when a call of eligible read tool T in request k has finished and returned a result without raising): request k-1 has a call of the same T; all other arguments equal (missing = default); different entity name; both names in one group of a successful result earlier than request k-1. Group = names of one JSON list value or one text section of a result (offline replay `episodes.groups_of`, unchanged). Several qualifying groups: take the smallest (ties: first found). A list-argument call (`nodes`, `topics`, `services`) counts as one call per name.
- Sweep set = group minus names called (by T with the same other arguments) in request k minus names T already ran on with the same other arguments (including names covered by an earlier sweep). Empty: no firing.
- Limits: at most 20 names in group order; stop adding when the real result size passes 3000 tokens. Interpretation: results are run in group order one name at a time; token size of a result = characters of its JSON text / 4; an item whose result would take the running total above 3000 tokens is not appended and the sweep stops there (it counts as an extra tool run and as cut). Names cut by either limit are listed in the fixed line.
- Eligible T: `ros2_param_get`, `ros2_param_list`, `ros2_node_info`, `ros2_topic_info`, `ros2_service_info` (read tools of the 12-tool menu with an entity argument per `episodes.entity_argument`; `ros2_topic_echo` excluded).
- Action (SWEEP only): run T once per sweep name with the same other arguments (a list-argument tool gets a list of one name; the result for that name is taken from the returned dict), append the results keyed by full name to the tool result of the first triggering call of request k, with the fixed line below. An item failure (error text/dict, or a raised exception) stays in its own entry as `{"error": ...}`. At most one firing per request (the first triggering call); later calls of the same request are not evaluated for firing.
- Names "called in request k" are read from the model's tool calls of that request (captured when the response arrives), so calls not yet executed are already excluded.
- Sweep results count as successful tool results for the ledger (their names and groups can serve later triggers) and for the answer-gate/rewrite name ledger. Scoring adapter (`score_round2.py`): the triggering call's row uses its ORIGINAL result (logged in `sweep_fire`), and each swept item becomes one ordinary single-entity row (same expansion idea as round 1's `list_item`). Unit test: with no sweep the adapter equals scorer v2.0 on recorded traces.
- Shadow mode: same trigger code and same state updates as live (covered names are marked as if swept; no tool is run); logs `sweep_shadow` (request index, T, group source, sweep set, names cut by the group limit only) and takes no action.
- Logging for every firing: `sweep_fire` / `sweep_shadow` with request index, T, group source (task of the result that listed the group: tool and request), sweep set, names cut, extra tool runs, real extra result characters and tokens (chars/4), original result.
- **FIXED LINE (frozen wording).** `Also read with the same arguments, for other names from the same list (results keyed by full name): {names read, comma-separated}.` If a limit cut the sweep, this second sentence follows in the same line: ` Not read (limit reached): {names not read, comma-separated}.` Placement: for a dict result the line is stored under the key `also_read_note` and the keyed results under `also_read` (added after the original keys); for a text result the line and the JSON of the keyed results are appended after a newline.

## 5. STEP 3: answer rewrite (shadow in both arms)
At the final answer (`final_answer` with a non-empty object): ledger = `answer_gate.allowed_names(task text, successful tool outputs)` (round 1 name rule; includes sweep outputs in the SWEEP arm). Any name-like string in a value or a nested key (top-level keys are not rewritten, as in the replay) that is not an exact ledger name and is the trailing part (whole final path segments) of exactly one ledger full name is replaced (`replay.rewrite`, copied unchanged). Never invent a name. 2+ candidates: log `would_reject_ambiguous`. A full name never seen: log `would_reject_never_seen` and whether the ledger has listed-but-unread entities. The submitted answer is NOT changed. Both the original and the rewritten answer are scored with scorer v2.0 on the same rows (`rewrite_shadow` event holds both).

## 6. STEP 4: design
- Models: lfm3:1.7b, qwen3.5:9b, gpt-oss:20b, bonsai-2:4b. Same settings as build round 1: think false, temperature 0.7, num_ctx 65536, num_predict 4096, 40-iteration cap, 90 s HTTP timeout, 900 s episode timeout, ROS domain 220 localhost only, same fixtures and oracle/cleanup checks (`run_pilot.session`), Ollama at the Windows host as in round 1, prompt = pilot A1 prompt + final_answer line, unchanged.
- Cells: enriched tasks h4, u3, v2: seeds 1..10 per model per arm = 3 x 10 x 4 x 2 = 240 episodes. Other tasks (7): seeds 1,2 = 7 x 2 x 4 x 2 = 112. Total 352. The same seed is used in both arms of a cell.
- Order: one fixture session per (model, environment); both arms' cells of that session are shuffled together with `random.Random(f"{MASTER_SEED}-{phase}-{model}-{env}")`, MASTER_SEED = 20261118.
- Smoke (phase "smoke", never in totals): 2 cells per arm = 4 episodes: bonsai-2:4b task v2 seed 2 and qwen3.5:9b task h4 seed 1, both arms.
- Add-on if V-c fails (ONCE): seeds 11..15 on h4, u3, v2, 4 models, both arms (120 episodes), phase "addon".
- One `RESULTS_LOG.jsonl`, append-only, rows from the first run on (smoke rows marked phase "smoke").
- Unit test before the run (V-a): with no trigger the SWEEP arm's request payloads (prompt messages, offered tool schemas, tool results fed back) equal CONTROL's.
- A cell with a backend crash or a missed scripted change is listed as a validity defect and keeps its label; the cell is not silently rerun.

## 7. Stop conditions (stop, write down why, report; do not improvise)
Another GPU/ROS job found running; Ollama unreachable (`run_pilot.session` rule); oracle mismatch; write command reaching ROS; cleanup failure; 6 h wall limit per session; smoke surprise (crash, a sweep that runs a write tool, an arm that behaves identically because the flag did nothing, unexpected payload difference, shadow log missing); a rule that cannot be implemented as written; V1 trigger on ros2_topic_echo (not the case). After a stop nothing is patched silently: any code fix needed for a crash is logged in BUILD_LOG.md with the reason, and no rule of this protocol changes.

## 8. STEP 5: analysis definitions and BARS (frozen)
Unit = the FIRST firing (live or shadow) in an episode. Per event: re-ask = any later request (index > k) whose calls are all the same T, same other arguments, with every name in the sweep set or already read by T; requests after fire = number of model requests after request k until the end of the episode; tokens after fire = input + output tokens of those requests (reported usage); supported = scorer v2.0 `supported_complete` of the submitted answer; hit cap = iteration cap reached. Report per arm, per model, per task. Later firings in an episode are reported separately and are not used for the bars. Arms are also paired by cell (same task, model, seed) for descriptive purposes.

BARS:
Validity (failure = invalid run, fix and rerun, say so):
- V-a payload identity test passes.
- V-b first-fire episode counts of the two arms differ by less than a factor of 2.
- V-c at least 15 first-fire events per arm from at least 3 models. If not, add 5 replicates on the enriched tasks ONCE (seeds 11..15), then judge as is; still below 15 = INCONCLUSIVE.
Sweep PASS needs all:
- P1 re-ask rate in SWEEP <= 25%.
- P2 mean requests after fire lower in SWEEP by >= 1.0 per event; median not higher; direction holds when the single largest CONTROL event is dropped.
- P3 mean tokens after fire lower in SWEEP.
- P4 hand-read every fired SWEEP episode that ends unsupported: 0 where the sweep caused it (the answer uses a wrong name or value from the sweep result, or the next request fails on length or parsing).
Sweep FAIL if any: re-ask rate >= 50%; mean requests after fire not lower; 2 or more P4 harm episodes. Exactly 1 P4 harm episode: give the owner the trace. Otherwise: NOT SHOWN.
Rewrite PASS: 0 supported answers become unsupported over all final answers in both arms. FAIL: 1 or more. Also report: unsupported -> supported count, distinct cells and models; would-reject counts and whether any would-reject answer was supported.

## 9. Report (REPORT.md, usual five-row header)
State pass / fail / not shown / inconclusive against each bar. Per-model and per-task event tables. Share of events on the largest task. Validity defects (backend crash, missed scripted change) listed, labels unchanged. Five hand-read fired episodes with trace paths. No novelty or significance claims; whole-arm totals are shown for the record only and must not be used as evidence. Anything about the stock-executor arm or the fixed-loop ablation is out of scope.

### Build brief (verbatim from the prompt file)
```
BUILD ROUND 2 LIVE TEST: sweep completion (2-call trigger) + answer rewrite in shadow.
Development tasks only. No held-out data. Scorer v2.0 untouched. uv only. Local commits allowed; no pushes.
Do not change any prompt, tool schema or tool description. Do not patch a rule after seeing results; report instead.

STEP 0. Freeze first.
Write PROTOCOL.md with the rules, arms and bars below, hash it, commit, then build. If a rule below cannot be
implemented as written, stop and tell the owner; do not adapt it.

STEP 1. Read from offline_replay_20261116/results.json and put in the protocol before any run:
- V1 trigger counts per task, per model and per tool.
- Enriched tasks = every development task with at least one V1 trigger.
- If any V1 trigger is on ros2_topic_echo, stop and tell the owner.

STEP 2. Build sweep completion on the fixed loop (reuse the replay's ledger and group code and the round 1
list executor).
- Trigger: request k has a call of read tool T; request k-1 has a call of the same T; all other arguments
  equal (missing = default); different entity name; both names in one group of a successful result earlier
  than request k-1. Group = names of one JSON list value or one text section of a result. Several qualifying
  groups: take the smallest.
- Sweep set = group minus names called in request k minus names T already ran on with the same other
  arguments. Empty: no firing.
- Limits: at most 20 names in group order; stop adding when real result size passes 3000 tokens.
- Eligible T: read tools of the 12-tool menu with an entity argument, except ros2_topic_echo.
- Action: run T on each sweep name; append the results, keyed by full name, to the tool result of the
  (first) triggering call in request k, with one fixed line: which names were also read, and which names
  of the group were NOT read if a limit cut the sweep. An item failure stays in its own entry.
- Sweep results count as successful tool results for the ledger, and are expanded to per-item rows by the
  round 1 scoring adapter. Unit test: adapter equals scorer v2.0 on recorded traces without sweeps.
- Freeze the fixed line's wording in PROTOCOL.md before the first episode.
- Shadow mode: same trigger code, logs sweep_shadow (request index, T, sweep set), takes no action.
- Log every firing: sweep_fire / sweep_shadow with request index, T, group source, sweep set, names cut,
  extra tool runs, real extra result tokens.

STEP 3. Answer rewrite, shadow in both arms.
- At the final answer: any name-like string in a value or nested key that is not an exact ledger name and
  is the trailing part (whole final path segments) of exactly one ledger full name is replaced. Never
  invent a name. 2+ candidates: log would_reject_ambiguous. Never seen: log would_reject_never_seen and
  whether the ledger has listed-but-unread entities.
- The submitted answer is NOT changed. Score both the original and the rewritten answer with scorer v2.0.
- No rejection, no nudge and no gate message is sent in either arm.

STEP 4. Arms (same runner, one RESULTS_LOG.jsonl).
- CONTROL: fixed loop, sweep in shadow, rewrite in shadow.
- SWEEP: fixed loop + sweep live, rewrite in shadow.
- Enriched tasks: 4 pilot models x 10 replicates per arm. Other development tasks: 4 models x 2 replicates
  per arm. Arms interleaved and shuffled within each model, fixed master seed. Same Ollama settings as
  build round 1. Smoke: 2 cells per arm first.
- Unit test before the run: with no trigger, the SWEEP arm's request payloads are identical to CONTROL's.

STEP 5. Analysis. Unit = the FIRST firing (live or shadow) in an episode.
Per event: re-ask (any later request whose calls are all same T, same other arguments, name in the sweep
set or already read); requests after fire; tokens after fire; supported; hit cap.
Report per arm, per model, per task. Later firings in an episode are reported separately, not used for bars.

BARS (frozen; do not change after the first episode)
[Validity, Sweep PASS/FAIL and Rewrite PASS/FAIL bars: see section 8; copied from the brief, the only addition is "(seeds 11..15)" naming the add-on replicates.]

REPORT (REPORT.md, the usual five-row header)
[see section 9]
```
(The brief file in the context mirror is the authoritative verbatim copy.)

## AMENDMENT 1 (2026-11-16, owner decision, made after the smoke stop and before any full-run episode)
Trigger: smoke session `bonsai-2_4b-stage3` stopped at the end-of-session oracle (`node not listed: /plant32/juniper`); see BUILD_LOG.md. Cause not established. Owner decision: treat it as an infrastructure flake, with this safeguard.
1. The end-of-session oracle read ("after") is retried ONCE after a 5-second wait before it counts as a failure; a failure after the retry stops the session as before (no further retry). Other oracle reads (before, periodic) are unchanged.
2. Every oracle read that reports a mismatch, first try and retry, any label, is logged to `oracle_failures.jsonl` (run folder) with session, label, attempt and the arms of the episodes since the previous oracle read, and is reported in REPORT.md per arm and per session.
3. If oracle failures occur in SWEEP-heavy sessions but not in CONTROL ones, REPORT.md flags it as possible sweep-induced load (a hypothesis, not a finding). Because both arms share each session, the per-arm attribution is by the arms run since the previous oracle read.
4. Smoke episodes (phase "smoke") are not counted in any bar.
Implementation: `run_round2.OracleWithRetry` (wrapper in the session process; `run_pilot.py` and all rules, arms, bars, seeds and the fixed line are unchanged).

## AMENDMENT 2 (2026-11-16, owner decision, made after the second stop and before resuming; no further full-run episode was run in between)
Trigger: session `qwen3.5_9b-stage3` stopped at the periodic oracle `after-012` (3 nodes not listed). Amendment 1 retried only the end-of-session read; the owner judged that too narrow.
1. EVERY oracle read (before, periodic and end-of-session) is retried once after a 5-second wait before it counts as a failure. If a check still fails after its retry, the session stops and is reported, as before. All failures (first try and retry) stay logged per arm and session in `oracle_failures.jsonl`.
2. Infrastructure rule for the interrupted session: the 12 logged episodes of `qwen3.5_9b-stage3` of run folder `full_20261116T003046Z` stay in RESULTS_LOG.jsonl and are listed in `INFRA_EXCLUDED.json` ("excluded: infrastructure (oracle)"); the analysis skips them. That whole session is rerun from the start with fresh fixtures (same plan, same seeds, new run folder; rerun rows carry the new folder name in their run_id). Completed sessions (lfm3:1.7b stage3 and e1h) stay as they are. Then the remaining sessions run.
3. Another stop after this amendment is reported, not worked around. Nothing else changes (rules, arms, bars, seeds, fixed line, analysis definitions).
Implementation: `run_round2.OracleWithRetry` (now all labels), `collect` run-id prefix for resume folders, `analyze_round2.load_rows` skips `INFRA_EXCLUDED.json`.

## AMENDMENT 3 (2026-11-16, owner decision; no episode run after the third stop)
Round 2 is PAUSED. The infrastructure rule of amendment 2 also applies to the rerun of `qwen3.5_9b-stage3` (run folder `full_resume1_20261116T064619Z`, 48 episodes, stopped at the periodic oracle `after-048` after its retry): those 48 episodes stay in RESULTS_LOG.jsonl, are added to `INFRA_EXCLUDED.json` ("excluded: infrastructure (oracle)") and that session will be rerun later. The 88 lfm3:1.7b episodes stay. Before any more episodes run, the owner asked for a root-cause study of the node-discovery flakes (DISCOVERY_FLAKES.md); no rule of this protocol changes.

## AMENDMENT 4 (2026-11-16, owner approval in principle of the fix proposed in DISCOVERY_FLAKES.md; made before any further episode; the owner asked for this draft and for round 2 to resume)
Trigger: the root-cause study (DISCOVERY_FLAKES.md): the oracle's `ros2 node list --no-daemon --spin-time 4` misses fixture nodes in a few percent of reads with no model involved (6 of 212 polls); the agent's own tools use the daemon and were never incomplete in the recorded traces; the daemon read missed 0 of 1,594 polls and 0 of 20 real oracle reads (current oracle: 2 of 20).
1. The oracle's node-list read is `ros2 node list` (daemon read, the command the agent's tool runs) through a daemon that is restarted once at the start of each session, before the first oracle read ("before"), followed by a 10-second settling wait. Nothing else in the oracle changes: parameter, topic and node-info reads, the expected values, the cleanup checks (`assert_domain_empty`, `verify_empty`, `wait_for`, which keep their no-daemon reads) and the stop rules.
2. The 5-second retry of every oracle read (amendments 1 and 2) stays; a check that still fails after its retry stops the session, which is reported, not worked around.
3. For EVERY oracle read, first try and retry, the raw node list is logged to `<session>/oracle-<label>/node_list_raw.jsonl` (time, duration, raw text, number of declared fixture nodes found, fixture retry count). Failures stay logged per arm and session in `oracle_failures.jsonl`.
4. Known property (measured, DISCOVERY_FLAKES.md section 6): the daemon keeps a crashed node listed for about 18-20 s. No oracle check depends on absence; every declared node also has its parameter read, which fails for a dead node.
5. Sessions and episodes: the 60 episodes already excluded stay excluded (`INFRA_EXCLUDED.json`); the 88 lfm3:1.7b episodes stay (they ran under the old read; the oracle does not feed any score). `qwen3.5_9b-stage3` is rerun from the start with fresh fixtures, then the remaining sessions in the planned order (qwen3.5 e1h, gpt-oss, bonsai). The old read is not used any more from this point. All sessions from here run under the new read, both arms of a session share it.
6. No change to prompts, tool schemas, arms, seeds, the fixed line, bars or analysis. Implementation: `run_round2.OracleWithRetry` (wrapper in the session process; `run_pilot.py` and the fixture files are not edited).
