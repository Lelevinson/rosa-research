# Mission B — Code-grounded investigation of ROSA tool-call efficiency

Date: 2026-11-09, Asia/Taipei. Scope: Mission B only; independent investigation, not implementation authorization.

## Decision

**A bounded compiler can generate useful ordinary JSON tools from reviewed ROS contracts. The inspected ROS capability graph does not yet justify claiming an algorithmic advantage over strong fixed helpers.** The strongest remaining candidate is a narrower methodological contribution: **choosing between compact parameterized interfaces and specialized generated functions under a measured schema budget, then testing their effect on unforced local-model use and full-answer cost.** Neither automatic composition nor budgeted coverage is new.

The important additional control is a **fixed parameterized traversal helper**. Its code can remain unchanged while a reviewed capability registry supplies new legal workflow choices. It can cover the same shallow combinations as generated functions without handwritten question-to-endpoint mappings. Comparing generated functions only against four GLBE-era helpers would leave this ordinary alternative unexplained.

Accordingly, reject CCVT's proposed *coverage over a fixed catalog* as sufficient justification for a new algorithm direction. Retain interface specialization as a conditional, falsifiable research candidate. Do not declare GLBE the answer by default either: it remains an integration design whose inference savings a same-path composite can match. A different, source-grounded opportunity—recovering valid parameter values from opaque failed bulk replies—is examined below; it also lacks a justified incremental algorithm claim at present.

**Crisp discriminator:** with identical contracts, bounded executor, legal workflows, native operations, recovery, and output evidence, do specialized generated functions beat one compact fixed helper on supported completion and total tokens/time? If the helper ties or wins, reject the proposed interface increment. If gains appear only against a narrow frozen catalog, they establish that catalog's limits, not superiority over ordinary composition.

## 1. Evidence boundary and inspected inputs

All six Markdown members of [the inbox ZIP](../../inbox/ROSA_Research_Investigation_Packet_2026-11-09.zip) were read: START HERE, the investigation brief, research context, GLBE v2, the previous Codex exploration, and the CCVT direction memo. The two design documents also present in `research/design/` are byte-identical to their ZIP members. Recommendations in those documents were treated as hypotheses, including the competing recommendations to retain GLBE and pursue CCVT. The investigation did not receive Mission A's output. A focused background literature review was part of this Mission B investigation.

Evidence labels used throughout:

| Label | What it establishes |
|---|---|
| Source | Inspected local code or installed public interface; no claim of runtime availability or performance. |
| Historical | Existing reports/source, read without rerunning scorers or experiments; original validity limits apply. |
| Literature | Primary publication text or publisher/arXiv record; no reproduction of reported results. |
| Proposal | Future interface, selection procedure, or test; nothing here was implemented or executed. |
| Judgment | Inference from that evidence, with uncertainty stated. |

Current checkout: branch `research/clean-foundation-20261108`, commit `94af17866cb82f3ea3f09422ef5cbb99b14cc89c`. Package metadata: ROSA project 1.0.10, LangChain 0.3.30, langchain-core 0.3.86, rosa-llm 0.1.0. Installed Debian packages: rclpy `7.1.12-1noble.20260902.053513`, rcl_interfaces `2.0.4-1noble.20260902.021729`, rosidl_runtime_py `0.13.2-1noble.20260612.050026`. These facts were read without importing ROSA or initializing ROS.

ROS documentation pages returned an access-denied page during browsing. Installed Jazzy source and official ROS GitHub source were inspected instead. Installed files are the authority for the signatures and line numbers below; a moving upstream Jazzy branch can differ from the installed package.

## 2. What the actual ROSA stack supplies and lacks

| Source finding | Design consequence |
|---|---|
| [ROSA accepts extra tools](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:82) and constructs the normal tool-calling agent/executor at [line 256](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:256). | An opt-in compiled interface is feasible without replacing ROSA's agent loop or model transport. |
| [ROSATools registration](/home/levinsonchen/project/rosa-research/src/rosa/tools/__init__.py:94) checks for `name` and `func`. | Generated tools need actual callable implementations; a schema alone does not create execution behavior. |
| [Node/topic info](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:174) and [service info](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:308) accept lists and loop internally. | Ordinary grouping already exists. No unavoidable model turn per entity should be assumed. |
| [The default prompt](/home/levinsonchen/project/rosa-research/src/rosa/prompts.py:81) prohibits multiple calls and batching. | Strong controls must replace the conflicting instruction. Appending contrary advice is insufficient. |
| [The runner](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:25) uses `shell=True`; `get_entities` can return an error string inside an entity list. | Composition needs shared safe primitives and authoritative transport status. These are backend repairs, not candidate-only algorithmic benefits. |
| [Parameter get](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:273) is scalar and returns CLI text; node/topic info also returns prose. | Current generic `dict` return annotations do not identify bindable typed output ports. Do not compile directly from today's input schemas. |
| [LangChain binds tools](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/tool_calling_agent/base.py:102); [tool schemas](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain_core/tools/base.py:558) describe inputs. Its [async dispatcher](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/agent.py:1543) already gathers independent actions. | Interface generation and bounded binding are possible; ordinary concurrency is not a missing invention. Match execution mode and caps. |
| [The installed model adapter](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/rosa_llm/langchain.py:140) rejects Ollama strict schemas and forced/parallel choice options. | Ordinary JSON does not guarantee valid selection. Actual unforced adoption and repair costs are decisive. |
| [Native parameter dump](/opt/ros/jazzy/lib/python3.12/site-packages/ros2param/verb/dump.py:70) already performs list-then-get. | Parameter enumeration followed by values is not a new dependent-execution opportunity versus a fair dump helper. |

