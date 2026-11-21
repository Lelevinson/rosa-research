# REPEATS_READING: why does Qwen repeat successful reads? (design input, not a stage; saved traces only)

Population: every RED (repeat) request in the Qwen A1 traces (Stage 3b, 22) and Qwen A2 traces (Stage 3d, 22), supported-complete episodes with excess > 0, as labelled by `stage3_labels.py`. Nothing was run. Definitions:

- **Not every RED is an identical repeat.** The Stage 3 labeller also gives RED to a `param_list` on a node when the parameter name is already in the task text (4 per arm). These have no identical earlier call; they are listed in the table (`dist` = n/a) and excluded from the counts, which use the identical repeats only (18 per arm).
- **dist**: requests back to the nearest earlier request containing the identical call (for a batch, the largest over its calls); 1 = the request just before.
- **src result**: the earlier result(s) of that identical call: all successful in this population; length in characters; `trunc` = a truncation marker in the text (none is expected; param/node results are short).
- **ans in src / ans in history**: how many of the task's expected-answer values (leaves of `stage3_tasks.json` answer, keys included) appear in that earlier result / in all successful results before the repeat, out of the total. `yes` = the earlier result held an answer value; the history column says how much of the answer was already held.
- **same string**: the proposed tool call(s) (name and arguments as stored in `model_end.tool_calls`) equal the immediately preceding request's. The trace stores parsed calls, not raw tokens, so this is the best available proxy for 'exact token string'.
- **text**: first line of the model's text in the repeating request (`none` if empty); **claimed done** = that text matches a done phrase ('all the information', 'final answer', 'compile', 'summary', ...), a regex on my part.

