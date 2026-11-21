# Independent assessment: evidence acquisition, answer coverage and framework admission

2026-11-11, Asia/Taipei. This assessment inspected source, preserved November11
traces and primary literature. It ran no ROS, model inference or candidate code.
It does not anticipate the parent investigation's new GPT experiment results.

**Recommendation:** retain generic evidence receipts and model-declared obligations
as a narrowly scoped engineering design to challenge, but **do not implement a
full algorithm yet**. The current record justifies a small model/prompt diagnostic
with adequate context and a strong ordinary verification instruction. It does not
yet justify a claim that selective framework verification saves total cost while
preserving complete answers. The missing distinction is against a fixed final
validator with the same model-declared manifest and receipts, not merely against
an unenforced instruction to be careful.

## 1. Direct evidence: what failed in d1_recovery

Source root is `/home/levinsonchen/project/rosa-research`. The raw records are
`research/_artifacts/action_narration_20261111/primary-v1/<episode>/trace.jsonl`.
The exact request requires checking the named stale identity first, discovering
actual topic endpoints and reporting each endpoint's configured use_sim_time.

| Episode | Directly inspected trace evidence | What it establishes |
|---|---|---|
| 01-d1_recovery-A | Lines4–7 inspect the named retired node and receive its actual missing error. Lines11–17 retrieve topic metadata; lines20–27 execute two parameter-value reads. Line29 final answer uses those values. | The ordinary model can perform the requested acquisition and recovery in this environment. A read was observed, not inferred from its final Boolean. |
| 11-d1_recovery-B | Lines4–7 retrieve topic metadata. Lines10–15 attempt bare node names and fail;18–29 discover full names and retrieve node info. Line31 returns two false clock values. No parameter-value read exists. | Both clock claims lack evidence, and the explicit stale-note check was omitted. Node-info advertises parameter service names; it does not give clock values. |
| 06-d1_recovery-C | Same relevant acquisition pattern and omissions; last node-info receipt is line29 and final false values are line31. | Permitting explanation after public tool errors did not repair coverage in this recorded cell. |

The B/C final responses have normal `stop` status. Their final prompt/output
counts are3047+124 and3068+124, respectively, below4096. Thus the x1 context
truncation cannot explain these particular omissions. This does **not** identify
the counterfactual internal cause: one seed cannot distinguish a universal model
limitation from sensitivity to instruction wording, task order or trajectory.
The eight-tool schemas permit actual parameter reads, as A demonstrates. The
current agent also has an acceptance gap: a text-only model response is accepted
as final without a receipt-based coverage check. That is verified framework
behavior, not yet proof that a new general checker can safely close the gap.

The JSON value-match screen gives B/C credit because the guessed false values
happen to equal the fixture. The correct error category is missing acquisition
plus unsupported claims and an ignored procedural obligation. Intermediate FQN
mistakes are separate. No final wrong-source attribution is established here.

The earlier report's conditional A3/4,B2/4,C2/4 judgments and incomplete final
inventory closure retain their stated limits. No success rate or efficiency
benefit is upgraded by this assessment. Source-supported answer quality,
protocol closure, and numerical value agreement are different questions.

## 2. Three causal questions must remain separate

1. **Capacity/provider behavior:** was enough effective context available, and did
   the provider return a complete output? Active model capacity and stop reason
   must be recorded; architectural capacity or a successful short activation is
   insufficient. This explains the observed x1 limit, not the below-limit d1
   missing reads.
2. **Model/prompt behavior:** with identical readable receipts and adequate context,
   does terse action guidance change what the model acquires, remembers or reports?
   A/B is an intervention on the entire prompt and therefore can change tool
   trajectories as well as prose. A new model may show the failure is contingent;
   success on another model does not prove the framework guarantees completeness.
3. **Framework opportunity:** can a public, generic pre-final signal correctly
   distinguish missing support and choose a lower-cost repair/admission action
   than strong ordinary verification? Existing tool success and valid JSON do
   not establish source support. A useful opportunity needs a trustworthy signal,
   not only a known bad final answer after manual inspection.

Consequently, the old traces do not establish an unavoidable efficiency/coverage
trade-off. B/C saved work by omitting obligations in d1, while A succeeded. They
also do not establish that a framework algorithm is unnecessary: the unchecked
terminal boundary is real, but its general solution still has information costs.

