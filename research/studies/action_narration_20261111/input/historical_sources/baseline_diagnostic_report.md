# Focused ROSA baseline diagnostic — 2026-11-07

## Executive result

A real residual inefficiency is verified: successful tool results are sometimes
reacquired even though the requested information is already in the model context.
In condition C this occurs in **6/12 episodes**, across Turtlesim and the ROS demo
application: **23 redundant CLI reads, 12.384 seconds of observed CLI duration**.
Only **14 reads / 5.536 seconds in five supported-correct episodes** qualify for
correctness-preserving native-cost opportunity accounting. These are measured
historical operation durations, not measured net savings of a new policy.

**Do not start algorithm development yet.** The residual survives strong guidance
and *access* to generic batching, but C never invokes the added batch wrapper.
The direct CLI opportunity is small; larger inference savings lack a reliable,
application-independent stopping rule and a demonstrated margin over ordinary
reuse controls. The separate replay does not establish an improved prompt.

The 36/36 primary episodes finished. **Study closeout failed afterward** on an
incomplete node-discovery snapshot. That failure remains in raw evidence; one C
inventory-completeness score is conservatively indeterminate. No primary episode
was replaced, patched, or rerun. All evidence is persistent, with a separate
same-machine backup. No new algorithm, paid inference, dependency upgrade,
commit, branch switch, push, or merge was performed.

## Frozen experiment and actual environment

Read [protocol.json](protocol.json), frozen before model execution, for the exact
requests, guidance, budgets, validity rules and stopping criterion.

| Task | Legitimate information need |
|---|---|
| t1 | Drawing node, configured RGB, pose topic type and publisher count |
| t2 | Discover node, clear/reset service types, configured clock; no service invocation |
| t3 | Controller wiring: published/subscribed application topics and types |
| d1 | Chatter endpoints, roles/counts/type and each endpoint's clock configuration |
| d2 | Arithmetic server, all non-parameter services/types and clock configuration |
| x1 | Every scoped node's clock, pose/chatter types and publisher counts |

A is original synchronous ROSA's executor/full registry with common tracing,
observation guard, fresh history and bounded iteration/timeout settings. B adds
ordinary efficient-use guidance. C adds equivalent guidance plus an independent
known-argument read batch. The batch does not select tools, infer arguments,
resolve references, cache results, or use task-to-endpoint mappings. Original
ROSA core files are unchanged. Thus A is a bounded observation-study baseline,
not a claim of unrestricted original defaults. The common guard also standardizes
CLI timeout/error reporting; conclusions are limited to this setup.

All conditions use local `qwen3.5:9b`, temperature0, seed42, reasoning disabled,
1,600 maximum generated tokens, 90-second client timeout, ten executor iterations
and 240-second process budget. Two repetitions per task/condition were shuffled
with the frozen seed. Domain89 is localhost-only. Four stock processes implement
Turtlesim plus talker/listener/arithmetic demo nodes. Python3.12.3, ROS2 Jazzy,
`rosa-llm==0.1.0`, exact installed packages, dependency lock, fixture commands,
source hashes and model digest are archived. During-run server metadata reported
Ollama0.40.15 and effective context length65,536; this is a point observation,
not a per-episode hardware guarantee. Model digest begins `56671c2ab9385f9c`.

No historical controller, semantic adapter, answer mapping or previous task
contract entered the agent. Fixed fixture names in the evaluator are isolated
from model input. Raw events record complete model messages/schemas, replies,
provider token metadata, actual tool arguments/results, CLI starts/results,
errors and timing. A native operation here is a CLI subprocess attempt, not an
individual DDS packet or infrastructure-service request. Parameter CLI reads do
use ROS services; no clear/reset or other application service was invoked.

## Correctness, completeness and closeout failure

Independent native snapshots bracket six-episode blocks. Scorer source was written
after execution began but before reading episode answers, using the frozen task
criteria and evaluation-only observations. Counting/parser fixes and the final
closeout-validity amendment are separately preserved; no task or baseline changed.