| arm | episode | req / line | call | dist | src len | trunc | ans in src | ans in history | between | same string | text before the repeat | claimed done | next |
|---|---|---|---|---:|---:|---|---|---|---|---|---|---|---|
| A1 | 03-h2-ollama-r0 | R4 / 22 | node_info(['/anvil']) | 1 | 970 | no | yes (7/7) | 7/7 | nothing | yes | I found the node information. The node `/plant32/anvil` publishes `/plant32/reef_t`. Now I need | no | final answer |
| A1 | 05-u4-ollama-r0 | R5 / 28 | param_list(/quill) | n/a | n/a | no | n/a (0/4) | 3/4 | n/a | no | Now I need to get the gain parameter of the `/plant32/quill` node. Let me list its parameters f | no | a new call |
| A1 | 13-v2-ollama-r0 | R4 / 58 | service_info(['/cedar_reset']) | 3 | 50 | no | yes (1/2) | 2/2 | other tool calls | no | I found it! Looking through the node information, I can see that `/plant32/wharf` has the servi | no | another repeat |
| A1 | 13-v2-ollama-r0 | R5 / 64 | service_info(['/cedar_reset']) | 1 | 50 | no | yes (1/2) | 2/2 | nothing | yes | Based on my analysis of the ROS2 node information, I found that: | no | final answer |
| A1 | 14-h4-ollama-r0 | R4 / 26 | param_list(/zephyr) ; param_list(/dune) ; param_list(/oasis) | n/a | n/a | no | n/a (0/13) | 10/13 | n/a | no | Now I have the publishers for each input topic: | no | a new call |
| A1 | 14-h4-ollama-r0 | R6 / 54 | param_get(/zephyr, gain) | 1 | 34 | no | yes (1/13) | 13/13 | nothing | no | Now I have all the information needed. Let me compile the JSON response: | yes | final answer |
| A1 | 22-u2-ollama-r0 | R5 / 28 | param_get(/yarrow, gain) | 1 | 34 | no | yes (1/2) | 2/2 | nothing | yes | none | no | another repeat |
| A1 | 22-u2-ollama-r0 | R6 / 34 | param_get(/yarrow, gain) | 1 | 34 | no | yes (1/2) | 2/2 | nothing | yes | I found the node and its gain parameter. The response shows "Integer value is: 50", so the gain | no | final answer |
| A1 | 25-h2-ollama-r1 | R4 / 22 | node_info(['/anvil']) | 1 | 970 | no | yes (7/7) | 7/7 | nothing | yes | I found the node information. The node `/plant32/anvil` publishes `/plant32/reef_t`. Now I need | no | final answer |
| A1 | 27-h4-ollama-r1 | R4 / 26 | param_list(/zephyr) ; param_list(/dune) ; param_list(/oasis) | n/a | n/a | no | n/a (0/13) | 10/13 | n/a | no | Now I have the publishers for each input topic: | no | a new call |
| A1 | 27-h4-ollama-r1 | R6 / 54 | param_get(/zephyr, gain) | 1 | 34 | no | yes (1/13) | 13/13 | nothing | no | Now I have all the information needed. Let me compile the JSON response: | yes | final answer |
| A1 | 29-u3-ollama-r1 | R6 / 34 | node_info(['/yarrow']) | 3 | 892 | no | yes (2/3) | 3/3 | other tool calls | no | Now I have confirmed all the information. Let me compile the JSON response: | yes | final answer |
| A1 | 37-v2-ollama-r1 | R4 / 58 | service_info(['/cedar_reset']) | 3 | 50 | no | yes (1/2) | 2/2 | other tool calls | no | I found it! Looking through the node information, I can see that `/plant32/wharf` has the servi | no | another repeat |
| A1 | 37-v2-ollama-r1 | R5 / 64 | service_info(['/cedar_reset']) | 1 | 50 | no | yes (1/2) | 2/2 | nothing | yes | Based on my analysis of the ROS2 node information, I found that: | no | final answer |
| A1 | 38-u2-ollama-r1 | R5 / 28 | param_get(/yarrow, gain) | 1 | 34 | no | yes (1/2) | 2/2 | nothing | yes | none | no | another repeat |
| A1 | 38-u2-ollama-r1 | R6 / 34 | param_get(/yarrow, gain) | 1 | 34 | no | yes (1/2) | 2/2 | nothing | yes | I found the node and its gain parameter. The response shows "Integer value is: 50", so the gain | no | final answer |
| A1 | 46-u4-ollama-r1 | R5 / 28 | param_list(/quill) | n/a | n/a | no | n/a (0/4) | 3/4 | n/a | no | Now I need to get the gain parameter of the `/plant32/quill` node. Let me list its parameters f | no | a new call |
| A1 | 46-u4-ollama-r1 | R8 / 46 | param_get(/quill, gain) | 2 | 34 | no | yes (1/4) | 4/4 | other tool calls | no | none | no | another repeat |
| A1 | 46-u4-ollama-r1 | R9 / 52 | param_get(/yarrow, gain) | 2 | 34 | no | no (0/4) | 4/4 | other tool calls | no | Based on my investigation, I have gathered all the required information: | yes | another repeat |
| A1 | 46-u4-ollama-r1 | R10 / 58 | param_get(/yarrow, gain) | 1 | 34 | no | no (0/4) | 4/4 | nothing | yes | Now I have all the information needed to construct the JSON response: | yes | another repeat |
| A1 | 46-u4-ollama-r1 | R11 / 64 | param_get(/quill, gain) | 3 | 34 | no | yes (1/4) | 4/4 | other tool calls | no | none | no | another repeat |
| A1 | 46-u4-ollama-r1 | R12 / 70 | param_get(/yarrow, gain) | 2 | 34 | no | no (0/4) | 4/4 | other tool calls | no | Based on my investigation, here's the complete information: | yes | final answer |
| A2 | 00-h3-ollama-r0 | R4 / 26 | topic_info(['/courier_t', '/fjord_t', '/prism_t']) | 1 | 2999 | no | yes (7/7) | 7/7 | nothing | yes | Now I have all the information needed. Let me compile the JSON response: | yes | final answer |
| A2 | 04-u3-ollama-r0 | R4 / 22 | topic_info(['/quarry_t']) | 3 | 548 | no | yes (1/3) | 3/3 | other tool calls | no | Now I have all the information I need: | yes | another repeat |
| A2 | 04-u3-ollama-r0 | R5 / 28 | node_info(['/yarrow']) | 3 | 892 | no | yes (2/3) | 3/3 | other tool calls | no | Based on the information gathered, I can now provide the answer: | no | final answer |
| A2 | 05-h2-ollama-r0 | R3 / 16 | node_info(['/anvil']) | 1 | 970 | no | yes (7/7) | 7/7 | nothing | yes | Perfect! I have the information I need. The node `/plant32/anvil` publishes `/plant32/reef_t`.  | no | final answer |
| A2 | 06-v4-ollama-r0 | R6 / 70 | param_get(/lumen, gain) | 1 | 34 | no | yes (1/3) | 3/3 | nothing | yes | I have all the information needed. Let me compile the JSON response: | yes | final answer |
| A2 | 07-h4-ollama-r0 | R4 / 26 | param_list(/zephyr) ; param_list(/dune) ; param_list(/oasis) | n/a | n/a | no | n/a (0/13) | 10/13 | n/a | no | Now I have the publishers for each input topic: | no | a new call |
| A2 | 07-h4-ollama-r0 | R6 / 54 | param_get(/zephyr, gain) ; param_get(/dune, gain) ; param_get(/oasis, gain) | 1 | 104 | no | yes (3/13) | 13/13 | nothing | yes | Now I have all the information needed. Let me compile the JSON response: | yes | final answer |
| A2 | 10-u2-ollama-r0 | R3 / 16 | param_get(/yarrow, gain) | 1 | 34 | no | yes (1/2) | 2/2 | nothing | yes | none | no | final answer |
| A2 | 11-u4-ollama-r0 | R5 / 28 | param_list(/quill) | n/a | n/a | no | n/a (0/4) | 3/4 | n/a | no | Now I need to get the gain parameter of the upstream node `/plant32/quill`. Let me list its par | no | a new call |
| A2 | 11-u4-ollama-r0 | R8 / 46 | param_get(/quill, gain) | 2 | 34 | no | yes (1/4) | 4/4 | other tool calls | no | I have all the information needed. Let me compile the final answer: | yes | another repeat |
| A2 | 11-u4-ollama-r0 | R9 / 52 | param_get(/quill, gain) | 1 | 34 | no | yes (1/4) | 4/4 | nothing | yes | Based on my investigation, here's the complete information: | yes | final answer |
| A2 | 12-u4-ollama-r1 | R5 / 28 | param_list(/quill) | n/a | n/a | no | n/a (0/4) | 3/4 | n/a | no | Now I need to get the gain parameter of the upstream node `/plant32/quill`. Let me list its par | no | a new call |
| A2 | 12-u4-ollama-r1 | R8 / 46 | param_get(/quill, gain) | 2 | 34 | no | yes (1/4) | 4/4 | other tool calls | no | I have all the information needed. Let me compile the final answer: | yes | another repeat |
| A2 | 12-u4-ollama-r1 | R9 / 52 | param_get(/quill, gain) | 1 | 34 | no | yes (1/4) | 4/4 | nothing | yes | Based on my investigation, here's the complete information: | yes | final answer |
| A2 | 13-h2-ollama-r1 | R3 / 16 | node_info(['/anvil']) | 1 | 970 | no | yes (7/7) | 7/7 | nothing | yes | Perfect! I have the information I need. The node `/plant32/anvil` publishes `/plant32/reef_t`.  | no | final answer |
| A2 | 14-u3-ollama-r1 | R4 / 22 | topic_info(['/quarry_t']) | 3 | 548 | no | yes (1/3) | 3/3 | other tool calls | no | Now I have all the information I need: | yes | another repeat |
| A2 | 14-u3-ollama-r1 | R5 / 28 | node_info(['/yarrow']) | 3 | 892 | no | yes (2/3) | 3/3 | other tool calls | no | Based on the information gathered, I can now provide the answer: | no | final answer |
| A2 | 16-h4-ollama-r1 | R4 / 26 | param_list(/zephyr) ; param_list(/dune) ; param_list(/oasis) | n/a | n/a | no | n/a (0/13) | 10/13 | n/a | no | Now I have the publishers for each input topic: | no | a new call |
| A2 | 16-h4-ollama-r1 | R6 / 54 | param_get(/zephyr, gain) ; param_get(/dune, gain) ; param_get(/oasis, gain) | 1 | 104 | no | yes (3/13) | 13/13 | nothing | yes | Now I have all the information needed. Let me compile the JSON response: | yes | final answer |
| A2 | 17-v4-ollama-r1 | R6 / 70 | param_get(/lumen, gain) | 1 | 34 | no | yes (1/3) | 3/3 | nothing | yes | I have all the information needed. Let me compile the JSON response: | yes | final answer |
| A2 | 19-h3-ollama-r1 | R4 / 26 | topic_info(['/courier_t', '/fjord_t', '/prism_t']) | 1 | 2999 | no | yes (7/7) | 7/7 | nothing | yes | Now I have all the information needed. Let me compile the JSON response: | yes | final answer |
| A2 | 23-u2-ollama-r1 | R3 / 16 | param_get(/yarrow, gain) | 1 | 34 | no | yes (1/2) | 2/2 | nothing | yes | none | no | final answer |

