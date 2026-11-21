# ROSA LLM decision optimization — independent investigation

10 November 2026 · Source and saved-evidence investigation only

**Recommendation: NO-GO for an algorithm prototype.** Avoidable intermediate decisions exist, but the demonstrated cases are covered by ordinary batching, result-bound execution, argument repair, or bounded macros. A genuinely different candidate—guarded reuse of a previous LLM decision—lacks a justified generalization guard and a measured opportunity beyond those controls. Exact-context reuse is ordinary memoization; relaxing context equality introduces an unproved semantic decision. Neither supports the requested contribution today.

## Evidence and scope

Inspected current ROSA source at `94af17866cb82f3ea3f09422ef5cbb99b14cc89c`, the [November 10 audit](../bottleneck_gate_20261110/ROSA_Bottleneck_Evidence_Gate_2026-11-10.md) and its ledgers, selected original baseline JSONL events, prior plan/interpreter source, JTVR policy source, and Martin's macro and termination source at local remote-tracking ref `b13df0f03677754f42383dee95424cded862b117`. No remote refresh was performed. The audit's exhaustive counts are reused; selected decisive events were inspected directly rather than rerunning its analysis or historical scorers.

Evidence roots:

- **P:** `/home/levinsonchen/project/rosa-research-previous-20261108/research/`.
- **B:** P`_artifacts/rosa-baseline-diagnostic-review-20261107.zip`; baseline members below start `evidence/primary-v1/`.
- **C:** P`_artifacts/rosa-paper-pilot-review-20261108.zip`.
- **J:** `/home/levinsonchen/project/rosa-method-lab/`.
- **M:** the pinned Martin Git tree above. Inspect any cited file with `git show b13df0f03677754f42383dee95424cded862b117:<path>` from this repository.

The baseline has 36 episodes and 227 completed model requests. Conservative supported-correct judgments are A 9/12, B 10/12, C 8/12 plus one indeterminate inventory. Historical baseline/pilot runs used ChatOllama with `qwen3.5:9b`; they do not measure current ChatRosaLLM performance. The reconstructed Dependent Plans archive lacks all 64 primary episode traces. Martin's referenced M4 raw evaluation is absent from the local sibling evaluation checkout. Those two evaluations below retain their respective historical-report and author-report status.

## Which decisions could disappear?

| Observed situation and witness | Classification | What can safely replace the decision? |
|---|---|---|
| B `00-x1-B-r0`, lines 8–38: discovery returns four FQNs; node metadata is read, then four explicit `use_sim_time` reads are emitted together. | Once the requested parameter and discovered scope are committed, enumerating reads needs no new interpretation. This trace already groups four reads in one model response. | A discovery/read macro or result-bound continuation. No saving of one model call per node can be inferred. Metadata also supplies topic identities later, so deleting it wholesale would be unjustified. |
| B `13-d1-C-r0`, lines 32,38: scalar parameter reads for two already selected endpoints; line 44 repeats topic metadata acquired earlier. | Parameter enumeration is mechanical; the repeat is potentially unnecessary only if the original observation remains acceptable. | Activated independent batching and explicit observation reuse. Same returned text at two times does not prove safe freshness. |
| B `07-d2-B-r0`, lines 32,38: identical `use_sim_time` read twice. | Candidate redundant read, but this answer also omits/misclassifies GetTypeDescription. | Reuse can avoid native work under an appropriate observation contract; it does not repair completeness or automatically remove the model decision that proposed the repeat. |
| B `13-d1-C-r0`, line 10: bare `source`/`listener` after topic metadata supplied names and namespaces; correct FQNs appear at line 24. | Mechanical identity assembly/unique repair can avoid the failed detour. | Ordinary FQN construction and conservative repair from public metadata. A refusal alone still needs model recovery. |
| C `research/_artifacts/paper-pilot-continuation-20261108/05-d1-C/trace.jsonl`, lines 6–31: discovery followed by three parameter reads over actual returned FQNs. | Demonstrated elimination of intermediate enumeration decisions. | Already achieved by the bounded CodeAct interpreter; ordinary discovery/read helpers are the strong comparator. |
| B `00-x1-B-r0`, lines 46,48: delivered observations followed by final JSON synthesis. | Serialization is mechanical **after** correct source bindings and complete answer obligations exist. Those prerequisites are not certified by ordinary tool success. | A trusted answer/report contract. Martin already terminates directly after a ledger-accepted report. |
| B `06-t1-A-r0`, lines 16–28: sensor RGB substituted for configured background RGB; older Round28 h09 acquires `sum_rgb` but renders `sum_rg`. | Source selection and answer-scope interpretation remain unresolved reasoning. | No justified generic bypass. Faster continuation or serialization can preserve the wrong answer. |

The last distinction is decisive: an operation being easy to execute does not establish that choosing it is unnecessary. Discovering an endpoint does not establish that it answers the user's question. A compiler correctly listing obligations does not establish their eventual acquisition or rendering. The November 10 older-event audit documents both failure layers separately.

