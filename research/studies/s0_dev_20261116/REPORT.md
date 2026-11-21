# Stock ROSA with its verbatim prompt on the development cells (2026-11-16)

Written for: the project owner (overnight Job 3). Stock ROSA (arm S0: the unmodified stock system prompt, which forbids parallel calls, all 47 stock tools, the stock executor) on the 80 pilot development cells (10 tasks x 2 seeds x 4 models), same Ollama settings as the pilot (temperature 0.7, num_ctx 65536, num_predict 4096, pilot SDK think default, 40-iteration cap), same fixtures, oracle and cleanup checks, same observation-only guard that blocks write tools before ROS, scorer v2.0 frozen. Runner [run_s0.py](run_s0.py) (reuses the pilot's `run_pilot.py` unchanged), every episode in [RESULTS_LOG.jsonl](RESULTS_LOG.jsonl) (phase `full`; 2 smoke episodes are phase `smoke`), notes in [RUN_NOTES.md](RUN_NOTES.md), tables [TABLES.md](TABLES.md). Smoke (2 cells, qwen3.5:9b) passed with no infrastructure problem. Prompt hash `daae74151b06` (stock prompt, 9 messages incl. "NEVER call multiple tools in parallel"), 47 tools offered.

| | |
|---|---|
| **Result** | Stock ROSA supported **40/80** (lfm3 13, qwen 16, gpt-oss 2, bonsai 9) vs **67/80** for the fixed loop rerun and 47/80 for the stock executor with the deconflicted prompt (A1, pilot); 480 requests and 3.74M tokens vs 506 and 2.00M (fixed loop) and 472 and 3.28M (A1). |
| **What it changes** | The comparison has its missing floor: the fixed loop beats stock ROSA by 27 supported answers on these cells (same-cell: only the fixed loop supported 30, only stock ROSA 3). Stock ROSA is also not just a weak prompt: stock is 7 below A1, so the deconflicted prompt alone recovers part of the gap and the executor/tool changes the rest. |
| **What it cannot show** | Which part of the fixed loop (errors as text, strict argument check, 12-tool menu, final-answer tool) causes the gain over stock; two seeds, 4 small models, development tasks only, no significance claim; the A1 and fixed-loop columns come from different sessions than S0 (A1 pilot; fixed loop round 1). |
| **Adoption-free?** | n/a (this is a baseline run, no mechanism). |
| **Cost** | Stock ROSA: 24 of 80 episodes ended with an abort/error (gpt-oss 18 of 20) vs 1 for the fixed loop; token cost about 1.9x the fixed loop (47-tool schema in every request, plus long episodes). |

## Per model and arm
| model | arm | episodes | supported-complete | LLM requests | tokens (in+out) | episodes with an abort/error |
|---|---|---:|---:|---:|---:|---:|
| lfm3:1.7b | stock ROSA, verbatim prompt (S0, this run) | 20 | 13 | 152 | 1280320 | 1 |
| lfm3:1.7b | fixed loop (build round 1 control) | 20 | 16 | 117 | 639889 | 0 |
| lfm3:1.7b | stock executor, deconflicted prompt (A1, pilot) | 20 | 15 | 135 | 1090427 | 2 |
| qwen3.5:9b | stock ROSA, verbatim prompt (S0, this run) | 20 | 16 | 120 | 851698 | 1 |
| qwen3.5:9b | fixed loop (build round 1 control) | 20 | 20 | 89 | 265853 | 0 |
| qwen3.5:9b | stock executor, deconflicted prompt (A1, pilot) | 20 | 19 | 86 | 563736 | 0 |
| gpt-oss:20b | stock ROSA, verbatim prompt (S0, this run) | 20 | 2 | 28 | 114512 | 18 |
| gpt-oss:20b | fixed loop (build round 1 control) | 20 | 16 | 116 | 293363 | 1 |
| gpt-oss:20b | stock executor, deconflicted prompt (A1, pilot) | 20 | 7 | 54 | 217813 | 11 |
| bonsai-2:4b | stock ROSA, verbatim prompt (S0, this run) | 20 | 9 | 180 | 1495780 | 4 |
| bonsai-2:4b | fixed loop (build round 1 control) | 20 | 15 | 184 | 796709 | 0 |
| bonsai-2:4b | stock executor, deconflicted prompt (A1, pilot) | 20 | 6 | 197 | 1409447 | 5 |
| all four | stock ROSA, verbatim prompt (S0, this run) | 80 | 40 | 480 | 3742310 | 24 |
| all four | fixed loop (build round 1 control) | 80 | 67 | 506 | 1995814 | 1 |
| all four | stock executor, deconflicted prompt (A1, pilot) | 80 | 47 | 472 | 3281423 | 18 |

Same-cell, S0 vs fixed loop (build round 1 control): both supported 37, only S0 3, only comparator 30, neither 10 (cells 80)

Same-cell, S0 vs stock executor, deconflicted prompt (A1, pilot): both supported 31, only S0 9, only comparator 16, neither 24 (cells 80)

S0 abort/error kinds: {'ResponseError': 3, 'validation error: request': 3, 'validation error: blacklist': 17, 'validation error: param_value': 1}

## Reading
- **Aborts dominate gpt-oss.** 17 of its 20 stock episodes ended on a validation error for the `blacklist` argument (the model passes a value the stock schema rejects, and the stock executor ends the episode), 1 on a tool-call parse error; supported 2/20 (A1: 11 aborts, 7/20; fixed loop: 1 abort, 16/20). 24 aborts overall: 17 `blacklist`, 3 `request` (a write-tool argument, blocked anyway), 1 `param_value`, 3 backend/response errors (lfm3 p3 seed 2 and bonsai e1h_abs_1 seed 2: XML tool-call syntax error; gpt-oss e1h_amb_1 seed 2: tool-call JSON parse error). No supported episode contained an abort.
- **Validity flags (kept in the table, labels unchanged).** Four changing-parameter episodes never received the scripted mid-episode change (known missed-hook defect, no `scripted_change` event): gpt-oss e1h_chg_1 seeds 1 and 2, e1h_chg_2 seed 2, bonsai e1h_chg_2 seed 2; all four are unsupported. No backend crash (CUDA) episodes this time.
- **qwen3.5:9b** is the one model where stock ROSA is nearly competitive (16 vs 20 vs 19) but uses 3.2x the tokens of the fixed loop (852k vs 266k).
- **Runs.** The bonsai stage-3 session stopped at its final "after" oracle (`node not listed: /plant32/jetty`) after all its 8 episodes had run; `/plant32/jetty` was listed in all 7 unfiltered node lists of the session, so the episodes were kept (same pattern as build round 1) and the remaining session (bonsai e1h, 12 cells) ran as a continuation. Cleanup was verified for every session; no write command reached ROS.

## Limits
Different sessions for the three columns (sampling noise between sessions in round 1 was about 3 supported cells and about 20 requests, so only the large gaps here are meaningful); the A1 pilot ran under the scorer-v2 relabelling of stored traces; A1 offered the same 47 tools as S0 but with the deconflicted prompt. Nothing here is a novelty or mechanism claim.
