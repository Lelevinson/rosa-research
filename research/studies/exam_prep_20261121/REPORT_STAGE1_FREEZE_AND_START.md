# Stage 1 freeze and laptop start (2026-11-21, 17:50-18:05 Asia/Taipei): report

Run by Claude Code (Sonnet 5.5) from `Claude outputs/2026-11-22_CC_STAGE1_FREEZE.md`, on the owner's authorisation to freeze Stage 1 and start the laptop queue. Counts only were read from the queue status; no held-out trace, row, log or task id was read.

## Top box
- **Frozen: yes.** Record `final_exam_draft_20261118/freeze_package_20261121/FREEZE.json` (committed a608d0a, git head of the frozen files 43e8787, `frozen_at` 2026-11-21T09:52:46Z = 17:52 Taipei). **SHA-256 of FREEZE.json: `40b26b0fc0ca391294541553c912225e612f94a4a22b2c567321375a0e8b974b`.** It hashes 43 files (final specs, analysis script, custodian MANIFEST and bridge, arms, harness, runners, scorer v2.0 `c6b02716...`, queue code, `uv.lock`) plus the digests of the 7 models and the Forge environment.
- **Master seed 20261122; seeds 1, 2, 3 per cell.** Cells per tier in `exam_spec_stage1.json`: tier 1 (EX-M, E1) **1,824**; tier 2 (S0, MT) **1,824**; tier 3 (ablations) **2,736**; tier 4 (extra models, EX-M and E1) **1,368**; total **7,752**. System F: **912** cells in its own spec `exam_spec_stage1_F.json` (total 8,664 as approved).
- **The run is NOT running.** The laptop queue started at **2026-11-21 17:52:55** and **crashed after its first episode** because of a plumbing defect in the custodian bridge (below). One held-out cell has a full result row; no further cell ran. Nothing is being monitored. I stopped and did not change any frozen file.

## Prerequisites (item 1), all passed before the freeze
Codex's `supported_raw` and `name_fix_changed` in bridge rows: custodian bridge tests (5) pass, including the replay on two public dev traces (unchanged and flipping case), and the frozen analyzer reads those compact replay rows ([REPORT_SUPPORTED_RAW.md](../custodian_stage1_20261121/REPORT_SUPPORTED_RAW.md)). Analysis script hash unchanged (`analyze_primary.sha256` OK). Queue suite (45 tests), arm tests (17), analysis tests (14) and the new spec test pass. F: not adapted to a held-out adapter yet, so **F stays out of the run**: the custodian launcher refuses any spec that contains a system without a held-out adapter, so F is in a separate frozen spec (a change of file layout only; the cell set is unchanged). It does not block tier 1.

## What happened at the start
1. The first start (tmux, `start_stage1_laptop.sh`, 17:52:55) ended within about two minutes with the status `crashed`; the monitor sent a **crash ntfy message at 17:55:01** (a daily summary message at 17:53:27 was also sent).
2. I restarted the runner once with only stderr captured (stdout discarded) to find the cause. It showed `running`, 1 of 7,752 done; seven minutes later its status was stale and stderr held a traceback. The traceback is a queue/bridge error, not a held-out content: in `recover()` at start-up, `queue_core.compact()` raised **`KeyError: 'model'`** for the first episode's row.
3. Cause: the bridge's result row carries the opaque id, scores and costs but **not `model` and `seed`**; `Results.add` merges only system, pool, tier, pair, machine, ..., and `queue_core.compact()` reads `row["model"]` and `row["seed"]`. The bridge's tests did not run a row through `compact()`. In the first run the full row was written (so the cell counts as done) and `compact()` then raised, so the runner died after the first episode; the restart's `recover` hit the same error. **The one completed episode has a full row and no compact row.**

## What is needed (decision for the owner and Codex; I made no change)
- **Fix (plumbing only):** in `queue_bridge.py`, add `model` and `seed` (available in `attempt["cell"]`) to the row returned by `episode_row`/`queue_row`, add a test that passes a bridge row through `queue_core.compact()`, and write the one missing compact row for the completed cell (or let `recover` rebuild it). The scorer, prompts, tasks, arms, specs and success criteria are not touched.
- **This is a change after the first held-out request.** The protocol says no task, scenario, scorer rule, prompt or schema change after the first held-out request, and a legitimate revision is written, hashed and reported separately. A row-plumbing fix is not one of the listed kinds, but `queue_bridge.py` is in the frozen file list, so the freeze record must be rewritten as a dated revision (new `FREEZE.json` hash, this report as its reason). **The one completed cell is not re-run** (it made a model request) and its result stays.
- Restart with the same run name `stage1_laptop_20261122` (the queue skips logged cells) via `start_stage1_laptop.sh` after the revision; the script verifies `FREEZE.json` and will refuse until it is re-recorded.

## Other findings
- **Ollama version drift:** the laptop's Ollama reports **0.40.17** (the dev studies and the lab used 0.40.16); model digests are unchanged. Recorded in `FREEZE.json` (`ollama_version`).
- **Monitor and status:** the ordinary monitor and exit hook look in `research/_artifacts/exam`, while the bridge keeps the queue folder in custody; `exam_queue/monitor_stage1.py` points both at the custody queue folder, and `exam_queue/status_stage1.py` prints a whitelist of status counts only (not in the frozen list).
- **Unknown:** why the first start's own stderr is lost (the tmux pane closed); it is presumed to be the same error because the first run's log state is consistent with it (one full row, no compact row).
- **ETA** (planning figures from the dev episode times, not measurements): the first 1,824 cells of tier 1 take about 20-25 hours on the laptop; all 7,752 cells about 4-5 days; the exam on the lab would be faster (dev ratio 0.2-0.6).

## Open search (unfiltered)
- Three tmux sessions (`exam-stage1_laptop_20261122`, `exam-diag`, `exam-monitor`, plus `gpusample`) were started and are now all killed; no episode process, fixture process or loaded model remains.
- The second start ran with stdout discarded and without the exit hook, so the monitor could not mark that crash; the stale-heartbeat rule would have reported it.
- Both starts wrote to the custodian queue folder; I did not list or read it.
- The bridge compact row also needs `supported_raw`/`name_fix_changed` (it has them); a row without `model` also means the interim analysis cannot run until the fix.
