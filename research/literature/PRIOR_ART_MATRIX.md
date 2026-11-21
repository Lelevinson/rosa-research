# Prior-art matrix

| Proposed family | Closest mechanisms / ordinary controls | Local evidence and required distinction |
|---|---|---|
| History-driven continuation | [AutoTool](papers/autotool.md), n-gram/backoff, [PASTE](papers/paste.md) | [Offline replay](../studies/autotool_iteration_20261112/REPLAY_REPORT.md): no candidate/backoff difference; action authorization and necessity unresolved. |
| Plan or program execution | [LLMCompiler](papers/llmcompiler.md), [ReWOO](papers/rewoo.md), [CodeAct](papers/codeact.md), [AWM](papers/awm.md) | Accepted plan or same-path helper is a strong control; historical adoption and answer completeness must be checked. |
| Batch/parallel native work | Ordinary fixed batching, async dispatch, persistent transport, AIMD/Gradient2 | [Native review](../studies/native_read_investigation_20261111/PRIOR_ART.md); charge setup, freshness and real critical path. |
| Selective/speculative read | [SpecAgent](papers/specagent.md), [selective classification](papers/selective-classification.md) | Reviewer/repair costs and independent necessity labels; sequential dependence limits guarantees. |
| Authority / semantic substitution | [AuthGraph](papers/authgraph.md), [AuthorityFlow](papers/authorityflow.md), [CaMeL](papers/camel.md) | [Capability findings](../studies/capability_discovery_20261110/REPORT.md): observed value similarity cannot authorize substitution. |
| Evidence and conditional decisions | Fixed composites, short-circuit/sequential testing | [CPAW report](../studies/cpaw_prototype_20261110/REPORT.md); compare fixed/adaptive alternatives with equivalent contracts. |
| Narration and generation | Static conditional prompts, TALE, CRANE, ToolGT | [Prior-art review](../studies/action_narration_20261111/PRIOR_ART_REVIEW.md); compare supported answers and all costs. |

This matrix is an entry point, not exhaustive novelty clearance. Inspect original sources and nearest negative evidence for the exact claim.
