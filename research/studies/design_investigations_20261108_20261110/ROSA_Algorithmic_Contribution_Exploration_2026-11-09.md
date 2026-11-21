# ROSA — Independent Algorithmic Contribution Exploration

**Date:** November 9, 2026, Asia/Taipei  
**Presentation:** December 2, 2026  
**Decision:** **Retain GLBE v2 as a bounded empirical systems optimization. Do not add an algorithmic extension for this project.**  
**Scope:** Research judgment, primary-paper reading, and local source/report inspection. No algorithm implementation, tests, ROS execution, model inference, paid API calls, dependency changes, or historical-evidence reconstruction.

## 1. Executive recommendation

Proceed with the simpler GLBE study. This investigation found feasible mechanisms that expand its capabilities, but **among the concrete workflows examined, no proposed extension has a defensible execution-decision advantage over both GLBE v2 and a comparable ordinary composite under the same legitimate runtime information**. The algorithmic contribution gap remains unresolved.

The strongest alternative is a small interpreter for model-selected, typed traversals across public ROS relationships. It can express combinations outside v2, such as topics → publisher nodes → named parameters. That is a real capability difference. However, a short reusable public-API helper can execute that example equally cheaply. A broader interpreter could outperform a frozen helper menu on previously unsupported combinations; this remains a plausible engineering hypothesis. Its current justification is weaker than the additional contracts, model syntax, validation, and evaluation it would require before December 2.

Selective checkpoints can also be useful, but ordinary composites can branch on exact user-authorized predicates and actual failures. Removing a checkpoint that requires semantic interpretation needs more than a successful tool response. Historical continuation prediction introduces a genuinely different next-tool decision, but this project lacks a grounded, calibrated rule that would justify that decision over strong ordinary controls while retaining ambiguous choices with the LLM.

Therefore:

- **Retain:** the v2 discovery/read executor, complete evidence accounting, and matched fixed-composite control.
- **Do not extend:** with typed chains, semantic checkpoint gates, or history/cost prediction in this implementation mission.
- **Do not replace:** GLBE with a larger compiler or optimizer.

This is an affirmative build recommendation with a narrower scientific claim, not a request for another sequence of feasibility audits. If original algorithmic novelty is mandatory for the degree, **GLBE v2 does not presently satisfy it**. Implementation and a positive result against ordinary batching would not, by themselves, change that conclusion.

## 2. Evidence and comparison rules

The original [v2 specification](ROSA_Algorithm_Specification_v2_2026-11-08.md), [critical review](GLBE_Independent_Critical_Review_2026-11-08.md), and preserved [v1](ROSA_Algorithm_Specification_v1_2026-11-08_working_copy.md) were read as proposals to challenge, not authorities whose recommendations must be retained.

Evidence labels in this report:

| Label | Meaning |
|---|---|
| **Literature** | Mechanism or limitation checked in a primary paper; its performance does not transfer automatically to ROSA. |
| **Source** | Current local implementation inspected directly; establishes code behavior, not measured runtime performance. |
| **Historical** | Saved local reports/source inspected read-only. Reported results retain their original qualifications; this mission did not replay their audits or independently rescore raw traces. |
| **Proposal** | An illustrative future interface, workflow, or experiment. It is not implemented functionality. |
| **Judgment / hypothesis** | This investigation's inference or a prospective claim requiring measurement. |

### What counts as a strong fixed composite?

A fixed composite is an ordinary reusable function over public API operations. Its inputs may include a namespace, parameter names, and explicit conditions. Its loops can consume unknown runtime collections; its branches can inspect results. “Fixed” describes its prewritten control structure, **not fixed entity names, unconditional execution, or fail-fast behavior**.

For each concrete witness below, compare with a simple helper covering the same public workflow, with identical information, native capabilities, budgets, output projection, failure isolation, and recovery rights. Such helpers cannot contain benchmark answers or question-to-endpoint tables. Freeze their menu before held-out evaluation; do not write a new helper after seeing each held-out request.