Current [ROSA](../../../src/rosa/rosa.py) uses `create_tool_calling_agent` and `AgentExecutor` (`_get_agent`, `_get_executor`); tool registration supplies callables. [ROS2 tools](../../../src/rosa/tools/ros2.py) include list-valued node/topic readers but largely return CLI text. There is no universal machine-checkable answer-completeness contract. The [system prompt](../../../src/rosa/prompts.py) still forbids batching; that contradiction must be removed in a fair batching baseline. Correcting it is baseline repair.

## Specific candidate: guarded reuse of one previous decision

**Hypothesis:** reuse a previously validated next action at a matching decision state, instead of asking the LLM to choose again. Execute the selected tool afresh; do not reuse its old physical observation. This changes the *source of the next decision*, rather than batching calls or executing a newly authored plan.

Proposed mechanism, not implemented:

1. At a completed model boundary, record the effective request, instructions/history, tool registry and implementation versions, model configuration, available observations with provenance/time scope, remaining budgets, and chosen action. Successful tool execution alone does not certify that action as correct; whole-task validation is a separate requirement.
2. Store a record `(guard, action, provenance)`. An action is a concrete tool invocation or a validated terminal result. Initially the guard requires equality of the complete effective decision input, execution permissions and relevant runtime constraints. Hash lookup must verify equality; generated call IDs must be freshly rebound without altering causal message links.
3. Before another model call, evaluate the guard. On a unique admissible match, emit the cached action through the normal executor and ordinary dispatch validation. Do not replay writes or irreversible operations. On any miss, ambiguity, invalidation or failure, use normal ROSA with the full accumulated evidence. Charge guard lookup and fallback costs.
4. The research extension would replace whole-input equality with a **certified sufficient subset of context**: omit an input only when changing it cannot change which next action is appropriate. This is where useful cross-context reuse—and the actual algorithmic burden—would reside.

### Adversarial result

The conservative version has a clear boundary but little demonstrated value. It can reproduce a previously selected action at an identical effective input; it cannot establish that action's correctness. For stochastic models it also replaces resampling with a fixed previous choice. Repeated tool arguments are not repeated decision inputs: accumulated history differs, and source observations, budgets and instructions may differ.

The generalized version fails its justification gate. A successful history shows what happened, not which inputs were irrelevant. Tool input schemas establish argument shape, not whether configured RGB or sensed RGB fulfills an obligation. A generated rationale or high next-tool frequency is not a sufficiency certificate. Confidence thresholds introduce a statistical error trade-off; fallback only protects detected uncertainty, not confident wrong reuse.

Adding an LLM to verify each proposed hit can consume the decision being saved. Preauthorizing the whole continuation instead returns to Dependent Plans/CodeAct. Supplying fixed predicates and output bindings returns to a macro. Handwritten question-to-source guards would violate the assignment. Thus the candidate is specified sufficiently to reject: **the safe restriction is ordinary memoization; the useful extension has no grounded guard or trace-demonstrated advantage.** This is a rejection of this candidate on current evidence, not a proof that learned decision reuse can never work.

## Generalization and correctness

The exact matcher is tool-agnostic because it stores ordinary registered call identities, schemas and arguments, rather than semantic equivalences. A registry change invalidates its key. Newly registered tools therefore work through normal ROSA immediately, but receive **zero justified cold-start decision savings**. Reuse becomes possible only after an appropriate prior decision exists. This is applicability across tools, not demonstrated generalization to unseen tools.

Transferring a guard across changed tool names, arguments, outputs or source identities requires knowing that the changed context preserves the decision. JSON string types and lexical similarity cannot establish that relation. No automatic semantic-equivalence discovery, inferred adapters or silent argument filling are proposed. Publicly declared contracts could support narrower proofs, but current ordinary registration does not provide the required decision/completeness semantics; adding them would be a different, contract-dependent claim.

Fresh tool execution preserves observation acquisition, but cannot correct a reused wrong source choice. Terminal reuse is stricter still: require complete, correctly bound, time-qualified evidence for every requested obligation. Neither local event silence nor an `ok` flag certifies that. Keep completeness, factual support, source correctness and formatting separate. Normal fallback is necessary, but does not itself prove no correctness loss.

## Comparison with existing approaches