## 3. Information boundary: what the framework actually knows

Current ROSA registry code supplies tool names, descriptions and input schemas;
`ROSATools` appends tools with callable implementations. It does not supply a
complete natural-language request decomposition, semantic output entailment,
trusted per-field provider contracts or an exhaustive answer schema for arbitrary
requests. Many outputs are CLI text or dictionaries containing CLI text. The
`ros2_param_get` output itself names the parameter, but node identity must also
be retained from the actual call arguments. See `src/rosa/tools/ros2.py` functions
`ros2_node_info`, `ros2_topic_info`, `ros2_param_get` and
`src/rosa/rosa.py::_get_agent`, `_get_executor`.

A generic runtime can independently certify that a call ID existed, its exact
arguments, tool identity/version, receipt bytes, status, time interval and selected
path/span. It cannot derive all requested semantic obligations or that one source
answers an obligation merely from those structural facts. In particular:

- Existence of a get_parameters service does not supply a parameter value.
- Matching the literal false in some receipt does not identify its subject.
- Receipt age or no observed error does not prove current physical-state validity.
- A valid node-info receipt does not show that every requested parameter was read.
- A model can omit an obligation from its declared checklist; all remaining links
  may then be structurally valid while the answer is incomplete.

Manually adding `d1_recovery → ros2_param_get(use_sim_time)` to the controller
would pre-solve the studied semantic decision and violate the required boundary.
An evaluator may use that domain knowledge to judge evidence after the run; the
runtime must not receive its task-to-source map. Public, tool-author-supplied
contracts would be a different, contract-dependent scope and must be disclosed.

## 4. Ordinary hostile controls that must receive full capability

**V0, static verification instruction:** augment the same A/B agent with a generic
instruction to account for every requested fact/procedure before finalizing,
ground each claim in actual tool observations, distinguish service availability
from acquired values, and acquire missing evidence or explicitly report it
unavailable. Do not add task names, node names, parameter names or a source map.
The model still selects tools and final status in its ordinary request. This is
the cheapest competing explanation; the old C only made error narration optional,
and was not a decisive evidence-verification control.

**V1, fixed draft review:** after an attempted final, provide the original request,
full transcript, draft and existing tools to one bounded verifier/reviser. It may
request missing authorized reads and repair the answer, with all calls/tokens
charged. A CRITIC-like loop is an ordinary control, not a privileged answer scorer.
It needs no manually prepared semantic map, but its own semantic mistakes remain.

**V2, fixed structural final validator:** if a candidate gets model-declared
obligations or claim-to-receipt links, give the same manifest and receipt metadata
to an ordinary fixed validator. Check the entire finite manifest at final, and
reject or request repair for invalid/missing bindings. Otherwise the candidate
would be credited with capabilities denied to its control. V2 must retain the
same ordinary fallback and request/repair budget.

A useful new method must beat whichever control is strongest under matched
quality/cost rights. Beating V0 alone may establish valuable enforcement engineering;
it does not isolate incremental scheduling or verification novelty over V2.

## 5. Candidate rules, action differences and counterexamples

These are designs, not implemented or validated policies.

### 5.1 Model-declared obligations plus evidence-bearing final admission

Let a model declare finite obligations O from the user request, with exact request
spans and stable IDs. The framework stores real execution receipts R. A final
proposal maps each declared obligation to either (a) a supported claim and links
to actual receipt paths/spans, (b) an explicit unavailable statement linked to
an attempted acquisition or reason, or (c) unresolved. Procedures and requested
absence checks are obligations too, not only final numeric properties.

**Concrete rule:** reject the proposed final if an obligation ID is absent,
duplicated or unresolved, a receipt ID/path/span does not exist, a cited operation
failed while the claim treats it as a successful value, or a declared argument/
subject binding conflicts with the actual receipt. Return only the offending IDs
and ordinary transcript to the model for one bounded repair. If the budget is
exhausted, return a transparent incomplete result. All semantic source selection
remains with the model; the validator must not invent missing calls.

