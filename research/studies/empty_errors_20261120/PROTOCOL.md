# Empty errors and empty-string arguments: offline sizing (frozen 2026-11-20, before the script)

Source: `Claude outputs/2026-11-20_CC_EMPTY_ERRORS.md` (the owner's message is the authorisation). Offline, CPU only (`nice`), saved traces only. No GPU, no model run, no production-code change, no held-out file, nothing built. Run with `PYTHONDONTWRITEBYTECODE=1`.

## Mechanisms sized (not built)
- **M1 informative errors:** a menu-tool result that is an error with empty or whitespace-only text is replaced by one line naming the entity kind and the listing tool; no candidate names.
- **M2 empty-string coercion:** `""` for an optional array argument is treated as not given.

## Populations
P1 = 288 loss-map episodes; P3 = the 144 FULL episodes of the list-values run (both parsed as in `derailment_20261120/derail.py`, classifier unchanged); P2 = the 1,832 saved episodes of `candidate_counts_20261118` (its `load_population()` and `parse_episode`; not independent of P1/P3 tasks). Reported separately; **P1+P3 decide**.

## Definitions
- **Empty-error call:** a call of a menu tool (not `final_answer`) whose output is a dict with key `error` whose value is empty or whitespace-only. **Non-empty not-found call:** a failed call of a menu tool whose text matches `Unable to find|Unknown (node|topic|service)|Node not found|not found|does not exist` and is not an empty error. For the comparison only tools that produced at least one empty error in P1+P3 are used.
- **Event:** one per (episode, request) that contains at least one such call (the first such call of the request names the tool, the entity kind and the typed argument). Entity kind = argument key minus `_name` and plural `s` (node, topic, service; `node_name` of the parameter tools = node).
- **Recovery window:** the next 5 requests after the error request, within the episode. **Recovered** if in the window (a) a successful call (not a harness error, not an error result) on an entity of the same kind whose string differs from the typed string (a different string counts, including the full name of a short name typed), or (b) the final answer is accepted and the episode is supported (scorer v2.0). **Requests to recovery** = index of the first recovering request minus the error request's index. An event with fewer than 5 requests left and no recovery is **not recovered** and also counted as *censored*.
- **Episode outcome:** supported or not (scorer v2.0 `supported_complete`).
- **M1 recovery gap** = recovery rate after non-empty not-found events minus the rate after empty-error events, in percentage points, P1+P3 pooled. Secondary (descriptive): first event per episode only; per model; per task; mean requests to recovery of the recovered events.
- **M1 size (upper bound):** for each episode with at least one non-recovered empty-error event, the requests after the FIRST such event's request to the end of the episode (counted once per episode), summed, as a share of all requests in P1+P3.
- **M2 event:** a call rejected by the harness with text `Invalid arguments for <tool>: field '<f>': expected array or null, received string ""`. Saved-max for an event = (index of the first later request in the episode with a successful call of the SAME tool) - (index of the rejected request), 0 if no later success (counted separately as "never retried"). Counts per tool, model, task; share of requests of P1+P3 and P2. Other string values (`"None"`, `"null"`) are counted separately and are out of scope.
- **Hand reading:** 8 empty-error events from P1+P3, `random.Random(20261120)`, stratified by model: 2 per model in sorted name order; if a model has fewer than 2 events all of its events are taken and the shortfall is drawn from the remaining pool of events sorted by run_id.

## Measures (per model, per task, per tool)
M1: number of empty-error events; recovery within 5 requests; requests to recovery; episode outcome; the same for the non-empty not-found events of the same tools (**key number**: the gap). M1 spread: tools, models, tasks producing empty errors; the share of task v2. M2: events, saved-max, never retried.

## Bars (frozen)
- **M1 case = yes** only if: the recovery gap >= 15 percentage points in P1+P3 AND >= 2 models have >= 5 empty-error events each.
- **Spread:** empty errors from >= 2 tools AND no task above 60% of the empty-error events (else the report says "one task only").
- **M1 size:** requests after empty errors in non-recovered episodes >= 3% of P1+P3 requests.
- M2: report only, no bar.

## Report
`REPORT.md`: top box (M1 case yes/no with the recovery numbers, spread, size; M2 count), measured vs interpretation, limits, open search section. Then stop and send ntfy.