| Condition | Episodes | Field-exact JSON facts | Conservatively supported | Incorrect | Indeterminate |
|---|---:|---:|---:|---:|---:|
| A | 12 | 9 | 9 | 3 | 0 |
| B | 12 | 10 | 10 | 2 | 0 |
| C | 12 | 9 | 8 | 3 | 1 |

All36 responses contain surrounding prose/fences: pure-JSON framing0/36. This
formatting result is not a semantic-success score. Full answers, including extra
prose, were reviewed; the JSON field scorer alone does not certify them.

Failures divide into distinct layers. t1-A-r0 and both t1-C repetitions substitute
sensor RGB `[255,255,255]` for requested configuration `[37,83,129]`; the tools
returned real observations from the wrong source. t1-A-r1 correctly reads the
parameters. d2-A/B in both repetitions and d2-C-r1 omit `get_type_description`;
some prose additionally misclassifies it as parameter management. Native acquisition
of that service type often succeeded, so these are interpretation/coverage failures,
not source unavailability. Bare/namespace-only node arguments cause recoverable
CLI failures in other episodes whose final requested facts are correct.

d2 has a pre-outcome-noted ambiguity: “application arithmetic service” may suggest
only the adder, while “all non-parameter services” literally includes type
introspection. Literal scores are retained. A narrower application-only reading
must be reported separately and cannot erase false service-taxonomy prose.
Installed ROS primary-source files corroborating the separate service categories
are bundled under `reference-source/`; native fixture snapshots establish actual
endpoints. Excluding d2 altogether is a sensitivity check, not a changed task.

At after36, `node list --no-daemon --spin-time 3` returned only the turtle node.
All four direct node-info/parameter snapshots and chatter endpoints still succeeded.
The parent saved the snapshot, raised `Independent oracle missing fixture nodes`,
and cleaned up its four processes; a subsequent final snapshot was not taken.
Why discovery omitted nodes is unresolved. The seven saved direct-field snapshots
agree, but the final inventory enumeration is incomplete. **33-x1-C-r1 is therefore
inventory-indeterminate**, excluded from supported matched-cost comparisons. It
is not reported as an observed incorrect inventory. The other fields have direct
independent support. No clean replacement closeout was generated.

## Costs: descriptive totals and matched correct pairs

| Condition | Issued model requests | Input / output tokens | Tool dispatches | CLI attempts / failures | Episode wall seconds |
|---|---:|---:|---:|---:|---:|
| A | 76 | 524,730 / 8,363 | 64 | 76 / 0 | 858.210 |
| B | 80 | 556,873 / 9,668 | 74 | 97 / 6 | 1,027.393 |
| C | 71 | 503,452 / 9,101 | 65 | 91 / 4 | 982.980 |

All227 issued primary model requests have saved responses; all264 CLI starts have
terminal events. No primary worker timeout or unfinished trace exists. Parent
closeout failure is separate. Tokens are provider-reported; wall time includes
worker startup and local-server variability. The host was not hardware-isolated.

The following comparisons include only same-task, same-repeat supported pairs;
different rows have different cohorts. Full metrics are in `comparison.json`.

| Pair | Supported pairs | Model requests | CLI attempts | Input tokens | Wall seconds |
|---|---:|---:|---:|---:|---:|
| A / B | 9 | 57 / 59 | 53 / 69 | 398,017 / 412,210 | 589.418 / 808.246 |
| A / C | 7 | 39 / 40 | 35 / 45 | 269,552 / 284,009 | 422.199 / 503.791 |
| B / C | 7 | 45 / 40 | 50 / 45 | 313,809 / 284,009 | 636.224 / 503.791 |

