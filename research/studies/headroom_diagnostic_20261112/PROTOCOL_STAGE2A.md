# PROTOCOL_STAGE2A (frozen before any computation)

Frozen: 2026-11-13. Offline replay only: no model inference, API call, fixture, or repository edit (`src/rosa/` untouched); outputs are study-folder files. Development evidence, no novelty claim, no selected algorithm. Revisions after the first computation are listed at the bottom, never edited into this text. Where the addendum left a detail open, the choice below is mine and is frozen here.

## Question
If the framework, after each tool result, had automatically executed the read-only follow-up call(s) the model usually makes next and appended their results to the same observation, how many model requests would have been removed beyond what batching and the prompt fix already remove?

## Data
- Evaluation traces (A0 only): Qwen from Stage 1a (12 episodes) and Luna from Stage 1c (12 episodes), in `research/_artifacts/runs/headroom_diagnostic_20261112/`.
- Training traces (leave-one-task-out): Stage 0 baseline (36), Stage 1a (24: A_orig and A0), Stage 1c (12). Narration and coverage traces are not used (different registry and result encoding). For a held-out task `T`, every episode whose task id is `T` is excluded; held-out `d1` is also never trained on its own episodes. Six folds: t1 t2 t3 d1 d2 x1.
- Units: one request = one model response with its calls and results; failed calls stay in the sequence.

## Definitions
- **Candidate call** in request k+1: read-only information tool (exclude `set_debugging`, `wait`, any no-information tool); every argument string is available from the task text or earlier results; and at least one argument string first appears in the results of request k (DEP: arguments derivable only after request k). Calls whose arguments were known earlier are batching's job and are not candidates; calls with guessed or unavailable arguments are not candidates.
- **Result fields** (generic parsers of ROS CLI output, no task maps): `node_list.nodes`, `topic_list.topics`, `service_list.services`, `node_info.publishers`, `node_info.subscribers`, `node_info.service_servers`, `node_info.service_clients`, `topic_info.endpoint_nodes` (full name assembled from `Node name` + `Node namespace`), `param_list.params`.
- **Binding signature** of a candidate call, computed against one tool `t` called in request k: for each string argument, in this order: `field:<result field>` when its value(s) occur in a field of `t`'s results; else `carry:<argument name>` when it equals an argument value of the call of `t` that produced the result (for example `param_list(node_name=X)` followed by `param_get(node_name=X)`); else `const:<value>`, allowed **only** if the value never appeared in any tool result earlier in the episode (it came from the task text or the model's prior, for example `use_sim_time`). A string value that appeared in earlier tool results and is neither field-bound nor carried is an environment entity the framework cannot supply, so the call is not speculable (this prevents memorising fixture names). Non-string arguments (numbers, booleans, null) are constants and null is ignored. A signature with more than one `field:` argument is not speculable. If a value occurs in several fields, the first field in the list above is taken.
- **Training statistic:** for each occurrence of tool `t` in a request that has a successor request (the successor may be the final answer), the set of candidate `(t', signature)` in the successor is recorded; `p(t -> (t', signature))` = occurrences of that pair / occurrences of `t` with a successor.
- **Learned predictor:** after request k, for every tool `t` called in k and every pair with `p >= tau` (tau in {0.5, 0.7, 0.9}), speculate: scalar-argument tools get one call per value of the bound field in that result (constants fixed from the signature); list-argument tools get one call with all values of the field. One level only: results of speculated calls do not trigger further speculation (primary); a chained variant is reported as secondary.
- **Static top-1 control:** for each tool `t`, always speculate its single most frequent training pair `(t', signature)` (ties by lexical order), regardless of `p`. **Oracle:** every candidate call speculated perfectly.
- **Covered call:** same tool, every constant argument equal, and every bound value contained in the speculated values. A request k+1 is **removable** if every call in it is a candidate and every call is covered. Partially covered requests are recorded as partial and not counted as removed. Final-answer requests and requests containing a non-candidate call are never removed.
- **Counting:** primary = non-chained greedy: scanning requests in order, request j is removed only if it is removable from the actual request j-1 and j-1 was not itself removed. Secondary = chained: each request judged independently from its actual predecessor.
- **Cost side** (counted at every request where speculation fires, whether or not a removal follows): speculative units executed (scalar calls or list elements); precision = units that the model's actual next request also made / units speculated; extra native operations = unused units (units the model would have made anyway are not extra); extra input tokens = for unused units, median result size in characters per unit of that tool over the training traces / 4, times the number of requests remaining after k; tokens saved = input tokens of the removed requests as recorded.

## Report (`REPORT_STAGE2A.md`)
Per task and per model: requests, candidate requests (oracle-removable), removable under oracle, learned (each tau) and static top-1; cost side as above; saving as a percentage of requests on held-out tasks with the per-task spread, naming savings that come from only one or two tasks; plain statement wherever the learned predictor does not beat the static top-1 rule.

## Kill bar (frozen)
Evaluated at **tau = 0.7** (primary) on the Qwen A0 traces (63 requests); 0.5 and 0.9 are reported but do not rescue a failure at 0.7. The direction is stopped if any of these holds: (a) learned saving on held-out tasks is under 10% of A0 Qwen requests; (b) learned removes no more requests than the static top-1 rule; (c) all removed requests come from one task. If exactly two tasks contribute, that is reported prominently but does not by itself stop the direction. The bar is not changed after seeing results.

## Housekeeping
Revisions go in a "Revisions" section; `DECISION_LEDGER.md` updated; `rosa-context-sync` run once at the end with its copied and removed files listed.

## Revisions
(none after the first computation yet)
Pre-computation clarification (made before any replay number existed): the binding-signature rule above originally allowed any learned constant; it was tightened to the `field` / `carry` / environment-free `const` rule to stop the predictor from memorising fixture entity names. No result had been computed.
