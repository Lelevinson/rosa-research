# Bounded macro v0.1: M1 contract

Status: implementation contract, 2026-10-27. Research prototype, not a general
planner or a physical-robot safety certification. M1 stops before M2/live studies.

## Existing code and reuse

| Existing component | Reuse / required boundary |
|---|---|
| `MacroSession -> ReferenceWorkflowSession -> WorkflowSession` | Retain inheritance and tested straight-line acquisition policy. Do not delete workflow scaffolding. |
| `ExecutionSession`, `EvidenceSession`, `ReliableTool` | Retain permission, dispatch reservations, evidence invalidation, feedback and actor accounting. Add only public-entry validation where required. |
| `make_reference_tools`, `AcceptedReportROSA`, `CompletionAwareROSA` | Reuse evidence IDs, accepted-report termination and pre-parser completion seam. |
| `BoundedPromptROSA` | Reuse the common five-tool prompt, with explicit authorized catalogue. |
| `ArmTransport` | Existing ROS 2 adapter, with independent read-only observer outside the macro. No ROS import in core registration. |
| Frozen experiment inference gate / simulator-home helper | Leave frozen files unchanged. Expose a research-side runner gate and simulator utility with equivalent bounded behavior, without importing experiment packages. |
| Fixture fault labels, expected outcomes and private scorer | Remain evaluation-only; never enter registered skills or runtime decisions. |

Both repositories were inspected on `member/martin`; substantial pre-existing
modified/untracked work is retained. M1 adds separate files and does not update
dependencies, historical sources, manifests, prompts or scores.

## Public API and deliberately limited scope

Import from `rosa_reliability.bounded_macro`. Register validated `StateSkill`
objects in `SkillRegistry`; call `registry.open(transport, limits=...)` for a
fresh invocation. The public `select_skill` argument is exactly one registered
`skill_id`; all target parameters are bound and validated by trusted application
code at registration, not arbitrary model-supplied controller coordinates.
Unknown IDs, extra tool arguments, incomplete or changed target writes fail
before native dispatch. A catalogue can expose multiple authorized IDs, but
numeric pose alternatives do not constitute different robot capabilities.

Version 0.1 supports one selected, single-node numeric-state skill and at most
one dispatched write per invocation. It is not an arbitrary callback/plugin SDK.
The transport supplies `read(node, fields)`, `write(node, values)`, and optionally
`validate_write(node, values)`, with bounded I/O and finite observations (or a
TimeoutError). Core policy contains no ROS node, joint, pose, fault or model name.
A future read-only capability requires an explicit new capability contract;
M1 does not pretend a pose definition already implements it.

Invocation exposes the existing five tools, direct scripted select/report calls,
the public catalogue and a snapshot. A selection runs the macro or exposes
primitives in the explicit comparison mode. Successful bundle verification is
not an accepted terminal report: the caller still classifies SUCCESS/FAILURE/
UNKNOWN and cites the latest task-local observation ID. No automatic report or
model mistake repair is credited as a model decision.

## Evidence, ownership and limits

The application authorizes the catalogue. The model selects/classifies. Python
owns bundled read/conditional-write/verify operations. The transport executes
native I/O. Independent outcome scoring remains outside all these components.
No runtime report consults a hidden evaluator. Missing state cannot authorize a
write; uncertain dispatch never permits replay; even a partially applied failed
write invalidates earlier evidence. Evidence freshness means latest task-local
acquisition after applicable writes; transport timestamps/fresh acquisitions
are a separate adapter responsibility, not a claim that stored values stay true.

`MacroLimits` bounds native operations, tool attempts, corrections and elapsed
time before dispatch. One-write permission is fixed. The reusable agent runner
separately reserves model requests before invocation, meters returned usage,
withholds truncated/over-budget generations before tool parsing and accounts
for unreturned requests. Per-trial limits do not supply a campaign budget: the
caller must supply a cumulative reservation callback for multi-trial runs.
External timeouts and transport I/O deadlines must bound already-running calls;
Python cannot safely cancel an arbitrary user callback and assume no write.
The Linux main-thread demo/validator uses an external alarm and records cleanup.
No claim of hard cancellation is made for arbitrary transports/platforms.

The public agent is synchronous, non-streaming, one invocation per fresh task,
and retains the exact five-tool registry and common prompt. Default upstream
ROSA is unchanged. Existing adapters remain unchanged; scripted adapter-contract
checks do not establish fresh live Qwen/Sol performance.

## Acceptance and evidence

M1 validation records PASS/FAIL/NOT YET TESTED for registration/rejection, two-ID
routing, scripted and Gazebo transports, already-achieved state, missing reads,
partial/uncertain execution, stale/cross-task evidence, report correction and
terminal handling, budgets/attribution, model usage/truncation accounting,
Phoenix exact span persistence, installed example entry points and frozen hashes.
Zero hosted/local inference requests are needed. Live model behavior and a
second genuinely different capability remain explicitly untested in M1.

Research code/docs/examples belong here; validation runner/logs and independent
observations belong in `rosa-evaluation`. Stop once M1 is evidenced and provide
an inventory-based M2 handoff. Do not launch a live benchmark or install the
teammate adapter, JTVR, episodic memory, a gripper or a general planner.
