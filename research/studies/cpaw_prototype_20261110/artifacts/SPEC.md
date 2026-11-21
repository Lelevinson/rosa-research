# ROSA — Adaptive Information Acquisition: Algorithm Design Contract v0.1

**Date:** 2026-11-10  
**Status:** Research design and executable specification; **not implemented, not experimentally validated, not a novelty claim**.  
**Objective:** A reusable framework-level optimization contribution for ROSA/LLM agents, potentially publishable if it beats strong comparators on correctly completed tasks without per-application semantic mappings. Performance may mean native cost, latency, token/LLM overhead, or a defensible weighted combination; do not constrain success to one metric.

## Decision summary

**Retain for focused prototype:** *certificate-preserving adaptive acquisition with uncertainty-aware execution waves*, provisionally **CPAW**. It is an algorithmic research candidate, not an algorithm selected for a final paper. The candidate is deliberately **not** “early stop + ordinary batching” alone. The experiment will isolate whether uncertainty-aware *online wave choice* is useful over the best classical batching and sequential testing methods **at matched information and safety privileges**.  

**Crucial discovery before coding:** Multiple close papers cover classic SBFE, staged/batched testing, and robust uncertain probabilities. In particular, *A General Framework for Sequential Batch-Testing* (Tan, Xu & Nagarajan, 2024 preprint / Operations Research Letters 2025) covers batching AND / k-of-n and has approximation guarantees; *Distributionally Robust k-of-n Sequential Testing* (Tan & Nagarajan, 2026 preprint) covers uncertainty intervals for test outcomes. “Adaptive batches with uncertain p” is **not independently defensible novelty**. The **hypothesis**, requiring a head-to-head test and mechanistic comparison, is an **online, outcome-conditioned, uncertainty-aware wave policy with explicit unresolved outcomes, measured runtime/setup cost and an admissibility/abstention layer for generic agent tools**. This may still reduce to an ordinary composition of known methods; do not call it publishable until this delta survives comparator parity.

**Crucial ROSA limitation:** The Nov 10 capability discovery report inspected 47 ROSA tools and found **zero informative machine-checkable output schemas** in their registered `StructuredTool` metadata. Arbitrary raw text cannot be safely converted into Boolean propositions, and identical values do not establish semantic identity. The planner **must not claim general optimization of all existing ROSA tools**. It can optimize a tool only when an independently supplied *typed outcome contract* exists. All remaining tools and tasks retain ordinary ROSA dispatch; report the eligible fraction. A generic contract at tool-authoring/registration time is allowed only if it is **not** a manually prepared question-to-source map or per-robot semantic adapter. If the only way to demonstrate benefit is to write special parsers or target predicates for benchmark tools, this candidate does **not** satisfy the project's generalization premise.

## A. Problem definition

Given one user request and an LLM-produced (not evaluator-supplied) **proposed** information plan, suppose it can be represented as a known set of read-only propositions `b_1 ... b_n` and a supported completion function `F(b_1,...,b_n)`, initially `ANY`, `ALL` or `K_OF_N`. Each proposition is acquired from **one explicitly named authorized tool invocation**; no substitution or inference that another arbitrary tool is equivalent. Each invocation returns `TRUE | FALSE | UNKNOWN` plus evidence provenance; `UNKNOWN` includes timeout, missing value and failure. Tool calls may be executed in waves of at most `K` concurrent calls and may have nonadditive wave startup costs or latency.

The **LLM remains responsible for interpreting the user request and selecting targets/tools**. A standard agent turn may propose a plan; the optimizer is not given hidden answers, source maps, correct predicates or benchmark labels. The engine validates structure, authority, bindings and evidence only. It **cannot certify** that the LLM's plan corresponds to the natural-language intent. An independent final scorer must catch wrong goal/target/source and omitted facts. Failed plan validation or unsupported/ambiguous goal means standard ROSA, not assumed successful optimization.