**Different action:** ordinary B accepted its line31 final. If B were required to
declare both clock obligations and actual supporting receipts, its current
transcript has no clock-value receipt to cite. A structural gate can reject
missing/fabricated bindings before delivering the two false claims. This is a
conditional counterfactual, not a retrospective proof that a model would emit
that honest manifest or repair successfully.

**Counterexamples:** B can cite an irrelevant node-info span, declare an incorrect
relationship, bind a clock of another entity, or omit the clock/stale-note
obligation entirely. Receipt existence does not entail the claim. Allowing only
exact copied scalars also rejects legitimate unit conversion, aggregation and
negative conclusions unless valid transformation contracts are available. An
LLM/NLI verifier can help with these semantics, but adds model cost and error risk.

**Incremental difference after V2:** none established. V2 can make exactly the
same deterministic reject/repair decision on the same manifest and receipts.
The retained value is explicit enforcement/provenance engineering. A future
algorithm claim must identify an additional justified selection or stopping rule,
not merely move this predicate into a framework class.

### 5.2 Incremental coverage state and selective semantic verification

Store accepted, unresolved and invalidated obligation/receipt bindings. Recheck
only bindings touched by new results, changed arguments, an error, or an explicit
user refresh requirement. Invoke a semantic verifier only for unresolved or
ambiguous bindings; admit a final when all obligations have accepted support.

**Concrete action difference:** V1 always spends a post-draft verifier call;
the selective candidate skips it on a fully accepted receipt-bound answer and
requests review on a missing-link answer. In d1 B, unresolved clock IDs would
trigger repair. On a valid A-style answer, a sufficient trusted contract could
avoid repeating a semantic check. This could be an incremental cost opportunity
even though verification and caching have prior art.

**Counterexample and missing prerequisite:** a wrong model-declared semantic
binding may appear structurally complete and therefore bypass the verifier.
An omitted obligation is never selected for checking. A status-only error trigger
misses unsupported claims after successful tools, precisely the d1 pattern.
No current contract certifies the semantic acceptance state; calling it accepted
would assume the property being studied. Moreover, V2 already avoids model
verification for the same structurally complete cases. Incrementally checking a
small dictionary instead of checking the entire dictionary at final does not show
a meaningful LLM/native-cost advantage on these few-field tasks.

**Decision:** mechanism-level hypothesis retained, implementation blocked on a
validated acceptance/abstention signal and a real action difference from V2.
This is the closest potentially useful algorithmic branch, not an admitted one.

### 5.3 Execute missing declared reads and render a report without a final model call

The model could authorize a bounded set of exact read arguments and an output
template/receipt binding in its existing action turn. The framework executes the
reads and renders their actual outcomes, reducing a final synthesis turn.

**Different action:** instead of predicting false, the model would bind the clock
fields to the actual pending reads; the framework never fills a value before its
receipt exists. Partial/failed reads remain unavailable, not defaults.

**Counterexample/control:** wrong or omitted source bindings still produce an
incorrect/incomplete task. Dynamic discovery needs authorized binding/relation
contracts. A same-path parameterized report helper with identical capabilities
can execute and render the same plan. This returns directly to GLBE/composite/
terminal-acceptance history, whose negative comparisons must remain in scope.
Do not rename the helper as a novel coverage algorithm. Retain only if an ordinary
systems implementation itself is the explicitly desired deliverable.

### 5.4 Error/status-conditioned output modes

The previous D rule—compact after success, repair-capable after error—does not
solve unsupported values after successful node info. Static C already expresses
that conditional behavior. Reopening requires a new observable signal with a
different justified action, not another label or threshold. This scoped rejection
remains unchanged.

## 6. Closest literature and actual inspected level

These are parent mechanisms and hostile controls, not automatic novelty vetoes.
Their results do not establish ROSA completeness or transfer without evaluation.

