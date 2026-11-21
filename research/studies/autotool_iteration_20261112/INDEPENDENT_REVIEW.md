# Independent source review of the offline investigation

Reviewed 2026-11-12 by the primary-source reviewer. Scope: source inspection of
`prepare_inputs.py`, `replay.py`, `test_replay.py`, `PROTOCOL_FROZEN.md`, and the
preserved original logger implementations. **No new experiment or test execution
was performed by this reviewer.** Implementation was still changing during this
review; findings below describe the inspected functions and require explicit
closeout rather than an assumption that a patch was tested.

**Final source reinspection:** The implementing researcher corrected the concrete
start-time leakage, legacy receipt identity, changed-source rejection, recent-k
parent query, missing timeout/rejection flags and multi-change ablation defects.
The final source is acceptable for a restricted, fail-closed shadow diagnostic
with the residual limitations below. It is not an executable safety-certified
continuation controller. Earlier invalid outputs remain in `results/pre_audit_v1`.

## Judgment

The file-only shadow approach respects the no-inference/no-ROS boundary, preserves
grouped decisions and avoids treating behavioral agreement as necessity. Its
fail-closed execution result is appropriate. However, the initial implementation
had concrete predecision-boundary and origin-identity defects, and its initial
ablation labels did not match one-component removals. These must be corrected
before presenting replay statistics as protocol-conforming. Even after correction,
the result establishes a bounded diagnostic/integration result, not policy safety,
live savings, complete-answer preservation, or proof that AutoTool-family research
is impossible.

## Concrete findings communicated immediately

1. **Predecision state included events after `model_start`.** `parse_trace`
   originally constructed state inside `model_end` from the then-current receipts
   and errors. A delayed tool result between start/end would enter a prediction
   that claims an earlier cutoff. Freeze the observable state at `model_start`;
   quarantine or separately account for later events. Add a delayed-receipt test
   with a same-model-window receipt and an error. This is a protocol defect even
   if the sampled synchronous traces happen not to contain such an overlap.

2. **Baseline receipt identity was missing.** The original `ToolRecorder` in
   preserved `menu_retrieval_run_study.py::on_tool_start/on_tool_end` records name
   and input at start, and output/run_id at end. Reading `event.get('name')` only
   on ends produces `None` for baseline tools. Join the end to its actual start
   by `run_id`, preserving arguments and original IDs. November11 wrappers use
   names and their tool IDs. Missing/unmatched IDs must remain unknown; do not
   infer them from neighboring positions when parallel calls are possible.

3. **Same-shaped wrong sources could bind.** `available_origins` initially stored
   only receipt index, path and shape; `instantiate` never compared the source
   tool or call identity. Training on tool A's `{id: x}` then replacing that
   receipt with tool B's same-shaped output could silently propose the binding.
   Preserve source tool and relevant actual input identity, reject mismatches,
   and retain current-episode provenance IDs in the log. A source tool-name
   check is necessary but insufficient: the same tool called on a different
   entity can have the same shape/type too. None of these checks proves semantic
   authorization.

4. **Ablations changed multiple mechanisms.** Initial `no_outcome`,
   `no_provenance`, and `no_cost` used a one-step state, whereas candidate used
   two-step/one-step backoff. `no_provenance` still ran the same unique binder
   and also dropped calibration. This is not removal of provenance-risk
   calibration alone. Factor mode-independent backoff/binding/state construction
   so each ablation toggles precisely one named component; preserve safety
   invariants in every arm. If a component is unavailable and cannot influence
   decisions, report an uninformative ablation rather than fabricate an effect.

5. **Initial parent query was not recent-k.** `parent_constrained` originally used
   full episode history, whereas the pinned parent agent passes recent
   `inertia_k` records. The implementing researcher acknowledged a last-two
   correction. Document remaining departures: semantic model unavailable,
   environment adapters prohibited, grouped model boundaries instead of atomic
   calls, STOP added, current structured-only binder and no online reinforcement.
   The constrained frequency score corresponds to an explicit changed mixture;
   it is not the original alpha=.5 score with a free missing semantic term.

6. **Some actual errors were not represented.** Baseline `guarded_native` records
   timeout as `ros_error`, not `ros_end` with a nonzero return code. November11
   logs can include `guard_rejection` and `budget_rejection`. These initial parser
   branches were ignored, and a `tool_end` can return failure data without a
   Python exception. Track public failure events or mark status unknown. Do not
   promote absence of `tool_error` into a successful outcome label. This matters
   directly to H1 and parent fairness.

