# How the name ledger is built (exact), name-fix applied test

Written 2026-11-18 after Codex's independent review (`CODEX_INDEPENDENT_REVIEW_20261117.md`, SHA-256 `c8704e86...`), which found that in 7 of the 8 rewritten episodes the full name was **reconstructed from separate namespace and name fields**, not seen as one string. The review is right; this file documents the rule exactly. Code: `build_round1_20261115/answer_gate.py` (`names_in_text`, `successful_text_parts`, `allowed_names`), called by `namefix_arm.NameFixArm.final_answer_tool` as `ag.allowed_names(task_text, tool_outputs)`; the rewrite rule `namefix_rule.py` replaces a short form only if **exactly one** ledger name ends with it (whole path segments) and the short form is not itself a ledger name.

## The ledger ("allowed" names) of one episode = the union of
1. **Names in the task text:** every string that matches `NAME_IN_TEXT = (?<![\w/.:-])/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+` (an absolute name that does not follow a word character, `/`, `.`, `:` or `-`; so `std_srvs/srv/Trigger` is not a name).
2. **Names in successful tool results.** For every tool call of the episode, in order, the output is reduced to its *successful* parts (`successful_text_parts`): a result that is a dict with an `error` key contributes nothing; in a result with one entry per requested item (`{item: result}`), the entries that carry an `error` are skipped one by one and the others are kept, as their JSON text; any other result (string or dict) is used as text. From each kept text, two kinds of names are added (`names_in_text`):
   - **(a) contiguous names:** every `NAME_IN_TEXT` match in the text (escaped `\n` first turned into line breaks);
   - **(b) joined names:** for every occurrence of `Node name:<ws>X<ws>Node namespace:<ws>Y` (`NODE_BLOCK`, i.e. the `Node name` line immediately followed by the `Node namespace` line of one endpoint block of `ros2 topic info --verbose`), the name `Y.rstrip('/') + '/' + X`. **This name never appears as one string in the tool output; it is built by the ledger.**
   - **(c)** for a `ros2_node_list` result with a `nodes` list: every list entry that is an absolute name.
3. **Not in the ledger:** names that occur only in failed calls or failed items; names that the model typed in its own arguments or in its answer; anything from the fixture graph (the graph is evaluator-only); the role of a name (publisher or subscriber, which node answers which question): the ledger is a set of strings with no roles. A node that only subscribes to a topic is in the ledger exactly like the publisher, if the topic-info result lists both endpoints.

## What this means for the 8 rewritten episodes (measured by `analyze_namefix.py`, `AUDIT.md`)
| episode | rewritten names | where the full names come from |
|---|---:|---|
| nf_single_2 lfm3 s1 | 1 | joined only (topic-info endpoint block: Node name + Node namespace) |
| nf_single_1 lfm3 s2 | 1 | joined only |
| nf_multi_1 qwen3.5 s2 | 3 | joined only |
| nf_multi_1 gpt-oss s2 | 3 | joined only |
| nf_single_1 bonsai s1 | 1 | joined only |
| nf_multi_2 bonsai s2 | 2 | joined only |
| nf_multi_1 bonsai s1 | 3 | **contiguous** (a successful node-list result contains the three full names) |
| nf_single_1 bonsai s2 | 1 | joined only |
So 7 of 8 episodes (12 of 15 rewritten names) used only joined names; 1 episode (3 names) used contiguous names. The joined name is the correct full name by ROS semantics (the endpoint block states that node, in that namespace, is an endpoint of the topic), and the audit confirmed each equals the task's required identity; but "the name appears in a tool result" was wrong wording and has been corrected in REPORT.md.

## Consequences and limits (interpretation)
- The rule's evidence standard is "the model's session contains the pieces of exactly one full name that ends with this short form", not "the model saw this name". Whether that is acceptable is a design decision of the feature; it is the same standard as the round-2 shadow rewrite (same ledger code).
- The ledger is role-blind, so a short form that is the unique suffix of a **subscriber** would be resolved to it even if the task asked for the publisher. In these 8 episodes this did not happen (each rewrite equals the required identity), but it was not exercised either.
- The audit's own "evidence" check in `analyze_namefix.py` mirrors the ledger's join, so it is not independent of the ledger; the independent confirmation is Codex's review, which read the traces directly.
