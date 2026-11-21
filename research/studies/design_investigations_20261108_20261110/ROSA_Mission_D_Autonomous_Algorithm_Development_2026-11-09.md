# Mission D — Autonomous, code-grounded algorithm development for ROSA

Date: 9 November 2026, Asia/Taipei. Presentation deadline: 2 December 2026.

Scope: independent Mission D, research and design only. This report contains no new implementation, ROS execution, model inference, benchmark, or measured performance result. All example observations and operation counts below are hypothetical traces or manual calculations, explicitly identified as such.

## 1. Executive selection and confidence/limits

**Reject the investigated mechanisms as a presently justified new algorithmic contribution. Select a compact ordinary read helper with explicit evidence contracts as the concrete systems alternative.** Do not begin a general workflow compiler, alias-selection campaign, or adaptive parameter-recovery optimizer on the strength of this investigation.

This conclusion follows three proposal–criticism–refinement cycles, rather than stopping at the first fixed-helper objection:

1. Contract-generated dependent reads have a real execution use, but a capability-equivalent parameterized ordinary helper has the same reachability and inference boundaries.
2. Budgeting specialized names is a genuine interface decision, but additional primary sources already optimize schema names and failure-driven documentation. The remaining deployment-budget increment has no established ROSA workload, adoption advantage, or calibrated traffic assumptions.
3. Opaque parameter-batch failure is verified in the installed ROS implementation. Recursive recovery changes a real native decision. However, established bisection, ordinary scalar recovery, and a stronger type-screened native alternative defeat its immediate justification. A retry-aware refinement collapses to scalar recovery under the existing shared per-key protocol.

**What is selected:** one ordinary JSON helper supporting two explicit public read workflows, plus direct read primitives; typed receipts; bounded result-dependent execution; model-directed singleton recovery when a parameter batch loses correlation; no semantic routing, generated programs, learned selector, or automatic retry. Section 4 specifies it sufficiently for a later implementation without another broad audit. It is a systems design assembled from known mechanisms, not a renamed novel optimizer. The second workflow extends beyond GLBE v2's terminal readers, but that extension does not establish an algorithmic advantage.

**Confidence:** high in the inspected code facts and the successful-path equivalence arguments; moderate in the project-scope rejection; low in predictions about local-model adoption and practical savings. The search does not establish that no worthwhile algorithm exists. It establishes that these proposals do not yet justify that claim under the required controls and deadline. No new Mission C report was read.

The defensible future claim is conditional: a bounded ordinary composite may reduce intermediate model decisions while preserving delivered evidence. Its value must be measured against activated batching and native alternatives. A result tying a same-path helper supports ordinary composition, not new algorithmic superiority.

## 2. Source-backed problem inventory and paper comparison

### 2.1 Evidence and provenance

Evidence labels used throughout:

| Label | Meaning |
|---|---|
| **Source** | Local implementation or installed interface inspected as text; no runtime validation. |
| **Literature** | Primary paper, author source, or publisher record inspected; no reproduction of its experiments. |
| **Historical** | Saved project reports/source; original validity limits remain. |
| **Design** | New proposed interface, policy, limit, or prospective protocol. |
| **Inference** | Reasoning from the preceding evidence, including hypothetical schedules. |

All five required reports were available and read directly from `research/inbox/ROSA_Algorithm_Development_Packet_2026-11-09.zip`: canonical context, Mission A, Mission B, GLBE v2, and the independent GLBE critical review. The archive's START HERE and Mission D brief supplied the deliverable requirements. Mission C's brief was visible in the packet; its new output was neither accessed nor used. The older `old.zip` was unnecessary once the dated development packet was identified. Historical documents' instructions to implement or update context were treated as historical material, not authorization for this task.

Current source checkpoint, independently rechecked: branch `research/clean-foundation-20261108`, commit `94af17866cb82f3ea3f09422ef5cbb99b14cc89c`; installed metadata identifies LangChain 0.3.30, langchain-core 0.3.86, and rosa-llm 0.1.0. Initial Git status already showed untracked `research/`; it was not a fully clean working tree. No existing file was edited.

### 2.2 What the actual stack does

| Verified source | Consequence for the decision |
|---|---|
| [ROSA constructor](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:82), [tool addition](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:278), [registry](/home/levinsonchen/project/rosa-research/src/rosa/tools/__init__.py:94) | Extra callable tools can be registered through `tools=`. They supplement the defaults; they do not replace or restrict them. A schema without a callable is insufficient. No replacement agent framework is needed. |
| [Agent/executor construction](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:256), [installed binding](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/tool_calling_agent/base.py:102) | Tools are bound during construction. A later schema change requires rebuilding/rebinding; changing a registry object alone does not update the model menu. |
| [Existing node/topic info](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:174) | Lists already group known entities, although their native calls are synchronous loops. There is no necessary model call per entity. |
| [Installed async dispatch](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/agent.py:1543) | Independent emitted actions already use `asyncio.gather`. Concurrency is an existing capability. Source inspection here does not establish its actual throughput. |
| [Default prompt](/home/levinsonchen/project/rosa-research/src/rosa/prompts.py:81) | It explicitly prohibits multiple calls and batching. A strong control needs an isolated replacement of that instruction. Appending contradictory advice is inadequate. |
| [Prompt construction](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:293) | Robot prompts append to the module-global list. Future arm construction needs copied prompts/fresh workers to prevent contamination. |
| [Legacy runner and discovery](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:25) | `shell=True` and error strings inside entity lists make these unsuitable binding contracts. A shared safe facade is infrastructure for every strong arm. |
| [Model adapter](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/rosa_llm/langchain.py:154) | Ordinary JSON function calling is supported. Ollama strict schemas and forced/parallel-choice settings cannot be assumed. The adapter transports calls; it does not execute ROS tools. |
| [Invocation](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:134), [stream events](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:170) | `invoke()` returns final text. Token/call accounting requires callbacks or event traces; printed OpenAI-only usage is inadequate for ChatRosaLLM. |
| [Native dump](/opt/ros/jazzy/lib/python3.12/site-packages/ros2param/verb/dump.py:70) | List-then-get already exists natively. Its unchecked `zip` is not acceptable correlation validation. Give strong controls a bounded equivalent. |

