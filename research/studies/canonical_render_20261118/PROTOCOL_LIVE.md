# Canonical result rendering: live protocol (frozen before the arm code and runner exist)

Dated 2026-11-18, Asia/Taipei. Development evidence only (synthetic fixtures, four small models); not a held-out result, not causal beyond these cells, not a novelty claim. Scorer v2.0 unchanged (`c6b02716...`). Held-out custodian files are not opened. The renderer is the frozen code of [PROTOCOL_OFFLINE.md](PROTOCOL_OFFLINE.md) (`FREEZE_RENDERER.json`); both offline bars were met ([REPORT_OFFLINE.md](REPORT_OFFLINE.md)). Authorisation: the owner's message of 2026-11-18 (freeze now; run only after the finish-split run has ended and its results are reported; smoke first; start the full run with nohup if the smoke is clean; one GPU job at a time).

## 1. Question and status
Does showing the model canonical renderings of tool results (consistent layout plus a joined full name where a namespace field and a name field share a block) reduce name errors, requests or tokens, without lowering supported answers? **Status of the idea: not yet justified as a method component.** The offline step showed the rendering is lossless and score-neutral and that for 57% of the recorded slashless fires the full name existed only as split fields; it did not show any model benefits. The closest prior mechanism, the tool-specific pilot arm `C1+FN`, gave no support gain (63/80 vs C1 65/80). The custodian's aggregate (0 of 76 held-out tasks need short-name resolution) means a development-task benefit may not transfer; this study cannot say.

## 2. Arms (differ in exactly one thing)
| arm | what the model is shown |
|---|---|
| `FULL` | pilot arm C1 unchanged (12 menu tools + `final_answer`, errors as tool messages, strict pre-check, one finish retry, observation-only guard) |
| `RENDER` | C1 unchanged, except that the successful result of each of the 12 menu tools is replaced by `render_result(raw result)` (frozen `render_core.py`) before it is returned to the model. Errors, harness messages and `final_answer` are untouched. The raw result is what the harness's own bookkeeping (ledger, step record) keeps; the raw and rendered text are both logged. Prompt, tool schemas and descriptions are byte-identical to `FULL` (hash-checked). |

## 3. Design
- **Tasks (18):** the 10 development tasks of the ablation (stage 3: `u3`, `p3`, `h4`, `v2`; e1h: `e1h_amb_1`, `e1h_amb_2`, `e1h_abs_1`, `e1h_abs_2`, `e1h_chg_1`, `e1h_chg_2`) and the 8 name-fix tasks (`nf_single_1`, `nf_single_2`, `nf_multi_1`, `nf_multi_2`, `nf_amb_1`, `nf_amb_2`, `nf_exact`, `nf_absent`). Interpretation of the instruction "dev tasks plus h4, u3, v2 and the name-fix tasks": all 10 dev tasks are included (h4, u3 and v2 are among them and form the stratum where 384 of the 406 recorded fires arose; `p3` and the e1h tasks are the other dev tasks). Strata: **S1** = `h4`, `u3`, `v2`; **S2** = the 8 name-fix tasks; **S3** = `p3` and the 6 e1h tasks (where the earlier fire counts were small, used as the harm check).
- **Models (4):** `lfm3:1.7b`, `qwen3.5:9b`, `gpt-oss:20b`, `bonsai-2:4b`; digests in `FREEZE_LIVE.json`. **Seeds:** 1 and 2. **Episodes:** 18 tasks x 4 models x 2 seeds x 2 arms = **288** (144 per arm).
- **Scheduling:** one fixture session per (model, environment) (stage3, e1h, namefix), both arms and both seeds of that session shuffled together, master seed 20261123. Settings: temperature 0.7, think false, num_ctx 65536, num_predict 4096, 40 iterations, 90 s HTTP and 900 s episode timeouts, round-2 oracle with the 5 s retry (amendment 4).
- **Known validity defect carried unchanged:** the scripted-change hook of `e1h_chg_*` misses when a node name is written without the leading slash; those cells stay in the denominators.
- Raw runs under `research/_artifacts/runs/canonical_render_20261118/`; results log `RESULTS_LOG_LIVE.jsonl` (append-only, one row per episode).

