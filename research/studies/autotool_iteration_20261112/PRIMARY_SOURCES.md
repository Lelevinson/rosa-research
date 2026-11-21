# Primary-source mechanism review, 2026-11-12

This is the independent literature/source component of the authorized AutoTool
mission. **L** denotes an inspected literature mechanism, **F** inspected source,
and **H** this reviewer's inference. It is not a replication result, execution
authorization, or a claim that the proposed candidate improves ROSA. No inference
provider or ROS operation was invoked by this review.

## Source identity and inspection trail

The public author repository was downloaded without running it. Resolved commit:
`c7010ff49750ed338fec61556f7797b104a6826e` (2025-12-28,
`feat: add ppt & poster`), from
[jiajingyyyyyy/AutoTool](https://github.com/jiajingyyyyyy/AutoTool).
`research/_artifacts/autotool_iteration_20261112/sources/AUTOTOOL_PIN.json`
records the revision and hashes of the inspected source subset. Core modules,
the embedding implementation, README, primary agent, and failure checker are
preserved. The full AgentBoard dependencies, model weights, data, and embedding
pickle are not included or executed. No repository license file was found in
the downloaded checkout; preserve attribution and check redistribution terms
before publishing the review archive publicly.

Paper downloads and exact SHA-256 values are in adjacent
`DOWNLOAD_MANIFEST.json`. HTML-to-text extraction is mechanical; original HTML
is retained. The ICML AWM PDF and selective-classification PDF were extracted
using a temporary `uv --no-project --with pypdf` environment. Project dependency
files were unchanged. Initial sandbox DNS failure, a blocked AAAI publisher page,
and absent `pdftotext` were resolved using public author source/arXiv and local
PDF extraction (`pypdf==7.0.1`). No failed fetch is represented as a successful
inspection.

| Source | Version inspected | Portions inspected |
|---|---|---|
| [AutoTool](https://arxiv.org/html/2511.14650v1) | arXiv:2511.14650v1, AAAI paper DOI supplied by mission | Sections 4.3–4.5, 5.3–5.4; Appendix A algorithms, D failure cases, G limitations, H filling criterion, I n-gram comparison |
| [PASTE](https://arxiv.org/html/2603.18897v3) | v3, 2026-06-16; current title *Parallelizing Tool Execution and LLM Generation for Low-Latency Agent Serving* | Sections 3.2–4.3, 6.6–6.9 |
| [Agent Workflow Memory](https://proceedings.mlr.press/v267/wang25bx.html) | ICML 2025 PDF, pp. 63897–63911; preprint v1 used as supplementary cross-check | Sections 2.2–2.3, 4.1–4.3, Appendix F/Table 13, workflow induction/evaluation |
| [LLMCompiler](https://arxiv.org/html/2312.04511) | retrieved HTML identifies arXiv:2312.04511v3, 2024-06-05 | Sections 3.1–3.4, 4.1–4.2, 5.1–5.3; Appendix B |
| [ReWOO](https://arxiv.org/html/2305.18323) | retrieved HTML identifies v1 | Sections 2.1–2.3, 3.2 and Figure 6 tool/failure contrasts, limitations |
| [CodeAct](https://arxiv.org/html/2402.01030) | v4, 2024-06-07 | Sections 2.1–2.4, 3; atomic-call format comparison and training-data ablation/Table A.8 |
| [SpecAgent](https://arxiv.org/html/2610.21463v1) | v1, 2026-10-15 | Algorithm 1, Sections 3.1–3.3, 4.2–4.3, 5 design/acceptance analysis |
| [Selective Classification](https://arxiv.org/pdf/1705.08500v2) | Geifman & El-Yaniv, v2, 2017 | Sections 2–3, Algorithm 1, Lemma 3.1/Theorem 3.2, Section 5 validation split |
| [Tracer](https://arxiv.org/html/2610.21267v1) | v1, 2026-10-15 | Sections 2–3.7, 5.6; description-only/edge-memory and constant/learned-weight ablations |
| [AuthGraph](https://arxiv.org/html/2605.26497v1) | v1, 2026-05-26 | Sections 3.1–3.4, parameter-policy/source alignment and clean authorization context |
| [AuthorityFlow](https://arxiv.org/html/2611.04673v1) | v1, 2026-11-03 | Sections 2.1, 3.1–3.4, 4.3: task-aware authority, support tracing and ablation |
| [CaMeL](https://arxiv.org/abs/2503.18813) | v2, 2025-06-24 | Abstract and public method overview; full HTML retained, no exhaustive method/ablation claim |

The publisher's DOI landing page was blocked. The author preprint and pinned
implementation were inspected; byte identity with the final AAAI PDF is
**unverified**. Preprint/final-version differences must remain possible.

## What the parent already does

**L — AutoTool (paper).** TIG combines transitions and parameter dependencies.
CIPS mixes frequency and task/intuition-to-description similarity. Parameter
completion tries dependency backtracking, environmental state, then heuristics;
uncertain attempts return to the LLM. Section 5.4 studies threshold/context weight
under inertia-rate/consecutive-call restrictions. Appendix I already compares a
trigram sharing the same filler, with and without recovery. Appendix D explicitly
identifies wrong-context parameters, redundant actions and overgeneralization.
Appendix H counts syntactic validity plus successful environmental feedback as
filling success; this does not establish complete user-task satisfaction.

**F — pinned implementation (source locations below).** The selector's candidate
frequency is multiplied by `1 - 1.1**(-support)`. It adds a SimCSE semantic term
and applies a strict threshold. `is_subsequence` finds the first **contiguous**
match. The active agent uses the last 50 characters of the preceding thought as
intuition. It limits inertia frequency and consecutive use, disables prediction
after domain-recognized failures, and has a fixed recovery after repeated invalid
actions. Filling learns matches by equality/list membership, then uses historical
source slots and domain adapters. The latter contain explicit task parsing and
semantic state. The native n-gram uses `n-1` preceding tools; `n=2,3` corresponds
to mission context lengths `k=1,2`. It does not automatically append STOP.

| Pinned file | Inspected lines | Reproduction consequence |
|---|---|---|
| `autool/core/tool_predict/datastruct.py` | 285–320, 602–722, 871–900 | Candidate indexing, support factor, score, threshold and contiguous match; not a calibrated complete-action probability |
| `autool/core/tool_predict/ngram_predictor.py` | 12–94 | Ordinary conditional-frequency baseline is native prior art |
| `autool/core/param_completion/param_dependency.py` | 77–177 | Equality/membership discovery provides association, not causal authorization |
| `autool/core/param_completion/param_completion.py` | 175–332 | Active `fill` uses dependency and environment context; a defined fallback method is not automatically active |
| `autool/core/param_completion/domain/tool_query.py` | 322–473 | Domain/task-specific contextual rules cannot be transplanted as a general ROSA binder |
| `agentboard/agents/test_agent.py` | 658–808 | Rate limits, failure rejection, fixed invalid-action recovery, thought suffix and prediction/fill/fallback |
| `autool/utils/parser/check_action.py` | entire file | Failure recognition is task-specific string matching; give constrained parent the same public structured error signal as controls |
| `autool/utils/embedding.py` | initialization and get_embedding | Model/tokenizer, cache and embedding overhead must be paid; source import can initialize model state |

**F — paper/code differences that matter.** Paper CIPS uses
`(1-alpha)*frequency + alpha*context`; pinned code uses
`alpha*frequency + (1-alpha)*semantic`. They coincide at 0.5 only. The paper's
list-source discussion says random unused choice; pinned filler uses first unused.
These are not permission to silently substitute a different algorithm. A no-map,
no-SimCSE adapter is an explicitly **constrained parent**, with unavailable
components and changes listed. Its measured cost cannot be represented as full
AutoTool cost. Neither successful tool calls nor CIPS establish necessity.

## Closest alternatives and adversarial implications

**L — PASTE.** Recurring patterns include tool/status context, argument mappers
instantiated from current payload, empirical confidence and expected-benefit
admission. Results remain isolated until the LLM emits the matching invocation.
Sections 6.6–6.9 examine scheduler ablations, prediction accuracy, side effects and
overhead. Therefore status-conditioned prediction and current-result argument
mapping are already present; the relevant mission difference is replacing a
decision, which removes PASTE's confirmation protection. PASTE's tool-only
ablation also warns that isolated tool speedups can increase system queueing.

**L — AWM.** Workflows abstract experiences and enter model memory; online
induction uses an evaluator for successful trajectories. Section 4 compares
rule/LM induction, text/code and observation representations. Appendix F also
wraps workflows as callable parameterized actions: AWM is not limited to prompt
hints. The final PDF's Table 13 lists task SR 4.8 for AWM and 3.6 for its action
variant, while adjacent prose claims the same 3.2; preserve this internal
inconsistency and avoid using that prose as a quantitative baseline claim.
Dynamic intermediate selections and low macro adoption are relevant failure
modes. Charge induction, evaluator and memory cost in any future comparison.

**L — LLMCompiler.** A model produces tasks/dependency placeholders; a fetching
unit substitutes observed outputs and dispatches ready independent tasks. It
supports streamed planning and model replanning for complex branching. Sections
5.1–5.3 separately evaluate independent, dependent and replanning workloads;
Appendix B discusses planning failures. This is a capable ordinary executor,
provided an accepted plan exists. It does not establish that the current local
model will reliably produce such plans, nor that an unselected history path is
authorized by a user request.

**L — ReWOO.** Planner emits interdependent plans/evidence variables before tool
responses; Workers supply actual evidence; Solver produces the answer. Figure 6
studies extraneous tools and forced tool failure. Planner specialization is a
separate training component, not required for every use. It is a strong comparison
for a predictable accepted workflow, with plan/solve costs counted. Later
observation-dependent judgment remains a limitation; do not equate a populated
evidence variable with entailment or full answer coverage.

**L — CodeAct.** Executable Python supplies native control/data flow and real
observations, including errors, in multi-turn interaction. Section 2 compares
atomic action formats and complex tool use; Section 3's training ablation removes
CodeActInstruct/general conversations. It is a strong accepted-program comparator
for branching and parameter reuse. An action representation and a trained agent
are different claims. Prior local program-adoption failure must remain in the
comparison; Python expressivity does not prove native model adoption.

**L — SpecAgent.** A weak model executes reads and holds the first state-changing
action, including final submission. A strong reviewer accepts a semantically valid
prefix and repairs rejection. At chunk length K, read-only chunks can commit
without review. Sections 4–5 separate token/traffic, FLOP and latency costs and
show acceptance/repair dependence. The MCP edge/cloud deployment does not show
uniform latency reduction. A history predictor plus semantic reviewer would
inherit this close mechanism and must pay draft/review/repair costs. Read-only
execution permits discarding results; it does not certify useful acquisition.

**L — selective prediction.** Geifman & El-Yaniv formalize selective risk as
conditional loss on accepted cases and coverage as acceptance mass. SGR chooses
a threshold with finite-sample binomial risk bounds under i.i.d. labeled samples,
with correction for threshold search. These are established statistical tools.
ROSA sequential boundaries are dependent and next-action agreement is a different
label from necessity. Calling Wilson/Clopper–Pearson/SGR on those boundaries does
not manufacture independent samples or missing semantic labels. Even with zero
failures, a one-sided 95% binomial bound needs 59 independent cases to lower-bound
success at 95%; that arithmetic alone is not a guarantee for this corpus.

**L — wider mechanism search.** Tracer already combines prefix transition counts,
context-specific edge memory, learned blending and confidence/OOD fallback, but
retrieves tools for a model that still chooses; it does not establish full-action
bypass. Its ablations compare description-only memory, constant blending and trie
depth. AuthGraph compares an isolated user-intent authorization graph with a
model-derived provenance graph; AuthorityFlow combines task-aware authority,
parameter support tracing and authorization verification. These are semantic
model-supported security mechanisms, not cost-free typed binders. CaMeL's public
overview separates trusted control from untrusted data and enforces capability
flow. Provenance, source authorization and task necessity must stay distinct.

## Mechanism-level comparison and actual possible increments

The following are **H — independent judgments**, not measured effects.

| Shared mechanism | Actual incremental question | Extra inputs/compute | Closest ordinary control | Counterexample | Evaluation needed |
|---|---|---|---|---|---|
| AutoTool + PASTE outcome/context scoring | Does any signal improve complete-action risk/coverage beyond equal conditional counts? | Outcome/schema features, support and calibration | Same-feature conditional table + STOP | Successful list call is followed by final for names-only, details for another goal | Episode/family-separated complete tool+args+STOP diagnostics; necessity remains independently judged |
| Parent parameter edges + ordinary typed binding | Can history resolve a source identity that public contracts actually authorize? | Slot hypotheses, origin IDs, ambiguity checks | Unique current typed/authorized source binder | Two equal strings from different roles; unique string still comes from wrong role | Distinct-source tests, renamed schemas, stale/text observations, no equality-as-authorization |
| Selective prediction + threshold | Does joint action calibration improve useful coverage at fixed real error? | Independent labeled development cases and interval/search accounting | Same calibration on simple predictor | High successor frequency but wrong arguments or unnecessary read | Honest support counts, episode clustering, complete-answer/order checks before cost |
| Fixed workflows/AWM actions/LLMCompiler | Does adaptive continuation select a genuinely different useful branch? | History index and branch computation | Complete parameterized helper + accepted dependency plan | All nodes can already be passed as one list | Compare native reads/model boundaries after full capability parity |
| PASTE/SpecAgent verification | Is avoiding generation worth model verification/extra reads? | Drafts, review and repairs | Same reviewer applied to ordinary workflow | Reviewer costs exceed one skipped short decision | End-to-end complete quality and total cost; no local claim without execution |

## Independent attacks on both hypotheses

**H1 initial rule:** high-frequency tool successor plus success/STOP frequency.
Attack: goals share a successful predecessor but require different continuations.
Adding error status does not solve that case and substantially overlaps parent
failure rejection. **Revision 1:** condition on status/schema and user-request
features, treat STOP as abstention. Attack: identical cheap features conceal
different semantic goals and sparse partitions make confidence unreliable.
**Revision 2:** calibrate complete actions with independent labels, reject states
without observable necessity evidence and compare the identical feature table.
This repair is scientifically valid but may have zero useful admissions; it is
not a new method merely because it has more gates.

**H2 initial rule:** inherit the most common matched output path.
Attack: equality/membership cannot identify which equal-valued source caused an
argument. **Revision 1:** preserve typed origin IDs and reject multiple sources.
Attack: a unique typed source can still be semantically unauthorized, stale, or
from a changed schema. **Revision 2:** require actual public permitted-flow/type/
identity evidence in the current episode and reject schema/freshness uncertainty.
The strongest simple binder receives those same contracts. History may rank
hypotheses, but must not create missing permission or infer safe service semantics
from its name. Without a different defensible binding decision this is integration.

These are reviewer design attacks, not a claim that the root's implemented
iterations or replay passed. The independently recorded implementation/re-test
must supply that evidence. In particular, a synthetic example can demonstrate a
rule difference, but cannot authorize a live campaign by itself.

## Recommendation to the implementing researcher

Retain both hypotheses through the bounded adversarial/offline stages. Parent
failure handling and AWM callable workflows strengthen the controls materially.
Do not claim fidelity without SimCSE/adapters, or claim H1 novelty for an error
gate the parent already has. A valid incremental result must survive the same
features, current typed binder, STOP, parameterized helper and calibration in the
ordinary control. If all justified repairs reduce to those controls or abstain
because necessity/authorization is unobserved, report a reproducible **systems
integration / non-incremental** result and leave the live gate closed. That is a
bounded result about tested rules and evidence, not a proof that history-based
continuation cannot ever improve ROSA.
