# Merge plan: Martin's bounded macro + Levinson's method M (PLAN ONLY)

Written 2026-11-21 (Taipei) by Session B (Claude, AI) for Martin and Levinson. **Zero model calls, no Gazebo, no GPU, nothing implemented.**
Branch `member/martin-merge`, created from `origin/member/levinson` `2b1c790`. Nothing was pushed to his branches.
Reads: rosa-research `origin/member/levinson` 2b1c790 and `origin/member/martin` 8713f9b; rosa-contexts `origin/member/levinson` 87eb2bd (the same research files).
Held-out material: none was read. Only his public dev tasks, public reports and aggregate category counts were used.

**Labels.** **(F)** = read in code or a document at the cited file and line. **(R)** = reported by a teammate, not re-run by us. **(H)** = my inference.
Paths: `L:` = `rosa-research` on `origin/member/levinson`; `M:` = `rosa-research` on `origin/member/martin`.

## 0. Findings that change the plan (read first)

1. **His branch is an orphan snapshot (F).** `git rev-list --count origin/member/levinson` = 1; its `src/` and `tests/` equal base `18a5f2f` (`git diff --quiet 18a5f2f L -- src tests`). My branch has 6 commits on `18a5f2f`. So there is no history to merge. The port is a **file-level copy of new files onto his tree**. A `git merge` is not needed and not wanted.
2. **His method M cannot run from the published tree (F).** `L:research/studies/exam_arms_20261121/exam_arms.py:22-28` imports `ablation_arms`, `answer_gate`, `scorer_v2`. `L:.../action_arms.py:18-26` imports `fair_arms`, `run_pilot`. None of these files is in the tree (`git ls-files | grep` count = 0 for `ablation_arms`, `answer_gate`, `scorer_v2`, `run_ablation`, `fair_arms`; `run_pilot`, `harness` also absent). `namefix_rule.py` and `queue_core.py` are present. This follows the removal of held-out and lab content (commit message of 2b1c790). **Consequence:** the flag-off identity test and any live run need his private checkout. This is blocker B-1 for Levinson.
3. **My stack is mostly not needed (H).** His arms accept plain LangChain `StructuredTool` lists (`action_arms.py:66-68`, `:80-84`). So the merge does not need `MacroROSA`, `prompt_contract`, `terminal`, `rosa_backends`, `rosa_auth` or the fork's `rosa.py` change. The portable part is the **bundle policy** (read, conditional write, fresh verification), about 60-100 lines on top of his `ActionExecutor`.
4. **My named-skill catalogue does not fit his action tasks (F+H).** His turtlesim tasks use arbitrary headings (`L:research/studies/action_dev_switch_20261118/judge.py:8-22`, e.g. 1.0, -2.5, 4.0, 0.5 then 2.8). A fixed-target skill per task would be exactly the "per-task map" taboo (section 1). Only parameterized skills (option b) fit.
5. **The one thing the macro can save in his loop is small (H).** His dev action rows already show ~1.7 requests per episode (216 and 203 requests over 64 episodes per arm; `L:research/studies/action_dev_switch_20261118/REPORT.md:8-11`) and 0.66-0.84 verification reads per episode. The saving is bounded by those reads and the closing steps. This is the honest size to test. It is not my 40-48%.
6. **The macro's value is call efficiency only (F, owner rule).** His report-gate sizing found 0 contradictions in 128 dev action episodes (`L:research/studies/report_gate_sizing_20261121/REPORT.md:7`). We do not claim the macro catches false reports.

## 1. Governance check

### 1.1 Does adding the macro conflict with his frozen M or his exam?
- **M is frozen.** Four parts: short 12-tool menu, structured `final_answer`, errors as text with strict pre-check, answer name fix (`L:research/METHOD_SUMMARY.md:8-11`). Idea freeze done 2026-11-21 (`L:research/ACTIVE_STATE.md:43`). Ideas had to pass offline sizing by Saturday 12:00 or not enter (`ACTIVE_STATE.md:34`). The macro did not. **So it cannot enter M.**
- **Stage 1 freeze package:** Sunday freeze = Stage 1 only, both strata (`ACTIVE_STATE.md:44`). I touch nothing in `freeze_package_20261121/`.
- **Stage 2 (turtlesim actions) is not frozen.** Draft v3 line 43 calls it "next week", "run once under the frozen action protocol" (`L:research/studies/final_exam_draft_20261118/PROTOCOL_DRAFT_v3_20261121.md:43`). The shared typed action tool already exists as an extension "every eligible system receives" (`:22`).
- **Reading (H):** the macro fits as a **separately labelled arm of the action stage**, not a change to M. Two ways:

