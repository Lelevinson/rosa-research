# ROSA — Cumulative algorithm-development iteration after the native-read investigation

**Date:** 11 November 2026 (Taiwan)  
**Status:** Independent source/evidence review and archived-trace analysis; **no new ROSA/model runs by this researcher**  
**Goal unchanged:** a meaningful and reusable framework-level algorithm or justified incremental method that reduces unnecessary LLM-agent tool-calling overhead while preserving correctness, provenance, and full requested answer coverage. Presentation deadline: 2 December 2026.

## Executive research decision

The new native-read investigation validates a useful engineering result but **falsifies the assumption that serial CLI list execution is a major bottleneck in the surviving historical workload**. Fixed width four reduced a small, stable native-read fixture's measured makespan; adaptive AIMD did not beat it. Reusing an existing ROS CLI daemon's graph observer dwarfed CLI scheduling gains for one narrowly specified *service-type metadata* operation. None of these tests produced new LLM-efficiency evidence or generalized semantic answers.

I independently reread the preserved original diagnostic trace archive and found a different, larger, directly observable cost: **the model's token *generation*, not native graph reads or prompt prefill**. In the archived 36 primary episodes, 227 model completions consumed 2,304.56 seconds of backend token-generation time, against 222.12 seconds of prompt evaluation, 9.48 seconds of model loading, and 2,541.79 seconds of total model-reported duration. **Of 191 model responses that issued at least one structured tool call, 174 also emitted assistant prose**, containing 5,955 whitespace-delimited words. Some of that prose may be useful; this is not a measured avoidable-token estimate.

This shifts the next *investigation* toward the boundary between LLM semantic decisions and the **format/length of action turns**. The first control must be a truly deconflicted, batching-enabled ROSA agent instructed to omit optional narration when making a tool call **while still producing a complete final answer**. Merely prompting brevity is *not a novel algorithm*. A limited algorithmic extension worth examining is **state-conditioned output-mode selection with explicit repair fallback**, driven only by framework-visible error/validation states. Its novelty and advantage are *not established*: a fixed prompt saying “be brief on actions, explain errors” could reproduce it. This ordinary control is essential, not optional.

**Current status:** (a) native width adaptation: not promoted; (b) persistent graph observer: a high-value systems control, not a new algorithm; (c) response-length/decision-budget work: evidence-backed *exploration*, not a selected method. The next step is a small, predeclared intervention with actual model inference and full-answer scoring—not another generic source audit, and not a sweeping 22-cell baseline rerun.

## 1. Preserved research context and exact provenance

The context through the post-CPAW addendum remains binding. Earlier results and decisions are retained, including JTVR, Rounds 1–28, semantic-adapter contamination, R24 parallel DAG studies, R25–26 conditional wins versus weaker controllers, R27–28 cross-application coverage loss, tool-menu retrieval (8/12 original, 10/12 strong prompt, 6/12 lexical, 7/12 candidate), structured dependency zero `$ref` adoption and irrecoverable 64 original traces, CodeAct 1/9 full program completion with the stronger comparison inconclusive, Missions A–D and GLBE/CCVT ordinary-helper parity, semantic source failures, CPAW's negative simulation and 0/47 strict-contract eligibility, and Martin's separate fixed-catalogue macros. **None is erased or retrospectively called a general win.**

The newly uploaded `ROSA_NATIVE_READ_REVIEW_20261111(1).zip` contains `REPORT.md`, `DECISION_LEDGER.md`, `PROTOCOL.md`, `PRIOR_ART.md`, frozen pre-execution sources, source snapshots, native-event JSONL, the two original archived trace ZIPs, hashes, and verifier. The package reports the local ROSA HEAD `94af17866cb82f3ea3f09422ef5cbb99b14cc89c` on `research/capability-discovery-20261110`; I **did not** see that local checkout directly. The archive's manifest/bytes were checked by running its `verify.py`: **90 declared hashes and sizes passed**; its four standalone `test_executor.py` tests passed. I independently read selected native journals and its audit/summary code, but did **not** reproduce ROS 2 measurements on the user's machine or claim independent experimental replication.

