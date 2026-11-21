# Blind audit answers — 2026-11-17

Reviewed only the task text, calls, displayed results and final responses in `AUDIT_PACKET.md`; no labels, scorer output, run folder or audit key were consulted. Judgments are for each episode's own displayed evidence, not evidence from another episode. Correctness below concerns **substance**, separate from strict response format. A fenced JSON block or prose surrounding JSON is not, as a whole, a JSON document. A nested `answer` object is valid JSON but does not have the requested keys at the top level. “Format-only: yes” means the substantive answer is correct and visibly supported, but the entire response is not the requested exact JSON. It does not assert how any particular scorer extracts answers.

For “stopped early,” the form offers yes/no; when a result is truncated and that prevents a conclusion, I record **cannot tell** rather than falsely infer whether the complete result was seen. An evidence-gathering order explicitly required by a task is part of evidence completeness, even when the returned values look plausible. For the running-node tasks, the leading slash denotes the exact full name in the question; a different fully qualified node with a matching suffix is a different node.

## Cell 01

### A
- Correct: **correct**. Topic info identifies yarrow, node info identifies harbor_t, and harbor_t info identifies quill.
- Complete evidence: **yes**. Stopped early: **no**. Format: **exact**. Format-only: **no**. Failure cause: —.
- Note: All three links of the requested chain are displayed.

### B
- Correct: **cannot tell**. The bulk node-info result is cut before the claimed publisher, subscription, and upstream relation can be checked.
- Complete evidence: **cannot tell**. Stopped early: **cannot tell**. Format: **not JSON / no answer** (a fenced JSON block is present). Format-only: **cannot tell**. Failure cause: **other — packet truncation prevents verification**.
- Note: A bulk node-info call was made, but its relevant results are not visible; no separate upstream topic-info call is shown.

## Cell 02

### A
- Correct: **correct**. The three parameter reads identify beacon, then juniper, and juniper's setpoint 873.
- Complete evidence: **yes**. Stopped early: **no**. Format: **exact**. Format-only: **no**. Failure cause: —.
- Note: Extra node-info calls precede the successful parameter chain.

### B
- Correct: **incorrect**. The reads identify beacon as first and juniper as second, but both JSON objects assign quartz and beacon to those keys.
- Complete evidence: **yes**. Stopped early: **no**. Format: **not JSON / no answer** (prose and two JSON objects). Format-only: **no**. Failure cause: **other — wrong assignment of the observed chain positions to answer fields**.
- Note: The prose lists the three nodes and correct setpoint, but the requested `first` and `second` fields are shifted; extracting either JSON object would not fix it.

## Cell 03

### A
- Correct: **correct**. The parameter chain reads beacon, juniper, and juniper's setpoint 873.
- Complete evidence: **yes**. Stopped early: **no**. Format: **exact**. Format-only: **no**. Failure cause: —.
- Note: Each required parameter is read in sequence.

### B
- Correct: **incorrect**. The displayed 694 is beacon's setpoint, while the requested setpoint belongs to juniper.
- Complete evidence: **no — juniper's setpoint was not read**. Stopped early: **yes**. Format: **not JSON / no answer** (fenced JSON). Format-only: **no**. Failure cause: **read chain not finished**.
- Note: The two next-node reads succeed, but the last value is taken from the preceding node.

## Cell 04

### A
- Correct: **correct**. The displayed reads in separate requests show first mode idle, flow 725, and a later mode run.
- Complete evidence: **yes**. Stopped early: **no**. Format: **exact**. Format-only: **no**. Failure cause: —.
- Note: An unrelated unsuccessful parameter read does not replace the ordered required reads.

### B
- Correct: **cannot tell**. The result `run` was read in request 1, before the successful flow read in request 3; the required later mode value is not shown.
- Complete evidence: **no — no mode read after the successful flow read**. Stopped early: **yes**. Format: **not JSON / no answer** (prose and multiple JSON renderings). Format-only: **no**. Failure cause: **read chain not finished**.
- Note: The task explicitly requires the final mode read after both earlier reads return; its value might have changed again, so the reported value cannot be verified as the required final value.

## Cell 05

### A
- Correct: **cannot tell**. The node and gains are displayed, but the multi-topic result is cut after the first input publisher and does not show the other two topic-to-publisher mappings.
- Complete evidence: **cannot tell**. Stopped early: **cannot tell**. Format: **not JSON / no answer** (prose and a fenced JSON object). Format-only: **cannot tell**. Failure cause: **other — packet truncation prevents verification**.
- Note: The episode queried all three topics together and read three gains; the displayed result does not show all mappings.