| Option | What | Effect on his frozen work | Risk |
|---|---|---|---|
| G1 | Separate labelled arm "XMM" (M + action tools, with the bundle replacing the single `rotate_to_heading` tool), in a **new** stage or tier | none to Stage 1 | needs Levinson's OK to add an arm to Stage 2 before its freeze |
| G2 | Separate study on public dev tasks only (signal), never in his exam | none | no held-out evidence for the merged method |
| G3 | Do not merge; joint paper with two strata (architecture C below) | none | no merged-method claim |

**Recommendation: G2 now (Sunday), G1 only if the signal passes and Levinson agrees before the Stage 2 freeze.** This is **a decision for Levinson** (D-L1).

### 1.2 His adapter rule, quoted
- Taboo: "Hand-written per-application or per-task answer/source maps ("adapters" that pre-solve tasks)." (`L:research/PAPER_GOAL_CONTRACT.md:37`)
- Hard constraint: "Do not require a handwritten per-task or per-application answer/source map inside the proposed **general** algorithm and then claim the method transfers to new applications. Ordinary interface adapters that connect to ROS/other frameworks are acceptable. Runtime metadata extracted from genuine tools/docs/observations is acceptable **if its collection cost, accuracy, and availability are accounted for**. Do not give the treatment semantic information that controls lack without an explicit fair accounting." (`rosa-contexts` `origin/member/levinson` 87eb2bd: `research/ROSA_RESEARCH_CONTEXT.md:84`; this file is not in the rosa-research snapshot.)
- Menu rule, item 3: "A deployment may separately authorize a narrowly constrained adapter or a verified service/type/argument allowlist, with explicit fallback and identical rights in every arm." (`L:research/decisions/2026-11-17-menu-coverage-and-rule.md:25`)
- His notes on me: whether my catalogue is such an adapter "is the owner's decision" (`L:research/teammates_20261121/martin.md:22`).
- Precedent that helps (F): his own typed tool is a **deployment policy** (tool name, field range, budget, deadlines) written once per robot, not per task (`L:research/studies/action_tool_s1_20261118/action_interface.py:33-41`, `turtlesim_backend.py:33-38`).

### 1.3 Options for the catalogue

| | (a) Named skills, disclosed as application configuration | (b) Parameterized skills | (c) Derived automatically from ROS interfaces |
|---|---|---|---|
| What | Today's `StateSkill`/`InspectionSkill` (`M:src/rosa_reliability/bounded_macro.py:30-48`, `capabilities.py:19-45`). Model picks `skill_id`. | One generic skill per action type, e.g. `rotate_verified(theta)`. Ranges come from his deployment policy. Model passes the number. | Build skills from message/action definitions at runtime. |
| Rule fit | **Weak.** Fixed targets pre-solve the tasks. Disclosure does not remove the taboo. Fits only if the owner explicitly allows it. | **Good.** Same kind of thing as his `DeploymentPolicy`. Nothing per task. | **Best on paper**, but ranges and meaning are not in interface definitions (his own caveat, `ROSA_RESEARCH_CONTEXT.md:84`, last sentences). |
| Fit to his tasks | None for headings (infinite targets). | Fits single, act-then-read and (if re-callable) two-step. | Unknown. |
| Changes my design | None | **Yes:** the model passes a number. I lose "model only picks an ID", and the checks move to range checks. | Large research question. |
| My existing evidence | **Stays relevant** (M4/G1/D are catalogue-based). | **Not transferable.** Needs its own stratum. | Not transferable. |

**Recommendation (H):** keep **(a) for my own evidence strata**, labelled "catalogue-configured", never pooled. Use **(b) for anything run with Levinson's method**. Treat **(c)** as future work. This keeps my existing evidence valid and avoids his taboo in the merged arm. **Decision for Martin and Levinson (D-M2, D-L2).**

### 1.4 His five-question preflight on "M + macro" (his section 12.2 rosa-contexts `ROSA_RESEARCH_CONTEXT.md:310-318`, and the five items of 14.2, `:384-392`)