Crucial nuance: its reported 798 verified historical member hashes include 332 baseline plus 466 CodeAct entries. Their 64 missing dependency-experiment event traces were **not restored**. The original primary baseline trace archive *is* included here and can be re-examined independently. Native source snapshots are **postexecution**, not full pre-execution closures; native_v1 encountered socket permission failure, native_v2 encountered a missing virtual-environment import only *after* finishing width tests, native_v3 resumed the transport portion without rerunning positive pairs. Fixture SIGKILL cleanup artifacts are preserved; a later separate cleanup smoke test succeeded.

The attached canonical context's Section 14 (written before the new study) states that no experiment was yet authorized. Treat it as dated historical guidance, not a ban retroactively contradicting the user's subsequent bounded native-study authorization. All prior *scientific* constraints—full answers, no semantic maps, strong controls, trace preservation—continue. This document itself is not a grant to run paid APIs or modify the local project.

## 2. Exact interpretation of the new native measurements

### 2.1 Incidence from original traces

The Codex archive reconstruction reports:

| Historical cohort | Primary baseline | CodeAct mixed evaluation/development/continuation |
|---|---:|---:|
| Trace episodes with relevant events | 36 | 30 |
| Tool start events | 203 | 142 |
| List-wrapper starts | 80 | 33 |
| Multi-entity list calls | 33 | 8 |
| Episodes with any multi-list call | 23 | 6 |
| Native CLI completions | 264 | 137 |
| Serial multi-list native summed duration | 40.8254 s | 8.9673 s |
| Zero-overhead, duration-invariant ideal overlap arithmetic | 27.2337 s | 4.6524 s |
| Total observed event spans | 2,805.8734 s | 1,303.4881 s |

The 27.23 seconds correspond to **0.9706%** of the baseline event spans. This is a *counterfactual replay arithmetic estimate*, not a universal physical upper bound: changing concurrency can change individual operation latency, resource contention, errors, graph observation times and critical paths. It is nevertheless a strong reason not to prioritize sophisticated adaptive width for this **specific** historical ROSA workload. The CodeAct cohort is not 30 independent complete evaluation tasks; it mixes conditions and must not be pooled for a randomized efficacy estimate.

### 2.2 Native fixture policies

In a stable, local Jazzy fixture with four disposable nodes and read-only graph APIs, the two repetitions of each four-entry family produced:

| Read family | Serial | Fixed-2 | Fixed-4 | AIMD |
|---|---:|---:|---:|---:|
| Node info, seconds | 2.7519 | 1.5432 | **0.8424** | 1.4892 |
| Topic verbose info | 2.8198 | 1.4944 | **0.8960** | 1.5564 |
| Service type | 2.8404 | 1.4874 | **0.8397** | 1.5152 |
| **Sum** | **8.4121** | **4.5249** | **2.5780** | **4.5607** |

All 96 fixture reads succeeded; pairwise normalized full-output multisets matched, with independently recorded per-position status/observations. These **are not model runs**, and the result is not an estimate of held-out ROSA correctness. AIMD began with a small width and could not compete with fixed-4 in two short, stable batches; this is not a universal claim against adaptive concurrency. Earlier Round 24 already studied scheduling typed DAGs, using application-specific task/field contracts, and found ordinary ready-list controls strong. An incremental scheduler would need demonstrable load heterogeneity and gains beyond a warmed, tuned limiter on realistic native *critical path* work.

### 2.3 Persistent service graph observer

For eight paired lists, 32 service-type metadata reads per arm:

- CLI subprocess serial: **11.419331 s** accumulated batch wall time.
- Reused `NodeStrategy` against the same existing ROS CLI daemon: **0.036736 s** accumulated batch wall time.
- Opening the reused context: **0.002784 s**, excluding cold daemon/middleware setup.
- All eight full-output comparisons passed in the stable fixture.

The warm-list comparison shows about **311×** narrower-operation latency reduction, **not** a 311× ROSA-agent speedup. It is primarily a result of replacing Python CLI invocations with in-process reads of an already available graph interface, **not** evidence of 32 avoided DDS discoveries. The two paths perform 32 logical reads; node/topic transport parity, graph churn, full cold initialization and device-level side effects are untested. A plain always-persistent read observer is the proper strong simple control; an adaptive CLI→observer switching policy has no demonstrated advantage here. This is worth incorporating as opt-in infrastructure and recording transparently in the final presentation, but **not** promoting as the project's main algorithm.

### 2.4 Coalescing was also screened

