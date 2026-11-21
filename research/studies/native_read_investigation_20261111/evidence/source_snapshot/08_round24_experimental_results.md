# Round 24: native results and retention decision

2026-11-03, Asia/Taipei. **Retain ordinary concurrent dependency execution and
simple observed-cost/outcome estimation. Neither candidate demonstrates an
incremental algorithmic improvement over its strongest simple controls.**
Ordinary concurrency yields a narrow descriptive engineering latency saving on
new multi-publisher graphs. No full-agent, model-cost or statistical superiority
is established. This is a completed two-family investigation, not a paper draft.

See the [prospective method](round24_method_specification.md),
[primary-source/duplication review](round24_related_work.md),
[separate confirmation protocol](round24_confirmation_protocol.md),
[independent review](round24_independent_review.md) and
[reproduction/archive instructions](round24_reproduction.md).

## What was implemented and executed

A: `src/rosa/concurrent_acquisition.py::run_concurrent` dispatches a grounded DAG
with a bounded thread pool. Its coordinator alone accepts evidence and releases
successors. `critical_ranks` adapts established upward longest-path ranking,
using only public nominal durations. Controls are sequential, ordinary ready-list
with two workers, ordinary execute-all-ready with eight workers, and critical
priority with two workers. Every current frontier fits the eight-worker bound.
No barrier delays accepted successors; all arms share one retry per failed read.

B: `src/rosa/online_tool_selection.py::OnlineToolSelector` implements fixed
cost/gain, cumulative learned gain/cost, an eight-query recent-window estimate
and its optimistic exploration variant. Observed masks are joint accepted-field
sets, not independent success probabilities. Two optimistic nominal anchors are
explicit in every new estimator. Actual selected reads pay discovery/nonresponse
costs. Retained Round 7 outcome_local and Round 12 lean_online execute unchanged.
The fresh evidence ledger is separate from cross-query performance history.

`research/experiments/round24/run_study.py` connects these opt-in modules to
`tasks.py::DependencyTask` / `ProviderTask` and `native.py::NativeApplications`.
Only `task.ingest` establishes typed evidence. Actual upstream Jazzy Turtlesim,
demo_nodes_cpp parameter blackboards, AddTwoInts and 1 Hz talkers communicate
through DDS in localhost domain 224 and `/r24_` namespaces. Native versions,
binary hashes, original ROSA source and installed LangChain executor source
are preserved. There are no physical robots, artificial tool sleeps or default
ROSA changes. Provider full/partial/off schedules are disclosed evaluator-controlled
process interventions, not measured deployment fault rates. One separate A case
rejects one actual native client reply per episode; its hidden raw reply remains
in the evaluator journal and cannot satisfy the policy ledger.

ROSA's original synchronous invoke delegates to AgentExecutor's per-action
tool.run loop. Installed LangChain 0.3.30 also has an asynchronous gather path.
Therefore, this work does not establish that ROSA generally lacks concurrency.
All arms here receive the same explicit task contracts; none pays language
interpretation. Original/prompted model arms were not run because no new
end-to-end candidate survived the policy controls. Their equivalence to these
direct native adapter experiments was not established. Zero LLM calls/tokens
means no model inference occurred, not that model work was eliminated fairly.
No LangChain invocation/Phoenix trace exists or is needed for this native-only
execution; native request/response journals are the primary evidence.

## Preserved attempts and freezes

- Three feasibility attempts: initial read-only log path failure; sandbox DDS
  socket/discovery failure; then five successful actual native reads. All are
  saved. Pilot source identities were recorded immediately after execution,
  explicitly not a prospective source freeze.
- Development-v1: five A graphs × three repetitions × four arms = 60 episodes;
  three B streams × 16 queries × three reset repetitions × six arms = 864.
  Protocol SHA-256 `594ba331b38a20e2baf379ddf54be2901041b345e6c30187c8e279ef33b04726`.
- One confirmation source-freeze attempt failed because a relative case path
  was not normalized. Its follow-on run-frozen attempt found no protocol; neither
  launched ROS. Partial source copies and attempt metadata remain in
  `confirmation-freeze-failed-v1`. The focused path fix preceded successful freeze.
- Confirmation-v1: three new multi-topic DAGs × three reset repetitions × four
  unchanged arms = 36. Protocol SHA-256
  `4c1c5938262eaeb7eaba9a19ac8e91f0e7b02235e9803de0dd299b91f8e7d87b`.
  Only native.py and run_study.py differ from initial development: optional
  remapped upstream talkers, selective source freezing, monotonic freeze metadata
  and the path fix. Neither policy implementation changed. No tuning followed.

