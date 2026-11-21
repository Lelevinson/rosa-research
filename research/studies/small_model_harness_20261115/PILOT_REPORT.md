# PILOT_REPORT: small-model harness pilot (descriptive only)

Study `small_model_harness_20261115`, 2026-11-14 to 2026-11-15, branch `research/capability-discovery-20261110`. Decision record: [DECISION_RECORD.md](DECISION_RECORD.md). Full generated tables, including every per-task row: [PILOT_TABLES.md](PILOT_TABLES.md). Episode-level data: `RESULTS_LOG.jsonl` (traces stay in `research/_artifacts/runs/small_model_harness_20261115/`, not in Git; log rows hold path and sha256). Chronology, revisions and failures: [PILOT_LOG.md](PILOT_LOG.md).

**This is a pilot of a built method, not a confirmatory test. Every number below is a count in a small synthetic fixture. No significance is claimed and no claim goes beyond what was run.**

## What was run
- **4 models, 576 planned episodes, 576 valid episodes completed.** Models: lfm3:1.7b, qwen3.5:9b, gpt-oss:20b, and **bonsai-2:4b, which was added** by my judgment after Step A: both of its Step A failures were stock-executor aborts (schema-validation errors on write tools, after it had collected the facts), which is the harness-level failure class the study asks about, and at 4B with Q2_0 quantisation it extends the size range downwards. **bonsai-2:4b is Qwen-family** (`/api/show` architecture `qwen35`, the same as qwen3.5:9b, ornith-1.5 and mimo-v2.6), so the pilot has three independent architectures (lfm3, qwen35 family, gpt-oss), not four. ministral-3:8b also qualified (one stock abort) and was not added.
- Per model: 144 episodes = tasks u3, p3, h4, v2 (Stage 3 fixture) and the 6 E1h harm tasks (frozen, hash in `E1H_FROZEN.json`), arms A1, C1, M0, C1+FN, C1+H2, C1+H1e, C1+H7 on all 10 tasks, C1+H1n on the 2 changing-parameter tasks; seeds 1 and 2; temperature 0.7; num_ctx 65536 (verified from `/api/ps`), num_predict 4096, max iterations 40; ROS domain 220. Order shuffled within each (model, environment) session with seeds derived from master seed 20261116. Scoring: strict Stage 3 support rule unchanged; the answer is the `final_answer` object when present, otherwise the last complete JSON object (one legacy rule for every arm).
- Not run: S0 (stock ROSA prompt) is built (`run_pilot.py`, `--arm S0`) but is not in the section 5 pilot arm list, so it has no pilot episodes. Held-out E2 tasks were not opened.
- Running time about 8.8 h of the 10 h cap (the pause is not counted).

## Protocol revisions and events (all in PILOT_LOG.md; originals kept in the log)
1. **12 lfm3 C1+H1e E1h episodes** crashed before any model request (my bug in `EpisodeHook.start`); excluded as infrastructure failures, rerun, hook fixed (`E1H_FROZEN.json` revisions).
2. **20 lfm3 C1+H7 episodes (version 1)** ran without telling the model the valid tool names while only `submit_plan` was offered; superseded and rerun with the revised arm. Version 1 result, reported separately: 5/20 supported, 15 invalid plans, 0 accepted plans, 92 requests.
3. One oracle read hit a CLI timeout before any episode (retry added); gpt-oss:20b failed on the host in Step A (CUDA runner fault) and later worked unchanged.
4. Episode `bonsai-2_4b-e1h/079-...` was killed by the owner's pause and `081-...` never finished; both excluded, cells rerun.
All tables use the 576 valid episodes (excluded: 12 + 20 + 2, still in the log).

## Per model and arm (supported-complete, cost totals over the assigned episodes)
| model | arm | episodes | supported-complete | LLM requests (total) | input tokens | output tokens | native ops | aborted episodes |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| bonsai-2:4b | A1 | 20 | 6 | 197 | 1391619 | 17828 | 191 | 5 |
| bonsai-2:4b | C1 | 20 | 13 | 189 | 726761 | 19728 | 198 | 0 |
| bonsai-2:4b | M0 | 20 | 13 | 164 | 592924 | 13721 | 188 | 0 |
| bonsai-2:4b | C1+FN | 20 | 13 | 179 | 715099 | 26347 | 253 | 0 |
| bonsai-2:4b | C1+H2 | 20 | 13 | 201 | 824245 | 23352 | 232 | 0 |
| bonsai-2:4b | C1+H1e | 20 | 13 | 206 | 951989 | 32914 | 215 | 0 |
| bonsai-2:4b | C1+H1n | 4 | 0 | 55 | 174481 | 2096 | 15 | 0 |
| bonsai-2:4b | C1+H7 | 20 | 6 | 326 | 1451534 | 35299 | 236 | 2 |
| gpt-oss:20b | A1 | 20 | 6 | 54 | 207182 | 10631 | 34 | 11 |
| gpt-oss:20b | C1 | 20 | 15 | 105 | 203554 | 20020 | 116 | 0 |
| gpt-oss:20b | M0 | 20 | 17 | 121 | 258790 | 21782 | 92 | 2 |
| gpt-oss:20b | C1+FN | 20 | 14 | 97 | 176373 | 16594 | 106 | 0 |
| gpt-oss:20b | C1+H2 | 20 | 17 | 98 | 182164 | 17578 | 107 | 0 |
| gpt-oss:20b | C1+H1e | 20 | 10 | 95 | 173308 | 17813 | 106 | 1 |
| gpt-oss:20b | C1+H1n | 4 | 0 | 16 | 23724 | 2775 | 8 | 0 |
| gpt-oss:20b | C1+H7 | 20 | 10 | 133 | 228757 | 37933 | 54 | 4 |
| lfm3:1.7b | A1 | 20 | 15 | 135 | 1028694 | 61733 | 129 | 2 |
| lfm3:1.7b | C1 | 20 | 17 | 105 | 408791 | 45905 | 122 | 0 |
| lfm3:1.7b | M0 | 20 | 18 | 134 | 713548 | 53384 | 145 | 1 |
| lfm3:1.7b | C1+FN | 20 | 16 | 105 | 443845 | 47846 | 108 | 0 |
| lfm3:1.7b | C1+H2 | 20 | 15 | 98 | 369191 | 39498 | 131 | 1 |
| lfm3:1.7b | C1+H1e | 20 | 18 | 98 | 317035 | 47765 | 99 | 0 |
| lfm3:1.7b | C1+H1n | 4 | 0 | 12 | 24178 | 2634 | 10 | 0 |
| lfm3:1.7b | C1+H7 | 20 | 5 | 237 | 1817668 | 191032 | 106 | 0 |
| qwen3.5:9b | A1 | 20 | 19 | 86 | 554213 | 9523 | 120 | 0 |
| qwen3.5:9b | C1 | 20 | 20 | 87 | 242071 | 9672 | 120 | 0 |
| qwen3.5:9b | M0 | 20 | 19 | 112 | 343516 | 10503 | 131 | 0 |
| qwen3.5:9b | C1+FN | 20 | 20 | 84 | 236086 | 9027 | 112 | 0 |
| qwen3.5:9b | C1+H2 | 20 | 20 | 81 | 224944 | 9341 | 116 | 0 |
| qwen3.5:9b | C1+H1e | 20 | 20 | 83 | 228682 | 9370 | 116 | 0 |
| qwen3.5:9b | C1+H1n | 4 | 0 | 13 | 29037 | 1565 | 8 | 0 |
| qwen3.5:9b | C1+H7 | 20 | 11 | 219 | 618541 | 26029 | 151 | 0 |