| # | Question | Answer (labelled) |
|---|---|---|
| 1 | Novelty / closest ordinary mechanism | Closest ordinary mechanism: a fixed composite tool (batching/packaging). My own code says so: "a strong packaging reference, not a new selection algorithm" (`M:src/rosa_reliability/macro.py:1-5`). Closest of his: S1 guarded tool, MT supertool (plan echo, not executed), sweep completion. **No novelty claim** (his anti-loop rule, `PAPER_GOAL_CONTRACT.md:70-75`). Claim = integration plus evidence. |
| 2 | Observed need, honest denominator | Mine (F, reported in my own records): 40-48% fewer calls in mock/Gazebo, different tasks and tool surface. His setting: ~1.7 requests and 0.66-0.84 verification reads per dev action episode (`action_dev_switch_20261118/REPORT.md:8-11`). **Opportunity in his setting is not measured; upper bound only (H).** Offline sizing on his dev rows is the first step (section 6, step 1). |
| 3 | Concrete policy, discriminating trace | Control (XM): `rotate_to_heading` → `read_turtle_pose` → `final_answer` (3 requests). Macro arm: `rotate_verified(theta)` returns the verified pose → `final_answer` (2 requests). The only difference is the bundled read-write-verify. |
| 4 | Fair control, no hidden oracle | The control is his XM with **the same executor, policy, goal budget (3), deadlines, pose-read tool**. The bundle uses the same `ActionExecutor`. Stock arms (XS0, XE1) do **not** get the bundle, so they are reference rows, not controls. No task-specific data. The macro tool is treatment-only: report as a component test of M-with-actions. |
| 5 | Non-repeating next action | Not a repeat of MT/H7 (plan-first, 80-episode pilot: C1 65, M0 67, H7 32, `METHOD_SUMMARY.md:21`). Closest negative: **sweep completion** (request savings, whole-episode tokens -1.4%, native operations +7.8%, `METHOD_SUMMARY.md:27`; `decisions/2026-11-17-list-sweep-whole-cost.md`). So the plan counts native operations and tokens, not only calls. Stop rule in section 5. |

**Honest verdict (H): "M + macro" passes the preflight only as a narrow, separately labelled, opt-in diagnostic arm.** It is `BLOCKED / NOT YET JUSTIFIED` for major implementation until the offline sizing (step 1) shows an opportunity, per his fail-closed rule (`ROSA_RESEARCH_CONTEXT.md:394` (rosa-contexts)). It is not justified as a core method part.

## 2. Architecture options

### 2.1 The three options

| | **A′ Macro as an action tool inside the steady loop (one-tool swap)** | **B Macro replaces his guarded tool** | **C Keep separate** |
|---|---|---|---|
| Idea | His menu does inspection and answers. XM already has `rotate_to_heading` and `read_turtle_pose` (`action_arms.py:28-30`). The macro arm replaces `rotate_to_heading` with `rotate_verified(theta)`, a bundle built **on his executor**. | Drop S1/S2 and use my write path (`write_state` through a transport). | No code merge. Two strata, one paper. |
| Guard | His lock, budget, deadlines, cancel stay (`action_executor.py:49-75`, `:67`). | I would lose UNKNOWN_LOCKED and cancel: my path has no lock or cancel (F, `M:src/rosa_reliability/execution.py`: write failures raise `ControlledStop`, no cancel). | Both intact. |
| Control | XM (same tools minus the bundle) | none clean | n/a |
| Menu size | 15 names, same as XM (a swap, not an addition) | n/a | n/a |
| Effort | small | large, and weaker safety | none |
| Evidence value | a clean one-component comparison | confounded | two separate strata |

**Recommendation: A′, with C as the fallback.** **B is not recommended**: it removes his lock and cancel, which my code does not have.

### 2.2 Reconciliations (for A′)

