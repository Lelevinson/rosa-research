# Stage 1 exam-path dress rehearsal: report (2026-11-22)

Written for the owner and Codex. Public development tasks only; no held-out task read; no frozen file edited (`verify_freeze.py` passed before the run; the frozen launcher, bridge, queue, scorer and analysis files were only imported); no push. Run folder: `research/_artifacts/runs/exam_dress_rehearsal_20261122/` (traces; not in Git). Rules: [RULES.md](RULES.md) with Amendment 1.

## Top box
- **Run:** shortened by owner instruction (time) to a balanced subset: 6 `e1h` tasks x 4 core models x {EX-M, E1} x seed 1 = **48 cells, 24 pairs**, run through the frozen `queue_core` -> `queue_bridge` -> `bridge` -> scorer v2.0 -> compact row -> `analyze_primary.py`. 48 of 48 done, stopped with the STOP file, no leftover process, ROS domain empty. **The laptop is free.**
- **Rules 1, 2, 3, 4, 6: PASS. Rule 5: one FLAG (gpt-oss, see below), judged not a wiring bug on the evidence we have.**
- **Big caveat:** the custodian's real pool, manifest, fixture runtime and scorer adapter were NOT used (I may not open them). A stand-in dev runtime was used. The rehearsal tests the queue, launcher, worker, arms, row/compact assembly and analysis plumbing, not the real fixtures.

## Pass/fail per rule (subset of 48 cells; rules unchanged apart from the arithmetic in Amendment 1)
| Rule | Result | Evidence |
|---|---|---|
| 1. Complete compact rows | **PASS** | 48 full rows = 48 planned cell ids (exact plan match from the frozen planner), 48 compact rows, 48 unique compact keys, compact keys = full keys one to one, 0 bad rows. All required fields present; `supported_raw` is a bool for EX-M and null for E1; endings: EX-M 24 answer; E1 22 answer + 2 `no_answer` (bonsai); 0 infrastructure. |
| 2. Independent rescoring | **PASS, 0 disagreements** | All 48 traces copied with the dev task id and rescored through the dev path (`run_exam.episode_row` -> `exam_arms.score_both` -> scorer v2.0; `queue_core.ending_class`). Compared: supported, supported_raw, name_fix_changed, exact, requests, input/output tokens, native_ops, ending. Limit: both paths use the same `scorer_v2.py` (hash `c6b02716...`), so this checks the row assembly, not the scorer. In the copy I added the field `prompt_sha256` to `episode_start` (the exam worker does not record it; the dev row builder wants it; scoring does not use it). |
| 3. `analyze_primary.py` runs | **PASS** | Exit 0; reports **24 pairs** (read from its JSON, not from the argument). **Do not quote its verdict:** with `--planned-pairs 24` it prints "FINAL ... PASS" for 24 pairs of dev tasks (`analysis_primary.md`); that is an exercise of the script, not a result. |
| 4. Hard kill and resume | **PASS (two kills, one design finding)** | Kill 1 (10:02, runner process group gone; the worker survived, finished its episode and removed its own fixtures): the restart killed the orphan worker; the cell had no row and was re-run. Kill 2 (about 10:08, runner, worker and its process group SIGKILLed with 14 fixture processes up): the restart logged `killed_orphans fixture_processes: 14`, the next episode started with a clean domain. Final: `merge-check` 0 duplicates, 0 outside spec, 0 missing in the subset (96 not-run cells are the unrun part of the 144 plan), all 48 done, ROS domain empty, no fixture or worker process left. **Design finding:** the stand-in preflight refused to restart while leftovers existed (strict variant, log `kill_test_A_strict_preflight_restart.log`), because the frozen `queue_core.run()` calls `load_spec` (which calls `backend().preflight()`) before its own orphan cleanup. Codex (CODEX_REVIEW section 2) read the real runtime: its `preflight()` checks hashes only and does not inspect the ROS graph, so this refusal does not apply there; I could not check that. For the second restart the stand-in preflight was relaxed (`ROSA_REHEARSAL_LAX_PREFLIGHT=1`), which changed the stand-in file and its manifest hash. |
| 5. Wiring sanity | **FLAG: gpt-oss (drop); no ratio flag** | EX-M supported out of 6 vs dev FULL reference: lfm3 6 vs 6.0, qwen3.5 6 vs 6.0, **gpt-oss 5 vs 6.0 (drop 1 cell = 16.7 points, above the 15-point threshold)**, bonsai 5 vs 5.0. Token ratio EX-M / E1 (24 pairs): lfm3 0.36, qwen3.5 0.36, gpt-oss 0.50, bonsai 0.38 (dev 0.42 / 0.33 / 0.38 / 0.25); all below 0.80. **Correction of my own amendment text:** Amendment 1 said "2 or more cells below"; 1 of 6 is 16.7 points, which exceeds 15, so the numeric rule flags 1 cell. I applied the numeric rule and report the flag. |
| 6. No write calls reach ROS | **PASS** | 48 traces scanned, 0 `ros param set` / `service call` / `topic pub` in any `ros_start`. The 16 scripted fixture changes (2 change tasks x 8 cells) are the fixture's own and are outside the agent's tools, as expected. |

## The rule 5 flag, investigated
gpt-oss missed `e1h_abs_1` with EX-M (and also with E1; the dev arms got it right in all 6 dev runs of gpt-oss: replA2 seeds 3-4, partA seeds 1-2, ablation seed 1, fairness E1 seeds 1-2). The task asks about `/ember/mistral`; the fixture has `/e1h/ember/mistral`. The EX-M trace: `ros2_node_list` with pattern `ember/mistral`, then `ros2_param_get`, answer `running: true`. Dev seed 1: pattern `/ember/mistral` (no match), then answer `running: false`.
**Wiring test I added (not one of the 6 rules):** `first_request_check.py` compares the first model request (messages, tool schemas, options) of every one of the 48 rehearsal cells with the dev seed-1 trace of the same task, model and arm: **48 of 48 identical**. So the model received exactly the same prompt, menu and settings on both paths; the different first tool call is a difference in the model's sampling. The cause is not established (candidates, unverified: GPU/Ollama nondeterminism, or Ollama 0.40.17 in the rehearsal vs 0.40.16 in the dev runs). One cell of 6 on one seed is within what can happen without a bug. Not a claim about method quality.

