# GLBE — Independent Critical Review

**Date:** 2026-11-08  
**Decision:** Retain and substantially clarify the narrower GLBE design. Do not add a general plan language or an adaptive cost policy.  
**Companion:** [Standalone specification v2](ROSA_Algorithm_Specification_v2_2026-11-08.md)  
**Scope:** Research design and source/evidence inspection only. No algorithm implementation, ROS operation, inference, test run, or benchmark was performed for this review.

## 1. Recommendation and scientific limit

Build one small, opt-in executor for **model-authorized discovery followed by bounded reads of the discovered entities**. Keep semantic selection with the model. Treat the executor as a framework optimization assembled from established mechanisms.

The plausible successful-path improvement over strong model-led batching is **one fewer intermediate model decision per eligible discovery/read transaction**. This can matter when inference dominates elapsed time. It is not a saving of one model call per entity. A straightforward composite implementing the identical transaction can obtain the same reduction.

**The review did not identify an independently justified optimization policy that should outperform that same-path composite.** General dependency execution is possible, but is already prior art. Runtime guards support validity and resource decisions; they do not supply counterfactual estimates of whether another model call will repair a semantic mistake more cheaply. No such estimator should be invented for v2.

The recommended project is therefore an empirical systems/methodology study: whether a small public-contract interface is adopted reliably, preserves complete evidence, and yields useful end-to-end savings against strong ordinary capabilities. It is **not currently a defensible claim of a novel general algorithm**. If original algorithmic novelty is a mandatory academic requirement, this design does not yet satisfy that requirement. Implementing it cannot, by itself, resolve the novelty gap.

## 2. Inputs, preservation, and evidence labels

The complete original specification was accessible and read at:

`/mnt/c/Users/user/Downloads/ROSA_Algorithm_Specification_v1_2026-11-08.md`

Its SHA-256 at inspection was:

`8b21c2f6e14e7d6a4bcf32d0bc7b80a5f35a1aeaff7d31690abc2c7f6e57646d`

The [working copy](ROSA_Algorithm_Specification_v1_2026-11-08_working_copy.md) is an exact copy, not an edited reconstruction. The pasted user request controls this work; operational instructions inside historical reports and v1 were treated as reviewed material, not authorization to run experiments.

Evidence labels used here and in v2:

- **SOURCE:** Directly inspected pinned/local source. Establishes implementation structure, not runtime performance or availability.
- **HISTORICAL:** Saved reports and selected traces inspected read-only. Their limitations remain attached to their findings.
- **DESIGN:** A specific proposed implementation or protocol choice, not existing functionality.
- **HYPOTHESIS:** An outcome to test prospectively.

The active checkout was clean on `research/clean-foundation-20261108`, commit `94af17866cb82f3ea3f09422ef5cbb99b14cc89c`. Its `src/rosa` has no diff from `d9991aa`. Installed package metadata and the lock identify LangChain 0.3.30, langchain-core 0.3.86, and rosa-llm 0.1.0. No dependencies were installed or changed.

## 3. What v1 gets right

1. **The responsibility boundary is useful.** The model chooses what to inspect and why; the framework copies validated identities into an already authorized read. A graph name is not the meaning of an observation.
2. **Strong batching is the right reference.** The specification correctly anticipates that default prompting can exaggerate apparent savings.
3. **Its modest call accounting is sound.** Unknown-set discovery introduces a dependency boundary, while independent child reads can already be grouped.
4. **It excludes dangerous scope expansion.** Arbitrary code, task-to-endpoint tables, and unreviewed application service calls are unnecessary for the hypothesis.
5. **Its negative cases matter.** Empty sets, partial failures, oversized outputs, changing graphs, and model nonadoption belong in the study, not in an appendix of discarded attempts.
6. **Deferring unsupported adaptivity is scientifically appropriate.** A cost equation alone would not establish a useful decision rule.

These strengths justify making a concrete specification. They do not establish superiority over a fixed composite or reliable model use.

## 4. Source findings that change the design