These totals do not identify avoidable operations or prove a batching effect.
C uses `batch_reads` **0/12 times**. B and C each emit multiple ordinary tool calls
in two decisions; A emits none, though original list-valued tools still group
node/topic reads. On x1, B/C select all four known clock reads in one decision,
while A selects them separately. Both repetitions demonstrate ordinary prompt-led
grouping with supported facts; the four native reads remain necessary. Other
trajectory errors erase any unqualified whole-study prompt advantage. Do not
attribute total time/token differences to a single mechanism.

## Trace-backed avoidability findings

Locations below are one-based `trace.jsonl` lines. The complete reviewed ledger
contains66 witnesses:50 redundant native reads, six unnecessary interface detours,
and ten unrequested debugging dispatches. Six parameter-name listings remain
unresolved opportunities without credited savings. No inference saving is inferred
merely by subtracting whole-episode call totals.

| Witness | Already available / subsequent operation | Interpretation and control |
|---|---|---|
| `01-t3-B-r0` | Node-info result14; repeated native read19,0.439s | Same requested interfaces already returned; no refresh/error. B repeats in r1 at21/19,0.398s. A and C avoid both; ordinary control already removes this pattern. |
| `04-t2-C-r0` | Node-info result14 contains both service types; native reads31/33,0.848s | Model acknowledges the types before requery. C-r1 repeats at35/31,33,0.795s. Safe omission preserves requested fields under observed static scope. |
| `16-d2-C-r0` | Node-info result14; eight type reads31–45,3.061s | Includes six excluded parameter services. All types already visible. Correct literal answer afterward. r1 repeats eight reads plus a clock read, but final answer is incomplete: no correctness-qualified saving for that episode. |
| `09-d1-B-r0`, `12-d1-A-r0`, `13-d1-C-r0` | Endpoint/count/type reply8; redundant topic reads33,33,47 | Respectively0.404,0.400,0.406s; repeats recur in r1. C naming-error recovery before47 is preserved separately. No refresh requested; source/count corroborated by static snapshots. |
| `09/12/24` d1 episodes | Endpoint names/namespaces already in reply8; six node-interface reads add2.326s total | Requested clocks can be read directly with known arguments. Other recovery-containing versions are not credited under this lower bound. |
| Debugging dispatches | A6, B1, C3 | Tasks do not request debugging, and these calls acquire no requested ROS facts. Dispatch is unnecessary; a whole inference's latency/tokens are not automatically removable. |

Redundant native reads by condition: A12 in3 episodes/4.709s; B15 in7/7.097s;
C23 in6/12.384s. Restricting to supported episodes leaves A2/0.843s,
B5/2.058s, C14/5.536s. Thus repeated reads persist under guidance and nominal
batch access, but effective wrapper use is untested. C's supported-read opportunity
is about0.85% of its supported episode wall time before any reuse/validation
overhead. Native duration is an opportunity bound, not achieved end-to-end saving.

Necessity was judged from prior *model-visible* replies, exact sources/arguments,
requested fields, error context, absence of writes/refresh requests, and independent
static snapshots. First reads, missing publisher counts, and recovery are not
renamed redundancy. Exact repeated discovery alone is insufficient: filtered tool
views may differ. A parameter listing might be subsumed by a direct named read,
but marginal costs/fallback equivalence were not established, so it remains unknown.

Application-independent recognition is plausible for exact successful read reuse
and standard ROS graph metadata such as a service's name/type. It still needs
source/field identity, visibility and validity. Generic tool-name transitions do
not establish semantics or answer completeness. Whole-answer early stopping is
harder: the d2 failures show that acquiring a field does not guarantee correct
classification or rendering. No generic stopping/validity rule was implemented.

## Separate controlled diagnostic replay

[replay-protocol.json](replay-protocol.json) froze two deliberately selected C
contexts after observing the redundancy: t2 before type requery, and d1 before
count/type refresh. Each was replayed twice with original context and twice with
an ordinary evidence-check instruction. Exact original messages/schemas are
preserved. Only genuine historical tool replies for matching arguments could be
appended; the lookup includes original-episode suffix replies and logs their
provenance. This is **model-only recorded-response replay**, not new native evidence.
Actual tool/CLI executions:0. New model requests:12 across8 replay attempts.