The missing information is a versioned **output-and-relation contract**, not another input-schema parser. Such a contract must state nominal identity types, exact projections, multiplicity, effect, errors, temporal meaning, and what evidence reaches the model. Ordinary adapters may supply these facts from public APIs. They must not supply the meaning of an arbitrary user question.

## 3. Three concrete public read workflows

These are technically real API traversals, not observed executions or claims about task prevalence. The first two satisfy the requirement for distinct multi-family workflows; the third checks whether useful diversity extends to service/interface metadata. Namespace and parameter literals below are illustrative user inputs, not application fixtures.

### A. Topic inventory → publisher owners → configured parameters

Request: “For every visible topic under `/demo`, list its publisher nodes and each publisher's configured `use_sim_time`.”

| Stage | Public API and typed contract | Binding and result obligations |
|---|---|---|
| Topic discovery | [`Node.get_topic_names_and_types()`](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:2055) returns `List[Tuple[str, List[str]]]`. | Adapter validates canonical topic identities and scopes them by namespace segments. Keep returned type lists. |
| Publisher lookup | [`get_publishers_info_by_topic(topic)`](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:2221) returns `List[TopicEndpointInfo]`. | Each endpoint supplies node name, node namespace, type, GID and QoS. Preserve topic→endpoint lineage. |
| Owner projection and parameter read | [`TopicEndpointInfo`](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/topic_endpoint_info.py:33) supplies the owner fields; [`AsyncParameterClient`](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/parameter_client.py:40) uses standard node-relative parameter services. [`GetParameters.srv`](/opt/ros/jazzy/share/rcl_interfaces/srv/GetParameters.srv:8) takes names and specifies aligned values. | Project the owner into a nominal `NodeId`; copy literal parameter names unchanged. Validate the whole reply's cardinality/types. Preserve every parent edge even when one valid node read serves several parents. |

The publisher node can be outside `/demo`: the request scopes **topics**, not their owners. Multiple endpoints from one uniquely named node are not multiple node identities. Conversely, an endpoint GID identifies an endpoint; it does not disambiguate two parameter servers sharing a node FQN. Unknown owner records or observed duplicate node names must remain unresolved. Additional discovery used to check uniqueness costs an operation; lack of observed duplicates cannot prove unique node incarnation.

**Missing today:** typed endpoint adapters, qualified owner identities, ambiguity handling, per-parameter outcomes, and a lineage-preserving output envelope. No task-to-answer map is needed for this explicit request. Missing parameters and disabled parameter services remain possible.

**Beyond GLBE v2:** its topic-info operation is terminal; it cannot bind publisher owners into parameter reads inside the same transaction. However, a fixed helper `topic_owner_parameters(namespace, endpoint_role, parameter_names)` can do exactly this with `endpoint_role="publisher"`. It must receive the same shared typed backend and guards. This helper is not an oracle if frozen before evaluation.

### B. Node inventory → published topics → subscription endpoint metadata

Request: “For every visible node under `/demo`, list its published topics and the observed subscriber endpoints and QoS on each topic.”

The first stage uses [`get_node_names_and_namespaces()`](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:2102), returning node-name/namespace tuples. The next uses [`get_publisher_names_and_types_by_node(name, namespace)`](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:1971), returning topic/type tuples owned by that node. The third uses [`get_subscriptions_info_by_topic(topic)`](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:2251), returning typed subscription endpoints. Thus the nominal path is `NodeId → TopicId → SubscriptionEndpoint`; no parameter semantics are involved.

Keep node→topic→subscriber lineage. A shared topic can occur under several root nodes; do not erase those relationships when reusing an identical read. The subscribers can be outside the root namespace. A topic with no observed subscribers has an empty endpoint collection, not an inferred broken communication link. Endpoint metadata/QoS is not a delivery test or proof that messages reached a recipient.

**Missing today:** typed by-node topic projections and subscriber records, explicit parent preservation, bounded nested fan-out, and time-qualified evidence. Node disappearance can raise `NodeNameNonExistentError`; graph changes can produce a different endpoint set later.

