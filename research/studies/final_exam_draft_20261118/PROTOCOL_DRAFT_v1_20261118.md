# Final-exam protocol: DRAFT (not frozen)

2026-11-18, Asia/Taipei. **Status: draft for the owner and the group. Nothing here is frozen, hashed or authorised to run.** The method's component list is deliberately **open** until the Saturday 21 November freeze; every place that depends on it is marked `OPEN`. Held-out pools belong to Codex as custodian; this draft uses only the sizes the owner has stated (held-out v2 76 tasks, Nav2 inspection 24, Nav2 read-then-act 10) and opens no custodian file. Development evidence quoted here is not a held-out result.

## 1. Purpose
A one-shot evaluation, written before any held-out task is run, that can support or refute the paper's claim. The contract's evaluation items (published baselines, strongest simple control, several models, frozen held-out tasks run once, multiple runs per task, confidence intervals, a robot that acts, ablations, one results log) are each given a concrete rule below. The claim itself, and which components the method has, are `OPEN`.

## 2. Systems (arms)
| id | system | status |
|---|---|---|
| S0 | original ROSA, verbatim prompt, stock executor and 47-tool menu | exists (dev run `s0_dev_20261116`) |
| E1 | strong ordinary baseline: stock executor, errors returned as text, better prompt that permits batching; batching use is reported | exists (`fairness_errors_as_text_20261117`) |
| F | Forge as released | dev run exists (`forge_baseline_20261115`); held-out feasibility unchecked |
| MT | MetaTool as released | not run; feasibility unchecked (contract item 3-4) |
| M | **the method** (steady loop plus the components chosen at the freeze) | `OPEN` |
| M-k | M with component k removed, one arm per component | `OPEN` (component list) |

Differences between systems that are not under test (prompt, executor, menu, error handling, interfaces) are listed in the report, not equalised (spec section 9 and the fairness decision).

## 3. Models and settings
Four models as in every dev study: `lfm3:1.7b`, `qwen3.5:9b`, `gpt-oss:20b`, `bonsai-2:4b`; digests recorded in a freeze file (dev digests are in `steady_loop_ablation_20261117/FREEZE.json`). Temperature 0.7, think false, num_ctx 65536, num_predict 4096, 40 iterations, 90 s HTTP and 900 s episode timeouts, 5 s oracle retry (amendment 4). `OPEN`: additional models (for example from the lab computer); any model added is added to **every** system. No model is dropped after results are seen.

## 4. Task pools and seeds
| pool | tasks | owner | notes |
|---|---:|---|---|
| held-out v2 (inspection and reads) | 76 | Codex | counts of task features are Codex's aggregate; task text stays with the custodian |
| Nav2 inspection | 24 | Nav2 teammate / Codex | unbuilt at the last state update |
| Nav2 read-then-act (robot acts) | 10 | Codex | `OPEN`: in or out of the paper (group decision before the freeze) |

- **Seeds:** `OPEN` between 2 and 3 per cell (sizing in section 8). Seeds are fixed in the manifest before the run; the same seeds for every system.
- **Run once.** Each cell is run once per system. A cell is re-run only if it is on the pre-declared infrastructure list: no model request was made (fixture, oracle, worker crash before the first request). The re-run uses the identical cell and is logged next to the original. A cell that made a model request is never re-run, whatever its outcome.
- **Scheduling:** one fixture session per (model, environment) with all systems and seeds of that session shuffled together under a master seed; one GPU/ROS job at a time.
- **No task, scenario, scorer rule, prompt or schema change after the first held-out request.** A legitimate protocol revision would be written, hashed and reported separately with its own results.
- Action tasks follow the spec: reset and stable-state check before each episode; a failed reset or residual motion invalidates the episode (recorded and re-run per the infrastructure rule), it is not an agent failure; success judged by an evaluator-side ground-truth reader, never shown to the model; "claims arrival but did not arrive" counted separately.

## 5. Metrics
- **Primary (correctness):** supported-complete using scorer v2.0 for inspection and reads and the custodian's frozen scorer for Nav2 inspection. Action tasks require independent final-state and truthful-answer checks plus [action judge v1.2](../action_dev_switch_20261118/judge_v1_2.py). Before exam use, freeze the per-step contracts and runner event capture with the custodian. Score actual dispatch and completion in order. For a read-derived goal, require a successful read from the bound source before dispatch and check that the command matches the recorded value under the frozen conversion. If calls were preselected together, record which results were available at selection.
- **Cost:** model requests, input tokens, output tokens, tool calls (native ROS operations) per episode and total. Wall-clock time is not a goal metric (contract).
- **Per model, always.** Every table has one row per model and a pooled row. The weak models dominate the unsupported cells and the long episodes, so a pooled number alone is not reported.
- **Totals with and without capped runs.** "Capped" = an episode that ended at the 40-iteration cap, a backend parse error (`ResponseError`, XML syntax), a worker or episode timeout, or any other ending with no answer object. Report cost totals and supported rates **with** all episodes and **without** capped ones, plus the number of capped episodes per model and system; a system must not look cheaper because its failures ended early, nor more expensive because one model looped (dev totals are dominated by a few bonsai episodes). The cap ending is read from `episode_end.answer` (the executor reports "Agent stopped due to max iterations." without an error).
- **Ending class** per system: accepted finish call, text answer, no answer (dev counts: 362 / 35 / 19 of 416 FULL-type episodes).
- **Harness exposure counters** per system: rejected calls, blocked write attempts (dev: 76 write attempts, 61 of them under the stock executor), repeated identical calls.
- **Confidence intervals:** 95% intervals by a **cluster bootstrap over tasks** (a task is the unit; its seeds and models travel with it), per model and pooled; paired differences between systems on the same cells. Cell-level binomial intervals are not used as the headline because tasks repeat across seeds and models.
- **Success criteria:** `OPEN`, to be written at the freeze. Candidate form (not adopted): the method is at least as correct as E1 within a margin delta and cheaper by at least x% in requests or tokens, per the pooled and per-model rows. Delta and x cannot be chosen smaller than the detectable effects in section 7.