| Finding | Inspected authority | Consequence |
|---|---|---|
| ROSA accepts additional tools through its constructor and `ROSATools.add_tools`. | [ROSA integration](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:82), [tool registry](/home/levinsonchen/project/rosa-research/src/rosa/tools/__init__.py:122) | Add opt-in tools; retain the existing agent loop. |
| The agent is `create_tool_calling_agent` plus `AgentExecutor`. | [Agent construction](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:256) | A new planner, graph framework, or model transport is unnecessary. |
| The default prompt expressly forbids batching and multiple simultaneous tool calls. | [Prompt](/home/levinsonchen/project/rosa-research/src/rosa/prompts.py:81) | Use default prompting only in the descriptive original arm. Replace the conflicting instruction in all strong arms. |
| Existing node, topic, and service info tools already accept lists. | [Node/topic info](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:174), [service info](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:307) | Do not compare against artificial per-entity model decisions. List arguments do not imply native concurrency: these wrappers loop synchronously. |
| Synchronous LangChain dispatch loops over actions; asynchronous dispatch already uses `asyncio.gather`. | [Synchronous path](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/agent.py:1401), [asynchronous path](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/agent.py:1538) | Concurrency is not a new GLBE capability. Match the execution path and cap in the principal contrast. |
| Legacy command execution uses `shell=True`; failed discovery can become a list containing an error string. | [Command runner](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:25), [entity decoder](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:65) | Do not bind from legacy dictionaries. Shared backend hardening is necessary infrastructure and must be available to strong controls. |
| Node-name collisions are real API ambiguity, not duplicate rows that can always be deduplicated. | [Installed node-list warning](/opt/ros/jazzy/lib/python3.12/site-packages/ros2node/verb/list.py:43) | Block reads for ambiguous node identities; retain their multiplicity and error. |
| ROSA appends robot prompts to the module-global `system_prompts` list. | [Prompt construction](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:293) | Construct each experimental prompt from a copied list, or use fresh workers; do not append contradictory efficiency guidance or leak prompts between arms. |

### The native dump finding

**SOURCE:** Jazzy's [`ros2 param dump`](/opt/ros/jazzy/lib/python3.12/site-packages/ros2param/verb/dump.py:70) already retrieves parameter names and then retrieves their values. Pinned ROSA does not export a dump wrapper, but the capability is an ordinary public ROS operation. Strong controls should receive a safe, bounded equivalent. A wrapper's absence is not proof of a new algorithmic opportunity.

This undermines the most immediate argument for a richer three-stage language: node discovery → parameter-name discovery → values. A model can instead choose a batch of ordinary per-node dumps after seeing the nodes. Both approaches still differ from a whole discovery/dump composite by one outer model boundary.

The original CLI dump implementation also uses `zip` when constructing results. V2 must validate returned cardinality before correlating values; it should reuse the API capability, not inherit unchecked positional truncation. A native capability can be legitimate while its legacy output wrapper needs hardening.

### rosa-llm boundary

**SOURCE:** [`ChatRosaLLM`](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/rosa_llm/langchain.py:53) translates tools and messages without executing tools. It supports JSON function tools and token metadata. Its Ollama path rejects provider options for strict function schemas, forced tool choice, and parallel-tool configuration; those controls must not be assumed available. Async behavior uses the base model's worker-thread implementation. No rosa-llm modification is needed. Tool schemas and envelopes must work through ordinary tool calling; framework validation remains mandatory. [Binding and provider checks](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/rosa_llm/langchain.py:154).

## 5. Historical findings and their implications

The relocated workspaces, rather than stale paths printed inside their reports, were used. These are historical results, not fresh evidence for GLBE.