**Beyond GLBE v2:** node info supplies first-hop wiring, but v2 has no transaction that feeds those actual topics into a subscriber-metadata reader. A fixed `node_topic_endpoints(namespace, node_role, endpoint_role)` helper with publisher/subscription choices performs the same work. Even v2 plus ordinary follow-up topic-info batching remains a fair fallback.

### C. Node inventory → provided service types → installed interface fields

Request: “For each visible node under `/demo`, list its provided services and the request/response field names and types for their interfaces; do not invoke the services.”

[`get_service_names_and_types_by_node(name, namespace)`](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:2015) supplies service/type tuples. [`rosidl_runtime_py.utilities.get_service(type_id)`](/opt/ros/jazzy/lib/python3.12/site-packages/rosidl_runtime_py/utilities.py:34) resolves an installed service class with `Request` and `Response`; generated message classes expose field/type metadata, supported by [`get_message_slot_types`](/opt/ros/jazzy/lib/python3.12/site-packages/rosidl_runtime_py/convert.py:248). This crosses graph ownership and local interface metadata, without making an arbitrary service request.

The nominal projection is `NodeId → ServiceTypeId → InterfaceSchema`, retaining the service-name association. The second stage can yield multiple advertised types; preserve all rather than selecting one by guess. A remote type may be uninstalled locally, and local schema/version equality with the remote endpoint is not established merely by matching a type name. Mark those limits. Dynamic imports load installed code: a future adapter must restrict resolution to trusted installed ROS interface packages, or use bounded installed interface-file parsing. This is not permission to import arbitrary graph-supplied Python modules.

**Beyond v2:** service-interface fields are absent from its fixed readers. An exact fair helper is `node_service_schemas(namespace)`. This is useful integration diversity, but its regular public structure makes it easy to add as one ordinary family helper. Interface availability was not tested here.

### Are these enough for a portfolio claim?

They establish **feasibility and more than one relationship shape**, not a representative distribution. Publisher/subscriber reversal, node-versus-topic roots, changed namespaces, and different parameter literals do not automatically create independent research families. All three workflows fit a small number of reusable parameterized helpers. No inspected workload establishes that useful combinations exceed a modest menu budget or that developers routinely encounter new relations requiring new wrapper code. Arbitrary service execution cannot be added to inflate diversity: its effect and semantic arguments are not supplied by a service type alone.

## 4. Public metadata versus manual semantic routing

| Legitimate declaration | Why it is public API knowledge |
|---|---|
| Endpoint `node_name` plus `node_namespace` projects to owner `NodeId`. | The graph API names those fields and their relationship. |
| By-node publisher lookup produces topic names associated with the input node. | Ownership is part of that operation's contract. |
| A named node's standard parameter reader accepts exact parameter names. | The standard parameter API defines this operation; the LLM/user supplies the literals. |
| Service type IDs resolve to installed request/response definitions, subject to availability. | This is interface introspection, not deciding what those fields mean for a task. |

Prohibited additions include “localization question → `/amcl_pose`,” “map frame → configured `frame_id`,” choosing a parameter name from question keywords, inferring that a publisher is the application's authoritative state source, and assuming a service named `get_*` is read-only. Shared JSON `string` types, matching field names, and co-occurrence in old traces establish none of these relations.

Public annotations still require human integration work. Record each adapter's owning API and version, and make the declarations available to every strong control. If adding a new application requires role names, expected values, benchmark IDs, or answer extraction tables, the claimed application-independent boundary has failed. Structural lineage establishes where an observation came from; it does not establish that the model selected the observation the user wanted.

