# Derailment study: where do bad episodes first go wrong? (frozen 2026-11-20, before the script is written)

Source prompt: `Claude outputs/2026-11-20_CC_DERAILMENT.md` (owner's message is the authorisation). Offline, CPU only (`nice`), saved traces and result rows only. No GPU, no Ollama, no model run, no held-out file, no production-code change, no mechanism built. Output folder: `research/studies/derailment_20261120/`. Run with `PYTHONDONTWRITEBYTECODE=1`.

## Question
The loss map counts wasted requests by type. This study asks what the model SAW in the request just before its FIRST wasted request (the trigger), and how often the same context does not derail. Measurement only.

## Populations
- **P1** = the 288 loss-map episodes (seeds 5-8). Per-request types are read from `research/studies/loss_map_20261120/labelled_lossmap.jsonl` (its SHA-256 is recorded in FREEZE.json); the request detail (calls, results) is re-parsed from the saved traces with the loss-map parser (`offline_replay_20261116/episodes.py`).
- **P3** = the FULL arm of the list-values live run (144 episodes, seeds 9-10, `research/_artifacts/exam/listval/RESULTS_LOG_all.jsonl`, rows with `arm == "FULL"`). It is labelled with the loss-map classifier UNCHANGED: `loss_map_20261120/classify.py::analyse` (SHA-256 in FREEZE.json; the script refuses to run on a different file). The FULL arm there runs the same tools with the LISTVAL switch off (`listval_arm.py`), so its trace has the same event kinds. If the classifier cannot be applied to a row (parser exception or a row without `trace_path`), the row is dropped and counted in the report; P3 is then reported with that gap.
- P1 and P3 are reported separately and then pooled. They share the 18 dev tasks and the four models, so they are not independent samples of tasks.

## Definitions
- **Request types**: exactly those of the loss-map classifier (`format`, `repeat`, `name_guess`, `name_recovery`, `serial_batchable`, `productive`).
- **Derailment point** of an episode: the first request whose type is `format`, `repeat` or `name_guess`. (`serial_batchable` is excluded by the prompt; `name_recovery` can only follow a `name_guess`, so it cannot be first.) An episode with no such request is **clean**.
- **Waste after the derailment** ("excess after"): the number of requests with index >= the derailment index whose type is any of the five waste types (format, repeat, name_guess, name_recovery, serial_batchable). Secondary: the classifier's per-episode `excess` (requests above the task floor), reported beside it.
- **Productive return distance**: d = (index of the first `productive` request after the derailment point) - (derailment index); the final answer is a productive request. If none exists, d is undefined.
- **Outcome** (frozen precedence): `never` if the episode ended unsupported (scorer v2.0 `supported_complete` false; this includes capped episodes); otherwise `quick` if d <= 3, else `slow`. Beside it the distance d is always reported, and the supported/unsupported split of each cell, so that "answered quickly but wrongly" stays visible.
- **Trigger context** of the derailment at request k: request k-1 (all its calls: tool, arguments, result size in characters, error or not, error text class) and its results. For k = 1 there is no previous request: the context is the task text only, flagged `first_request`.
- **String reuse**: the derailing request's calls name a string (the entity argument, or for a call without entity argument each string argument value of length >= 3) that occurs as a substring (case-sensitive) in the result text of request k-1. Reported as yes/no/n.a. (k = 1).

## Trigger categories (one primary per derailment, precedence 1 to 6; "other" is not a category: whatever matches nothing is 6)
Evaluated on request k-1 (categories 1-3) and on the task (4, 5):
1. **error result**: any call of request k-1 failed (`ok` false or a harness error) or returned an error result. Sub-class by the text of the FIRST failed call, in this order: `empty` (the output is a dict whose `error` is empty or whitespace); `not-found` (regex `Unable to find|Unknown (node|topic|service)|Node not found|not found|does not exist`); `regex` (`multiple repeat|nothing to repeat|bad escape|unterminated|re\.error`); `validation` (`^Invalid arguments|^final_answer needs|^Answer not accepted|is not available`); `other`. (These classes were written after looking at the error texts of the 230 development episodes, `labelled_dev.jsonl`, not of P1 or P3.)
2. **split name**: no category 1, and a result of request k-1 contains a `Node name: X` line followed by a `Node namespace: Y` line (topic_info publisher/subscriber blocks), and the derailing call's entity string equals X alone or Y alone and is not itself an absolute full name seen in the ledger. Request k-1 results that have no such pair never count.
3. **long result**: no category 1-2, and a result of request k-1 has >= 3,000 characters.
4. **absent or ambiguous task**: no category 1-3, and the task is an absent-entity task (`e1h_abs_1`, `e1h_abs_2`, `nf_absent`) or an ambiguity task (`e1h_amb_1`, `e1h_amb_2`, `nf_amb_1`, `nf_amb_2`).
5. **scripted change**: no category 1-4, and the task is `e1h_chg_1` or `e1h_chg_2`.
6. **none**: a clean, short (< 3,000 characters), successful previous result in any other task, including a first-request derailment in such a task.
For a first-request derailment (k = 1) categories 1-3 cannot apply; 4, 5, 6 apply by task.
- **Underlying category (descriptive secondary)**: the same assignment skipping 4 and 5 (so a derailment in an absent/ambiguous/change task is also classed by what the previous result looked like). Reported beside the primary because the precedence lets the task class hide the result class.

## Measures
1. Per model and per task: derailed episodes, derailment request index (median, range), trigger category, outcome, waste after the derailment.
2. **Key table**: trigger category (primary) x outcome (quick / slow / never), with episodes, waste-after requests (sum and mean), and the number of episodes ending unsupported. P1, P3, pooled; per model for the pooled table.
3. Category 1: the error texts (names replaced by `<N>`, first 110 characters), ranked by the sum of waste-after requests that follow them: top 10 with counts, mean waste-after and up to 3 trace paths each.
4. **Derailment rate per trigger context.** An *exposure* is a (episode, k) pair with k from 0 to n-1 (n = number of requests; k = 0 is the task-only context before request 1), counted only while no derailment has happened before request k+1, i.e. k+1 <= derailment index (or all k in clean episodes). The exposure gets one primary category from request k (and the task) by the precedence above (k = 0: category 4, 5 or 6 by task). It *derails* if request k+1 is the derailment point. Rate = derailments / exposures per category, with the number of exposures in clean episodes and in derailed episodes shown separately, per model and pooled. Exposures after the final answer do not exist (k+1 <= n).
5. **Hand reading**: 10 derailment points, pooled P1+P3, random seed 20261120 (`random.Random(20261120)` over the episodes sorted by `run_id` within each model), stratified by model: 3, 3, 2, 2 episodes for the models in sorted name order (bonsai-2:4b, gpt-oss:20b, lfm3:1.7b, qwen3.5:9b). For each, the report quotes the previous request and the derailing call and says whether the assigned category was right (right / wrong / debatable, with the reason). A wrong assignment is reported, not corrected in the numbers.
6. Open search (end of report): other patterns noticed in the traces, counts and trace paths, unfiltered.

## Not done / limits (stated before)
The classifier's labels are detectors (see `loss_map_20261120/CLASSIFIER_NOTES.md`), not ground truth. A trigger is the context before the first wasted request, not a proven cause. No mechanism is proposed or built; at most one line "possible fix to size later". Scripted-change tasks (e1h_chg) have a mid-episode state change the classifier does not model.

## Files
`PROTOCOL.md` (this), `FREEZE.json` (hashes), then `derail.py` (script), `derail_rows.jsonl` (one row per episode), `results.json`, `REPORT.md`, `OUTPUT.sha256`.
