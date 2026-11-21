# Preserved evaluation history

1. `PROTOCOL.md` frozen before implementation; `FREEZE.json` records the engine,
   development fixtures and nine passing unit tests before extension creation.
2. Initial full run: `results/`. Untouched implementation, evaluator, fixture,
   test and protocol copies live in `initial_source/`. Nine initial unit tests
   passed (`unit_tests_initial.txt`). The extension is synthetic and authored by
   the same researcher, not an independent held-out benchmark.
   Scoring clarification implemented before that first run: broad semantic
   positives include aliases, renamed arguments, numeric representation changes,
   unit conversion, and opaque renderings of the same quantity. This makes broad
   recall stricter than the protocol's identical-path eligibility criterion.
   Evaluation labels never enter the engine; all labels remain unchanged in the
   corrected run. Report broad recall and exact-match limitations together.
3. Post-run code review found two implementation defects. Recursive documentation
   cleanup incorrectly removed argument names `title`/`description` and data
   inside `const` objects. The opaque-text filter covered root text but missed
   nested text and arrays of CLI strings, contrary to the protocol. Two new
   regression tests failed on that implementation (`regression_failures.txt`).
4. Corrected schema traversal preserves property names and data literals. The
   text filter conservatively excludes **all string-valued leaves and arrays
   containing strings**, since metadata cannot reliably distinguish text payloads
   from structured identifiers. This also loses valid string capabilities.
5. `FREEZE_CORRECTED.json` records the correction before rerunning the unchanged
   fixtures, thresholds and semantic labels. `results_corrected/` is a regression
   rerun of already-seen extension fixtures, not a fresh held-out result. The
   empirical false-support failure is retained, not tuned away.
