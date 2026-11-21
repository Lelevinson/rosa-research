# Frozen smoke protocol, 2026-11-15

Owner decisions resolve the prior setup stop. This amendment supersedes the
unresolved-choice rows in the initial report; it does not authorize a full run.

- Two attempts only: Stage 3 pilot `p3` on `lfm3:1.7b`, seed 1, then `u3` on
  the same model, seed 2. One attempt per task. These are development tasks.
- Same request text and 12 read tools as C1. No write tools or task routes.
- Exact C1 system messages in their original order and separate message
  boundaries; replace only `final_answer` with `respond`. Save the complete
  before/after messages and unified diff. Keep the resulting JSON-object
  wording even though released `respond(message: str)` takes a string: no
  additional prompt repair is authorized.
- Released PyPI Forge 0.10.1 `WorkflowRunner`, max_iterations 40,
  required_steps empty, no prerequisites, terminal `respond`. All validation,
  retries, execution-error limits, rescue, reasoning replay and termination
  use the release implementation/defaults.
- TieredCompact(keep_recent=2), budget_tokens 65536. Record every compaction.
- Thin client override changes only `_build_options`: temperature 0.7,
  num_ctx 65536, num_predict 4096, assigned seed. Inherit released `send`
  unchanged. Record the released and actual request, asserting that the
  options dictionary is their only difference. Configure think=False, as in
  the release API; this suppresses think=True rather than adding a false
  field. Record exact wire behavior and any reasoning returned.
- Isolated Forge uv environment; expose existing ROSA integration dependencies
  read-only. Do not install anything in the project environment.
- ROS_DOMAIN_ID=220, ROS_LOCALHOST_ONLY=1. Use the unchanged Stage 3 fixture,
  readiness check and before/after oracle. Refuse preexisting fixture nodes.
- Maximum 900 seconds per episode, as in the pilot. Record failures and
  timeouts without rerunning. Stop on native guard rejection, write dispatch,
  wrong loaded context, fixture/oracle failure or failed cleanup. Stop and
  ask before changing Forge logic. Always terminate owned fixture processes.
- Verify `/api/ps` reports actual context_length 65536 after each attempt.
- Append raw attempt metadata to RESULTS_LOG.jsonl from the first attempt.
  Preserve requests, responses, token usage, tool/native events and final
  output in a unique directory under research/_artifacts/runs/forge_baseline_20261115/.
- Use Claude Code's frozen scorer-v2.0 only after verifying its SHA-256
  c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9.
  `respond` output is final text: use the frozen last-object/unwrap rule and
  strict evidence support, with no new scoring exceptions.
- Main question: does the authorized integration produce auditable ROS tool
  execution, terminal results and measurable costs without modifying Forge?
  Two successes permit reporting technical readiness only. Failures require
  trace inspection and reporting, not automatic repairs or further inference.
- Report both attempts and stop. Do not inspect held-out E2/E3/E3b. No
  comparative effectiveness or novelty inference from a two-task smoke.

The initial report contains the canonical five-question preflight and nearest
negative result. Source and protocol hashes are frozen before model inference
in the run directory. Preparation/import errors remain setup events, outside
the two model-attempt denominator.