| Topic | His | Mine | Proposal |
|---|---|---|---|
| **Terminal** | `final_answer` takes a JSON object and ends the episode (`exam_arms.py:59-69`; name fix applied there). | `submit_report(status, observation_id)` plus an accepted-report terminal (`M:terminal.py:30-48`, `reference.py:15-62`). | **One terminal: his `final_answer`.** Drop `submit_report` and the report gate in the merged arm. Reason: the gate is not shown useful (0 contradictions, `report_gate_sizing`), and two terminals would break his scorer (the name fix is applied only in `final_answer`). The bundle returns its own verification text instead. |
| **Errors** | Errors returned to the model as text with field, expected type and received value; strict pre-check (`METHOD_SUMMARY.md:10`; `exam_arms.py:44-52`). | `session.feedback` raises `ToolException` with JSON `{code, details, rejected, corrections_remaining}`, and **ends the episode after 3 corrections** via `ControlledStop` (`M:execution.py:105-116`). | Route all bundle rejections through his soft-error text. Do not use my correction budget to end episodes (his arms have no such stop). Keep my codes as the **text content**, so evidence stays readable. Report any ControlledStop-like ending as its own class. |
| **Write block** | C1 blocks write tools; the typed action tool is the only way to move the robot (`action_arms.py:9`; stock write paths blocked by `guarded_native`). | One write per invocation, validated against a registered target (`bounded_macro.py:60-82`). | The bundle's only write is a call to his `ActionExecutor.execute`. It counts against his goal budget (3). My "one write per bundle call" stays as an inner bound. **Open (D-M3):** my "select once per task" rule breaks his two-step tasks (M1-M3). Allow several bundle calls per episode, each within the goal budget? This is a design change, so it needs your decision. |
| **Menu size and wording** | 12 read tools + finish; stock tool schemas cost about 58-105 tokens each (`METHOD_SUMMARY.md:8`: 35 schemas = 2,029-3,666 tokens). | Five tools in a fixed prompt contract (`prompt_contract.py:13-49`). | A′ adds no tool (swap). Use his prompt unchanged except one tool description. **Do not port my five-tool prompt contract** (it replaces ROSA's generic prefix and is incompatible with M's prompt). |
| **Model families** | Core: lfm3:1.7b, qwen3.5:9b, gpt-oss:20b, bonsai-2:4b. Extras checked: gemma4:e4b, granite4.2:8b, llama3.1:8b, ministral-3:8b (`MODEL_DIGESTS_DRAFT.json`; `PROTOCOL_DRAFT_v3:48`). Temperature 0.7, num_ctx 65536, num_predict 4096, 40 iterations. | G1 settings: temperature 0, num_ctx 8192, seed 42; backends in `rosa_backends` (Ollama + hosted OAuth). | Use **his** settings and **his** model plumbing. Do not port `rosa_backends` or `rosa_auth` (his `rosa-llm` package already covers OAuth/Ollama, `L:AGENTS.md:56-62`; `rosa_auth` is protected). |

### 2.3 What his models need (native-schema-v1 coverage)
- `native-schema-v1` has guidance only for `llama3.1` and `granite3.3` (`M:src/rosa_backends/tool_contract_ollama.py:12-14`) and skips other families (`:35`). Levinson's notes say it "rejects our four model families" (`martin.md:38`).
- **His four core models need no native-schema profile (H):** they emitted structured tool calls through his own loop. His extras: structured calls were emitted by gemma4, granite4.2, llama3.1, ministral-3 with open defects listed in his prep report (`PROTOCOL_DRAFT_v3:141`), which I did not read in full.
- **granite4.2 is a different family from my granite3.3 (F):** my PA-1 sentence is IBM's granite3.3 template. Do not reuse it for granite4.2 without checking IBM's own template (H, open).
- **gpt-oss uses its own format and wrapped answers** (`stage2_prep_20261121/REPORT.md` section 1: judge v1.2 fails on wrapped structured answers; `judge_exam.py` normalizes). The bundle must return plain text so it adds no new wrapping.
- **Recommendation:** the merged arm uses no model-specific profile, and it is tested on his four core models only. Granite/Llama stay in my own strata.

## 3. Code merge (rosa-research)

### 3.1 Base difference and conflicts
Base `18a5f2f` (2026-10-20). Files changed on **both** sides: `.gitignore`, `README.md`, `pyproject.toml`, `uv.lock` (F, `git diff --name-only`). Only mine: `src/rosa/rosa.py`, `src/rosa/tools/__init__.py`, all of `src/rosa_*`, `tests/` additions, `docs/`, `scripts/`, root `*.md`. Only his: `AGENTS.md`, `docs/START_HERE.md`, `research/`.

