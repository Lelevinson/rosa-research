# Build round 2: sweep completion (live) and answer rewrite (shadow), live test report (2026-11-17)

Written for: the project owner. Protocol and bars frozen before any full-run episode ([PROTOCOL.md](PROTOCOL.md) and amendments 1-4, hashes in `PROTOCOL*.sha256` and [FREEZE.json](FREEZE.json)); numbers by [analyze_round2.py](analyze_round2.py) -> `ANALYSIS.json`, `TABLES.md`. 352 valid episodes (CONTROL 176, SWEEP 176), four models, development tasks only, scorer v2.0, no held-out data. Nothing here is a novelty or significance claim.

| | |
|---|---|
| **Result** | **Sweep completion passes every frozen bar; answer rewrite passes.** First-firing episodes: CONTROL 17, SWEEP 20 (V-b, V-c met, no add-on needed). Re-ask rate 15% in SWEEP vs 65% in CONTROL (bar <= 25%). Mean requests after the firing 2.95 vs 4.59 (-1.64; bar -1.0), median 2 vs 3, mean tokens after 28.9k vs 33.7k (-14%). P4: 2 unsupported fired SWEEP episodes hand-read, 0 caused by the sweep. Rewrite: 0 of 296 answers went from supported to unsupported; 2 went the other way (1 cell). |
| **What it changes** | The fixed loop with a system-run sweep removes most of the one-by-one re-reads the model otherwise does after a two-call scan (the model did read the swept names itself in 11 of 17 CONTROL events, in 3 of 20 SWEEP events). The result is a live test on development tasks with small events (17 and 20) and it is carried by two tasks (h4 and v2: 19 of 20 SWEEP events), so it is not yet evidence for held-out tasks. |
| **What it cannot show** | Effects on whole-episode outcomes: the two arms diverge before the firing (sampling), so "requests after the firing" is a per-event measure, not a matched comparison, and whole-arm totals (SWEEP 146 vs CONTROL 141 supported of 176; 1,558 vs 1,599 requests) are shown for the record only. lfm3 shows no gain (4.17 vs 4.33 requests after). A very large group is swept only partly (one lfm3 event: 20 of 132 service names, which was not a useful sibling set). |
| **Adoption-free?** | Yes for the action (the system runs the reads), but the model must use the appended results: it did (re-ask 15%); one lfm3 episode shows it can ignore them. |
| **Cost** | 22 live firings ran 220 extra tool runs (about 25k estimated result tokens); the run was interrupted by oracle stops and resumed three times (section 5); total wall time was not summed. |

## 1. Bars (PROTOCOL.md section 8)
| bar | rule | result | verdict |
|---|---|---|---|
| V-a | payload identity without trigger | unit test passes (14 tests, `tests/test_round2.py`) | met |
| V-b | first-fire counts within factor 2 | 17 vs 20 | met |
| V-c | >= 15 per arm from >= 3 models | 17 / 20 from 4 models each | met (add-on not run) |
| P1 | re-ask rate in SWEEP <= 25% (FAIL at >= 50%) | 15% (CONTROL 65%) | **pass** |
| P2 | mean requests after fire lower by >= 1.0; median not higher; holds without the largest CONTROL event | 4.59 -> 2.95 (-1.64); median 3 -> 2; holds | **pass** |
| P3 | mean tokens after fire lower | 33,712 -> 28,883 | **pass** |
| P4 | hand-read each fired SWEEP episode that ends unsupported: 0 caused by the sweep | 2 read, 0 caused (section 3) | **pass** |
| Rewrite | 0 supported answers become unsupported | 0 of 296 | **pass** |
Sweep verdict (all of P1-P4 and no FAIL condition): **PASS**.

## 2. Tables
Unit = first firing in an episode (live or shadow). Per arm: events, re-ask, mean requests after, median, mean tokens after, supported answers of the event episodes.
| arm | events | models | re-ask | mean req. after | median | mean tokens after | supported |
|---|---:|---:|---:|---:|---:|---:|---:|
| CONTROL (shadow) | 17 | 4 | 0.65 | 4.59 | 3 | 33,712 | 14 |
| SWEEP (live) | 20 | 4 | 0.15 | 2.95 | 2 | 28,883 | 18 |
Later firings in the same episodes (not used): CONTROL 4, SWEEP 2. Live extra: 220 tool runs, about 24.8k estimated tokens. Cut by the name limit (20): lfm3 v2 seed 10 (112 of 132 names; both arms log it); by the 3000-token limit: 2 to 3 names in five events. `sweep_empty_after_limit`: 0.

| model | CONTROL events (re-ask, mean after) | SWEEP events (re-ask, mean after) |
|---|---|---|
| bonsai-2:4b | 2 (1.00, 13.5) | 2 (0.50, 4.0) |
| gpt-oss:20b | 5 (0.80, 3.2) | 7 (0.00, 2.4) |
| lfm3:1.7b | 6 (0.50, 4.2) | 6 (0.33, 4.3) |
| qwen3.5:9b | 4 (0.50, 2.5) | 5 (0.00, 1.6) |
| task | CONTROL | SWEEP |
|---|---|---|
| h4 | 11 events, 3.91 after | 10 events, 2.70 after |
| v2 | 5 events, 6.80 after | 9 events, 3.44 after |
| e1h_amb_2 | 1 | 1 |
Share of events on the largest task: h4 11 of 17 (65%) in CONTROL, 10 of 20 (50%) in SWEEP. Tools of the first firings (SWEEP): node info 8, topic info 5, param get 4, param list 2, service info 1.