The missing contract is principally about **outputs and public relationships**, not input JSON syntax. An input accepting a string does not establish that another tool's string is the correct source identity. Public API ownership links are legitimate; handwritten user-question-to-endpoint mappings are excluded.

### 2.3 Historical bottlenecks, with limits

These records were checked in their current saved locations; no scorer or raw experiment was rerun.

| Historical record | What it supports here |
|---|---|
| [Baseline diagnostic](/home/levinsonchen/project/rosa-research-previous-20261108/research/baseline_diagnostic/report.md:5) | The added batch wrapper was unused. Fourteen repeated reads/5.536 seconds in supported episodes were an opportunity bound, not achieved savings or avoided inference. |
| [Structured-dependency study](/home/levinsonchen/project/rosa-research-previous-20261108/research/multistep/report.md:197) | Zero intended result-reference adoption; 77 versus 63 model requests on the limited first-object-supported pairs. Missing primary traces prevent a new full raw audit. This does not falsify all dependent execution. |
| [CodeAct-style pilot](/home/levinsonchen/project/rosa-research-previous-20261108/research/paper_pilot/report.md:64) | Nine program invocations: five pre-read rejections, three partial/failing, one complete. No valid matched strong-control continuation pairs. This is an interface warning and inconclusive efficiency evidence. |
| Packet context and Mission B's R25–28 source review | Ordinary controls explained earlier scheduling/reuse gains; semantic maps and omitted fields damaged cross-application validity. These historical summaries are not new measurements or independent rescoring. |

There is no observed frequency estimate for poisoned parameter batches, no demonstrated compact-helper repair rate, and no representative distribution of new workflow compositions. Source feasibility cannot supply those missing quantities.

### 2.4 Closest primary mechanisms

This table makes narrow mechanism comparisons. Published benchmark improvements are not imported into ROSA predictions.