The algorithm makes **one decision per executable wave**, within the framework, *without an LLM call between waves*. It may reduce native calls when early termination is logically justified; it may reduce latency via concurrency if independent reads are legal. It does **not** attempt to reduce inferencing time, infer tool equivalence, or reuse stale observations.

### Generic plan / probe API (conceptual, not existing ROSA schema)

```python
Goal = {"kind": "K_OF_N", "k": 1, "probe_ids": ["p1", "p2", "p3"]}
# The LLM may propose only target calls, NOT authorization or truth contracts.
ProbeRequest = {"id": "p1", "tool_name": "registered_read_tool",
                "arguments": {"target": "/scope/a"}}
# Separately, the TRUSTED registry/executor owns these facts (not model-controlled):
TrustedRegistration = {"tool_name": "registered_read_tool",
                       "read_only": True,
                       "outcome_contract": "TRI_STATE_V1",
                       "concurrent_safe": True}
# The executor records provenance, rather than accepting model-authored claims:
Result = {"probe_id": "p1", "value": True, "status": "OK",
          "source": "registered_read_tool", "scope": "/scope/a",
          "observed_at": 0.0}
```

**Security invariant:** A model-proposed JSON field saying `read_only: true`, `contract: TRI_STATE_V1` or `authorized: true` has **zero authority**. The trusted registry, permission system and executor must independently supply and enforce these properties. Provenance is executor-originated, not accepted from the LLM.

`TRI_STATE_V1` is a **capability interface**, not a library of app-specific mappings. A newly written tool can expose it directly without changing the scheduler. But retrofitting legacy CLI-text tools may require implementation changes: **those are excluded from the claim and test unless the conversion is transparently general and independently justified**. The user-facing answer must keep all source/obligation requirements separate from this computational certificate.

### Logical certificate

At any state let `t` = confirmed TRUE, `f` = confirmed FALSE, `u` = observed UNKNOWN, and `r` = not-yet-run. For a k-of-n goal:

- Return **TRUE** only when `t >= k`.
- Return **FALSE** only when `t + u + r < k`.
- If all probes have been attempted and neither rule applies, return **UNRESOLVED**. Do not turn UNKNOWN into FALSE or success.
- For `ANY`, set `k=1`. For `ALL`, set `k=n`. Other user requests, especially enumeration and multi-fact summaries, do **not** inherit early-stop eligibility.

The certificate is **logical only relative to the declared propositions and their stable observation scopes**. When robot/world state changes between probes, a cross-probe decision may not describe one coherent state. Require an explicit valid snapshot/state stability policy or limit the claim to observations at their measured times; otherwise abstain. Plain timestamp proximity alone is not atomicity.

## B. Cost and uncertainty model

Let an action `B` be a nonempty subset of not-yet-attempted, mutually independent *read-only* probes with `|B| <= K`. Read-only alone is insufficient for parallel safety: the executor must also authorize concurrency and resource sharing. Obtain durations and native/transport costs from **prior training/calibration data only**, never held-out answers. Model three outcomes `T/F/U`; do not assume independent probabilities without stating and checking that restriction.

A task-level objective can be:

`J(pi) = E[sum_{waves B} (sum_{i in B} c_i + setup(B) + lambda * makespan(B)) + planner_overhead]`

Here `setup` is an actually observed per-wave cost, `makespan` is observed wave elapsed time (not a sum of parallel durations), `lambda` converts time into an explicit trade-off weight, and `c_i` includes native work. Do **not** count inference time twice, or treat model latency as a guaranteed saving: inference is measured separately. Report native cost and actual elapsed time independently from any composite score. If a task cannot reach a justified answer by the deadline/budget, return `UNRESOLVED` and count it separately rather than secretly optimizing cost by failing tasks.

