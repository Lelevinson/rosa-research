# Frozen bounded AutoTool-family offline investigation

Frozen 2026-11-12 before fitting predictors or scoring any replay. The supplied
mission is adopted only within the user's explicit request and restrictions.
No OpenAI/paid inference, external task disclosure, ROS operation or model call
is authorized by this protocol. Offline programs read preserved files only.

## Preflight: Sections 12.2 and 14.2

1. Observed opportunity: surviving baseline model_end records and November11
   traces record real decision boundaries, structured receipts and final turns.
   We will enumerate rather than assume skip opportunities. STOP and multicalls
   are part of the denominator; a tool match is behavioral, not needed-action truth.
2. Mechanism: compare outcome-conditioned continuation (H1) and learned argument
   origin paths (H2), followed by complete-action risk/cost admission. Neither a
   confidence threshold, parameter flow nor fallback is new. Strong conditional
   frequency with identical features, binder and safety gates is decisive.
3. Increment unknown: candidate may distinguish source/schema changes and terminal
   contexts from tool-only prediction; equal-information conditional tables may
   duplicate those decisions. This is NOT YET JUSTIFIED for live execution.
4. Fairness: all offline predictors see the same public preceding decisions,
   receipts, status, schemas and request text. No evaluator answer maps, task IDs,
   expected fields or final answers enter prediction. All use the same safety
   filter. A/B are unexecuted ordinary-agent/composite controls; their existing
   native batching capability must not be replaced by a serial-only prompt.
5. New information: previous work did not implement these side-by-side boundary
   predictors, preserve grouped decisions, score canonical arguments plus STOP,
   or test both revisions. A finite replay and six adversarial families can decide
   whether a justified live contrast exists. Stop after these iterations if absent;
   do not launch another algorithm family or broad benchmark.

## Inputs, split and leakage

Use original primary-v1 November7 diagnostic traces: all turtlesim-only episodes
for training, all demo_nodes-only episodes for development, all mixed x1 episodes
for locked retrospective validation. Add November11 action-narration and coverage
primary traces as temporal transport validation, never training. Episode and
task-family groups remain intact. Activation/replay/oracle traces are excluded.
All these tasks were previously inspected/reused: NONE is a fresh prospective
held-out benchmark. The mixed family shares application components; report this
dependency rather than claim application-independent generalization. Preserve
input hashes and memberships before fitting. No outcome-driven retuning.

Primary parser: ordered model_end events; each tool_calls array is ONE decision.
Receipts after that event and strictly before the next model_start are observable
at the next boundary. Initial model decisions cannot be skipped; report them
separately. Missing completions, invalid tool calls and absent receipts stay
unknown, never manufactured STOP labels. A normal completed model response with
no calls is the only observed STOP. Truncated finals are unknown outcomes.
Canonical action is ordered [(tool, canonical JSON arguments), ...] or STOP.

## Frozen rules, controls and metrics

Minimum support 3, empirical probability threshold 0.90, one-sided Wilson lower
bound with z=1.645, candidate risk limit 0.05. These are design constants, not
calibrated guarantees. Tool ngrams k=1,2; strong conditional table uses last group,
public error status and schema fingerprint; constrained parent uses observed
successor frequency/support (embedding and domain adapters unavailable, explicitly
not a faithful reproduction). Candidate backoff selects the most specific supported
state; charge fitting, binding and policy time. H1/H2 and single-removal ablations
are diagnostic. Report complete-action behavioral agreement, STOP mistakes,
missed matches, missing/ambiguous/stale/unauthorized provenance, and all abstentions.
Do not estimate P(action needed) from behavior; unknown need => no auto-execution.
No forced STOP; STOP predictions hand off to LLM. No mutable evidence reuse.

Primary quality/cost claims remain unavailable offline: no full-answer causal
effect, saved tokens or latency benefit inferred from match counts. Report model
boundary upper bound, model timing when recorded, and measured offline overhead.
The useful upper bound cannot exceed noninitial tool-bearing model decisions;
last final-answer decisions are retained even after an automatic read.

## Adversarial development and stop rule

Six families: changed goal/STOP; success/error; equal-value different-source;
stale/text-only observation; list/composite equivalence; changed output schema.
Run initial H1/H2, revise origin ambiguity + schema/STOP handling, then revise
need-label identifiability + calibrated admission. Preserve initial failures and
all re-tests. Synthetic tests establish logic only, never real opportunity rates.

## Live gate and budget (conditional, not activated)

Require all mission F gates, especially a non-synthetic beneficial action contrast
against same-information C AND same-path B, public authorized current binding,
complete independent answer/order scoring and actual effective Qwen context.
If absent, write BLOCKER_AND_NEXT_DECISION.md and do not start ROSA/ROS/model setup.
If met, a separate frozen addendum must specify new tasks, thresholds, exact
deconflicted prompts and effective num_ctx before execution: max12 scored episodes,
10 model iterations,64 native reads,240s each, local Qwen only, isolated owned
fixture with before/after inventories and one cleanup. Writes, arbitrary services,
physical/production robots, forced final answers and evaluation oracle access
are prohibited. No new inference occurs merely to recheck known access.