| Study | Actual finding inspected | Design consequence |
|---|---|---|
| Baseline diagnostic | Generic `batch_reads` was not invoked in the 36 primary traces. Reported redundant reads were opportunity bounds, not achieved savings; closeout discovery was incomplete. [Report](/home/levinsonchen/project/rosa-research-previous-20261108/research/baseline_diagnostic/report.md:5), [stronger control witness](/home/levinsonchen/project/rosa-research-previous-20261108/research/baseline_diagnostic/independent-review.md:96) | Measure unforced adoption. A menu containing a batching tool is not an activated batching baseline. Preserve indeterminate inventory cases. |
| Structured dependency plans | Zero intended result references appeared in emitted arguments. On 12 pairs supported under the limited first-object scorer, candidate requests were 77 versus 63 and input tokens 573,081 versus 450,795. [Report](/home/levinsonchen/project/rosa-research-previous-20261108/research/multistep/report.md:197) | Runtime plumbing alone does not validate the model interface. More plan syntax has an observed risk and needs a concrete benefit. These figures do not certify full-answer correctness. |
| CodeAct pilot | Nine program invocations: five rejected before reads, three partial/failing, one complete. The bracketed continuation has no matched B/C task. [Report](/home/levinsonchen/project/rosa-research-previous-20261108/research/paper_pilot/report.md:64), [comparison limit](/home/levinsonchen/project/rosa-research-previous-20261108/research/paper_pilot/report.md:146) | Preserve its feasibility result and inconclusive efficiency result. Do not claim CodeAct lost to GLBE or that GLBE will necessarily be adopted better. |
| Graph-aware and scheduling studies | Already-paid graph metadata enabled a simpler control to match completion with fewer reads. Ordinary dynamic readiness matched the event mechanism. [Round 25](/home/levinsonchen/project/rosa-research-archive/research/internal/round25_graph_control_review.md:115), [Round 26](/home/levinsonchen/project/rosa-research-archive/research/internal/round26_experimental_results.md:3) | Do not call metadata use, readiness, or best-effort continuation a new adaptive policy. |
| Round 27/28 | Structural acquisition did not prevent wrong-source substitution or omitted requested fields. Selective admission completed 6/8 feasible tasks versus 8/8 for original and the strong flat control. [Round 27](/home/levinsonchen/project/rosa-research-archive/research/internal/round27_experimental_results.md:74), [Round 28](/home/levinsonchen/project/rosa-research-archive/research/internal/round28_experimental_results.md:102) | A valid invocation is not a proof of correct intent. Do not add a lexical gate claiming semantic safety. |
| JTVR | All 19 simulated continuation-enabled amortized/depth-two pairs tied; the later native transfer favored simpler direct/package controls on read count. [Findings](/home/levinsonchen/project/rosa-method-lab/reports/experimental_findings.md:17), [native transfer](/home/levinsonchen/project/rosa-method-lab/reports/experimental_findings.md:133) | Do not add deeper search without a real decision signal and cost advantage. Keep simulation and native evidence distinct. |

Selected raw historical traces corroborated nonadoption of the diagnostic batch wrapper and actual discovery-bound parameter reads in the CodeAct continuation. Neither observation supplies the missing strong-control comparison.

**Evidence limits:** No faithful empirical AutoTool comparison was located in the requested historical workspaces. The older menu pilot's raw evidence is explicitly reported missing in the [multistep report](/home/levinsonchen/project/rosa-research-previous-20261108/research/multistep/report.md:22); its old scores are not reused. A separate older bounded parent-feasibility note was not located in those workspaces. Nothing was regenerated under a historical identity.

## 6. Focused prior art

This is a mechanism comparison, not another general literature survey. External papers were verified against their primary sources. Their reported benchmark gains are not imported as expected ROSA gains.