| File | Conflict | Plan |
|---|---|---|
| `pyproject.toml`, `uv.lock` | Real. Mine adds the `siwc` group (`pyjwt`); his adds `rosa-llm[langchain]==0.1.0` (which brings `pyjwt`). | **Do not take mine.** The minimal port needs no new dependency. |
| `.gitignore` | Real (`docs` vs `docs/*` + exception; mine adds `.venv-*/`). | Keep his. |
| `README.md` | Real. | Keep his; add one pointer line only if approved. |
| `src/rosa/rosa.py`, `src/rosa/tools/__init__.py` | None (he did not change them). Mine adds `load_default_tools`, `tool_names`. | **Do not port.** Needed only by `MacroROSA`, which is out. This also keeps his baseline ROSA byte-identical (his AGENTS.md forbids changing the baseline checkout). |
| Root `*.md`, `docs/`, `scripts/` | Name clashes with his `docs/START_HERE.md` only. | Out. |

### 3.2 Minimal port (new files only)

| Port | Source | Why |
|---|---|---|
| **New:** `research/studies/macro_action_20261122/macro_action.py` | rewritten from the policy in `M:macro.py:15-41` and `workflow.py:100-132` | the bundle: read pose → if outside tolerance, `ActionExecutor.execute` once → read pose again → return verification. No replay. Written for his executor, not copied class-for-class. |
| **New:** `.../macro_arms.py` (`ActionMM`) | pattern of `action_arms.py:71-84` | the arm with the flag. Subclasses his arm; his files are not edited. |
| **New:** tests, protocol, freeze | his study layout (`PROTOCOL.md`, `FREEZE.json`, `make_freeze.py`) | same style |
| Maybe port | `M:execution.py` `OperationBudget` pattern | only if a native-operation count is needed. His executor already records events. Prefer his counters. |

**Stay out:** `rosa_auth/` (protected, never merged), the Sol OAuth path (`rosa_backends/chat_siwc.py`, `rosa_auth`), `rosa_backends/` (his `rosa-llm` replaces it), `capability_demo.py`, `gazebo_demo.py`, `ur5e_macro_demo.py`, `macro_demo.py`, `sim/`, `prompt_contract.py`, `terminal.py`, `completion.py`, `macro_agent.py`, `capabilities.py`, `reference.py` (the report-gate path), all my tests. They stay in `member/martin`.

### 3.3 Flag and the flag-off proof
- **Flag:** a new arm id (`XMM`) and one environment variable or spec field, `macro_action=true`. Default off. With it off, `make_arm` for `XM`, `XS0`, `XE1`, `M` is called exactly as today. My files are not imported on his paths unless the flag is on (lazy import).
- **No edits to his frozen files.** The new arm registers at run time like his own launcher does (`run_actions_queue.py`, `action_systems.py`). His own report says `systems.py` is in the frozen file list (`stage2_prep_20261121/REPORT.md` intro).
- **Test that proves identity (3 layers):**
  1. His own tests, unchanged: 19 executor tests, 7 turtlesim-backend tests (need ROS), 10 `test_exam_actions.py`, `test_exam_arms.py`, `test_queue.py`. Same counts as his reports.
  2. **No-diff hash check.** Before any change, record from his private checkout, for each of `M`, `XM`, `XS0`, `XE1`: SHA-256 of (system prompt text, tool names, descriptions and JSON schemas in order). His dev rows already store `prompt_hash` and `tools_hash` per episode (e.g. `RESULTS_LOG.jsonl` row 1 in `action_dev_switch_20261118`), and his test suite checks schema equality across systems. After the port, with the flag off, recompute and require **byte-identical** hashes.
  3. **File-level no-diff:** `git diff --stat` of the merge branch against `2b1c790` must list **only new files** under `research/studies/macro_action_20261122/` and `research/merge_martin_20261122/`. Any modified file fails the check.
- This needs blocker B-1 (his private modules) for layers 1-2. Layer 3 and the hash recorder can be written now.

## 4. His tasks after the merge (public dev descriptions and reports only)

### 4.1 Which tasks can be expressed
Source: public dev tasks `judge.py:8-22` and aggregate category counts (5 single, 4 act-then-read, 4 two-step, 1 refusal turtlesim; 10 Nav2 read-then-act, "from wording and design cues", `action_readiness_20261121/REPORT.md` row "Held-out turtlesim", `PROTOCOL_DRAFT_v3:56`). **I did not see any held-out task; the held-out mapping is for Levinson to do privately (4.3).**

