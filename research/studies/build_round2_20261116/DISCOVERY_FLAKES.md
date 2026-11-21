# Node-discovery flakes: reproduction, scope and one proposed fix (2026-11-16)

Written for: the project owner (round 2 is paused). No model episode was run; CPU/ROS only. One Ollama model (gpt-oss:20b) generated text in the background only to simulate load. The fix in sections 1-5 was a proposal; **sections 6-9 (added after the owner approved it in principle) answer the owner's three questions and record that it is applied by PROTOCOL.md amendment 4.**

| | |
|---|---|
| **Result** | The flakes reproduce without any model: the oracle's node-list read (`ros2 node list --no-daemon --spin-time 4`) missed fixture nodes in 6 of 212 polls (2.8%). The same read with `--spin-time 10` missed 0 of 103, and the daemon read (`ros2 node list`, what the agent's tool runs) missed 0 of 1,594. In the real oracle, interleaved under load, the current version failed 2 of 20 reads and the daemon-read version 0 of 20. |
| **What it changes** | The flakes are a property of the no-daemon oracle read, not of the fixture, the sweep or the model. The agent's own `ros2 node list`, `node info` and `topic info` calls were never incomplete in 1,212 / 3,035 / 1,262 recorded calls, so models did not see incomplete lists during the flakes. A one-line change in the oracle (read the node list through a freshly restarted daemon) removed the flakes in the reproduction. |
| **What it cannot show** | Why the 4-second no-daemon spin sometimes hears only a few of 19 nodes (cause not established; hypothesis only). 0 of 103 for `--spin-time 10` is weak evidence (p about 0.06 if the true rate were 2.8%), so I do not propose it. The verification has 20 reads per variant: 0 of 20 is consistent with a small residual rate. Power/idle effects were checked only while the owner was away. |
| **Does it touch what the model sees?** | No. The oracle runs between episodes; the agent's tools are unchanged and already use the daemon. The only side effect is that the daemon starts (and stays warm) a few minutes earlier in a session. Same for both arms (they share each session). |
| **Cost** | Reproduction about 95 minutes, verification about 60 minutes of CPU/ROS time; no model episodes. |