The Codex interval analysis identified 14 exact repeat native commands among 264 baseline completions and 24 among 137 CodeAct completions. **Zero** overlapping identical command intervals were found in either surviving cohort. Hence *in-flight singleflight* is not currently activated. Sequential repetitions are not safe cache hits merely because literal arguments or stdout match; ROS state can change. This is not evidence that singleflight is impossible for other deployed agents, but it is sufficient to avoid another benchmark tailored to make it look positive.

## 3. New independent archived-model-turn audit

This section is **new analysis from original retained trace JSONL**, not an independent ROSA rerun. The included `replay_model_turn_costs.py` parses exactly `evidence/primary-v1/*/trace.jsonl` in the original baseline archive; it excludes seven oracle snapshot files and all diagnostic replay trials. It asserts 36 primary episodes, 227 model completions, and the archived 1,585,055 input and 27,132 output token counts. `model_turn_costs_replay.json` contains per-arm, per-model-response, and predecision-state aggregates with every source trace location.

| Model-reported metric, 227 completions | Total | Share of summed backend total duration |
|---|---:|---:|
| Output token generation (`eval_duration`) | **2,304.560 s** | **90.66%** |
| Input processing (`prompt_eval_duration`) | 222.124 s | 8.74% |
| Model loading (`load_duration`) | 9.481 s | 0.37% |
| Residual backend accounting | ~5.620 s | ~0.22% |
| **Backend total (`total_duration`)** | **2,541.785 s** | 100% |

For a different denominator, output generation was roughly **82.1% of the 2,805.873 seconds of summed event spans**. The model total was roughly 90.6% of that span sum. The components should **not** be blindly added to native-CLI durations, because event spans and nested tool/model accounting may overlap and not all timings have identical clock/accounting semantics.

| Model response kind | Turns | Output tokens | Backend decode seconds | Visible assistant words |
|---|---:|---:|---:|---:|
| Has tool call **and prose** | **174** | 16,801 | 1,349.806 | **5,955** |
| Tool call, no prose | 17 | 833 | 62.856 | 0 |
| Final answer, no tool call | 36 | 9,498 | 891.898 | 3,557 |
| **All** | **227** | **27,132** | **2,304.560** | **9,512** |

Thus 174/191 (**91.1%**) of tool-action turns contained assistant narrative text. This is an **eligibility signal for studying action-format efficiency**, *not* a proof that 5,955 words can be removed without changing decisions. They may function as the model's explicit context for later steps; the saved LangChain scratchpad includes original assistant/tool messages. The baseline's full tool-call token encoding, reasoning, and content have no per-span token breakdown. **Never** estimate actual causal savings by simply deleting words after inference (which saves no generated-token time), nor assume textual word count equals tokenizer output tokens.

Predecision trace structure, reconstructed without looking at task answer labels:

| Observable state before model turn | Tool-action turns | Final turns | Total |
|---|---:|---:|---:|
| Initial request | 36 | 0 | 36 |
| After a tool result with no recorded native failure | 148 | 36 | 184 |
| After at least one native failure | 7 | 0 | 7 |

This gives a **real state variable**—observed native failure versus no recorded failure—but only seven failure-conditioned decisions in the historical sample. No policy is justified by claiming error states are numerous, or by assuming an initial turn always needs tools on arbitrary queries. The 36 final turns after tool results without recorded native failure also prove the runtime **cannot know that the next model turn is an action** merely because a tool succeeded. Any shortening mechanism must retain the model's freedom to output a complete final answer on that same call.

### A prompt-caching misconception corrected

The initial intuition that ~1.6 million input tokens automatically makes prefix caching the main opportunity is **not supported**. This archived backend reports only 222.1 seconds of prompt evaluation versus 2,304.6 seconds of generation. Current Ollama documents expose `prompt_eval_cached_count`, but this field is **absent** from these historical model events; we do not know actual cache hit rates. Existing SGLang/vLLM automatic prefix caching is powerful prior art. Even eliminating all **observed** prompt-eval time would save under 9% of the summed provider model total in this sample; it would not solve the main output-generation bottleneck. A different model, uncached backend or cold deployment could reverse this priority; do not generalize from one Qwen/Ollama setup.

## 4. Multiple design iterations and explicit rejections/revisions

