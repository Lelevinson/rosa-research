# Action narration: independent primary-source review and D admission

Date: 2026-11-11. Scope: read-only source/literature review of the continuation package, with no ROS/model execution. This note is a design judgment, not experimental evidence.

## Decision

**Do not implement D for this mission. Run the authorized bounded A/B/C comparison.** A framework branch on an error already visible in the ordinary transcript has no demonstrated information or action advantage over C's static conditional instruction. Different prompt strings establish an implementation difference, not an incremental algorithmic result. An empirical instruction-following advantage is possible, but no evidence presently justifies it; that possibility must not be promoted into a supported mechanism.

The experiment can still establish a useful systems result: whether suppressing unnecessary action-turn narration preserves source-supported complete answers while reducing actual generation cost. Neither existing prose word counts nor the sources below answer that causal question.

## Primary-source checks

| Source and inspected section | Actual mechanism | Implication for this study |
|---|---|---|
| [TALE: Token-Budget-Aware LLM Reasoning](https://aclanthology.org/2025.findings-acl.1274.pdf), Section 5 and Figures 4–6 | TALE-EP first estimates a problem-dependent token budget, ordinarily with another model invocation, and inserts the estimate into the generation prompt. TALE-PT internalizes budget awareness through post-training. The budget search uses correctness and actual token reduction, rather than assuming smaller requested budgets always reduce output. | Adaptive output budgeting and prompt-based token reduction are established. This ROSA experiment changes action narration rather than problem-dependent numerical budgets. Charge all generation and any estimator overhead. Published reasoning-task results do not certify ROSA answers. |
| [CRANE](https://arxiv.org/html/2502.09061v3), Section 4 and Algorithm 1; [published ICML record](https://proceedings.mlr.press/v267/banerjee25a.html) | Decoding starts unconstrained. Generated delimiters select grammar-constrained windows; closing delimiters restore unconstrained generation. This is token-level constrained decoding, not tool-status prompt switching. | A decoder that changes constraints by mode already has close conceptual ancestry. The theoretical expressivity construction is not a guarantee that an arbitrary installed ROSA model preserves semantic correctness. No decoder or grammar implementation is needed for the authorized narration test. |
| [Guided-Structured Templates / ToolGT](https://aclanthology.org/2025.emnlp-main.1242.pdf), Sections 2.2–2.3 and Appendix A.2 | Fixed templates structure function selection, documentation review, parameter analysis/conversion, drafting and revalidation. A synthetic-data pipeline also supports fine-tuning. Appendix A.2 includes conditional behavior when tools or required information are insufficient. | Static prompts can already express conditional function-call behavior. This is a strong counterexample to treating external selection of a short normal/error prompt as inherently necessary. The paper does not establish universal superiority of no-thought or terse output. |
| [Constraint Tax](https://arxiv.org/abs/2606.25605), author abstract | Reports tool suppression when JSON Schema constraints and native tool calling are enabled together, with grammar masks implicated; proposes two-pass separation. Its behavioral hypothesis is distinguished from a verified internal mechanism. | Keep the A/B/C test on unchanged native tools. Do not assume joint schema/tool support or claim this paper proves failure of the particular installed Ollama stack. |

Verification boundary: TALE and ToolGT full PDFs and relevant method sections were inspected. CRANE's published landing page and author preprint v3 full HTML algorithm were inspected; the published PDF endpoint returned an unsupported content type, so exact final-version textual identity was not checked. Constraint Tax was checked at author-abstract level only; its experiments/code were not replicated. None of the papers was replicated in this review. The source summaries above are deliberately scoped; no global novelty-search completeness is claimed.

## Immediate discriminant check: two invocation envelopes

These are **illustrative design envelopes, not recorded invocations or runtime schema dumps**. For each state, A/B/C/D receive exactly the same base conversation, tool schemas, model/settings and public tool observation. Only the policy instruction differs. Neither envelope forces a tool call or restricts final answers. Actual implementation must retain real LangChain tool IDs and complete schemas.

Shared policy text for every arm: independent authorized read-only calls may be grouped; preserve dependency order; answer every requested field with source identity and uncertainty. A has no added narration policy. B adds: `When calling tools, omit unnecessary narration. Preserve complete final answers.` C adds: `When calling tools, omit unnecessary narration; after a tool error you may explain the repair briefly. Preserve complete final answers.`

Success-state envelope:

```json
{
  "messages": [
    {"role": "system", "content": "<same deconflicted base policy> + <arm instruction>"},
    {"role": "user", "content": "<same original saved task wording>"},
    {"role": "assistant", "tool_calls": [{"id": "call_1", "name": "ros2_node_list", "args": {}}]},
    {"role": "tool", "tool_call_id": "call_1", "content": "<same successful node-list observation>"}
  ],
  "tools": "<same exact bound registry schemas>",
  "model_settings": "<same checkpoint, seed, temperature and budgets>",
  "D_instruction": "When calling tools, omit unnecessary narration. Preserve complete final answers."
}
```

Error-state envelope:

```json
{
  "messages": [
    {"role": "system", "content": "<same deconflicted base policy> + <arm instruction>"},
    {"role": "user", "content": "<same original saved task wording>"},
    {"role": "assistant", "tool_calls": [{"id": "call_2", "name": "ros2_node_info", "args": {"nodes": ["/diag_turtle"]}}]},
    {"role": "tool", "tool_call_id": "call_2", "content": "<same complete wrapper observation containing the actual native error: Unable to find node '/diag_turtle'>"}
  ],
  "tools": "<same exact bound registry schemas>",
  "model_settings": "<same checkpoint, seed, temperature and budgets>",
  "D_instruction": "You may explain the repair briefly after the tool error. Preserve complete final answers."
}
```

The error is grounded in the existing extracted native ledger at `research/diagnostics/bottleneck_gate_20261110/native_calls.jsonl`: primary episode `11-t2-B-r0`, original archive member `evidence/primary-v1/11-t2-B-r0/trace.jsonl`, source line 13, `ros2 node info /diag_turtle`, return code 1, stderr `Unable to find node '/diag_turtle'`. This ledger is secondary extraction of a historical trace, not a fresh error experiment. The illustrative tool-message wrapper is explicitly not reconstructed as historical fact.

D's normal instruction is effectively B's instruction; its error instruction selects the permission already expressed by C. C has the same evidence necessary to select that behavior. D might reduce repeated conditional-instruction tokens or improve instruction salience, but its state detection, prompt changes and loss of prefix reuse also have costs. No result presently establishes a favorable trade-off, much less a distinct algorithmic contribution. This gate fails before D implementation.

## Disconfirming cases and interpretation rules

1. A successful read can deliver a semantically surprising or ambiguous result. A public `success` flag does not mean that the model needs no further reasoning. Framework status must not suppress source interpretation or force another action.
2. A failed read can be the correct endpoint of an unavailable-field task. Error status does not authorize retries indefinitely or imply a repair is needed. A complete final answer can correctly state the limitation.
3. An arm can save prose but add a model turn, choose the wrong source, or omit a field. Lower action word count is insufficient: score the final answer and charge all model/native work.
4. C can match D exactly in intended behavior on both envelopes. Unless different action/quality/cost behavior survives this control under equal information, D has no supported incremental delta.

A favorable A/B/C development result should be reported as exploratory prompt/systems evidence. Twelve single-seed episodes cannot establish statistical noninferiority, broad cross-application generalization, or a new framework-level algorithm. A negative result should stop the assigned branch without a fifth arm or renamed controller.

## Adversarial review of the frozen development design

Read-only review of `run_study.py`, `score.py`, `cases.json`, `PROTOCOL.md` and original ROSA tools/prompts. No code execution or modification was used for this review. Observations apply to the source read at review time, before subsequent corrections, if any.

No fatal A/B/C control-parity defect or runtime access to scoring truth was found. All arms derive from the same prompt builder and eight original tool schemas. The complete sequential block is removed. The isolated read-only argv backend and restricted registry apply equally. `score.py` is not imported by the runtime, and snapshot-derived values are evaluation only. Original tool outputs retain their shape. Conclusions remain about this restricted registry, fixture, checkpoint and exploratory development set.

Concrete issues to inspect before conclusions:

- **Call correlation:** `make_tools()` generates a fresh journal `tool_id`, rather than retaining the assistant's native tool-call ID. Saved model messages preserve native IDs, arguments and scratchpad messages; native events join to wrapper UUIDs. Repeated identical concurrent proposals cannot necessarily be paired unambiguously to model call IDs. Do not claim exact ID-preserving audit correlation without checking this boundary; missing joins should be recorded, not guessed.
- **Concurrent retry enforcement:** `native_guard()` checks completed failure counts, then increments them after a native command finishes. Several identical failing commands emitted concurrently can all pass admission before the first failure completes. The 64-attempt cap still bounds total native calls. Inspect actual trace for this race before claiming the one-additional-failed-attempt rule was mechanically guaranteed.
- **Activation strength:** automatic activation checks show a multi-call response, a two-node list argument and at least three successful native reads overall. They do not by themselves prove successful execution of both requested tool names in that same response or native overlap. Inspect timestamps/commands and final content for every arm. A successful node-info batch alone must not stand in for successful independent topic-info execution.
- **Checkpoint identity:** the driver logs Ollama tags and declares the frozen digest in cases.json; it does not assert that the named checkpoint resolves to that digest. Verify the saved response against the declared digest. Logging a configuration is weaker than validating the effective model identity.
- **Scoring boundary:** `strict_values` checks snapshot truth and format, including exact Python leaf types; it does not prove acquisition/support. Manual adjudication must establish successful model-visible evidence for every claimed field, the explicitly requested absent-node attempt, source/role distinctions, extra narrative claims, and truncation/final-answer completeness. Wrapper returns can contain native error dictionaries, so tool-return counts are not successful-tool counts.
- **Partial/failure accounting:** model metadata sums cover completed model responses. A timed-out/incomplete request may consume unreported backend generation; mark its token/time cost unknown rather than zero. Preserve launched cells without closeout and include them as failed/incomplete rather than dropping them from the denominator.
- **Recovery realism:** d1_recovery deliberately adds an absent-node instruction. It tests response to a real native error, but is not a verbatim historical d1 request, a natural failure-frequency sample, a held-out case or evidence of stale-incarnation prevalence. The protocol states this limitation correctly.

These are review findings, not assertions that the problematic events occurred. Parent inspection of actual artifacts must settle activation, retries, effective checkpoint, support and failure accounting. Do not silently repair already attempted identities or pool a corrected run as though nothing changed.
