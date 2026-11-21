# Codex assignment — ROSA model-action output cost, after native-read study

**Purpose:** The next *single* decision-changing engineering/research iteration. This is not a request for another broad audit, a new name, or a 22-cell baseline rerun. Own implementation and skeptical comparison within the gates below. Code and detailed reporting in English; findings for the user in Indonesian.

## Exact inputs and continuity

Read the **current local** `ROSA_RESEARCH_CONTEXT.md` sections 0, 1–4, 5, 12, 14, and the native-read study's newest additive context entry; `research/native_read_investigation_20261111/{REPORT.md,PROTOCOL.md,DECISION_LEDGER.md}` and its original raw evidence; R24 code/report; `src/rosa/{prompts.py,rosa.py}`; actual `rosa-llm`/`ChatOllama` installed model invocation; original code and prompts for baseline A/B/C; the four-method `TECHNICAL_RESEARCH_REPORT.md` supplied with this assignment and `model_turn_costs_replay.json`. Do not overwrite `AGENTS.md`, rewrite history, or assume the Git state matches a report; inspect it first. The local user controls real ROSA/WSL execution; this ChatGPT has not run ROS or model inference.

### Preverified observations that motivated this assignment

- Native study: serial fixed list operation 8.4121s, fixed4 2.5780s, AIMD 4.5607s, on 24 batches/96 CLI reads; only ~27.234s optimistic saved latency / 2,805.873s original trace event spans (0.9706%) for multi-entity lists. Reused service-graph observer 0.036736s versus 11.419331s for 32 service-type reads in warm local fixture, no model calls. Do not re-run or recast these as algorithmic wins.
- Original 36 primary diagnostic episodes have 227 `model_end` events and 1,585,055 input / 27,132 output tokens. An independently reproducible read-only audit finds 2,304.56s output token generation, 222.12s prefill, 9.481s load and 2,541.785s model total. 191 model turns issue tool calls; 174 of them also include 5,955 surface words of prose. This is **not** evidence that prose deletion preserves semantic correctness.
- Predecision model-turn states in the same archive: initial 36 tool calls, after tool results without recorded native failure 148 tool calls + 36 final answers, after failure seven tool calls. An error state exists, but an arbitrary post-tool-result turn can still be the final answer. Do not force a tool call from state alone.
- Old `rosa/prompts.py` explicitly says *never batch tool calls*. A valid new strong baseline must replace this instruction and verify that actual model/runtime batch execution works. Historic B/C prompts did not contain a decisive action-prose suppression comparison; do not call them that control.

## Scientific question

**Q1.** Against a deconflicted strong ROSA agent, does a fixed, minimal *action-only narration* instruction reduce generated tokens and actual model/episode latency while preserving complete source-supported answers?

**Q2.** **Only if Q1 is positive**, can a dynamic framework mode based on public tool-result errors and validation states improve the cost/quality trade-off beyond *both* a fixed terse prompt and a fixed conditional prompt that already describes how to behave after errors? If there is no unique improvement over the ordinary static conditional instruction, there is no algorithmic delta and the task stops with an honest systems result.

**Q3.** What does this imply for the locked framework-level research objective, given the already measured small native latency and existing grammar/effort-control prior art?

The candidate is not selected. This mission tests whether there is an **actual incremental policy** after an evidence-backed initial action-cost signal. Do not implement a new output decoder, model training or code-generation language merely to manufacture a distinct result.

## Controls and conditional implementation

All arms must use exactly the same local model name/checkpoint/version/settings, tool registry/schemas, ROS fixture and data, access permissions, retry budgets, max iteration/time limits, full task wording, answer scorer, tools' raw outputs, and allowed effects. Freeze and record differences in messages/invocation configuration; do not give one arm extra domain hints or manually prepared field-to-source maps. The historical original ROSA is *descriptive*, not decisive.

**A — Strong ordinary ROSA.** Remove—not append to—contradictory default sequential/no-batching messages and replace them with safety-scoped instructions allowing independent read-only tool calls together, preserving proper dependencies and strict sequencing of writes. Activate supported list-valued tool args; confirm via at least one real trace. Do not grant special semantic knowledge or change final-answer obligations.

**B — Strong ordinary ROSA + fixed terse action instruction.** Identical to A, plus a **static** instruction that when tool calls are made, they should be issued with no unnecessary natural-language preamble; when answering the user, all requested fields, source distinctions, uncertainty and correctness obligations remain. Never post-hoc remove prose and count that as generation saved.

**C — Strong ordinary ROSA + fixed *conditional* instruction.** Identical to A, plus one static instruction to be terse on ordinary tool calls and allow short error explanation when a prior tool failed; require complete final answers. This is a hostile comparison that may match a dynamic controller. **No privileged tool outcomes beyond the ordinary transcript.**

**D — Optional dynamic mode-selection candidate, after gate below.** The framework reads its own event status (`initial`, `success`, `tool_failure`, `invalid_tool_call`, `timeout`) and selects compact instruction in normal states or repair-capable instruction after errors. The model still decides action/final and actual tool arguments in the same request; same tool schemas and history; all errors and extra calls charged. Do **not** use forced `tool_choice=required`, truncate the response globally, or conflate `reasoning=False` with `think` unless the installed model advertises and proves its mode support. **Do not** turn on JSON-schema constrained outputs together with native tools without explicit compatibility verification; 2026 research reports tool suppression.