## 1. Reproduction (item 1)
Script `discovery_repro.py` (this folder); raw output `research/_artifacts/runs/discovery_20261116/repro_20261116T093206Z/` (`polls.jsonl`, `windows_power.jsonl`, `conditions.jsonl`; not in the mirror). Stage 3 fixture (19 nodes, `run_pilot.session`'s commands), ROS domain 220, `ROS_LOCALHOST_ONLY=1`, same as the sessions. Each condition polled for 600 s, one second pause between polls; "missing" = a declared fixture node absent from the returned list. A poll also records whether every fixture process was alive (it always was: no node died; every miss is a discovery miss).

| mode (command) | background model | polls | polls with missing nodes | nodes missing per event |
|---|---|---:|---:|---|
| oracle: `ros2 node list --no-daemon --spin-time 4` | off | 109 | **2** | 2, 1 |
| oracle | on | 103 | **4** | 8, 9, 6, 16 |
| `--no-daemon --spin-time 10` | off | 52 | 0 | |
| `--no-daemon --spin-time 10` | on | 51 | 0 | |
| daemon restarted (`ros2 daemon stop/start`), then `ros2 node list` | off | 437 | 0 | |
| daemon restarted | on | 362 | 0 | |
| daemon left running (aged), `ros2 node list` | off | 434 | 0 | |
| daemon left running | on | 361 | 0 | |

Reading: (a) misses occur with no load (2 of 109), so the model is not required; load makes them look larger (4 of 103; events missing 6 to 16 of 19 nodes against 1 to 2 without load), but the counts are too small to claim a load effect. (b) The misses are not timeouts: the missed polls took 4.5 to 4.9 s, like the good ones; the CLI finished its 4-second window having heard only part of the graph. (c) The daemon, which is one long-lived participant that already knows all peers, never missed in 1,594 polls, fresh or aged, with or without load. Condition order: the load level order inside each pair was randomized (seeded); the modes ran in the fixed order oracle, spin 10, daemon fresh, daemon aged, so mode is confounded with time of day (about 85 minutes in total). The Windows state was constant over the whole run (section 4), so I see no time-of-day mechanism, but I did not test one.

## 2. Does the agent go through the same path? (item 2)
- **Code.** ROSA's `ros2_node_list` calls `execute_ros_command("ros2 node list")` (`src/rosa/tools/ros2.py`), run through the study's `guarded_native` (`menu_run_study.py`) as `subprocess.run(["ros2","node","list"])`: **daemon mode**, no `--no-daemon`, 15 s timeout. `ros2 node info` and `ros2 topic info --verbose` are run the same way. The oracle (`stage3_fixture.oracle`, `e1h_fixture`) uses `--no-daemon --spin-time 4` for the node list. So the failing read and the agent's read are different discovery paths.
- **Recorded traces** (`discovery_history.py`, `discovery_history2.py`; `discovery_history.json`): across every trace of the pilot, round 1, the Forge baseline, the stock ROSA run, the Stage 1-3 studies and round 2, the agent's successful `ros2 node list` calls were **1,212, with 0 incomplete** (some but not all fixture nodes listed); `ros2 node info` on a stage 3 node **3,035 calls, 0 missing a declared topic or service**; `ros2 topic info --verbose` **1,262 calls, 0 with a wrong publisher/subscriber set**. In the sessions that stopped on an oracle failure the agent's lists were complete too (round 2 qwen3.5 stage3 rerun: 42 node lists, 0 incomplete). So there is no sign that models saw incomplete graphs during flakes. Limit: the check can only see a miss that leaves a declared fixture node out; it cannot see an extra stale node. Other agent tools (`ros2 param get`, `service list`) were not checked.

## 3. History of the oracle failures (item 4, part 1) and the proposed fix (item 3)
Final oracle files over all studies: 194 reads, 7 with mismatches (3.6%): 6 "node not listed" and 1 topic publisher/subscriber mismatch (round 1, "before"). Round 2 had 3 failing of 21 final reads, plus the two first-try failures that the retry rescued. All involve the no-daemon node-list read except possibly the topic case (`topic info --verbose` is also read by the oracle; the agent's own 1,262 recorded reads were all correct, so I do not claim anything about that one).

| file time (+08) | study | label | what failed |
|---|---|---|---|
| 11-14 00:42 | Stage 3b | after | juniper, mantle not listed |
| 11-15 20:02 | round 1 lfm3 stage3 | before | topic upland_t publishers/subscribers differ |
| 11-15 22:13 | round 1 qwen3.5 e1h | after | marlin, dahlia not listed |
| 11-16 02:28 | stock ROSA S0 bonsai stage3 | after | jetty not listed |
| 11-16 08:17 | round 2 smoke bonsai stage3 | after | juniper not listed |
| 11-16 10:12 | round 2 qwen3.5 stage3 | after-012 | beacon, dune, lumen not listed |
| 11-16 16:00 | round 2 qwen3.5 stage3 rerun | after-048 | lattice, beacon, juniper (retry: 4 nodes) |
(plus round 2 lfm3 stage3 "after", first try, 09:42, rescued by the retry.)

**Proposed fix (one change):** make the oracle's node-list read go through a daemon that was restarted at the start of the session: before the first oracle read run `ros2 daemon stop; ros2 daemon start`, and read `ros2 node list` without `--no-daemon` (the same command the agent's tool runs). Everything else in the oracle (parameter reads, topic info, node info, the expected values) stays as it is. Implementation without editing the frozen fixture files: in the session process, replace `stage3_fixture.cli` / `e1h_fixture.cli` by a wrapper that rewrites exactly the call `("node","list","--no-daemon",...)` to `("node","list")` (the same wrapper style as `OracleWithRetry`), and restart the daemon once at session start.
- **Evidence it removes the flakes:** reproduction 0 of 1,594 daemon polls against 6 of 212 for the oracle command; real-oracle verification (`discovery_verify.py`, `.../verify_20261116T105625Z/verify.jsonl`): 20 reads per variant, alternating order, Ollama generating throughout, same live fixture: current oracle **2 of 20 failed** (anvil, xenon; elm, quill, lumen), daemon-read oracle **0 of 20**. Mean read time 85.9 s vs 83.4 s.
- **Caveat the daemon introduces:** the daemon can keep a node in its list for a short time after the node died, so a dead node could be reported as listed. `run_pilot.session` already checks before every cell that no fixture process has exited, so a dead fixture is caught independently. The cleanup checks (`assert_domain_empty`, `verify_empty`, `wait_for`) keep their no-daemon reads (they look for extra nodes, where a miss is harmless); I did not change them.
- **Applies equally to all arms:** the oracle is a session-level check between episodes; both arms of a model/environment share the session, the fixture, the daemon and the oracle. The agent's tools, prompts, schemas, the model's inputs and every study rule are unchanged. It would need a dated protocol amendment before use; I have not made one and have not applied it.
- **Not done / not claimed:** `--spin-time 10` alone (0 of 103) is not proposed because the evidence is weak. The retries added in amendments 1 and 2 reduce but do not remove the problem: the after-048 failure was two failures in a row (2 nodes, then 4), so misses are not independent between reads.

## 4. Windows power state and whether flakes follow idleness (item 4)
Sampled every 60 s during the reproduction by a PowerShell loop (`windows_power.jsonl`, 81 samples, 17:32 to 18:55 +08 on 2026-11-16):
- Power plan **Performance**; **on AC** (Win32_Battery BatteryStatus 2) all 81 samples, charge 94%.
- CPU (AMD Ryzen 5 7535HS): current clock 3,301 MHz = max in every sample; "% Processor Performance" 104 to 127 (no throttling). Display and sleep timeouts on AC are **0 = never** (powercfg), on battery 3600 s; no sleep or wake events in the System log for the previous 14 hours.
- **Screen:** not directly observable from here. With AC power and a "never" display timeout it should have stayed on; I did not verify the panel.
- **Idle time** (GetLastInputInfo): 36,834 s at the start of the run and 41,799 s at the end, i.e. no keyboard or mouse input since about 07:18 on 2026-11-16. So the whole reproduction ran while the owner was away, and flakes (6 of 212 oracle-mode polls) occurred anyway, including with no load, at full clock speed, on AC. **No evidence that screen-off or idle throttling causes them; no test with the owner present** (that would need the owner at the keyboard, which I did not arrange), so "present vs away" is untested, not excluded.
- Earlier failures while the owner was away: the idle counter only reaches back to about 07:18 on 11-16. **Verified away:** the four round 2 failures (08:17, 09:42, 10:12, 16:00) happened 1 to 9 hours after the last input. **Inferred, not verified:** 02:28 (the stock-ROSA run was the overnight job). **Unknown:** 11-14 00:42, 11-15 20:02 and 22:13 (no record of whether the owner was present). Windows keeps no sleep/lock log for those hours (the Security and Winlogon logs are empty or unreadable without admin rights). Since the same reads succeeded most of the time while the owner was away (3 of 21 failing in round 2), being away is neither necessary nor sufficient.

## 5. Files
`discovery_repro.py` (reproduction), `discovery_verify.py` (real-oracle A/B), `discovery_history.py` and `discovery_history2.py` with `discovery_history.json` (history), raw runs under `research/_artifacts/runs/discovery_20261116/` (not mirrored). Round 2 state: paused; INFRA_EXCLUDED.json lists the 60 excluded qwen3.5 stage3 episodes (12 + 48); the 88 lfm3:1.7b episodes stay; PROTOCOL.md amendments 1-3.

## 6. Staleness: how long does the daemon still list a dead node? (follow-up question 1)
Script `discovery_staleness.py`; raw `research/_artifacts/runs/discovery_20261116/staleness_*/staleness.jsonl` (not mirrored). Stage 3 fixture, daemon restarted, no model load. Six trials, alternating a crash (SIGKILL) and a clean exit (SIGINT), polling the daemon's `ros2 node list` every 0.5 s.

| node | how it died | daemon stopped listing it after | `ros2 param get` on it while still listed | no-daemon spin-4 list still shows it |
|---|---|---:|---|---|
| quill | SIGKILL | 17.9 s | rc 1 ("Wait for service timed out ... /plant32/quill") | no |
| lumen | SIGKILL | 19.5 s | rc 1 (same) | no |
| yarrow | SIGKILL | 18.5 s | rc 1 (same) | no |
| juniper, yonder, anvil | SIGINT | 0.5 to 0.6 s | not needed (already gone) | no |

- **Window: about 18 to 20 s after a crash** (3 of 3), about 0.5 s after a clean exit (3 of 3). The no-daemon read never listed a dead node. n = 3 per kind; I did not test under load.
- **Does any oracle check depend on a node being absent within that window? No.** The oracle (`stage3_fixture.oracle`, `e1h_fixture.oracle`) asks only for presence: "node not listed" for each declared node. A node that crashed less than about 20 s before the node-list read would show up as listed, but the same oracle then reads a parameter from every node (all 19 stage 3 nodes and all 14 e1h nodes declare at least one parameter), and that read fails for a dead node (rc 1 above), which is reported as a mismatch. `run_pilot.session` also stops before the next episode if any fixture process has exited. The absence checks of the session (`assert_domain_empty` at the start, `verify_empty` at the end, `wait_for` readiness) call `run_stage1.node_list` (`--no-daemon --spin-time 3`) directly, not the fixture's `cli`, so amendment 4 does not touch them. Limit: a node that dies after its own parameter read but before the end of the oracle would be missed by both the old and the new oracle (as before).

## 7. The oracle reads of the 88 valid lfm3 episodes (follow-up question 2)
Round 2's run folder, sessions `lfm3_1.7b-stage3` (64 episodes) and `lfm3_1.7b-e1h` (24 episodes): 10 oracle reads (7 + 3), each read from its `oracle.json`, `oracle_failures.jsonl` and `setup.jsonl`.
- **Needed the retry: 1 of 10.** `lfm3_1.7b-stage3` "after": the first try listed 5 nodes as missing (gantry, quill, zephyr, lumen, yonder), the retry 5 s later was clean. **Returned fewer nodes on the final read: 0 of 10** (any missing declared node is a mismatch, so "fewer nodes" and "mismatch" are the same event; extra nodes are not checked).
- Other signs: in one e1h read (`before`) one parameter read needed one of the fixture's own CLI retries (non-zero exit, unrelated to the node list). No `oracle_cli_timeout` in either session.
- **The raw node list was not logged** in these reads (only the mismatches), so a list that was merely smaller than usual but still complete cannot be seen; this is why amendment 4 adds the raw log.
- **Does the oracle feed ground truth to the scorer? No.** `score_round2.py`, `run_round2.episode_row` and `analyze_round2.py` never read the oracle files; scoring uses the episode trace and the task's own expected value. The oracle only gates fixture health: a mismatch stops the session (`run_pilot.session`), and the episodes since the previous clean oracle read are then excluded by the infrastructure rule. A flake therefore cannot change a score; it can only stop a session and discard episodes.

## 8. Did the "2 of 20 as it is today" reads include the 5 s retry? (follow-up question 3)
**No.** `discovery_verify.py` calls the fixture's `oracle()` directly, once per variant, without `OracleWithRetry`. So the 2 of 20 are first-try reads (about 10% per read, with the model generating in the background). Why one retry does not simply cut the miss rate to its square:
1. **Inside the fixture, `cli()` retries only a non-zero exit code.** A node list that exits 0 with only some of the nodes is returned as it is, so there is no retry for the failure that matters.
2. **The 5 s retry is a whole second oracle read.** If the misses were independent at about 3% to 10%, it would leave about 0.1% to 1%. In my polling reproduction the six missed polls were all isolated (the polls before and after each were complete), so a retry five seconds later would have caught all six.
3. **In the real sessions the numbers are worse than that, and the retry did not absorb them.** Counting every oracle read of round 2 that has a file (17: 3 lfm3 e1h, 7 lfm3 stage3, 2 + 5 qwen3.5 stage3): the first try failed in 3 (about 18%, a wide interval) against 2.8% per poll in the reproduction. Of the reads that had the retry in force, one first-try failure was rescued (lfm3 stage3 "after") and one failed again (qwen3.5 stage3 `after-048`: 2 nodes missing, then 4 others five seconds later). The `after-012` failure had no retry (amendment 2 came after it). So the retry rescued 1 of 2 retried failures; two reads are too few to say whether the misses are correlated within a session. **Cause not established; hypothesis only:** the per-read miss rate in a real session (after dozens of episodes, with agent processes and the model on the same machine) is higher than in the quiet polling reproduction, so even an independent retry leaves a visible residue, and a second miss close in time is possible when the conditions that caused the first one still hold.
4. This is why the proposal removes the cause (the short-lived no-daemon spin) instead of adding more retries.

## 9. Applied as amendment 4 (2026-11-16, after the owner's approval in principle)
`PROTOCOL.md` amendment 4 and `run_round2.OracleWithRetry` (the wrapper): (a) restart the daemon once per session before the first oracle read, wait 10 s; (b) the oracle's one call `ros2 node list --no-daemon --spin-time 4` is read as `ros2 node list` through that daemon; the 5 s retry of amendments 1 and 2 stays; (c) the raw node list of every such read (both attempts) is written to `<session>/oracle-<label>/node_list_raw.jsonl` with the time, duration, number of declared nodes found, and the fixture's own retry count. Checks: 15 unit tests pass (new test: only the node-list call changes, both attempts are logged, one daemon restart per session); the real wrapper around the real stage 3 oracle ran three consecutive reads on a live fixture with no model: all clean, 19 of 19 nodes listed each time (`discovery_amendment4_check.py`, raw `amend4_check_*`). That is a function check, not evidence of a rate: with 3 reads it cannot show that the flake rate is zero; the earlier 0 of 20 and 0 of 1,594 are the evidence, and the raw logs of the resumed run will add more.