Explicit output-to-operation links are already standard API-description practice: [OpenAPI 3.1.1, Link Object](https://spec.openapis.org/oas/v3.1.1.html#link-object). This is an analogy for reviewed bindings, not a proposal to migrate ROSA to HTTP/OpenAPI.

## 5. Closest prior art and the smallest remaining delta

The following comparison uses mechanisms, not papers' reported speedups. Full method text was inspected for LLM-Tool Compiler, HyperAgent and the older semantic-composition work; the background review also inspected ToolScope and State-Path method/appendix material. HyperTool and ToolPro claims here are restricted to their primary abstracts/publisher records. Implementations and published experiments were not reproduced. All seven principal pressure-point citations in the mission brief resolved to matching primary publications/preprints.

| Closest work | Inputs, decision and computation | Interface/preparation and failure implication | What remains different here |
|---|---|---|---|
| [LLMCompiler](https://arxiv.org/abs/2312.04511), planner/fetcher/executor | Model plans calls and dependencies; dispatcher schedules executable tasks. | Plan generation and result substitution already remove intermediate reasoning turns. Model planning errors remain possible. | Restrict execution to contract-enumerated shallow reads and avoid an additional planning call. No new dependency algorithm. |
| [LLM-Tool Compiler, §3](https://arxiv.org/html/2405.17438v1) | Request/tool-conditioned GPT fuser groups operations, using intent examples and type/name lookup checks. | Exposes fused operations as unified ordinary function interfaces; fusion preparation and possible wrong grouping matter. | Deterministic request-independent registration from authoritative contracts removes that fuser call and narrows what can be inferred. Ordinary generated composites are already established. |
| [HyperAgent, HyperGraph Construction and Agent Implementation](https://arxiv.org/html/2608.02650v1) | Schema hypergraph with joint input requirements and deficit-oriented support expansion. Inter-API links use LLM filtering/expert annotation; reported semantic planning/selection uses GPT-4o. | Executable supports depend on correct relationships and planning; graph construction is not free. | Only API-authoritative links, no runtime semantic support planner; gives up broader semantic planning capability. Hypergraphs/type composition are not the delta. |
| [HyperTool](https://arxiv.org/abs/2606.13663) | One executable interface accepts code that calls tools and passes intermediate values. | Uses synthesized, execution-verified training trajectories. Code adoption/training costs differ from ordinary function calling. | An untrained local model chooses normal JSON functions. One outer call and local dataflow are already known. |
| [ToolPro](https://proceedings.mlr.press/v306/liu26cb.html) | Tool programs, effect types, replay and profile-driven consolidation. | Expresses loops, joins, conditions and retries; needs program/effect/runtime machinery. | A bounded read-only subset reduces machinery and preparation. It does not invent effect-aware consolidation. |
| [ToolScope](https://aclanthology.org/2026.acl-long.1573/) | Merges redundant interfaces and filters using context. | Reduces menu ambiguity/context cost; erroneous filtering can remove necessary capabilities. | Generates dependency compositions rather than only merging redundancy, but must still justify menu cost and selection. |
| [The Menu Is an Execution Prior / State-Path](https://aclanthology.org/2026.emnlp-main.1577/), appendices A/C | Trajectory/path statistics train retrieval/reranking toward executable prerequisite-complete menus. | Needs training/history and request relevance; prerequisite coverage is explicit prior art. | Request-independent contract enumeration has no trained relevance signal. Avoiding training is a trade-off, not proof of better menus. |

The neighborhood outside recent agent papers is also decisive. [Relational semantic-service composition](https://arxiv.org/html/2005.05046v1) explicitly represents binary relations between parameter objects; [OpenAPI semantic-annotation composition](https://arxiv.org/html/2005.02628v1) automatically constructs compositions from enriched service descriptions. Therefore even “relations beyond matching shared string types” and “no LLM required to compose” are not new principles. The latter work assumes information services insensitive to world/time changes; ROS needs additional temporal qualifications. Ordinary observation intervals and rechecks address that obligation but do not by themselves create a new optimizer.

**Smallest plausible increment:** a controlled method for allocating a limited model-facing schema budget between a compact fixed interface and more descriptive specialized functions, using only reviewed public contracts, with explicit measurement of adoption, full-answer support, and cold/warm preparation costs. It is an interface/compilation adaptation. This investigation does not establish an unprecedented selection algorithm or a measured advantage.

## 6. A precise bounded compiler and portfolio rule

This section specifies a proposal sufficiently concrete to refute; it does not implement it.

### Compilation inputs and legal outputs

The registry contains capabilities and approved projections: nominal inputs/outputs, multiplicity, required literals, public source, effects, decoder/error contract, identity/time limits, and static wording fragments. It contains no request text, training task frequency, semantic endpoint routes, or expected answer. Enumerate only finite, acyclic workflows with at most two binding edges and three native-capability stages. A validated endpoint→owner projection is part of a stage's declared output, not a hidden fourth acquisition. Any separate identity-check observation is still charged native work.

Generate each function's arguments from the root's literal arguments plus unresolved reader literals. Fill entity arguments only at runtime from validated outputs. No generated Python, arbitrary result paths, runtime user-supplied tool IDs, or LLM-generated DAG enters the tool. Deterministic wording templates state the complete operation and output scope. For example:

```json
{"tool":"topics_publishers_parameters","arguments":{"namespace":"/demo","parameter_names":["use_sim_time"]}}
```

This is an illustrative tool-call envelope. The provider uses its normal function-call transport. The compiler generates the schema and binds it to a host-owned callable over a fixed executor. Registration occurs before constructing/binding the agent; changing a registry requires an explicit menu rebuild/rebind, not an assumption that the already-bound agent notices new tools.

Every workflow returns intermediate requested identities, relation lineage, delivered values, failures, observation intervals and unresolved work. Preserve GLBE's distinction between observed-set execution coverage and semantic answer correctness. Reject oversized discovery before admitting a usable collection; do not silently choose a prefix. Reject ambiguous identities, arbitrary service execution and unsupported bindings; preserve valid siblings and bounded direct fallback.

### Fixed parameterized helper: the necessary counterexample

A fixed `inspect_related(root_kind, namespace, relation_1, relation_2, reader, parameter_names)` function can interpret only the same approved relation combinations. All choices are bounded enums; invalid combinations fail validation. A still simpler representation is `inspect_workflow(workflow, namespace, parameter_names)`, where `workflow` is an enum of the same legal registered paths. New registry metadata can extend both interfaces without new application-specific code. The model emits ordinary JSON in either case; relation slots are a small additional selection burden, not free usability.

Use the same path enumeration and description fragments for this helper and specialized functions. Otherwise a compiler or better documentation advantage would be confused with representation. The helper's menu choices and registry-update rules must be frozen before held-out tasks. It cannot acquire a task-specific route after seeing a question. Conversely, do not freeze it to outdated metadata while allowing the candidate to consume new metadata.

### Operational portfolio selection, without invented utility estimates

Let `U` be the finite set of legal workflow contracts. A contract includes root scope, exact relation sequence, terminal reader and required exported lineage; namespace/parameter literal variations do not create new elements. Let candidate interfaces include one-path specialized functions and compatible grouped enum interfaces. `covers(i)` contains only workflows exactly expressible by interface `i`, with the same output obligations. Read count savings or task correctness are not inferred from this structural set.

Use the following initial rule:

1. Reserve the common primitive/fallback schemas. Define the total menu budget as their exact serialized token length plus 1,024 tokens of optional interfaces. This is a proposed resource setting, not an observed optimum. Use the actual provider tokenizer; if unavailable, report a byte budget and never relabel it tokens.
2. Canonicalize duplicate interfaces by schema and execution/output contract. Generate at most 12 optional interfaces using fixed templates. If the registry exceeds that design bound, retain the compact fixed helper instead of truncating discovery or inventing a semantic top-k selector.
3. For this deliberately small universe, examine all subsets of the optional interfaces. Admit only subsets whose **whole serialized menu** fits the budget. Choose the subset that covers the most distinct members of `U`; among ties, choose fewer menu tokens, then fewer functions, then stable lexical order. Charge this enumeration/tokenization at registration.
4. Never hide primitive fallback because a composition was omitted. Recompute only when the registry/version changes, not from the user question or held-out answer.

This is a finite coverage/representation procedure, not an optimizer for expected latency. Exhaustive subset search is bounded here by 12 interfaces; it is not a scalable algorithm claim. Whole-menu token measurement avoids pretending costs are necessarily additive. The underlying set-coverage objective is old: [Khuller, Moss and Naor, Budgeted Maximum Coverage](https://www.sciencedirect.com/science/article/pii/S0020019099000319). Only the primary abstract/problem statement was available reliably; no approximation guarantee is borrowed.

**Critical consequence:** if one small helper covers all of `U`, the stated rule selects it over an equally covering larger menu. If each specialized function covers one distinct path, a coverage-per-token greedy variant largely becomes “prefer short schemas.” Neither rule models how understandable a function is to the local LLM. Assigning unmeasured adoption probabilities or arbitrary task weights would hide that deficiency. Exposing the full bounded specialized menu as an evaluation arm is therefore necessary to test the interface hypothesis separately from this selector.

### Comparison with simple controls

| Control | Decision available without special knowledge | What would explain a candidate win or loss |
|---|---|---|
| Primitive batching/full menu | Model discovers, then groups reads using known IDs; native dump and ordinary reuse are available. | A saved intermediate model decision can be ordinary composition. |
| Frozen reasonable catalog | Reusable family helpers A/B/C above plus ordinary primitives; no post-task wrapper writing. | A coverage gain matters only if the parameterized-helper control does not explain it. |
| Fixed parameterized helper | Same registered paths and literals, one callable interface. | Equal coverage defeats a claim that one generated function per path is necessary. |
| Prerequisite-aware primitive menu | From a frozen lexical request/tool match, close transitively over all public producer alternatives needed for selected consumers; charge selection and schema costs, retain an explicit full-menu fallback. | Tests ordinary prerequisite coverage. A terminal reader requiring a literal ID does not itself mandate discovery; literals are legal alternatives. This is a simple analogue, not a reproduction of trained State-Path. |
| Exact same-path helper | A direct conventional function implementing the target workflow. | Same native schedule and ideal inference count are expected; report as an oracle if authored after task revelation. |

If menu limits exclude paths, report structural omissions separately from model selection failure. Request-independent uniform coverage cannot guarantee that the retained paths match real demand. If all useful interfaces already fit, there is no meaningful menu-allocation problem on that registry.

## 7. Historical failures that constrain this proposal

These findings were checked in saved reports and relevant source, not independently rescored from all raw traces.

| Historical evidence | Design consequence |
|---|---|
| [Baseline diagnostic](/home/levinsonchen/project/rosa-research-previous-20261108/research/baseline_diagnostic/report.md:5): batch wrapper never invoked; 23 repeated CLI reads, but only 14 reads/5.536 s in supported episodes qualify as native opportunity; closeout discovery failed. | Capability availability is not adoption. Do not infer model-time savings from repeated command durations or repair the missing closeout retrospectively. |
| [Structured multistep report](/home/levinsonchen/project/rosa-research-previous-20261108/research/multistep/report.md:197): zero intended dependency references; 77 versus 63 model requests on 12 limited first-object-supported pairs. Its [source review](/home/levinsonchen/project/rosa-research-previous-20261108/research/multistep/independent-source-review.md:13) found generic bounded execution, not application answer maps. | The earlier mechanism was unused; it does not falsify all binding designs. Measure emitted valid calls, activated dependent reads and final answers separately. Primary traces were subsequently lost; preserved summaries do not enable a new raw audit. |
| [CodeAct pilot](/home/levinsonchen/project/rosa-research-previous-20261108/research/paper_pilot/report.md:64): nine programs, five rejected before reads, three partial/failing, one complete; continuation had no matched strong-control task pair. | Ordinary JSON is a plausible interface simplification, not evidence of superiority. Do not claim CodeAct failed generally or compare unmatched efficiency rows. |
| [Round 25 strong graph control](/home/levinsonchen/project/rosa-research-archive/research/internal/round25_graph_control_review.md:115): both arms 22/24; simple control 42 versus candidate 44 data acquisitions on matched complete tasks. [Round 26](/home/levinsonchen/project/rosa-research-archive/research/internal/round26_experimental_results.md:120): ordinary dynamic readiness expressed the claimed scheduling repair. | Share already-paid metadata, grouping, reuse, ready-list scheduling and failure rights. A new name does not change the decision. |
| [Round 28](/home/levinsonchen/project/rosa-research-archive/research/internal/round28_experimental_results.md:102): selective arm 6/8 strict feasible versus 8/8 original and strong prompt/compiler. [Round 27 application source](/home/levinsonchen/project/rosa-research-archive/research/experiments/round27/application.py:23) contains prepared field/source bindings. | No imported application field map or executor success flag may stand in for user-request coverage. Source identity, acquisition, rendering and unsupported assertions need distinct judgments. |

No AutoTool end-to-end failure is inferred from the earlier feasibility-only missions. Old retrieval scores without original raw traces are not reused as validated evidence here.

## 8. Different bottleneck investigated: opaque bulk-parameter failure

**Source:** the installed [`ParameterService._get_parameters_callback`](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/parameter_service.py:80) catches undeclared/uninitialized parameter exceptions, replaces the response with an empty values list and returns. It can discard valid earlier values in the same request. This differs from the normal [GetParameters aligned-result contract](https://raw.githubusercontent.com/ros2/rcl_interfaces/jazzy/rcl_interfaces/srv/GetParameters.srv), which documents positional values and `PARAMETER_NOT_SET`. The same exception branch is visible in [official rclpy source](https://raw.githubusercontent.com/ros2/rclpy/jazzy/rclpy/rclpy/parameter_service.py).

That is a concrete acquisition/recovery issue, independent of generated tool menus. A generic mechanism could request a batch and, **only after a transported but invalid-cardinality response**, recursively split its names, retaining valid sub-batch replies and explicit unavailable singleton outcomes. Do not split on endpoint timeout: it is not evidence that one parameter poisoned a batch. Do not call an empty malformed reply proof that every parameter is absent. Timeouts, cardinality faults and well-formed `NOT_SET` values need separate handling.

The policy needs no user-question routing. It makes a real native grouping/recovery decision. However, it is ordinary adaptive partitioning/group testing inside a fixed helper; a defensible contribution would require an additional justified decision, not the name of this pattern.

The strong controls are: one batch then scalar fallback; native `ListParameters` then a filtered bulk read; and independent singleton reads. Under a hypothetical stable eight-name request with one undeclared name, balanced recursive splitting uses seven requests, singleton reads eight, while a successful list plus one filtered get can use two. With no poisoned name, direct bulk uses one versus list-plus-get two; if every singleton is invalid, full splitting can use fifteen. These are analytically counted hypothetical schedules, not measurements. Listing does not solve uninitialized-but-declared values or make subsequent reads atomic.

A credible selector would need predecision evidence about failure frequency, listing cost/size, server behavior and remaining budget. None is established by source inspection or the existing workload reports. Retrying split keys would also conflict with v2's one-additional-attempt rule unless a new shared recovery protocol were explicitly frozen; no hidden exemption is acceptable. Consequently, **do not replace CCVT with a claimed new adaptive parameter algorithm now**. A later recovery study would have to beat list/filter and ordinary fallback with all failed requests charged. This investigation found a real failure mechanism, not a justified positive research result.

Temporal/identity validation was also considered as a bottleneck: a node can restart or graph relationships can change between stages. A graph epoch or extra recheck does not certify parameter-server incarnation, and ordinary revalidation plus the project's historical epoch controls remain strong competitors. No cheaper correctness-preserving decision signal was established here.

## 9. Minimal coherent future prototype and decisive test

Nothing in this section was executed. It describes the smallest coherent discriminator if the advisor elects to investigate the remaining interface trade-off.

### Prototype boundary

Use three small opt-in responsibilities: (1) reviewed capability/relation contracts and deterministic interface templates, (2) shared typed ROS reads plus bounded identity/lineage receipts, and (3) the finite compiler/selector and fixed parameterized adapter over the same executor. Register through `ROSA(tools=...)`. A study driver owns isolated prompts, traces and arm construction. No ROSA-core, model-transport, dependency, application-controller or historical-source change is indicated.

Start with workflows A and B. Add C only as an explicit public-contract extension shared by all arms, not as an arbitrary service execution facility. Keep v2's resource limits as starting values: 16 admitted entities at each collection stage plus a 64-attempt request-global native cap, 32 parameter literals, 8 issued model requests, 45-second composite/180-second request deadlines, 8 KiB per-native delivered payload and 24 KiB composite envelope. Nested fan-out must also fit the global budget; 16 per stage does not authorize an unbounded cross product. Overflow is explicit partial/rejection, never silent truncation. Freeze any changes before evaluation and apply them to every strong arm.

### Development gate and freeze

Before held-out use, future implementation checks would establish identity ambiguity handling, namespace boundary rules, lineage conservation, reply cardinality, no shell/service-write path, output limits and cancellation. In a disposable simulator, verify the same-path executor schedules agree. Then use eight development requests: six eligible A/B/C requests and two direct/ineligible cases. Require at least five of six appropriate first calls in both specialized and fixed-helper representations, all six supported answers after permitted recovery, real batching in the primitive control, and no unsafe dispatch. Allow one development-only correction per affected interface, preserving the previous version; stop if activation still fails.

Freeze exact contracts, schemas, prompts, model digest/options, tokenizer/budget, primitive concurrency, recovery rules, tasks, scorer and fixture recipe before held-out model calls. A registry relation can be new to the frozen catalog, but its capability and metadata must be supplied equally to every strong arm. Updating a helper's metadata-driven choices must be allowed under its predeclared rule. Merely changing namespaces or values is instance transfer, not unseen composition.

### Small matched study

Use five arms: **B** strong primitive batching/full menu; **C** frozen practical family-helper catalog; **G** compact fixed parameterized workflow helper; **D** bounded generated interface portfolio; **P** prerequisite-aware primitive menu. All retain legitimate ordinary fallback. Report a same-path conventional helper as an oracle reference when authored after task revelation. Original-default ROSA is optional descriptive context, not needed for the decisive attribution.

Six eligible requests, two per workflow A/B/C, two repeats and five arms give **60 proposed episodes**. Include four additional cases once per arm—known direct identities, empty root set, observed ambiguous/disappearing identity, and a request requiring measured state rather than configuration—for **20 robustness episodes**. These are 80 bounded future attempts, not an authorized run or a population-level correctness test. Repetitions and rewordings do not multiply independent workflow families. If no credible held-out relation combination can be specified without artificially withholding a general helper, label the portfolio claim untestable on this scope and omit that claim rather than manufacturing workloads.

Keep serial native execution initially to isolate representation. Both G and D use the same enumerated paths and output templates. Record D's actually selected menu; if the coverage rule selects G's representation, that is an informative negative selector result. A full bounded specialized-menu variant can then be reported only as a separately frozen representation ablation, not silently substituted for D. No training or extra model planner is included. Published learned methods are conceptual/mechanism comparisons unless actually reproduced with all their preparation charged.

### Measurements and rejection rules

Score independent full-answer support and complete requested identity/field coverage first. Include extra prose assertions, correct source ownership, honest partials, and appropriate abstention. Execution success and strict JSON formatting are separate. Bracket stable fixture episodes independently; preserve dynamic transitions with timestamps. Missing brackets mean indeterminate coverage, not a regenerated clean run.

Measure every actual model request including repair/errors, provider input/output tokens, total schema tokens, registration/tokenization CPU, observer startup, delivered observation size, native graph observations/RPCs/subprocesses, waits, retries, serialization and end-to-end time. Keep all-attempt expenditure and completion, then compare efficiency only on identical mutually supported pairs. Do not double-count nested timing intervals. Persist traces beyond `/tmp`; missing usage is unknown.

Reject the claimed increment if:

1. G matches D's supported completion/adoption with equal or lower total cost; D's combinational coverage alone is then explained by an ordinary fixed interpreter.
2. D loses requested coverage, invents source equivalence or hides unresolved targets, regardless of apparent savings.
3. D only beats B/C by removing ordinary model boundaries, while G or the same-path helper matches it.
4. Extra schemas, wrong selections, compilation or repair erase savings on supported pairs; show both cold registration and a stated amortized reuse scenario.
5. The available meaningful workflows fit the simple menu, so portfolio selection never faces a real resource trade-off.

A positive narrow result would require D to preserve full support and show an actual adoption or token/time advantage over G as well as B/P on held-out combinations, with equal native information. Even then, the supported claim is an empirical interface-specialization method on a small public ROS registry, not novel composition theory or broad robot reliability. One local model and three workflows cannot establish general noninferiority.

## 10. Mission B answers and handoff

| Mission B requirement | Investigation answer |
|---|---|
| Useful normal JSON virtual tools without task/answer maps or model-generated plans? | Yes, with reviewed output/projection contracts and host-owned implementations; today's ROSA input schemas alone are insufficient. Sections 2–4 and 6. |
| Precise bounded compilation/portfolio rule and strong controls? | Finite two-edge enumeration, explicit schema budget and coverage/token tie-breaking; the rule can collapse to the compact helper. Primitive, fixed-catalog, prerequisite-menu and same-path controls are explicit. Section 6. |
| Annotation boundary? | Public ownership/identity/type relations are permitted; semantic source selection and application answer routing are not. Section 4. |
| Concrete workflow beyond v2 and exact fair helper? | A/B/C supply different relation paths and named ordinary helpers; none proves per-workflow execution superiority. Section 3. |
| Minimal prototype, decisive test and diversity limit? | Shared executor with representation-only contrast, explicit activation/freeze/falsification and a small proposed matrix; sufficient representative composition diversity remains unestablished. Section 9. |
| If weak, investigate another bottleneck? | Opaque bulk parameter replies support adaptive recovery, but list/filter and ordinary fallback challenge it; no justified new selector or measured opportunity. Section 8. |

**Recommendation to the advisor:** do not adopt “CCVT v3” as a newly established algorithm. If pursuing one bounded candidate, investigate compact-versus-specialized contract-derived interfaces with G as the decisive control. This is the strongest technically realistic residual trade-off found here. If an algorithmic advantage beyond ordinary fixed composition is mandatory at proposal time, the present outcome is **explicit rejection for insufficient evidence**, not a positive direction disguised by a new name. It does not establish that no such improvement exists.

**Ringkasan Indonesia:** Rangkaian ROS lintas tool memang bisa dibuat otomatis dari kontrak API publik. Tetapi satu helper biasa dengan pilihan workflow juga bisa mencakup rangkaian yang sama. Jadi, pertanyaan riset yang masih masuk akal adalah apakah fungsi hasil kompilasi lebih mudah dipilih model dan lebih hemat setelah biaya menu serta perbaikan dihitung. Belum ada bukti bahwa ini algoritma baru yang unggul. Masalah kegagalan parameter batch juga nyata di source, tetapi solusi sederhana harus dikalahkan dahulu. Tidak ada implementasi atau eksperimen yang dijalankan dalam misi ini.

## Appendix: provenance and preservation

Inbox ZIP SHA-256: `f6db7dbe97d07218a12d50fd79621b019a080c47a47d9e732270b0685624ab47`.

| Read ZIP member | SHA-256 |
|---|---|
| `ROSA_START_HERE_2026-11-09.md` | `e2199cba9b42283587ceab0399b68de24d5a3d519a6b519e787cf469b5380e70` |
| `ROSA_Investigation_Prompt_Work_and_Codex.md` | `b6551735b203d5fa017c684ab66b8e6fc64a0656391b63840f3951e3d97c6c63` |
| `ROSA_RESEARCH_CONTEXT.md` | `2e45d916b40a7d3fab160a0c317949dde67518eeeed72aa54e6802ec2276a4f9` |
| `ROSA_Algorithm_Specification_v2_2026-11-08.md` | `e312a953dccdac648a2a892e01a4cfee9f8e05555d52da28f2a66a4036838931` |
| `ROSA_Algorithmic_Contribution_Exploration_2026-11-09.md` | `d51760357faa1e480b2511cabb8d2aecaa4c6203438beadda83a9de2f3974bf0` |
| `ROSA_Research_Direction_Decision_2026-11-09.md` | `cbb922da1abc73de576de3e96ddb528302164971871f06683d0d3d0eb6364068` |

Installed rclpy source hashes used for exact local API/behavior claims:

| File under `/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/` | SHA-256 |
|---|---|
| `node.py` | `8b7fe0ea64e0de12cc1d5d01ebf56c202fa6e153251eb71dfff93e35eb5b3c80` |
| `topic_endpoint_info.py` | `d4271d3d6fc8fecd74e96e61e2651cfbdb04a95572280af04364dce4fa20b6e9` |
| `parameter_client.py` | `31daa88e9477e61c507c6ba93fa7319d56580637010c946f6d4a5576e0123ff9` |
| `parameter_service.py` | `f7546866ac5e9443b5524f1ec0e63eeb8bdca1041e7392d2390d5f5b68396aaa` |

Only this standalone report was added. Existing inbox/design documents, source, dependency files, tests, historical reports and Git history were preserved. A before-write hash manifest of 38 existing workspace files was used for the final preservation check. Read-only work comprised archive/text inspection, package metadata, Git status/identity, hashes and public literature/API browsing. No ROS process, model inference, algorithm prototype, benchmark, test suite, paid inference, commit or history operation was executed.