### Iteration A — Improve adaptive native scheduling, not merely abandon it

**Starting hypothesis:** a policy choosing batch width from observed service time, occupancy and error signals can outperform fixed concurrency while leaving semantic tool choice unchanged.

**Challenge from new data:** the original trace replay attributes only ~0.97% of event spans to optimistic overlap of existing list reads; stable fixture fixed-4 is faster than AIMD. The stronger transport control eliminates most per-read CLI interpreter overhead for service-type metadata. Generic AIMD/Gradient2 methods and ordinary fixed width are already established; R24 also tested generic ready-list scheduling. No measured workload regime demonstrates a cross-over in the best width. Selecting a q90 threshold or training a width predictor on synthetic congestion would be methodological theatre.

**Revision:** retain the bounded executor as a **safe infrastructure option** for workloads where genuinely slow independent reads exist, and write a future reopening condition: independently observed remote service read latency along the agent's critical path, variable contention, repeated comparable decisions, and an action difference not reproduced by Gradient2/fixed widths with the same information. **Do not rerun the current native width matrix.**

### Iteration B — Replace subprocess lifetime, and challenge adaptive switching

**Starting hypothesis:** pay a setup fee for a long-lived read observer only when enough repeated reads justify it (online rent/buy).

**Challenge:** the warm observer opened almost instantly and dominated CLI serial service-type lookups. A plainly reused observer is the right countercontrol. Unmeasured *cold* client construction and graph freshness prevent generalizing the figure. The previously proposed ski-rental mathematical rule is classical and adds runtime logic without a demonstrated tradeoff; it is not a new ROSA optimization algorithm here.

**Revision:** make a persistent observer a baseline infrastructure option with per-family semantic parity tests and separate cold/warm accounting. Do **not** build a switching optimizer without an actual distribution of short sessions where the simple always-reuse control is worse. No model plans or semantic contracts are introduced.

### Iteration C — Check the next genuine bottleneck: decode-phase generation

**Starting hypothesis:** reduce model latency by stabilizing long prompts/prefix cache. **Counterevidence:** archived model prefill constitutes only 8.74% of backend time; token decoding 90.66%. **Revision:** examine unnecessary *generated* assistant prose on action turns rather than prioritizing prompt compression.

**Primary observation:** 174/191 action turns include prose, a much more prevalent signal than eligible overlapping duplicate native reads. A first intervention should ask for tool calls without narration, keeping the final answer unconstrained. This is a strong **ordinary** prompt control—not research novelty. Further gains should be measured against it, not inferred from original ROSA's verbose action behavior.

### Iteration D — Consider strict action grammar, then challenge it with prior art

**Starting hypothesis:** make action messages an output protocol with a compact schema, forcing the model to generate only action semantics while leaving final answers unrestricted.

**Critical constraints:** (i) the model must decide `action` vs `final` *within the same inference*; forcing an action on every post-tool turn would suppress full answers; (ii) constrained decoding is established and can alter reasoning quality, as CRANE and JSONSchemaBench discuss; (iii) **Constraint Tax (2026)** reports that applying JSON-schema constraints alongside native tool calling can suppress tools, so dual-mode JSON+native tooling must **not** be assumed compatible; (iv) a structured action envelope often adds JSON tokens; (v) hard `max_tokens` can truncate arguments or final answers, violating correctness. Qwen/Ollama model support also must be verified in the actual installed stack.

**Revision:** do **not** select JSON grammar as the first trial. Retain native tool calling intact and study a **soft action-compact instruction** first, with a separate conditional policy arm only if it behaves differently from a fixed, good prompt. A future provider-specific grammar experiment requires demonstrated mutual compatibility and strong answer-quality controls; otherwise stop.

### Iteration E — Feedback-conditioned action-output policy (conditional incremental candidate)

**Mechanism:** The runtime tracks only **public agent events**, never a handwritten task→tool/source map: `last_tool_outcome∈{initial,success,error,invalid}`, `last_action_format_valid`, any timeout, and an episode-local failure counter. Before each next model request, it selects one of two *model-instruction modes*:

- **Compact action mode:** if the model decides to call a tool, emit the native tool call without optional narration. If it decides to finish, return the *complete* final answer. Do not shorten or omit any requested output fields.
- **Repair-capable mode:** after an actual tool error, invalid tool-call syntax, or timeout, permit a short explanation of uncertainty/recovery while preserving the same tools and answer obligations.

