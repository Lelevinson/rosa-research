# Round 24: two bounded acquisition investigations

2026-11-03, Asia/Taipei. Prospective specification, written before native pilot.
All changes are opt-in. Original ROSA, dependencies, historical results and Git
branch remain intact. See [primary sources](round24_related_work.md).

## Questions and decisions

**A: bounded dependency scheduling.** Adapt upward critical-path ranking to a
grounded read DAG. Available information is public dependencies, nominal read
durations and accepted results; actual future durations are unavailable. Compare
sequential, ordinary work-conserving ready-list execution with two workers,
ordinary execute-all-ready execution (up to eight workers), and critical-path
priority with two workers. Every control releases successors immediately after
accepted results, without a batch barrier. All share retry and parser contracts.
Critical priority can differ when more than two independent operations compete
for workers. It may improve a restricted worker-cap schedule but cannot be
credited with the ordinary concurrency gain. The all-ready control can dominate
when contention is negligible. There is no claim that DAGs or priority lists are
novel, or that concurrent ROS replies form an atomic global snapshot.

**B: paid online provider re-exploration.** Use observed joint accepted-field
masks and total dispatch durations to rank alternative providers by residual
gain/cost. Candidate `window_ucb` uses a query-age window of eight, two optimistic
nominal anchors, and an optimistic exploration bonus capped at the advertised
residual coverage. Compare fixed nominal cost/gain, cumulative learned gain/cost,
the same window without exploration, retained Round 7 `outcome_local`, and
retained Round 12 `lean_online`. The candidate's distinct mechanism is choosing
an uncertain or aged alternative, paying the actual read; it is not the first
use of online costs, masks or forgetting in this repository. No independence,
stationarity, calibrated probabilities or transferred regret/cover guarantee is
assumed. All alternatives receive the same native rights and fresh ledgers.

For both hypotheses, completion and evidence validity precede costs. Support
requires different factual decisions plus a net saving against the strongest
matched control with no loss of feasible completion. A tie, worse cost, or gains
only against sequential/fixed arms refutes an incremental candidate claim on
this workload. Descriptive latency differences on one host are not statistical
significance or deployment prevalence.

## Environment, workload and bounded process

Use actual installed upstream Jazzy Turtlesim, demo_nodes_cpp parameter
blackboard, AddTwoInts server and talker, in private localhost domain 224 and
single-component `/r24_` namespaces. No physical robot or production endpoint.
Persistent rclpy clients are shared infrastructure, not a ROSA default change.
Every operation records monotonic start/end, exact request, raw response, failure,
receipt and provenance. Only task.ingest accepts typed parsed evidence. Setup,
graph discovery, native service requests, fresh subscriptions, local tool
dispatches and controller overhead are separate. No artificial sleeps are added
to a tool to give an arm an advantage. Upstream 1 Hz talker and Pose discovery
provide real heterogeneous durations.

First run a small native feasibility pilot before implementing the scheduler.
Preserve startup/transport failures. Development: A five structures, three reset
repetitions, four arms; B three streams, sixteen tasks per stream, three reset
repetitions, six arms. The streams comprise stable full coverage, provider
availability/coverage shifts and correlated changes. State changes are disclosed
controlled fixture interventions implemented through actual process lifecycles;
they do not estimate natural fault rates. No candidate sees the intervention
schedule or phase labels. No synthetic latency benefit is claimed.

A includes independent reads, dependent service arguments, fanout, native
nonresponse and a separately labelled one-time client-reply rejection. The
rejection is identical across arms and is solely a recovery diagnostic. Native
failures remain charged. Successful independent operations are not restarted.
Retries are common and bounded at one per failed operation; blocked descendants
remain unresolved. B allows each provider at most once per task and at most
three dispatches. Learning stores retain performance only, never state values.
Each stream and repetition starts cold; there is no free calibration. Cost
estimates are nominal hypotheses, not oracle prices. Setup changes and discovery
are separately paid and retained even when they amortize over multiple tasks.

No arbitrary third family. At most one justified development refinement per
family, with a separately frozen cohort and preserved earlier results. Both
families must complete meaningful native evaluation. If neither beats its
strongest simple control, stop with a negative decision. If either does, freeze
the best-supported method and new tasks before confirmation; no tuning after
confirmation. Held-out task construction, source hashes, budgets and criteria
must be saved before running. A confirmation may also be used to check a narrow
engineering result without claiming a new algorithm. Natural-language inference
is a separate boundary: supplied contracts are equally supplied to policy arms.
Original ROSA/strong prompting are required only where end-to-end equivalence
is established and a promising end-to-end candidate exists. Zero model calls
here establishes no model-efficiency gain. Phoenix is relevant only if an actual
LangChain/model invocation is run; native JSON journals are otherwise primary.

## Evidence and preservation

Native parameter type tags, request-name ordering and finite values are checked.
AddTwoInts depends on actually accepted operands. New volatile subscriptions
prove receipt after dispatch, not producer time. Data are quiescent except the
talker's increasing counter; no cross-source snapshot consistency is asserted.
Every report carries raw-event provenance. External evaluator expectations and
interventions are excluded from policy inputs.

Record all attempts, component costs, decision scores, overlapping native spans,
protocol/source hashes, package identities and exact commands. Compare efficiency
only on mutually complete tasks and report incomplete costs separately. Freeze
source snapshots before each campaign; fail on drift. Independent checking must
reconstruct saved native evidence rather than trust success flags. Preserve the
initial fingerprint of pre-existing files and baseline checkout. Only append a
Round 24 navigation paragraph to docs/START_HERE.md. Archive both implementations,
all protocols, trajectories, old source versions, tests, audit, limitations and
reproduction instructions with exact SHA-256 membership and extraction checks.
