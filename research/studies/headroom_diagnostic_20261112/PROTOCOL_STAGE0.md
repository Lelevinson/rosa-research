# Stage 0 protocol: offline request-headroom analysis

Date: 2026-11-12. Scope: Stage 0 only (no inference, no ROS operation, no fixture). Stage 1 is **not** frozen or authorized here. Written before the label counts and tables were produced; the codebook, floors and rules below were fixed first, then applied. Post-hoc changes during review are listed in section 7.

## 1. Inputs

58 preserved primary traces (36 baseline, 12 action narration, 10 GPT coverage), the copies listed with SHA-256 in `research/_artifacts/autotool_iteration_20261112/INPUTS_FROZEN.json`. `extract_requests.py` verifies each hash before reading. One row per model request; 327 requests (baseline A 76, B 80, C 71 reproduce the prior baseline report).
Support judgments (supported-complete or not) are taken from the earlier studies, not re-scored: baseline `independent-judgments.json` (`strict_correct`), narration `INDEPENDENT_ANSWER_REVIEW.md`, coverage `evaluation_stdout.json` plus the independent ordering adjudication in the coverage REPORT section 4 (cells 04, 05, 07 fail). Baseline uses `strict_correct` (C 9/12), which differs from the report's conservative count (C 8 plus one indeterminate).

## 2. What the prompts actually allowed (F, checked in the traces)

| Corpus | System text about batching | Label used |
|---|---|---|
| Baseline A, B, C | Original ROSA text "NEVER call multiple tools in parallel ... Do not batch tool calls together" is present in all three arms. B and C append "Use independent tool calls together when possible." C adds `batch_reads`. | conflicted |
| Narration A, B, C; coverage A, B, V | The prohibition is absent. | deconflicted |

So baseline B and C are not deconflicted batching arms; their low batching is not evidence about the model's willingness. `batch_reads` appears 0 times in all 58 traces.

## 3. Floor (lower bound on model requests)

Floor = number of observation stages that must be separated by an observation + 1 final-answer request. Within a stage all calls whose arguments are already known are batched. Native cost is ignored. `strict`: argument strings must come verbatim from the task text or an earlier result (a full node name may be assembled from `Node name` + `Node namespace`). `alt`: allows one named shortcut.

| Task | Stages (strict) | strict | alt |
|---|---|---:|---:|
| t1 | {node_list, topic_list} then {param_list, topic_info(pose)} then {param_get background_r/g/b} | 4 | 3 (parameter names assumed known) |
| t2 | {node_list, service_list} then {service_info(clear, reset), param_get use_sim_time} | 3 | 3 |
| t3 | {node_list} then {node_info} (lists topics with types) | 3 | 3 |
| d1 | {topic_info(chatter), verbose names} then {param_get per endpoint} | 3 | 3 |
| d2 | {node_list} then {node_info of candidates} then {param_get on the server} | 4 | 3 (param_get over-fetched in parallel) |
| x1 | {node_list, topic_list} then {param_get x4, topic_info x2} | 3 | 3 |
| d1_recovery | {node_info retired_source alone, because the task says "first"} then {topic_info} then {param_get per endpoint} | 4 | 4 |

Checks: no episode is below its strict floor (0 of 58). A GPT trace reaches the floor on x1 (3 requests). The floor is a derived bound, not a proven minimum; a different valid route could be shorter.

## 4. Per-request features and labels

Codebook: `CODEBOOK.md` (labels JUDG, DEP, REC, ORD, FIN, RED, UNCLEAR as in the brief). Extra non-label columns: `batchable` (all string arguments were verbatim available at least one request earlier), `ready_request`, `own_call_error`, `designed_recovery`. First requests are not labeled. `label_requests.py` applies deterministic first-pass rules; `manual_labels.json` holds 17 manual overrides with reasons (about 6% of 269). ORD was never needed.

## 5. Blind check

A separate subagent that had not seen the primary labels relabeled a seeded random 20% (54 requests, seed 20261112) from `CODEBOOK.md` and the blind input only. Limitation: it had file tools and was instructed, not technically prevented, to read nothing else. Result in `RELABEL_AGREEMENT.md`.

## 6. Metrics

Excess = actual − strict floor, summed over episodes, reported for all episodes and for supported-complete episodes. Headroom = (DEP + RED) / labeled requests (with and without FIN). Adoption among opportunities = multi-call requests / (multi-call + single-call batchable requests). Tokens and seconds are descriptive.

## 7. Changes made while reviewing (disclosed)

1. The first rule set mislabeled selection requests as UNCLEAR and ignored failed calls; added a selection rule, the `own_call_error` column and manual overrides.
2. Rule (c) for RED (param_list when the parameter name is in the task text) was added after viewing the traces and affects 14 requests.
3. Narration/coverage results are repr strings with literal `\n`; normalised before parsing, which fixed false "guessed argument" flags.
4. Table 3 and Table 5 definitions were revised after a first look (adoption denominator; ranking by wasted input tokens instead of position).
No tasks, support judgments or floors were changed to improve any result.

## 8. Reproduce

```bash
D=research/studies/headroom_diagnostic_20261112
python3 $D/label_requests.py . $D          # labeled_requests.csv
python3 $D/summarize_stage0.py $D          # STAGE0_TABLES.md
python3 $D/compare_relabel.py $D           # RELABEL_AGREEMENT.md
```
`label_requests.py` reads the earlier baseline `independent-judgments.json` from the sibling checkout `../rosa-research-previous-20261108` (path in `research/.local/WORKSPACE_MAP.md`).
