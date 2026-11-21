# DRAFT protocol: start block (name resolution at episode start) — NOT frozen, NOT run (2026-11-17)

Status: draft for the owner. CPU only; nothing was run or implemented beyond the offline counts of REPORT.md section 1. It becomes a protocol only when the owner approves it and its SHA-256 is written before any episode. The "not listed" part of the offline variant is **removed** (it used later failures, i.e. knowledge from the future).

## 1. Preflight decision record (AGENTS.md)
- **Observed opportunity and evidence.** In the 400 recorded fixed-loop episodes, the model often spends requests turning a short task word into a full name: of the 280 requests the offline count marked as covered by the start block, 200 were list calls whose pattern contains a task word and 79 were failed calls on a bare task word the block maps (1 mixed) (REPORT.md section 1; offline prediction 280 of 2,430 requests, 11.5%, 71k tokens added vs 907k saved; per model bonsai 17.2%, gpt-oss 13.7%, lfm3 8.9%, qwen3.5 1.6%). Re-counted without the "not listed" rule (removed here) the prediction is unchanged, 280 (no covered request depended on it); it rests on an untested assumption (the model skips the search).
- **Candidate vs control action difference.** CONTROL: the fixed loop as it is (round 1 arm C1). START BLOCK: the same loop with one block of text added to the first user message, built by the system from the three list tools, mapping task words to full names. Nothing else differs. **This changes what the model sees** (a few dozen tokens in the first request); it does not change tools, schemas, descriptions, the system prompt or any later message.
- **Closest prior mechanisms.** (a) The structure-snapshot replay (`snapshot_replay_20261115`): putting node list, topic list, service list and every node's info in the context removed 28 to 107 requests per model but its text cost more input tokens than it saved for 3 of 4 models; the start block is the small version of that idea (only task words, no per-node info) and must show it does not repeat the cost. (b) Round 2's sweep completion (system completes a scan the model started): different trigger and moment. (c) The pilot's name/reuse arms (`small_model_harness_20261115`): not re-read for this draft; to be checked before the freeze. No novelty claim is made; entity grounding by name lookup is ordinary practice.
- **Fair evaluation and cost.** Matched cells (same task, model, seed), both arms in the same fixture session, same oracle and stop rules as round 2 (amendments 1 to 4 apply unchanged). Cost: the block's tokens counted in every request of the BLOCK arm, three extra list tool runs per BLOCK episode (not model requests, logged).
- **Smallest decision-changing next action and stop rule.** A smoke of 4 episodes (payload and block check), then the full run below. Stop: oracle failure after its retry, payload identity failure, or a block that differs from the expected one (section 3).

## 2. Mechanism (all rules frozen at approval)
At episode start, before request 1, the system runs `ros2_node_list`, `ros2_topic_list` and `ros2_service_list` (no arguments) and takes the full names. A **task word** is a maximal run of letters, digits and underscores in the task text, in order of first occurrence. A task word is **mapped** if it equals the final path segment of at least one listed full name (kind = the list it came from), or if a listed full name occurs in the task text as a whole. Entries: the word, then every matching full name with its kind, in list order; at most 5 matches per word and 10 words (more are cut and the cut is logged). No word is ever mentioned unless it is mapped. If no word is mapped there is no block and the first message is unchanged.

Fixed text (wording frozen at approval; not changed afterwards):
```
Names in the system that match words in the task (full name, kind):
{word}: {full name} ({kind})[, {full name} ({kind})]
```
one line per mapped word. The block is added to the first user message after the task text, separated by one blank line. The three list results are **not** shown to the model as tool calls. A full name that is already in the task text is mapped to itself.

No per-task or per-application map, no ground truth, no choice between matches (two matches are both shown), and the system never answers for the model. Offline, all 18 development tasks give a block (1 to 3 mapped words); the e1h look-alike tasks (`amb_1`, `amb_2`) show two matches for one word.

## 3. Arms and design
- **CONTROL** = round 1 arm C1 (fixed loop); the block is computed and logged (`start_block_shadow`) but not added. **BLOCK** = the same with the block added. Round 2's sweep and rewrite are **not** part of either arm (their combination is not tested). The answer gate and the nudge stay off.
- Cells: the round 2 plan (enriched tasks h4, u3, v2 seeds 1 to 10, other development tasks seeds 1 and 2, four models, e1h and stage 3; 176 cells, 352 episodes), new master seed, same session structure and oracle rules (amendments 1 to 4), smoke of 4 episodes first (not in totals). Wall time about 4 hours. A smaller option, if the owner prefers: the enriched tasks only (h4, u3, v2, seeds 1 to 10, 4 models = 120 cells, 240 episodes) — to be chosen at approval.
- **Checks before the full run:** (V-a) with the block removed from the first message, the first-request payload of BLOCK equals CONTROL byte for byte on every task; (V-b) the live block equals the offline block of `START_BLOCK` for every task (computed from the real list tools of the running fixture); (V-c) no list tool run is counted as a model request.

## 4. Measures and bars (to be frozen)
Unit: the episode; paired by cell.
- **Primary:** mean requests per episode, BLOCK vs CONTROL, pooled and per model. **Adoption:** share of episodes with a list call whose pattern contains a mapped word, BLOCK vs CONTROL.
- **Secondary:** mean input+output tokens per episode (the block's tokens included), supported cells won and lost, wall time.
- **Bar for "worth a second look"** (all must hold): (1) mean requests lower by at least 5% pooled and lower in at least 3 of 4 models; (2) mean tokens per episode not higher; (3) supported cells: cells lost minus cells won at most 2, and every lost cell read by hand (look-alike names, wrong entity); (4) adoption: the share of episodes with a name-resolving list call falls by at least half. If (4) fails the mechanism was not adopted whatever the other numbers say. The `amb` tasks (look-alike names) are reported on their own with every episode read by hand.
- Not claimed: anything about held-out tasks or other fixtures; two seeds in most cells make per-cell flips common (round 1 saw it), so the bar uses pooled and paired totals only.

## 5. Limits stated in advance
The block gives names, not answers; if the model still has to choose between two matches it can choose wrongly (this is what the `amb` reading checks). The benefit shown offline depends on models that search for names with `pattern`; qwen3.5 rarely does. The development fixtures are synthetic, one naming scheme: a name map built from the three lists is cheap here (19 nodes, 21 topics, 135 services) and may not be on a large system (cap of 10 words and 5 matches, but the list calls themselves would be larger). Per-task and per-model effects are descriptive.

## 6. Decisions for the owner before freezing
1. Full design (352 episodes) or enriched tasks only. 2. Whether to include the e1h `amb` tasks in the primary count or only in their own reading. 3. Approval of the fixed text in section 2.