| Primary source | Inspected mechanism and implication |
|---|---|
| [ReAct author project](https://react-lm.github.io/), prompting description and act-only counterexample | Interleaves reasoning and actions, with sparse reasoning in some tasks. It motivates testing whether useful task tracking was suppressed, rather than assuming every action word is dispensable. It does not require keeping all narration or certify these ROSA traces. |
| [CRITIC author paper](https://arxiv.org/html/2305.11738v4), Sections3.2–3.4, AppendixA | Uses external tool interaction to critique an initial output, then revise. The paper explicitly recognizes iteration latency and uses pre-specified tool choices in its evaluation. V1 is a strong ordinary version here; all its repair/verification costs must count. A trusted selective gate could differ by skipping checks, but that trust cannot be assumed from a receipt ID. |
| [Reflexion author paper](https://arxiv.org/html/2303.11366v4), Section3 evaluator/reflection and Section5 | Converts feedback to persistent verbal guidance for later trials. Its evaluator variants include exact matching, tailored heuristics and LLM evaluation; no general semantic success guarantee follows. Reusing an expert d1 failure explanation in the runtime would need fair accounting and could leak the diagnostic answer map. |
| [ALCE published paper](https://aclanthology.org/2023.emnlp-main.398.pdf), Section3.3, Section4.3 and AppendixG.2 | Separates answer correctness from citation support; evaluates support through entailment, not citation presence alone. This is directly relevant to guessed-but-correct clocks. Citation generation/post-editing already exists; links are useful provenance but not a complete framework algorithm. Its instruction comparison also cautions against assuming brevity has no quality effect. |

No paper was replicated. CRITIC and Reflexion method sections were inspected in
full author HTML, ReAct at the author project's mechanism/example level, and ALCE
in its published PDF's relevant methods/ablation sections. This is a focused
mechanism review, not an exhaustive novelty search or proof of global novelty.

## 7. Bounded discriminator and stopping rule

The parent investigation's authorized small A/B model comparison is valuable
because it can remove the known context-limit confound and test whether the
below-limit d1 omission reproduces with another accessible model/provider. Keep
task wording, tools, evidence rights and support scoring unchanged. A successful
GPT cell would establish conditional model/prompt robustness; a failed one would
strengthen recurrence, not automatically validate a proposed gate.

Before major candidate work, the smallest new policy discriminator is **ordinary
generic evidence-verification guidance versus a receipt-bound final contract** on
the same small development slice, only when separately frozen within authorized
scope. The latter is an interface/engineering test first. It must retain the
same model's semantic responsibility and must not receive an evaluator source map.
If the ordinary instruction already preserves supported coverage at lower total
cost, stop the enforcement-efficiency claim. If receipt enforcement helps, compare
against V2 with the exact same manifest before claiming an incremental algorithm.

Charge obligation declaration tokens/calls, receipt/path serialization, all
rejected finals, semantic reviews, authorized acquisition, repair attempts, final
rendering, context/prefill effects and latency. Report every requested field,
source-supported correctness, wrong citations/subjects, omitted procedures,
abstentions and incomplete runs before supported-pair efficiency. Fewer delivered
words on an incomplete answer is not a benefit.

**Stop major implementation now if** obligations are supplied by a handwritten
application catalogue, successful receipt links are treated as entailment, omitted
obligations are invisible, V2 chooses the same actions/cost, or the proposed signal
only detects syntax/errors while misses occur after successful tools. The current
record has not cleared these prerequisites. It supports an executable narrow
model/prompt diagnostic and concrete design alternatives; no main algorithm is
selected or claimed by this assessment.

Ringkasan: kegagalan d1 memang nyata dan tidak disebabkan batas4096 pada respons
itu. Framework bisa menyimpan bukti dan menolak tautan bukti yang tidak valid,
tetapi belum bisa memastikan semua kebutuhan semantik sudah tercakup. Pembanding
terkuat adalah prompt verifikasi biasa dan validator tetap dengan bukti yang sama.
Mekanisme selektif masih layak diteliti, tetapi belum layak diimplementasikan penuh
atau disebut kontribusi algoritmik tanpa pembeda dan pengukuran biaya tersebut.

## 8. Independent pre-primary harness review

The parent requested a read-only audit of `run_study.py`, `evaluate.py`,
`cases.json` and `PROTOCOL.md` before the newly authorized scored cells. No fatal
arm-parity or evaluator-to-runtime source-map leak was found. A/B task wording
and eight read schemas remain common; V is an explicit generic ordinary-control
instruction. The actual ROSA/ChatRosaLLM integration preserves the same execution
responsibilities. Provider-default differences are documented, so this design
cannot isolate model weights alone from provider/adapter differences.

Three concrete accounting/validation issues were sent to the parent. A follow-up
source read confirmed corrections before primary work: attempt counts distinguish
scheduled from attempted cells instead of reporting the full schedule after a
budget break; the oracle now requires the actual return1/missing-node message,
not arbitrary nonzero/timeout, before asserting retired-node absence; and
reasoning/cache aggregates carry explicit reported-detail flags. Missing detail
must remain unknown even if an internal sum uses zero as its empty accumulator.
These are source-inspection findings, not claims that the defective paths occurred.
The parent's final source freeze establishes the actual execution version.

One remaining screen limitation needs manual review: `procedure_satisfied` checks
that the stale read is the first native start and occurs once. It does not prove
that its result preceded dependent recovery/discovery. If a model emits a
multicall with overlapping initial stale-check and recovery operations, inspect
intervals and the exact request order rather than treating the screen as a
procedure proof. Likewise, successful argv presence is an acquisition screen;
inspect decoded returned content and final narrative before accepting support.
The evaluator already labels its output as requiring independent manual review.

This audit performed no model call, ROS operation or source edit outside this
assessment. It does not certify closeout before the actual final observations
and owned-process cleanup have been preserved.

## 9. Post-results update: narrow new evidence, unchanged algorithm gate

The independent10-cell review is now complete in INDEPENDENT_RESULTS_REVIEW.md.
All requested final factual fields in all10 new cells have actual acquired
support, including both d1 clock values. Thus the old missing-clock failure is
not reproduced here, and a claim that concise action turns necessarily prevent
evidence acquisition is contradicted by this sample. Both models also produce
complete x1 answers without length termination. This does not isolate whether
context, adapter/provider behavior, model capability or trajectory changes caused
the historical difference.

Full task compliance remains a separate axis:04/05 B and07 Qwen V begin endpoint
discovery before the prescribed initial stale-check outcome. They fail the same
strict procedural rule, despite fully supported final data. Exact strict support
is A4/4,B2/4,V1/2. Luna's ordinary static V cell addresses its B ordering failure
in this observation; Qwen's V does not. V is a concrete strong ordinary control,
not a general guarantee, and the sample supplies no basis for claiming a necessary
efficiency-versus-completeness trade-off or a new runtime algorithm.

The procedural failures suggest an inspectable distinction between an LLM's
proposed call-array order and real concurrent execution. A framework could enforce
an explicit model-declared dependency edge, but the ordinary same-information
dependency executor/composite can do so too. Automatically deriving the exact
edge from arbitrary natural-language procedural conditions still requires semantic
interpretation; hand-coding this task's edge would violate the study boundary.
Do not pivot into a named dependency scheduler without resolving that existing
strong-control and information boundary.

The prior candidate rules and counterexamples remain useful designs. None is
promoted automatically by a persistent ordering failure. The real next gate is a
concrete, charged action difference from ordinary verification prompting and a
fixed validator/dependency executor with identical declarations and evidence.
No full algorithm was implemented or newly justified by this assessment.

### Strong ordinary host control for the observed ordering failure

The first assistant tool_calls array at line4 of each04-openai-d1_recovery-B,
05-ollama-d1_recovery-B and07-ollama-d1_recovery-V lists the retired-node
node-info call first and chatter topic-info second. Thus a plain host executor
that dispatches each emitted batch **serially in proposal order** would complete
the stale inspection before starting the second proposed call in these exact
recorded batches. It needs no d1/source map, new model decision or semantic
dependency inference. This is stronger than asking the same model to restate an
ordering instruction, and is a mandatory ordinary structural countercontrol.

That statement is a conditional counterfactual about dispatch order only. No
serial repair was executed; it does not establish unchanged later observations,
final text, success probability, latency or net efficiency. It would sacrifice
overlap for other independent calls. A future comparison must retain the actual
concurrent baseline's capabilities, charge serial wall time and compare the
quality/cost trade-off, rather than weaken batching to manufacture novelty.
An ordinary dependency executor given valid model-declared edges can also retain
independent overlap while imposing a barrier on this edge; LLMCompiler/DAG
execution already provides the relevant scheduling parent mechanism. The unresolved
increment is obtaining trustworthy generic dependencies or choosing a beneficial
policy beyond those ordinary controls, not inventing another selective-barrier name.