Supported-complete by environment:

| model | arm | stage3 tasks (supported/n) | E1h tasks (supported/n) |
|---|---|---:|---:|
| bonsai-2:4b | A1 | 1/8 | 5/12 |
| bonsai-2:4b | C1 | 5/8 | 8/12 |
| bonsai-2:4b | M0 | 5/8 | 8/12 |
| bonsai-2:4b | C1+FN | 4/8 | 9/12 |
| bonsai-2:4b | C1+H2 | 5/8 | 8/12 |
| bonsai-2:4b | C1+H1e | 5/8 | 8/12 |
| bonsai-2:4b | C1+H1n | - | 0/4 |
| bonsai-2:4b | C1+H7 | 2/8 | 4/12 |
| gpt-oss:20b | A1 | 1/8 | 5/12 |
| gpt-oss:20b | C1 | 5/8 | 10/12 |
| gpt-oss:20b | M0 | 6/8 | 11/12 |
| gpt-oss:20b | C1+FN | 6/8 | 8/12 |
| gpt-oss:20b | C1+H2 | 7/8 | 10/12 |
| gpt-oss:20b | C1+H1e | 2/8 | 8/12 |
| gpt-oss:20b | C1+H1n | - | 0/4 |
| gpt-oss:20b | C1+H7 | 2/8 | 8/12 |
| lfm3:1.7b | A1 | 4/8 | 11/12 |
| lfm3:1.7b | C1 | 5/8 | 12/12 |
| lfm3:1.7b | M0 | 6/8 | 12/12 |
| lfm3:1.7b | C1+FN | 5/8 | 11/12 |
| lfm3:1.7b | C1+H2 | 4/8 | 11/12 |
| lfm3:1.7b | C1+H1e | 6/8 | 12/12 |
| lfm3:1.7b | C1+H1n | - | 0/4 |
| lfm3:1.7b | C1+H7 | 3/8 | 2/12 |
| qwen3.5:9b | A1 | 7/8 | 12/12 |
| qwen3.5:9b | C1 | 8/8 | 12/12 |
| qwen3.5:9b | M0 | 8/8 | 11/12 |
| qwen3.5:9b | C1+FN | 8/8 | 12/12 |
| qwen3.5:9b | C1+H2 | 8/8 | 12/12 |
| qwen3.5:9b | C1+H1e | 8/8 | 12/12 |
| qwen3.5:9b | C1+H1n | - | 0/4 |
| qwen3.5:9b | C1+H7 | 3/8 | 8/12 |

## Paired disagreement counts, C1 vs each arm (for the power analysis)
Pairs are the same model, task and seed (20 per model and arm; 4 for H1n). "C1 only" = C1 supported and the arm not; "arm only" = the reverse.

| model | arm vs C1 | pairs | both supported | C1 only (arm worse) | arm only (arm better) | neither |
|---|---|---:|---:|---:|---:|---:|
| bonsai-2:4b | A1 | 20 | 3 | 10 | 3 | 4 |
| bonsai-2:4b | M0 | 20 | 10 | 3 | 3 | 4 |
| bonsai-2:4b | C1+FN | 20 | 12 | 1 | 1 | 6 |
| bonsai-2:4b | C1+H2 | 20 | 12 | 1 | 1 | 6 |
| bonsai-2:4b | C1+H1e | 20 | 13 | 0 | 0 | 7 |
| bonsai-2:4b | C1+H1n | 4 | 0 | 3 | 0 | 1 |
| bonsai-2:4b | C1+H7 | 20 | 4 | 9 | 2 | 5 |
| gpt-oss:20b | A1 | 20 | 4 | 11 | 2 | 3 |
| gpt-oss:20b | M0 | 20 | 14 | 1 | 3 | 2 |
| gpt-oss:20b | C1+FN | 20 | 13 | 2 | 1 | 4 |
| gpt-oss:20b | C1+H2 | 20 | 14 | 1 | 3 | 2 |
| gpt-oss:20b | C1+H1e | 20 | 9 | 6 | 1 | 4 |
| gpt-oss:20b | C1+H1n | 4 | 0 | 4 | 0 | 0 |
| gpt-oss:20b | C1+H7 | 20 | 8 | 7 | 2 | 3 |
| lfm3:1.7b | A1 | 20 | 15 | 2 | 0 | 3 |
| lfm3:1.7b | M0 | 20 | 17 | 0 | 1 | 2 |
| lfm3:1.7b | C1+FN | 20 | 15 | 2 | 1 | 2 |
| lfm3:1.7b | C1+H2 | 20 | 14 | 3 | 1 | 2 |
| lfm3:1.7b | C1+H1e | 20 | 16 | 1 | 2 | 1 |
| lfm3:1.7b | C1+H1n | 4 | 0 | 4 | 0 | 0 |
| lfm3:1.7b | C1+H7 | 20 | 4 | 13 | 1 | 2 |
| qwen3.5:9b | A1 | 20 | 19 | 1 | 0 | 0 |
| qwen3.5:9b | M0 | 20 | 19 | 1 | 0 | 0 |
| qwen3.5:9b | C1+FN | 20 | 20 | 0 | 0 | 0 |
| qwen3.5:9b | C1+H2 | 20 | 20 | 0 | 0 | 0 |
| qwen3.5:9b | C1+H1e | 20 | 20 | 0 | 0 | 0 |
| qwen3.5:9b | C1+H1n | 4 | 0 | 4 | 0 | 0 |
| qwen3.5:9b | C1+H7 | 20 | 11 | 9 | 0 | 0 |