## Every difference found (Part A and the run)
1. Arm-name log label (`FULL` / `NAMEFIX` / `M`): log only. 2. Dev NAMEFIX arm writes a shadow-gate event `gate_shadow` that EX-M does not: log only. 3. EX-M vs dev FULL: name-fix events and rewrite, intended. 4. Worker passes `{id, request}` only and records no `prompt_sha256`/floor in `episode_start` (rule 2 needed a placeholder). 5. Fixtures started and reset per episode instead of per block. 6. Stand-in preflight strictness (above). 7. `PARITY.md` had labelling errors (tool counts 51 registered / 13 offered; probe counts) found by Codex and corrected. Full list: [PARITY.md](PARITY.md).

## What I could not check
- The real custodian pool/manifest binding, fixture runtime (startup, reset, teardown, the read-trigger change on held-out tasks), temporal scorer and held-out scoring adapter. Codex's planned real-runtime validation (CODEX_REVIEW section 4) is the remaining gate; it needs this laptop.
- The name-fix rewrite path on live traces: the subset has only `e1h` tasks; `name_fix_changed` was false in all 48 rows. The path is covered only by the static sample test (PARITY.md).
- Stage3 and name-fix environments, the other 6 systems, seeds 2-3, the 3 extra models, Forge and MetaTool.
- Exam-time behaviour of the real launcher after a crash between the full-row and compact-row writes (Codex's crash window, not provoked here).
- Why gpt-oss diverged (above).

## Timing (no scores; episodes started after 10:20, kill-test period excluded; 41 of 48 cells)
Minutes per cell (`wall_seconds`, whole episode including fixture start, oracle reads and teardown):
| Model | EX-M | E1 | model mean |
|---|---|---|---|
| lfm3:1.7b | 2.22 (2 cells) | 2.31 (3 cells) | 2.27 |
| qwen3.5:9b | 2.58 (6) | 2.64 (6) | 2.61 |
| gpt-oss:20b | 2.35 (6) | 2.31 (6) | 2.33 |
| bonsai-2:4b | 2.26 (6) | 2.23 (6) | 2.25 |
| **system mean** | 2.38 (20) | 2.38 (21) | |
The queue adds about 0.22 minute per cell between episodes (rows 2.60 minutes apart on average). Time is almost the same for every model and both systems: it is dominated by a roughly fixed per-episode cost (starting 14 fixture nodes, a 6-second wait, readiness and two oracle reads, a daemon restart), not by the model. That fixed cost belongs to my stand-in runtime; the real runtime's may differ, so these are upper-level planning numbers, not predictions.
Projection at 2.6 minutes per cell (measured per model and system, plus overhead; e1h tasks only):
- **Stage 1 tier 1 (1,824 cells): about 78 hours (3.3 days).**
- Tier 2 (S0, MT; priced like E1) 79 h, tier 3 (ablations) 117 h, tier 4 (extra models, priced at the core mean because they were not measured) 59 h: **full queue 7,752 cells about 333 hours (13.9 days)**, F excluded (912 more cells).
- The earlier planning figure was 20-25 hours for tier 1; this measurement is about 3 times higher. Held-out tasks may be longer than the e1h dev tasks (more tool calls), which would raise it further. The lab at the dev speed ratio (0.2-0.6) would be faster. Script: `timing.py`.

## Open search (unfiltered)
- `analyze_primary.py` prints "FINAL ... PASS: claim supported" for any 24-pair file when `--planned-pairs 24` is given; a risk of quoting it by mistake (point for rev 2 and the interim-look rule).
- bonsai E1: 2 `no_answer` of 6 and 1 of 6 supported, vs EX-M 5 of 6 (same tasks, same seed): dev-like pattern (E1 token-heavy for the smallest model); not interpreted.
- lfm3 has only 5 cells after the cutoff because most of its block ran before 10:20.
- The tmux server was `kill -9`-ed in kill test 1 by mistake of target (pgrep matched the tmux command line); it still counts as a hard kill of the runner (the runner died with its terminal) but it was not a clean "runner only" kill; kill 2 targeted the python processes directly.
- `git add` of the study folder committed Codex's untracked `CODEX_REVIEW.md` (commit 33ab668) by accident; content untouched.
- The stand-in `sitecustomize.py` redirect worked in worker subprocesses through `PYTHONPATH`; the real run will not have it, so a real run has no such layer.
- Ollama version during the rehearsal: 0.40.17 (frozen value); `version_guard` tested separately ([OLLAMA_AUTOUPDATE.md](OLLAMA_AUTOUPDATE.md)); the auto-update switch is still ON (owner click pending).

## Files (all in this folder)
`RULES.md`, `PARITY.md`, `parity_capture.py/.json`, `check_rules.py`, `rules_result.json`, `first_request_check.py`, `timing.py`, `analysis_primary.md/.json`, `compact_rows.jsonl`, `setup_rehearsal.py`, `fixtures_dev.py`, `sitecustomize.py`, `env.sh`, `idmap.json`, `rehearsal_spec.json`, `test_version_guard.py`, `OLLAMA_AUTOUPDATE.md`, `REV2_FREEZE_DRAFT.md` (draft, not applied), `CODEX_REVIEW.md` (Codex).
