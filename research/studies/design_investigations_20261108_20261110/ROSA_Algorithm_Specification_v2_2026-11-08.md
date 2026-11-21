# ROSA Algorithm Specification v2 — Guarded Late-Bound Execution

**Date:** 2026-11-08  
**Status:** Implementation-ready research design; not implemented or experimentally validated by this review.  
**Presentation:** 2026-12-02  
**Method:** GLBE, a bounded model-authorized discovery/read executor. The name is not a novelty claim.  
**Review:** [Independent critical review](GLBE_Independent_Critical_Review_2026-11-08.md)  
**Preserved input:** [Exact v1 working copy](ROSA_Algorithm_Specification_v1_2026-11-08_working_copy.md)

## 1. Final decision and scope

Implement one opt-in executor that discovers an entity collection and performs an explicitly selected read over that observed collection without an intervening model call. Expose two small tools: one for nodes, one for topics. Reuse one inventory/map execution engine for their public read capabilities.

**Do not implement a DAG language, generated code, learned scheduler, provider predictor, workflow memory, semantic admission classifier, or cost-based stopping policy.** A fixed composite can implement the same successful path and obtain the same model-call reduction. It is a required control, not a deliberately weaker baseline.

The research question is whether this restricted interface provides useful, reliable end-to-end efficiency in ROSA after accounting for actual adoption, evidence completeness, recovery, and schema overhead. The work may support a bounded framework/methodology contribution. It does not currently support a claim of a new general optimization algorithm.

This document specifies future work. It does not authorize implementation or experiments. The present design task ends after the documents are delivered.

### Evidence labels

- **SOURCE:** Confirmed by inspected source; not a runtime measurement.
- **HISTORICAL:** Saved evidence with its original validity limits.
- **DESIGN:** A required choice for the proposed prototype or evaluation.
- **HYPOTHESIS:** A prospective outcome, including any performance claim.

All new tools, result contracts, numerical budgets, gates, and evaluation settings below are **DESIGN** unless explicitly labeled otherwise.

## 2. Research definition

### 2.1 Exact problem

Consider: “For every node under `/demo`, report its configured `use_sim_time`.” The namespace and parameter are supplied by the request; the node identities are not known until discovery.

A strong ordinary agent can discover once, request all independent parameter reads in one subsequent model decision, and then answer. GLBE lets the model authorize that whole bounded operation at the first decision. The framework supplies only the runtime identities; it does not decide what the user meant or which semantic source is appropriate.

This is a **late binding** problem: fill a previously authorized reader's entity argument from a validated discovery response. It is not task-to-endpoint inference.

### 2.2 Hypotheses and attribution

**H1 — integration efficiency:** On eligible unknown-set requests, GLBE reduces model calls, total tokens, and end-to-end latency versus strong ordinary ROSA without reducing supported completion or increasing equivalent native work.

**H2 — interface practicality:** A small shared-engine interface can preserve the correctness and adoption of straightforward family-specific composites, with limited additional overhead and no application-specific code.

H2 does not predict fewer model calls than a same-path composite. If C and D tie, that attributes the inference-boundary gain to ordinary composition. If the simple composites perform better, recommend them.

**No adaptive-policy hypothesis is included.** Correctness guards and deterministic best effort are ordinary execution policies shared with the simple control.

### 2.3 Parent mechanisms and contribution boundary