| Task type (dev examples) | Expressible with a parameterized macro? | Skill to register / note |
|---|---|---|
| Single rotate (S1, S2) | Yes | `rotate_verified(theta)`; range from `TURTLESIM_POLICY` ([-π, π]) |
| Out-of-range target (S3: 4.0 rad) | Yes, same as control: the executor rejects; model must normalize | no change; do not add normalization in the bundle (would give the treatment extra help; fair-accounting rule) |
| Act then read (R1: read a parameter, divide, rotate; R2: rotate, then read x, y) | Yes | the parameter read stays a menu tool (`ros2_param_get`); the pose read stays `read_turtle_pose` |
| Two-step (M1, M2) | **Only if the bundle is re-callable** (D-M3) | each call is one bundle |
| Relative turn (M3: "a further 1.5 rad ccw from where it ended") | Only if re-callable, and the model must read the heading first | model computes the new absolute heading |
| Refusal task (1 in the pool) | Neutral (the model should not act) | no skill; check the bundle is not called |
| Continuous rotation, velocity commands, spirals, pen/teleport | **No** | no registered action; also not in his policy |
| Nav2 `navigate_to_pose(x, y, yaw)` single goal | Possible later | needs a Nav2 backend with lifecycle/TF readiness and cancel, which does not exist (`action_readiness_20261121/REPORT.md`, Nav2 row: "no runner, no judge, no S1 backend") |
| Nav2 multi-waypoint, replanning, mid-route cancel, goals derived from several reads | **No** | not a single bundle |

**Result:** after the merge, turtlesim single, act-then-read and (with D-M3) two-step tasks fit; Nav2 does not fit this weekend and is out of the signal check.

### 4.2 Skills to register (option b)
Only one for turtlesim: `rotate_verified` with field `theta` in [-π, π], tolerance, and his deadlines. Nothing per task. Nav2 later: `navigate_verified(x, y, yaw)`. Both reuse his `DeploymentPolicy`.

### 4.3 Checklist for Levinson (to run privately on the held-out pool; do not share results with me except as counts)
1. **Menu coverage:** for each action task, can it be completed with `rotate_verified` + the 12 read tools + `read_turtle_pose` + `final_answer`? Record counts per category only. Compare with the XM witness.
2. **Task validity:** no task needs a motion type outside the policy field range; the refusal task still has a correct refusal path; no task depends on a registered target.
3. **Scorer compatibility:** judge v1.2 through `judge_exam` reads the macro arm's trace (dispatch events and `action_call` events must exist). "Dispatch before required read" rule: the bundle's internal pose read must be recorded as a read event, or the judge's read-before-dispatch check (`judge_v1_2.verify_sequence`) will mark every macro episode invalid. **Highest risk; check first.** Also the ground-truth reader stays independent of the bundle.
4. **Safety guards:** a macro call cannot exceed goal budget 3; LOCKED persists after an unresolved goal and the bundle never retries or unlocks; ack deadline, 15 s execution deadline, cancel settlement unchanged; stock write paths still blocked; the bundle cannot send a goal when `readiness()` fails.
5. **Class rules:** the new endings (bundle rejected, bundle not called) map onto his classes (a)-(c).
6. **Equal treatment:** no extra information reaches the macro arm (same prompt, same policy, same state access).
7. **Hash check:** flag-off hashes equal the frozen ones.

## 5. Evaluation plan

### 5.1 Signal-level on the laptop (small, honest)
- **Tasks:** his 8 **public dev** action tasks (S1-S3, R1, R2, M1-M3). Dev only, so no claim.
- **Arms:** XM (control) vs XMM (bundle). References only, not controls: XS0 and XE1 if his harness runs them cheaply (they already exist in `action_arms.py`; XS0 is original ROSA with the same two tools plus the stock 47 tools). "Original ROSA where his harness supports it" = XS0.
- **Models:** qwen3.5:9b first (his and my main model). Then bonsai-2:4b and lfm3:1.7b if time allows. gpt-oss:20b is too heavy for 6 GB partial offload (H).
- **Size:** 8 tasks × 2 arms × 2 seeds × 1 model = **32 episodes** per model. Three models = 96.
- **Pre-registered reading (set before any run; frozen with a hash):**
  - **Good signal:** per model, success is not lower than control by more than 1 episode of 16 paired; matched-success requests are **≥ 25% lower**; bundle adoption (macro tool called when a rotation is needed) **≥ 80%**; 0 goal-budget, lock or write-path violations; native operations and tokens **not higher by more than 10%** (sweep-completion lesson).
  - **Bad signal:** success lower by ≥ 2 of 16 in any model; or requests not lower; or adoption < 50%; or any guard violation; or the judge cannot read the traces (then it is a wiring failure, not a result).
  - **In between:** report as no evidence; do not go to paper scale on it.
