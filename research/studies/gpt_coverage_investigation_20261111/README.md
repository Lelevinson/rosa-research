# GPT integration and answer-coverage investigation

Read [REPORT.md](REPORT.md), [DECISION_LEDGER.md](DECISION_LEDGER.md) and the frozen
[PROTOCOL.md](PROTOCOL.md). [ALGORITHM_ASSESSMENT.md](ALGORITHM_ASSESSMENT.md) examines
concrete rules, primary literature and countercontrols. The independent full-trace
review is [INDEPENDENT_RESULTS_REVIEW.md](INDEPENDENT_RESULTS_REVIEW.md).

This is a new bounded diagnostic, not a rerun or overwrite of November11 evidence.
GPT-6 Luna was selected from the real account catalog and tested through existing
ChatGPT-plan OAuth after explicit data-disclosure approval. Other catalog models
were not inferred to support runtime calls. No API key, paid API-key billing,
model download, production ROSA edit or speculative optimizer was used.

Execution flow:

- `access_probe.py::main` checks existing nonsecret grant state and account catalog;
  it never generates a model answer or exports tokens.
- `run_study.py::run` freezes sources, starts an isolated stock ROS fixture and
  independent persistent oracle, launches activation or10 frozen cells and closes
  all owned processes. Existing user Ollama service remains running.
- `EvaluationROSA` overrides only prompt/tool assembly, preserving actual ROSA
  agent/executor behavior. `episode` supplies `ChatRosaLLM` through ROSA's llm
  interface and invokes its asynchronous executor.
- `MeasuredModel._generate` and the rosa-llm observer preserve full messages,
  schema hashes, native request bodies/decoded stream events, original call IDs,
  usage, statuses and timing. Tool receipts use unchanged Nov11 read-only helpers.
- `evaluate.py::analyze` derives expected values from independent native snapshots;
  it is never imported by runtime. Its first-start procedural screen is weaker
  than the required completion-before-recovery rule. Manual adjudication and raw
  intervals deliberately reject those false screen passes.
- `summarize_results.py::summarize` combines frozen measurements with explicit
  manual judgments; `verify.py` checks source/trace/closure and ZIP integrity.

Offline verification requires only Python standard library:

```bash
python3 research/studies/gpt_coverage_investigation_20261111/verify.py \
  research/_artifacts/gpt_coverage_investigation_20261111/primary-v1
python3 research/studies/gpt_coverage_investigation_20261111/verify.py \
  research/_artifacts/ROSA_GPT_COVERAGE_REVIEW_20261111.zip
```

Recalculate derived evaluations with the existing locked uv environment:

```bash
UV_CACHE_DIR=/tmp/rosa-uv-cache uv run --no-sync python \
  research/studies/gpt_coverage_investigation_20261111/evaluate.py \
  research/_artifacts/gpt_coverage_investigation_20261111/primary-v1
UV_CACHE_DIR=/tmp/rosa-uv-cache uv run --no-sync python \
  research/studies/gpt_coverage_investigation_20261111/summarize_results.py \
  research/_artifacts/gpt_coverage_investigation_20261111/primary-v1
```

These commands rewrite derived files only; preserve originals when auditing.
`--no-sync` avoids dependency changes. Source/transport checks do not certify
semantic correctness; read the manual source and temporal-order judgments.

Native reproduction requires ROS2 Jazzy, the pinned uv environment, the existing
Qwen checkpoint and an eligible user's own authorized ChatGPT-plan grant. A new
external disclosure/inference run must be authorized; current approval covers
only the completed bounded run. No credentials, weights or virtual environment
are in the ZIP. To inspect the execution command without running it, see the
saved setup worker commands, cases.json and frozen protocol. Use a new output
identity/domain after checking isolation; never overwrite preserved primary-v1.

Artifacts are under research/_artifacts/gpt_coverage_investigation_20261111/;
second persistent backup under research/_artifacts/backups/gpt_coverage_investigation_20261111/.
The ZIP includes the full prior action-narration review as a nested historical
archive. Both backups share this host/filesystem, not off-machine protection.
Source defaults, AGENTS.md and Git history remain unchanged. Canonical context
has an additive results entry; ChatGPT Project Sources are not synchronized by
this local update.