Operation planning separated from evidence collection is established in [ReWOO](https://arxiv.org/html/2305.18323v1); dependency execution and readiness in [LLMCompiler](https://arxiv.org/html/2312.04511v3); broader executable composition in [CodeAct](https://arxiv.org/html/2402.01030v4). Guarded optimization also overlaps [Agent JIT](https://arxiv.org/html/2605.21470v2) and [AgentPRO](https://arxiv.org/html/2611.00628v1).

The proposed increment is a constrained ROSA integration with an explicit public-contract boundary and a matched evaluation of adoption, coverage, and net cost. It is not new dependency theory, new batching, semantic verification, or a novel optimal policy. The review explains why AutoTool-style historical prediction and workflow induction are excluded.

### 2.4 Ideal successful-path accounting

| Approach | Ideal model calls for one unknown-set transaction | Native work |
|---|---:|---|
| Strong ordinary ROSA | 3: choose discovery; choose grouped reads; answer | One discovery plus the requested reads |
| Straightforward full composite | 2: choose composite; answer | Same |
| GLBE | 2: choose operation; answer | Same |

These are illustrative bounds under the specified interaction pattern, not guaranteed observations. Count actual requests, including malformed calls and recovery. Already-known entities should use direct ordinary tools and may need only two calls. Large fan-out does not imply proportionally more model calls saved.

**SOURCE:** Standard Jazzy `ros2 param dump` already lists parameter names and fetches values internally. Strong arms receive an equivalent bounded helper. Do not claim the parameter-name/value boundary is inherently an additional LLM decision. [Installed source](/opt/ros/jazzy/lib/python3.12/site-packages/ros2param/verb/dump.py:70).

## 3. Responsibility and knowledge boundaries

| Component | Owns | Must not do |
|---|---|---|
| User request | Requested observations and scope | Supply evaluator truth to the executor |
| Model | Select capability, namespace, parameter literals; handle semantic ambiguity; interpret evidence and answer | Delegate an unselected semantic decision to the binder |
| Framework | Validate schemas/contracts, discover, copy observed IDs into approved inputs, enforce budgets, execute, preserve receipts | Interpret question keywords into endpoints, rank semantic sources, invent missing values, certify intent |
| Tool adapter | Public API decoding, effect declaration, status, identifier validation, source/timing metadata | Encode application names, expected answers, question-to-field extraction rules |
| Evaluator | Independently check inventory, values, requested coverage, and full-answer support | Pass hidden fixture state or expected fields into model/tool inputs |

Permitted declarations include “this public node-list API returns `NodeId` values” and “this parameter reader accepts a `NodeId` and literal parameter names.” These are tool contracts, not user-question mappings.

Prohibited examples include “when the user asks for map frame, call this configured-parameter endpoint,” substituting a configured frame for an observed header, recognizing benchmark task IDs, or using a hidden list of application nodes to complete discovery.

Adapters may use the standard parameter API's documented node-relative service names. This is a ROS API rule, not a handwritten per-application endpoint table. Arbitrary application service calls remain excluded.

## 4. Model-facing interface

Use ordinary LangChain JSON function tools. No code, result-reference expressions, regular expressions, generated argument paths, or freely supplied tool names are accepted.

### 4.1 `inspect_discovered_nodes`

| Argument | Contract |
|---|---|
| `namespace` | Required absolute ROS namespace. `/` explicitly means all visible namespaces. |
| `read` | Required enum: `info`, `parameters`, or `all_parameters`. |
| `parameter_names` | Required string array. Nonempty only for `parameters`; empty for other variants. Maximum 32 unique literal names. |

Meanings:

- `info`: discover nodes, then obtain ordinary node metadata for each uniquely addressable observed node.
- `parameters`: discover nodes, then fetch exactly the model-specified parameter names for each node, using the shared per-node native batch API.
- `all_parameters`: discover nodes, then perform a bounded equivalent of the ordinary parameter dump for each node. All names means the names returned by that node's list response during this transaction.

Example tool arguments, not implementation code:

```json
{
  "namespace": "/demo",
  "read": "parameters",
  "parameter_names": ["use_sim_time"]
}
```

### 4.2 `inspect_discovered_topics`

| Argument | Contract |
|---|---|
| `namespace` | Required absolute ROS namespace, with the same scope rule. |

Discover topics and obtain ordinary verbose topic metadata for each observed topic. This is metadata introspection, not subscribing to messages or inferring what their values mean.

### 4.3 Shared interface rules

1. Selection is always **all observed entities in the stated scope**. There is no `unique`, first-match, importance ranking, or silent top-k mode in v2.
2. A namespace selects descendants: `/demo/a` is inside `/demo`; `/demo2/a` and a root-level entity named `/demo` are outside. `/` includes all absolute names permitted by the visibility policy. This is a segment rule, not substring matching. Accept `/` or a canonical namespace without a trailing slash; reject other forms rather than silently changing them.
3. Hidden graph entities are excluded in the first protocol. Requests explicitly requiring hidden entities use ordinary supported tools or receive an explicit limitation; they must not silently receive a visible-only answer.
4. No default namespace is inferred by the framework. The model must supply `/` or a specific namespace. Framework syntax checks do not prove this matches the request.
5. Parameters are exact API names, not fuzzy matches. Reject repeated literal names. Do not apply topic-name rules to parameter names; validate them using their own bounded API contract. V2 limits namespace, entity, and parameter-name strings to 256 UTF-8 bytes each as an explicit support/resource limit, not a claim that ROS rejects every longer name.
6. Reject extra fields, invalid enum combinations, non-string names, and invalid namespace syntax before discovery. Do not coerce malformed arguments into a guessed operation.
7. Direct tools remain available. Known identities, requests needing message contents, ambiguous semantics, and unsupported capabilities do not need this composite.

The tool descriptions must say that they return time-qualified observations and per-entity failures, not an atomic snapshot or a certified final answer.

## 5. Shared primitive contracts and backend

These are **proposed hardened facades**, not claims about current ROSA signatures. Expose the same primitives, output information, public descriptions, budgets, and ordinary grouping helper in strong arms B, C, and D.

| Primitive capability | Input | Output and execution contract |
|---|---|---|
| `list_nodes` | Explicit namespace and frozen visibility policy | One bounded graph observation; typed node name/namespace rows; duplicates retained; response status and interval |
| `read_node_info` | List of explicit `NodeId` values | Per-node terminal metadata receipts; one CLI attempt per node using argv, no shell |
| `read_parameters` | One `NodeId`, list of literal parameter names | One typed GetParameters request; checked name/value correlation and per-value status |
| `dump_parameters` | One `NodeId` | Typed ListParameters then GetParameters for exactly the returned names, both recorded; empty names require no value request |
| `list_topics` | Explicit namespace and visibility policy | Typed unique topic names, available graph type metadata, response status and interval |
| `read_topic_info` | List of explicit `TopicId` values | Per-topic terminal metadata receipts; one verbose CLI attempt per topic using argv |
| `batch_reads` | Explicit primitive calls with already-known arguments | Ordinary bounded grouping; no discovery binding, selection, hidden cache, or question interpretation |

The primitive names above are internal contract identifiers; their exposed LangChain names/descriptions must be frozen before evaluation. Use clear unique names rather than shadowing legacy tools with conflicting schemas. Related original read tools remain available under documented names where safe and needed for ineligible tasks.

### 5.1 Required contract metadata

Each capability declares a version, input schema, output schema, effect (`graph_read`, `parameter_read`, or terminal metadata read), nominal entity kind, underlying native operations, decoder, completeness meaning, error classes, and resource limits. The registry contains no question text, fixture IDs, expected values, or application-specific routes.

A nominal type means a declared identity category such as `NodeId` or `TopicId`, rather than merely a JSON string. V2 uses explicit approved discovery/reader pairs; it does not infer arbitrary links from matching field names or Python annotations. The same registry facts must be visible to all strong controls.

### 5.2 Backend choice

Use a request-scoped `rclpy` observer for graph collections and **read-only typed clients** for `ListParameters` and `GetParameters`. Use a small shared argv runner for `ros2 node info` and `ros2 topic info --verbose`, whose text is a terminal observation. Do not bind new entities by parsing their prose.

**SOURCE:** Graph methods return typed name/namespace or name/type collections. [Installed rclpy graph APIs](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py:2055). Parameter requests are already list-valued. [Installed parameter client](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/parameter_client.py:136), [GetParameters contract](/opt/ros/jazzy/share/rcl_interfaces/srv/GetParameters.srv:8).

Do not instantiate a broad write-capable API and call `wait_for_services` as the read authorization check. **SOURCE:** `AsyncParameterClient.services_are_ready()` checks write services too. Use only the particular read client's bounded readiness condition. [Installed readiness implementation](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/parameter_client.py:105).

The observer is a framework-owned hidden node under the frozen visibility policy; its identity must not leak into the reported application set. All strong arms use the same observer lifecycle and graph settling interval. Observer startup and spin time are charged equally.

### 5.3 Status and parameter validation

- Record transport status separately from domain payload. Never recursively treat a data key named `error` as framework failure.
- A received response is not automatically a complete valid result. Validate shape, bounds, identities, owner, requested names, and positional lengths.
- `GetParameters` response values correspond to requested names only if length and ordering satisfy the API contract. On mismatch, mark the whole affected request invalid; do not zip a short response into apparently successful partial values.
- `PARAMETER_NOT_SET` is a distinct outcome, not `false`, zero, or JSON null masquerading as a known value.
- **SOURCE:** The installed server can return an empty values array after an undeclared/uninitialized-parameter exception. Distinguish that response from a valid value for every requested name. [Installed parameter service](/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/parameter_service.py:80).
- Preserve exact parameter names and typed values, including arrays. A dump must not lose identity by flattening dotted names into a nested dictionary.
- A valid empty list response means that this API returned no names. It does not certify global absence or a semantic claim beyond that observation.

## 6. Result envelope and completion semantics

Every composite returns a JSON-serializable evidence envelope. Serialize it deterministically, with a frozen version. The framework generates statuses; the model does not fill them.

| Field | Required content |
|---|---|
| `schema_version`, `transaction_id` | Contract identity and request-local correlation |
| `authorization` | Exact model tool name and arguments; selected capability |
| `scope` | Namespace, visibility policy, observation interval, graph-relative limitation |
| `discovery` | Native receipt, validated observed entities when the response is admitted, duplicate/invalid records, decoding status; otherwise bounded overflow/failure metadata |
| `items` | One record per observed identity or explicit ambiguous group: inputs, native receipts, delivered result or error, timestamps |
| `coverage` | Counts and IDs for succeeded, failed, ambiguous, and pending items; parameter-level outcomes where relevant |
| `execution_status` | `complete`, `partial`, or `rejected` |
| `stop_reason` | `finished`, `empty_observation`, `invalid_arguments`, `discovery_failed`, `invalid_discovery`, `fanout_limit`, `deadline`, `operation_limit`, `output_limit`, `cancelled`, or `backend_failed` |
| `limitations` | Snapshot, freshness, scope, visibility, missing-result, and output limitations |
| `cost` | Attempted native operations by category, elapsed intervals, validation/serialization CPU time, consumed limits |

Each native receipt includes capability/version, actual arguments, source identity, start/end monotonic timestamps, transport outcome, response validation outcome, bounded delivered payload, and failure reason. CLI receipts also include exit code, timeout, stderr, and truncation flags. Trace persistence is an additional audit record; facts stored only in a trace are not facts delivered to the model. An identity table may store each ID once, with explicit references from receipts/items/coverage, to avoid repeating long names. Do not duplicate the entire discovery payload in several envelope fields.

**Pre-ledger discovery bound:** admit a discovery collection only if it contains at most 128 raw entries, its bounded serialized representation fits 8 KiB, and its validated identity/accounting representation can fit the envelope. On overflow, create no usable observed-set ledger and dispatch no children. Return available observed-count information, which limit failed, whether the count/payload is incomplete, and a failure receipt; do not promise every ID is visible. Counts are exact only if the complete typed response was available and counted. A partial prefix is diagnostic data, never an authorized collection. The 16-entity composite fan-out check is a separate later check on an admitted, scoped collection.

Use these meanings precisely:

- **Response decoded:** the received collection was processed without transport/shape/truncation error.
- **Observed-set coverage:** every identity in an admitted collection has an explicit succeeded, failed, ambiguous, or pending record; invalid identities are classified as failed. A pre-ledger overflow is rejected discovery, not a partially covered usable collection.
- **Execution complete:** every identity in the admitted scoped collection is uniquely valid and every required read/result is successful, validated, and fully delivered. There are zero failed, invalid, ambiguous, or pending identity/parameter outcomes. A valid empty observation can be complete with the stated absence limitation.
- **Execution partial:** discovery was usable, but some requested results failed, were unavailable, exceeded limits, or remain pending. Accounting for an error does not turn it into a known value.
- **Rejected:** no child read was admitted because arguments/discovery/whole-transaction constraints failed. Discovery may already have incurred cost.
- **Answer correct:** independently evaluated full requested coverage and source support. This is not an executor status.

No envelope field may claim “user request verified.” A perfectly completed composite can be the wrong operation for the request.

## 7. Algorithm and exact runtime decisions

### 7.1 Inputs and outputs

Inputs are the validated model operation and literals, immutable public capability contracts, fixed request/transaction budgets, and the shared backend. The engine receives no natural-language-to-answer map and no evaluator state.

Output is the evidence envelope. It never directly emits the final user answer and never silently repairs the model's semantic selection.

### 7.2 Execution sequence

1. **Admit.** Validate the argument schema and allowed capability pair. Check remaining request budgets. Reject invalid arguments before native work.
2. **Discover.** Execute the common root observation, recording its interval and authoritative status. Enforce the pre-ledger discovery bounds. A failed/oversized/malformed discovery authorizes no child reads and produces only a bounded failure receipt, not a usable collection.
3. **Scope and validate.** Apply the explicit namespace/visibility contract. Validate each identifier. Retain duplicate node identities as ambiguous; do not silently merge distinct nodes sharing a name. Sort addressable identities deterministically.
4. **Check fan-out.** If the admitted scoped observed set exceeds the composite fan-out cap, return its bounded identity/accounting representation with no child dispatch. Do not choose the first 16 and call them all. If even that representation cannot fit, classify it as rejected discovery before establishing the ledger.
5. **Bind.** For each admitted identity, copy its typed value into the entity input of the preselected reader. Copy the literal parameter names unchanged. No field extraction from descriptive CLI prose or semantic endpoint choice occurs.
6. **Read.** Dispatch in the frozen order under the global budgets. A local failure becomes an item failure; other valid identities continue. For `all_parameters`, the shared native dump helper owns its internal names/values contract and records both requests.
7. **Return.** Finalize all statuses and pending identities; include only delivered, validated evidence as success. Return to the normal agent loop for interpretation, repair, clarification, or answer synthesis.

### 7.3 Pseudocode — specification only

```text
GLBE(operation, contracts, request_budget):
    validate operation and its explicit discovery/reader pair
    if invalid or no remaining budget:
        return rejected envelope

    discovery_receipt := run the authorized shared discovery
    if transport, decoding, pre-ledger bounds, or discovery validation failed:
        return rejected envelope with discovery cost and failure

    observed := apply the declared namespace and visibility policy
    classify invalid IDs and ambiguous node identities
    establish stable order over uniquely addressable observed IDs
    if observed identity/accounting representation cannot fit the envelope:
        return rejected discovery receipt without a usable observed-set ledger
    if observed fan-out exceeds the transaction cap:
        return rejected envelope with admitted identities and fanout_limit

    ledger := every observed identity, initially pending or invalid/ambiguous
    for identity in stable order:
        if cancelled, globally unhealthy, or global budget exhausted:
            stop dispatch and retain remaining identities as pending
            break
        if identity is not uniquely valid:
            retain its explicit failure and continue
        inputs := identity plus exactly the authorized literal arguments
        reserve native and output resources before dispatch
        receipt := run the shared reader under the remaining deadline
        validate receipt and record its delivered results or local failure
        continue independent valid siblings after a local failure

    return envelope with ledger, limitations, costs, and precise stop reason
```

The internal dump helper is bounded `ListParameters → validate names → GetParameters → validate length/types`. It contains no model call, and is equally available as an ordinary primitive in B, C, and D.

### 7.4 Runtime decision rule

At each dispatch checkpoint, let `ready` mean an explicitly authorized, pending, uniquely valid identity with all literal arguments present. Continue exactly when `ready` is true, the backend is healthy, and operation/time/output reservations permit the read. Otherwise skip the local invalid identity or stop globally with the corresponding reason.

There is no utility score or learned estimator. Do not infer urgency, semantic importance, likelihood of repair, or physical state from these signals. Deterministic continuation and failure isolation are also required in control C.

### 7.5 Invariants

- Every dispatched child belongs to the validated observed set and the exact model-authorized scope.
- Every child uses the preselected read capability and unchanged literal parameters.
- After admission, no observed identity disappears from the accounting after a failure or limit. Rejected pre-ledger discovery carries no false all-ID-delivered claim.
- No invalid/short/oversized payload is labeled a complete success.
- A local failure cannot erase successful siblings.
- The sum of completed, failed, ambiguous, and pending identities equals the admitted observed identity accounting, including duplicate multiplicity where applicable and invalid IDs within failed outcomes.
- No new native request starts after cancellation, expiration, or exhausted request budget.
- Technical completion never establishes final semantic correctness.

## 8. Failure, recovery, freshness, and safety

| Event | Required action |
|---|---|
| Invalid schema, unsupported capability, invalid namespace | Reject before discovery; return a schema error for ordinary model repair |
| Discovery transport/shape/truncation failure | No child binding; preserve authoritative failure and return control |
| Duplicate node FQN | Mark that identity ambiguous, block its child reads, retain valid siblings |
| Empty observed set | No child reads; return complete empty observation with visibility/time limitation |
| Missing parameter, invalid cardinality, or disappeared node | Preserve explicit local failure; continue siblings; return partial |
| One dump exceeds per-node parameter count | Do not truncate or guess a subset; mark that node incomplete and continue permitted siblings |
| Scoped fan-out exceeds cap | Dispatch no children; return bounded discovery and limit reason for ordinary fallback |
| Deadline, cancellation, global output/operation cap, corrupted trusted backend state | Stop further dispatch; account for all pending items |
| Model selected a valid but semantically wrong family | Framework cannot certify or automatically fix it; independent evaluation records the error |

**Retries:** No automatic retry inside a composite in the first study. The model may use ordinary primitives to retry failed items, within the common request budget and at most one additional native attempt for the same failed logical read. All attempts count. Repeating already successful items is allowed only under the same general budget and is charged as redundant work. Do not expose a candidate-only resume cache or infer missing obligations from the question.

Maintain request-global failure counters in the shared backend, not inside individual composite invocations. Define logical keys as: `(node_info, NodeId)`, `(topic_info, TopicId)`, `(parameter_list, NodeId, exact_prefixes, depth)`, `(parameter_value, NodeId, exact_parameter_name)`, and `(discovery, entity_kind, namespace, visibility_policy)`. Freeze contract versions for the request. A parameter batch expands into one value key per requested name; a failed/malformed batch records failure for every requested slot. A dump uses the same parameter-list/value keys as direct primitives. Reordering names, splitting a batch, or switching wrappers cannot reset counters. Keep original argument order for response correlation. Before a repeat dispatch, reject an entire proposed batch if any included failed key has exhausted its one additional attempt; the model can instead request the still-permitted subset. This is accounting, not cached answer reuse. The same restrictions apply through the external guard in A where the legacy operation corresponds to these keys.

All strong arms retain successful evidence in the same agent history. The prompt asks the model to repair unresolved items directly rather than rerun an entire successful prefix. This is guidance, not a correctness guarantee or a hidden executor privilege.

**Freshness:** This is a sequence of observations. Return per-operation intervals and state that discovery plus reads is not atomic. A restarted node can reuse the same FQN; v2 does not establish incarnation identity. Do not claim the graph remained unchanged merely because no change was detected. No extra graph recheck is hidden in GLBE. Any future recheck must be charged and shared by controls.

**Safe execution:** No `shell=True`, arbitrary command text, file output path, write service, parameter setter, robot motion, or generic application service call enters the composite. The common argv runner captures status and bounded stdout/stderr, enforces a real timeout, and terminates/reaps its process group when required. Treat tool text as untrusted data; it cannot extend the capability allowlist.

Typed parameter reads are logically read-only under the reviewed ROS API contract; this does not prove arbitrary third-party server implementations have no side effects. Initial evaluation is confined to disposable local simulators/applications, with no physical robot or production system.

Cancelling a local ROS future does not cancel an already delivered remote request. Stop awaiting/binding expired results and record their disposition; never promise remote rollback. Process and client cleanup are framework duties. Do not rely on cancelling an asyncio task to terminate a blocking subprocess or worker thread.

## 9. Frozen prototype resource profile

These are conservative initial protocol values, not measured optimal settings. Any development adjustment is versioned before held-out execution and applied to all comparable controls.

| Resource | Value and meaning |
|---|---|
| Maximum scoped composite fan-out | 16 observed entities; over limit means no child dispatch |
| Pre-ledger discovery response | At most 128 raw entries and 8 KiB serialized representation; accounting must fit the envelope, otherwise no usable collection |
| Maximum parameter names per node/read | 32; exact names, no silent truncation |
| Maximum returned parameter values per transaction | 128; stop further work if this would be exceeded |
| Native attempts per whole request | 64; includes failed attempts, dump subrequests, recovery, and any extra discovery |
| Simultaneous native operations | 1 in the principal matrix, across all tools in a worker |
| Per-native operation deadline | 3 seconds, including that operation's readiness/wait interval |
| Per-composite deadline | 45 seconds, capped by remaining request time |
| Per-request worker deadline | 180 seconds, including model calls and cleanup |
| Maximum issued model requests | 8 per task; parsing/repair/provider retry requests count |
| Requested generated-token cap | 2,048 per model response, identical across arms |
| Model-request timeout | 90 seconds, additionally bounded by remaining worker time |
| Per-native delivered payload | 8 KiB; excess is an explicit output failure, never a complete result |
| Total composite envelope | 24 KiB, including status and IDs; enforce incrementally and reserve space for failure/pending accounting |
| Automatic composite retries | 0 |
| Additional model-directed attempts after a failed logical read | At most 1 per key, within the global caps |

Use monotonic time for deadlines. In-flight work must fit the remaining deadline and operation budget before dispatch. A dump reserves up to two native requests; no second request starts if the remaining budget is insufficient. Middleware-level allocation can occur before payload-size checks; these application bounds are not a proof of memory safety against malicious DDS traffic.

Keep bounded raw audit records in the study artifact directory. If the model-visible envelope cannot contain all results, mark it partial and identify omitted/pending work. Storage in an artifact never substitutes for delivery to the model. Trace collection, context serialization, and observer startup remain measured overhead.

## 10. Example executions

### 10.1 Successful named parameter read

The user asks for the configured clock parameter for every node under `/demo`. The model selects `inspect_discovered_nodes`, `read=parameters`, and `parameter_names=["use_sim_time"]`.

Discovery observes `/demo/a` and `/demo/b`. Both identities are valid and unique. The reader sends one GetParameters request per node. Both return one typed Boolean. The envelope contains both exact source identities, arguments, times, and values; status is complete relative to the observed set. The model reports both values and the observation scope. No intermediate model decision selected those identities.

### 10.2 Empty discovery

Discovery returns no visible topics under `/missing`. The engine sends no topic-info commands. It returns an empty observation, not a fabricated claim that no process anywhere could publish such a topic. Independent inventory checks determine whether the task-level absence claim is supported.

### 10.3 Disappearing child

Discovery returns nodes a, b, and c. Node b becomes unavailable before its parameter read. The engine retains a's valid result, records b's timeout, and reads c if budgets remain. It returns partial coverage and b as unresolved. The model may retry b once directly or explain the missing value. It must not say all three clock values were acquired.

### 10.4 Invalid discovery and misleading payload

A legacy-looking response contains `{"nodes":["command failed"]}` without authoritative success metadata. It is not a valid hardened discovery receipt and authorizes no child read. Conversely, a legitimate string parameter whose content includes the word `error` is still ordinary parameter data when transport and typed validation succeeded.

### 10.5 Wrong semantic source

The user requests a currently observed frame, but the model selects a configured parameter. The parameter read can execute perfectly. GLBE does not declare the answer correct; the independent scorer rejects source substitution. There is no handwritten frame-to-endpoint rule in the executor.

### 10.6 Native dump and its limit

For all parameters on each observed node, the shared helper lists names and fetches their values without another model call. A same-path fixed composite does exactly the same work. If one node lists 40 parameters, the helper reports the 32-name limit and does not fetch the first 32 as a supposedly complete dump.

## 11. Architecture grounded in the pinned stack

### 11.1 Source checkpoint

**SOURCE:** Primary checkout `/home/levinsonchen/project/rosa-research`, branch `research/clean-foundation-20261108`, commit `94af17866cb82f3ea3f09422ef5cbb99b14cc89c`. `src/rosa` matches `d9991aa` at review. Installed/locked versions inspected: LangChain 0.3.30, langchain-core 0.3.86, rosa-llm 0.1.0.

| Existing component | Reuse / implication |
|---|---|
| [ROSA constructor and extra tools](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:82) | Register optional LangChain tools through `tools=`. |
| [Agent and executor construction](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:256) | Keep the normal planning/tool/result loop and iteration limits. |
| [ROSATools registry](/home/levinsonchen/project/rosa-research/src/rosa/tools/__init__.py:122) | Tools need usable function implementations; do not assume a coroutine-only tool passes this registration path. |
| [Native node/topic list-argument tools](/home/levinsonchen/project/rosa-research/src/rosa/tools/ros2.py:174) | Preserve equivalent grouping in the strong control. |
| [Default sequential prompt](/home/levinsonchen/project/rosa-research/src/rosa/prompts.py:81) | Explicitly replace this instruction for B/C/D; do not just append a contradiction. |
| [Prompt list mutation](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:293) | Isolate experimental prompt construction and copy the global list. |
| [LangChain tool agent](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/tool_calling_agent/base.py:97) | Uses `bind_tools`; output parsing and intermediate tool messages already exist. |
| [Sync dispatch](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/agent.py:1401), [async dispatch](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/agent.py:1538) | Sync is sequential across emitted actions; async already gathers them. No new concurrency claim. |
| [Tool message serialization](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/langchain/agents/format_scratchpad/tools.py:18) | Return a JSON-compatible envelope; retain original action/result correlation. Do not assume arbitrary artifact objects are transparently model-visible. |
| [ChatRosaLLM](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/rosa_llm/langchain.py:53) | Supplies model/message/tool transport, not orchestration or ROS execution. |

### 11.2 Small implementation boundary

Future prototype responsibilities should fit in three small modules under a new opt-in research directory:

1. `contracts`: argument/result definitions, approved capability pairs, budgets, and status vocabulary.
2. `ros_reads`: shared graph/parameter/argv backends, common primitive tools, and the two GLBE tool adapters.
3. `executor`: one explicit bounded inventory/map loop and receipt assembly.

The experiment driver owns arm construction, isolated prompts, global request limits, traces, and evaluation orchestration. The fixed-control wrappers are small direct functions over the same primitives; they do not need a second architecture. Reuse the repository's evaluation infrastructure where it remains compatible; do not import historical semantic task adapters or scorers as execution logic.

These are proposed responsibilities, not files created by this design task. No ROSA core, dependency, provider, or historical source changes are necessary. If a later implementation discovers a required core change, document that need separately before altering the pinned baseline.

### 11.3 Model transport and instrumentation

Use `ChatRosaLLM` with `rosa-llm[langchain]==0.1.0` as a supplied BaseChatModel. Keep provider history and tool-call IDs intact. Do not modify rosa-llm, silently switch providers, or use model-specific forced tool selection to manufacture adoption.

**SOURCE:** Its Ollama binding rejects strict function-schema and forced/parallel-tool-choice options. Async uses worker-thread fallback. [Adapter behavior](/home/levinsonchen/project/rosa-research/.venv/lib/python3.12/site-packages/rosa_llm/langchain.py:141). Record raw provider token metadata through callbacks/traces; ROSA's built-in printed token tracker is restricted to OpenAI/Azure classes and does not establish ChatRosaLLM accounting. [ROSA token tracking](/home/levinsonchen/project/rosa-research/src/rosa/rosa.py:114).

The principal matrix uses synchronous invocation and a common serial native budget to isolate inference-boundary effects. An async comparison is optional only after the principal study, under a separately frozen matched cap; it is not required for H1 and is not a v2 contribution.

## 12. Comparison arms

| Arm | Definition | Interpretation |
|---|---|---|
| A — bounded original ROSA | Pinned source, default prompt and original tool interfaces, same model and fresh history; external observation-only guard, time/output/native limits, and tracing | Descriptive baseline for original behavior under declared safety bounds; not unrestricted deployment defaults |
| B — strong ordinary ROSA | Same agent loop, corrected batching prompt, hardened common primitives, actual list/multi-call grouping, native parameter dump helper, ordinary reuse and failure recovery | Main comparator for H1 |
| C — straightforward fixed composites | B plus four explicit wrappers: list/read node info, list/read named parameters, list/dump parameters, list/read topic info | Same successful execution path and guards as D; explains the benefit of ordinary composition |
| D — GLBE | B plus the two schemas in section 4, using the shared inventory/map engine | Candidate integration/interface |

C exposes the same four capabilities as D's enum variants and topic operation. It receives the same status envelope, fan-out caps, per-child failure isolation, ordering, deadlines, shared backend, and retry rights. Do not make it fail-fast, omit a dump helper, or artificially limit it to one application. Its composite wrappers contain public API composition only, not task-to-answer maps.

C and D intentionally have **no different continuation policy**. Their contrast concerns interface organization and reusable implementation. Do not report D beating B as an adaptive-policy gain. If C matches D, say so plainly.

A cannot simultaneously preserve legacy outputs and use all new typed facades. Keep its source unchanged, document the external guard and any intercepted unsafe attempts, and exclude A-to-D differences from backend-mechanism attribution. In its disposable worker, intercept legacy command execution before the original shell runner: parse only the reviewed read-command grammar into argv, reject unsupported tokens/verbs, use the bounded safe runner, and retain the legacy `(success, output)` boundary and outer wrapper shapes. This is an explicit runtime guard, not an untouched native-backend claim. Never execute the original `shell=True` branch. The decisive controlled contrasts are among B/C/D.

All strong arms receive the same information-bearing primitive contracts, already-paid graph metadata, legitimate read capabilities, and evidence retention. Tool descriptions may differ where interfaces necessarily differ; their tokens count. Do not hide the new schema cost or artificially pad B to erase it.

## 13. Development checks inside the implementation mission

Do these checks while building the one prototype, before opening held-out results. They are not a new sequence of independent feasibility studies.

1. **Contract and safety checks:** fake-backend cases for malformed discovery, status/payload separation, duplicate identities, namespace boundaries, parameter cardinality, exact budget edges, local failure isolation, oversized outputs, and cancellation/cleanup. These verify meaningful boundaries rather than merely mirroring the loop.
2. **Deterministic native checks:** in disposable stock applications, compare B's explicit grouped schedule, C, and D using the same runtime identities. Establish that their intended receipts/native work agree. Hand-authored invocations establish backend behavior only.
3. **Unforced model adoption:** eight development requests across Turtlesim and `demo_nodes_cpp`: six eligible multi-entity requests and two known-identity/ineligible cases. Do not inject expected tool arguments or force the chosen tool. Include named parameters, node metadata, native dump, and topic metadata.
4. **Activation gate:** in B, demonstrate real grouping on at least two multi-item tasks; in C and D, select an appropriate composite with valid first-call arguments on at least five of six eligible requests. All six eligible answers must be fully supported after permitted recovery. No unsafe native dispatch may occur. Report first-attempt and post-recovery outcomes separately.
5. **One bounded revision:** allow at most one development-only interface/prompt correction per affected arm; preserve both versions/attempts and keep B's reasonable guidance equally maintained. Repeat the complete development set under the new version. No held-out tuning.

If the gate remains unsatisfied, preserve the failed activation result and stop before the held-out matrix. Do not replace it with forced invocation scores or quietly start another algorithm. A functioning C with failed D adoption supports the simpler composite, not the shared-engine interface claim.

The held-out scorer, exact task text, fixture recipes, registry, schemas, model configuration, budgets, and randomization must be versioned and frozen before held-out model calls.

## 14. Practical held-out protocol

### 14.1 Environment and split

Development uses disposable stock Turtlesim and ROS demo nodes. The planned held-out application is a separate Nav2 MapServer/lifecycle-manager launch using standard graph/parameter APIs. This is a **planned** environment, not a claim that its runtime was checked here. Fix its exact packages, launch recipe, small map fixture, namespace, readiness procedure, and allowed processes during development without looking at held-out model outputs.

If that application cannot be prepared within the implementation window, freeze a documented replacement before any held-out calls and label the change; do not select a replacement after observing candidate outcomes. No hidden application-specific parsing or selection code may be added to make it work.

Use different namespaces, entity counts, parameter values, and wording from development. The scorer may know launch manifests and fixture truth, but those records are isolated from the executor. Values in task text are legitimate user literals; expected answers are not model inputs.

### 14.2 Twelve task templates

Freeze exact wording and expected obligations when constructing the fixture. This table fixes the task categories and semantic boundaries, not answer mappings inside the method.

| ID | Request category | Principal check |
|---|---|---|
| h01 | Published-topic names/types for every node under the user-stated namespace | Eligible node-info coverage |
| h02 | One explicitly named configured parameter for every scoped node | Eligible exact source and parameter coverage |
| h03 | Two explicitly named configured parameters for every scoped node | Native per-node batching; no extra model call per parameter |
| h04 | All currently declared parameter names and values for every scoped node | Ordinary dump available to B; no invented inner-boundary advantage |
| h05 | Type and publisher/subscriber metadata for all topics in a stated topic namespace | Same engine with TopicId; no inference that node namespace equals topic ownership |
| h06 | Subscribed-topic names/types for every scoped node, with changed wording/cardinality | Same node-info API; answer coverage and limited robustness transfer |
| h07 | Named parameter for an explicit known node | Ordinary direct path; composite not needed |
| h08 | Metadata for explicit known topic names | Ordinary list-argument grouping; no rediscovery advantage |
| h09 | All observations in an independently empty namespace | Qualified empty observation and no fabricated absence |
| h10 | Unknown-set read with one fixture node removed after discovery | Honest partial, preserved siblings, bounded recovery |
| h11 | Scoped set of 17 entities, exceeding composite fan-out | Explicit limit, no silent truncation, ordinary fallback permitted |
| h12 | Ambiguous or unsupported inference from configuration to measured state | Clarification/limitation or separately supported sources; no configured-to-observed substitution |

h01–h06 have valid requested values within the normal resource profile. Repeated templates or two node-info projections are not independent algorithm families. h10 and h12 require robustness/semantic scoring distinct from fully acquired values. h11 remains a real request: if ordinary fallback can complete it within the global budget, that completion receives full credit.

For h10, key the fixture transition to the same relevant discovery event and target identity in each arm, not to a global tool-call index. Record the transition independently. A change schedule is evaluator infrastructure, not a rule accessible to the executor.

Malformed responses and adversarial payloads belong in labeled fake-backend contract tests. Do not report synthetic decoder faults as native ROS benchmark events.

### 14.3 Size and execution order

Run **12 templates × 4 arms × 2 repeats = 96 primary episodes** on the same frozen model/configuration. Keep matched task/repeat identities. Use fresh agent history and clean fixture reset for each episode. Randomize and counterbalance arm order within task/repeat blocks using recorded seed `20261108`.

Proposed primary model is the same local `qwen3.5:9b` family used historically, accessed through ChatRosaLLM. Pin its actual digest and available provider version during preparation. Request temperature 0, seed 42, reasoning disabled, and the 2,048-token response cap where supported; archive exact supported/effective options and context size. A required option that is unavailable must be resolved and versioned during development, not silently ignored in the held-out run. Do not assume a provider supports settings merely because another adapter does. No paid API is required or authorized.

Use a six-hour matrix wall limit in addition to episode limits. If interrupted, retain attempted, incomplete, and never-started cells distinctly. A continuation gets a separate identity and fresh independent brackets; never regenerate a missing closing observation or pool unbalanced blocks as a complete matched study.

## 15. Correctness, evidence, and independent ground truth

Freeze the scorer before held-out model responses. It must not read candidate internal success flags as truth.

For stable tasks, independently bracket each episode with native inventory and direct field observations, after readiness and before teardown/reset. Compare discovered inventory and values at both boundaries using frozen discrepancy rules, then retain matched task/repeat blocks for analysis. Save original failures. Missing or inconsistent independent inventory makes an all-entities coverage claim indeterminate, even if individual values are supported. Evaluation-only fixture/oracle work is timed and reported separately from agent worker cost; framework observer startup and agent tool work remain inside worker cost.

For dynamic h10, use independently timestamped fixture transitions and time-qualified direct observations. Do not pretend its before/after states are equal. Score requested values that could be obtained, correct identification of missing items, preserved unaffected siblings, and unsupported claims separately.

Report these dimensions separately for every attempt:

1. Appropriate unforced operation choice, including appropriate nonuse on ineligible requests.
2. First-call schema validity and subsequent repair attempts.
3. Actual result-dependent binding: child arguments came from returned observations.
4. Acquired and delivered native evidence, with exact observed-set accounting.
5. Requested-field coverage in the final answer.
6. Support for every positive claim in the entire answer, including extra prose.
7. Honest partial/ambiguity handling and correct source attribution.
8. Strict output framing, only if a frozen task explicitly requires it.
9. Unsafe or out-of-scope attempts and actual dispatches.

A factual answer in prose receives the same factual credit as equivalent JSON. JSON syntax is not semantic correctness. A true statement stored only in the trace but omitted from the final requested answer does not satisfy answer coverage. Do not invent a user-question-to-field parser for the executor; manual or independently defined evaluation is a separate responsibility.

The small study cannot establish population-level noninferiority or universal safety. Report counts and task-level differences; keep any intervals clustered by task template and label their limited power. Two repeats are not two new task families.

## 16. Cost and overhead measurement

Record every attempted model request, response/error, input/output tokens, provider metadata, native dispatch, receipt, timeout, retry, and worker termination. Preserve exact prompts/tool schemas, source hashes, package versions, fixture state, and timing clocks.

Required cost dimensions:

- Model requests, including failed generation and parsing/repair requests.
- Input/output/total tokens; separately cached/reasoning tokens if reported. Missing usage is unknown, not zero.
- Outer LangChain tool calls and inner primitive/native operations separately.
- Native cost vector: graph API observations, parameter RPCs, CLI subprocess attempts, and explicit waits. A parameter dump is not one native RPC merely because it is one helper call.
- End-to-end worker time, model elapsed time, observer startup/spin, native work, validation CPU, envelope serialization, trace writing, and recovery.
- Completed, failed, skipped, expired, and pending work.

Do not equate legacy CLI attempts in A with typed parameter RPCs in B/D as a single physical unit. B/C/D share the backend and therefore admit clean per-category native comparisons. A remains useful for behavior/call/token comparison with its backend difference disclosed.

Use nonoverlapping timing categories or label nested intervals. Executor CPU measured inside total tool time must not be added to total wall time again. The serial principal profile simplifies attribution but does not imply ROSA lacks asynchronous concurrency.

Conceptually, net latency improvement equals model time avoided plus any native critical-path difference, minus additional validation, schema/serialization, and recovery costs. Compute it from recorded complete episodes; do not substitute historical average LLM latency into a claimed measured result.

Report **all-attempt completion and costs first**, then efficiency on mutually fully supported same-task/repeat pairs. Preserve how many pairs are excluded and why. Do not turn incomplete, truncated, unsafe, or unsupported answers into apparent savings.

## 17. Minimum evidence and decisions

These are practical promotion criteria for a small project, not statistical proof.

### 17.1 H1: useful integration improvement over B

Require all of the following:

1. The development activation gate passed without held-out tuning.
2. No unsafe native dispatch or unsupported global-completion claim by D.
3. D has no loss of supported completion versus B on feasible requests; honest partial and ambiguity outcomes are also reported without regression hidden by aggregation.
4. At least 10 of the 12 eligible task/repeat pairs are mutually fully supported, covering named parameters, dump, node metadata, and topic metadata.
5. D saves at least one actual model request on at least eight eligible matched pairs; matched total tokens and end-to-end time are each at least 10% lower than B.
6. Equivalent native work does not increase on those normal successful pairs; stress/fallback attempts remain in the all-attempt report.

If the sample is incomplete or usage/ground truth is insufficient, label H1 inconclusive rather than silently relaxing the gate. Report absolute differences alongside percentages. These thresholds are design targets, not expected measured results.

### 17.2 H2 and the simple-composite ceiling

Compare D and C on their own mutually supported cohort, not automatically the B/D subset. Require no supported-completion loss and report total token/time overhead. An overhead above 5% on the same successful paths is a reason to prefer the simpler interface unless a separately measured adoption/coverage benefit explains it.

- If C and D both beat B and match one another, attribute the gain to ordinary discovery/read composition. The shared engine is an implementation/methodology result.
- If C beats D, recommend C; do not create a new policy to rescue D.
- If neither beats B after overhead/recovery, reject the integration-efficiency hypothesis on this scope.
- If D alone appears better, inspect adoption, schema length, prompt differences, and actual native schedules before making a causal claim. There is no different scheduler to credit.

Portability requires the same engine and reviewed public adapters on held-out application instances, without task-specific branches or semantic extraction rules. Node and topic cases support bounded API portability, not arbitrary tools or broad robotics generality.

## 18. Delivery schedule and implementation checklist

The schedule assumes a separate instruction to start implementation after this design review.

| Dates, 2026 | Work product |
|---|---|
| November 8 | Review and standalone v2 finalized; no implementation |
| November 9–14 | One coherent prototype, shared hardened primitives, fixed composites, meaningful contract checks |
| November 15–17 | Development adoption/validation gate; at most one revision; freeze exact held-out protocol/scorer |
| November 18–22 | One matched primary matrix, with the declared time cap and preserved failures |
| November 23–26 | Independent correctness review, matched analysis, limitations, reproduction package |
| November 27–30 | Presentation and demonstration preparation |
| December 1 | Buffer and rehearsal |
| December 2 | Presentation |

Before held-out execution, an implementer must have: unique tool schemas; public contract versions; a shared read-only backend; authoritative receipts; global budget enforcement; equivalent C/D guards and failure handling; activated B batching; unforced C/D adoption; frozen tasks/scorer; independent ground truth; raw traces; and an interruption rule.

These are completion criteria inside the implementation mission, not permission to begin it now. No separate learned-policy study, large model sweep, general compiler, or application-specific semantic layer belongs in this scope.

## 19. Final implementation boundary

**Build:** two small GLBE tools; one bounded discovery/map executor; shared safe graph/parameter/metadata primitives; standard dump capability for all strong controls; four simple composites; request accounting; essential validation/adoption checks; one matched evaluation.

**Do not build:** a general plan language, adaptive cost optimizer, endpoint predictor, task mapping, source-equivalence rules, arbitrary code/service runner, cross-task memory, candidate-only cache/concurrency advantage, or automatic semantic correctness gate.

The specification is ready for implementation as a narrowly scoped research candidate. Its empirical value and model adoption remain hypotheses. Its successful-path execution mechanism can be matched by an ordinary composite, so novel algorithmic superiority remains outside the supported claim.
