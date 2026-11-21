# ROSA Algorithm Specification v1 — Guarded, Late-Bound Tool Execution

**Status:** Research design candidate, not an implemented or demonstrated improvement  
**Date:** 2026-11-08  
**Target:** Undergraduate Special Project, presentation 2026-12-02  
**Working title:** Guarded Late-Bound Execution (GLBE). The name is provisional and is not a novelty claim.

## 0. Executive decision

We will study whether a **minimal model-facing operation** and a **framework-side, contract-checked executor** can carry out a bounded set of dependent read operations without an intermediate LLM decision, while preserving complete, auditable results. The **main test is against a strong native-batching control**, not merely the default ROSA prompt. No cost-based adaptive stopping is assumed useful yet. It becomes a second research mechanism only if measured traces reveal recurrent, *valid* choices between continuing and handing control back.

This retains the useful dependency-resolution concepts of LLMCompiler, ReWOO, and CodeAct without making the model emit a DAG, Python, or `$ref` syntax. Agent JIT provides cost-accounting and validation inspiration, not a borrowed complex program optimizer. The primary technical change is the **contract and binding execution**, not autonomous semantic tool selection.

## 1. Research problem and hypothesis

### Problem

In a common ROSA pattern, the user asks for observations about all members of an unknown set. ROSA must first discover the set, return it to the model, and then use the model to select a read using the newly available names. Normal batching can group read requests **once the names are known**, but it cannot bind names that do not yet exist at the model's current decision point. ROSA's default prompt also discourages batch/parallel calls, so the correct strong comparison must remove that avoidable restriction.

### Primary hypothesis (H1)

For requests with a clearly model-authorized, structurally defined discovery-to-read dependency, a bounded executor with validated late binding can reduce LLM decisions and latency relative to strong model-led batching **without degrading requested-field coverage, factual support, or safety**.

### Secondary hypothesis (H2, conditional)

If there are recurrent runtime states where a **different continuation-versus-handoff decision** can preserve task correctness and reduce expected end-to-end cost beyond the fixed executor, a measurable adaptive policy may improve performance. **Do not implement or claim H2 simply because a cost equation can be written.**

### Deliberately excluded

No task-to-endpoint/answer maps; no inference of which robot service is the semantic source; no arbitrary code execution; no side-effectful services; no training or historical trace requirement; no claim that a ROS graph alone explains the meaning of an observation.

## 2. Conceptual model and example

**User:** “For all nodes under `/demo`, report their configured `use_sim_time` parameter.”

- **Model:** decides the target namespace, the selection `all`, the requested parameter, and that this specific read family matches the request.
- **Framework:** performs actual node discovery, accepts only successful and complete discovery results, validates node identities, and binds discovered names into an authorized read operation for each node (or a semantically equivalent native batch).
- **Framework:** records per-node value/error, source, arguments, timestamps, pending work, and any stop reason.
- **Model:** interprets the evidence and produces the answer; if the question was semantically ambiguous, it must clarify or choose ordinary tools rather than delegate a guessed binding.

**Strong batching control:** model decides `list nodes` → sees names → model decides one batch of reads → model synthesizes. **Proposed operation:** model chooses a bounded composite → composite discovers and binds reads → model synthesizes. In the ideal case both perform the same ROS reads; the opportunity is an *intermediate LLM decision*, not `n` model calls saved for `n` nodes.

## 3. Two layers: reusable engine and ROS interface adapters

### Layer A: model-visible operation

Use **simple, flat tool schemas** instead of a full plan language. The first advertised operations can be specialized by **public ROS tool capabilities**:

- `inspect_discovered_nodes(namespace, selection="all")`: discover nodes and call existing node-info reads over the observed set.
- `read_parameter_for_discovered_nodes(namespace, parameter_name, selection="all")`: discover nodes and fetch one explicitly named parameter from each observed node.

These are **examples, pending exact signature verification**. `selection="unique"` is allowed only when a unique entity is actually observed; it is not a heuristic for picking the first item. The runtime, not the model, owns maximum fan-out, total native operations, deadlines, and output sizes. The model must not choose arbitrary target tools through unrestricted strings.

A later operation family is useful only if it uses the **same engine without writing new task-answer semantics**. Fixed adapter declarations may document genuine API contracts such as `list of node IDs` → `node_name argument`; they must not specify “if user asks X, the correct service is Y.”

### Layer B: contract-checked execution engine

Generic phases:

1. **Admit:** verify that operation and literal arguments are in a read-only allowlist, request scope is explicit, and all fixed budgets are satisfied.
2. **Discover:** run the selected discovery through a hardened adapter with authoritative exit/status capture (not just a legacy dictionary).
3. **Validate:** require successful and complete discovery; check typed collection, canonical IDs, exact namespace-segment matching, deduplication where identity is well-defined, and resource limits. On unknown/error/oversized discovery, hand back the evidence; do not silently truncate or substitute data.
4. **Bind:** copy validated observed IDs into a declared argument position in a preapproved reader contract. No ad hoc parsing of descriptive CLI prose and no model- or application-specific field extraction.
5. **Execute:** run bounded independent reads, respecting the same concurrency limits as controls; preserve successful siblings when a child read fails, while stopping on common failure, deadline, unsafe values, or invalidated scope.
6. **Hand back:** return one evidence envelope containing original discovery, per-child inputs/outputs/status/time, unresolved IDs, completeness/freshness limitations, and explicit stop reason.

The first implementation policy is **fixed guarded continuation**: continue all authorized, feasible reads; stop at genuine contract/resource violations. Do not use an unsupported score to decide which requested results are “important.” A later adaptive scheduler would be separately plugged into the same executor and tested against its fixed policy.