### B
- Correct: **cannot tell**. The multi-topic result is cut after the first input publisher, so the other two claimed mappings are not visible despite all three gains being read.
- Complete evidence: **cannot tell**. Stopped early: **cannot tell**. Format: **exact**. Format-only: **cannot tell**. Failure cause: **other — packet truncation prevents verification**.
- Note: The three gain reads are visible; their association with two input topics is hidden by the result cut.

## Cell 06

### A
- Correct: **incorrect**. All required values were read in the required order, but the episode has no final answer and ends in a response parsing error.
- Complete evidence: **yes**. Stopped early: **no**. Format: **not JSON / no answer**. Format-only: **no**. Failure cause: **tool or backend error**.
- Note: The packet reports an XML syntax `ResponseError` after the three reads; this is not an extractable final answer.

### B
- Correct: **correct**. The first mode, flow and later mode reads show idle, 725 and run, respectively.
- Complete evidence: **yes**. Stopped early: **no**. Format: **exact**. Format-only: **no**. Failure cause: —.
- Note: An unsuccessful topic echo is followed by the required parameter reads.

## Cell 07

### A
- Correct: **correct**. Topic info, node info and upstream topic info respectively establish yarrow, harbor_t and quill.
- Complete evidence: **yes**. Stopped early: **no**. Format: **exact**. Format-only: **no**. Failure cause: —.
- Note: The relevant parts of all three results are visible despite result cuts.

### B
- Correct: **correct**. The topic and node-info results establish the same three requested values as the final response.
- Complete evidence: **yes**. Stopped early: **no**. Format: **not JSON / no answer** (prose plus fenced JSON). Format-only: **yes**. Failure cause: **answer format**.
- Note: The answer is supported; the response as a whole is not a JSON document.

## Cell 08

### A
- Correct: **cannot tell**. The node and all three gains are shown, but the bulk topic-info output is cut before two claimed publisher mappings.
- Complete evidence: **cannot tell**. Stopped early: **cannot tell**. Format: **not JSON / no answer** (prose and fenced JSON). Format-only: **cannot tell**. Failure cause: **other — packet truncation prevents verification**.
- Note: The unsuccessful short names were followed by successful fully qualified parameter reads.

### B
- Correct: **cannot tell**. The bulk topic-info output is cut before two publisher mappings, although all three gain reads are visible.
- Complete evidence: **cannot tell**. Stopped early: **cannot tell**. Format: **exact**. Format-only: **cannot tell**. Failure cause: **other — packet truncation prevents verification**.
- Note: Two short-name attempts fail before the full-name reads; the results visible in the packet do not show the complete mapping.

## Cell 09

### A
- Correct: **correct**. The displayed filtered node list contains `/e1h/ember/mistral`, not the exact queried `/ember/mistral`.
- Complete evidence: **yes**. Stopped early: **no**. Format: **exact**. Format-only: **no**. Failure cause: —.
- Note: The pattern returns a suffix match, which does not make it the exact full node name.

### B
- Correct: **incorrect**. The node-list result contains `/e1h/ember/mistral`, not `/ember/mistral`, and the limit read is from the former.
- Complete evidence: **yes — the displayed filtered list distinguishes the exact name from the suffix match**. Stopped early: **no**. Format: **not JSON / no answer** (fenced JSON). Format-only: **no**. Failure cause: **wrong entity chosen**.
- Note: The episode changes the node under investigation to the longer full name.

## Cell 10

### A
- Correct: **incorrect**. Node info says `/alder/pewter` cannot be found, while the final response reports a different `/e1h/alder/pewter` as running.
- Complete evidence: **yes — the exact requested node was checked**. Stopped early: **no**. Format: **not JSON / no answer** (prose and two fenced JSON objects). Format-only: **no**. Failure cause: **wrong entity chosen**.
- Note: The 657 rate is a supported reading for the longer name, not for the exact requested node.

### B
- Correct: **correct**. Node info reports the exact requested `/alder/pewter` not found and the answer reports that exact name as not running.
- Complete evidence: **yes**. Stopped early: **no**. Format: **exact**. Format-only: **no**. Failure cause: —.
- Note: The task specifies no rate in the not-running case.

## Cell 11

### A
- Correct: **correct**. The node list and parameter reads show basalt/sorrel has mode fast and limit 891; the other sorrel reads slow.
- Complete evidence: **yes**. Stopped early: **no**. Format: **not JSON / no answer** (fenced JSON). Format-only: **yes**. Failure cause: **answer format**.
- Note: A failed wrongly prefixed lookup is followed by a successful read of the other node.

### B
- Correct: **correct**. The reads show basalt/sorrel is fast with limit 891 and cobalt/sorrel is slow; those values appear inside `answer`.
- Complete evidence: **yes**. Stopped early: **no**. Format: **other — valid JSON with an extra `answer` wrapper and missing requested top-level keys**. Format-only: **yes**. Failure cause: **answer format**.
- Note: Removing the wrapper yields the requested supported object; whether a scorer does so is not assumed.