There are two different claims:

1. **Per-workflow efficiency:** does a new policy choose or execute better than an ordinary implementation of that workflow?
2. **Portfolio coverage:** can one interface handle previously unsupported combinations more economically than a frozen practical helper library?

A typed interpreter can plausibly improve the second even when it ties the first. Conversely, an unlimited catalog of hindsight-written helpers would make the comparison meaningless. This report rejects neither reusable interpreters in principle nor hypotheses merely because experiments have not yet established them.

## 3. Source facts that constrain the choices

**Source checkpoint:** active branch `research/clean-foundation-20261108`, commit `94af17866cb82f3ea3f09422ef5cbb99b14cc89c`. Installed package metadata identifies LangChain 0.3.30, langchain-core 0.3.86, and rosa-llm 0.1.0. These were inspected without importing or running ROSA.

| Code-verified fact | Consequence for the research question |
|---|---|
| ROSA registers supplied tools and uses the existing tool-calling agent plus `AgentExecutor`. [Constructor](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:82), [construction](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:256). | A small opt-in tool is feasible without replacing the planner or model transport. |
| Default instructions explicitly prohibit batching. [Prompt](/home/levinsonchen/project/rosa-research/src/rosa/prompts.py:81). | Default ROSA alone is an insufficient attribution control. Replace conflicting instructions in every strong arm. |
| Node/topic/service information tools already accept lists; their implementations loop over those inputs. [Node/topic](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:174), [services](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:308). | Never count one unavoidable model decision per discovered entity. List acceptance does not itself establish concurrent native execution. |
| LangChain's sync path iterates actions; its async path uses `asyncio.gather`. [Sync](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/agent.py:1403), [async](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/agent.py:1543). | Ordinary concurrency is already available. Match execution mode and concurrency limits. |
| The tool-call schema is derived from input arguments; the agent binds tools and serializes observations into its scratchpad. [Schema](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain_core/tools/base.py:558), [agent](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/tool_calling_agent/base.py:102), [messages](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/format_scratchpad/tools.py:18). | Existing input schemas do not automatically supply trustworthy output ports, semantic links, or knowledge of everything a future LLM answer will need. |
| The ROSA command runner uses `shell=True`, and discovery failure can appear as a list containing an error string. [Runner/decoder](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:25). | Any derived-argument executor needs shared hardened primitives. Backend hardening is not candidate-only algorithmic gain. |
| Jazzy parameter dump already lists names and retrieves their values. [Installed source](/opt/ros/jazzy/lib/python3.12/site-packages/ros2param/verb/dump.py:70). | An all-parameter chain must be compared with a bounded native dump helper, not two artificially separated model decisions. |
| `rclpy` exposes topics published by a node and publisher endpoint information containing node identity, type, and QoS. [Node→topics](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:1971), [topic→publishers](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:2221). | Cross-family traversals are technically real. Their relations come from public graph APIs, without an application-specific semantic table. |
| The Ollama adapter rejects strict function-schema request options and forced/parallel tool-choice controls. [Adapter](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/rosa_llm/langchain.py:141). | A new plan format needs actual unforced adoption and framework validation; provider-enforced correctness cannot be assumed. |

