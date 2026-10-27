# M1 checkpoint: bounded ROSA macro prototype 0.1.0

The reusable numeric-state macro and its tested runtime dependencies are
checkpointed together on member/martin. Much supporting code predates M1;
this commit does not claim all included safeguards are new research results.

Public API: `rosa_reliability.bounded_macro`. ROSA integration:
`rosa_reliability.macro_agent`. Reuse of WorkflowSession scaffolding is deliberate;
pausing its experimental policy does not remove shared evidence/permission code.

- [Specification](docs/MACRO_MODULE_V1_SPEC.md)
- [API, installation and examples](docs/MACRO_MODULE_V1_README.md)
- [Optional protected remembered authorization](docs/REMEMBERED_CHATGPT_AUTH.md)

Engineering acceptance: 36 focused test methods,12 scripted real-ROSA paths,
7 deterministic Gazebo checks, exact persisted Phoenix audits and isolated wheel
installation passed. No new live-model performance finding is claimed. The
sibling evaluation repository retains the complete M1 report and checksummed
archive `ROSA_MACRO_MODULE_V1_M1_ENGINEERING_2026-10-27.zip`.

M1 supports one fixed numeric-state skill per fresh invocation, one write,
explicit permissions and fresh evidence-referenced reports. Pose alternatives
remain one capability. M2 adds a separate read-only contract; no JTVR, memory,
planner, teammate-adapter migration or physical hardware is required.

The earlier macro-focus study stays incomplete at69/72 attempts. Its failures,
limits, source snapshots and scores are not changed by this checkpoint.
Remembered OAuth is opt-in; actual provider resume is not yet tested and no real
remembered grant was provisioned. Default memory-only revocation remains intact.
