# M2/M3: bounded inspection and live ROSA demonstration

M1 checkpoint: cc4a170, branch member/martin. M2 independently passed ten Gazebo
engineering checks. M3 completed three tasks per backend: deterministic 3/3,
Sol 3/3, Qwen 2/3. Qwen selected a permitted inspection for an ambiguous request
instead of asking for clarification. No replacement trial or prompt retuning.

The component supports bounded named-pose movement and zero-write readiness
inspection; it does not add a second actuator, planner, memory or JTVR. Per-model
observations and program actions are distinguished. The separate post-demo OAuth
fix validates one actual protected refresh across process restarts.

- [Public demo/API instructions](docs/MACRO_CAPABILITIES_V2_README.md)
- [Additive capability contract](docs/MACRO_CAPABILITIES_V2_SPEC.md)
- [Remembered authorization fix and live validation](docs/REMEMBERED_AUTH_ROTATION_VALIDATION_2026-10-27.md)
- [Combined report in evaluation repository](../rosa-evaluation/docs/M2_M3_COMBINED_REPORT_2026-10-27.md)

This is an engineering/demo milestone with a documented Qwen failure, not a
comparative performance result. M4 remains unstarted. Archived M1/M3 runtime
versions remain immutable; the working OAuth hotfix is a prospective change.
