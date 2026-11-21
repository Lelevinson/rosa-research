# Implementation clarifications and invalidated analysis

The original PROTOCOL_FROZEN.md and INPUTS_FROZEN.json are immutable. This note
records implementation differences and repairs; it does not change their hashes.

Before first replay, the strongest C gained ordinary k2→k1 backoff as well as
fixed-order C. The candidate's proposed backoff is ordinary and must not be kept
exclusive. Parent constrained recent-k2 score uses alpha1 and strict threshold0.4;
embedding/domain adapters and original activation/rate policy are unavailable.

The development Wilson diagnostic estimates complete behavioral agreement from
development-only examples, never from training template counts. Need remains
unlabeled. The risk-calibration ablation name no_provenance means removal of this
complete-action/provenance-risk admission calibration, not removal of the hard
unique-origin binder. All candidate ablations use identical context/backoff.

The first replay was invalidated by independent parser/source review. Its source,
predictions, stdout and summary survive under results/pre_audit_v1 and its hash
freeze at evidence root. Corrected analysis on the same immutable inputs/splits
changes event cutoff/identity/error handling and fixes ablation confounds; it
does not tune thresholds or reinterpret incorrect predictions as successful ones.
Final source freeze and test logs identify the corrected revision.

Two executable synthetic revision layers are distinguished. test_replay.py
contains conceptual gate functions with stipulated contracts. adversarial.py
uses actual fitted Predictor objects and the shared binder for initial,
unique-origin, and final admission variants. The latter was added after review
to close the gap between conceptual examples and executable learner revisions.
Those8 fixtures remain development counterexamples, not held-out frequency data.

Follow-up fixes also split parent training paths at UNKNOWN and reject unmatched
real receipt origins. These are conservative parser corrections. Shadow execution
stays disabled; policy admission is separately computed from logged gate failures.
There was no live phase, no live protocol revision and no missing run closeout.