### Safety/validity contract

- Selected subprocess invocations must use safe argument vectors or a reviewed ROS client; legacy `shell=True` command construction is not a trustworthy boundary for derived names.
- Return command status separately from output. A string appearing in the `nodes` list is not sufficient proof of discovery success; a nested `error` key in arbitrary payload is not always a framework error.
- Capture subprocess timeout and cancellation/reaping, output limits, and per-child status.
- Model instruction alone is not safety authorization. Services with side effects are excluded; a generic service-call wrapper cannot be assumed read-only.
- A discovery+read sequence is **not an atomic snapshot**. Report when each observation was made and what was not verified after graph changes.
- Separate **technical execution success** from **semantic correctness of the final answer**. The engine does not determine the intended source when the request is ambiguous.

## 4. Why this is research, and what remains unproven

**Established prior art:** dependency resolution, program-based tool composition, execution guards, batching, and LLM handoff are known concepts (LLMCompiler, ReWOO, CodeAct, Agent JIT, AutoTool, etc.). Merely coding a composite tool is not by itself a novel algorithm.

**Testable incremental methodological question:** Does replacing fragile general plans/code with **one model-authorized, public, typed late-binding operation** meaningfully increase *actual adoption*, completed dependent execution, and end-to-end efficiency on ROSA and a held-out ROS application, compared with both native batching and richer plan interfaces? Does the interface preserve evidence completeness when discovery and reads partially fail?

**Main risks:** (a) the model fails to select even a simple tool correctly; (b) a strong batch control already avoids most relevant decisions; (c) only a small slice of ROSA requests fits the contract; (d) validating/parsing safe outputs costs more than saved inference; (e) the approach succeeds on node-info but not other types and is not broadly transferable; (f) claims of adaptive optimization are unsupported.

**Possible extension worth considering after direct evidence:** evaluate selective checkpointing when some valid authorized work remains but a model decision could materially revise it. This requires witnessed policy disagreements and measurable costs/recovery outcomes. It is not necessary for H1 and should not be dressed up as an already justified contribution.

## 5. Comparative evaluation (freeze before experimental coding)

### Arms

A. **Original ROSA**: pinned clean source, normal tool menu and prompt, same model/configuration.  
B. **Strong ordinary ROSA**: same model and information, with explicit permission/guidance for existing native batching and multiple calls, same safe read backend and evidence contracts; no composite.  
C. **Proposed fixed executor**: identical safe backend and tool/result information, plus the optional typed late-binding operation.  
D. **Adaptive policy, only if justified**: same composite mechanism and model contract as C, replacing only its continuation decision rule.

Do not equate C vs A with proof of an algorithmic advantage if B can already achieve the same savings. Preserve original ROSA separately from shared-backend hardened controls and document that distinction.

### Workload

Use at least two compatible **read families** if possible: node discovery → node info; node discovery → named parameter reads. Include eligible all-items requests, known-argument requests better served by batching, ambiguous semantics, empty discovery, malformed output, missing parameter, disappearing/restarted nodes, and oversize fan-out. Keep **held-out ROS application** separate from development examples; do not encode evaluator answers in adapters.

### Crucial measurements

- Request-level **model adoption** (selected appropriate operation unforced), valid arguments, binding execution, exact per-request requested coverage, final factual support/correctness and unsafe/wrong-source results.
- Actual model decisions and input/output tokens; wrapper tool calls vs native ROS commands; recovery/retries; elapsed time; failed/skipped work; adapter/policy overhead.
- Report all attempts and separately comparable correct pairs. Record raw traces, model/provider, settings, exact Git commits, tool schema versions, environment state, error categories and time-qualified ground truth.

### Compact sequence rather than repeated isolated pilot rounds

**Step 1 — Freeze spec and controls:** finalize concrete schemas and safety contracts in the clean ROSA worktree, along with a small reproducible task suite.  
**Step 2 — One implementation mission:** build the minimal engine and two public operation adapters, plus mock/safety tests. Within that mission, perform an early model-adoption smoke check; treat failure as a reason to revise the exposed interface once, not to run an endless prototype series. No paid inference without user permission.  
**Step 3 — Matched evaluation:** run A/B/C on development and held-out cases with frozen scorer and identical resources.  
**Step 4 — Decide on H2:** only if valid policy disagreements recur and there is enough headroom, design and test adaptive D against C; otherwise present honest evidence for H1 and its limits.

### Practical promotion/stop conditions

- Do not promote C if supported-answer coverage or safety is worse than B, if unforced tool adoption is near-zero, or if total savings vanish after recovery/overhead.
- Do not claim generalization from a single ROS environment or one hardcoded tool pair. The second family and held-out evaluation provide **bounded** evidence, not universality.
- Do not claim mathematically optimized adaptivity unless an actual policy beats the same executor under a fixed rule. Negative findings are legitimate project results.

## 6. Decisions for the next review

1. Should the first model-visible interface be **two specialized public tools**, or **one constrained typed operation** with an enumerated read family? Prefer the simpler model interface unless the same internal engine can transparently support both.
2. Confirm the exact available wrapper signatures and choose the safest command/ROS-client backend without giving candidate-only functionality to controls.
3. Define a fair, compact suite of eligible/negative cases and ground-truth procedure before implementation.
4. Set acceptable correctness thresholds and a practical time budget for Dec 2; avoid expensive adaptive modeling without evidence of meaningful decision states.

**Current recommendation:** approve GLBE as an implementable *research candidate*, not a proven novel optimizer. Deliver an explicit typed contract, reliable result binding, and strong matched evidence first. Defer cost-based stopping; revisit it only on observed decision opportunities.
