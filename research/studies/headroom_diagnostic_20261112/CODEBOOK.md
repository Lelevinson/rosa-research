# Request-reason codebook (Stage 0)

Applies to every model request after the first in an episode. One label per request. A request is one model response together with the tool calls it emitted. The label answers: **why did this request have to exist, given what was already known when it was issued?**

You see: the task text, the earlier requests of the episode (their calls and a short excerpt of each result), and the request to label (its calls and the model's short comment, if any). Judge only from this; do not use hindsight about how the episode ended.

| Label | Use when | Tie-breaker |
|---|---|---|
| FIN | The request has no tool call (it is the final answer). | Always FIN. |
| RED | The request obtains nothing the answer still needs: (a) every item it fetches was already fetched successfully earlier (exact repeat or subset of an earlier result); or (b) the tool returns no task information (for example `set_debugging`, `wait`); or (c) it lists parameter names although the task text already names the parameter (`use_sim_time`) and the parameter is not otherwise unknown. | An unnecessary but not repeated *route* (for example `node_info` where `topic_list` would also work) is NOT RED. |
| REC | The request exists because an earlier call in the episode returned an error, or it repeats discovery after such an error, or it re-issues a failed call with corrected arguments. | The task `d1_recovery` plants a missing node on purpose; discovery after that planned miss is still REC (it is separately tagged `designed_recovery`). |
| ORD | The request exists only because the task text requires an order or a verification step (for example "first inspect X once, then ...") and the step could otherwise have been merged into another request. | Use rarely. If the step is also needed for information, prefer JUDG or DEP. |
| DEP | Every argument was already verbatim available (task text or an earlier result, including a full node name assembled from `Node name` + `Node namespace`), and the request only carries those values forward. A mechanical rule would produce the same call. Typical: one `param_get` per discovered node, an `info` call over names just listed, a call that could have been issued in an earlier request. | If the model had to *choose among alternatives by meaning* (which of several nodes or topics matches the task), it is JUDG, not DEP. |
| JUDG | Producing the request required interpreting an earlier observation or the task: choosing which observed node, topic or service to inspect, choosing a source for a requested field, or deciding what to do after an unexpected result. | Choosing a subset by task meaning is JUDG even when the choice looks easy. |
| UNCLEAR | You cannot decide between two labels from the visible information. Never force a label. | Say which two labels competed. |

Notes:
- A request that contains both a mechanical call and a judgment call takes the label of the call that made the request necessary; if that is not decidable, UNCLEAR.
- Whether a request could have been merged into an earlier one is a separate flag (`batchable`) computed from argument availability; do not use it to choose DEP vs JUDG on its own.
- A failed call (error result) keeps the label of its own intent (usually DEP or JUDG); the error is recorded in `own_call_error`. The request that follows the error is REC.
