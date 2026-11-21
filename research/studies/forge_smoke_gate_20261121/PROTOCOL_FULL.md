# Matched Forge pilot comparison: frozen before inference

2026-11-15, Asia/Taipei. The owner authorized the full run after the separately
retained thinking-on smoke. This protocol supersedes the smoke's two-cell cap
only for this new dataset. No held-out E2/E3/E3b inspection or inference.

## Preflight and question

1. Need: the pilot has 80 C1 episodes across four local models, but released
   Forge has not been measured under matched sampling. The two thinking-on
   smokes cannot answer this comparison. Preserve those as a separate dataset.
2. Mechanism: released WorkflowRunner on the same ordinary 12 read tools,
   plus released respond as terminal; no required steps or prerequisites.
   Closest control C1 uses ordinary strict argument/error handling and its
   own final-answer tool; A1 is the deconflicted-prompt stock executor.
   A bare-text answer may terminate C1 but trigger a released Forge retry.
   A correct early answer can therefore cost Forge more, a counterexample
   to assuming its guardrails improve efficiency.
3. No novelty is claimed by this baseline integration. Source-level parent
   mechanism comparison is FORGE_COMPARISON.md in the residual study. The
   closest negative snapshot replay shows why all input/output tokens and
   native work must be counted, not only requests. Raw behavioral comparison
   was absent from that source-only review; this is not a rerun of R1–28.
4. Fairness: exact pilot tasks, seeds, run count, context and generation cap;
   C1 system messages with only final_answer -> respond. Same ROS fixture,
   native guard and scripted change/reset hook, no application answer map.
   Historical controls rescored with the same frozen scorer, not fresh runs.
   Source support and complete answers precede cost interpretation.
5. Owner-authorized minimum full matrix: 4 models × 10 development tasks ×
   2 seeds = 80 attempts. Stop after these; no tuning, model-error reruns,
   default-budget extra arm, or independent thinking ablation. Results decide
   what behavioral differences exist on this pilot, not broad superiority.

## Frozen execution

- Models: lfm3:1.7b, qwen3.5:9b, gpt-oss:20b, bonsai-2:4b.
- Task/seed tuples extracted from the pilot's valid C1 rows, excluding the
  original INFRA_EXCLUDED.json entries, with unique-cell and hash checks.
  Each model has 8 Stage 3 cells (u3,p3,h4,v2 × seeds 1,2) and 12 E1h cells
  (six harm tasks × seeds 1,2). FULL_PLAN.json freezes deterministic shuffle
  seed `20261115-forge-matched-<model>-<env>` within each model/environment.
- 40 LLM calls including retries; release default validation, rescue,
  consecutive-error budgets, reasoning replay, step and termination logic.
  No changes to Forge-owned logic without an owner decision.
- TieredCompact(keep_recent=2), budget 65536, log every compaction.
- temperature .7, num_ctx 65536, num_predict 4096, assigned seed, explicit
  per-model think value copied from PILOT_TRANSPORT.json. Reconstruct the
  pilot SDK request offline from actual logical trace messages/schemas and
  unchanged factory. Historical raw HTTP bodies were not retained, so label
  this reconstruction. Confirm live outgoing field, context and returned
  thinking on the first real request/response of each model; audit every
  episode too. Save all unexpected thinking rather than suppressing it.
  Historical raw thinking is unavailable: absence in saved LangChain output
  is not proof it was absent on the wire, since reasoning=False skips capture.
- Only Ollama options and explicit think field differ from the released
  request. Use a thin HTTP transport, inherited send/parser unchanged.
- ROS domain 220, localhost only, same pilot fixture processes/interpreter,
  pre/post oracles, readiness, and cleanup checks. E1h scripted external
  parameter writes/resets are unchanged fixture behavior, not agent tools.
- 900 seconds per episode, 90 seconds HTTP timeout, 10-hour total wall cap
  as in the original pilot. No model-loading probe inference outside cells.
- Append attempt start before dispatch to ATTEMPTS_FULL.jsonl. Append every
  attempt outcome, including errors, to RESULTS_MATCHED.jsonl; raw traces
  live in a unique full_* directory under research/_artifacts/runs/forge_baseline_20261115/.
  Neither thinking-on smoke row enters the matched denominator. Preserve the
  original RESULTS_LOG.jsonl and copied RESULTS_THINKING_ON_SMOKE.jsonl.
- Same frozen scorer-v2.0 SHA256
  c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9.
  No changed answer or support rules. Respond string is final text under the
  existing last-object/unwrap rule. Tool exceptions do not count as support.
- Stop for wrong wire settings, wrong loaded context, unsafe native dispatch,
  failed fixture/oracle/reset/cleanup, or unavailable infrastructure. Repair
  infrastructure only while preserving attempts and without replaying a
  completed model cell; ask before modifying any Forge-owned logic.

## Analysis and limits

Report all assigned attempts, success/error/timeout counts, requests, token
input/output, native work and compaction, per model and same cell against
historical A1/C1 under scorer v2. Inspect 3–5 real Forge failures if available,
prioritizing disagreements, with original trace line numbers. Preserve
negative results and distinguish static fixture evidence, live local model
execution, reported historical outcomes, and scientific interpretation.

No confirmatory confidence claim from two seeds on development tasks, and no
claim of independent architectures for bonsai and Qwen (both Qwen family).
Prompt/schema/tool-terminal differences and distinct sessions remain limits.

Open question only, requested by owner: thinking-on Forge solved smoke p3
where historical thinking-off C1 failed. A separate thinking-on/off test may
be useful later. This observation is confounded and is not permission to run
that test, tune prompts, or mix smoke with matched results.

## Orchestration amendment after 53 recorded cells (no model rerun)

The parent driver inherited an extra smoke-only stop on any guard rejection.
A malformed read argument was safely rejected in cell 52; Forge recovered and
returned a supported answer. The parent then stopped. All owned nodes were
cleaned up. This was an orchestration stop, not a Forge abort or unsafe command
execution. Change only the parent to record such rejections and continue;
retain the unchanged native guard and stop on any actual write reaching ROS.
Resume only unrecorded cells in their original order, under the original
10-hour wall cap. Freeze the amended driver separately before those cells.
No parser, validation, retry, call budget, tool dispatch, terminal behavior,
prompt, sampling, fixture hook or scorer changes. Preserve the interrupted
session and its missing post-oracle rather than reconstructing it.

Validity observation, not a protocol change: cell 50's valid relative-name
parameter reads did not activate the unchanged hook's exact absolute-command
watch. The final read still observed the initial value. Retain its frozen
failure and record this missed scripted event separately from model errors.
Do not repair the hook, rerun the cell, or adjust the score during this matrix.
