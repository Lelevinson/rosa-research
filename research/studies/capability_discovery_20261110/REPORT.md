# ROSA automatic tool capability discovery: prototype and findings

2026-11-10 · experiment branch `research/capability-discovery-20261110` · base
`94af17866cb82f3ea3f09422ef5cbb99b14cc89c`

## Decision

**Do not integrate this mechanism as authority to substitute tools in the
access-path optimizer.** Existing ROSA metadata plus finite runtime comparisons
can discover plausible partial overlaps and reject many bad relationships. They
cannot establish adapter-free semantic equivalence. The prototype demonstrates
this limitation: among ten extension tools, seven pairs passed empirical
validation, but five were semantically unrelated. An additional input falsified
three of those five; two remained indistinguishable from values alone.

The working implementation is suitable only as an opt-in diagnostic observer.
It never authorizes replacements, never skips a requested call, and preserves
ordinary tool calling. This is a negative prerequisite result, not an efficiency
improvement or a novel optimizer. No vertex cover, cut, or cost optimizer was
implemented. [Implementation](discovery.py), [actual results](results_corrected/results.json).

## Actual framework inspection

ROSA's `ROSATools` scans calculation, log, system and selected ROS-version modules
for objects exposing `name` and `func`. `add_tools()` and `add_packages()` append
extensions through that same path. There is no capability ontology, duplicate
check, semantic-equivalence contract or reliable read-only declaration. Blacklist
configuration can wrap callables. `get_tools()` exposes the current list.
[Registry source](../../../src/rosa/tools/__init__.py).

Ordinary LangChain tools expose names, docstring descriptions, inferred input
schemas, required arguments/defaults, callable annotations, metadata and tags.
The installed ordinary `StructuredTool` inherits an `Any` output schema: return
annotations are not an enforced output-field contract. The actual inspected ROS 2
registry had **47 tools, zero informative output schemas**. The observer made
177 metadata-only proposals among 1,081 pairs, validating none. Same input schemas
occur on unrelated tools, including node/topic/service lists and several arithmetic
operations. [Full source-grounded inspection](ARCHITECTURE.md),
[recorded registry inventory](results_corrected/results.json).

ROS output dictionaries often contain CLI strings, dynamically named keys or
mixed error results. Topic echo normally returns only a success flag unless
`return_echoes=True`; printed payload is not returned evidence. Some list helper
failures are embedded in lists, without a consistent error envelope. Therefore
JSON parsing or transport success alone cannot establish a meaningful observation.
[ROS 2 implementations](../../../src/rosa/tools/ros2.py).