Outcome probabilities and durations are uncertain: build a confidence/uncertainty set `Theta` from **training traces or prior observed executions only**, keyed by generic tool/contract metadata and observable scope, **not hardcoded node/tool-name semantics**. For a previously unseen tool there may be no calibrated signal: use a broad uncertainty set and the standard baseline/fallback. Correlation and state changes invalidate the product-distribution simplification; a robust or scenario model must state which dependence it supports. Do not claim distribution-free optimality.

### Chosen policy: bounded robust rollout against a strong baseline

At each state `s`, consider a small, deterministic candidate set of waves: (1) the strongest next singleton(s) from cost/probability order, (2) a prefix of that order, (3) feasible all-remaining / full native batch, and (4) a bounded number of alternate combinations chosen from admissible probes. Limit combinatorial growth. Candidate generation is **tool-name agnostic**.

For each `B`:

`Q_h(s,B) = immediate_measured_or_estimated_wave_cost(B) + sup_{theta in Theta} E_theta[V_{h-1}(next(s,B,Y_B))]`

`V_0` is the best *strong baseline continuation cost*, not zero. `h` is a bounded lookahead depth and `Y_B` are possible T/F/U outcomes. Use exact enumeration for toy instances, bounded scenarios for larger instances, and label scenario approximations as such. The policy chooses the lowest estimated `Q_h` **only when its conservative advantage exceeds its estimated computation/preparation overhead**. Otherwise dispatch the strong reference wave. A zero or misleading uncertainty interval must not be silently substituted for missing history.

This **fallback margin** is a proposed guard against overfitting overhead, not a theorem that performance is never worse. Evaluate the policy both with and without it; report cold-start fallback frequency and confidence-interval coverage. Budget exhaustion, invalid contracts, model disagreement about user intent, or failed evidence verification must not suppress mandatory acquisitions.

### Pseudocode

```text
plan = model_generated_plan_from_normal_ROSA_turn(query)
if !validate_generic_plan(plan) or !prove_executable_contracts(plan):
    return normal_ROSA_execution(query)

state = all_requested_probes_unobserved()
while not logically_decidable(state):
    if budget_expired: return unresolved_with_evidence(state)
    admissible = authorized_independent_read_probes(state)
    if not admissible: return unresolved_with_evidence(state)
    candidate_waves = generate_generic_waves(admissible, baseline_policy, K)
    wave = bounded_robust_rollout_or_baseline(candidate_waves, state, Theta, time_budget)
    observations = execute_through_original_ROSA_dispatcher(wave)
    state = attach_checked_tri_state_evidence(state, observations)
return certified_result_and_complete_evidence(state)
```

No hidden native calls, synthetic semantics, silent argument repair or model-inference loops. Preserve attempts, errors, provenance, unknowns, and unacquired probes for the final LLM and independent scorer.

## C. What is actually new? Comparator-level discriminators

### Clearly **not new**

1. Short-circuit evaluation of `ANY`/`ALL` and `K_OF_N`.
2. Optimal sequential ordering `c_i/p_i` for simple independent `ANY` tasks with known positive probability `p_i` and additive per-test cost (exchange argument).
3. Staged/batched testing and fixed non-adaptive batch schedules.
4. Distributionally robust probability intervals for k-of-n sequential testing.
5. Exact branch-and-bound / decision diagram methods for stochastic Boolean function evaluation.
6. Ordinary tool registration contracts, fixed conditional helpers, concurrency, and standard fallback.

### Candidate incremental delta (unproven)

Joint decision over **outcome-contingent waves**, **tri-state/missing evidence**, **uncertain heterogeneous costs/probabilities**, **explicit computation overhead**, and **conservative reference-policy admission**, inside one real ROSA tool-execution boundary with no per-application mappings or extra LLM decisions. The research claim would be about **measured policy advantage attributable to the joint rule**, not about first discovery of adaptive batching or unknown probabilities.

### Critical self-check: `ANY` and `ALL` do not demonstrate meaningful branching

