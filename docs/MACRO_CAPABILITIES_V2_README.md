# Bounded movement and read-only inspection

This additive v0.2 interface reuses the M1 execution and report guards. It supports
one state-changing capability (named UR5e poses) and one distinct read-only
diagnostic capability. Two named poses are not two actuated skills. No gripper,
grasping, collision planner, memory or general planner is included.

## Run the public demo

Use the existing WSL research environment with ROS 2 Jazzy and the installed
UR5e Gazebo/controller packages. Do not run against physical hardware. Choose an
unused output directory and run only one simulator demo at a time.

```bash
source /opt/ros/jazzy/setup.bash
source /home/martin/.local/share/rosa-envs/research/bin/activate
python -m rosa_reliability.capability_demo --mode deterministic \
  --skill ur5e.inspect_readiness --output /tmp/rosa-inspect-example
python -m rosa_reliability.capability_demo --mode deterministic \
  --skill ur5e.offset --output /tmp/rosa-move-example
```

These are deterministic controls given a resolved skill, not language reasoning.
The public live demo uses `--mode ollama --ollama-url YOUR_LOCAL_ENDPOINT
--request "Inspect readiness without moving" --output /tmp/rosa-live-example`,
or `--mode siwc --request ...`. Hosted mode explicitly opts into the remembered
session. The CLI has an external deadline and bounded inference, but is a demo,
not an independent benchmark scorer. Its `pass` field means an accepted report;
it does not by itself establish that the user requested the selected skill.

The stronger M2/M3 harness is in `rosa-evaluation/experiments/macro_capabilities_v2`.
M2 exercises completion, already-satisfied state, ineffective/partial execution,
missing observations, actual controller deactivation and blocked inspection
writes. M3 records actual model selection, program actions, independent observers,
source freezes, usage, local traces and exact persisted Phoenix span matching.
Its fixed output paths reject duplicate runs; preserve completed records.

## Integrate a bounded capability

```python
from rosa_reliability.bounded_macro import StateSkill, MacroLimits
from rosa_reliability.capabilities import CapabilityRegistry, InspectionSkill

catalogue = (CapabilityRegistry()
    .register(StateSkill(skill_id="arm.home", targets={"/arm": {"joint": 0.0}}))
    .register(InspectionSkill(skill_id="arm.inspect", subject="/arm_readiness",
        checks={"controllers": ["active"], "sensor": ["fresh"]})))
invocation = catalogue.open(
    {"state": bounded_state_transport, "inspection": bounded_inspection_transport},
    allowed_skills=["arm.inspect"], limits=MacroLimits())
bundle = invocation.execute("arm.inspect")
# A caller/model classifies the actual latest evidence, then cites its ID.
evidence = invocation.session.observations[-1]
invocation.submit_report("SUCCESS", evidence["observation_id"])
```

The last line is appropriate only if all actual required conditions are freshly
true. Use FAILURE for observed unready conditions and UNKNOWN for unavailable
evidence; a report does not create facts. Invalid classifications are rejected.
The example transport names are caller-provided adapters, not installed devices.
Inspection transports implement bounded `read_group(source, names)` returning
exact requested Boolean values or null; state transports implement bounded
`read`/`write`. Registration copies and validates definitions. Allowed skill
subsets are permissions set by the application, not inferred from model prose.

The five tools remain select_skill, read_state, write_state, verify_outcome and
submit_report. The model chooses a permitted skill and classification; Python
owns routine acquisitions, one guarded movement at most, fresh verification and
terminal handling. An inspection has zero writes and no trajectory publisher.
Each source group costs one native operation: the readiness skill normally uses
one controller query and one fresh joint-sample acquisition. Values are explicitly
encoded true=1.0, false=0.0, unavailable=null for the existing evidence validator.

Use a fresh invocation per task. A readiness report does not authorize a later
movement or guarantee future state. Unknown/ineffective writes are not replayed.
Caller transports must enforce their own I/O bounds; use an external watchdog
and cumulative inference budget in real runners. Default task limits are ten
native operations, sixteen tool attempts, three corrections and 180 seconds.
The default joint tolerance is 0.025 rad; it is not a collision-safety criterion.

## Observed limits

The October 27 M3 smoke had one run of three tasks per model. Sol completed 3/3;
Qwen completed movement and inspection but inspected an ambiguous request instead
of asking for clarification (2/3). No Qwen-specific repair was added. The read-only
permission prevented motion, but that does not make the semantic decision correct.
There is no comparative efficiency or generalization claim from this smoke.

Readiness means controller activation plus a fresh complete finite joint sample,
not path safety, torque readiness or grasping. The final observer is independent
of the actor instance but uses the same simulator, messages and controller APIs.
`selected_max_writes` is diagnostic only after selection; before selection the
current snapshot defaults to one even in a read-only catalogue. Actual catalogue
permissions and dispatch guards enforce zero writes in these read-only tasks.
