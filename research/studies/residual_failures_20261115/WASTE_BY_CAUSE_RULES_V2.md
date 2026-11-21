# Attribution rules v2 (written after the v1 accuracy check and before any v2 number), 2026-11-15

The v1 rules (`WASTE_BY_CAUSE_RULES.md`, frozen hash in `WASTE_BY_CAUSE_RULES.freeze.json`) stay as they are and their results are reported. The hand check of 10 random v1 tags found 1 clearly right (see WASTE_BY_CAUSE.md), with three systematic faults, which v2 changes. Everything not listed here is as in v1.

1. **(a) dependence on the previous result.** v1 counted a string as "known" if it appeared anywhere in earlier results, so names in a big list result made dependent requests look batchable. v2: request k is (a) only if it has calls, no call failed or was rejected, request k-1 had calls and **did not fail or get rejected**, every string argument appears in the task text, in the arguments of earlier requests, or in results of requests before k-1, **and no string argument that is absent from the task text and from earlier arguments appears in the result text of request k-1** (that argument was taken from the previous result, so the request depended on it).
2. **(b) recovery lists.** The request directly after a (b) request is also (b) if it consists only of list calls (`node_list`, `topic_list`, `service_list`), with or without a pattern (v1 required a pattern containing the name). A not-found-type failure includes a result whose error text is empty (`{'error': ''}`, what `service_info` returned for a short service name).
3. **Priority.** (f) off-route tool is tested before (a): order e, d, b, c, f-off-route, a, then the other (f) cases (empty-pattern lists, not-found guesses).

The accuracy check is repeated on a new random sample of 10 tagged requests (seed 20261116) from the v2 tags.
