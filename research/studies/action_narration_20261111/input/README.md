# ROSA research continuation — 2026-11-11

This package continues the canonical 10 November ROSA context and integrates the 11 November native-read Codex experiment without overwriting past results. It also contains a **new independent offline audit** of existing primary diagnostic model-end metadata. No new ROSA/ROS2 or LLM experiment was run here.

## Read order

1. `TECHNICAL_RESEARCH_REPORT.md` — independent evidence integration, five algorithm-design iterations, primary-literature comparisons, experimental recommendation.
2. `DECISION_LEDGER.md` — what changed, what did not, and falsifiers.
3. `CODEX_EXPERIMENT_PLAN.md` — constrained next causal model-agent comparison with fully enabled strongest simple controls and protected answer quality.
4. `ROSA_RESEARCH_CONTEXT_2026-11-11_UPDATED.md` — full existing cumulative context through Section 15 plus additive Sections 16–17. This is a **proposed replacement copy**, not automatically synchronized with local Git or Project Sources.
5. `replay_model_turn_costs.py` and `model_turn_costs_replay.json` — original trace-derived token/time audit.

## Independent audit reproduction

Extract the user's `ROSA_NATIVE_READ_REVIEW_20261111(1).zip` package; it contains `evidence/historical_archives/rosa-baseline-diagnostic-review-20261107.zip`. Run:

```bash
python3 replay_model_turn_costs.py \
  /path/to/native_read_investigation_20261111/evidence/historical_archives/rosa-baseline-diagnostic-review-20261107.zip \
  --out model_turn_costs_replay_new.json
```

The script uses the Python standard library, checks ZIP CRC, excludes oracle and diagnostic replay trace files, validates the 36 primary episodes and 227 completions, and emits independent aggregate metadata. It **does not** run ROS or any LLM. For the original native fixture, follow the Codex archive's own `README.md` only in the user's authorized local ROS environment; do not rerun it merely to recreate this report.

## Scope

- New native-read Codex results: bounded ROS2 experimental report **as externally conducted**, original saved journals reviewed and archive hashes/tests checked; not independently executed on ROS2 here.
- New model-turn diagnosis: actual baseline primary trace JSONL replay **executed in this environment**; not an inference experiment or causal prompt intervention.
- Next proposed intervention: local model/agent comparison, not yet executed; no paid API inference or edits to the user's local repository.

Files in this ZIP do not include the ~7.5MB native Codex evidence already provided by the user. Keep it and its complete historical trace archives intact for reproduction.
