# Stall hint v2, Step 1 (offline): result = FAIL, no live run

2026-11-18, Asia/Taipei. Protocol and pass bar: [PROTOCOL_STEP1.md](PROTOCOL_STEP1.md), SHA-256 `fe09b1877d6754f9d3a99f4298650b5708b563eafc1759c600008b2cd5e3c97e`, written and hashed before the script existed. Script: [step1_offline.py](step1_offline.py). Outputs: `step1_results.json` (frozen-protocol run), `step1_fires.jsonl` (every fire with its hint), `step1_results_clean.json` (post-hoc run). CPU only; Ollama was idle (`/api/ps` empty); nothing was run live.

## Measured (frozen protocol; primary population = C1-type episodes of bonsai-2:4b and lfm3:1.7b, 168 episodes)

| bar | needed | measured | result |
|---|---|---|---|
| B0 reproduction of the recount | all 1,248 episodes equal | 1,248 / 1,248 equal (1,788 stall calls) | pass |
| B1 episodes with an informative fire | >= 10% | 42 / 168 = 25.0% | pass |
| B2 first informative fire is *pointed* (entity and tool), supported episodes with a later progress call | >= 50% | 8 / 18 = 44.4% | **fail** |
| B3 pointed fires that are delayed (r+2 or later) | >= 30% | 2 / 8 = 25.0% | **fail** |
| B4 contradicted | <= 25% | 1 / 18 = 5.6% | pass |
| B5 informative share of all fires | >= 50% | 319 / 507 = 62.9% | pass |

Denominator 18 >= 15, so the outcome is conclusive under the protocol: **FAIL, stop, no Step 2.** Fires in this population: 319 informative, 60 repeat-only (the hint can only repeat the model's own name), 128 empty (nothing to match). 85 informative fires are kind mismatches (e.g. a node lookup of a name that was seen as a service). B2 classes: 6 pointed-immediate, 2 pointed-delayed, 1 contradicted, 9 indeterminate (hint has names but the model's next new-information call used a different entity: 6 with a relevant tool suggested, 3 with no known kind so no tool advice).

Other populations (no bar): C1-type all four models: B2 11/21 = 52.4%, B3 4/11 = 36.4%, informative-episode rate 14.9%. All arms: B2 33/60 = 55.0%, B3 13/33 = 39.4%. Round-2 CONTROL seeds 1-2 only (weak models): 4 B2 cases. Round-2 extra seeds only: 7 B2 cases (71.4% pointed). These pass the numeric thresholds but they are not the primary population and the pooled figures include bonsai-dominated enriched seeds; denominators are small.

## What this means (interpretation, labelled)

- Offline, a stall hint with names does appear in about a quarter of weak-model C1 episodes and usually has content (H: that part supports the idea). The weak spot is whether that content is the thing the session later needed: in the 18 supported episodes where it can be checked, it matched the next new-information step in fewer than half the cases, and in most matches (6 of 8) the model took that step in the very next request anyway, so the hint would not have changed the action there.
- The mechanism limit I can see in the cases (H, not proven): the hint is built only from names already seen, but the next needed step is often to query a name not yet seen (e.g. the next node along a parameter chain), which no hint from the record can contain.
- It does **not** show a hint would fail live: this is hindsight agreement on trajectories recorded *without* a hint, 18 episodes, repeated tasks and seeds, synthetic fixtures. It also does not show the old failure ("Repeated call" did not stop loops) is cured; no model response to any hint was measured.

## Defects in my own protocol, found after the results (reported, not patched)

1. **Two ledgers conflated.** The protocol said the hint's ledger is "as in the recount". The recount's ledger counts the echoed name of a *failed* list item (`{'/plant32/cedar': {'error': ...}}`) as seen, because the unit counts as ok. The name-fix ledger (`answer_gate.successful_text_parts`), which the owner named for the hint, skips such items. In the frozen run **69 of 507 primary fires (13.6%; 67 of 319 informative ones)** listed at least one name that only occurred in a failed lookup, i.e. the model's own wrong guess shown back as "already seen". Stall detection must keep the recount ledger (B0); hint content should use the clean one. Post-hoc run `--clean-ledger` (`step1_results_clean.json`): informative 288, B1 24.4%, B2 8/18, B3 2/8, B4 1/18 - **same verdict**.
2. **Exact-string comparison of P's entity.** In 3 of the 9 indeterminate cases the model's later call wrote `plant32/zephyr` without the leading slash. With a leading-slash-normalised comparison (post-hoc, `post_hoc_diagnostics.py`, clean ledger) B2 = 10/18 = 55.6% and B3 = 3/10 = 30.0%, i.e. both at the bar. This is a post-hoc change on 18 episodes and is **not** taken as a pass.
3. Not tested: fairness, ablation, name-fix and compaction runs (different arms); a model's response to a hint; whether the 40-cell live design could detect an effect at +-4 per 40 noise (a 25% informative-episode rate means roughly 10 episodes per model-arm could receive a hint, far too few to see a correctness change).
4. Teammate-context check (`rosa-contexts` member branches) not done: no local clone found; no overlap known.

## Decision requested from the owner

Per the instruction, Step 1 failed its bar, so there is no Step 2 and no live run. If the owner wants a v2.1 anyway, the evidence suggests: fix defect 1 and 2 in a new frozen protocol (reported as a protocol revision, results separate), and decide whether a hint that can only contain already-seen names can ever address the cases where the needed entity is unseen. I have not designed or run that.
