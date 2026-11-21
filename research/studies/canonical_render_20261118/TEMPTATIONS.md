# Temptation log: places where a tool-, field- or fixture-specific rule suggested itself (none was added)

Started 2026-11-18 while sampling saved results to design the renderer, and kept while writing and testing it. Format: what the rule would have done, why it is outside the two principles. Rules R1-R8 of `PROTOCOL_OFFLINE.md` are the only rules.

1. **Drop `Topic type hash`, `GID` and the QoS block of topic info** (about half the characters of a topic-info result). Would shrink tokens; it removes facts and names a tool's fields. Not allowed (lossless, no tool-specific rules).
2. **Turn `Integer value is: 74` into a typed value (`gain = 74`, a JSON number).** Names one tool's phrasing. R7: it is only a key-value line.
3. **Node info: treat the first bare line (`/plant32/anvil`) as the node name, turn `Subscribers:` / `Publishers:` / `Service Servers:` into lists, mark `/parameter_events` and `/rosout` as noise.** Section semantics belong to one tool.
4. **Drop the seven standard parameter services (`describe_parameters`, ..., `set_parameters_atomically`) that every node lists** in node info and in the service list (the largest repeated boilerplate in the long results). Fixture- and ROS-default-specific; removes facts.
5. **Strip the two leading spaces of parameter-list entries** and drop `start_type_description_service` / `use_sim_time`. Entries are list items (bare lines); changing them is tool-specific and the dropped ones are facts.
6. **Group the service list by node.** Needs knowledge that a service name is `<node>/<suffix>`: a naming convention of one tool's output.
7. **Role labels: write `Publisher: /plant32/anvil` using `Endpoint type: PUBLISHER`.** Would make the ledger role-aware (the known gap of the name-fix ledger) but reads the meaning of one field. Not generic.
8. **Match the literal key `Node name` / `Node namespace`.** The prefix `P` of R6 handles it without naming the field; the literal match was the shorter code.
9. **Resolve a slashless name argument at call time (candidate (a) of the candidate counts)** when a unique ledger suffix exists. It is an input rule with a ledger, not a result rendering; kept out.
10. **Add a hint to the not-found / "Could not determine the type for the passed topic" error text** (for example "this topic may not exist; list topics first"). Error text is outside the two principles (R8).
11. **Truncate `roslog_list` (186 files) to the newest few.** Removes facts, one tool's list.
12. **Rewrite `Publisher count: 1` / `Subscription count: 0` as sentences or flag `Subscription count: 0` as "nobody subscribes".** Interpretation of one tool's fields.
