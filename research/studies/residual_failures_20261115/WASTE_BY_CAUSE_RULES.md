# Attribution rules (written and frozen before any attribution number was computed), 2026-11-15

Read-only on existing pilot traces; scorer v2.0 decides which episodes are supported-complete; floors as in WASTE_ANALYSIS.md. No model, no ROS.

**Unit.** Request = one `model_end` with its tool calls and their results (aligned by order). Per episode, excess E = requests - floor (episodes with E <= 0 get no attribution; their count is reported).

**Step 1: tag each request with at most one cause, first matching rule wins, in this order.** Requests with no calls (the closing free-text answer) or a `final_answer` call are never tagged.
- **(e) bad arguments rejected and retried:** some call's result text starts with `Invalid arguments`, `Invalid plan`, `Tool ... is not available`, `Tool ... failed`, or contains `Observation-only study: command rejected` (schema rejection, plan or gate refusal, tool exception, rejected glob).
- **(d) identical call repeated:** every call of the request (tool name and arguments) is identical to a call of an earlier request (successful or not).
- **(b) wrong name form then recovered:** a call returned a not-found error (`not found`, `Unable to find`) for a name that does not start with a single `/` (relative, `ns:name`, `//x`) or is a bare name, and a later call uses a string argument that ends with that name on a `/` boundary (the full form); also the immediately following request if it is a `node_list`, `topic_list` or `service_list` whose pattern contains that name (the recovery search).
- **(c) re-lookup of information already in an earlier result:** (c1) `node_list`/`topic_list`/`service_list` after an earlier successful call of the same tool with no pattern (a full list already seen); (c2) `param_list` of a node when every parameter name read by later `param_get` calls of the episode already appears in the task text; (c3) `node_info`/`topic_info`/`service_info` where every requested entity already has a successful result in an earlier call of the same tool.
- **(a) independent calls issued one per request instead of batched:** the request has calls, none failed, the previous request had calls, and every string argument of every call already appeared in the task text, in the arguments of earlier requests, or in the results of requests before the previous one (so it was knowable when the previous request was written and could have been batched with it). Single or multiple calls count.
- **(f) wrong tool or pattern:** a call to a tool outside the task's minimal route (route tools of the pilot harness, plus `final_answer`); or a list call (`node_list`/`topic_list`/`service_list`) with a pattern that returned an empty list; or a call that returned a not-found error for an absolute name (a guessed entity).
- Untagged requests are "needed or other" and are not counted as waste.

**Step 2: turn tags into above-floor attribution.** Let t_c be the number of requests tagged c in an episode, W = sum t_c, E > 0 its excess. If W <= E: each cause gets t_c and (g) other gets E - W. If W > E (some tagged requests were part of the floor): each cause gets E * t_c / W (fractions are kept in sums, shown to one decimal). Raw tag counts are reported next to the attribution.

**Accuracy check.** After the attribution, 10 tagged requests are drawn at random (seed 20261115, from C1 and A1 supported episodes) and judged by hand against the trace; the result is an estimate on 10 items, not a measurement of accuracy.

**Reuse (H1e/H1n) and name fixer (H2) questions** use the `handler` events in the traces and the same cells in arm C1 (same model, task, seed); differences between arms on the same cell include the pilot's run-to-run noise.