| Approach | What the inspected evidence establishes | Consequence |
|---|---|---|
| Strong batching | List tools exist; several traces group calls. The baseline's extra `batch_reads` helper was unused in C, and contradictory sequential guidance remained. | Historical C is insufficient to establish a ceiling for an activated, corrected batching control. |
| Dependent Plans | P`multistep/read_plan.py` resolves explicit `$ref`/`$item`/`foreach` over actual results, with partial-evidence fallback. Historical report: zero dependency-reference adoption; 12 mutually supported pairs used 77 versus 63 model requests and 573,081 versus 450,795 input tokens. Original episode traces are missing. | Negative adoption/integration result, not proof dependent execution cannot work. A new execution notation is not the missing algorithm. |
| CodeAct | Restricted AST read interpreter activated real result-bound loops. One bracketed continuation d1 comparison against original A used 2 versus 4 model calls and 4 versus 7 CLI attempts; nine evaluation/continuation program attempts yielded one complete, three partial and five pre-read rejections. No bracketed strong B/C task pair. | Demonstrated feasibility; no established increment over batching/macros. |
| JTVR | J`prototypes/lab.py` uses explicit `Contract.observes/requires`, bounded prerequisite packages and a shared continuation runner. Saved `reports/experimental_findings.md` and `results/paired_analysis.json`: amortized completion and depth-two rollout tied on sequence/cost/success in all 19 continuation-enabled cases. | Broader search did not beat the strong simple policy. Synthetic inference boundaries are not measured LLM savings; declared field semantics cannot silently transfer to arbitrary tools. |
| Martin bounded macros | M`src/rosa_reliability/macro.py`: read → conditional authorized write → fresh verification → model classification. `bounded_macro.py` explicitly registers targets. `terminal.py:30–48` returns `AgentFinish` after checking bound-session ledger acceptance, without another model acknowledgment. | Covers predictable conditional execution **and** accepted-report termination. General final-turn elimination is not a new distinction. |
| Guarded decision reuse | Does not require a new plan from the current LLM, but useful reuse needs a sufficient-context guard not supplied by the evidence. | Compare with exact memoization and ordinary cached workflows, not only primitive ROSA. No incremental benefit demonstrated. |

Martin's M`docs/M5_MODULE_DELIVERY_README_2026-10-27.md` reports M4 Sol success 20/20 in both conditions, calls 68→38, mean time 16.42→9.73 s, native operations 38→40. Qwen success fell 15/20→14/20 despite calls 91→53 and mean time 133.49→85.18 s. Five accepted grounded Qwen reports answered a wrong/unresolved goal. These are **author-reported fixed-catalogue simulation results**, not an independently re-audited raw corpus or adapter-free transfer result. They show why reduced calls alone cannot justify adoption. His `terminal.py` also rejects multi-call responses, so a strongest-baseline study must separately allow safe read batching.

## Benefit bounds and conditional evaluation plan

The audit records 14 exact repeated commands among 264 baseline native executions (5.3%), all with equal stdout. This bounds removal of those particular native repeats only under an additional valid-reuse assumption; it does **not** bound or demonstrate saved model requests. Ten native identity failures occurred across seven proposal turns: perfect removal of those seven turns would be 7/227 ≈ 3.1% of baseline model requests, before replacement/guard costs. Ordinary identity repair competes for that same opportunity. Do not add these overlapping ceilings.

At B `07-d2-B-r0` line 38, the repeated-read proposal itself took 13.168 s and 7,328 input/150 output tokens. At `00-x1-B-r0` line 48, final synthesis took 28.391 s and 8,500 input/277 output tokens. These are actual recorded local costs of particular model requests, **not achievable savings estimates**: deleting them requires a justified replacement and preserving every obligation. The former episode is factually incomplete; Martin already supplies a terminal baseline for the latter class.

**Expected incremental saving for the proposed candidate: unknown; demonstrated saving: none.** No certified cross-context hits or unseen-tool transfer rate has been established. The appropriate accounting is `net saved cost = avoided model-request cost − lookup/certification/preparation cost − extra recovery cost`, measured separately for tokens and elapsed time. Native durations cannot substitute for avoided inference durations.

If new evidence later justifies reopening, freeze this narrow evaluation before implementation:

1. First identify a concrete supported trace boundary where an observable guard selects a correct continuation that corrected batching and an equally capable macro do not already remove. Specify how guard correctness is established without evaluator truth or semantic mappings. **Current evidence does not pass this gate.**
2. Compare corrected ROSA with activated batching/reuse, bounded macros plus trusted terminal handling, exact-context memoization, and the proposed generalized guard. Share native backends, schemas, evidence, concurrency, budgets, recovery, model settings and answer obligations. Charge training/preparation, cold starts, rejected hits and fallback.
3. Separate historical development histories from held-out requests and newly registered tool families. Keep cold unseen-tool fallback in the denominator; do not train on held-out suffixes or treat same-template repeats as transfer. Independently score full factual/source-supported completion and exact scope before comparing paired efficiency. Preserve all-attempt failures and invalid runs separately.
4. A proposed screening threshold is at least one actual model request saved on supported pairs in two tool families, lower total cost after overhead, and no lost correctness/completeness. This is a future design criterion, not an empirical estimate or a statistical guarantee. A tie with ordinary memoization/macros, or reliance on handcrafted source guards, rejects the algorithmic claim.

**Decision: do not prototype now.** The evidence supports ordinary execution packaging and baseline repairs as engineering opportunities. It does not support a meaningful new framework algorithm that eliminates additional LLM decisions while preserving correctness and completeness. No implementation, ROS/model execution, benchmark, dependency change or historical-result modification was performed; only this report was added.
