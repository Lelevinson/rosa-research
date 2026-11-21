# Offline replay protocol (frozen 2026-11-16, before any number was computed)

Source: `Claude outputs/2026-11-16_PROMPT_CLAUDECODE_overnight.md`, Job 1. No GPU, no model, no ROS, no held-out data, scorer v2.0 unchanged. Everything below is a *prediction from recorded traces*, not a measurement of the proposed mechanisms: the model's later behaviour after a mechanism fired is unknown.

## Episode set
Recorded fixed-loop episodes: the pilot's fixed loop (arm C1 of `small_model_harness_20261115/RESULTS_LOG.jsonl`, rows not in INFRA_EXCLUDED.json) and all four arms of build round 1 (`build_round1_20261115/RESULTS_LOG.jsonl`, phase `full`). The pilot's other arms (names/reuse/plan variants) are not used. Reported per model and in total; the 80 round-1 control episodes, 240 add-on episodes and 80 pilot episodes are also shown separately. List-argument episodes are read per item.

## Shared definitions
- **Request** = one model response with its tool calls. **Call** = one tool call; a call whose entity argument is a list is one call per item. **Entity argument**: an argument of the tool's schema whose property name, after removing a trailing `_name` and a plural `s`, is `node`, `topic` or `service` (schema-based; no task knowledge).
- **Ledger**: every full name (valid absolute ROS name) seen in a *successful* tool result (failed calls and failed items of list results excluded) or in the task text, with its first source (request, tool or `task`) and the read tools that were run on it. Names are matched by the same rule as the answer gate (`build_round1_20261115/answer_gate.py`).
- **Group** (used for sibling sets): the full names of one JSON list value of a result, or of one text section of a result (the lines under one heading such as `Subscribers:`, `Publishers:`); a result with a single name is a group of one.
- **Tokens**: recorded input+output tokens of a request. Result sizes of siblings the model never queried are *estimated*: median characters of that tool's single-entity results over the episode set, divided by 4.

## Proposal 1: sweep completion (two trigger variants, both evaluated)
- **V1 (two calls)**: request k contains a call of tool T and request k-1 contains a call of the same T with all other arguments equal and a different entity name; both names are in one common group of an earlier result (earlier than request k-1); the group with the fewest names is the sibling set.
- **V2 (one call, small group)**: a call of tool T on entity e whose smallest earlier group containing e has between 2 and **4** names (threshold fixed here, before computing).
- Sweep set = group minus the called names minus names T already ran on with the same other arguments; at most 20 names; stop adding names when the estimated extra result size exceeds 3000 tokens. The sweep result is returned with the triggering call.
- **Predicted saving**: later requests all of whose calls (T, same other arguments, entity inside sweep set or already queried) are covered are removed (partly covered requests are kept). Saved tokens = recorded tokens of removed requests. **Extra tokens** = estimated tokens of sibling results the model never queried later x number of requests that remain after the trigger. Extra tool executions also reported.
- **Pass bar**: predicted saved requests >= 3% of all fixed-loop requests in the set AND predicted extra tokens < predicted saved tokens, for the variant (each variant judged separately).
- Not shown by a replay: whether the changed context changes the model's later choices, and whether sweeping siblings that exist only in other result sections is harmless.

## Proposal 2: stall breaker
- **Stall rule (as written by the owner)**: a call is a stall if (a) its tool and result text equal an earlier call's tool and result text, or (b) it is the second empty / not-found result of the same tool since the last result that added a new name to the ledger. Empty = a result whose only content is empty lists/dicts; not-found = matches `not found|Unable to find|does not exist|no such`. A repeated call that returns a new value is not a stall (it follows from (a)). **Sensitivity rule (a')**: tool, arguments and result text equal (reported next to (a) because two different entities can return equal text by chance).
- First stall: ledger lookup added to its result (cannot be replayed in effect; counted). Second stall on the same tool: tool hidden for the next request only.
- Reported: stalls per episode and per model, requests after the first and after the second stall, stalls inside supported episodes.
- **Harm check and pass bar**: for every second stall, was the tool called in the very next request, and was that call *useful* (its result is successful and adds a new ledger name or a value not seen before)? **Pass if the number of supported episodes in which hiding would have removed a useful call is 0.** All episodes also reported.

## Proposal 3: answer gate with repair
- Replay the final answer (the `final_answer` object, else the last JSON object) of every recorded episode with the episode's own ledger. Rewrite rule: a name-like string in a value or nested key that is not an exact ledger name and is the trailing part of **exactly one** ledger full name is rewritten to it (logged); never invents a name. 2+ candidates: would reject listing them. Never-seen: would reject with a next step (listed-but-unread entities and the tool that reads them; counted whether such a next step exists).
- Rewritten answers are scored with scorer v2.0 (`build_round1_20261115/score_round1.py` adapter) on the episode's own tool rows and reported as their own group.
- **Pass bar**: 0 supported answers become unsupported. Reported: how many unsupported answers become supported by the rewrite alone; how many would be rejected (outcome unknown).

## Stop condition
A rule that cannot be applied without task knowledge or ground truth is reported "not general as written" and is not patched.