## Counts

| group | repeats | distance 1 | distance > 1 | earlier result success | earlier result error | earlier result held an answer value | whole answer already in history | truncated | same string as preceding call | had model text | claimed done in the text | nothing in between | next: another repeat / final answer |
|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | 18 | 11/18 (61%) | 7/18 (39%) | 18/18 (100%) | 0/18 | 15/18 (83%) | 18/18 (100%) | 0/18 (0%) | 9/18 (50%) | 14/18 (78%) | 6/18 (33%) | 11/18 (61%) | 8/18 (44%) / 10/18 (56%) |
| A2 | 18 | 12/18 (67%) | 6/18 (33%) | 18/18 (100%) | 0/18 | 18/18 (100%) | 18/18 (100%) | 0/18 (0%) | 12/18 (67%) | 16/18 (89%) | 12/18 (67%) | 12/18 (67%) | 4/18 (22%) / 14/18 (78%) |
| both | 36 | 23/36 (64%) | 13/36 (36%) | 36/36 (100%) | 0/36 | 33/36 (92%) | 36/36 (100%) | 0/36 (0%) | 21/36 (58%) | 30/36 (83%) | 18/36 (50%) | 23/36 (64%) | 12/36 (33%) / 24/36 (67%) |

## Plain observation (no conclusion about mechanism)
Of the 36 identical repeats (18 per arm), all repeat a read that had succeeded, none is truncated, and in all 36 the history already held every expected answer value when the repeat was issued. 23 of 36 (64%) repeat the call of the request just before (distance 1) and 21 of 36 (58%) have the same parsed call as that preceding request; the other 13 (36%) sit 2 to 3 requests back, after other successful calls, and none follows a failed call. In 30 of 36 the repeating request carried model text, and in 18 of 36 that text already states the answer or says it is compiling it ("I have all the information needed") while the request still issues the call. Under A2 the repeats are shorter loops than under A1 (the next request is another repeat in 4 of 18 against 8 of 18, and the final answer in 14 of 18 against 10 of 18).
Limits: the trace stores parsed tool calls, not raw token text, so "same string" is a proxy; the 36 repeats come from 24 episodes, and Qwen's two repeats per task at temperature 0 are near-duplicates (the true sample is smaller); the answer-held test is a string match against the task's expected values; 8 further RED requests (4 per arm) are listed above but are `param_list` calls, not repeats, and are excluded from the counts.
