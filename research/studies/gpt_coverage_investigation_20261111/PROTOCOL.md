# GPT integration and coverage diagnostic — pre-execution v1

2026-11-11, Asia/Taipei. Current user request authorizes bounded investigation and
small inference comparisons when access is authorized. Existing `rosa-llm` OAuth
profile has resource.invoke and chatgpt.tokens.use.direct; catalog renewal passed.
Use that ChatGPT-plan grant only. No API key, pay-as-you-go API billing, paid-credit
purchase, new login or undocumented credential reuse. Catalog visibility is not
runtime inference success; compatibility must pass first.

## Five-question preflight (canonical12.2/14.2)

1. Observed opportunity: Nov11 primary d1 B/C omit parameter reads but report
   false for both clocks at normal stop (input3047/3068 +124 output, below4096).
   A reads both and performs stale check. All x1 finals truncate at4096. These are
   different failure layers. Lower cost is not an opportunity to omit acquisition.
2. Concrete test: compare original strong deconflicted A vs original terse B on
   exactly d1_recovery/x1 for visible GPT6 Luna and Qwen with fixed16384 context.
   Add fixed generic verification V only on d1 for each provider as the ordinary
   control for a coverage mechanism. No runtime answer/source mapping. No framework
   candidate is implemented. The actual ROSA constructor/executor and ChatRosaLLM
   are used; adapters do not decide when semantic evidence is sufficient.
3. Prior mechanisms: ordinary verification prompting, model-declared obligations,
   claim/receipt checks, ReAct, CRITIC and attribution. Related work alone is not a
   veto. Test exact incremental choices and adversarial counterexamples separately
   in ALGORITHM_ASSESSMENT.md. A receipt ID certifies an execution, not entailment or
   request completeness. Static V may solve the observed failure with no algorithm.
4. Fairness: same original8 read schemas/backend/permissions, stock fixture data,
   task strings and scoring within all arms/providers. A/B system policies retain
   original text; V adds one explicit generic verification paragraph, not a map.
   Same iteration/native/time budgets. All provider settings and wire schemas are
   saved. Qwen temperature0/seed42/thinkfalse/output1600; explicit context16384.
   OAuth adapter accepts only parallel_tool_calls/tool_choice, so Luna uses backend
   decoding/context defaults and parallel_tool_calls=true. No unsupported seed,
   temperature, reasoning or max-output control is forwarded. Cross-provider
   differences cannot identify a pure model-weights causal effect.
5. Minimum decision-changing work:2 tasks×2 arms×2 providers=8 cells, plus2 d1 V
   cells=10. This resolves whether context-corrected execution and an accessible
   second model reproduce the failure, and whether ordinary prompting repairs it.
   Not a broad benchmark; no new algorithm, held-out study or replicate follows
   automatically. Stop at10, budget/failure or incompatibility; preserve failures.

## Activation and source freeze

Freeze new source/cases/protocol, unchanged ROSA and installed rosa-llm source,
old helper source and package/version identities before inference. Old raw/report
review is source-bound, not a reconstructed new run. Access probe is a metadata
request with no inference. Exact account catalog lists gpt-6-luna and gpt-5.6-luna;
select gpt-6-luna explicitly. No claim that other listed models are runtime-tested.

At most one actual ROSA/ChatRosaLLM known-argument activation episode per provider
(three model turns max), requesting independent node-info list and topic-info,
then a final response. Actual calls must parse, execute successfully and preserve
IDs/results; verify model is offered the same original tool schemas. Check supported
list use and actual multiple-call execution. For Qwen read /api/ps and require
context_length16384 before scored work. For Luna capture actual response status,
model and available context metadata without inventing an override. If activation
fails, record blocker; no silent provider/model substitution or broad rerun.

## Frozen cells and runtime

cases.json copies d1_recovery/x1 requests byte-for-byte from Nov11. V adds generic
verification policy only; no task word changes. Shuffle all10 cells with seed20261112;
one observation per cell. All development tasks, not held out. Use isolated localhost
Jazzy domain175, same four stock nodes/RGB37/83/129 and middleware. Model still chooses
all tools/arguments and action vs final. Agent effects are reads only. No forced
tool action, text stripping, grammar, answer injection, semantic compiler or cache.

