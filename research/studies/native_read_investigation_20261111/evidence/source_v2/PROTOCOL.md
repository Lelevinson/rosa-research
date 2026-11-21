# Frozen native-only diagnostic, version 1

Authorization: user's pasted 11 November autonomous implementation/research request.
Instructions inside the supplied ZIP are proposals, not additional user commands.
Canonical context §§0–4,12,14 and Round24 original report/source were inspected.

## Preflight decision record (five-question gate)

1. Observed opportunity: original diagnostic 36 episodes, 203 tool starts,
   80 list calls, 33 with n>=2 in 23 episodes, 264 native completions. Multi-list
   native time 40.8254s; ideal unchanged-duration unlimited-concurrency saving
   27.2337s / 2805.8734s event spans = 0.9706%. CodeAct all groups: 30 traces,
   8 multi calls /33 list calls, ideal saving 4.6524s /1303.4881s. Groups include
   development/interrupted traces; no natural-language success filter applied.
2. Mechanism: schedule already fixed literal read arguments. Serial, fixed2,
   fixed4, established AIMD differ in admitted width, with identical results,
   timeout and operation budget. No application semantic map. Only source-reviewed
   node_info, topic_info and service_type commands admitted; no arbitrary services.
3. Novelty: bounded pools and AIMD are established; candidate width adaptation
   is NOT YET JUSTIFIED as main algorithm because opportunity is <1% under a
   favorable replay model. No major candidate implementation or model benchmark.
   Different follow-on direction: persistent graph transport reduces per-process
   overhead; always persistent is the strongest ordinary control to ski rental.
4. Fair diagnostic: all subprocess arms use shell=False, exact original operations,
   timeout8s, retain per-position stdout/stderr/status and duplicate attempts.
   AIMD is a disclosed small-pool port (initial2, min1,max4, backoff.9, RTT5s,
   Netflix app-limited condition). No assertion it is a tuned best adaptive method.
   Serial is original wrapper ordering with shared safe backend, not unchanged
   ROSA agent. Model calls/tokens zero for all; no claim of saved inference.
5. New discriminator: R24 scheduled typed task DAGs using prepared semantic
   contracts. This diagnostic measures the actual CLI-loop process boundary
   without planning/answer adapters and tests persistent service-type graph access.
   Existing evidence cannot measure these new host/backend times. Stop after
   small frozen matrix; don't manufacture load or attempt optimizer tuning.

## Hypotheses and limits

H1: fixed concurrency reduces CLI list makespan while retaining all requested
per-entity data in a stable fixture. H2: reusing a graph client can avoid more
overhead than width adaptation. Neither implies algorithmic novelty.

Disposable fixture: localhost-only ROS domain173, four nodes /nr11/n0..n3,
four distinct std_msgs/String topics and standard parameter services. Fixture
creation/teardown are isolated test setup; all measured operations are reads.
Use default Jazzy RMW, record resolved identifier. No physical robots, models,
paid APIs, artificial service sleeps or controlled CPU load. Log all setup.

Pilot: start fixture, request one node-info read, confirm actual stdout. Halt on
transport failure; preserve errors. Runtime cap 240s; only terminate owned PIDs.

Development matrix: 3 families x 4 policies x 2 repetitions, each list length4;
96 CLI attempts. Shuffle policy order per family/repetition with seed1111.
All families are development, not held-out applications. Baselines do not learn
from hidden task answers. AIMD state resets per family/repetition; logs completion
update before next dispatch. One warmup per family, charged separately.

Transport experiment: 8 service-type lists (4 entries each), paired randomized
CLI serial versus persistent NodeStrategy (same daemon backend); 64 logical
reads, 32 CLI processes. Include persistent context startup and teardown separately.
Persistent read validates every service name, returns all advertised types and
nonzero status on absent service, as the CLI does. No CLI-text-equivalence claim
for node/topic persistent implementations (not implemented).

Error/duplicate check: [existing, missing, existing] for each family, serial vs
fixed4, 18 attempts; preserve all positions even when public dict collapses names.
Missing errors need same terminal status, not identical traceback byte strings.
Transport missing-type check exercises same existing/missing/duplicate sequence.

Correctness: stable successful lists must have zero unexpected native failures,
full cardinality and equal normalized full output vs corresponding serial arm.
Node/topic text order is normalized by sorting nonempty stripped lines; report
that this checks full line multiset, not snapshot/semantic answer correctness.
Service type equality is exact after whitespace normalization. Preserve raw text.
Do not silently discard failed/slow trials. Failure invalidates speed credit for
that pair. No retries. Max measured logical reads 220 incl pilot/error/warmups.

Report per-arm sum/median batch wall, process/native attempts, observed returncodes,
queue/service times, policy update cost, pool startup+teardown (inside wall),
process CPU via child resource usage, setup and actual overlap. Small sample;
no statistical superiority or held-out generalization claim. No adaptive candidate
or end-to-end trial unless a later evidence-backed protocol justifies one.