With reliable binary probes and no UNKNOWN values, an `ANY` task has only one possible nonterminal outcome after each wave: all attempted items were FALSE. Similarly, for `ALL`, all attempted items must be TRUE to keep going. Consequently, an outcome-conditioned policy for these cases is essentially a **prearranged batch sequence with early stopping**. It does *not* establish a new adaptive decision rule. These cases are useful regression checks but **must not be the primary novelty demonstration**. The first mechanism-discriminating workload should use an interior threshold `1 < k < n`, composite obligations with defensible semantics, or properly modeled UNKNOWN branches.

Concrete branching witness for `K_OF_N(k=2,n=4)`: after the first two authorized probes, `T,F` means one additional TRUE is needed; `F,F` means both remaining probes must be TRUE. Suppose two remaining probes have equal cost and probability of TRUE 0.95 and 0.05 respectively. With small setup cost, the best **next singleton** is the high-TRUE-probability probe after `T,F` (seek one TRUE), but the low-TRUE-probability probe after `F,F` (seek one FALSE). Both are nonterminal states; an outcome-conditioned policy changes its next action. **This adaptive behavior is classical k-of-n sequential testing, not an originality claim.** The proposed extension must outperform or improve an exact/strong adaptive comparator after uncertainty, wave costs, and overhead are matched.

### Hard comparator requirements

Use identical tasks, available tool registry, typed outcome capability, concurrency limits, failures, observations, budgets and execution permissions in all arms:

- Unmodified ROSA **as a descriptive reference only**.
- ROSA with the default anti-batching prompt **replaced/deconflicted**, not merely appended to; verify actual batched dispatch.
- Same-capability full batch / parallel-all.
- Same-capability sequential `c/p` (for ANY) / **classical optimal adaptive k-of-n policy** under its assumptions (Salloum–Breuer / Ben-Dov), with ordinary early stop; a nonadaptive sorter alone is a weak comparator for interior thresholds.
- A fixed-size / fixed-prefix batch policy and the Tan–Xu–Nagarajan 2025 sequential batching comparator where the published assumptions fit.
- Adaptive greedy with the same outcome and cost information, including UNKNOWN handling.
- Robust non-adaptive k-of-n baseline from Tan & Nagarajan 2026 where assumptions fit, and a **small-instance exact dynamic-programming oracle** under stated distributions.
- Existing JTVR/composite and Martin macro findings are contextual evidence, not unfair weak arms; add matching macro baseline only for genuinely overlapping tasks with parity of permissions.

**Necessary novelty signal:** Show held-out cases where the candidate and strongest prior policy make *different wave decisions given the same information*, and improvement remains after overhead and correctness matching. Difference from only `batch_all` or original weak prompt is insufficient. If under matched information the policy reduces to an existing algorithm, describe the outcome as an engineering replication, not a new algorithm.

## D. Design-stage counterexamples (must pass before any ROS integration)