**Noise floor (read this before using the table above).** Seed and prompt are the same in a pair, yet runs are not reproducible. In pairs where the other arm's handler never fired (C1+H2, C1+H1e: identical prompt and tools, so a deterministic model would repeat the episode), the supported flag or the request count still differed:

| model | arm | pairs where the handler never fired | same supported flag and same request count | different outcome or request count |
|---|---|---:|---:|---:|
| bonsai-2:4b | C1+H2 | 11 | 9 | 2 |
| bonsai-2:4b | C1+H1e | 16 | 13 | 3 |
| gpt-oss:20b | C1+H2 | 19 | 9 | 10 |
| gpt-oss:20b | C1+H1e | 16 | 3 | 13 |
| lfm3:1.7b | C1+H2 | 10 | 7 | 3 |
| lfm3:1.7b | C1+H1e | 15 | 8 | 7 |
| qwen3.5:9b | C1+H2 | 14 | 12 | 2 |
| qwen3.5:9b | C1+H1e | 16 | 14 | 2 |

So a discordant pair is not evidence of a handler effect unless the handler fired; for gpt-oss about 50 to 80 percent of such pairs differ and for qwen about 12 percent.

## Wall time per episode
| model | arm | episodes | median s | p90 s | max s | episodes > 150 s |
|---|---|---:|---:|---:|---:|---:|
| bonsai-2:4b | A1 | 20 | 18 | 36 | 78 | 0 |
| bonsai-2:4b | C1 | 20 | 16 | 47 | 73 | 0 |
| bonsai-2:4b | M0 | 20 | 18 | 25 | 46 | 0 |
| bonsai-2:4b | C1+FN | 20 | 17 | 62 | 111 | 0 |
| bonsai-2:4b | C1+H2 | 20 | 16 | 52 | 85 | 0 |
| bonsai-2:4b | C1+H1e | 20 | 18 | 64 | 222 | 1 |
| bonsai-2:4b | C1+H1n | 4 | 18 | 21 | 21 | 0 |
| bonsai-2:4b | C1+H7 | 20 | 25 | 76 | 123 | 0 |
| gpt-oss:20b | A1 | 20 | 22 | 54 | 114 | 0 |
| gpt-oss:20b | C1 | 20 | 43 | 96 | 128 | 0 |
| gpt-oss:20b | M0 | 20 | 51 | 93 | 150 | 1 |
| gpt-oss:20b | C1+FN | 20 | 45 | 65 | 80 | 0 |
| gpt-oss:20b | C1+H2 | 20 | 44 | 78 | 95 | 0 |
| gpt-oss:20b | C1+H1e | 20 | 50 | 76 | 100 | 0 |
| gpt-oss:20b | C1+H1n | 4 | 39 | 53 | 53 | 0 |
| gpt-oss:20b | C1+H7 | 20 | 77 | 157 | 174 | 3 |
| lfm3:1.7b | A1 | 20 | 24 | 50 | 131 | 0 |
| lfm3:1.7b | C1 | 20 | 23 | 38 | 98 | 0 |
| lfm3:1.7b | M0 | 20 | 21 | 51 | 99 | 0 |
| lfm3:1.7b | C1+FN | 20 | 20 | 43 | 92 | 0 |
| lfm3:1.7b | C1+H2 | 20 | 20 | 42 | 76 | 0 |
| lfm3:1.7b | C1+H1e | 20 | 27 | 43 | 63 | 0 |
| lfm3:1.7b | C1+H1n | 4 | 18 | 20 | 20 | 0 |
| lfm3:1.7b | C1+H7 | 20 | 73 | 110 | 165 | 1 |
| qwen3.5:9b | A1 | 20 | 47 | 85 | 156 | 1 |
| qwen3.5:9b | C1 | 20 | 39 | 73 | 105 | 0 |
| qwen3.5:9b | M0 | 20 | 43 | 73 | 106 | 0 |
| qwen3.5:9b | C1+FN | 20 | 38 | 64 | 92 | 0 |
| qwen3.5:9b | C1+H2 | 20 | 39 | 73 | 98 | 0 |
| qwen3.5:9b | C1+H1e | 20 | 42 | 61 | 109 | 0 |
| qwen3.5:9b | C1+H1n | 4 | 36 | 38 | 38 | 0 |
| qwen3.5:9b | C1+H7 | 20 | 42 | 246 | 486 | 4 |

Episodes above 150 s: bonsai 1 (C1+H1e), gpt-oss 4 (M0 1, C1+H7 3), lfm3 1 (C1+H7), qwen 5 (A1 1, C1+H7 4; longest 486 s under C1+H7). H7 has the largest maximum for lfm3, gpt-oss and qwen, and a higher median than C1 for lfm3 (73 s against 23 s), gpt-oss (77 s against 43 s) and bonsai (25 s against 16 s); for qwen the median is similar (42 s against 39 s) but the p90 is 246 s against 73 s.