- **Reporting:** descriptive. Per model, never pooled across models. Cost counts: requests, tokens, native operations, verification reads. Failures kept.
- **No pooling** with my M4, G1, D, F1 or parity results, or with his past results. Separate stratum ids: `merge-signal-20261122`.

### 5.2 Paper scale on the lab (Monday onward)
- **Arms:** M (his existing), XM, XMM, plus XS0/XE1 where he runs them; optionally my primitives-mode control later.
- **Style:** reuse his frozen-protocol style: spec JSON generated by a script, `FREEZE.json` with hashes, version guard, append-only results log, frozen analysis with task-clustered bootstrap (`freeze_package_20261121/analyze_primary.py`), one run per cell, ending classes, GPU-state rows.
- **Adding the arm without touching Stage 1:** a **new** spec and a new tier/stage (e.g. "A-MM"), a new run name, a new freeze file. Stage 1's `exam_spec_stage1.json` and its hashes are never opened for writing. The arm would join **Stage 2** only if Levinson agrees (D-L1) and **before** Stage 2's freeze, with its own pre-registered comparison (XMM vs XM, paired by task and model, bootstrap over tasks). One held-out run only; no tuning on held-out results.
- **Strata:** lab results are their own stratum. Laptop signal results are never pooled with lab results (his own rule, `ACTIVE_STATE.md:44`).
- **Stop rule:** if the signal check is "bad" or "in between", do not add the arm to Stage 2. Report the signal result as an honest negative.

## 6. Sunday work list (after approval; correctness first)

Prerequisite on every step: **no GPU or model call until `STATUS.md` shows Session A's chain finished.** Scripted checks can run any time. Estimates are mine and assume steady work; add slack.

| # | Step | Verification after the step | Est. |
|---|---|---|---|
| 0 | Read `STATUS.md`; fetch refs; confirm decisions D-L1, D-M1 to D-M3 are answered. **STOP POINT 1.** | Written answers on file in this folder | 0.5 h |
| 1 | **Offline sizing** of the bundleable share on his dev rows (`RESULTS_LOG.jsonl`: `tool_calls`, `requests`, `verification_calls`, `rotate_results`). Count episodes where a rotate is followed by a pose read, and the requests that a bundle would remove. Protocol frozen before the script. | Counts reproduce his reported 216/203 requests and 54/42 verification calls. Report the upper bound. **STOP POINT 2:** if the upper bound is below 10% of requests, stop and report. | 1.5 h |
| 2 | Get his private modules or a read-only copy of his working tree (B-1). Set up a **separate** uv environment (his rule: no installs into the project env). Run his existing tests. | Executor 19 pass, backend 7 pass (ROS), `test_exam_actions` 10 pass; counts equal his reports | 1.5 h |
| 3 | **Record golden hashes** (prompt, tools JSON) for `M`, `XM`, `XS0`, `XE1` **before editing anything**. | Hashes equal the `prompt_hash` and `tools_hash` in his dev rows where the setups match; otherwise record why | 1 h |
| 4 | Write the signal protocol, the pre-registered reading (section 5.1) and `FREEZE.json`. | Hash file; `git diff --stat` shows only new files. **STOP POINT 3 (Martin and Levinson read the protocol).** | 1.5 h |
| 5 | Implement `macro_action.py` on his `ActionExecutor`. Tests against his `fake_backend.py`: success; already at goal (no write); pose unavailable (no write); `NOT_READY`; `REJECTED` out of range; `LOCKED` after unresolved goal; budget shared with direct calls; **never replays**; ack lost; rejection text passes through soft errors. | All new tests pass; his 19 executor tests still pass unchanged | 3 h |
| 6 | Implement `macro_arms.py` (`ActionMM`) and the run-time registration. Tests: menu equals XM's except one tool; schema and policy identical elsewhere; flag-off creates XM/XS0/XE1/M **unchanged**. | **Flag-off identity check:** golden hashes byte-identical; `git diff --stat` vs `2b1c790` lists only new files. **STOP POINT 4:** a failure here ends the work until understood. | 2 h |
| 7 | Scripted dry run: a fake chat model with scripted tool calls through XM and XMM against the fake robot; trace through `judge_exam`. **0 real model calls.** | Judge verdicts equal expected on all 8 dev tasks; macro traces pass `verify_sequence` (checklist item 3) | 2 h |
| 8 | Check `STATUS.md`: is Session A's chain done? If not, wait; do not start the GPU. | STATUS entry present | — |
| 9 | **Live smoke** (after the chain): 2 dev tasks (S3, R1) × qwen3.5:9b × XM/XMM, seed 1, as his own smoke did. Deterministic repeat once. | Rows have GPU state and no infra class; both arms run; judge reads both; hashes of prompt/tools match the dry run | 1 h |
| 10 | **Signal run** per the frozen reading, qwen3.5:9b first. | Per section 5.1, counts and the pre-registered reading applied literally. **STOP POINT 5:** good/bad/in-between decided by the rule, then Martin and Levinson decide paper scale. | 3-4 h per model |