## 6. Reporting rules
Every episode goes into one results log from the first run (append-only, run id, cell, system, model digest, seed, code revision, trace hash, scorer, outcome, cost, ending class). Negative results and failed cells are kept and reported. Held-out task text, answers, support lists and routes stay with the custodian; the report carries counts and aggregate tables only. Differences from the dev studies (new pools, new scorers for Nav2) are listed with their expected effect on interpretation. The conclusion is limited to what the experiment measures: these tasks, models and simulators, a development-to-held-out gap, and no claim about real robots.

## 7. Power note: what the dev noise lets us detect
Source: `power_inputs.py` and `power_inputs.json` in this folder (saved logs only). The same fixed loop was run six times on the same 40 development cells (pilot C1 x2 seeds, round-1 C1 x2 seeds, ablation FULL, compaction FULL):
- **Supported cells per run: 36, 32, 35, 35, 32, 35 of 40** (mean 34.2, SD 1.72 cells = 4.3 points). Two runs of the loop flip the supported flag of **15.8%** of cells (mean over run pairs), i.e. a per-cell variance of about 0.079, which reproduces the observed SD.
- **Requests per 40-cell run: 211, 218, 222, 264, 195, 311** (CV 18%); **tokens** CV 22%. The spread is driven by a few long bonsai episodes (the 311-request run has the same loop as the 195-request run). The per-cell log-ratio of requests between two runs of the same loop has an SD of 0.54.
- **Detectable effect (two arms, 80% power, two-sided 5%, normal approximation, cells treated as independent):**

| design (cells per arm) | supported rate | supported cells | requests (mean per-cell ratio) |
|---|---:|---:|---:|
| dev, 40 cells | 17.6 points (31.3 at worst-case noise) | about 7 of 40 | 27% |
| the finish-split run, 80 cells | 12.5 points | about 10 of 80 | 19% |
| one model, 110 tasks x 3 seeds = 330 | 6.1 points | | 8.7% |
| 4 models x 110 tasks x 1 seed = 440 | 5.3 points | | 7.5% |
| 4 models x 110 tasks x 3 seeds = 1,320 | 3.1 points (5.4 worst case) | | 4.3% |
| held-out v2 only, 4 x 76 x 3 = 912 | 3.7 points (6.6) | | 5.2% |
| Nav2 inspection, 4 x 24 x 3 = 288 | 6.6 points (11.7) | | 9.4% |
| Nav2 read-then-act, 4 x 10 x 3 = 120 | 10.2 points (18.1) | | 14.9% |

- **Reading.** (i) Differences of 3-4 cells of 40 in the dev studies are noise, as the team already treats them. (ii) The earlier finish-tool gap (-7 of 40, 17.5 points) sits at the dev detection limit; it is plausible but one run cannot confirm it. (iii) On the full held-out set a pooled difference of about 3-5 points in supported rate and about 4-5% in requests is detectable; per model the limit is about 6-11 points, so per-model claims need larger effects or more seeds. (iv) The 10 read-then-act tasks can only support a descriptive statement with a wide interval, not a significance claim. (v) These are lower bounds on the noise: they ignore task-by-system interaction, heavy tails and model differences, which the task-level bootstrap in section 5 captures and these figures do not. (vi) **A flag on the finish-split protocol:** its reading rule treats a gap of 6 or more of 80 as "separated", which is below the 10 of 80 this note says can be detected; its conclusions must therefore be read as patterns, not detections.

## 8. Sizing and cost (dev speeds, episode time only; planning figures, not measurements of held-out runs)
Mean episode wall time of the unchanged loop in dev: lfm3 30-33 s, qwen3.5 38 s, gpt-oss 49-53 s, bonsai 18-26 s (mean of the four about 35 s); stock ROSA arms are slower for qwen3.5 (52-58 s) and the full 48-tool menu slower for gpt-oss (76 s). One system over all three pools needs 4 models x 110 tasks = 440 episodes per seed, about 4.4 hours of episode time per seed (the Nav2 and action episodes may be slower; not measured). Options for `OPEN` decisions, with this per-seed figure:
| option | seeds | systems | episodes | hours (episode time) |
|---|---:|---|---:|---:|
| A | 3 | S0, E1, F, M | 5,280 | about 53 |
| B | 3 | S0, E1, F, M plus 4 ablation arms, all pools | 10,560 | about 106 |
| C | 2 | S0, E1, F, M on all pools; 4 ablation arms on held-out v2 only (304 cells per seed per arm) | 5,952 | about 60 |
MetaTool as released, if it can be run, adds one system to each row. The window between the freeze and the 2 December presentation is about 10 days; a second machine (lab computer) or fewer seeds may be needed. These are budget figures for the decision, not a recommendation.

## 9. Open decisions for the Saturday freeze (nothing below is decided)
1. Component list of the method and the ablation arms (the finish-tool split and the candidate counts of 2026-11-18 feed this).
2. Action tasks in or out; if in, the Nav2 read-then-act pool size and the judge.
3. Seeds (2 or 3), models added, ablations on which pools.
4. Success criteria (delta, x) given section 7.
5. Whether Forge and MetaTool "as released" can be run on the held-out pools and by whom; their exact versions.
6. The exact definition of "capped" for the with/without totals and who reviews the list.
7. How the custodian's pool hash, scorer hash and task-count manifest are recorded without exposing task content.