## Abort causes per arm (episodes whose run ended with an exception, timeout or iteration limit)
| model | arm | aborted episodes | causes |
|---|---|---:|---|
| bonsai-2:4b | A1 | 5 | error('multiple repeat at position 2') x2; 1 validation error for ros2_service_call request Input should be a val x2; 1 validation error for ros2_param_set param_value Input should be a va x1 |
| bonsai-2:4b | C1+H7 | 2 | ResponseError('XML syntax error on line 3: element <function> closed b x2 |
| gpt-oss:20b | A1 | 11 | 1 validation error for ros2_node_list blacklist Input should be a vali x5; 1 validation error for ros2_topic_list blacklist Input should be a val x2; 1 validation error for ros2_topic_info topics Field required [type=mis x2; 1 validation error for ros2_service_list blacklist Input should be a v x2 |
| gpt-oss:20b | M0 | 2 | ResponseError('error parsing tool call: raw=\'{"node_name":"/e2/??","p x1; ResponseError('error parsing tool call: raw=\'We need to find which no x1 |
| gpt-oss:20b | C1+H1e | 1 | ResponseError('error parsing tool call: raw=\'{"pattern":"^/alder/pewt x1 |
| gpt-oss:20b | C1+H7 | 4 | ResponseError('error parsing tool call: raw=\'{"steps":[{"tool":"ros2_ x1; ResponseError('error parsing tool call: raw=\'We need to list nodes, t x1; ResponseError('error parsing tool call: raw=\'{"steps":[{"tool":"ros_p x1; ResponseError('error parsing tool call: raw=\'{"pattern":"^/plant32/ce x1 |
| lfm3:1.7b | A1 | 2 | error('multiple repeat at position 2') x1; 1 validation error for ros2_service_call request Input should be a val x1 |
| lfm3:1.7b | M0 | 1 | ResponseError('XML syntax error on line 13: unexpected EOF') x1 |
| lfm3:1.7b | C1+H2 | 1 | ResponseError('XML syntax error on line 10: element <function> closed  x1 |

No abort under C1 in any model; the A1 aborts are the stock-executor failure class (invalid optional-list argument, bad regex pattern, non-string argument to a write tool). The remaining aborts in other arms are Ollama-side `error parsing tool call` / `XML syntax error` replies, i.e. the model emitted a malformed tool call that the server rejected; they are not caused by the handlers but they are not removed by them either.

## Handler results
**H2 (unique-suffix repair).** 17 repairs, 16 judged correct by the heuristic (resolved name appears in the task's truth or support), **1 harmful**: `bonsai-2_4b-e1h/027-e1h_abs_1-C1+H2-bonsai-2_4b-s2` asked about `/ember/mistral` (not running), H2 resolved it to the running `/e1h/ember/mistral`, and the episode was unsupported. This is the known harm mode, observed once; on the absent-target tasks there were 11 H2 decisions in all and models mostly did not use suffix names. 27 decisions made no repair (zero or several matches; 2 of them on the ambiguous tasks, which is the intended no-repair branch). The full repair list is in PILOT_TABLES.md.

| model | arm | reuse events | reuse blocked by event | changing-task episodes | answered with the stale value (not supported) |
|---|---|---:|---:|---:|---:|
| bonsai-2:4b | C1+H1e | 2 | 3 | 4 | 0 |
| bonsai-2:4b | C1+H1n | 39 | 0 | 4 | 4 |
| gpt-oss:20b | C1+H1e | 0 | 4 | 4 | 0 |
| gpt-oss:20b | C1+H1n | 4 | 0 | 4 | 4 |
| lfm3:1.7b | C1+H1e | 1 | 4 | 4 | 0 |
| lfm3:1.7b | C1+H1n | 4 | 0 | 4 | 4 |
| qwen3.5:9b | C1+H1e | 0 | 4 | 4 | 0 |
| qwen3.5:9b | C1+H1n | 4 | 0 | 4 | 4 |

H1e never returned a stale value: on all 16 changing-parameter episodes the scripted change was seen on `/parameter_events` and reuse was blocked in 15 (the monitor added about 3 s of start-up per episode, logged as `monitor_overhead`). It also saved almost nothing: 3 reuse events in 80 episodes. **H1n returned the stale value in 16 of 16 changing-parameter episodes** (harm probe, by design). The lower gpt-oss H1e count (10/20 vs C1 15/20) comes with 0 reuse events and the noise floor above.

**H7 (plan enforcement)** (valid, revised arm only):

| model | episodes | plan accepted | invalid plans | fallbacks | replans | accepted plans complete vs floor route | supported-complete | LLM requests (total) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bonsai-2:4b | 20 | 22 | 2 | 0 | 2 | 5/22 | 6 | 326 |
| gpt-oss:20b | 20 | 8 | 28 | 10 | 0 | 5/8 | 10 | 133 |
| lfm3:1.7b | 20 | 15 | 26 | 9 | 5 | 2/15 | 5 | 237 |
| qwen3.5:9b | 20 | 27 | 7 | 1 | 7 | 11/27 | 11 | 219 |

H7 is below C1 in supported-complete for every model (lfm3 5 vs 17, bonsai 6 vs 13, gpt-oss 10 vs 15, qwen 11 vs 20) and costs 1.3 to 2.5 times the requests of C1 (gpt-oss 1.3, bonsai 1.7, lfm3 2.3, qwen 2.5). The mechanism worked as specified and is the cause: plans are often incomplete against the verified floor route (accepted plans complete 5/22, 5/8, 2/15, 11/27), tools outside the current and next step are refused, and models rarely call `replan` (14 replans in 80 episodes). Example: qwen planned only `ros2_service_info` for v2 and then repeated it until it submitted `node: unknown`.

**M0 (MetaTool supertool).**
| model | M0 episodes | supertool called | supertool before any other tool | answered with final_answer |
|---|---:|---:|---:|---:|
| bonsai-2:4b | 20 | 2 | 2 | n/a |
| gpt-oss:20b | 20 | 20 | 20 | n/a |
| lfm3:1.7b | 20 | 0 | 0 | n/a |
| qwen3.5:9b | 20 | 0 | 0 | n/a |
Adoption differs sharply by model: gpt-oss called supertool first in 20/20 episodes (17/20 supported vs C1 15/20, within the noise above); the other three almost never called it (the added sentence changes the prompt only). M0 is not distinguishable from C1 in this pilot.

**C1+FN.** No visible effect on supported-complete or requests (see tables); it never changes a trace unless a tool output contains `Node name` / `Node namespace`.

**C1 versus A1 (the harness-level question).** C1 bundles four changes (errors as text, strict argument check, domain menu, `final_answer`), so only the bundle can be read. Supported-complete A1 to C1: bonsai 6 to 13, gpt-oss 6 to 15, lfm3 15 to 17, qwen 19 to 20; aborts A1 to C1: 5 to 0, 11 to 0, 2 to 0, 0 to 0. For the two small/weak models and gpt-oss most of the A1 failures were stock aborts; for qwen the bundle changed little.

## Harm cases
"Harm" below means supported under C1 but not under the other arm in the same model, task and seed pair. For A1 this is the absence of the C1 executor and not a harm of A1. For arms whose handler did not fire in the pair, the difference is run noise (see the noise floor). Counts per model and arm are the "C1 only" column of the paired table; every case is listed here with its run id and automatic failure-row labels (taxonomy rows 1 to 14; rows 9 and 15 are not labelled; labels are heuristics):

- bonsai-2:4b A1 e1h_abs_1 seed 2: bonsai-2_4b-e1h/001-e1h_abs_1-A1-bonsai-2_4b-s2, failure rows [2, 8, 13]
- bonsai-2:4b A1 e1h_chg_1 seed 2: bonsai-2_4b-e1h/022-e1h_chg_1-A1-bonsai-2_4b-s2, failure rows [1, 5, 6, 10, 13]
- bonsai-2:4b A1 e1h_chg_1 seed 1: bonsai-2_4b-e1h/049-e1h_chg_1-A1-bonsai-2_4b-s1, failure rows [1, 5, 12]
- bonsai-2:4b A1 e1h_amb_2 seed 1: bonsai-2_4b-e1h/058-e1h_amb_2-A1-bonsai-2_4b-s1, failure rows [10, 13]
- bonsai-2:4b A1 e1h_abs_1 seed 1: bonsai-2_4b-e1h/064-e1h_abs_1-A1-bonsai-2_4b-s1, failure rows [1, 13]
- bonsai-2:4b A1 e1h_chg_2 seed 1: bonsai-2_4b-e1h/072-e1h_chg_2-A1-bonsai-2_4b-s1, failure rows [1, 7, 10]
- bonsai-2:4b A1 u3 seed 2: bonsai-2_4b-stage3/017-u3-A1-bonsai-2_4b-s2, failure rows [2, 7]
- bonsai-2:4b A1 v2 seed 2: bonsai-2_4b-stage3/034-v2-A1-bonsai-2_4b-s2, failure rows [1, 8, 10, 12]
- bonsai-2:4b A1 h4 seed 2: bonsai-2_4b-stage3/045-h4-A1-bonsai-2_4b-s2, failure rows [7, 10]
- bonsai-2:4b A1 p3 seed 1: bonsai-2_4b-stage3/048-p3-A1-bonsai-2_4b-s1, failure rows [7]
- bonsai-2:4b M0 e1h_abs_1 seed 2: bonsai-2_4b-e1h/063-e1h_abs_1-M0-bonsai-2_4b-s2, failure rows [13]
- bonsai-2:4b M0 p3 seed 1: bonsai-2_4b-stage3/001-p3-M0-bonsai-2_4b-s1, failure rows [11]
- bonsai-2:4b M0 p3 seed 2: bonsai-2_4b-stage3/016-p3-M0-bonsai-2_4b-s2, failure rows [2, 10, 13]
- bonsai-2:4b C1+FN h4 seed 2: bonsai-2_4b-stage3/042-h4-C1+FN-bonsai-2_4b-s2, failure rows [1, 2, 10, 13]
- bonsai-2:4b C1+H2 e1h_abs_1 seed 2: bonsai-2_4b-e1h/027-e1h_abs_1-C1+H2-bonsai-2_4b-s2, failure rows [13]
- bonsai-2:4b C1+H1n e1h_chg_1 seed 1: bonsai-2_4b-e1h/045-e1h_chg_1-C1+H1n-bonsai-2_4b-s1, failure rows [1, 10, 13]
- bonsai-2:4b C1+H1n e1h_chg_2 seed 1: bonsai-2_4b-e1h/048-e1h_chg_2-C1+H1n-bonsai-2_4b-s1, failure rows [1, 10, 13]
- bonsai-2:4b C1+H1n e1h_chg_1 seed 2: bonsai-2_4b-e1h/053-e1h_chg_1-C1+H1n-bonsai-2_4b-s2, failure rows [1, 10, 13]
- bonsai-2:4b C1+H7 e1h_abs_1 seed 1: bonsai-2_4b-e1h/040-e1h_abs_1-C1+H7-bonsai-2_4b-s1, failure rows [2, 11]
- bonsai-2:4b C1+H7 e1h_chg_2 seed 1: bonsai-2_4b-e1h/047-e1h_chg_2-C1+H7-bonsai-2_4b-s1, failure rows [1, 10, 13]
- bonsai-2:4b C1+H7 e1h_chg_1 seed 2: bonsai-2_4b-e1h/070-e1h_chg_1-C1+H7-bonsai-2_4b-s2, failure rows [1, 10, 12]
- bonsai-2:4b C1+H7 e1h_amb_2 seed 1: bonsai-2_4b-e1h/074-e1h_amb_2-C1+H7-bonsai-2_4b-s1, failure rows [7, 10]
- bonsai-2:4b C1+H7 h4 seed 2: bonsai-2_4b-stage3/004-h4-C1+H7-bonsai-2_4b-s2, failure rows [2, 8, 10, 12]
- bonsai-2:4b C1+H7 u3 seed 2: bonsai-2_4b-stage3/024-u3-C1+H7-bonsai-2_4b-s2, failure rows [1, 10, 13]
- bonsai-2:4b C1+H7 p3 seed 1: bonsai-2_4b-stage3/036-p3-C1+H7-bonsai-2_4b-s1, failure rows [10, 13]
- bonsai-2:4b C1+H7 v2 seed 2: bonsai-2_4b-stage3/055-v2-C1+H7-bonsai-2_4b-s2, failure rows [2, 8, 12]
- bonsai-2:4b C1+H7 e1h_amb_1 seed 2: bonsai-2_4b-e1h-resume1/000-e1h_amb_1-C1+H7-bonsai-2_4b-s2, failure rows [1, 10, 13]
- gpt-oss:20b A1 e1h_amb_1 seed 2: gpt-oss_20b-e1h/033-e1h_amb_1-A1-gpt-oss_20b-s2, failure rows [7, 10]
- gpt-oss:20b A1 e1h_amb_2 seed 2: gpt-oss_20b-e1h/057-e1h_amb_2-A1-gpt-oss_20b-s2, failure rows [7, 10]
- gpt-oss:20b A1 e1h_abs_1 seed 1: gpt-oss_20b-e1h/069-e1h_abs_1-A1-gpt-oss_20b-s1, failure rows [7, 10]
- gpt-oss:20b A1 e1h_amb_1 seed 1: gpt-oss_20b-e1h/076-e1h_amb_1-A1-gpt-oss_20b-s1, failure rows [7, 10]
- gpt-oss:20b A1 e1h_chg_2 seed 2: gpt-oss_20b-e1h/079-e1h_chg_2-A1-gpt-oss_20b-s2, failure rows [1, 10, 13]
- gpt-oss:20b A1 e1h_abs_2 seed 1: gpt-oss_20b-e1h/082-e1h_abs_2-A1-gpt-oss_20b-s1, failure rows [7, 10]
- gpt-oss:20b A1 u3 seed 2: gpt-oss_20b-stage3/010-u3-A1-gpt-oss_20b-s2, failure rows [7, 10]
- gpt-oss:20b A1 h4 seed 2: gpt-oss_20b-stage3/015-h4-A1-gpt-oss_20b-s2, failure rows [7, 10]
- gpt-oss:20b A1 p3 seed 2: gpt-oss_20b-stage3/039-p3-A1-gpt-oss_20b-s2, failure rows [11]
- gpt-oss:20b A1 u3 seed 1: gpt-oss_20b-stage3/041-u3-A1-gpt-oss_20b-s1, failure rows [7, 10]
- gpt-oss:20b A1 v2 seed 1: gpt-oss_20b-stage3/043-v2-A1-gpt-oss_20b-s1, failure rows [7, 10]
- gpt-oss:20b M0 e1h_chg_2 seed 1: gpt-oss_20b-e1h/065-e1h_chg_2-M0-gpt-oss_20b-s1, failure rows [7, 10]
- gpt-oss:20b C1+FN e1h_abs_2 seed 1: gpt-oss_20b-e1h/052-e1h_abs_2-C1+FN-gpt-oss_20b-s1, failure rows [13]
- gpt-oss:20b C1+FN e1h_chg_2 seed 2: gpt-oss_20b-e1h/084-e1h_chg_2-C1+FN-gpt-oss_20b-s2, failure rows [1, 10, 13]
- gpt-oss:20b C1+H2 e1h_abs_1 seed 1: gpt-oss_20b-e1h/075-e1h_abs_1-C1+H2-gpt-oss_20b-s1, failure rows [13]
- gpt-oss:20b C1+H1e e1h_abs_2 seed 1: gpt-oss_20b-e1h/023-e1h_abs_2-C1+H1e-gpt-oss_20b-s1, failure rows [13]
- gpt-oss:20b C1+H1e e1h_abs_1 seed 1: gpt-oss_20b-e1h/034-e1h_abs_1-C1+H1e-gpt-oss_20b-s1, failure rows [13]
- gpt-oss:20b C1+H1e h4 seed 2: gpt-oss_20b-stage3/006-h4-C1+H1e-gpt-oss_20b-s2, failure rows [10, 12]
- gpt-oss:20b C1+H1e v2 seed 1: gpt-oss_20b-stage3/025-v2-C1+H1e-gpt-oss_20b-s1, failure rows [13]
- gpt-oss:20b C1+H1e p3 seed 2: gpt-oss_20b-stage3/026-p3-C1+H1e-gpt-oss_20b-s2, failure rows [10, 13]
- gpt-oss:20b C1+H1e u3 seed 1: gpt-oss_20b-stage3/050-u3-C1+H1e-gpt-oss_20b-s1, failure rows [13]
- gpt-oss:20b C1+H1n e1h_chg_2 seed 2: gpt-oss_20b-e1h/020-e1h_chg_2-C1+H1n-gpt-oss_20b-s2, failure rows [1, 10, 13]
- gpt-oss:20b C1+H1n e1h_chg_2 seed 1: gpt-oss_20b-e1h/029-e1h_chg_2-C1+H1n-gpt-oss_20b-s1, failure rows [1, 10, 13]
- gpt-oss:20b C1+H1n e1h_chg_1 seed 1: gpt-oss_20b-e1h/045-e1h_chg_1-C1+H1n-gpt-oss_20b-s1, failure rows [1, 10, 13]
- gpt-oss:20b C1+H1n e1h_chg_1 seed 2: gpt-oss_20b-e1h/085-e1h_chg_1-C1+H1n-gpt-oss_20b-s2, failure rows [1, 10, 13]
- gpt-oss:20b C1+H7 e1h_chg_2 seed 2: gpt-oss_20b-e1h/035-e1h_chg_2-C1+H7-gpt-oss_20b-s2, failure rows [7, 10, 14]
- gpt-oss:20b C1+H7 e1h_amb_1 seed 1: gpt-oss_20b-e1h/060-e1h_amb_1-C1+H7-gpt-oss_20b-s1, failure rows [7, 10]
- gpt-oss:20b C1+H7 e1h_amb_2 seed 1: gpt-oss_20b-e1h/074-e1h_amb_2-C1+H7-gpt-oss_20b-s1, failure rows [10, 13]
- gpt-oss:20b C1+H7 e1h_abs_2 seed 1: gpt-oss_20b-e1h/086-e1h_abs_2-C1+H7-gpt-oss_20b-s1, failure rows [13]
- gpt-oss:20b C1+H7 u3 seed 2: gpt-oss_20b-stage3/002-u3-C1+H7-gpt-oss_20b-s2, failure rows [10, 13]
- gpt-oss:20b C1+H7 h4 seed 2: gpt-oss_20b-stage3/027-h4-C1+H7-gpt-oss_20b-s2, failure rows [2, 13]
- gpt-oss:20b C1+H7 v2 seed 1: gpt-oss_20b-stage3/035-v2-C1+H7-gpt-oss_20b-s1, failure rows [7, 10]
- lfm3:1.7b A1 e1h_abs_1 seed 1: lfm3_1.7b-e1h/019-e1h_abs_1-A1-lfm3_1.7b-s1, failure rows [2, 13]
- lfm3:1.7b A1 v2 seed 1: lfm3_1.7b-stage3/020-v2-A1-lfm3_1.7b-s1, failure rows [1, 2, 7]
- lfm3:1.7b C1+FN e1h_chg_2 seed 1: lfm3_1.7b-e1h/003-e1h_chg_2-C1+FN-lfm3_1.7b-s1, failure rows [1, 10, 13]
- lfm3:1.7b C1+FN v2 seed 1: lfm3_1.7b-stage3/051-v2-C1+FN-lfm3_1.7b-s1, failure rows [1, 2, 8, 13]
- lfm3:1.7b C1+H2 e1h_abs_1 seed 2: lfm3_1.7b-e1h/074-e1h_abs_1-C1+H2-lfm3_1.7b-s2, failure rows [2, 7]
- lfm3:1.7b C1+H2 v2 seed 1: lfm3_1.7b-stage3/018-v2-C1+H2-lfm3_1.7b-s1, failure rows [10, 12, 14]
- lfm3:1.7b C1+H2 h4 seed 1: lfm3_1.7b-stage3/032-h4-C1+H2-lfm3_1.7b-s1, failure rows [13]
- lfm3:1.7b C1+H1e v2 seed 1: lfm3_1.7b-stage3/006-v2-C1+H1e-lfm3_1.7b-s1, failure rows [1, 2, 13]
- lfm3:1.7b C1+H1n e1h_chg_2 seed 1: lfm3_1.7b-e1h/044-e1h_chg_2-C1+H1n-lfm3_1.7b-s1, failure rows [1, 10, 13]
- lfm3:1.7b C1+H1n e1h_chg_2 seed 2: lfm3_1.7b-e1h/047-e1h_chg_2-C1+H1n-lfm3_1.7b-s2, failure rows [1, 10, 13]
- lfm3:1.7b C1+H1n e1h_chg_1 seed 1: lfm3_1.7b-e1h/069-e1h_chg_1-C1+H1n-lfm3_1.7b-s1, failure rows [1, 10, 13]
- lfm3:1.7b C1+H1n e1h_chg_1 seed 2: lfm3_1.7b-e1h/086-e1h_chg_1-C1+H1n-lfm3_1.7b-s2, failure rows [1, 10, 13]
- lfm3:1.7b C1+H7 e1h_amb_1 seed 1: lfm3_repair-e1h/002-e1h_amb_1-C1+H7-lfm3_1.7b-s1, failure rows [1, 10, 13]
- lfm3:1.7b C1+H7 e1h_amb_1 seed 2: lfm3_repair-e1h/005-e1h_amb_1-C1+H7-lfm3_1.7b-s2, failure rows [1, 10, 13]
- lfm3:1.7b C1+H7 e1h_abs_2 seed 2: lfm3_repair-e1h/007-e1h_abs_2-C1+H7-lfm3_1.7b-s2, failure rows [1, 2, 13]
- lfm3:1.7b C1+H7 e1h_abs_1 seed 1: lfm3_repair-e1h/008-e1h_abs_1-C1+H7-lfm3_1.7b-s1, failure rows [1, 13]
- lfm3:1.7b C1+H7 e1h_chg_2 seed 1: lfm3_repair-e1h/011-e1h_chg_2-C1+H7-lfm3_1.7b-s1, failure rows [10, 13]
- lfm3:1.7b C1+H7 e1h_abs_2 seed 1: lfm3_repair-e1h/014-e1h_abs_2-C1+H7-lfm3_1.7b-s1, failure rows [1, 13]
- lfm3:1.7b C1+H7 e1h_chg_1 seed 1: lfm3_repair-e1h/015-e1h_chg_1-C1+H7-lfm3_1.7b-s1, failure rows [10, 12, 14]
- lfm3:1.7b C1+H7 e1h_amb_2 seed 1: lfm3_repair-e1h/016-e1h_amb_2-C1+H7-lfm3_1.7b-s1, failure rows [1, 10, 13]
- lfm3:1.7b C1+H7 e1h_chg_2 seed 2: lfm3_repair-e1h/020-e1h_chg_2-C1+H7-lfm3_1.7b-s2, failure rows [10, 12, 14]
- lfm3:1.7b C1+H7 e1h_abs_1 seed 2: lfm3_repair-e1h/023-e1h_abs_1-C1+H7-lfm3_1.7b-s2, failure rows [1, 13]
- lfm3:1.7b C1+H7 u3 seed 2: lfm3_repair-stage3/001-u3-C1+H7-lfm3_1.7b-s2, failure rows [1, 10, 12]
- lfm3:1.7b C1+H7 u3 seed 1: lfm3_repair-stage3/003-u3-C1+H7-lfm3_1.7b-s1, failure rows [2, 8, 10, 13]
- lfm3:1.7b C1+H7 h4 seed 2: lfm3_repair-stage3/007-h4-C1+H7-lfm3_1.7b-s2, failure rows [1, 10, 13]
- qwen3.5:9b A1 p3 seed 1: qwen3.5_9b-stage3/038-p3-A1-qwen3.5_9b-s1, failure rows [10, 13]
- qwen3.5:9b M0 e1h_abs_1 seed 1: qwen3.5_9b-e1h/050-e1h_abs_1-M0-qwen3.5_9b-s1, failure rows [13]
- qwen3.5:9b C1+H1n e1h_chg_2 seed 2: qwen3.5_9b-e1h/030-e1h_chg_2-C1+H1n-qwen3.5_9b-s2, failure rows [1, 10, 13]
- qwen3.5:9b C1+H1n e1h_chg_2 seed 1: qwen3.5_9b-e1h/040-e1h_chg_2-C1+H1n-qwen3.5_9b-s1, failure rows [1, 10, 13]
- qwen3.5:9b C1+H1n e1h_chg_1 seed 1: qwen3.5_9b-e1h/042-e1h_chg_1-C1+H1n-qwen3.5_9b-s1, failure rows [1, 10, 13]
- qwen3.5:9b C1+H1n e1h_chg_1 seed 2: qwen3.5_9b-e1h/078-e1h_chg_1-C1+H1n-qwen3.5_9b-s2, failure rows [1, 10, 13]
- qwen3.5:9b C1+H7 u3 seed 1: qwen3.5_9b-stage3/024-u3-C1+H7-qwen3.5_9b-s1, failure rows [1, 8, 10, 12]
- qwen3.5:9b C1+H7 u3 seed 2: qwen3.5_9b-stage3/046-u3-C1+H7-qwen3.5_9b-s2, failure rows [1, 10, 13]
- qwen3.5:9b C1+H7 v2 seed 1: qwen3.5_9b-stage3/050-v2-C1+H7-qwen3.5_9b-s1, failure rows [1, 10, 13]
- qwen3.5:9b C1+H7 v2 seed 2: qwen3.5_9b-stage3/051-v2-C1+H7-qwen3.5_9b-s2, failure rows [1, 10, 13]
- qwen3.5:9b C1+H7 h4 seed 2: qwen3.5_9b-stage3/054-h4-C1+H7-qwen3.5_9b-s2, failure rows [1, 10, 13]
- qwen3.5:9b C1+H7 e1h_amb_1 seed 2: qwen3.5_9b-e1h/004-e1h_amb_1-C1+H7-qwen3.5_9b-s2, failure rows [1, 10, 13]
- qwen3.5:9b C1+H7 e1h_amb_2 seed 1: qwen3.5_9b-e1h/012-e1h_amb_2-C1+H7-qwen3.5_9b-s1, failure rows [1, 10, 13]
- qwen3.5:9b C1+H7 e1h_abs_1 seed 2: qwen3.5_9b-e1h/061-e1h_abs_1-C1+H7-qwen3.5_9b-s2, failure rows [1, 13]
- qwen3.5:9b C1+H7 e1h_abs_2 seed 2: qwen3.5_9b-e1h/068-e1h_abs_2-C1+H7-qwen3.5_9b-s2, failure rows [1, 13]

Handler-attributable harm that I can confirm from the traces: H1n stale answers (16/16), the H2 repair on an absent node (1), and H7 plan-driven failures (all four models, mechanism read from the traces above). Other entries are consistent with noise or the A1 comparison and were not individually attributed.

## Failure rows of unsupported episodes (automatic labels)
| model | arm | unsupported episodes | taxonomy rows (automatic, descriptive; row 9 and 15 not labelled) |
|---|---|---:|---|
| bonsai-2:4b | A1 | 14 | row 1: 7, row 2: 4, row 5: 2, row 6: 1, row 7: 5, row 8: 3, row 10: 6, row 11: 1, row 12: 4, row 13: 4 |
| bonsai-2:4b | C1 | 7 | row 1: 2, row 2: 4, row 8: 2, row 10: 2, row 11: 1, row 12: 2, row 13: 4 |
| bonsai-2:4b | M0 | 7 | row 1: 1, row 2: 1, row 10: 1, row 11: 1, row 13: 6 |
| bonsai-2:4b | C1+FN | 7 | row 1: 2, row 2: 3, row 8: 1, row 10: 3, row 11: 1, row 12: 2, row 13: 4 |
| bonsai-2:4b | C1+H2 | 7 | row 1: 2, row 2: 3, row 8: 1, row 10: 2, row 11: 1, row 12: 2, row 13: 4 |
| bonsai-2:4b | C1+H1e | 7 | row 1: 3, row 2: 2, row 8: 1, row 10: 3, row 11: 1, row 12: 4, row 13: 2 |
| bonsai-2:4b | C1+H1n | 4 | row 1: 4, row 8: 1, row 10: 4, row 12: 1, row 13: 3 |
| bonsai-2:4b | C1+H7 | 14 | row 1: 6, row 2: 4, row 7: 2, row 8: 3, row 10: 11, row 11: 2, row 12: 5, row 13: 5 |
| gpt-oss:20b | A1 | 14 | row 1: 1, row 2: 1, row 7: 11, row 10: 13, row 11: 1, row 12: 1, row 13: 1 |
| gpt-oss:20b | C1 | 5 | row 1: 1, row 11: 1, row 13: 4 |
| gpt-oss:20b | M0 | 3 | row 1: 1, row 2: 1, row 7: 2, row 10: 1, row 13: 1 |
| gpt-oss:20b | C1+FN | 6 | row 1: 1, row 10: 1, row 13: 6 |
| gpt-oss:20b | C1+H2 | 3 | row 11: 1, row 13: 2 |
| gpt-oss:20b | C1+H1e | 10 | row 7: 1, row 10: 3, row 11: 1, row 12: 1, row 13: 7, row 14: 1 |
| gpt-oss:20b | C1+H1n | 4 | row 1: 4, row 10: 4, row 13: 4 |
| gpt-oss:20b | C1+H7 | 10 | row 2: 1, row 7: 4, row 10: 7, row 13: 6, row 14: 2 |
| lfm3:1.7b | A1 | 5 | row 1: 2, row 2: 3, row 7: 2, row 10: 1, row 13: 3 |
| lfm3:1.7b | C1 | 3 | row 13: 3 |
| lfm3:1.7b | M0 | 2 | row 1: 1, row 2: 1, row 7: 1, row 8: 1, row 10: 1, row 13: 1 |
| lfm3:1.7b | C1+FN | 4 | row 1: 2, row 2: 2, row 8: 1, row 10: 1, row 13: 4 |
| lfm3:1.7b | C1+H2 | 5 | row 1: 1, row 2: 1, row 7: 1, row 10: 1, row 12: 1, row 13: 3, row 14: 1 |
| lfm3:1.7b | C1+H1e | 2 | row 1: 1, row 2: 1, row 13: 2 |
| lfm3:1.7b | C1+H1n | 4 | row 1: 4, row 10: 4, row 13: 4 |
| lfm3:1.7b | C1+H7 | 15 | row 1: 10, row 2: 3, row 8: 2, row 10: 11, row 12: 4, row 13: 11, row 14: 2 |
| qwen3.5:9b | A1 | 1 | row 10: 1, row 13: 1 |
| qwen3.5:9b | M0 | 1 | row 13: 1 |
| qwen3.5:9b | C1+H1n | 4 | row 1: 4, row 10: 4, row 13: 4 |
| qwen3.5:9b | C1+H7 | 9 | row 1: 9, row 8: 1, row 10: 7, row 12: 1, row 13: 8 |

## Limits
- Synthetic read-only fixtures; 4 Stage 3 tasks and 6 harm tasks; 2 seeds per cell at temperature 0.7; 20 pairs per model and arm; no confidence intervals or tests.
- Runs are not reproducible from the seed (noise floor); Ollama 0.40.16 on a Windows host, model digests in `model_check/api_show.json` (modified-at dates only).
- C1 is a bundle; the pilot does not attribute its gain to a component. M0 and H7 are my implementation of the build document's description (the M0 source was not read by me; it comes from the build document).
- H7 was revised once after the first lfm3 results (registry names shown); H1e had one infrastructure bug; both disclosed above. Other arms were not changed after their first episode.
- The automatic taxonomy labels, the H2 "correct" heuristic and the answer rule (last JSON object, not the Stage 1 to 3 first-object rule) are conventions of this study. Under the last-object rule the answers of earlier stages would score differently from their published numbers.
- bonsai-2:4b is not an independent architecture; the pilot has three.
- No S0 episodes; no E2 or held-out use; no live robot; no paid API.
- Taken together this supports only: the C1 executor removed the stock-abort failures here; the specified H1n, and H7 as I implemented it, hurt in this fixture; H1e did not hurt and did not help; H2 and FN did not show a measurable effect, and H2 once did harm.