Whole-arm totals, for the record only: CONTROL 141 supported, 1,599 requests, 6.91M tokens; SWEEP 146, 1,558, 6.81M. Same-cell (176 cells): both supported 140, only SWEEP 6, only CONTROL 1, neither 29. Aborts (non-iteration): CONTROL 2 (gpt-oss, both `ResponseError` tool-call parse errors), SWEEP 0; iteration-cap hits 0 in both arms.

## 3. Hand reading (five episodes; traces under `research/_artifacts/runs/build_round2_20261116/`)
1. **lfm3 v2 seed 10, SWEEP, unsupported** (`full_20261116T003046Z/lfm3_1.7b-stage3/033-v2-SWEEP-lfm3_1.7b-s10`): the model scanned `get_parameter_types`/`describe_parameters` services of nodes (a 132-name group of all services); the sweep read 20 of them (112 cut), which are unrelated to the asked service. It answered node `/plant32/cedar`, a name it guessed from the task's service name `cedar_reset` (its third call listed nodes with pattern `cedar`); the same wrong node is the answer in CONTROL (25 requests, unsupported, with a short type `Trigger`). Not caused by the sweep; but the firing did not help and the episode ran 7 requests longer than its CONTROL pair. A group this large is not a meaningful sibling set (see the proposal below).
2. **lfm3 h4 seed 3, SWEEP, unsupported** (`.../040-h4-SWEEP-lfm3_1.7b-s3`): the only issue is an extra key (`gains[/plant32/anvil]`, a node that was the starting node and not a publisher); all required values and names are correct. The model read anvil's gain itself before the firing. Not caused by the sweep; the CONTROL pair (`060-h4-CONTROL-...-s3`) was supported in 14 requests against 11.
3. **bonsai v2 seed 2** (`full_resume2_20261116T132848Z/bonsai-2_4b-stage3/008-v2-CONTROL-...-s2` vs `017-v2-SWEEP-...-s2`), both supported: CONTROL scanned all 19 nodes with node info one per request (31 requests); SWEEP fired at request 10 after two node infos, swept 14 nodes, finished in 16 requests. The clearest case of the mechanism.
4. **gpt-oss h4 seed 5** (`.../gpt-oss_20b-stage3/038-h4-CONTROL-...-s5` vs `021-h4-SWEEP-...-s5`), both supported, 10 requests each. The paired "requests after the firing" (6 vs 1) is an artefact: the two trajectories differ from request 3 on, so the firings happen at different requests (4 vs 9). Do not read per-cell pairs as matched effects.
5. The paired-cell list in `ANALYSIS.json` (`paired_cells_both_fired`, 12 cells) is descriptive only; for the same reason (diverging trajectories) it cannot be used as a test.

## 4. Answer rewrite (shadow in both arms)
296 final answers with an object. The rewrite would change 2 (both `upstream: quill` -> `/plant32/quill`, bonsai u3 seed 8, one cell in both arms), and both would turn an unsupported answer into a supported one; 0 supported -> unsupported. Would-reject: 13 answers with a full name never seen (all with listed-but-unread entities in the ledger), 0 ambiguous, 0 of them supported. **PASS** (and the live value is small: one cell).

## 5. Validity and infrastructure (all logged; labels unchanged)
- One missed scripted change (known hook defect): `e1h_chg_2` seed 2, CONTROL, gpt-oss; kept as is. No backend (CUDA) crashes.
- **Oracle / node-discovery stops** (details in BUILD_LOG.md and [DISCOVERY_FLAKES.md](DISCOVERY_FLAKES.md)): the end-of-session oracle failed in the smoke (juniper not listed) and in lfm3 stage 3 (first try, rescued by the retry of amendment 1); qwen3.5 stage 3 stopped at `after-012` (before amendment 2) and again at `after-048` after its retry (amendment 2). Those two qwen3.5 sessions (12 + 48 episodes) are excluded as "excluded: infrastructure (oracle)" (`INFRA_EXCLUDED.json`) and the session was rerun from the start; the 88 lfm3 episodes stay. Failures were in sessions with both arms, so no arm-specific signal (amendment 1's flag: no SWEEP-only failures). Root cause: the oracle's `--no-daemon --spin-time 4` node list (DISCOVERY_FLAKES.md); with amendment 4 (daemon read, raw log) the resumed run had **0 oracle failures in 30 reads** (not comparable as a rate; sessions and load differ).
- **Deviation found at build time (logged, no rule changed):** the replay's trigger treats names of the same list call as unread; the protocol excludes all names called in request k. On the 400 recorded episodes the replay-mimic gives the replay's 31 triggers, the protocol rule 22 in 19 episodes (BUILD_LOG.md).
- Smoke episodes (4) are not in any total. No add-on run.

## 6. Limits
Development tasks and fixtures only; four small models; small events (17, 20); arms diverge before firing; the effect sits mainly on h4 and v2 (the V1 tasks), nothing was tested on tasks without a two-call scan; lfm3 did not gain; sibling groups much larger than 20 are only partly swept (one lfm3 case). Whole-arm differences (5 supported cells, 41 requests) are within the noise seen in earlier rounds and are not evidence.

## 7. Proposal (not run)
If the owner wants a follow-up: run the same arms on the held-out-style tasks only after a freeze; and for large groups (> 20 names) do not fire at all (a size cap is a rule change, so a new protocol and a new round, not a patch).