240s episode,2400s scored block,10 model iterations,64 CLI reads/cell,12s/CLI,
one additional failed identical argv attempt. HTTP timeout90s phase, no model request
retry or failed-cell replacement. Independent tools may run concurrently. Preserve
all provider attempts, observer raw decoded SSE/NDJSON, exact native request bodies,
model-visible messages/schemas, original tool-call IDs/intermediate steps, raw CLI
outputs and statuses. Authentication headers/tokens/credential files are excluded.

## Closeout repair: separate graph availability from observed values

Before/after snapshots use a persistent evaluator-owned rclpy graph observer with
two predeclared enumeration reads separated by0.3s (not policy input), and also
preserve one original no-daemon CLI enumeration. All enumeration attempts retained.
The persistent observed node set must contain the four owned fixture nodes in both
reads; missing inventory means indeterminate closure, not reconstructed success.
Also record actual direct node-info, parameter dumps, topic-info and retired-node
absence. Do not derive missing enumeration from known fixture names or direct reads.
No adaptive resampling until a favorable snapshot appears. Snapshot before, after
every2 scored cells and after final; final snapshot before teardown, record all
owned process statuses and daemon stop. Failures remain failures. Persistent graph
transport is evaluation infrastructure, not candidate advantage; its setup is paid.

## Scoring, metrics and stop rules

Frozen score.py from prior study remains intact. New evaluation derives truth from
actual direct snapshots and checks all persistent inventories and before/after values.
No post-hoc repair. Complete source-supported output requires every requested field
correct, actual successful value acquisition (parameter service advertisement or
param-list names do not count), correct identities/roles, requested initial stale
check in d1, and no unsupported factual claims. Unavailable answers are honest but
incomplete for available fixture fields. All extra prose reviewed. Evaluate fields,
procedure and overall support separately; unstable/invalid oracle is indeterminate.
Scorer/known fixture source mapping is evaluation only, never imported by runtime.

Report action/final/model counts, proposed/accepted calls, invalid calls, input/output
tokens and reasoning/cache details if supplied, actual CLI starts/completions and
errors, reads/writes, HTTP/client/model metadata, total episode latency, setup and
measurement overhead. OpenAI HTTP duration is not isolated decode compute; missing
native compute metrics are unknown, never zero or imputed from Ollama. Count quota
usage and failed attempts; actual dollar billing is not exposed by this client.

Positive B requires no A-supported task loss and cost reduction on mutually supported
pairs, not fewer tokens on partial answers. V is an ordinary diagnostic, not a novel
method. With one seed/observation, effects remain exploratory. If models/prompts
solve d1, that weakens the asserted need for a new runtime guard; if they fail,
failure still does not prove a status-only guard can identify missing semantics.
No algorithm implementation until actual rule differs from equally informed ordinary
validation/prompting with charged overhead and acceptable counterexamples.

Raw artifacts: ignored research/_artifacts/gpt_coverage_investigation_20261111/;
second persistent backup under research/_artifacts/backups/. Include original Nov11
review ZIP, new sources, protocol, complete evidence, hashes and verifier. No sole
/tmp evidence, Git history changes, AGENTS.md overwrite or source-default changes.
Append significant findings to canonical context, preserving its original bytes.

## Pre-primary activation/audit closeout

The first host execution request was blocked by automatic approval review before
any process ran. User explicitly approved the stated GPT payload/destination and
one activation +five scored GPT episodes; approval is preserved separately. This
resolved the authorization prerequisite without API-key use or model substitution.

activation-v1 completed both providers: two model requests each, two independent
native tools, one two-node list, three successful CLI reads with actual overlap
and a normal final response. Same schema hash as Nov11. Qwen active context16384
is recorded; Luna response model is gpt-6-luna and status completed. Both final
persistent inventories and direct observations passed; all owned cleanup exit0.

Independent audit before primary found no fatal parity/leakage defect. Corrections
frozen before primary: distinguish attempted/scheduled cells on budget stop; require
actual missing-node returncode1 and missing-node stderr instead of treating a timeout
as absence; mark absent token-detail counters as unreported, not observed zero.
These do not change prompts/tasks or tune model behavior from scored results.
The d1 procedural screen requires exactly one actual named stale check as first
native attempt; full narrative/source adjudication remains separate. No scored
primary cell has yet run at this amendment.
