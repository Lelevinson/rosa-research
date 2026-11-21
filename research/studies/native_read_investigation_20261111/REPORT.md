# ROSA native-read execution investigation

11 November 2026. **Recommendation: do not promote Adaptive Native-Read Execution
as the main algorithm. Retain ordinary bounded concurrency and persistent graph
transport as stronger engineering controls.** This investigation implemented and
ran native experiments, continued through a distinct transport mechanism and an
in-flight coalescing screen, and retained every failure. No new algorithmic
superiority or end-to-end answer-quality improvement was established.

## Scope and authority

The user's pasted autonomous research assignment is the request. The eight files
inside the supplied ZIP are inspected research inputs; their imperative next-step
text is not treated as additional user instructions. The source ZIP CRC and all
seven declared member hashes were checked. Its four arithmetic tests illustrate
synthetic policies; none is credited as native evidence here. Current authorization
permits bounded prototypes and read-only experiments, superseding older context
statements that no run had yet been authorized. All scientific constraints remain.

The active branch is `research/capability-discovery-20261110`, initial HEAD
`94af17866cb82f3ea3f09422ef5cbb99b14cc89c`. `AGENTS.md` and `research/` were
already untracked. No branch switch, commit, reset, clean, push or merge occurred.
Production ROSA source, dependencies and defaults were not changed. New work is
isolated in this directory; the canonical context receives an additive result
entry. Pre-existing files are checked against a SHA-256 preservation inventory.

Evidence terminology: **F** means directly inspected source or original events;
**R** means historical reported result; **L** means primary-source prior mechanism;
**H** means interpretation. New measured results below are F, with limited scope.

## 1. What source and Round 24 actually establish

F: `src/rosa/tools/ros2.py::ros2_node_info`, `ros2_topic_info`, and
`ros2_service_info` loop serially over list inputs, respectively invoking
`ros2 node info`, `ros2 topic info --verbose`, and `ros2 service type` per entity.
One wrapper is therefore several native CLI read attempts. The executor's sync
path and an asynchronous LangChain gather path are different boundaries: async
outer dispatch does not parallelize an internal Python loop. The default prompt's
one-tool/no-batching restriction is already known; a fair future optimized agent
must replace it. This experiment contains no agent prompt comparison.

F: Jazzy `NodeStrategy` reuses an available ROS CLI daemon. Process creation is
not evidence of fresh DDS discovery. Graph inspection reads local middleware/daemon
graph metadata; it does not invoke arbitrary robot services or parameter values.
CLI source and local ROSA files are preserved with provenance hashes.

F for inspected historical documents/code, R for their unrerun measurements:
Round24 used grounded typed task DAGs with sequential, ready-two, ready-all-eight
and critical-priority-two controls. Its confirmation reported sequential11.889384s,
ready-two8.981407s, ready-all8.981324s, priority9.076641s across nine tasks with
equal operation counts. Provider UCB lost to ordinary learned cost controls;
same-state replay changed zero choices. We inspected its original report,
specification and `concurrent_acquisition.py`; we did not re-audit all960 episodes.
The new question is the post-bound CLI process/lifetime boundary without those
task/field adapters, not rediscovering concurrency or claiming ROSA cannot do it.