The initial single talker's phase masked most makespan differences. The separate
prospective confirmation requests two/three distinct periodic sources without
changing their native publication rate. Its new graphs reuse earlier primitive
types; they are designed held-out engineering checks, not independent deployments
or a selected positive adaptive algorithm. B failed the strong-control gate and
has no held-out performance claim. No arbitrary third mechanism was attempted.

## Family A: initial development and actual failure

All-attempt totals, including intentionally impossible missing-Pose cases:

| Arm | Supported /15 | Acquisition attempts / dispatches | Query seconds | Scheduler wall ms |
|---|---:|---:|---:|---:|
| Sequential |12|84|14.026702|29.404|
| Ordinary ready, two workers |12|86|13.786936|50.000|
| Execute all ready, up to eight |11|87|13.866265|77.639|
| Critical priority, two workers |12|84|14.304822|45.555|

Three missing-source cases per arm are deliberately unresolved. Accepted sibling
values remain, missing operations retry once, and descendants cannot run from
failed prerequisites. One additional ready_all independent episode loses both
parameter fields after actual service-reply deadlines, even after retries:
`development-v1/a-repeat-2/00-ready_all.json`. ready_two also encounters two
reply deadlines in repeat1 and succeeds on its common retry. All failures remain.
The evidence does not identify their cause or establish a priority reliability
advantage. Thus initial A is 47/48 feasible completions, plus 12 deliberately
impossible cases; do not describe it as perfect completion preservation.

On12 mutually complete critical/ready_two pairs, critical has one fewer-operation
pair and 11 ties; the count gap is the observed transport retries, not an isolated
causal scheduling gain. On11 critical/ready_all mutually complete pairs, operation
counts tie. Initial single-source phase-sensitive times provide no priority win.

## Family A: separately frozen engineering confirmation

All36 episodes complete with valid current evidence and no native failures:

| Arm, nine tasks | Native attempts / dispatches | Query seconds | Scheduler wall ms |
|---|---:|---:|---:|
| Sequential |54|11.889384|19.532|
| Ordinary ready, two workers |54|8.981407|32.663|
| Execute all ready |54|8.981324|65.260|
| Critical priority, two workers |54|9.076641|27.840|

Ordinary ready_all saves 2.908060 query seconds,24.46% of this nine-task sum,
without reducing calls. The effect concentrates in three-periodic fanout:
sequential sums 5.887718 s across three repeats (individual1.946–1.993 s), versus
2.983215 s ready_all (0.994–0.995 s). Two-source and two-source-chain cases are
approximately 0.994 s per arm: another retained null/regression condition.

Critical priority changes submission order on 6/9 comparisons with ordinary
ready_two but is 0.095235 s slower in aggregate. On three-periodic fanout it takes
1.037–1.040 s versus ready_two 0.993–0.994 s. It cannot claim the ordinary concurrency
gain; both strong parallel controls obtain at least the same effect. Three reset
repetitions on one host and producer-phase sensitivity do not establish latency
significance. Every native span is retained to show actual overlap. The sum of
overlapping native spans can exceed query elapsed and is not total latency.

## Family B: online learning versus simpler learning

All arms144/144 supported; all pairs are mutually complete. No history provides
current values. Three48-query strata are stable, alternating availability/coverage,
and correlated provider changes. The healthy Turtlesim alternative remains
available even when both blackboards are unavailable or partial.

| Arm | Native attempts / dispatches | Query seconds | Controller wall ms | Whole nine-block seconds |
|---|---:|---:|---:|---:|
| Fixed nominal greedy |216|18.545023|13.777|120.754792|
| Simple cumulative gain/cost |155|6.717698|11.608|109.036978|
| Recent window, no bonus |156|6.988815|11.629|112.106681|
| Candidate window UCB |160|7.217510|12.188|111.973104|
| Retained Round 7 outcome_local |156|7.012469|35.909|112.989015|
| Retained Round 12 lean_online |174|14.212412|36.528|121.229358|

