# Substantive iterations, failures and corrections

## 1 — parent replication constraints and initial hypotheses

Inspected pinned source and paper before promotion. Parent error fallback and
native ngram were already present; SimCSE and domain semantic adapters could not
be fairly imported under the no-map/current-inference constraints. Implemented
an explicitly constrained parent path score, ngrams, grouped STOP labels and
H1/H2 associations. Full reproduction was not performed.

Initial H1: after successful predecessor, follow a supported successor. Initial
H2: choose the first equal typed historical output slot. `adversarial.py` actually
fits the shared Predictor and instantiates this initial association-first variant
on eight synthetic cases. Version0 makes four false diagnostic admissions:
goal already complete, equal-value source collision, changed source identity,
and changed nested schema. These are fixture results, not a measured ROS failure rate.

## 2 — two revisions, each attacked and re-tested

Revision1 H1 adds explicit error/STOP/registry/output-shape conditioning and hands
predicted STOP back. H2 preserves all origins, checks current uniqueness, source
tool+arguments and shape. Re-test through actual conditional Predictor/current
binder in adversarial.py reduces false synthetic admissions4→1. The remaining
goal_STOP case is decisive: both needs-more and names-only have the same cheap
features, so high next-tool frequency still proposes an unnecessary read.

Revision2 H1 requires development complete-action uncertainty, observable need and
net cost instead of treating tool frequency as benefit. H2 requires actual source
authority/current validity in addition to type/path identity. Missing certificates
remain unknown. Final candidate re-test has zero diagnostic admissions and zero
false admissions in these eight fixtures. It also rejects useful cases; this is
lost coverage, not proof of safe useful continuation. The same-information ordinary
backoff control produces identical full predictions. List-helper case is already
covered by an ordinary parameterized helper. No invented new algorithm name.

`test_replay.py` additionally preserves conceptual H1/H2 version functions across
eight cases, including stale/text-only, STOP competition and schema change. These
stipulate `needed/permitted_flow/current` as fixture contracts, not values recovered
from ROSA. They are separate from executable learner tests. Production-code tests
exercise real outcome-conditioned counts, /a→/b current-origin rebinding, ambiguous
values, changed source identity/schema and unknown-permission abstention.

## 3 — frozen replay and independent adversarial review

Inputs frozen before predictor scoring: train18 turtle episodes; dev12 demo;
historical mixed validation6; temporal transport validation22. Previously reused
tasks are never called fresh held-out. Counts/thresholds are not tuned on validation.

Independent source review found start/end cutoff leakage, missing legacy receipt
ID joins, incomplete source-identity checks and ablations changing context length.
The first outputs and original replay.py survive in results/pre_audit_v1/ and
REPLAY_SOURCE_FREEZE.json. They are INVALIDATED for interpretation. Corrections
freeze deep state at model_start; join actual call IDs; preserve tool+source args;
use identical backoff for all candidate ablations. Regression tests cover each.
Initial preparation also caught oracle contamination before input freeze; no
oracle trace enters final inputs. A uv-cache read-only error was resolved by a
task-specific /tmp cache; no dependency change or permission escalation.

Corrected replay:269 continuation boundaries,58 initial decisions; candidate
exact behavioral matches12 overall, all STOP; zero complete tool+args matches.
Two of the STOP matches are in mixed validation, neither saves a final decision.
Ten raw differences from fixed-order C disappear against ordinary C_backoff.
Permission, necessity and complete-answer counterfactuals are not identified.
Live gate fails; no ROS/model setup or runtime prototype is performed.

This is a finite family investigation with two executable rule repairs and a
frozen historical replay, not three end-to-end ROSA experiments. Initial failures,
counterexamples and negative historical findings remain preserved.