A declared `NodeId`→`node` relationship is legitimate public-contract metadata. Inferring that two arbitrary strings have interchangeable meanings is not. OpenAPI already distinguishes explicit response-to-operation relationships from mere schema compatibility. [OpenAPI 3.1.1, Link Object](https://spec.openapis.org/oas/v3.1.1.html#link-object). This is an API-contract analogy; ROSA does not need an OpenAPI migration.

## 4. Historical evidence that affects the choice

These are **historical findings**, not new tests of GLBE or proof that a future improved interface must fail.

| Inspected evidence | Finding and implication |
|---|---|
| [Baseline diagnostic](/home/levinsonchen/project/rosa-research-previous-20261108/research/baseline_diagnostic/report.md:5). | The added batch wrapper was never invoked. Redundant-read opportunity was observed, but closeout discovery failed. Tool availability and opportunity counts do not establish activated savings. |
| [Structured-plan study](/home/levinsonchen/project/rosa-research-previous-20261108/research/multistep/report.md:197), [source review](/home/levinsonchen/project/rosa-research-previous-20261108/research/multistep/independent-source-review.md:13). | The model emitted zero intended dependency references. On 12 pairs supported by its limited first-object scorer, the candidate used 77 versus 63 model requests. A functioning binder is insufficient if its model interface is unused. This was not a valid full-answer proof against dependency planning generally. |
| [CodeAct pilot](/home/levinsonchen/project/rosa-research-previous-20261108/research/paper_pilot/report.md:64), [comparison limits](/home/levinsonchen/project/rosa-research-previous-20261108/research/paper_pilot/report.md:146). | Nine program invocations: five rejected before child reads, three partial/failing, one complete. The bracketed continuation lacked matched B/C tasks. This establishes interface risk and limited feasibility, not CodeAct inferiority or GLBE superiority. |
| [Round 25 graph control](/home/levinsonchen/project/rosa-research-archive/research/internal/round25_graph_control_review.md:115). | Both arms completed 22/24; the simple graph-aware control used 42 versus 44 data acquisitions on mutually complete pairs. Already-paid metadata can explain apparent adaptivity. |
| [Round 26](/home/levinsonchen/project/rosa-research-archive/research/internal/round26_experimental_results.md:3). | Ordinary dynamic readiness expressed the event-scheduling repair. A new scheduling label did not create a new decision advantage. |
| [Round 28](/home/levinsonchen/project/rosa-research-archive/research/internal/round28_experimental_results.md:102). | Selective acquisition completed 6/8 feasible requests versus 8/8 for original and the strong prompt/compiler control. Valid native acquisition and requested-answer completeness remained distinct. |

The inspected [multistep report](/home/levinsonchen/project/rosa-research-previous-20261108/research/multistep/report.md:22) also identifies missing older menu-pilot raw evidence. This report does not reuse those old scores as validated evidence, reconstruct missing runs, or imply an empirical AutoTool comparison exists here.

## 5. Focused primary-paper comparison

The following mechanisms, rather than headline speedups, affect the decision. Interpret the 2026 papers below as inspected preprints; no venue-template text is treated as proof of acceptance.

| Primary source and relevant section | Established mechanism / limitation | Implication for ROSA |
|---|---|---|
| [LLMCompiler, Kim et al., 2024, §§3.1–3.4](https://arxiv.org/html/2312.04511v3#S3). | Plans encode dependencies; runtime results fill dependent arguments. Simple branches can be preplanned; complex observation-dependent choices return to the model. | A bounded chain or model checkpoint is technically credible but already has a close parent mechanism. |
| [ReWOO, Xu et al., 2023, §§2.1, 4](https://arxiv.org/html/2305.18323v1). | Separates planning, evidence collection, and solving. Unforeseeable environment-dependent reasoning limits advance planning. | Execution can need a value without the planner needing to interpret it. This separation is established prior art. |
| [CodeAct, Wang et al., 2024, §§2.1–2.4](https://arxiv.org/html/2402.01030v4). | Executable actions express composition, loops, and conditions; execution feedback supports repair. The action format itself does not require training, though the paper separately trains models. | A smaller typed format trades expressivity for validation/adoption simplicity; it does not invent programmable continuation. |
| [Agent JIT, Winston et al., 2026, §§3, 6](https://arxiv.org/html/2605.21470v2). | Uses input/output and state contracts, multiple generated plans, and scheduling from learned latency distributions. Offline application-tool synthesis and trace collection have costs. | Its cost-directed choices cannot be imported without contracts, profiles, and setup accounting. Plain bounded concurrency remains a required control. |
| [AgentPRO, Ren and Wang, 2026, §§4.1–4.6, 6.5](https://arxiv.org/html/2611.00628v1). | Separates generation needs from execution dependencies. Its concrete read rewrite needs a pinned backend-specific equivalence contract and current referential-integrity check. General selective recompilation is proposed; the held-out selector loses to the training-selected fixed policy. | Guards alone do not create a new contribution or certify generic equivalence. Its adaptive read-elimination example does not independently establish a net adaptive token/latency advantage. |
| [AutoTool, Jia and Li, 2025 preprint, §4, Appendices D/G/H](https://arxiv.org/html/2511.14650v1). | Predicts tools and fills arguments from historical transitions/dependencies, with context scoring and fallback. Discusses cold start, incorrect-context filling, redundant actions, overgeneralization, and custom parsing. | A genuinely different selection mechanism, with data and relevance assumptions. Successful invocation/feedback is weaker than full requested-answer correctness. |
| [LLM-Tool Compiler, Singh et al., 2024, §3](https://arxiv.org/html/2405.17438v1). | Runtime interface fusion uses an additional model, grouping examples, and tool-type lookup information. | Fusing several operations into one advertised interface is also prior art; fusion is not free schema-only semantic discovery. |

Here **AgentPRO** means the compiler preprint `2611.00628`, not the similarly named older agent papers. No reported benchmark percentage above is used as an expected ROSA effect.

## 6. Three serious candidate mechanisms

### Candidate 1 — Bounded model-selected typed traversal

**Problem and new capability.** GLBE v2 fixes each transaction to an inventory plus one reader family. A small traversal interpreter could connect a few declared public output ports to compatible reader inputs. It could support cross-family combinations without a separate wrapper for each combination.

**Proposed interface and flow.** The LLM would emit an ordinary tool call containing a short ordered list of approved capability/port IDs and literal arguments. For example: list scoped topics; obtain their publishers; read a literal parameter on the resulting nodes. The framework would validate the whole sequence, bind only typed observations, preserve topic→publisher lineage, reuse repeated reads where valid, and stop or return partial evidence under fixed bounds. No free Python, arbitrary JSON paths, recursive search, or question parsing is necessary. Nevertheless, this is additional model output syntax and a small interpreter, beyond v2.

**Runtime information.** Actual topic identities, typed publisher endpoint records, validated node identities, and parameter responses. The public graph API establishes the publisher relationship. Topic scope does not imply publisher-node scope: a publisher outside the topic namespace still belongs in the requested result. Unknown or ambiguous node identities cannot be silently guessed or merged.

**Concrete witness, proposal.** “For every observed topic under `/demo`, report its publisher nodes and each publisher's configured `use_sim_time`.” The topic set and publisher identities are unknown in advance. V2 cannot bind the publishers returned by its terminal topic metadata into a new parameter reader within that transaction. The proposed traversal can.

**Strong-control challenge.** An ordinary `inspect_topic_publishers(namespace, parameter_names)` helper can use exactly the same public endpoint API and parameter batch client. It can preserve the same lineage, deduplicate valid repeated reads, isolate failures, and make the same native calls with the same two ideal model requests. These are API relations, not handwritten task semantics. Do not deny that helper to the comparator merely to make the traversal win. An analogous node→published topics→metadata helper defeats the simpler chain witness too.

**What remains potentially distinct.** Across genuinely new combinations outside a *frozen practical* helper menu, composition could save model boundaries and wrapper-authoring effort. That is a legitimate portfolio-level hypothesis. This investigation identified no concrete workflow that defeats both v2 and its comparable simple helper, and no established representative portfolio making the additional interface cost compelling now. This is not an impossibility claim about such a portfolio.

**Prior art and feasibility judgment.** Dependency substitution and programmable composition are already covered by the papers in §5. No training or history is inherently required; output contracts, relation validation, and model adoption are required. It could transfer across graph and parameter APIs and applications sharing them. Arbitrary application services would need additional independently justified effect/output contracts. Technically implementable before December 2, but the increased model/contract surface and historical adoption risk make it a weaker build choice than v2. **Do not select.**

### Candidate 2 — Selective checkpoints and observation delivery

**Problem and new decision.** Avoid a model call, an unnecessary read, or a large observation when execution can proceed under a previously authorized condition. Unlike v2's fixed inventory/map, this candidate explicitly decides whether to take another authorized branch or return to the LLM.

**Proposed interface.** The LLM supplies a bounded continuation and either an exact predicate or an explicit “model must inspect this result” checkpoint. The framework evaluates declared predicates over validated typed results. Requested exports, identity, failures, and unresolved branches remain visible. A general dependency analysis would additionally need reliable declarations of every later consumer, including the final answer.

**Runtime information.** Public result values, freshness/status information, exact literal conditions authorized by the user/model, and remaining budgets. These can establish substantive facts about a contract; they do not establish that an arbitrary question has been understood correctly.

**Strongest concrete witness, proposal.** “For each node under `/demo`, read `use_sim_time`; only where it is `true`, also report node metadata.” A literal Boolean branch avoids unnecessary metadata reads. V2 cannot express this conditional transaction in one call. However, a short conditional discovery/parameter/info helper can make exactly the same decision, with no semantic mapping. This shows useful dynamic behavior, not a new policy advantage over the fair helper.

For a harder request such as “find the node relevant to the localization problem, then inspect its observations,” neither a Boolean success flag nor type compatibility selects the correct semantic branch. Returning control is appropriate. Moving this interpretation into a lexical gate repeats the source-selection problem seen historically.

**Observation versus execution.** An identifier may be needed solely to issue the next call. Its entire raw discovery response need not be shown at an intermediate model boundary if that boundary is eliminated. However, requested identities and values must still reach the final answer. Removing unused fields can also save tokens without removing calls. The fair control therefore receives the same deterministic field projection and compact receipt format; compare equal delivered information, not compact candidate output against gratuitously verbose controls. A trace containing omitted facts does not satisfy the user.

**Why not select.** Exact predicates, branch-local failure handling, early exit on failed contracts, and declared field projection are ordinary reusable programming. For a more ambitious checkpoint policy, the missing ingredient is a trustworthy signal separating observations needed for semantic reasoning from those that can safely be bypassed. A model-supplied declaration can be wrong; structural validation cannot repair it. Added validator-model calls would need to be charged. This overlaps the generation/execution distinction and guarded rewrites in §5. A narrow conditional helper is feasible without training; a generally reliable semantic checkpoint mechanism is not currently specified. **Do not select.**

### Candidate 3 — History-conditioned continuation and cost-based handoff

**Problem and new decision.** Predict the next tool or decide whether to continue locally rather than ask the LLM. This could cover workflows not explicitly preauthorized as a chain, so it introduces a genuine tool-selection policy rather than merely reorganizing execution.

**Proposed flow and inputs.** Retain trajectory transitions and argument provenance; match the present tool/result/request context; propose a next allowed read with grounded arguments; continue only when a confidence/eligibility gate passes, otherwise use the normal LLM. An estimated-cost variant would choose between continuing and handing off based on expected remaining work and recovery.

**Strongest attempted witness, proposal.** After discovering publishers for a topic, history predicts a read of each publisher's `use_sim_time`. If the request explicitly asks for that parameter, a public-API composite already knows the next operation. If the request asks only for publisher identities, the extra read is unnecessary. If its intended configuration need is ambiguous, a frequent historical transition does not resolve it. No inspected case establishes a useful history-specific decision after those alternatives are controlled.

**Data and estimation requirements.** Besides tool identity and valid arguments, a credible gate needs evidence about task relevance and false continuation under changed requests/applications. A cost optimizer needs both legal alternatives, their future model/native costs, the probability and cost of repair, and an agreed correctness constraint. Observing one successful historical path does not reveal the counterfactual handoff outcome. Confidence derived from transition frequency is not calibrated semantic correctness.

**Could this ever be valid?** Yes. A learned predictor with abstention and a suitably validated task distribution can be a legitimate mechanism. The issue is its grounding here, not that learned continuation is intrinsically invalid. Any data collection, parsing, profiling, validation, additional model work, and errors must count. A training-free graph can still require substantial history and environment adapters.

**Generalization and feasibility judgment.** Unlike the first two candidates, it needs a history/profiling lifecycle and shift evaluation across tool families/applications. Reusing old trajectories without renewed contract/source validation risks incorrect-context argument filling or hidden mappings. AutoTool and Agent JIT already cover central prediction/cost mechanisms. A minimal implementation is possible, but a defensible matched study of its new decision before December 2 is a poor trade given the ungrounded policy inputs. **Do not select.** No mathematical optimizer is specified because its estimators and useful decision state are missing.

### Comparative decision

| Criterion | Typed traversal | Selective checkpoints | History/cost continuation |
|---|---|---|---|
| Real capability beyond v2? | Yes, cross-family chains. | Yes, explicit conditional branches. | Yes, prediction of an unselected next action. |
| Concrete advantage over comparable simple helper? | None found; possible frozen-menu portfolio advantage. | None found for grounded predicates/projection. | None found after relevance and ordinary controls. |
| Special model output? | Short capability/port sequence. | Continuation, predicates, exports/checkpoints. | Not necessarily, but internal history/context representation is required. |
| Extra calls/data? | No inherent extra model call; repair may add calls. | No for exact predicates; model validators add calls. | Historical data/calibration; profiling or context analysis may add costs. |
| Main repeat-failure risk | Unused/invalid plan syntax. | Semantic omissions or wrong-source admission. | Context mismatch, redundant actions, hidden argument mappings. |
| Deadline judgment | Buildable, insufficient incremental justification. | Narrow helper buildable; broader policy unresolved. | Implementation easier than credible validation. |

## 7. Selected direction: retain GLBE v2

### Model contract and responsibility

**Proposal, unchanged v2 concept.** The model receives the user request, public tool descriptions/schemas, common budget/visibility limits, and actual previous observations. It chooses the semantic operation, scope, and literals through ordinary JSON function calling. It receives no evaluator inventory or expected answer.

The node tool accepts `namespace`, `read` (`info`, `parameters`, or `all_parameters`), and `parameter_names`. The topic tool accepts `namespace` and obtains verbose metadata for every observed topic. Ambiguous or unsupported requests remain model responsibilities and can use ordinary tools or clarification.

Example model output:

```json
{"namespace":"/demo","read":"parameters","parameter_names":["use_sim_time"]}
```

The framework returns an evidence envelope; the LLM interprets it and answers. Execution completion never means “the user request has been semantically verified.”

### Conceptual algorithm and exact flow

1. Validate the selected operation, literal arguments, public discovery/reader contract, and remaining request budget. Reject invalid selection before discovery.
2. Perform the shared typed graph observation. Validate transport, shape, size, and the declared visibility/scope. Failed or oversized discovery provides no usable child-binding collection.
3. Classify observed identities, preserving ambiguous node-name collisions. Apply namespace segment rules and a stable order; never silently choose a prefix of an oversized collection.
4. Create a bounded ledger of success, failure, ambiguity, and pending work. Bind each valid identity into the already selected reader, copying literals unchanged.
5. Before every dispatch, check cancellation, backend health, deadline, and native/output reservations. Continue valid siblings after a local child failure; stop globally when required.
6. Validate each receipt and parameter response correlation. Retain actual source, arguments, intervals, costs, and missing outcomes. All-parameter reads use the same bounded native dump helper supplied to ordinary controls.
7. Return complete/partial/rejected status, precise scope limitations, delivered evidence, and unresolved identities. Let the normal agent handle interpretation, bounded direct repair, or the final answer.

This is one explicit procedure. It needs no learned score, additional planner, or decorative optimization equation. Discovery supplies execution arguments; it does not choose their semantic purpose. Fixed composites receive the same procedure and information.

### Data sources and validation constraints

Use public graph APIs, typed standard parameter requests, and a safe argument-vector runner for terminal metadata. Do not derive bindings from arbitrary CLI prose. Parameter values must match requested names by the documented ordering and cardinality; a short response is not silently zipped into success. A parameter containing the text `error` is ordinary data when its authoritative receipt is valid.

Retain v2's explicit budgets: 16-entity transaction fan-out, 32 parameter names per node, 64 native attempts per request, 8 model requests, 45-second transaction and 180-second request limits, and bounded delivered payloads. These are design limits, not measured optimal settings. Use the same limits and request-global retry accounting in strong controls. The first study has no automatic composite retry; a model-directed failed logical read can receive at most one additional native attempt.

Observed-set coverage is relative to the observer and interval. It is not proof of a globally complete or atomic graph, stable node incarnation, or physical robot state. Final requested-field coverage and support for every asserted fact require independent evaluation.

### Normal and failure examples

**Normal, hypothetical.** The user requests configured `use_sim_time` for all visible nodes under `/demo`. The model emits the call above. Discovery observes uniquely addressable `/demo/a` and `/demo/b`; two typed parameter reads return valid Boolean values. The model receives both values, identities, and intervals, then answers. Strong model-led batching ideally needs three model requests: discovery selection, grouped-reader selection, final answer. GLBE and the matching fixed composite ideally need two. Native work is the same. These counts illustrate the boundary, not an observed result.

**Failure, hypothetical.** Discovery observes a, b, and c; b becomes unavailable before its parameter read. Preserve a's value, record b's failure, and acquire c if the global budget permits. Return a partial envelope identifying b. The model can retry b directly within the shared allowance or report its value unavailable. It cannot replace the missing value, erase b, or declare all values known. A strong fixed composite behaves identically. If the requested fact was instead an observed message frame but the model selected a configured parameter, successful execution still fails semantic correctness.

### Expected benefit, limitations, and minimum changes

**Hypothesis:** eliminate one intermediate model decision on eligible unknown-set requests, reducing tokens/time when that saving exceeds schema, validation, output, and recovery costs. Do not predict one saving per child, fewer native reads, or superiority over the same-path fixed composite.

**Bounded generalization:** the same inventory/map engine can serve node metadata, parameters, and topic metadata across applications using those public APIs. This does not establish arbitrary tool composition or understanding of application-specific services. Known identities, semantic source selection, graph instability, fan-out limits, and model nonadoption limit the eligible workload.

**Minimum future implementation:** three small opt-in responsibilities—contracts/status/budgets; shared safe read primitives; one bounded inventory/map executor—with two model-facing adapters. Add four straightforward fixed wrappers over those same primitives, an isolated strong-arm prompt replacement, request accounting, and study instrumentation. Register through `ROSA(tools=...)`; no core ROSA, LangChain, rosa-llm, or dependency change is indicated by the inspected integration. This describes future work only.

Its relationship to the literature is adaptation of established observation binding, composition, and guarded execution to a deliberately restricted ROSA interface. Potential contributions are measured integration behavior, implementation reuse, evidence/failure handling, and a rigorous attribution result. **A positive empirical result would not establish a newly invented general optimization algorithm.**

## 8. Smallest decisive experiment

This is a **proposed first falsification block**, not a run performed here, and not a silent replacement of v2's 96-episode protocol. It can reject the narrow hypothesis early; passing it is limited evidence, not satisfaction of v2's larger promotion criteria.

Use three arms: **B**, strong ordinary ROSA with actual grouping, native dump, ordinary reuse/repair, and shared hardened backend; **C**, B plus the four straightforward public-family composites; **D**, B plus GLBE's two schemas/shared engine. Original-default A can remain in the larger study but is unnecessary for this attribution block.

Freeze six eligible natural-language requests before inference: named parameters on unknown node sets in two applications; an all-parameter request in one; node metadata in the other; and topic metadata in both. Use held-out namespaces/entity counts and two repetitions: **6 × 3 × 2 = 36 episodes**. Add one known-identity request and one deliberately disappearing-child request in each arm once: **6 additional episodes, 42 total**. No new applications or learned policies are needed. Repetitions do not create independent task families.

All strong arms receive identical primitive contracts, delivered information, backend, budgets, concurrency cap, model settings, history policy, and recovery rights. Freeze helper interfaces before held-out requests are inspected. Establish ordinary batching and unforced composite adoption within the implementation mission's bounded development check, not by forcing the target tool during evaluation. An arm that never uses its advertised mechanism cannot support a claim about that mechanism's efficiency.

Independently bracket stable episodes with inventory/value observations; preserve dynamic failure timestamps and time-qualified outcomes for the disappearing child. Charge observer startup, validation, serialization, repair, failed calls, and all model/native work. Keep raw traces and incomplete attempts; missing closing evidence is indeterminate, never regenerated under its old identity.

**Decisive interpretations:**

- D loses supported completion or requested information against B: reject the correctness-preserving improvement on this scope, irrespective of fewer calls.
- D fails to remove the predicted intermediate model boundary on adopted, comparable successful requests: the proposed mechanism did not yield its intended saving there.
- D removes that boundary but token/time savings disappear after overhead and recovery: reject the net-efficiency hypothesis for this block.
- C and D both improve over B with equivalent schedules: ordinary composition explains the saving; the algorithmic advantage claim fails.
- C outperforms D: prefer the simpler fixed interface. D outperforming C through better adoption would be an interface result, requiring inspection of schemas/prompts and actual trajectories, not attribution to a different scheduler.

Report all-attempt completion/cost first, then exact mutually supported pairs, with factual coverage, unsupported extras, and formatting separate. A positive small block can justify the existing bounded study; it cannot establish population noninferiority, universal safety, or algorithmic novelty. No additional audit ladder or optimizer-development phase is recommended.

## 9. Delivery decision and Indonesian summary

**Build next, when implementation is requested:** GLBE v2 and its strong fixed-composite controls. Use November 9–17 for one bounded implementation/development/freeze effort, November 18–22 for the matched study, November 23–26 for analysis and evidence preservation, and the remaining days for the December 2 presentation. This is a proposed allocation, not a promise of measured success.

The exploration does not resolve the original novelty problem. It does establish why broader composition, conditional continuation, and learned prediction should not be added solely to obtain a more algorithmic-looking project. A credible negative attribution result is preferable to an unsupported new label.

**Ringkasan untuk mahasiswa S1:** Lanjutkan GLBE v2 sebagai optimasi sistem yang diuji secara empiris. LLM menentukan apa yang diminta pengguna; framework mengisi identitas hasil discovery ke operasi baca yang sudah dipilih, memeriksa hasil, dan mencatat bagian yang gagal.

Rangkaian bertipe dan percabangan berdasarkan hasil memang dapat memperluas kemampuan GLBE. Namun, pada contoh konkret yang ditemukan, fungsi gabungan biasa dapat menjalankan langkah dan keputusan yang sama dengan biaya yang sama. Prediksi berbasis riwayat menawarkan keputusan baru, tetapi belum memiliki dasar data dan aturan handoff yang cukup kuat untuk proyek ini.

Potensi manfaat GLBE adalah menghilangkan **satu keputusan LLM di tengah workflow yang sesuai**, bukan satu panggilan untuk setiap node. Bandingkan dengan batching yang benar-benar digunakan dan composite sederhana. Jika keduanya memberi penghematan yang sama, simpulkan bahwa manfaat berasal dari penggabungan operasi. Kontribusinya dapat berupa implementasi ROSA, evaluasi yang adil, serta penanganan bukti dan kegagalan; **belum ada dasar untuk mengklaim algoritma baru yang lebih unggul**.

## 10. Preservation record

Only this report was added to the workspace. Existing design inputs, ROSA source, dependency files, Git history, archives, and private configuration were not modified. Read-only checks used source/report reading, package metadata, Git identity/status, and file hashes. Historical reports were not treated as new measurements; no algorithm, ROS process, model, benchmark, or test suite was executed.