No new model invocation is required solely to classify the turn, and no tool names/arguments are inferred by the framework. **Do not strip already-generated prose as the optimization.** The *causal intervention* must occur before decoding by choosing the invocation instruction. The policy can always abstain and use the ordinary strong agent mode, and incomplete/error results still go back to the model. All ROS actions retain existing authorization and safety rules.

A possible frozen rule, subject to challenge:

```text
next_model_request(state, conversation, available_tools):
    if state.last_tool_failed_or_invalid or state.repeated_format_failure:
        mode = REPAIR_CAPABLE
    else:
        mode = COMPACT_TOOL_ACTION
    # Both modes retain the same native tools and permit complete final answers.
    # Only optional narration for tool-calling turns differs.
    invoke_unchanged_tool_call_model(mode, conversation, available_tools)
    validate emitted native tool names and argument schemas as usual
    execute authorized actions; record all outcomes and original responses
    never assert answer completeness from schema validation alone
```

**Exact behavior/action difference:** after an observed `ros2 node info` FQN failure, this policy sends `REPAIR_CAPABLE` while an *always-compact* policy sends `COMPACT_TOOL_ACTION`. After successful reads it sends compact. But a **static conditional prompt** (“If calling tools, be terse; if a tool fails, explain recovery; always answer completely”) might behave identically. A simple model-agnostic dynamic prompt switch is not automatically a meaningful algorithm; success must isolate additional value over this **strongest ordinary fixed-conditional control**.

**What could be new, incrementally?** A measured, formally scoped policy based on **observable tool-execution feedback** that allocates expensive output budget to repair turns while keeping routine action turns terse, with documented noninferiority of complete answers and model-call accounting. The technical addition, if established, is the *conditional allocation rule* and its robust coverage/cost behavior in actual ROSA—not generic prompting, caching, structured output, or error retry. On this dataset only 7/227 turns followed recorded native errors; the algorithm may offer negligible extra savings versus a fixed terse instruction. A negative outcome is plausible and will be acknowledged.

**Strongest counterexample:** wrong-source answers and missing requested fields can occur after syntactically successful tools; no status-only controller sees them. Forcing short output can reduce a model's opportunity to reason about observed-vs-configured values. The method cannot guarantee full-answer coverage and should remain an *experiment*, not a selected optimizer, until blind evaluation. Another counterexample: a fixed concise instruction may achieve exactly the same model behavior with zero policy overhead.

## 5. Formal decision and measurable contrast

Let `s_t` denote framework-visible state before model request `t`, `a_t∈{C,R}` the selected compact or repair mode, `T^G_t(a)` model generation duration, `T^P_t(a)` prompt evaluation, and `T^T_t` tool duration. For an episode:

\[
C(\pi)=\sum_t \bigl(T^G_t(\pi(s_t))+T^P_t(\pi(s_t))+T^T_t\bigr) + T_{\rm policy}+T_{\rm setup},
\]

with clocks and concurrency measured consistently rather than naively summed in final attribution. The optimization desideratum is lower **actual** paired episode wall time/tokens while complete source-supported quality is no worse than the best ordinary control at a predeclared tolerance, no new unauthorized actions occur, and all retries count against the method.

A post-hoc counterfactual **cannot compute** `T^G_t(C)` from observed `T^G_t(R)`; generation/args/next-turn trajectory change when prompted differently. Only controlled actual inference resolves the effect. Candidate is promoted only if (i) full answer correctness/coverage is noninferior at an appropriately cautious sample size, (ii) actual per-turn decoded tokens and duration fall, (iii) *no hidden additional model calls* are used for recovery, and (iv) the dynamic policy beats **deconflicted static terse** *and* **fixed conditional** controls on comparable tasks. If a simple prompt ties or wins, retain that engineering gain and reject the policy's incremental claim.

The archive suggests an *eligible action-turn opportunity*, not a numeric saving. We intentionally report no invented time savings, no arbitrary confidence intervals, and no retrospective success improvement.

## 6. Prior art and exact adjacency

