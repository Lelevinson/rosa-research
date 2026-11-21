# Fresh FULL arm: where the tokens and requests go (definitions fixed 2026-11-17, before any number was computed on the ablation's FULL arm)

Owner request (2026-11-17): on the fresh FULL (C1) arm of the steady-loop ablation, (a) split input tokens per request into system prompt + tool schemas, conversation history and new content, and show how input grows over the steps; (b) count requests above the minimum, by cause; (c) one line of failure cause for every unsupported cell. Offline, from the saved traces; no GPU. Exploratory, not part of the frozen ablation protocol; descriptive only. "Measured" and "interpretation" are kept apart in the report. The code (`full_arm_map.py`) was tested on round 1 control traces before it was run on the FULL arm.

## (a) Input token split (per request k of an episode, reported `usage.input_tokens` of the model response)
- **Fixed part** = input tokens of request 1 (system prompt + tool schemas + task text; there is no history yet). Exact (it is what the model was sent).
- **New content of request k** = input_k - input_(k-1) (the previous assistant message with its tool calls plus the tool results added since). Exact, because the prompt prefix is identical between consecutive requests of an episode.
- **History of request k** = input_(k-1) - input_1 = everything older than the new content (old messages and old tool results).  Identity: input_k = fixed + history_k + new_k for k >= 2 (for k = 1: fixed only).
- **Split of the fixed part** into system prompt, tool schemas and task text is an ESTIMATE: proportional to characters of the serialized system messages, the serialized offered schemas (as sent) and the task text, taken from the `model_start` event of request 1; the characters-to-token ratio is the same for all three parts of one episode. Cross-check where possible with the exact measurement from the ablation's other arms on the same cell (NO_MENU adds 35 tool schemas, NO_FINISH removes final_answer and its prompt line).
- **Growth**: mean input tokens per request index (1, 2, 3, ...) over episodes still running, per model; the totals by part over all FULL episodes (sum over requests of fixed, history, new) and their shares of all input tokens; output tokens shown separately. What the provider actually recomputes is unknown (prefix caching in Ollama is not visible in the trace): the shares are shares of **reported prompt tokens**, not of compute time.

## (b) Requests above the minimum, by cause
- **Floor** of a task = `floor` of the task file (depth + 1: the sequential observation stages plus the answer request; Stage 3 protocol; independent reads inside a stage count as one). **Excess** of an episode = requests - floor (may be negative if the model batches).
- Each request is given ONE mechanical class, by the first rule that applies (an automatic analogue of the Stage 0 codebook; not hand labels):
  1. **FIN**: it contains an accepted `final_answer` (the last request of an episode that ended with an answer).
  2. **ERR**: every call of the request failed (validation text, not-found, blocked tool, tool exception text; the same judgement as `episodes.parse`: `ok` false).
  3. **REC**: the previous request had a failed call and this request calls the same tool again (re-issue after an error).
  4. **RED**: every call repeats a call (tool, arguments, entity) that already succeeded earlier in the episode, or the tool returns no task information (`wait`, `set_debugging`, `set_verbosity`).
  5. **NAME**: every call is a list tool with a non-empty `pattern` argument (a name search).
  6. **BATCH**: every entity named in the request already appeared in the ledger (task text or a successful result) before the PREVIOUS request was issued, i.e. the request could have been merged into the previous one (argument availability, as the codebook's `batchable` flag).
  7. **OTHER**: all remaining requests (dependency- or judgement-driven reads that the mechanical rules cannot call avoidable).
- Reported: per class the number of requests, their share, their own input+output tokens (the full cost of the request, not the marginal one), per model and per task; total excess vs the sum of ERR+REC+RED+NAME+BATCH; the remaining excess is "reads beyond the route" (OTHER above the floor minus the final request). Interpretation is kept separate: the classes are mechanical and cannot say whether a model had a reason to do a "RED" read.

## (c) Unsupported FULL cells
Every unsupported FULL episode (scorer v2.0 `supported_complete` false) gets one line: what failed (scorer issues / missing support) and the cause found by reading the trace (hand reading, one of: wrong entity chosen, name not resolved, scan not finished, answer format, backend/tool-call parse error, no answer, other). The line names the evidence (request number) and is marked measured (scorer) vs interpretation (cause).