**Preimplementation discriminant gate for D:** Write two concrete sample model invocation envelopes (same conversation/tools, one after success, one after actual tool error) where D sends a different *effective* model instruction/config from A/B/C, and explain why C's static conditional instruction should not already achieve the same behavior. If this cannot be defended, run **A vs B vs C only**, state there is no supported adaptive contribution, and stop D. This is not another open-ended feasibility audit; it is an immediate design firewall before speculative code.

If a dynamic candidate is implemented, preserve original ROSA as the default and make it opt-in in a small model-call integration wrapper. Do not change how LangChain tool-call IDs, scratchpad histories, Python callbacks, authorization, failure statuses or final answer output are correlated. Unit-test action and final turns separately.

## Frozen experiment stages and scope

1. **Source/invocation fact check, before expensive trials:** show actual ROSA model API and version; distinguish tool-call assistant prose from hidden reasoning fields; validate `max_tokens` / Ollama `think` controls only if used; ensure native tool-call outputs remain parseable; list original sequential prompts removed; verify all arms can issue parallel independent requests. The fix for an incompatible installed model or provider must not be retroactively tuned using held-out outcomes.
2. **Small stage 1, no large benchmark:** use four *predeclared development tasks* from saved diagnostic tasks, including at least one source-confusion task and one native error-recovery scenario. Run A/B/C in randomized orders, one seed each (12 episodes), no semantic task maps. Save full events and independently evaluate source-supported complete answers. If B/C neither save decode time nor preserve quality, stop. If B and C tie and D has no grounded unique action difference, stop D. Do not silently modify the tasks after looking at results.
3. **Conditional candidate stage:** if B/C demonstrate a positive, correctness-preserving signal **and** the D gate passes, implement D with a frozen, explicit state rule and run on the *same development tasks* under identical budgets. A false/absent error signal is an explicit failure mode. Do not tune an adaptive threshold on the held-out set.
4. **Prospective evaluation only if stage 1 justifies:** freeze a new **held-out** cross-application task set (at least eight tasks with different services/source distinctions, some complete and some unavailable). Score every requested field, semantics of observed/configured values, source identity, missing fields, hallucinations, safety/side effects, and overall supported answer. Evaluate the actual best simple control(s) versus candidate; report task-wise paired outcomes, not just aggregate accuracy. Any further replicates must have a predeclared budget and preserve all failures. A small run is exploratory, not a statistical noninferiority proof.

**Explicit no-go conditions:** incompatible model-native tool formatting; request/response histories not equivalent across arms; candidate cannot preserve final answers; new invalid or unauthorized operations; tool-call acceptance rate collapses; error- or late-stage facts lost; D duplicates C in decisions/cost; only a weak original sequential prompt is beaten. Do not respond by inventing per-task adapters or a fifth arm just to get a win. Count all failed attempts and extra model retries.

## Metrics and preservation

- Report per episode: strict complete/correct supported answer; per-field coverage; false-source selections; tool-action and final turn counts; response `content` words; successful tool call rate; attempted and observed underlying ROS read/write counts; `model_end` token and Ollama `total_duration`, `eval_duration`, `prompt_eval_duration`, `load_duration`; prompt token counts; end-to-end wall time; policy/serialization overhead and all repair/retry calls.
- Frozen scoring protocol **must** not be provided as a task→source map to the runtime. Complete answer scorer operates after the agent outputs, and its construction/checks are recorded independently; use actual ground-truth snapshots and preserve ambiguity rather than forcing unanswerable fields.
- Prompt and tool parity must be verifiable from saved per-invocation messages, schema hashes, and actual results. Log the exact system-prompt change in each arm and prove prompt-level batching prohibition was removed, not contradicted by appending another message.
- Save raw traces, arguments, statuses, model metadata, scorer and case definitions, versions/hashes, a manifest, and diagnostic failures under `research/_artifacts/` or another durable ignored path; second persistent backup; no sole `/tmp`; no hidden harness knowledge or paid inference. Do not override existing `AGENTS.md`; no commit/push/merge/reset unless separately instructed by user.
- Preserve source snapshot provenance as precisely as the native-read package did; distinguish pre-execution freeze and postexecution imports; don't present stale code branches as current.

## Deliverable and autonomy rule

Produce `REPORT.md`, `DECISION_LEDGER.md`, `PROTOCOL.md`, execution/measurement source, complete raw preserved artifacts and a self-contained evidence ZIP. Review at least one disconfirming case *before* declaring a win. Distinguish code success, prototype activation, answer quality and methodological novelty.

**Conclusions must branch:**

- If B alone gives robust savings, call it a strong **simple** improvement and update framework reference; do not call it a new algorithm.
- If D uniquely beats A/B/C with full answers and accounted cost, specify the actual incremental observable state/action rule, limits, and adjacent TALE/CRANE/structured-template prior art, then consider a larger independent evaluation.
- If D ties C, stop D and preserve the negative result. Return to the primary objective with truthful scope; do not loop through new names.

This experiment, if run, is the first *causal* test of action-turn token reduction; the archived model-turn audit alone is not that test.
