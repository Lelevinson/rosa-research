# Candidate counts for the improvement search: frozen protocol

Dated 2026-11-18, Asia/Taipei. Written and hashed **before** any count exists and before the counting script exists. Offline only: CPU, saved traces, no model, no ROS, no GPU. Development evidence only (synthetic fixtures, four small models); nothing here is held-out, causal or a novelty claim. Held-out custodian files are not opened. Scorer v2.0 (`residual_failures_20261115/scorer_v2.py`, SHA-256 `c6b02716...`) is used unchanged.

## 0. Preflight record (AGENTS.md mandatory context)
- Observed opportunity and evidence: remaining waste is request count (handoff: excess 83 over floor 128, 51 serial reads, 46 name guessing / error recovery) and weak-model worst cases; the finish tool's -7/40 has an unresolved mechanism.
- Candidate vs control action difference: (a) the harness rewrites a not-found name argument to a unique ledger suffix before the call, versus the model retrying alone; (b) the harness shows partial matches, versus nothing; (c) a finish tool, versus text; (d) result-focus, versus the full result.
- Closest prior mechanisms in this repository: name-fix v2 (applied at the answer, `name_fix_applied_20261117`), offline replay 2 "start block" (parked; custodian count 0/76 held-out tasks need short-name resolution), stall hint v2 (closed, failed its bar), finish-gate check (`decisions/2026-11-17-finish-gate-check.md`), round-1 bare-text nudge.
- Known contradiction to carry: the custodian count (0 of 76 held-out tasks need short-name resolution) means (a) can matter on held-out tasks only through models writing names without the leading slash in other tasks; this study cannot measure that and says so.
- Smallest decision-changing next action: this offline count. Stop rule: the bars in section 4; no live run follows from it without a new frozen protocol.

## 1. Population (fixed before counting)
Every row with a `trace_path` in these `RESULTS_LOG.jsonl` files, `phase` equal to `full` (pilot has no phase: all rows), deduplicated by trace path, minus infrastructure exclusions already recorded by the owner (`small_model_harness_20261115/INFRA_EXCLUDED.json`, `build_round2_20261116/INFRA_EXCLUDED.json`, same selection logic as `stall_hint_v2_20261118/step1_offline.py::load_population`):

| study key | folder | arms present |
|---|---|---|
| pilot | `small_model_harness_20261115` | A1, C1, C1+FN, C1+H1e, C1+H1n, C1+H2, C1+H7, M0 |
| round1 | `build_round1_20261115` | C1, C1+AG, C1+LA, C1+AG+LA |
| round2 | `build_round2_20261116` | CONTROL, SWEEP |
| fairness | `fairness_errors_as_text_20261117` | E0, E1 |
| ablation | `steady_loop_ablation_20261117` | FULL, NO_SOFT_ERRORS, NO_PRECHECK, NO_MENU, NO_FINISH |
| namefix | `name_fix_applied_20261117` | NAMEFIX |
| compaction | `tool_description_compaction_20261117` | FULL, COMPACT |
| s0 | `s0_dev_20261116` | S0 (stock, verbatim prompt) |

Not included: Forge baseline (different executor and trace layout; two log rows only), smoke runs, runs with no trace. Reported **per model (four) and per study**; the "all" rows are sums of those cells, not independent samples (same tasks and seeds recur across studies and arms; round 2 has extra seeds). The `all` total counts every episode once per study.

Episode parsing: `offline_replay_20261116/episodes.py::parse` (requests, units, calls), extended only to know the name-fix task file (`name_fix_applied_20261117/namefix_tasks.json`) in addition to the stage3 and e1h task files. Re-scored with scorer v2.0 from the trace; for `namefix` the answer scored is the **original** answer (`final_answer_original` event) so that the rewrite does not change it.

**B0 (data check, reported, not a bar on the ideas):** the re-scored `supported_complete` is compared with the logged value (pilot: `residual_failures_20261115/rescore_v2.json` `new`; namefix: `strict_original`) and the re-derived answer source with the logged `answer_source`. Episodes that disagree are listed. They stay in (a), (b), (e) and are excluded from (c) and (d); the exclusion count is reported. No rule is changed because of B0.

## 2. Ledger and conventions
- **Clean ledger at a call** = `answer_gate.allowed_names(task_text, outputs of all calls in strictly earlier requests)` (names in the task text, names in successful results; failed calls and failed list items contribute nothing; node blocks are joined from `Node name` + `Node namespace`; node-list entries). Same code as the name-fix v2 ledger. Calls in the same request do not see each other.
- A **call** is one entity of an expanded call (`episodes.expand_call`); `ok` and `harness_error` as defined there. A not-found call is a call with `ok` false, `harness_error` false and `NOT_FOUND` matching its result text.
- Entity normalisation for comparisons: `"/" + name.lstrip("/")`.
- Request distance = later request index minus the request index of the fire.