The candidate beats fixed by 56 operations but loses to cumulative by 5, recent
mean by 4 and retained outcome_local by 4. Against cumulative it has 0 operation
wins,139 ties and 5 regressions. The three streams' calls are candidate 48/58/54
versus cumulative 48/53/54; stable behavior gives no advantage. Full blocks charge
startup, native profile changes, file writing and teardown. Each B arm has the
same69 launches and 60 setup discovery waits. Setup timing varies on this host;
candidate's111.973 s is still above cumulative 109.037 s. A small difference against
another arm's setup total cannot establish an acquisition algorithm advantage.

**Mechanism ablation:** independent same-state replay compares window_ucb and
window_mean at all 160 actual candidate predecision states and 156 actual mean
states. The bonus changes **zero choices** in either set. Four cross-arm query
trajectory differences follow different measured duration histories; the first
divergence already has capped optimistic gain under both modes. Do not attribute
those extra calls causally to exploration. Unit tests exhibit a separate state
where the formula can change a choice; no native outcome is credited for it.
This diagnostic is decision-only and supplies no counterfactual successes or
unexecuted latency. See `round24_b_same_state_audit.json` and its reproduction
script. Recent estimates and passive outcome learning remain retained prior
methods, not a new contribution from this round.

## Total cost, evidence, limitations and decision

Development has 1358 native acquisition attempts/dispatches,1115 inferable service
RPC requests,110 service-discovery failures before any RPC,133 fresh subscriptions
and zero unknown RPC stages. Confirmation adds 216 attempts/dispatches,108 RPCs
and 108 subscriptions. Campaign totals are 1574 attempts,1223 inferred RPCs,
241 subscriptions and 110 discovery failures; the separate pilot adds five reads.
Successful flags or dispatches never certify values. Twelve synthetic reply
rejections are distinct from actual native failures and remain charged.

Development block elapsed totals 746.526696 s, including573.931815 s of setup
discovery waits; confirmation totals 41.949467 s with 0.769043 s setup discovery.
Query elapsed totals 155.607408 s across both campaigns. Setup intervals and native
spans overlap other clocks and must not be added to fabricate a larger cost.
One-time source freezing, assistant development/research time, CPU energy,
transport bytes and deployment monitoring cost are not fully measured. The
performance result is native policy/query and block accounting, not the entire
scientific mission's cost or a full ROSA end-to-end speedup. Native wait parameters
and scheduler submission deadlines are bounded waits, not preemptive hard limits
on Python threads; observed full intervals are retained.

Independent standard-library audit reconstructs 960 episodes, 947 supported complete
reports and 13 truthful incomplete reports (12 impossible, one unexpected failure).
It checks all 6 B modes, accepted masks, requests, DAG priority/release timing,
typed provenance, outcomes, budgets, source identities and raw-block conservation.
The focused suite passes 87 tests: 17 new method/evidence tests, 23 independent
tampering tests and 47 retained controller/policy regressions. Independent checking
uses the same workspace and saved client journals, not separate laboratory
replication, wire capture or server attestation. Concurrent replies remain
individually timed non-atomic samples. Intent inference is supplied, provider
profiles are designed, horizons are short and no population reliability follows.

Retain A's small ordinary ready executor, common evidence-gated dependencies,
bounded retries, partial-result preservation and inspectable schedules. Keep
critical priority experimental. Retain B's performance-only observations and
strong simple/retained comparators; do not promote its bonus or call forgetting
new. The defensible incremental finding is a conditional **engineering** benefit
from ordinary concurrency plus negative algorithmic controls. There is no new
paper-worthy algorithm or demonstrated **end-to-end** improvement yet.

The single next step is an equal-intent native ROSA comparison of its existing
asynchronous tool path and this ordinary ready executor, charging actual model,
discovery and failure costs. Establish that execution seam before inventing
another priority or learning rule. Preserve the known transport failure during
that comparison. No commit, push, merge, branch switch, dependency change or
baseline edit is part of Round 24. Exact final preservation, source/test checks,
selection and archive verification are linked in the reproduction guide.

The first archive privacy scan stopped before ZIP creation on public upstream
package attribution emails. It found no credential signatures. The attribution
was checked, the allowlist explicitly revised and selection v2 issued. The
failed packager, selection and review metadata remain preserved; no experimental
evidence or native outcome was changed to pass packaging. Extracting the first
ZIP then exposed two omitted retained test modules; the independent native audit
already passed, but the full regression check did not. Selection v3 adds the
unchanged missing tests. The failed archive and its diagnostics are preserved,
and all checks must pass again on the corrected extraction.