ROSA binds its registered tool list into the model agent and `AgentExecutor`.
Streaming already exposes tool-start/tool-end events. These could feed a passive
monitor, but do not provide a common-state snapshot or semantic validator.
Existing asynchronous dispatch can already execute multiple actions concurrently.
The registry also contains mutators and arbitrary service calls; a plausible
description cannot authorize safe probing. This study imported the registry but
dispatched **zero native ROS operations**. [ROSA dispatch](../../../src/rosa/rosa.py),
[installed dispatch details](ARCHITECTURE.md#dispatch-and-safety-boundary).

## Chosen algorithm

The implementation uses existing schemas and passive observations, with lexical
metadata proposals. An optional LLM was considered and omitted: it could propose
aliases or argument correspondences, but would add inference/call cost without
resolving the tested validation failure. This study makes no claim about a tested
LLM-assisted alternative.

1. **Inventory and refresh.** Read registered names, descriptions, input/output
   JSON schemas and callable source/identity/defaults. Reject duplicate names.
   Explicit `refresh()` admits new tools and removes evidence for removed or
   visibly changed registrations. This does not rebind an already-running ROSA
   model or silently monitor registry mutation.
2. **Propose overlaps.** Propose a pair if it shares declared or observed field
   paths, or its name/description token Jaccard score is at least 0.2. Proposals
   are hypotheses only. Description changes cannot validate a relationship.
3. **Collect authorized observations.** The engine performs no exploratory
   dispatch. A collector supplies an already-authorized read-only invocation's
   tool name, explicit arguments, parsed result, success flag and common snapshot
   ID. The synthetic/pure-function harness can assert frozen state; current ROSA
   events alone cannot supply this assertion for a changing robot.
4. **Admit restricted data.** Validate arguments against the existing input model;
   reject unknown arguments and non-finite/non-JSON values. Reject error envelopes,
   unsuccessful calls, empty information and acknowledgements. Extract exact
   dictionary paths and structured numeric/array values; preserve nested paths.
   Exclude all string leaves and arrays containing strings because no generic
   parser can identify opaque CLI text reliably. This deliberately excludes valid
   string identifiers too. Scalar numeric results use the empty root path.
5. **Align without adapters.** Compare only identical explicit argument objects
   under a common collector-declared snapshot and structurally identical input
   schemas, ignoring schema documentation but preserving names/defaults/constraints.
   No argument renaming, entity mapping, field synonyms, unit conversion, numeric
   coercion or inferred default filling occurs in the engine.
6. **Validate empirical field overlap.** For each shared path, require at least
   three distinct argument contexts, at least two distinct values, and no observed
   mismatch or missing field in matched observations. Repeated snapshots of one
   input do not increase context diversity. Compare exact values and types,
   separating integers, floats and booleans. A counterexample marks that field
   contradicted and revokes its support. An invalid observation conservatively
   blocks support involving that tool for this observer session; there is no
   automatic recovery/expiry policy in the prototype.
7. **Keep the scope explicit.** Output per-field witnesses, mismatches and states:
   candidate/uncertain, empirically supported, or contradicted. A pair with one
   supported field has a partial overlap, even if another field differs. It is
   never whole-tool equivalence, output containment or a transitive relation.
   `semantic_equivalence` remains `unestablished`; `replacement_allowed` is false.
8. **Fallback.** The explicit ordinary-call seam forwards the original name and
   arguments to the caller's dispatcher. It does not select another tool or bypass
   that dispatcher's safety policy. All four study fallback calls executed their
   original tools, and a behavioral test verifies exact forwarding.

Thus the mechanism distinguishes a proposal, bounded validated *observational
agreement*, and the stronger semantic validation required for safe replacement.
It establishes no relationships at that strongest level. The test oracle's
semantic labels are used only by the evaluator and never enter discovery.
[Frozen protocol](PROTOCOL.md), [engine](discovery.py), [tests](test_discovery.py).

## Experiments and actual outcomes

The protocol preceded implementation. The first engine freeze preceded creation
of ten additional synthetic extension tools. Development and extension registries
each contain ten tools; all 45 unordered pairs in each registry are scored, and
an actual refresh into a combined 20-tool registry scores all 190 pairs. Each
initial tool receives inputs 0, 1 and 4. The extension later receives input 9,
which triggers the delayed-drift counterexample.

Both sets include aggregate/projection tools, nested fields, unrelated tools,
ambiguous descriptions, renamed fields/arguments and different representations.
Development also includes constant outputs and integer/float variation. Extension
adds different units, opaque text, a correlated foreign source and delayed drift.
The engine has no fixture-specific names, dispatch rules or semantic tables.
[Development fixtures](fixtures_development.py), [extension fixtures](fixtures_extension.py),
[evaluation harness](run_study.py).

The ground truth measures **broad underlying information overlap**, including
renamed fields/arguments, numeric representations, unit conversion and opaque
renderings. This intentionally counts useful but unsupported relationships as
false negatives. It is broader than the engine's exact-path eligibility rule;
recall must be read with that restriction. There are 12 broad positive development
pairs and 16 extension pairs. This scoring clarification was implemented before
the initial run and disclosed in [the change log](CHANGELOG.md).

| Empirical support evaluation | TP | FP | TN | FN | Precision | Broad recall | Accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development, 45 pairs | 2 | 0 | 33 | 10 | 100% | 16.7% | 77.8% |
| Extension, first 3 inputs, 45 pairs | 2 | 5 | 24 | 14 | 28.6% | 12.5% | 57.8% |
| Extension, after counterexample | 2 | 2 | 27 | 14 | 50% | 12.5% | 64.4% |
| Newly registered extension in combined registry, 190 pairs | 4 | 5 | 157 | 24 | 44.4% | 14.3% | 84.7% |

The two correct extension supports are inventory→processor load and
inventory→nested queue depth. No engine changes or application mappings were
needed to admit them. But agreement among processor, inventory, correlated foreign
source and delayed-drift source initially produced five false supports. Input 9
contradicted all three relationships involving delayed drift. Foreign-source
outputs stayed numerically equal to processor/inventory, leaving two false
supports. These cases test source identity, not merely coincident constants.
The empirical false-positive rate fell from **5/29 = 17.2%** to **2/29 = 6.9%**;
that remains unacceptable for substitution.

As weak proposal baselines, metadata alone proposed 23 development pairs
(12 true, 11 false) and 26 extension pairs (14 true, 12 false). With observed
paths, proposals became 29 in each registry: development 12 true/17 false,
extension 15 true/14 false. More output structure increases coverage but also
proposes more unrelated same-shape pairs. **Asserted semantic equivalences were
zero and replacement abstention was 100% throughout.** That zero is a deliberate
safety boundary, not demonstrated semantic classification accuracy.

A real ROSA pure-calculation check invoked sum, product, mean/stdev, median and
variance on four lists: 20 normal `.invoke()` calls, ten negative pairs. The
first list makes sum/product and mean/median coincide, while subsequent lists
separate them. All ten pairs were proposed; none passed empirical validation.
This validates a small real dispatch path and useful negatives; it demonstrates
no native ROS overlap discovery or optimizer speedup.

Eleven behavioral tests pass. They cover threshold/diversity gates, disjoint
snapshots, incompatible arguments, missing fields, type collisions, errors,
non-JSON values, snapshot conflicts, registration invalidation/removal/duplicates,
input mutation, declared-schema-only uncertainty, wrapped opaque text, and
ordinary fallback. Replay independently reconstructs confusion counts and all
saved pair decisions, including the real calculation check, from 120 raw
validation observations without invoking tools. [Test output](unit_tests_final.txt),
[replay output](audit_final.txt), [raw observations](results_corrected/observations.jsonl).

### Preserved unsuccessful work

The original nine tests passed, but post-run review found two defects: schema
cleanup could erase argument names `description`/`title`, and text filtering
missed nested/array CLI payloads. Two new regression tests failed on that code.
The original sources, freeze, results and failure log are retained. The corrected
engine preserves property names/data literals and conservatively excludes text.
Rerunning identical fixtures/labels produces the same confusion counts above.
The corrected run is a regression run of already-seen fixtures, **not a new
held-out evaluation**. Both initial and corrected results retain the false
supports. [History and preserved failures](CHANGELOG.md),
[initial sources](initial_source/), [initial results](results/results.json),
[regression failures](regression_failures.txt).

## Overhead and call accounting

Measured locally with Python 3.12.3, LangChain 0.3.30, langchain-core 0.3.86 and
Pydantic 2.14.1. The detailed environment is recorded with the results. On 100
fixture observations, ingestion median was **0.0278 ms**, p95 **0.0373 ms**, including
rejected opaque outputs. Scale measurements use nine repetitions, three replayed
observations per tool, and dense shared-field proposals. Values are median/p95
milliseconds; with nine samples p95 is the largest sample, not a robust tail estimate.

| Tools / pairs | Registry refresh | Ingest all observations | Discover all pairs |
|---|---:|---:|---:|
| 10 / 45 | 2.58 / 4.86 | 0.48 / 0.55 | 1.52 / 1.62 |
| 50 / 1,225 | 13.33 / 22.08 | 2.21 / 2.36 | 50.17 / 122.06 |
| 100 / 4,950 | 26.14 / 38.02 | 4.42 / 4.63 | 308.32 / 340.46 |

The simple implementation enumerates O(T²) pairs and scans the observation store
for each pair; worst-case work is O(T²·M) plus field/value comparisons, with M
stored observations. Memory and retained counterexamples are unbounded within
this short experiment. Indexing, expiry and sparse candidate evaluation were
not implemented because semantic validity failed first.

Per full study run there were **100 fixture validation calls, 20 real pure
calculation calls and 4 explicit fallback calls**: 124 actual tool invocations.
The two recorded full runs therefore used 248, excluding unit-test invocations.
The engine initiated zero probes; scale measurements and audit are passive
replay. Extra LLM calls, paid API calls and native ROS dispatches were all zero.
In a live passive observer, existing observations would already be paid; actively
obtaining enough matched observations would add real validation cost, as this
harness does. No savings or end-to-end ROSA latency benefit were measured.

## Generalization and integration limits

The ten extension tools were authored after the initial engine freeze, and
registering them required no semantic mapping changes. This establishes mechanical
extension handling within the tested representation. Both fixture sets and the
adversarial controls were designed by the same researcher; they are not an
independent, randomized or representative benchmark. Pairs share tools and are
not independent samples. The tables are exact fixture outcomes, not population
accuracy estimates.

Schema/path matching misses synonymous fields, renamed parameters, typed output
references/unions, useful constant fields and textual data. It assumes existing
metadata is trusted to inspect; it is not a sandbox against malicious tool
implementations. Fingerprints are process-local and cover visible registration
changes, not mutable closure state, arbitrary implementation mutation or external
world changes. Cache evidence is neither persisted nor restored across processes.
Declared output schemas are used for proposals, not enforced as output validators;
admitted observations receive finite-JSON and envelope checks, not semantic validation.
Conservative error-key filtering can reject legitimate fields and cannot detect
every tool-specific failure encoding. No live ROS observation parser, entity
alignment, unit/freshness contract or real shared-snapshot collector was invented
to fill these gaps.

The counterexample is fundamental: given observations on finite input set S,
another tool can agree on every element of S and differ elsewhere. Even unlimited
agreement in the supplied cases cannot identify distinct entities with coincident
values. More samples can falsify a relationship; without additional assumptions
they cannot prove the semantic identity required to omit a target acquisition.
The adversarial controls make that distinction observable in this study.

Retain this as an inspection/diagnostic artifact. Reconsider optimizer integration
only if automatically available contracts establish entity identity, units,
argument alignment, output coverage and freshness—or if optimization is confined
to a narrower mechanically justified operation such as reusing the same tool's
already-valid observation under an explicit state contract. New semantic adapters
or LLM-authored tables would change the research premise and were not added here.

## Reproduction and preservation

From the repository root:

```bash
.venv/bin/python -m unittest discover -s research/capability_discovery -p 'test_*.py' -v
.venv/bin/python research/capability_discovery/audit_results.py research/capability_discovery/results_corrected
source /opt/ros/jazzy/setup.bash
.venv/bin/python research/capability_discovery/run_study.py --output /tmp/rosa-capability-reproduction
.venv/bin/python research/capability_discovery/audit_results.py /tmp/rosa-capability-reproduction
```

The study refuses to overwrite results and verifies the corrected freeze before
running. [README](README.md) identifies all artifacts and initial-run reproduction.
No dependencies or core ROSA files changed. Both runs verified hashes for 60
pre-existing tracked/research files and protected Git state before/after.
`origin/member/martin` remained `b13df0f03677754f42383dee95424cded862b117`;
there is no local `member/martin` branch. No worktrees, commits, pushes or merges
were created. Deliverables remain uncommitted in the requested experiment branch.