## Additional interpretation and completeness limits

- **Execution is deliberately unavailable.** `predict` returns `execute=False`
  unconditionally and records unobserved necessity/authorization/net benefit.
  Therefore zero admissions is a designed shadow-mode fact, not an empirically
  estimated safety rate. It cannot validate the admission policy or show that
  all real opportunities are absent. A model-boundary count is an optimistic
  maximum, not achievable savings; final answers still require model decisions.

- **Behavioral fitting is legitimate; semantic provenance is not learned.**
  `learn_template` uses training observed tool arguments to create equality-based
  origin hypotheses. That does not leak future validation actions if fitting is
  confined to training and calibration to development. But a unique matching
  value is still only an association. Preserve the terms “candidate origin” and
  “behavioral match”; no probability of action necessity can be calibrated from
  this label. `state['request']` exists but is not used by the state key, so this
  implementation does not test sophisticated request-conditioned admission.

- **The binder is deliberately narrower than public-information maximum.** It
  uses structured outputs from the most recent decision interval, excluding
  earlier current-episode inputs, request-origin values and unstructured outputs.
  These restrictions can be defensible, but missing bindings do not establish
  the impossibility of safe full-episode provenance. The parent itself supports
  broader history/input/context matching. Report restriction-caused abstentions.

- **Schema fingerprinting is conservative structural matching.** `shape` includes
  list length and receipt sequence order; ordinary size/arrival-order changes can
  fragment counts even when the interface is unchanged. This is not a proof of
  semantic schema change. Do not call an array cardinality change an endpoint
  contract violation. An alternative normalized schema would be a new exploratory
  protocol, not an after-the-fact correction chosen to improve scores.

- **Unknown model turns must interrupt evidence.** If an uncompleted model
  request is followed by another start, incrementing an incompleteness count
  alone does not establish an adjacent known transition. Do not bridge unknown
  decisions during parent path reconstruction. Likewise, a malformed/no-call
  response lacking a certified normal completion must not silently become STOP.
  The existing length/invalid-call checks are useful but not exhaustive.

- **Data split labels are honest but not confirmatory.** Task/application-level
  grouping avoids random call leakage and train/dev/test episodes are separate.
  The tasks and later trace families were previously inspected, mixed episodes
  share application components, and all historical prompt arms are not
  automatically strong deconflicted baselines. Neither an untouched retrospective
  split nor temporal transport constitutes new prospective held-out validation.

- **Calibration has no theorem here.** Wilson lower bounds describe the chosen
  behavioral count under simplifying assumptions; sequential and same-task
  episodes are dependent, states are selected, support is tiny, and no
  multiplicity correction establishes a global risk guarantee. Development can
  set thresholds, but the reported same-development performance is not independent
  validation of the calibration. Preserve the protocol's explicit caveat.

- **Control equivalence must be meaningful.** A candidate whose only added
  mechanism is ordinary variable-order backoff should be compared to a
  same-feature backoff control. If both call the same code with identical inputs,
  equality establishes implementation equivalence by construction, not empirical
  superiority or a theorem covering other algorithms. The initial parity test
  compared an expression to itself; replacement with separately constructed
  candidate/control objects is more useful, though one trivial fixture alone is
  weak evidence. Compare all paired replay proposals as well as gate reasons.

- **Synthetic revisions initially exercised separate toy functions.** `h1` and
  `h2` encode gate revisions, while `Predictor` is the actual fitted policy. These
  toy counterexamples support a conceptual repair narrative; they do not by
  themselves establish three implemented learner revisions or actual parent
  behavior on the same inputs. Add production-function tests for boundary,
  source identity, same-value ambiguity and changed-schema repairs, and explicitly
  distinguish conceptual versus implemented re-tests.

- **“Public needed=True” needs a contract, not a label.** The list/composite
  synthetic fixture initially directly supplies `needed=True` and
  `permitted_flow=True`; expected truth is also stipulated separately. These are
  synthetic authorization assumptions, not fields ordinarily available from ROSA
  tool receipts. A valid concrete fixture can provide an explicit accepted
  workflow request and documented source contract, but the runtime must not
  obtain evaluator necessity. Error/STOP/source identity booleans are similarly
  derived signals or assumptions whose availability must be stated.