## Cell 12

### A
- Correct: **cannot tell**. The service type is shown, but the bulk node-info output is cut before the claimed provider's service list.
- Complete evidence: **cannot tell**. Stopped early: **cannot tell**. Format: **exact**. Format-only: **cannot tell**. Failure cause: **other — packet truncation prevents provider verification**.
- Note: The bulk call includes the named provider among its arguments, but the displayed result does not show the relevant provider-to-service link.

### B
- Correct: **incorrect**. The service-info result provides the type, but the final response explicitly cannot identify the required provider.
- Complete evidence: **no — provider not established**. Stopped early: **yes**. Format: **not JSON / no answer** (extended prose and inconsistent proposed JSON fragments). Format-only: **no**. Failure cause: **name not resolved or guessed**.
- Note: The node-info attempts use unresolved or incomplete names; listing the service and its type does not establish its provider.

## Cell 13

### A
- Correct: **correct**. Separate topic-info results identify each of the three publishers and the subsequent gain reads match the final mapping and values.
- Complete evidence: **yes**. Stopped early: **no**. Format: **not JSON / no answer** (fenced JSON). Format-only: **yes**. Failure cause: **answer format**.
- Note: One short-name gain lookup fails, then the fully qualified retry succeeds.

### B
- Correct: **correct**. The separate topic-info results and gain reads establish all three publisher mappings and values in the answer.
- Complete evidence: **yes**. Stopped early: **no**. Format: **exact**. Format-only: **no**. Failure cause: —.
- Note: An extra topic-list call does not affect the displayed chain.

## Cell 14

### A
- Correct: **correct**. Node info reports the exact `/ember/mistral` not found, and the final answer reports that name as not running.
- Complete evidence: **yes**. Stopped early: **no**. Format: **exact**. Format-only: **no**. Failure cause: —.
- Note: No limit is required for the specified not-running branch.

### B
- Correct: **incorrect**. The exact requested name is not found; the reported running node and limit belong to `/e1h/ember/mistral` instead.
- Complete evidence: **yes — the exact requested name was checked**. Stopped early: **no**. Format: **not JSON / no answer** (prose, a JSON object and a fenced duplicate). Format-only: **no**. Failure cause: **wrong entity chosen**.
- Note: Successful lookup of the longer name does not establish that the distinct requested name is running.

## Per-cell comparison

| Cell | Better supported | Explanation and ending versus earlier choices |
|---|---|---|
| 01 | A on visible evidence; B cannot be resolved | A shows each chain link. B's bulk result is cut; its fenced output differs in form, but the missing displayed evidence prevents attributing the difference to ending or earlier choices. |
| 02 | A | Both read the full chain, but B assigns the first two answer fields to the wrong nodes. This is answer construction at the end, not simply invalid JSON or an unfinished read chain. |
| 03 | A | B reads the setpoint from the previous node and never reads the required node's value. This is an earlier read-chain choice followed by stopping. |
| 04 | A | B reads the proposed final mode before the successful flow read and does not re-read afterward. The problem is the order and stopping point, not just response formatting. |
| 05 | Cannot tell | Both query the three input topics in bulk and read all gains; both bulk results are cut. A has prose and fenced JSON; B has exact JSON. Evidence sufficiency and any substantive difference cannot be settled from the packet. |
| 06 | B | Both gather the ordered reads, but A ends with a reported response error and no answer. The observed difference is at termination or backend response, not the required evidence chain. |
| 07 | Same in substantive support | Both show all chain links and correct values. B adds calls and prose/fenced JSON; A returns exact JSON. The strict-format difference is in the ending. |
| 08 | Cannot tell | Both query the three inputs in bulk and read all gains, but mappings for two inputs are hidden by truncation. A's prose/fenced response and B's exact JSON differ in format; substantive support is unresolved. |
| 09 | A | A treats the filtered suffix match as distinct from the exact name; B reads and answers for the longer name. The difference is entity selection, not only the final format. |
| 10 | B | Both check the exact name; A then substitutes a different fully qualified node, while B answers the exact-name result. The difference is entity selection. |
| 11 | Same in substantive support | Both identify the fast node and its limit. A returns fenced JSON; B wraps the correct fields in `answer`. Differences concern response format, not support. |
| 12 | A potentially, but A cannot be verified | A requests bulk node info and gives a provider, but the relevant result is cut; B never establishes the provider and says so. B's missing read chain is visible; A's support cannot be certified. |
| 13 | Same in substantive support | Both display the publisher and gain chains and correct values. A has a recovered short-name error and fenced JSON; B has an extra listing call and exact JSON. The strict-format difference is at the end. |
| 14 | A | Both check the exact name; B then answers for the different longer name. The difference is entity selection, not merely response formatting. |

No setting or arm identity was inferred or guessed.