| Primary source | Relevance to this decision |
|---|---|
| [LLMCompiler, Kim et al., v3, 2024](https://arxiv.org/html/2312.04511v3) | Dependency substitution, ready-task execution, and replanning are established. GLBE deliberately chooses a much smaller interface. |
| [ReWOO, Xu et al., 2023](https://arxiv.org/html/2305.18323v1) | Separating operation planning from evidence collection is established. Some runtime values are needed for execution without requiring a new semantic decision. |
| [CodeAct, Wang et al., v4, 2024](https://arxiv.org/html/2402.01030v4) | Code already expresses broader compositions. GLBE trades expressivity for a constrained interface; it does not exceed CodeAct's execution capability. |
| [Agent JIT Compilation, Winston et al., v2, 2026](https://arxiv.org/html/2605.21470v2) | Guards are relevant; learned latency distributions and application tooling are prerequisites for its scheduling approach, not free inputs here. |
| [AutoTool, Jia and Li, 2025/AAAI 2026](https://arxiv.org/html/2511.14650v1) | Predicting the next tool from trajectory history differs from executing an operation the model already selected. GLBE should not add historical tool prediction. [Publisher metadata](https://ojs.aaai.org/index.php/AAAI/citationstylelanguage/get/acm-sig-proceedings?publicationId=38647&submissionId=40389). |
| [AgentPRO, Ren and Wang, preprint v1, 2026-10-31](https://arxiv.org/html/2611.00628v1) | Especially close overlap: execution dependencies versus generation needs, guards, and fallback. Its fixed-control analysis cautions against assuming adaptive headroom. It is not evidence that this ROSA design is novel. |
| [Agent Workflow Memory, Wang et al., 2024](https://arxiv.org/html/2409.07429v1) | Workflow shortcuts already exist. Its action-use analysis reinforces adoption measurement and handoff for semantic choices. Memory induction adds a separate lifecycle and is excluded. |

“AgentPRO” is ambiguous: the compiler preprint above differs from [Agent-Pro, ACL 2024](https://github.com/ZJU-OmniAI/Agent-Pro) and [AgentPro, EMNLP 2025](https://aclanthology.org/2025.emnlp-main.506/). No acceptance claim is made from the compiler paper's conference template text.

Public response-to-operation links are also an established API concept: [OpenAPI 3.1.1, Link Object](https://spec.openapis.org/oas/v3.1.1.html#link-object). GLBE needs reviewed tool contracts, not an OpenAPI migration. A JSON-schema string type alone cannot establish that a value is a node identity or that a consumer argument has the same meaning. [JSON Schema string reference](https://json-schema.org/understanding-json-schema/reference/string).

## 7. Weaknesses in v1 that v2 resolves

### 7.1 “Complete discovery” overstates the guarantee

A successful graph call returns what that observer discovered under its visibility policy and observation interval. It cannot prove a globally complete or atomic ROS graph. V2 distinguishes complete decoding of one response, coverage of the observed set, and independent task-level inventory validity. Empty discovery means “none observed in this scope,” not “no such nodes exist anywhere.”

### 7.2 The safety boundary is not just a tool name

An allowlisted wrapper can interpolate arguments into a shell, silently lose status, or call a generic side-effectful service. V2 requires typed graph/parameter clients, narrowly defined read capabilities, and argument-vector execution for terminal CLI metadata. Hardened primitives are shared infrastructure, not candidate-only advantages.

### 7.3 Two node readers do not demonstrate broad generality

Node-info and named-parameter reads share the same inventory/map structure. V2 adds a small topic-metadata transfer case using the same engine, while expressly limiting the claim to graph introspection and parameter APIs. A second application tests portability of these APIs, not arbitrary tool composition.

### 7.4 The fixed composite control is essential

V1 compares the fixed executor mainly with model-led batching. That can answer an integration question, but cannot distinguish an algorithm from packaging. V2 adds straightforward family-specific composites with identical backend, guards, result envelopes, and recovery rights. Their successful execution paths should match GLBE. If they do, report attribution to ordinary composition.

### 7.5 Failure handling needs explicit state

V2 separates transport, decoding, item validity, observed-set coverage, and answer correctness. It defines branch-local failures, globally fatal failures, pending identities, bounded outputs, and request-global retry keys that cannot be reset by regrouping calls. Oversized discovery is rejected before establishing a usable collection; ambiguous identities prevent complete status. A nested data field named `error` is not a transport status. Successful siblings are retained even when a child fails.

### 7.6 The two layers are justified only as small modules

The model-facing schema and shared executor are a useful responsibility split. They do not justify a new framework, elaborate intermediate representation, second planner, or service. Public `ROSA(tools=...)` integration is enough. Strong-arm prompt replacement requires a small isolated adapter because merely adding guidance leaves the default batching prohibition in place.

## 8. Alternatives considered and selection reasons

| Alternative | Decision | Reason |
|---|---|---|
| Two small operation schemas plus a shared bounded inventory/map engine | **Select** | Concrete inference-boundary hypothesis, simple authorization, and no task-specific endpoint knowledge. |
| One unrestricted tool-name/arguments composite | Reject | Allows undeclared tool choice and weakly typed argument binding; recreates the old plan interface. |
| General DAG, Python, or result-reference language | Reject for v2 | Broader capability is established, while historical adoption is weak. The immediate parameter example has a native dump alternative. |
| Bounded typed linear chains | Defer | Technically plausible, including public node-to-published-topic relations. They require additional typed output ports, lineage rules, and model syntax. No reviewed task establishes a decision-policy advantage over an equivalent fixed traversal; do not build that language just to claim a larger algorithm. |
| Validation-driven branch-local continuation | **Select as ordinary execution policy** | Uses actual status and budgets, preserves valid siblings, and needs no hidden semantic knowledge. Give it to the fixed control too. |
| Fail-fast versus best-effort as a novelty comparison | Reject | A strong ordinary executor can use the same best-effort rule. A weakened comparator would misattribute the gain. |
| Learned continuation/handoff cost policy | Reject for v2 | Missing counterfactual repair success, legal substitute actions, and calibrated remaining costs. Graph presence does not supply them. |
| Provider ranking, history, or workflow memory | Reject | Changes the selection problem and creates setup/shift costs. These are unnecessary for the selected hypothesis. |
| Candidate-only caching, filtering, concurrency, or safe backend | Reject | Confounds the mechanism. Equivalent legitimate capabilities belong in all strong arms. |
| Semantic coverage gate over user wording | Reject | Cannot certify intent and repeats a documented historical failure mode. |

The typed-chain alternative is not rejected because its performance has not been demonstrated. It is rejected as the initial implementation because its identified concrete gain is obtainable by simpler public-capability composition, while its interface introduces an additional failure surface. A future chain study would need a frozen workload that distinguishes compositional scope, not an artificially disabled native helper.

## 9. Exact runtime decision and why it is not a cost optimizer

At each child-dispatch checkpoint, the available inputs are the model-selected capability and literals, validated discovered IDs, per-child statuses, remaining operation/time/output budgets, and backend health.

The rule is procedural:

1. Stop globally on cancellation, exhausted budget, invalid discovery response, or trusted evidence corruption.
2. Skip and report an identity with ambiguous ownership or an invalid contract.
3. Continue the next authorized, valid, pending identity in deterministic order.
4. On a local child failure, retain the failure and continue valid siblings.
5. Return the accumulated envelope when the observed set is settled or a global stop occurs.

This requires no probability estimate. It can outperform a fail-fast implementation on coverage after a local failure, but the simple control receives the same rule. It therefore carries **no independent adaptive-policy claim**.

An eventual cost policy would need a checkpoint with at least two legal actions, information available before the choice, estimates of both outcomes including model repair, and a policy-only comparison on identical executor states. None is supplied by the current source/evidence. V2 does not make implementation conditional on launching another preliminary research round.

## 10. Fair evaluation and deadline decision

The standalone v2 freezes four roles: bounded original ROSA; strong ordinary ROSA with actual grouping and safe native dump; straightforward fixed composites; GLBE's shared-engine interface. It sets a 96-episode held-out design, explicit development adoption gates, correctness and cost rules, and failure preservation. It separates natural model behavior from deterministic schedule/contract checks.

The principal attribution questions are:

- **D versus B:** Does adding the whole discovery/read operation improve deployed agent behavior after schema, recovery, and validation costs?
- **C versus B:** How much of that effect is already explained by an ordinary composite?
- **D versus C:** Does the chosen interface preserve adoption and correctness with acceptable overhead? A tie is an expected, informative result, not a new algorithmic win.

The proposal is ready to implement as a bounded research candidate, subject to a new user instruction to begin implementation. It is not ready to claim efficiency, model adoption, general correctness, or algorithmic novelty. A focused implementation and matched study can fit before December 2 if scope remains fixed; another optimizer or plan language would weaken that schedule without a clear mechanism-level return.

**Final design judgment:** retain GLBE, narrow its claim, strengthen its contracts and controls, and test one coherent prototype. If ordinary composition explains all gains, the project's defensible result is a measured framework integration and its limits. Preserve that result rather than relabeling it as algorithmic superiority.
