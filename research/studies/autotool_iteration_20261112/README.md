# AutoTool-family research iteration, 12 November 2026

Read [RESEARCH_REPORT.md](RESEARCH_REPORT.md), [ITERATION_LOG.md](ITERATION_LOG.md),
[REPLAY_REPORT.md](REPLAY_REPORT.md), then
[BLOCKER_AND_NEXT_DECISION.md](BLOCKER_AND_NEXT_DECISION.md).
Result: reproducible offline integration/negative finding; no algorithmic
increment or live ROSA efficiency claim. No model/native operation was executed.

Source inventory, primary literature, mechanism, frozen protocol/amendments,
independent review and decision ledger are adjacent. Exact inputs, rejected
predictions, initial invalidated analysis, sources and hash freezes live in
`research/_artifacts/autotool_iteration_20261112/` and the persistent review ZIP.

Execution flow: `prepare_inputs.py::main` freezes original public traces and
historical sources once; `audit_history.py::main` supplements native continuity;
`replay.py::parse_trace` freezes predecision state; `Predictor.fit/calibrate/predict`
learns earlier behavior and produces shadow proposals; `instantiate` checks
current origin hypotheses; `main` compares the next recorded action afterward.
`adversarial.py::run` executes two rule repairs against synthetic counterexamples.
No experiment module, ROS executor, evaluator truth or HTTP client is imported.

Reproduce from repository root or an extracted ZIP with the same relative paths:

```bash
UV_CACHE_DIR=/tmp/rosa-uv-cache uv run --no-sync python research/studies/autotool_iteration_20261112/test_replay.py
UV_CACHE_DIR=/tmp/rosa-uv-cache uv run --no-sync python research/studies/autotool_iteration_20261112/adversarial.py
UV_CACHE_DIR=/tmp/rosa-uv-cache uv run --no-sync python research/studies/autotool_iteration_20261112/replay.py
```

`uv run` uses the environment, `--no-sync` prevents dependency synchronization,
and UV_CACHE_DIR places cache writes in the permitted temporary directory. All
three scripts also run with ordinary Python3 standard library in an extracted
review copy. They overwrite DERIVED results only; use the extracted copy to
preserve the packaged measurements. `prepare_inputs.py` refuses to replace a
freeze and needs the original sibling paths; it is not needed for packaged replay.

Use `verify.py REVIEW.zip` to check CRC, exact manifest coverage and every SHA-256.
The ZIP and matching second persistent backup are under research/_artifacts/ and
its backups/ folder. Both share this machine/filesystem; neither is off-machine.
No credentials, model weights or virtual environments are included.
