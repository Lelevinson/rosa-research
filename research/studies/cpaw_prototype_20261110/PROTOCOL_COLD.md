# Cold-start reference correction, frozen before regression run

The earlier cold arm abstained from rollout but inadvertently used a reference schedule optimized from 64 training outcomes. That does not model a no-history tool. Replace only its reference with the fixed model-free order (0,1) then (2,3), respecting the capacity in both suites; charge no model-derived preparation to that arm. It receives no training-derived decision. All other arms, seeds, costs, metrics and models remain fixed. Preserve previous outputs. Rerun both suites and replay.

The final regression supplies an empty scenario tuple to the cold policy itself and reports zero calibration episodes for that arm, making the no-history boundary executable rather than relying solely on the cold guard.
