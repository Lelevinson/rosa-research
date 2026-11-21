# Fairness test: how much of the fixed loop's gain is "errors returned as text" alone? (protocol frozen 2026-11-17, before any episode)

Owner brief (pasted, 2026-11-17, no brief file exists): arms on the ORIGINAL ROSA executor with all 47 stock tools and nothing else from the fixed loop; same 80 development cells; interpretation bands frozen by the owner. Development tasks only, no held-out data, scorer v2.0 untouched, no change to any tool schema or description, no push.

## 1. Question and preflight record (AGENTS.md)
- **Opportunity and evidence.** Supported answers on the 80 development cells: stock ROSA with its verbatim prompt 40 (`s0_dev_20261116`), stock executor + deconflicted prompt (A1) 47, Forge baseline 55, the fixed loop 70 (pilot) / 67 (round 1 control). 24 of S0's 80 episodes ended on an abort (gpt-oss 18 of 20; 17 `blacklist` validation errors), 18 of A1's. The fixed loop returns failed calls as text but also changes four other things (strict argument check, 12-tool menu, final-answer tool, bare-text handling). The size of the gain that errors-as-text alone explains is unknown; until measured, "the fixed loop's gain" cannot be attributed to its design.
- **Candidate vs control difference.** One change relative to the stock arms S0 and A1: a failed tool call no longer ends the episode; the model receives the error as the tool result. Nothing else.
- **Closest prior.** The pilot's S0 and A1 arms and `forge_baseline_20261115` (a pip-installed guardrail framework with its own retry rules) are the comparators; none isolates errors-as-text. No novelty claim.
- **Fair evaluation and cost.** Same cells, models, seeds, settings, fixtures and oracle as the pilot/S0; arms shuffled together inside one fixture session per (model, environment). 160 episodes, about 3 to 4 hours on this machine; CPU/GPU/ROS busy, so it runs after round 2 has ended.

## 2. Arms (original ROSA executor, all 47 stock tools)
- **E0**: the verbatim stock ROSA system prompt (the prompt of pilot arm S0, Stage 1 `A_orig`) + errors returned as text.
- **E1**: the deconflicted prompt (the prompt of pilot arm A1, Stage 3b) + errors returned as text.
- **Errors as text (the only change; implemented in `fair_arms.py`):** a tool call that fails by (a) argument validation of the tool's own stock schema (pydantic `ValidationError`), or (b) an exception raised by the tool, does not end the episode; the model receives, as the tool message, for (a) the error text exactly as pydantic prints it, for (b) `<ExceptionType>: <message>`. Each such event is logged (`tool_error_returned`: tool, kind, text). The tools' names, descriptions and schemas are not touched; same `AgentExecutor` (`handle_parsing_errors=True` as in S0/A1, 40 iterations); no argument pre-check, no short menu, no finish tool, no extra rule. Errors that are not tool calls (Ollama backend errors, a model output the SDK cannot parse into a tool call) are **not** tool errors and still end the episode as in S0/A1; they are counted as aborts.
- Not run (stated in advance): the fixed loop with the 47-tool menu and the fixed loop without the argument pre-check are only **proposed** in the report; the stall breaker stays parked.

## 3. Cells and settings
- 10 development tasks (stage 3: u3, p3, h4, v2; e1h: amb_1, amb_2, abs_1, abs_2, chg_1, chg_2) x 4 models (lfm3:1.7b, qwen3.5:9b, gpt-oss:20b, bonsai-2:4b) x seeds 1, 2 = the 80 pilot cells, each run under both arms = **160 episodes**. One fixture session per (model, environment) with both arms shuffled together (master seed 20261119): 16 episodes per stage 3 session, 24 per e1h session.
- Ollama as the pilot: temperature 0.7, `think` false (pilot SDK default), `num_ctx` 65536, `num_predict` 4096, assigned seed, 40-iteration cap, same observation-only guard that blocks write tools before ROS. Scorer v2.0 (`residual_failures_20261115/scorer_v2.py`), unchanged.
- **Oracle:** the pilot session's oracle with round 2's amendments 1, 2 and 4 (every oracle read retried once after 5 s; node list read through a daemon restarted once per session; raw node list logged), implemented by `run_round2.OracleWithRetry` imported unchanged. A smoke of 4 episodes (qwen3.5:9b, one stage 3 cell and one e1h cell under both arms) runs first and is not part of the totals.

## 4. Measures
Per arm, per model and pooled: supported-complete answers of 80 cells (scorer v2.0), episodes ending in an abort or error (by kind, from `episode_end`) and iteration-limit episodes, LLM requests, input+output tokens, requests per supported answer (total requests / supported), and the number of returned tool errors per episode (by kind). Same-cell comparison of E1 against A1 (existing rows) and E0 against S0; gpt-oss is reported separately (14 of the fixed loop's 27 extra cells over S0 came from it). Comparison numbers are taken from the existing logs: S0 40/80 (`s0_dev_20261116/RESULTS_LOG.jsonl`), A1 47/80, Forge 55/80 (`forge_baseline_20261115`), fixed loop 70/80 (pilot) and 67/80 (round 1 control); the A1 and S0 columns come from other sessions than this run, so differences of about 3 cells are noise.

## 5. Interpretation bands (frozen by the owner; noise is about +-3 cells). Applied to arm E1 (better prompt + errors as text) supported out of 80:
- **E1 >= 62:** most of the gain is errors-as-text; the claim about the loop's other parts must shrink.
- **E1 52 to 61:** errors-as-text is a large part; the other parts also matter.
- **E1 <= 51:** the other parts carry most of the gain.
E0 is reported without a band (the gain from errors-as-text with the original prompt). Per-model results and the abort breakdown are descriptive.

## 6. Stop and infrastructure rules
- Stop and report: Ollama unreachable, a write command reaching ROS, a cleanup failure, the wall-time limit (6 h per session), a tool-call path where the arm's handler visibly fails to return an error (an exception that ends an episode that should return text; counted per kind and reported).
- Oracle: a check that still fails after its retry stops the session. The infrastructure rule of the evaluation plan (as applied in round 2, amendments 2 and 3) is used: the stopped session's episodes stay in the log marked "excluded: infrastructure (oracle)" and the session is rerun once from the start with fresh fixtures (new run folder). A second oracle failure of the same session stops the run and is reported.
- No rule above is patched after results are seen; deviations are reported.

## 7. Limits (stated in advance)
Development tasks only, 4 small models, two seeds per cell, one fixture style; arms E0/E1 and the comparison columns come from different sessions; the tool error text is whatever pydantic or the tool prints, which may be less informative than the fixed loop's own messages. Nothing here is a novelty or significance claim, and the result answers only "errors-as-text alone", not what the other parts contribute individually (that is the proposed ablation, not run).

## 8. Output
`REPORT.md` with the usual five-row header (result, what it changes, what it cannot show, adoption-free, cost), per-model table, abort table, the band reading, and the proposal of the two ablations (fixed loop with the 47-tool menu; fixed loop without the argument pre-check): design, cells, bars, cost, not run.
