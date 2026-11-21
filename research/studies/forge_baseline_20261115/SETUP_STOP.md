# Forge released-baseline smoke: setup stopped before inference

2026-11-15, Asia/Taipei. **BLOCKED / NOT YET JUSTIFIED for execution:** the handoff explicitly requires stopping when a setup choice is uncovered. No Forge episodes, model requests, ROS commands, or scoring have run. The full pilot comparison has not started.

## Authorization and scope

The owner requested the context-mirror handoff `Claude outputs/2026-11-15_PROMPT_CODEX_forge_baseline.md`, with an overriding limit of **2 tasks × 1 model, then stop and report**. Scoring must wait for Claude Code's frozen scorer; otherwise raw outputs are retained. E2, E3 and E3b were not opened or run. No paid APIs or write tools are authorized.

Read the handoff, `PAPER_GOAL_CONTRACT.md`, [source comparison](../residual_failures_20261115/FORGE_COMPARISON.md), [residual analysis](../residual_failures_20261115/RESIDUAL_FAILURES.md), research entrypoint, active state, rules, canonical context §§0–4, 12 and 14 and later relevant updates, pilot implementation/report and closest negative snapshot replay. Existing findings remain scoped to their evidence; no novelty or comparative-effectiveness conclusion follows from this preparation.

## Setup and unresolved choices

| Item | Required or observed setup |
|---|---|
| Distribution | Installed **PyPI `forge-guardrails==0.10.1`**, rather than running the two-commits-after-tag reference checkout. |
| Isolation | Dedicated uv environment `/tmp/rosa-forge-env-20261115`, Python 3.12.3. Project environment, `pyproject.toml` and `uv.lock` untouched. Dependency inventory and hashes: `SETUP_PROVENANCE.json`. This temporary environment is reproducible from the inventory; durable provenance stays here. |
| Entrypoint | Required: released `WorkflowRunner`; its installed signature was inspected, without calling it. |
| Tools | Required: same 12 ROS read tools as C1 plus Forge `respond`, terminal `respond`, `required_steps=[]`, no prerequisites. `ros2_param_set` and `ros2_service_call` exclusion is a shared safety setting, not a Forge feature. Registration has not been implemented. |
| Context | Required: manually set Ollama `num_ctx=65536` and check actual `/api/ps` context. No model has been loaded or checked. |
| Call budget | Required: 40, counting retries; no additional 10-call default-budget arm in this smoke. |
| System prompt | **Unresolved:** `Workflow` requires `system_prompt_template`; there is no default runner system prompt. Forge's README supplies the example quoted below. The instruction “Forge's own templates” does not select a workflow prompt. |
| Compaction | **Unresolved:** `ContextManager` requires a strategy. Forge exposes both `TieredCompact` and `NoCompact`. Proposed for owner decision: the README example `TieredCompact(keep_recent=2)`, with budget 65536. |
| Sampling | Pilot: temperature 0.7, `num_predict=4096`, seeds 1 and 2, reasoning disabled. Released `OllamaClient` has a temperature setting and `set_num_ctx`, but no `num_predict` setting. It accepts seed as a per-call sampling override; `WorkflowRunner.run` exposes no sampling argument. Matching these settings would require an adapter or lower-level configuration beyond the supplied setup. Preserve released behavior and disclose differences, or approve a transport adapter: **unresolved**. |
| Smoke cells | Not selected or executed while setup is unresolved; maximum remains two pilot development tasks on one existing local model, one attempt each. No held-out inspection is needed. |
| Scorer | Claude Code's freeze appeared during preparation: **`scorer-v2.0`**, [decision](../../decisions/2026-11-15-scorer-v2.md), `../residual_failures_20261115/SCORER_V2_FREEZE.json`. Scorer SHA-256 `c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9` was checked against the manifest. No scoring was performed because there are no smoke outputs. |
| Traces/log | No runs exist yet, so there are no raw model outputs or scored rows. On execution, append every attempt to this study's `RESULTS_LOG.jsonl` from the first attempt, retaining raw requests, responses, usage, tool/native events, final output and failures under `research/_artifacts/runs/forge_baseline_20261115/`. |

The exact README example prompt proposed for approval is:

```text
You are a helpful assistant. Use the available tools to answer the user.
```

This text has **not** been sent to a model. No custom ROS instructions, per-task routes, source maps, required steps or answer-format repairs have been added.

The installed release confirms these required constructors:

```text
Workflow(..., required_steps, terminal_tool, system_prompt_template)
ContextManager(strategy, budget_tokens, ...)
WorkflowRunner(client, context_manager, max_iterations=10, ...)
```

The released client's `_build_options` forwards configured sampling fields and `num_ctx`, but has no `num_predict` option. Passing an arbitrary `num_predict` sampling override would silently omit it; that is not a verified way to match the pilot. `think=False` suppresses Forge's optional `think=True` field rather than sending the pilot's explicit `think:false`; any eventual smoke must retain the exact wire request so this difference is visible.

## Preflight decision record (canonical §§12.2 and 14.2)

1. **Observed need and denominators:** the pilot reports 80 C1 episodes over four local models, 20 per model. The new scorer decision reports corrected C1 counts of lfm3 17/20, Qwen 20/20, gpt-oss 20/20 and bonsai 13/20. The initial residual report's six-artifact interpretation was subsequently corrected: failed relative `node_info` does not prove absence, leaving five artifacts. These are reported findings, not independently rescored here. The source comparison has no behavioral Forge runs, so existing evidence cannot answer whether released Forge works on these tasks. Correctness failures alone do not establish an efficiency gain.
2. **Mechanism and control:** this is a released baseline integration, with no new algorithm claimed. Forge receives the ordinary ROS read registry and unchanged pilot request text. C1 is the strongest relevant ordinary loop comparator; A1 is the deconflicted stock-loop comparator, not the original stock ROSA prompt. Forge adds its own rescue/retry/termination behavior; no privileged task information or enforced route may be supplied. A bare-text response can trigger a Forge retry where C1 would terminate; a correct early response may instead incur extra Forge calls. Both outcomes must remain visible.
3. **Closest mechanisms and negative evidence:** source-level Forge/C1 differences are documented in `FORGE_COMPARISON.md`; no broader novelty conclusion is made. The snapshot replay's negative token-cost result warns against assuming fewer requests imply lower total cost. It is not a reason to add snapshots to this arm.
4. **Fairness and measurement:** keep model, task text, fixture, read tools and budget matched where authorized. Record every deviation, system prompt, released-package hashes, actual context, requests, tokens, native operations, time, crashes and timeouts. Score supported-complete answers only with the common frozen scorer. A two-task smoke cannot estimate model-level effectiveness, confidence intervals, or generalization.
5. **Smallest decision-changing action and stop:** after the uncovered setup choices are resolved, two development attempts can test whether the released runner actually dispatches ROS tools, terminates through `respond`, exposes the correct loaded context and produces complete auditable traces. Stop after those attempts regardless of outcome. Stop earlier on an uncovered setup choice, unsafe dispatch, fixture/oracle failure, or failed cleanup. No repair loop, full pilot or held-out run is authorized by this smoke.

## Environment and coordination events

- Initial Git working tree was clean on `research/capability-discovery-20261110`; source HEAD is recorded in provenance. No existing research or production code was edited.
- `git fetch origin` in the shared context clone failed first under the filesystem sandbox; the authorized elevated retry failed with `could not read Username for 'https://github.com': No such device or address`. Cached refs expose only `origin/member/levinson`, at `7d430ac72eb396961a68715515cd85aefb743dd8`; its entrypoint, active state and synchronization manifest were inspected. Current remote teammate overlap cannot be certified. No remote push, merge or branch checkout occurred.
- The first uv attempt used the unwritable default cache. Retried with `UV_CACHE_DIR=/tmp/rosa-forge-uv-cache`; sandbox DNS failed. The authorized network-enabled retry installed the release successfully in the isolated environment. These are setup events, not model failures.
- Two clarification requests were submitted: approve exact README prompt/compaction, and choose released sampling behavior versus a settings adapter. No unanswered choice is treated as approval.
- Shared active-state and study-index files were left to the concurrent research-state writer; this study report owns the local setup finding and can be linked by that writer.

## Results and limits

**0/2 smoke attempts executed; 0 model requests; no scores.** Supported-complete rate, token totals, crashes/timeouts and Forge-versus-C1 disagreements are **not measured**, rather than zero. There are no failure traces to hand-read. The requested full-run tables and 3–5 failure analyses require later authorization and data.

Verified here: the PyPI package installs in isolation, imports, and exposes the inspected APIs. This does not establish ROS connectivity, tool execution, context activation or task success. The setup stop follows the handoff's explicit instruction; it is not a negative behavioral result for Forge.