## 3. Counts
### (a) Name binding at input
A **fire** is a not-found call (`ok` false, not a harness error) whose entity argument (`node`, `topic`, `service`; schema-based `entity_argument`) is a string that matches `RELATIVE_NAME` and has **no leading slash**, is not itself in the clean ledger at that call, and has **exactly one** ledger name `R` with `R.endswith("/" + typed)` (`answer_gate.trailing_matches`; name-fix v2 rule). `R` is the resolution.
For each fire, find the **later call** = the first call in a later request that is `ok`, not a harness error, has an entity argument whose normalised value ends at a `/` boundary with `"/" + typed` (or equals it). If found: `agree` if that value equals `R`, `differ` otherwise; record the request distance and whether `R` itself is ever used successfully later. If not found: `no_later_use`.
Reported per (study, model): fires, episodes with a fire, agree, differ, no_later_use, request distance (median, mean), and the full list of `differ` fires with trace paths. The `agree + differ` count is reported as the informative denominator (not part of the bar).

### (b) Partial-match exposure
A **partial-match event** is an `ok` call with a `pattern` argument that is a string fully matching `ABSOLUTE_NAME`, such that no name in the result equals the pattern, and at least one name in the result is a strictly longer string that contains the pattern as a substring. Result names = absolute names in list values of a dict output plus `NAME_IN_TEXT` matches in the result text. Reported: events and episodes per (study, model); then, for the events' episodes, whether the **final answer** contains (as an exact string, key or value, at any depth; for an answer with no object, as a whole-token match in the end text) any exposed partial-match name or the typed absolute name; and whether the answer is supported. Counts only; no judgment of correctness beyond the scorer.

### (c) Finish tool
In **FULL-type arms** = pilot `C1`, round1 `C1`, round2 `CONTROL`, ablation `FULL`, compaction `FULL`: classify each episode by ending: `final_answer` (an accepted `final_answer` event exists), `text` (no accepted finish call and a JSON object recoverable by the scorer), `none` (no answer object: iteration cap, backend error, timeout). Report per class: episodes, supported rate (scorer v2.0), per (study, model). Secondary table, same classes, for the other arms that offer `final_answer` (round1 add-ons, round2 SWEEP, pilot add-ons, ablation NO_* except NO_FINISH, namefix, compaction COMPACT), and for the arms without it (ablation NO_FINISH, fairness, s0). The old round-1 bare-text nudge result is **quoted** from `decisions/2026-11-17-finish-gate-check.md` (C1+AG 4 nudged episodes, 4 supported; C1+AG+LA 8, 6) with its caveats, not recomputed.

### (d) Needle missed
A **failed** episode = re-scored `supported_complete` false. A **needle-missed** episode (`D1`) = failed, an answer object exists, `exact` is false, and `support_missing` is empty, i.e. every fact the fixture truth lists as deciding the answer (`task["support"]`) appeared in a successful result, and the answer is still wrong. Also reported: `D0` = failed, no answer object, `support_missing` empty (not counted toward the bar); episodes failing only on `support_missing` (answer exact, fact not read) as `S`. For each D1 episode record the character length of the longest successful result that supplies a support fact (a result containing the `text` fact or the `param` read) and flag `long` if >= 8,000 characters (about 2,000 tokens at 4 characters per token; an estimate, not a tokenizer count). Reported per (study, model), with distinct (task, model) pairs next to episodes.

### (e) Open search
Computed for every episode by fixed detectors (no filtering by method fit), per (study, model), each with a count and up to three example trace paths:
1. identical repeated call: same tool and arguments as an earlier `ok` call of the episode;
2. identical repeated failed call: same tool and arguments as an earlier failed call;
3. harness-rejected calls by prefix of the harness text (`Invalid arguments`, `Tool ... is not available`, `final_answer needs`, `Answer not accepted`, `The list of names`, `Too many names`);
4. mid-episode text-only request (a request with no tool call that is not the last request);
5. backend errors at the end (`ResponseError`, `XML syntax`, `Agent stopped due to max iterations` in `episode_end` answer or `aborts`);
6. long results: successful results >= 8,000 characters (count and share of requests that follow them);
7. fresh read of an entity whose result is already in the episode's successful results for the same tool and argument but written differently (leading slash added or dropped);
8. calls to write tools or tools not offered;
9. answer wrong although every support fact was read (same as D1; not repeated).
Then hand reading: a short, labelled list of anything else seen while reading example traces, each with a count only if a rule for it is stated in the report; items found after seeing (a)-(d) results are marked post hoc.

## 4. Bars and reporting (frozen)
- **(a) keep the name-binding-at-input idea alive** only if fires >= 10 over >= 2 models **and** differ = 0. Fewer fires, one model only, or any `differ` = the idea does not reach the bar on this evidence; the report also states the `agree + differ` count so a pass on thin informative evidence is visible.
- **(d) keep the "long-result focus" idea** only if `D1` episodes >= 5 over >= 2 models. The `long` subset is reported beside it; the bar is applied to `D1` as written by the owner, and the report states whether the `long` subset alone would also reach it.
- (b), (c), (e): no bar; measured values only.
- Report **measured** values separately from **interpretation**, and make no recommendation beyond the bars.
- Any deviation from this protocol during implementation is listed in the report as a deviation with its reason; no rule is changed after seeing counts. Counts are produced by one script, `count_candidates.py`, whose SHA-256 is recorded with the output; `results.json` is hashed after the run.

## 5. Outputs (this folder)
`PROTOCOL.md`, `PROTOCOL.sha256`, `count_candidates.py`, `results.json`, `fires_a.jsonl`, `events_b.jsonl`, `needle_d.jsonl`, `TABLES.md`, `REPORT.md`, `OUTPUT.sha256`.