L: AIMD, Gradient2, LLMCompiler and persistent asynchronous clients are existing
mechanisms. See [primary-source review](PRIOR_ART.md). Bound-list scheduling avoids
complex model-authored plans but this alone is an integration distinction.
[Netflix AIMD](https://github.com/Netflix/concurrency-limits/blob/main/concurrency-limits-core/src/main/java/com/netflix/concurrency/limits/limit/AIMDLimit.java)
and [LLMCompiler](https://proceedings.mlr.press/v235/kim24y.html) are explicit
hostile comparisons, not novelty endorsements.

## 2. Original incidence and bottleneck reconstruction

Both original historical archives passed CRC and all declared member hashes:
baseline332 members and CodeAct466, zero mismatches. Entire archives are included,
not just this report's derived index. Missing64 structured-dependency traces remain
missing and are not reconstructed. `inventory.py` reads actual tool_start and
native completion events. Replay-only traces and oracle snapshots are separated.

| Observed measure | Baseline primary | CodeAct all recorded groups |
|---|---:|---:|
| Episode trace files |36|30|
| Tool starts |203|142|
| List-wrapper starts |80|33|
| Multi-entity list calls |33|8|
| Episodes containing multi-list calls |23|6|
| Native CLI completions |264|137|
| Multi-list native duration sum, seconds |40.8254|8.9673|
| Ideal replay saving, seconds |27.2337|4.6524|
| Sum of first-to-last event spans, seconds |2805.8734|1303.4881|
| Model start events |227|137|
| Matched model event duration sum, seconds |2542.6100|1127.4648|
| Recorded input / output tokens |1,585,055 /27,132|925,516 /11,349|

Baseline list size histogram: n1:47, n2:21, n3:2, n4:6, n8:4. Representative original
events are retained in `evidence/inventory.json::representative_multi_events`.
CodeAct includes development/interrupted/continuation episodes and must not be
described as30 complete controlled evaluation tasks. Token counts are archived
usage reports, not newly measured inference or billed costs.

For each recorded serial list, the ideal calculation is sum(native durations)
minus max(native duration). This assumes unlimited parallelism, unchanged per-read
durations, no resource contention and zero overhead. It is a replay opportunity
calculation, **not a universal physical upper bound**. It gives0.9706% of baseline
event time and0.3569% of CodeAct event time. Source-level eligibility is frequent,
but its measured latency share is small. All native commands together sum254.9521s
in baseline (9.09% of event spans); model event spans account for90.62%. This
supports concentrating future research on a justified decision/inference mechanism,
but does not authorize dropping necessary model reasoning or replacing it with
handwritten semantic mappings.

No success filtering or retrospective correctness rescoring improved these
figures. Event spans and sums of component durations are not universally additive
under overlap. The sample is historical and prompt-confounded, not an optimized
batch-enabled future task distribution. These are the reasons to decline a major
q90-width candidate or expensive model benchmark, not proof of global impossibility.

## 3. Native width experiment, exact controls and results

[PROTOCOL.md](PROTOCOL.md) contains the preregistered five-question gate, resource
cap, seed1111, controls and continuation amendment. Read-only graph fixture uses
four disposable rclpy nodes, four distinct String topics and normal parameter
service advertisements, in localhost domain173, Jazzy, `rmw_fastrtps_cpp`, Python3.12.3.
It has no physical robot, simulated delay, hidden load signal, application-answer
map or model-generated plan. Fixture lifecycle is test setup, not a robot operation.

Three families × four policies × two repetitions =24 four-entry lists /96 CLI
attempts. Per-family policy order is seeded and shuffled. All arms use the same
safe argv backend, validated FQNs and8s process timeout, no retries. Serial retains
the original wrapper's operation order; it is not an unchanged ROSA-agent run.
Fixed widths are2 and4. AIMD ports Netflix's completed-request rule, initial2,
min1,max4, backoff0.9, RTT threshold5s and application-limited guard. It starts
fresh for each family/repetition, as frozen; this small finite-batch characterization
does not establish the performance of warmed, tuned limiters across many batches.
No custom adaptive candidate was justified or implemented.

| Family; eight reads per arm | Serial s | Fixed2 s | Fixed4 s | AIMD s |
|---|---:|---:|---:|---:|
| Node info |2.751856|1.543150|0.842403|1.489178|
| Topic info, full verbose metadata |2.819817|1.494410|0.895952|1.556366|
| Service type |2.840409|1.487355|0.839679|1.515195|
| Sum |8.412082|4.524915|2.578034|4.560739|

All96 reads succeeded. All18 nonserial/serial comparisons retained every position,
status and complete normalized output line multiset. Raw stdout/stderr, timestamps,
queue waits, admission widths and policy update time remain in the journals. Pool
creation/teardown and scheduling are inside batch wall time. Actual overlap and
worker ceilings passed the independent raw-journal audit. Four unit tests check
rejection of injection/mutators, whole-batch validation before dispatch, AIMD
decrease/growth conditions and line-multiset preservation.

H: fixed4 obtains about69.35% lower CLI batch wall than serial here; AIMD takes
about76.91% longer than fixed4. This is ordinary concurrency under stable metadata,
not an algorithmic advantage, significance claim, variable-load study or held-out
generalization. No inference calls/tokens occurred in these experiments. No claim
of answer-completeness preservation follows from metadata equality alone.

## 4. Distinct transport iteration

The initial hypothesis failed the meaningful-opportunity gate, so the next
implementation tested a different action: retain a graph client context instead
of creating CLI processes. A warm `NodeStrategy` uses the **same already-running
daemon** as CLI and calls the same public service-name/type API as `ros2 service
type`. This controls graph source rather than confusing a cached direct observer
with fresh remote calls. Only service-type parity is implemented; node/topic
persistent transports are not silently generalized from it.

Eight paired four-entry lists, randomized order:32 service reads per arm. CLI
serial total11.419331s; reused client total0.036736s. Opening the persistent context
took0.002784s, with shared daemon startup/discovery charged separately. All8 paired
outputs agree completely with zero unexpected failures. The reused context is
about311x faster in this small warm graph-lookup measurement (about289x including
context opening), **not** a311x ROSA-agent speedup. There are32 fewer CLI processes;
both arms still request32 graph reads. Nothing removes model calls or semantic work.

H: the simplest always-reused observer is the strongest incumbent here. Classic
ski-rental switching would defer a very cheap reusable context; no measured
cold-session distribution or new action signal justifies that extra policy. Full
cold middleware/client creation is not measured by the0.002784s figure. The shared
daemon, fixture initialization, waits and cleanup are accounted in whole-run logs.
This result is useful systems integration, not a novel online transport algorithm.

## 5. Errors, costs and reproducibility limits

Existing/missing/existing duplicate tests add18 CLI attempts across three families
and two widths, plus3 persistent service reads. All seven intentionally missing
entities produce nonzero terminal status; both successful duplicate positions are
retained. Public dict wrappers would collapse duplicate keys, so this executor
keeps per-position receipts internally and makes no new public duplicate contract.

Across measured runs including pilot/warmups: **186 logical native read attempts,
151 CLI processes,35 in-process graph reads, seven expected missing results,
zero unexpected read failures**. This counts top-level native CLI/API reads, not
all internal graph API calls, XML-RPC requests, DDS packets or service RPCs. Node
and topic commands invoke several graph APIs; those internal operations were not
individually instrumented. Do not present151 processes as151 DDS discoveries.
Setup CLI daemon commands and lifecycle actions are separate journal events.

native_v1 failed on socket permissions before fixture creation; it remains raw
evidence. native_v2 finished the width/error matrix but failed at transport import:
existing system `psutil` was invisible to the venv. native_v3 exposes existing
`/usr/lib/python3/dist-packages` through PYTHONPATH and runs **only** the unattempted
transport component; no policy changes or selective comparison reruns occurred.

Original whole-run times: native_v2 34.067971s; native_v3 19.677819s. Child CPU
user/system totals are respectively43.148647/7.246853s and12.152603/1.984588s.
These include owned fixture/CLI children and overlap, exclude detached daemon
CPU, and are not per-arm CPU estimates. Full setup and per-read timing are in
`evidence/measurements.json` and JSONL. AIMD update time is measured separately;
queueing and pool overhead remain inside wall. Packaging/auditing time is not
credited as saved execution cost.

Both fixture cleanup attempts needed SIGKILL (returncode-9), adding real shutdown
cost. Cause: shutdown called from the spinning thread's signal handler could wait
on that thread. The final fixture raises KeyboardInterrupt and shuts down after
leaving spin. A separately frozen cleanup-only smoke exited0 in0.128065s. Original
performance runs and forced-shutdown costs were retained. Daemon stop succeeded
in both runs. Exact frozen pre-fix code is archived for reproduction.

Driver/control/protocol hashes were recorded before execution. Installed source
snapshots are explicitly **postexecution**, not a complete pre-execution lazy-import
closure. We do not claim stronger runtime provenance. No dependency files changed.
No held-out application, workload reversal, graph-churn snapshot, server-overlap,
full-agent interpretation or full natural-language answer experiment occurred.
These boundaries make a novel adaptive-concurrency claim unjustified. Gradient2
was source-reviewed but not benchmarked; beating AIMD would not certify superiority
over all existing adaptive methods. No candidate won even that promotion gate.

## 6. Another execution alternative: in-flight coalescing

`alternatives.py` reconstructs native intervals from completion times and recorded
durations. Baseline has14 exact repeat commands /264 completions; CodeAct has24/137.
There are **zero overlapping identical requests** in either corpus. An executor
singleflight table therefore cannot save an observed request. Sequential repeats
are not automatically cache-safe: robot state, observations and permission contexts
may differ. This is a missing applicability prerequisite, not a fixable scheduler
bug. No cache/alias contract or new workload was invented to activate it.

## 7. Final research recommendation and presentation result

The [decision ledger](DECISION_LEDGER.md) distinguishes environmental defects,
algorithm limitations, already-solved mechanisms and absent prerequisites. It is
not an arbitrary sequence of renamed hypotheses. We have exhausted the
evidence-supported variants examined in this branch, not proved that no useful
algorithm exists anywhere in ROSA.

**Do not select adaptive native-read width or rent/buy transport as the main
algorithm from this evidence.** Retain this source-preserving prototype as ordinary
infrastructure and a stronger comparator. A new candidate needs real eligible
latency, repeated observable load variation, and a different action that beats
fixed concurrency, an existing adaptive controller and reused transport with
complete source-supported answers. The present sample does not supply these.

For2 December, the strongest result from this assignment is an executable systems
and negative-research study: **large local CLI-loop gains can correspond to less
than1% plausible historical agent-time opportunity; transport reuse can dominate
width-policy complexity.** Show one original multi-read trace, the full control
table and warm-client result, then explicitly separate these from novelty and
natural-language correctness. Earlier research remains available but is not promoted
by this investigation. [README.md](README.md) provides commands and archive checks.