| Primary material | Inspected level | What it already provides / why it matters | Relationship to this iteration |
|---|---|---|---|
| ROSA public source (`src/rosa/prompts.py`, `src/rosa/tools/ros2.py`, `src/rosa/rosa.py`) and frozen native ZIP | Code and original journal review | Default prohibits batching at prompt level; list tools loop over CLI; LangChain model/tool boundary provides invocation hook. | Non-contradictory strong prompt, native tool-call retention mandatory. |
| R24 original local report/code (preserved in ZIP) | Source/report | Fixed ready-list parallel execution and historical learned scheduler comparisons already strong. | Blocks claiming generic adaptive batching as novel. |
| Netflix [AIMD](https://github.com/Netflix/concurrency-limits/blob/main/concurrency-limits-core/src/main/java/com/netflix/concurrency/limits/limit/AIMDLimit.java) and [Gradient2](https://github.com/Netflix/concurrency-limits) | Source reference via Codex's prior-art review; no new runtime here | Adaptive concurrency policies use latency/drop feedback. | Compulsory controls if native scheduler reopened. |
| SGLang, [RadixAttention](https://www.lmsys.org/blog/2024-01-17-sglang/) (2024), vLLM [automatic prefix caching](https://docs.vllm.ai/en/v0.14.1/design/prefix_caching/) | Primary system description | Prefix/KV reuse widely implemented. | Prompt-caching alone is not novel; lower present-workload prefill share. |
| [Automata-based constraints for language model decoding](https://research.google/pubs/automata-based-constraints-for-language-model-decoding/) | Primary research abstract/method description | Formal grammar token constraints for API/JSON output. | Compact action grammar has substantial parent work. |
| [CRANE](https://proceedings.mlr.press/v267/banerjee25a.html) (ICML 2025) | Primary paper abstract/results/approach | Strict grammar can degrade reasoning; extra reasoning rules improve quality. | Inhibits overclaim that constrained output preserves semantic correctness. |
| [JSONSchemaBench](https://arxiv.org/abs/2501.10868) (2025) | Primary paper abstract | Different schema engines trade compliance, coverage, and quality. | Verify actual provider support; schema compliance ≠ correct tools. |
| [Constraint Tax](https://arxiv.org/abs/2606.25605) (June 2026) | Primary paper abstract | Joint structured-output and native tool-call constraints can suppress tool use. | **Do not silently combine JSON Schema mode with native tools.** |
| [Token-Budget-Aware LLM Reasoning](https://aclanthology.org/2025.findings-acl.1274.pdf) (2025) | Primary paper abstract | Adaptive reasoning/output budgets already established broadly. | Incremental claim must isolate external **tool-event-conditioned** policy and beat fixed concise budgets. |
| [Guided-Structured Templates for Function Calling](https://aclanthology.org/2025.emnlp-main.1242/) (2025) | Primary paper abstract | Structured reasoning templates improve function-call reliability; free-form reasoning may harm. | More words are not always better; simple template is a hostile comparator. |
| [When2Tool / Probe&Prefill](https://arxiv.org/abs/2605.09252) (2026) | Primary paper abstract and reported outcomes | Uses model hidden-state signal to decide tool necessity. | Different target; local chat API does not expose such states by default. |
| [AsyncLM](https://arxiv.org/abs/2412.07017) (2024) | Primary abstract | Asynchronous model/tool execution and interrupts can reduce latency. | Overlap is already prior art; native critical-path ceiling makes it secondary here. |
| [LLMCompiler](https://proceedings.mlr.press/v235/kim24y.html), ReWOO, CodeAct, Martin macros, GLBE, CCVT | Previous saved source/evaluation and parent mechanisms | Dependency execution, simple macros, result-bound continuation and terminal acceptance. | Do not repackage deterministic loops or model-authored complex plans under a fresh name. |

This is **not** a claim that every paper was independently replicated, every full PDF inspected, or that research novelty is globally settled. Terms and strong controls are stated so future comparisons can be corrected by closer prior art. The `Constraint Tax` and `CRANE` sources are important disconfirming evidence, not just favorable citations.

## 7. What Codex should implement/measure next

See the accompanying `CODEX_EXPERIMENT_PLAN.md` for a bounded, executable assignment. Summary:

1. **Don't rerun native read matrices.** Preserve the new artifact and adopt the persistent service-graph observer only as an opt-in engineering reference (not a speedup attributed to the model).
2. **Create actual, fully deconflicted strong-control prompts**, replacing—not appending to—the built-in sequential restriction; preserve tool set and information parity. Confirm multiple issued independent tools are actually accepted/executed when applicable. Test strict completeness.
3. **Implement static concise action prompt and static conditional concise/repair prompt as hostile comparators**. Both permit complete final answers; neither omits requested facts or bypasses semantic judgment. Only then implement a small, opt-in dynamic `success→compact; error→repair` controller, preserving unchanged model API/tools and LangChain traces. No JSON+tools constraint until verified compatible.
4. **Predeclare a small first-stage matched experiment** including original source-sensitive cases and at least one fresh held-out application/source distinction. Keep model, seed/config, tools, data, safety, timeouts and scoring fixed. Record model response tokens and `eval_duration`, prompt evaluation time, tool/native operations, corrected complete answers and every failure. Use the same correctly activated strong control in every arm.
5. **Evaluate increment over the *best simple* control**, not original ROSA. If only a static prompt helps, present it honestly as engineering and stop dynamic-mode claims. If the dynamic policy shows a genuine unique pattern with no quality regression, extend with independent held-out tasks and clarify exactly what the controller adds. Otherwise do not launch a larger benchmark just because a few source cases looked good.

Full-answer quality is primary. The resulting source and traces must be durable, reproducible and backed up independently of `/tmp`; no model training, per-application semantic answer maps, or paid inference. A 12-task study cannot *statistically prove* population-level noninferiority; label it exploratory and report paired task-level facts and uncertainty.

## 8. Decision ledger and contribution boundary

| Direction | New evidence or argument | Current classification | Falsifiable next condition |
|---|---|---|---|
| Adaptive CLI read width | Real width4 2.578 s versus serial 8.412 and AIMD 4.561; historical ideal replay 0.97% | **Not promoted; systems control** | Measurable native critical path and variable-load cross-over versus fixed/Gradient2 |
| Persistent graph reads | 32 warm same-daemon service-type reads 11.419 s CLI versus 0.0367 s persistent | **Strong simple systems integration control** | Cold total lifecycle, broader API family parity, graph changes |
| In-flight singleflight | Zero overlapping identical requests in 264+137 original completions | **Not applicable in these traces** | Concurrent same-key read demands with a justified freshness contract |
| Prefix-cache scheduling | Prompt evaluation 8.74% of summed model backend time; cache hits unreported | **Low present priority** | Different deployment with demonstrably uncached prefill dominance |
| Fixed concise action messages | 174/191 tool-action turns included text; 5,955 surface words | **High-value, ordinary control to test** | Actual token/time savings and unchanged full answers under strong prompt |
| State-conditioned action/repair output mode | Existing 7 post-error tool-turns, 184 post-tool-result turns without recorded native failure; external outcome signal real | **Conditional incremental algorithm investigation; not selected** | Unique win against *static terse and static conditional* prompts with no completeness loss |
| Forced JSON grammar with native tool calls | Documented tool suppression and reasoning-quality risks in primary literature | **Blocked until provider parity proven** | Installed model supports compatible native tools, complete outputs and lower actual end-to-end cost |
| Result-bound CodeAct/GLBE follow-on | 1/9 fully adopted code programs; compact parameterized helper can tie | **Not main next action, not declared impossible** | Framework signal differentiating a robust continuation rule from helper/macros |

**Presentation-ready claim today:** “A ROSA native-read implementation and archived-trace reconstruction show that large operation-level speedups need not translate into meaningful agent-level gains. The trace-derived dominant bottleneck is output-token generation, and a new hypothesis targets cheap model action turns under strict full-answer controls.” **Not:** “We have a novel, validated ROSA algorithm.”

---

### Audit/execution boundaries

- Executed here: ZIP inspection/hash verification, four preexisting offline unit tests, and **new** independent archived `model_end` analysis with reproducible code.
- Not executed here: ROS2 CLI/rclpy fixture, Ollama inference, evaluation of new prompts, controlled intervention, held-out cross-application answer scoring, local source modifications, cold transport tests.
- Preserve the exact evidence pack; use new source-only instructions to Codex **only** if the user runs them. The updated canonical context file in this deliverable is a **proposed synchronized copy**, not an assertion that an uploaded ChatGPT Project Source or user's local Git file has been changed.