| Primary source and inspected extent | Existing mechanism | Consequence/delta |
|---|---|---|
| [LLMCompiler, v3, §§3.1–3.4, June 2024](https://arxiv.org/html/2312.04511v3#S3), method text | Model plans dependencies; fetcher substitutes results and dispatches ready work; executor runs independent tasks; replanning handles changing needs. | Binding, readiness, and simple precompiled branches are established. Restricting them to public ROS reads is an integration specialization. |
| [ReWOO, §2.1, May 2023](https://arxiv.org/html/2305.18323v1#S2.SS1), method text | Plan, work, and solve separate reasoning from evidence acquisition. | Avoiding repeated observation-conditioned reasoning is an established mechanism. |
| [CodeAct, §§2.1–2.4, June 2024 v4](https://arxiv.org/html/2402.01030v4#S2), method text | Executable code composes calls and uses intermediate observations. | A JSON enum sacrifices expressivity to reduce adoption risk; it is not more expressive execution. |
| [LLM-Tool Compiler, §3, May 2024](https://arxiv.org/html/2405.17438v1#S3), method text | A model fuser identifies operations; lookup checks and definition construction expose fused functions through ordinary calling. | Fused JSON functions already exist. Registration-time public composition avoids a serving fuser but restricts available workflows. |
| [PA-Tool, ACL 2026, pp. 20695–20719](https://aclanthology.org/2026.acl-long.948/), publisher abstract and [author repository](https://github.com/holi-lab/PA-Tool) | Training-free schema adaptation samples names and selects by a peakedness signal of model familiarity. | A familiar specialized name is not itself a new contribution. Full PDF was unavailable to the background reviewer; no section-level claim beyond verified material is made. |
| [DocsChisel, August 2026 v1, §§III-B–E](https://arxiv.org/html/2608.10037v1), method text | Iterative failure diagnosis edits documentation fields; final selection maximizes validation success and breaks ties by shortest documentation. | Even success-first, size-aware schema refinement has direct precedent. A recurring optional-alias budget would be a narrower deployment question, not this mechanism's invention. |
| [State-Path Tool Menu, §§3.1–3.4, September 2026 v1](https://arxiv.org/html/2609.09395v1), background primary review | Learns request/state/path representations to retrieve runnable routes and order prerequisites. | Dependency-complete menu construction already exists. Our fallback performs neither learned retrieval nor semantic pruning. |
| [Aldridge, Rates of Adaptive Group Testing, v2, §III](https://arxiv.org/html/1901.09687), algorithm text | Adaptive pooling and binary splitting use prior test outcomes; population assumptions determine the useful grouping regime. | Splitting opaque failures is an application of established search. Its stable binary-test assumptions do not automatically hold for ROS transport faults or churn. |
| [AWS Lambda, DynamoDB error handling](https://docs.aws.amazon.com/lambda/latest/dg/services-dynamodb-errors.html), official documentation | Failed batches can be bisected to isolate bad records under explicit retry controls. | Practical failure-isolating batch recovery is also established systems behavior. ROSA must charge every attempt; AWS's quota convention is not borrowed. |
| [OpenAPI 3.1.1, Link Object](https://spec.openapis.org/oas/v3.1.1.html#link-object), specification | Explicit links connect response data with subsequent operation parameters. | Reviewed output-to-input links are established API-description practice, not automatic semantic understanding. |

Eddies was also considered as an older adaptive-query-processing parent. The background reviewer obtained indexed method extracts but could not load the full author PDFs. No decisive conclusion depends on a claimed full Eddies review. Similarly, the packet's descriptions of ToolPro/HyperTool were not promoted here into independently verified full-paper claims.

## 3. Independent iteration ledger

The cycles below were performed through reasoning, source inspection, and primary-source checks. “Success” describes a plausible witness, not an executed task. An ordinary function can implement any algorithm; that observation alone is not a refutation. The relevant challenge is whether a credible simple policy, with identical predecision information and capabilities, already makes the same decisions or wins the proposed trade-off.

### Cycle 1 — generated workflows → compact full-capability control

**Proposal:** enumerate shallow public read paths, generate a normal function for each, and expose the generated menu. Runtime input is an approved path plus user/model literals. State comprises validated observations, pending bindings, receipts, and budgets. The model chooses the semantic operation; the host binds actual identities and executes it.

**Successful witness:** discover `/demo` nodes, fetch their published topics, and retrieve subscriber endpoints for each topic. This removes intermediate selection turns without requiring `$ref` syntax.

**Attack:** a fixed `inspect_ros_reads(workflow, namespace, parameter_names)` interpreter over the same two legal workflows performs exactly those operations. New approved metadata can extend its choices under the same registration rule. Freezing that control to an outdated catalog while updating the candidate would manufacture an advantage. LLMCompiler and LLM-Tool Compiler independently cover the main execution/interface ingredients.

**Refinement:** keep the ordinary compact interface as the full-capability substrate. Stop claiming novel execution or unseen-path coverage. Consider optional specialized names only if they change actual selection/recovery cost. This leaves a different decision for cycle 2 rather than merely renaming the compiler.

### Cycle 2 — optional alias budget → model-aware documentation overlap

**Proposal:** at registration choose zero or one specialized alias using development paired costs, retaining the compact helper and all legal capabilities. Observables are exact rendered schema size, development full-support outcomes, all-turn token differences, and a declared target-traffic share. No new model planner is used at serving time.

**Successful witness:** a model repeatedly chooses an invalid workflow literal in the compact helper but reliably chooses an explicit `inspect_node_topic_subscribers` name. An alias could avoid repair. If the compact call is already correct on its first turn, both need two ideal model requests and the alias adds recurring context.

**Attack and calculation:** suppose development estimates a gross saving of `d` tokens on target requests, a non-target penalty `h`, and extra alias-schema cost `s` per model request. At target share `q` and at most `K` model requests, a conservative planning score is `q*d - (1-q)*h - K*s`. This is the packet's break-even idea, not a new algorithm. None of `d`, `h`, or credible `q` is measured for the proposed interface. A fixed best development alias or simple frequency-per-token rule may match it. PA-Tool adds a direct training-free naming precedent; DocsChisel adds failure-driven refinement and support-first/shorter-document selection.

**Refinement:** a support-constrained, zero-or-one selector could still be an empirical deployment adaptation if it beat those simple selectors on independent families after preparation costs. It remains scientifically possible. However, it now requires profiling, traffic assumptions, and real family diversity beyond the present evidence. Do not select it as Mission D's algorithm merely because Missions A/B left it open. Its minimal contrast remains compact-only versus a fixed development alias versus the calibrated selector, all sharing execution. Withdraw the novelty claim if closest-method replication explains any effect.

**Decision:** reject it as the selected project direction for this deadline; preserve the exact conditional question above. No interface failure has been experimentally demonstrated here.

### Cycle 3 — opaque batch recovery → retry-aware reservation → native screening

**Verified failure:** installed [ParameterService callback](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/parameter_service.py:80) resets the entire response to an empty array on undeclared or statically uninitialized parameters. Previously accumulated valid values are lost. That differs from the positional [GetParameters contract](https://raw.githubusercontent.com/ros2/rcl_interfaces/jazzy/rcl_interfaces/srv/GetParameters.srv). This behavior is also discussed in the upstream [ROS issue #2512](https://github.com/ros2/rclcpp/issues/2512). It is not a new ROS bug discovery by this mission.

**Proposal:** after a transported but wrong-cardinality batch, recursively split parameter names, retaining successful sub-batches and unresolved singleton outcomes. Observable inputs are requested literal names, validated reply cardinality, per-key participation counters, and remaining budgets. The model still chooses nodes/parameters. The host changes grouping, not semantic sources. Never split a timeout on the assumption that one name poisoned the batch.

**Successful witness:** eight stable requested names, exactly one undeclared name, all other values available. Full binary splitting can recover seven values in seven total value requests. That is fewer than eight initial singletons or nine requests for a failed batch followed by eight singletons. These are manual counts, not measurements.

**First attack:** the operation is ordinary bisection/group testing. A fixed adaptive helper can implement it; the closest practical control already exists in batch-recovery systems. It needs no generated tool menu. A successful `ListParameters` followed by a filtered value request takes only two requests in the stable undeclared-name case. Every missing requested name must retain an explicit listing-based outcome, not vanish from the answer.

**Refinement:** reserve enough request budget to give each unresolved name a final independent read. Split only when reservations and retry keys permit it; otherwise switch to singletons. This uses actual counters rather than invented defect probabilities.

**Second attack, decisive protocol constraint:** GLBE v2 allows one additional failed logical-read attempt, shared across wrappers and regroupings. The failed initial batch consumes one participation for every requested value key. A failed recovery batch containing two or more names can consume the final allowed participation of a valid peer. That peer then cannot be independently recovered. Therefore singleton fallback is the only grouping that gives every unresolved name its own final observation opportunity under arbitrary poison placement. It does not guarantee transport success. A total remaining budget of `n` alone is insufficient for this argument; the **per-key** cap is essential. Sparse single-poison splitting can sometimes fit that total while still violating the key cap.

**Third attack, stronger ordinary native alternative:** source inspection found that [GetParameterTypes](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:630) reads the stored type without the uninitialized-value exception raised by [GetParameter](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:665). Thus `ListParameters → GetParameterTypes → omit NOT_SET from the value batch → GetParameters` can screen that particular stable uninitialized case. Preserve `NOT_SET` as a type observation and lack of an acquired value; do not infer its static/dynamic cause without descriptor evidence. Types/describe batches can themselves lose correlation on undeclared names, and changes between calls invalidate any atomic interpretation. [Official Jazzy node source](https://raw.githubusercontent.com/ros2/rclpy/jazzy/rclpy/rclpy/node.py).

| Eight-name stable hypothetical case | Singletons | Batch then singletons | Full balanced bisection | List/filter/get | List/types/filter/get |
|---|---:|---:|---:|---:|---:|
| All initialized and declared | 8 | 1 | 1 | 2 | 3 |
| One undeclared, seven initialized | 8 | 9 | 7 | 2 | 3 |
| One declared static uninitialized, seven initialized | 8 | 9 | 7 | 2, but final value batch still fails | 3 |
| Every requested name undeclared | 8 | 9 | 15 | 1, no values dispatched | 1, no types/values dispatched |

Counts include successful/failed service requests, excluding common readiness/startup. Listing is bounded and recursive; it may be much larger in bytes than the requested name set. Bisection rows assume unrestricted per-key participation and therefore **are not admissible GLBE v2 schedules**. Counts do not equate a metadata request with a value request's latency. The listing/type branches preserve missing names and type evidence rather than supplying missing values.

**Decision:** reject recursive recovery as the selected new algorithm. Keep ordinary singleton recovery in the shared protocol. A future adaptive choice between direct batching and metadata screening would require actual predecision signals, native costs, and failure/race prevalence. It must beat fixed screening, fixed scalar recovery, and ordinary adaptive splitting under one newly frozen shared retry protocol. This mission supplies no such estimator and does not silently loosen v2 to rescue the proposal.

### Result of the loop

The surviving route is concrete integration, not another open-ended search: implement the ordinary helper specified next only if a later task authorizes implementation, test its unforced adoption and evidence preservation, and accept a systems result or stop. Do not infer a new policy from agreement between reviewers. The background primary-source adversary supplied additional paper overlap and challenged the recovery argument; local source and explicit counterexamples determine the conclusions.

## 4. Selected detailed specification: ordinary bounded reads

### 4.1 Exact interface and responsibility boundary

**Design, not existing exported functionality.** Register one ordinary JSON function:

```text
inspect_ros_reads(
    workflow: enum("node_parameters", "node_topic_subscribers"),
    namespace: string,
    parameter_names: array[string]
) -> EvidenceEnvelope
```

All three arguments are required; reject extra keys. `parameter_names` contains 1–32 unique exact names for `node_parameters` and must be empty for `node_topic_subscribers`. Accept `/` or a canonical absolute namespace without a trailing slash; scope by namespace segments, never substring. Limit each supplied string to 256 UTF-8 bytes as a support bound. The model must supply the namespace and exact parameter literals; no keyword mapping or semantic completion occurs in the host.

The description states: inspect all visible, addressable nodes observed in this namespace; either read the named configured parameters or preserve their published-topic-to-subscriber relations. Results are time-qualified observations, not an atomic graph or proof of message delivery. Hidden entities are outside this initial visibility policy and must be disclosed. Direct tools remain available for known identities, message contents, unsupported requests, and repair.

Required ordinary facades, shared by all strong arms:

| Facade | Exact conceptual input/output |
|---|---|
| `list_nodes(namespace)` | Typed `(node_name, node_namespace)` rows, duplicate multiplicity, interval/status. |
| `read_parameters(node, names)` | Literal ordered names; typed correlated values or explicit whole-batch validation failure. |
| `list_parameters(node)` / `read_parameter_types(node, names)` | Bounded full listing / aligned type observations. Shared native alternatives, not candidate privileges. |
| `published_topics(node)` | Topic/type tuples owned by that node, preserving the parent relation. |
| `subscriber_endpoints(topic)` | Endpoint owner, GID, type/hash and QoS records; no communication-success assertion. |
| `batch_reads(calls)` | Bounded array of explicit already-bound read calls, including grouped singleton repairs. No references, programs, arbitrary callable IDs, or binding expressions. |

`NodeId` means a validated public name/namespace pair, not an established process incarnation. Duplicate observed FQNs are ambiguous and block name-addressed reads for that group. Absence of an observed duplicate cannot establish globally unique identity. Topic identities are canonical absolute names. Parameter names have their own validation and are not topic names.

### 4.2 Contracts, state, and limits

Public contract declarations are hand-reviewed API integration facts: operation/version/effect, nominal input/output identity, decoder, ownership projection, multiplicity, temporal meaning, native request categories, and failure semantics. They contain no application node list, requested-answer map, expected value, task ID, or question text. There is no general path enumerator in the selected scope; two ordinary branches suffice.

Runtime state: immutable model authorization; contract versions; admitted root rows; per-root and per-relation outcome ledger; typed observations with intervals; request-global logical-read counters; pending work; and operation/time/output reservations. The host does not receive the evaluator's answer obligations.

Initial shared bounds reuse v2 where applicable: 128 raw root entries/8 KiB before root admission; 16 scoped roots; 16 entries per subsequent relation collection; 32 parameter literals; 128 returned parameter values; 64 attempted native operations per request; serial native dispatch; 3-second per-operation, 45-second helper and 180-second request deadlines; 8 model requests; 8 KiB per native payload; 24 KiB delivered envelope. These are proposed support limits, not measured optima. Nested fan-out must also fit the global caps. Reserve compact failure/pending accounting before dispatch; if an entire bounded relation cannot be represented, reject its expansion and record parent/limit metadata. Do not establish a usable child collection from a truncated prefix.

The selected helper has **zero automatic retries**, preserving v2. A malformed batch marks every included value key failed. The normal model may authorize direct singleton repair through `batch_reads` in one subsequent model request. At most one additional attempt is permitted per failed key `(parameter_value, node, exact_name)` across all wrappers. Every attempt counts; regrouping cannot reset counters. Successful observations remain in history; they are not silently reread during repair. Listing/types have distinct public operation keys but consume the same global native budget.

The same one-additional-attempt rule applies to every failed logical read, including graph/metadata repair: `(node_discovery, namespace, visibility_policy)`, `(published_topics, NodeId, visibility_policy)`, `(subscriber_endpoints, TopicId, visibility_policy)`, `(parameter_list, NodeId, exact_prefixes, depth)`, and `(parameter_type, NodeId, exact_name)`. The selected listing uses empty prefixes and recursive depth. A failed types batch debits every included type key, just as a failed values batch debits every value key. Keep contract versions fixed for the request. Reject an entire proposed batch if any included failed key has exhausted its allowance; the model may request a still-permitted subset. New helper invocations, reordered literals and wrappers share these counters. No successful prefix is automatically repeated after a child failure; any model-directed repeat is charged under the common budgets.

### 4.3 Procedural algorithm

```text
INSPECT(call, request_state):
    validate exact signature, namespace, literal names, and remaining resources
    root_receipt = observe node names/namespaces
    if transport/shape/pre-admission bound fails:
        return rejected receipt; authorize no root-derived reads
    scope rows; classify duplicate/invalid identities; admit bounded ledger
    if root count/accounting exceeds supported bounds:
        return explicit rejection, with no child dispatch

    for each uniquely addressable root in stable order:
        if global stop or resource reservation fails: retain pending; stop
        if workflow == node_parameters:
            receipt = one GetParameters(root, exact literal names)
            if response is aligned and typed:
                record every value or explicit NOT_SET outcome
            else:
                record whole-batch invalidity, all names unresolved
                update request-global failed-key counters
        else:
            receipt = published-topic relation for root
            validate full bounded relation, or record local failure
            for each admitted topic in stable order:
                retain root -> topic edge
                obtain subscriber endpoint observation, or attach a permitted
                    same-invocation observation with its original interval
                retain topic -> endpoint edges, empty sets, and failures
        preserve valid siblings after local failure

    return delivered evidence, failed/ambiguous/pending work, costs, intervals
    return control to ordinary model loop; never certify the user's intent
```

No branch decides whether a configured parameter answers a measured-state question. The model handles that semantic decision. Valid empty graph observations mean none observed at that time/scope. Transport failure is not an empty set. An empty value array for a nonempty request is invalid correlation, not evidence that all parameters are absent.

The envelope contains `version`, `authorization`, `scope`, `observations`, `relations`, `outcomes`, `coverage`, `execution_status`, `stop_reason`, `limitations`, and `cost`. Receipts include actual arguments, capability version, operation category, start/end times, transport and validation statuses, and delivered typed data. An observation table may avoid duplicate payloads, but every parent edge references its actual supporting observation. Ledger counts balance; no failed child disappears.

`complete` requires all admitted roots and required children to be valid, addressable, successful, and delivered, with no missing parameter values. `NOT_SET` is an explicit acquired status but not an acquired configured value; report the value-acquisition result as partial when values were requested. `partial` preserves unresolved outcomes; `rejected` means expansion was not admitted. These technical statuses never prove final-answer correctness.

Reuse is limited to identical reads within this one explicitly time-qualified inspection. It conveys the original observation interval. No cross-request cache, TTL freshness guarantee, or node-incarnation inference is added. A request demanding a new observation at each parent cannot reuse one; disclose unsupported atomicity. Give every strong control identical reuse rights.

### 4.4 Workflow A: unknown-set map with parameter outcomes

User: “For each node observed under `/demo` during this inspection, report its configured `use_sim_time`.”

**Hypothetical exact trace:**

1. Model request M1 chooses `inspect_ros_reads({"workflow":"node_parameters","namespace":"/demo","parameter_names":["use_sim_time"]})`.
2. Native G1 returns `[('a','/demo'), ('b','/demo')]`; typed admission creates `/demo/a`, `/demo/b`.
3. Native P1 gets `['use_sim_time']` from `/demo/a`: one Boolean `false`.
4. Native P2 gets the same literal name from `/demo/b`: one Boolean `true`.
5. Host delivers two source-qualified values, their intervals and the observed inventory, with `complete` relative to that observation.
6. M2 answers: `/demo/a: false; /demo/b: true`, qualified to the inspection. It makes no claim about clock behavior or global graph completeness.

Ideal count: two model requests, one graph observation, two parameter service requests; one outer helper call. For `N` addressable nodes, normal native work is `1 graph + N value RPCs`. The strong primitive path needs M1 discovery, M2 grouped reads, M3 answer, with identical native work. A fixed `node_parameters(namespace,names)` composite needs the same two model requests as the selected helper.

**Failure/partial example:** M1 instead requests `['use_sim_time','optional_mode']` on both nodes. For `/demo/a`, the installed strict undeclared-name behavior returns `[]`; `/demo/b` returns aligned values. The host retains b, marks both a slots unresolved, and does not zip or assert absence. M2 may issue a batch of two explicit singleton reads for a. If they return `[false]` and `[]`, only the first value is recovered; the second remains an invalid/unavailable singleton outcome. M3 must identify that missing value. Counts: one graph observation, two initial value requests, two recovery requests, three model requests. The same ordinary helper with the same protocol has exactly that trace. A timeout permits ordinary bounded repair but supplies no poison-name diagnosis.

### 4.5 Workflow B: fan-out with shared-topic convergence

User: “For each node observed under `/demo` during this inspection, list its published topics and the subscriber endpoint owners, GIDs and QoS observed on each topic.”

**Hypothetical exact trace:**

1. M1 chooses `inspect_ros_reads({"workflow":"node_topic_subscribers","namespace":"/demo","parameter_names":[]})`.
2. G1 inventories `/demo/a`, `/demo/b`.
3. G2, `published_topics(a)`, returns `/shared/x` of `std_msgs/msg/String` and `/demo/y` of that type.
4. G3, `published_topics(b)`, returns `/shared/x` of that type.
5. G4, `subscriber_endpoints('/shared/x')`, returns one subscription owned by `/outside/c`, GID `g1`, with reliable/volatile/keep-last-depth-10 QoS and the backend's remaining explicit QoS fields. `g1` is a schematic identifier, not a claimed ROS encoding.
6. G5, `subscriber_endpoints('/demo/y')`, returns a valid empty list.
7. Host preserves `a→x→g1`, `b→x→g1`, and `a→y→empty`. The single x observation is shared with its original interval; the out-of-namespace subscriber remains in the answer because the namespace scopes roots only.
8. M2 renders all three root-topic relations, the returned endpoint/QoS evidence, the empty observation, and temporal limits. It does not infer delivery or compatibility.

Native work is five graph observations, zero parameter RPCs; generally `1 + N + U` graph calls for N roots and U distinct admitted topics, before equally charged validation/recovery. A strong primitive schedule ideally uses four model requests: inventory, grouped by-node relations, grouped endpoint reads, answer. Either ordinary composite uses two. The path is a relation-preserving traversal with convergence, rather than workflow A's independent per-root values. This is useful structural diversity, not broad composition generalization.

If G3 raises `NodeNameNonExistentError`, preserve a's acquired relations and mark b's topic collection unresolved. Never report b as publishing nothing. If the topic collection exceeds a bound, report that parent's unresolved expansion; do not present a prefix as the full published set. These public methods and owner fields are verified in [installed graph APIs](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:1971), [endpoint APIs](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:2251), and [endpoint record](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/topic_endpoint_info.py:33).

## 5. Strong control challenge and exact remaining advantage

| Control | Capabilities/information it must receive | Expected discriminator |
|---|---|---|
| Activated ordinary primitives | Same typed public reads, batch helper, native dump/screening, output evidence, reuse, recovery, time/concurrency/native limits; corrected prompt. | Tests whether an outer composite avoids model boundaries in actual local-model behavior. |
| Compact parameterized ordinary helper | Same two workflows, descriptions, contracts, literals, and executor rights. This is the selected alternative itself. | There is no predicted policy advantage over it. A generated compiler must beat this to claim more than packaging. |
| Two straightforward same-path functions | `node_parameters(namespace,names)` and `node_topic_subscribers(namespace)` with identical receipt/guard semantics and normal JSON choice. | Tests enum-versus-name adoption and schema burden. Both match ideal native and model-request counts. |
| Best fixed development interface policy | Compact-only, both named wrappers, or at most one alias, selected before held-out use. Same schema budget where relevant. | Stronger than comparing a calibrated selector only with a weak arbitrary naming choice. |
| Ordinary parameter recovery alternatives | Scalar reads, batch then scalar repair, list/filter/get, list/types/filter/get, and bisection only under a separately shared expanded protocol. | Attributes any grouping benefit to native policy rather than tool generation. |

The exact surviving advantage is **integration efficiency relative to an activated primitive agent**, if adoption and net costs support it. There is no identified new execution decision versus the full-capability helper and no per-workflow advantage versus same-path composites. Public-contract reuse can reduce duplicated implementation effort across workflows; it does not automatically reduce native work or prove a portfolio advantage.

Do not artificially require the control's fixed function to ignore runtime arguments, branch conditions, or shared relations. Conversely, a control implementing precisely the proposed grouping policy is its replica; the fact that it can be written in Python is not a separate novelty rebuttal. The substantive failures here are existing equivalent policies, ungrounded deployment estimates, and protocol constraints.

Compile/setup cost is zero for a path compiler because none is selected. Adapter authoring, contract review, schemas, validation, observer startup, and registration still cost work and time. Report them. Schema tokens recur per rendered model request, including requests where the helper is unused. Result/status serialization and repair costs also count. No defensible payback horizon can be calculated before measuring net savings and stating a real workload mix.

## 6. ROSA integration, dependencies, and safety boundaries

Future integration would use `ROSA(tools=[...])` before normal agent construction. Three small responsibilities suffice: reviewed read contracts, typed ROS facades, and ordinary workflow wrappers/receipt assembly. A driver owns arm construction, copied prompts, global counters, traces and independent scoring. No LangGraph migration, model transport changes, dependency installation, generated Python, or ROSA core rewrite is indicated by source inspection.

Two narrow construction overrides are necessary in a research-only ROSA subclass. Override `_get_prompts` to construct a fresh `ChatPromptTemplate` from copied system messages, replacing the batching prohibition and retaining `chat_history`, `input`, and `agent_scratchpad` placeholders. The constructor's `prompts=` alone only appends robot guidance. Override `_get_tools` to filter the constructed registry's `get_tools()` list to an explicit allowlist of reviewed facade callables and safe direct reads before the agent binds it. Merely passing extra tools leaves legacy motion/write/generic-service/system tools available. The existing `blacklist` injection filters entity arguments and must not be mistaken for an execution-security allowlist. Both overrides are opt-in driver integration over the inspected extension methods, not modifications to pinned source. Apply identical restrictions to all strong arms.

Use a bounded framework-owned `rclpy` observer and only explicit graph/read service clients. Do not use `AsyncParameterClient.services_are_ready()` as a read-only authorization test: the [installed method](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/parameter_client.py:105) checks write services as well. Readiness applies to the particular authorized read client. Observer identity, graph settling and visibility rules are common, documented costs.

No arbitrary application service invocation, parameter write, motion, shell text, filesystem output path, or graph-controlled code import enters the helper. Legacy command wrappers cannot be used unchanged. If needed for direct metadata tools, use a shared reviewed argv grammar with `shell=False`, captured status/stderr, bounded payload and actual process timeout/reaping. The two selected workflows can use typed APIs throughout.

Cancellation stops new dispatch and marks pending work; a cancelled local future does not roll back a remote read. Late replies cannot become evidence after expiration. Resource cleanup and audit persistence remain host responsibilities. These API reads are logically read-only under reviewed contracts, not proof about every third-party server's implementation. A later native study would use disposable local applications only.

No semantic source substitution is allowed. A requested measured frame cannot be replaced with a configured parameter. A valid endpoint record does not certify a message path. Output text is untrusted data; it cannot alter authorization, add tools, or supply executable instructions.

## 7. Minimal realistic implementation and fair prospective test

Nothing in this section was executed or authorized for execution by this task. It specifies a bounded next decision, not another broad literature mission.

### 7.1 Implementation scope and development gate

Build only the two branches and common direct facades in section 4. Use meaningful fake-backend checks for malformed cardinality, root/relation overflow, ambiguous FQNs, namespace boundaries, failure isolation, exact retry caps, and cancellation. A deterministic schedule check compares compact and named helpers over identical observations; it establishes execution equivalence, not adoption.

Then, in a separately authorized disposable native setting, use six development prompts: two eligible per workflow, one known-target direct request, and one configured-versus-observed semantic trap. Keep selection unforced. Pin the available local model digest, tokenizer/template, provider/options and context; historical model names are not verified current endpoints. No paid inference or training is needed.

Require valid appropriate first calls on at least three of the four eligible requests for each composite representation; all feasible development requests must be fully supported after permitted repair; primitive grouping must actually activate; no unsafe dispatch is acceptable. Allow one preserved development-only interface correction, shared fairly where applicable. If activation still fails, stop with that adoption result. Do not replace it with forced-call scores.

### 7.2 Smallest decisive local-model study

Three arms are sufficient for the selected systems question:

- **P:** strong activated ordinary primitives.
- **G:** compact ordinary helper plus P.
- **F:** two ordinary named same-path functions plus P.

Freeze contracts, prompts, schema wording, backend, serial native cap, repair protocol, task wording, scorer and thresholds before held-out inference. Give every arm native dump and listing/type-screening alternatives, not only the treatment. Original-default ROSA is optional descriptive context; it is not the decisive control.

Use ten frozen held-out requests, two counterbalanced repeats, three arms: **60 prospective episodes**, maximum four-hour block and the section 4 request limits. Stop with attempted/incomplete/unstarted cells preserved if the block expires. Ten cases comprise four normal requests (two per workflow), one known-node direct read, one empty root namespace, one undeclared-parameter partial, one declared-uninitialized partial, one node disappearance after inventory, and one request requiring measured rather than configured state. Freeze exact fixtures and acceptable outcomes before model calls. Partial cases can earn honest-partial credit without counting as fully acquired feasible values.

Development and held-out use separately configured stock applications, for example demo nodes versus Turtlesim/Nav2 where their actual installed APIs permit the declared cases. Validate a fixture's feasibility before freezing; do not assume every standard node declares every parameter. A later test-only rclpy node with declared/uninitialized parameters is a labeled contract-stress fixture, not evidence of natural poison prevalence. Freeze any application substitution before held-out responses. Names, values and paraphrases are instance transfer; the two workflows do **not** establish held-out workflow-family transfer. No compiler/general portfolio claim is tested by these 60 episodes.

Record a matched transition on the relevant inventory event for the disappearance case. Independent observer brackets establish stable requested inventories/values; timestamped transitions govern dynamic scoring. Observer truth and manual answer obligations are evaluator inputs only. Missing brackets mean indeterminate coverage, not permission to regenerate truth afterward.

Measure all attempts first: supported/full completion, honest partials, wrong sources, unsupported extra claims, failed interface choices, schema repairs, actual model requests, rendered input/output/schema tokens, provider usage/cache data where available, native graph/list/type/value requests, failed/redundant work, startup, waiting, validation/serialization, preparation and end-to-end latency. Missing usage is unknown. Do not add nested timings twice. Preserve prompts, tool definitions and receipts durably outside `/tmp` for that future study.

Then compare efficiency on mutually fully supported matched task/repeat pairs, showing excluded pairs and reasons. Repeats do not create independent task families. A small study can falsify adoption/savings; it cannot prove population noninferiority or universal safety.

**Predeclared practical decision:** G is worth retaining as a systems integration only if it has no feasible supported-completion loss against P, no unsafe dispatch, complete unresolved-work accounting, and at least 10% lower summed tokens and end-to-end time on mutually supported normal pairs, with no extra normal-path native requests. Report actual saved model decisions rather than assuming them. Require at least six of eight normal task/repeat pairs to be mutually fully supported; otherwise call the efficiency comparison inconclusive. Stress/direct cases remain in all-attempt totals and can veto adoption for a correctness defect. These thresholds are project choices, not statistical guarantees.

If F ties G in correctness and is no more costly, choose the simpler representation by implementation and maintenance burden. If F is better, prefer F. A G/F tie is the expected attribution result. If neither improves on P after overhead, reject the integration-efficiency hypothesis. Do not start a new algorithm campaign automatically.

### 7.3 Small recovery discriminator, only if later justified

The decisive recovery objection is already static: bisection cannot satisfy the same independent-final-attempt property under v2's per-key cap. No model matrix is needed to establish that. A future ordinary recovery comparison can use deterministic explicit calls, outside the local-model adoption scores, on the four stable cases in section 3 and a race case. Compare scalar, batch/scalar, list/get, and list/types/get with identical bounded receipts. This checks source-derived behavior and practical cost, not a new algorithm.

To reopen adaptive grouping as research, first state a new **shared** protocol permitting deeper recovery; include bisection as an ordinary adaptive competitor; obtain a predecision signal beyond task IDs/hidden fixture knowledge; and freeze a selector and heterogeneous workload before testing. Reject the selector if fixed screening or simple scalar recovery matches its correctness/cost, if gains require a handpicked poison ratio, or if malformed batches are incorrectly treated as authoritative defect certificates. Until those inputs exist, the present decision is closed rather than deferred to another unrestricted audit.

## 8. Recommendation, uncertainties, and Indonesian summary

**Recommendation: reject the proposed new algorithm claims for this scope.** The strongest valid alternative is a small ordinary public-read integration and a bounded adoption/completeness study. Implement that only under a later implementation instruction and describe it as systems engineering. If the academic requirement strictly demands a new algorithm, this investigation does not meet it; do not relabel the helper, bisection, or interface naming to suggest otherwise.

This differs from simply endorsing GLBE or CCVT: it rejects a general compiler/menu optimizer; adds a concrete native metadata countercontrol; demonstrates the retry-cap conflict of recursive recovery; and leaves a complete ordinary-helper implementation and rejection route. It also narrows the residual interface hypothesis after new primary-paper overlap, rather than treating the earlier A/B recommendation as binding.

Outstanding factual uncertainties are local-model unforced adoption; actual native batch-failure frequency and race rates; useful schema-token and wall-time savings; representative task demand; and how many public workflows are worth supporting. Static source facts settle none of these. The proposed study tests instance/application transfer only. Claims about arbitrary ROS services, broad tool registries, new semantic source selection, or general algorithmic optimality remain unsupported.

**Ringkasan Indonesia:** Saya menguji tiga arah lewat source dan literatur: rangkaian tool otomatis, pemilihan nama fungsi, dan pemulihan parameter batch yang gagal. Belum ada dasar kuat untuk menyebut salah satunya algoritma baru yang layak dipromosikan. Helper biasa sudah bisa menyamai rangkaian tool; optimasi nama/schema punya penelitian yang dekat; pemecahan batch bisa menghabiskan jatah percobaan parameter yang sebenarnya valid. Alternatif sederhana adalah membaca tipe parameter dahulu, atau memperbaiki nilai satu per satu sesuai batas yang sama. Kalau proyek dilanjutkan, buat helper baca kecil dengan bukti lengkap lalu uji apakah model benar-benar memakainya dan apakah biaya total turun. Itu kontribusi integrasi sistem yang jujur, bukan bukti algoritma baru. Misi ini hanya menghasilkan laporan; tidak ada kode atau eksperimen yang dijalankan.

### Preservation record

Input archive SHA-256: `1981f5200e9e4ae9a808ac588679dfe20a9562523c096953eb3f449383a251a9`.

| Required input member | SHA-256 |
|---|---|
| `ROSA_RESEARCH_CONTEXT.md` | `2e45d916b40a7d3fab160a0c317949dde67518eeeed72aa54e6802ec2276a4f9` |
| `ROSA_Mission_A_Research_Report_2026-11-09.md` | `cedbd7f29a5a7a8e92b206442b5eb7449aed8c80f3b5ce0006fa28be4fbbce42` |
| `ROSA_Mission_B_Code_Grounded_Investigation_2026-11-09.md` | `007679606c1c92933b77105281fc4f19bc804715c3ba31f76688065df938df4a` |
| `ROSA_Algorithm_Specification_v2_2026-11-08.md` | `e312a953dccdac648a2a892e01a4cfee9f8e05555d52da28f2a66a4036838931` |
| `GLBE_Independent_Critical_Review_2026-11-08.md` | `d2d0862989520f034a074798024e0fea1e756a4d1c049cdfd664be245975c867` |

Selected exact source hashes: `src/rosa/rosa.py`: `21c35b1bdb14f6c8f6fd2f449943de7f1ba177fdce51ba0a6344b5ec9991e66b`; installed `rclpy/node.py`: `8b7fe0ea64e0de12cc1d5d01ebf56c202fa6e153251eb71dfff93e35eb5b3c80`; installed `rclpy/parameter_service.py`: `f7546866ac5e9443b5524f1ec0e63eeb8bdca1041e7392d2390d5f5b68396aaa`. Moving upstream Jazzy sources can differ in line numbers; local links identify the inspected implementation.

Only this requested Markdown report was created. Preservation was checked against an in-memory hash inventory of 45 pre-existing files under the workspace's source, tests, research, and root files. No original design report, source, dependency, historical result, Git history or setting was modified. Read-only shell work used file/archive inspection, hashes, package metadata, and Git identity/status; literature browsing and manual arithmetic supplied the research. No implementation, test suite, ROS process, model inference, benchmark, install, commit, push, or paid inference was performed.