Unchanged contexts produce supported finals4/4. Added instruction produces2/4;
the two t2 paths request unmatched `set_debugging(false)` and stop unresolved.
Those paths are a replay coverage boundary, not proven live-task failures or wins.
In t2, both unchanged replays answer directly without service requery, confirming
that the saved evidence can support complete rendering. Their divergence from
the primary trace has no established cause. In d1 all four replays still request
the redundant topic reply. The added instruction does not eliminate it.

For the only mutually complete replay context, d1: both variants issue4 requests
across their two repetitions and replay2 tool replies. Original/additional-prompt
input tokens32,112/32,418; output716/778; inference73.214/78.708s.
This includes full rendering and instruction overhead. No net prompt saving is
established. Small selected contexts, repeated seed, recorded responses and local
runtime variability preclude general causal or deployment claims.

## Research decision and next bounded investigation

The strongest residual witness is **reacquisition of already visible source
metadata**, especially node-info → service-type lookup, rather than lack of a
batching API. It appears across two applications and three C tasks, but direct
CLI savings are small and larger safe inference savings remain unestablished.
No algorithmic contribution is justified by these data alone.

AutoTool's historical transition/inference bypass is relevant only if a recurring
next decision can be grounded and safely skipped beyond ordinary controls. That
advantage is not demonstrated here. DTDR addresses tool-menu selection; the full
47/48-tool registry has irrelevant debugging choices, but menu distraction was
not causally isolated. LLMCompiler/ReWOO dependency/planning separation is relevant
to known-argument grouping, which ordinary prompting already activates. These
are plausible mechanisms, not validated ROSA improvements; see the focused
[primary-source note](../multistep/baseline-diagnostic-mechanism-notes.md).

The strongest simple baseline a future method must beat combines efficient
prompting, concise requested output, actual independent batching/list arguments,
explicit source-preserving observation reuse, and ordinary recovery. Current C
provides batch access but does not demonstrate that fully exercised control.
B's guidance also lacks an explicit JSON-only brevity instruction; verbose final
rendering remains an ordinary prompting issue, not evidence of a novel mechanism.

Recommend one targeted follow-up **before selecting an algorithm**: freeze
unambiguous requested fields and static/dynamic validity obligations, then isolate
raw CLI text versus generic structured ROS outputs with ordinary exact reuse and
explicit known-argument batching. Measure whether residual selection turns remain
necessary and charge all parsing, validation, fallback and rendering overhead.
Use general ROS schemas rather than application task-to-endpoint tables. This
could distinguish presentation/binding defects from a true decision-policy gap.
**No such follow-up or algorithm phase was launched.**

## Review artifacts and verification

Raw primary traces, seven oracle snapshots, failures, source freeze, replay traces,
automatic scores, manual judgments, operation ledgers and comparisons are under
`research/_artifacts/baseline-diagnostic/`. Nothing depends on a sole `/tmp` copy.
The separate backup is `/home/levinsonchen/project/rosa-baseline-diagnostic-backup-20261107/`.
It is an independent file copy on the same machine, not off-machine protection.

The final complete ZIP is `research/_artifacts/rosa-baseline-diagnostic-review-20261107.zip`.
Its internal `MANIFEST.json` hashes every member except itself; an external ZIP
SHA-256 and raw-file manifest accompany it. `VERIFY.md` explains standard-library
verification. Checks cover CRC, membership/hashes,36 actual primary raw traces,
8 actual replay traces, context/result fields and oracle presence; a tampered
copy must be rejected. Preservation checks do not erase the closeout failure or
establish scientific generalization. Native reproduction needs the pinned local
model and ROS environment; model weights, credentials and installed environments
are intentionally not bundled.