1. **Unrelated data with equal values:** two tools returning 75 for unrelated entities must never be treated as alternatives; no equivalence resolution exists.
2. **Classical degeneracy:** for reliable binary `ANY`/`ALL`, the sequence of nonterminal observations does not branch. Do not misrepresent preset staged batching as adaptive novelty. Interior `K_OF_N` needs comparisons to the classical optimal adaptive k-of-n algorithm.
3. **Opaque output:** `"Node X ready"` or CLI text without a validated typed proposition cannot be dynamically parsed into an eligible stop certificate; fallback.
4. **Wrong LLM plan:** user asks for *all* defective nodes but model proposes `ANY`; structural validity is not task correctness. Independent scorer marks answer incomplete; no claim of safe optimization.
5. **UNKNOWN:** one UNKNOWN and the rest FALSE under `ANY` must yield UNRESOLVED, not FALSE.
6. **Changing state:** non-atomic readings across a mutable ROS graph do not constitute a consistent snapshot; abort/scope the claim.
7. **Dependence/resource:** a mutator or dependent read may not be co-scheduled solely because it has a structured output; consult permissions/dependencies; default ordinary executor.
8. **No free history:** all new tools cold-start without semantic maps; record how often the optimizer abstains. A new typed tool should register with no scheduler code modification.
9. **Dominant inference:** simulate slow local LLM while keeping tool policy fixed; report the unchanged inference component and native savings. No fabricated end-to-end speedup.
10. **Adversarial probabilities:** when p estimates are wrong or samples correlated, the guarded policy should fall back or show failures transparently. Do not assume robust bounds without calibrated coverage.
11. **Native aggregation:** if ROSA already offers one bulk call for all targets, all arms have that capability. Counting only wrapper calls is invalid.
12. **Pathological setup:** if per-wave startup overhead is zero and latency is not valued, **simultaneous execution cannot improve expected number of necessary `ANY` reads over the optimal sequential policy**; this is a self-check, not novelty. With high measured setup/makespan costs, batching can become rational.
13. **Certificate vs user intent:** a correct `K_OF_N` proof never implies that an unrelated natural-language goal was addressed. Score both separately.

## E. Implementation and evaluation stages (single-threaded; no parallel worktrees)

**Stage 1: pure algorithm/contract prototype, no ROSA core edits.** Implement Goal/Probe/Evidence validators; an exact small-n DP reference; classical baselines; bounded wave selector with fallback/abstention. Test all thirteen counterexamples. Store deterministic seeds/fixtures and full action logs. No privileged evaluation truth enters policy. Use offline synthetic data **only** to establish algorithmic mechanics and theoretical edge cases, not to claim ROSA efficiency or generalization.

**Stage 2: source-grounded eligibility and generic integration.** Inspect which **existing** ROSA tools can furnish trustworthy structured T/F/U propositions without benchmark adapters. Add opt-in routing *only* for those tools or for independently authored new typed tools. Log eligibility and abstention fraction by tool family, plus prompt-inferred goal errors. If eligibility is near zero on representative ROSA tasks, this is a limitation of the method for current ROSA; **do not manufacture application-specific wrappers to raise the denominator**. Still complete the small policy experiment and report whether this should remain a narrow research component or be reframed. Original ROSA path must remain unaffected.

**Stage 3: matched end-to-end tests.** After freezing policies and task families, use local + hosted backends only if permissions and budget permit. Compare on held-out tool families and nontrivial tasks including no-shortcut enumeration; independent evaluator scores full factual correctness/source/scope, logical certificate, task success, abstentions, failures, unknowns and latency/cost. Also separate eligible-only analysis from all-task intention-to-treat analysis. The teammate's fixed macro catalogue and earlier JTVR evidence are existing controls, not generalization evidence.

**Metrics:** supported-correct full answers; eligible/abstained tasks; native ROS operations (not just tools); total model requests/tokens; wave count; end-to-end time; native wall time; scheduler runtime; extra memory/preparation and history collection; retries; cache hits; failure/unknown rate. Pair by task and run, keep attempts and unsuccessful cases, use uncertainty intervals where enough repetitions. Avoid changing a baseline's rights or task inputs to make the candidate win.

**Artifact rules:** create an isolated experiment branch only at coding time; save immutable source revision, frozen protocol, raw traces, outputs, seed, environment and model settings under a durable repo-relative `research/_artifacts/...` (never solely `/tmp`); no unreviewed edits to teammate branch or previous evidence. Keep `rosa-llm` optional and do not spend paid API quota without authorization.

## F. Research decision ledger

