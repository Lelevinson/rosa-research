# M2/M3 additive capability contract, 2026-10-27

M1 checkpoint: research cc4a170; evaluation 0c95c9b. The M1 v0.1 API, source
snapshots, reports and archive stay unchanged. New public imports live in
`rosa_reliability.capabilities`, component version0.2.0.

CapabilityRegistry accepts existing StateSkill and a new InspectionSkill.
Selection/invocation/reporting retain the same five tools and shared guards.
One skill is selected per fresh invocation. A movement has at most one write;
an inspection has ZERO writes, enforced even if the caller requests write_state.
Reselection cannot turn an inspection task into permission to move.

Inspection is an explicit read-only readiness contract, not another target pose.
Its application-bound subject and source/check groups define authorized Boolean
observations. Every source group is one separately reserved, bounded native I/O
acquisition. Results retain each source operation ID and fresh task evidence.
Required conditions true means SUCCESS; known false means FAILURE (observed
unready); any unavailable value conservatively means UNKNOWN. Acquisition itself
and readiness are distinct outcomes. For compatibility with the existing trusted
report validator, Boolean facts have an explicit reversible1/0/null encoding.
No joint pose is treated as the inspection's goal and no controller is changed.

The ROS adapter queries ListControllers and separately acquires a fresh joint
sample through a read-only transport with no trajectory publisher. It reports
activation and observation availability, not collision safety, torque readiness,
future motion success or the ability to grasp objects. Observation/permission
checks occur again in a later movement invocation; readiness is not a reusable
authorization token or evidence cache.

M2 acceptance: independent movement and inspection checks in Gazebo, including
unready/missing observations, truthful classifications, zero inspection writes,
ordinary state-skill guards, native budgets, source provenance, terminal handling
and exact Phoenix audit. Deterministic/reference clients are labeled as such.

M3 begins only after M2 passes. Deliver a runnable natural-language demo using
the same public registry, clear caller/program attribution, deterministic control,
and clarification/escalation cases. A small live smoke is permitted, not a large
benchmark: at most three healthy/ambiguous requests per backend,24 requests per
backend,180 seconds per task,10 native operations,16 tool attempts,2048 observed
output tokens,1024 local per-call,context8192,temperature0,seed42. Healthy movement
and inspection execute separately; no multi-write outer task is authorized.
Scripted tests do not count as live model decisions. Any unavailable hosted
authorization is recorded as pending, never a model failure or assumed success.

M2/M3 are engineering/demo milestones, not a new causal comparison or a guarantee
of Qwen/Sol reliability. Stop before M4 and prepare a combined report. No JTVR,
episodic memory, extra robot/controller installation, planner or backend migration.