## 4. Metrics (frozen)
Per arm, per model, per stratum and overall: **supported-complete** (scorer v2.0); **model requests**; **input and output tokens** (as logged by the backend); **ending class** (accepted finish call, text answer, no answer: cap, backend error, timeout) and capped counts; **tool calls**.
**Name-error counts** (computed from the traces by the frozen `candidate_counts_20261118/count_candidates.py::fires_a` and `canonical_render_20261118/offline_check.py::classify_fire`, run on the raw results of the episode):
- (N1) slashless not-found **fires** (the definition of the candidate counts) per 100 episodes, split into **split-only** (the full name existed only as namespace + name fields before the fire) and **other** (contiguous earlier or in the task text);
- (N2) all not-found calls that name an entity (any form), per episode;
- (N3) failed calls (any reason) per episode;
- (N4) the request distance from a fire to the next successful call on that name.
Paired view: per (task, model, seed) cell, supported in both / FULL only / RENDER only / neither. Descriptive only (trajectories diverge from request 1-2).

## 5. Reading rule (frozen before any episode runs)
Conventions, not significance tests; chosen from the dev noise (`final_exam_draft_20261118/power_inputs.json`: about 15.8% of cells flip between two runs of the same loop; with 144 cells per arm the detectable difference at 80% power is about 9 points of supported rate, about 13 cells, and about 13.5% in the mean per-cell request ratio).
- **Mechanism signal (M):** in S1 + S2 together, split-only fires per 100 episodes are at least 30% lower in `RENDER` than in `FULL`, **and** the other fires are not lowered by 30% or more (the other fires are an internal control: rendering gives the model nothing new for names it already saw whole). Report the counts with their denominators whatever the outcome.
- **Harm flags (any one):** supported in `RENDER` lower than in `FULL` by 10 or more cells of 144; total requests up by 15% or more; total input + output tokens up by 10% or more; capped or no-answer endings up by 5 or more episodes; or the same sign of the supported difference (RENDER lower by 4 or more cells) in 3 or more of the 4 models.
- **Classes:** A = M seen and no harm flag: "eligible for consideration as a method component; a benefit in supported answers, requests or tokens is established only if it exceeds the detectable difference". B = M not seen and no harm flag: "no evidence of a benefit in these cells". C = a harm flag, whatever M: reported, not adopted. D = M seen with a harm flag: both reported.
- Every statement is limited to these 18 tasks, 4 models, 2 seeds and these fixtures. Differences in supported answers of up to about 13 cells cannot be told from noise. No change to a prompt, schema, renderer rule, scorer or scenario after the first live request.

## 6. Smoke, clean criteria and stop rules
- **Smoke:** `qwen3.5:9b`, tasks `u3` (stage 3), `e1h_amb_1` (e1h), `nf_single_1` (name-fix), seed 1, both arms = 6 episodes (not in any total).
- **Clean means all of:** (1) every episode finishes with an `episode_end`, no worker crash, no oracle failure, none over 900 s; (2) **arm fidelity from the traces:** the serialized prompts and the offered tool schemas of the two arms are identical; in `RENDER` every menu-tool result in the trace equals `render_result` of the logged raw result, and the number of derived `full name:` lines in `FULL` traces is 0; `FULL` traces contain no render events; (3) the six rows are collected with scorer v2.0 results; (4) Ollama loaded only the expected model and it is unloaded afterwards. A smoke episode that is unsupported is a model outcome, not a stop condition. Any harness, fixture, oracle or fidelity anomaly: stop and report; do not start the full run.
- **Order of events (owner's rule):** the full run and its smoke start only after (a) the finish-split run has ended and its results are reported, (b) the GPU is idle (`curl http://172.30.80.1:11434/api/ps` empty and `pgrep -af "run_"` empty of other jobs). Start the full run with `nohup`. Stop and report if Ollama becomes unreachable, if three consecutive episodes fail for infrastructure reasons, or if another job takes the GPU. Infrastructure-failed cells (no model request made) are listed and reported with and without them; none is silently dropped or re-run under a changed rule.

## 7. Outputs
`PROTOCOL_LIVE.md`, `PROTOCOL_LIVE.sha256`, `render_arm.py`, `run_render.py`, `tests/test_render_arm.py`, `smoke_check_live.py`, `FREEZE_LIVE.json`, `RESULTS_LOG_LIVE.jsonl`, later `analyze_live.py` (written and hashed before the full run starts, so the reading rule is applied by frozen code) and `REPORT_LIVE.md`.

## 8. Step 4 (not now)
After this study: run the frozen renderer unchanged on Nav2 / TurtleBot3 tool outputs and report coverage (share of leaves and lines parsed, derived lines), breakage (any lossless violation, using `offline_check.lossless_violations`) and size change; no rule is added to fix a failure there.