- **Missing files should not be silently absent from inventory.**
  `prepare_inputs.py` checks the baseline count but not all other roots, and raw
  history discovery can find no files without emitting an explicit unavailable
  record for that round. Archive opening fails loudly, which is preferable to
  apparent success. Add per-root/per-round status or explain specific missing
  evidence in the inventory; a copied report is not primary raw evidence.

## Additional public-input counterexamples

These are source-review examples, not newly executed experiments.

**Delayed result:** `model_start S0`, then a slow previous tool returns a unique
`id`, then `model_end M0`. A source-compliant predictor frozen at S0 cannot use
that id, while the initial parser could. Next-action labels can look correct
because of an observation that was unavailable at the claimed cutoff.

**Same tool, different entity:** train a receipt from `inspect(node='/a')` with
output `{'id':'item1'}` and a successor consuming that id. In a new episode,
`inspect(node='/b')` returns the same type/shape. Tool-name and shape checks pass,
but source role/identity and the user's requested node can differ. Abstain unless
the public interface/request authorizes that flow. Equality does not resolve it.

**Reordered concurrent receipts:** one decision emits `[inspect('/a'),
inspect('/b')]`; completion order reverses. Receipt-index-based learned slots can
select the wrong node despite preserving the model-call group. Preserve request/
call identities; arrival order is not semantic order.

**Unknown bridge:** known call A, an uncompleted model request with an unrecorded
action, then known call B. Removing the unknown record creates a fictitious
adjacent A→B transition. Keep an UNKNOWN barrier or exclude that sequence segment.

## Required closeout evidence

Before final packaging, record which findings were fixed, which are retained
limitations, the final hashes, and the implementing researcher's actual targeted
test/replay evidence. This reviewer has not executed the study. The literature
review independently supports keeping the live gate closed without a real,
non-synthetic advantage over the same-information table/binder/helper. It does
not establish that a broader history policy could never supply such an advantage.

## Closeout after source reinspection

**F — statically verified changes:** `parse_trace` now deep-copies state at
`model_start`; matches legacy/current tool IDs to actual starts; preserves source
names/arguments and rejects name/argument changes during instantiation; records
timeout and explicit guard/budget failures. Parent matching uses the last two
groups. All candidate ablations now retain the same two-to-one backoff, with
`no_provenance` explicitly removing development complete-action/provenance-risk
calibration while retaining the hard binder. That narrower ablation name must
remain explicit in the report. The candidate and `conditional_backoff` have
identical capability by construction. Tests now instantiate separate policies,
exercise success/error conditioning, replace current discovered identities and
check authorization abstention; the original self-comparison was removed.

**R — implementing researcher's execution, not independently rerun:** 13 focused
tests passed; replay covers 58 traces and 269 continuation boundaries, with ten
raw proposal contrasts versus fixed-order conditional C and zero versus C with
ordinary backoff. The inspected summary file also reports ten and zero contrasts.
The summary explicitly labels replay diagnostic and not fresh held-out evidence.
Because there is no supported incremental live contrast, the closed live gate is
appropriate. No complete-answer preservation, saved calls/tokens, latency gain or
calibrated necessity was measured by this offline study.

**Residual source limitations:** Late receipts after the frozen start no longer
leak, but are discarded when the current model ends, rather than carried forward
with an explicit delayed-event disposition. Unknown/incomplete turns can still
be removed from parent path construction, producing a fictitious bridge in a
corpus containing such an intervening turn; the reported zero incomplete pairs
does not prove general parser correctness. Identity joins without a usable ID
or parseable argument can remain unknown; hardcoded `execute=False` prevents
those projected bindings from becoming real actions. The narrow binder stores
exact source arguments, conservatively rejecting harmless argument variations;
its failures are not an impossibility result for richer public provenance.

The h1/h2 version tests are expressly conceptual, with stipulated fixture
necessity/permission/currentness. New production-function tests substantiate the
implemented final safeguards, but do not turn every conceptual version into an
independent full AutoTool learner evaluation. A/B/composite and parent behavior
in the adversarial JSON is partly qualitative; it must not be presented as
executed parent/macro comparisons. Thus the mission's negative/integration
deliverable is defensible, while a claim of a complete faithful parent benchmark
or three empirically evaluated end-to-end algorithms would be unsupported.

Snapshot SHA-256 values at reinspection:

| File | SHA-256 |
|---|---|
| `prepare_inputs.py` | `43bd19748953df0194817381d7caa3414231114b782825cca38248e23c20fc39` |
| `replay.py` | `8b2e8f4044ea82c141dbf5e6a971af9d698ea65dace50c038b5b33dd758b1884` |
| `test_replay.py` | `65745d3245d7e51669f74a5606af8a19a44d7ed4f995f072bfbd318b61ae8812` |
| `PROTOCOL_FROZEN.md` | `723e5fd65938b6c3bbaa6f7ff8c353d11af04af1d147882a41877452dd8ec465` |

Later fixes, if any, need their own artifact hash and validation record; these
hashes document this review snapshot, not an instruction to revert subsequent
corrections.

## Final addendum: executable learner revisions and admission separation

The final static reinspection additionally covered `adversarial.py`,
`PROTOCOL_AMENDMENTS.md`, revised `replay.py`/`test_replay.py`, and
`RESEARCH_REPORT.md`. No test or replay was executed by this reviewer.

**F — the earlier conceptual-versus-production gap is narrowed materially.**
`adversarial.py` now fits actual `Predictor` objects on five explicitly synthetic
training episodes per fixture. Its initial variant uses the actual learned origin
templates with an intentionally unsafe first-association filler; the intermediate
variant uses outcome/shape-conditioned counts and the production unique binder;
the final variant uses the actual logged admission decision. Evaluation truth is
separate from predictor state. Eight fixtures cover names-only stopping, details,
errors, equal-valued sources, text, changed source/schema and a list helper.
The saved-output claim of four→one→zero false diagnostic admissions is consistent
with the branches inspected: source identity/schema ambiguity is repaired before
the remaining names-only continuation is blocked by the final abstention gate.
Useful cases are blocked too, as the report explicitly acknowledges. This is
executable development of rule revisions, not eight real ROSA opportunities.

The runner separately constructs the strongest ordinary backoff policy and asserts
equality of its full final prediction object on each fixture. This is a meaningful
check of same-capability implementation parity, albeit equivalence by construction
and not a general theorem. The parent/composite is still not fully executed, and
the report correctly states that limitation. The old conceptual h1/h2 tests remain
clearly distinguished from this newer fitted-learner layer.

**F — additional parser/admission repairs:** Parent training now retains UNKNOWN
sentinels and splits paths at them. Unmatched real receipts with no start line are
excluded from origin candidates. `admission` is calculated independently from the
shadow-mode `execute=False`, enabling distinct policy and execution counters.
Unrecorded/incomplete pending model requests do not themselves inject UNKNOWN
rows, so arbitrary interrupted traces still need a declared parser policy; this
does not invalidate the reported corpus with zero incomplete pairs. Late arrivals
are still discarded as noted above.

**Important admission limit:** For every proposed tool, the current program
unconditionally appends `needed_unlabeled` and
`readonly_permission_not_certified`; argument-bearing proposals get additional
unknown-flow/freshness reasons. The final implementation therefore has no positive
tool-admission path with the currently represented evidence. Its zero policy
admissions establish an explicit unavailable-evidence, fail-closed design outcome.
They do not establish a learned safe acceptance region, real risk control, or
nontrivial coverage. The report's all-reject and non-promotion interpretation is
consistent with that source fact.

**Review of report claims:** No blocking substantive misstatement was found in
`RESEARCH_REPORT.md` at the snapshot below. It preserves the constrained-parent
qualification, prior evidence/missing traces, synthetic nature, grouped replay,
ordinary-control equality, retrospective status, coverage loss, dependent-data
calibration caveat and closed live gate. The complete-action matches all being
STOP is treated correctly as no demonstrated tool+argument gain. This remains a
bounded integration/negative result with no demonstrated algorithmic contribution.

Final inspected snapshot (supersedes earlier hashes only for files changed):

| File | SHA-256 |
|---|---|
| `replay.py` | `53ad74e0458842b11832fafde6a1aa5477f6de4088c8ee1abfcb6b8be428a408` |
| `test_replay.py` | `65745d3245d7e51669f74a5606af8a19a44d7ed4f995f072bfbd318b61ae8812` |
| `adversarial.py` | `cb5c0988d6468f9360c9e461a8a582fb30aa509c260c4af77957d9a0210eee47` |
| `PROTOCOL_AMENDMENTS.md` | `cce5073aba2c9a403ad6a444da64f966af8ddb454347a306e957a3ea12a586c3` |
| `RESEARCH_REPORT.md` | `c44390200146d0f6e443b88d74410b8f95827acd37b9b82bb4d6d66c7627111d` |