| Item | Decision as of 2026-11-10 | What could change it |
|---|---|---|
| Adaptive acquisition | **Conditionally retained for a focused prototype** | Strong prior policy dominates or eligible fraction too small for useful ROSA impact |
| Generic unknown-aware wave selector | **Specific mechanism defined**, not proven novel | Demonstrates distinct correct actions + lower total cost on new tool families at matched information, or fails those tests |
| Output capability generalization | **Strictly typed-contract-only** | A generic, externally validated output contract mechanism that does not depend on app-specific mappings |
| Paper status | **Not established** | Mechanism-level delta from strongest cited prior work plus replicable held-out advantage, ideally formal property beyond basic certificate safety |
| LLM timing/freshness | **Not a fundamental assumption** | Optional metric; do not claim speedup from local-model characteristics |
| Next action | **One Codex prototype assignment for Stage 1 (plus narrow Stage 2 eligibility instrumentation)** | No more general GO/NO-GO report; code and direct comparator evidence should be returned |

### Immediate codex contract (when implementing)

Implement exactly Stage 1 and its self-checks, plus an instrument that counts real ROSA eligible tools *without modifying their semantics*. Never hide the absence of typed output contracts. Unit tests must include branch-contrasting `K_OF_N` cases (not merely `ANY` and `ALL`), corrupted goal/UNKNOWN, newly registered typed tools, miscalibrated probabilities, budget/time fallback, true concurrency restrictions, and no-hidden-map checks. Report whether the policy ever differs from a **strong existing batching algorithm** on the same information; otherwise do not claim novelty. Provide code + tests + truthfully labeled negative/positive results. Do **not** stop after an initial failure just to issue a new NO-GO report; identify cause, test at least one principled correction, and preserve both versions.

## G. Primary literature (checked for mechanism overlap)

1. Golovin & Krause (2011), *Adaptive Submodularity: Theory and Applications in Active Learning and Stochastic Optimization*, JAIR. https://mlanthology.org/jair/2011/golovin2011jair-adaptive/
2. Deshpande, Hellerstein & Kletenik (2016), *Approximation Algorithms for Stochastic Submodular Set Cover with Applications to Boolean Function Evaluation and Min-Knapsack*, ACM TALG. https://doi.org/10.1145/2876506
3. Tan, Xu & Nagarajan (2025; 2024 preprint), *A General Framework for Sequential Batch-Testing*, Operations Research Letters. https://doi.org/10.1016/j.orl.2025.107348
4. Harris, Nagarajan & Tan (2025), *Sequential Testing with Subadditive Costs*, IPCO. https://arxiv.org/abs/2501.18010
5. Tan & Nagarajan (2026), *Distributionally Robust k-of-n Sequential Testing*, arXiv. https://arxiv.org/abs/2603.23705
6. Zong, Lehtonen & Rintanen (2026), *Cost-Optimal Decision Diagrams for Stochastic Boolean Function Evaluation*, arXiv. https://arxiv.org/abs/2606.24672
7. Hellerstein, Kletenik, Liu & Witter (2022), *Adaptivity Gaps for the Stochastic Boolean Function Evaluation Problem*. https://arxiv.org/abs/2208.03810
8. Salloum & Breuer (1984), *An Optimum Testing Algorithm for Some Symmetric Coherent Systems*. https://doi.org/10.1016/0022-247X(84)90064-7 ; Ben-Dov (1981), *Optimal Testing Procedures for Special Structures of Coherent Systems*. https://doi.org/10.1287/mnsc.27.12.1410
9. Nielsen, Rohwedder & Schewior (2025), *Non-Adaptive Evaluation of k-of-n Functions: Tight Gap and a Unit-Cost PTAS*. https://doi.org/10.4230/LIPIcs.APPROX/RANDOM.2025.26

**Project evidence read:** `ROSA_RESEARCH_CONTEXT.md` (Sections 0 and 12); `REPORT.md` (Nov 10 capability-discovery negative study); `ROSA_LLM_Decision_Optimization_Investigation_2026-11-10.md`; `ROSA_Bottleneck_Evidence_Gate_2026-11-10.md`. The latest context document predates the subsequent conversational candidate-selection; that historical distinction is preserved rather than silently rewritten.