Total scripted work (steps 0-7): about **13 h**; live (9-10): about **4-5 h** for one model. Realistically, Sunday fits steps 0-7 and maybe the smoke. The signal run for three models may slip to Monday. That is acceptable: paper-scale testing is on the lab anyway.

## 7. Decisions needed

**For Levinson**
- **D-L1:** May the macro enter as a separately labelled arm (XMM) in a new stage and, if the signal is good, in Stage 2 before its freeze? M and Stage 1 stay untouched. *Recommend yes, with the stop rule in 5.2.* Reason: it respects his freeze and gives a clean one-component test.
- **D-L2:** Is a parameterized skill (option b, deployment-policy style) acceptable under the adapter rule, and are named skills (a) disallowed in the merged arm? *Recommend: b allowed, a not used.* Reason: (b) is the same kind of object as his `DeploymentPolicy`.
- **D-L3 (blocker B-1):** Provide a read-only copy of the missing modules (`run_pilot`, `fair_arms`, `ablation_arms`, `answer_gate`, `scorer_v2`, `harness`) or run steps 2-3 yourself. *Recommend: you run the hash recorder script I write.* Reason: the held-out boundary stays his.
- **D-L4:** Is the judge's read-before-dispatch rule satisfied by a bundle-internal pose read? If not, the macro arm cannot be scored fairly. *Recommend: decide before step 6.*

**For Martin**
- **D-M1:** Approve the architecture A′ (one-tool swap) with C as fallback. *Recommend yes.* Reason: only A′ keeps his lock and cancel and gives a one-component test.
- **D-M2:** Accept that merged evidence uses option (b) and is a **new stratum** that does not reuse my M4/G1/D evidence. *Recommend yes.* Reason: that evidence is catalogue-based.
- **D-M3:** Allow the bundle to be called more than once per episode (my "select once" rule changes). *Recommend yes, each call inside his goal budget.* Reason: his two-step tasks need it; without it the macro cannot be tested on 3 of 8 dev tasks.
- **D-M4:** Drop `submit_report` and the report gate in the merged arm; the claim is call efficiency only. *Recommend yes.* Reason: 0 contradictions in his 128 dev action episodes; two terminals would break his scorer.
- **D-M5:** Approve live use of the laptop GPU only after Session A's chain has finished. *Recommend yes.*

## 8. Limits and open items
- I read his public files only. Items not read in full: `PROTOCOL_DRAFT_v3` beyond the cited sections, `exam_prep_20261121/REPORT.md`, `queue_core.py`, `judge_v1_2.py` internals. Claims about them come from his reports (R).
- The M core modules are absent, so every statement about how M composes its tools rests on `exam_arms.py` and `action_arms.py` (F) and not on running them.
- My efficiency evidence (40-48%) is from my own harness and tool surface (R from my own records). It is not evidence for his setting.
- The bounded numbers for his loop are from his dev rows (R: not rerun here). The offline sizing in step 1 will replace the estimate in section 0.5.
- Nothing here is a result. No novelty claim is made.
