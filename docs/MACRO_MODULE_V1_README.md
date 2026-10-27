# Bounded ROSA macro 0.1.0

Research prototype for one authorized numeric-state skill per invocation. The
application supplies permitted targets; the model chooses a skill and classifies
current evidence. Python performs the routine read / conditional write / fresh
verify steps. No model training, planner, memory, discovery or automatic replay.

## Install and run without a model

In the research checkout, use the existing Python 3.12/uv environment:

```bash
uv sync --locked
uv run python -m rosa_reliability.macro_demo
uv run python -m rosa_reliability.macro_demo --fault missing_before
uv run python -m rosa_reliability.macro_demo --fault partial
```

These are deterministic caller demonstrations, not model-performance tests.
The prototype is included in the existing `jpl-rosa` package; it needs no new
dependency or separate package installation. It is not published to PyPI.

## Register and invoke

```python
from rosa_reliability.bounded_macro import SkillRegistry, StateSkill, MacroLimits
from rosa_reliability.macro_demo import MemoryTransport

registry = SkillRegistry().register(StateSkill(
    skill_id="arm.inspect",
    targets={"/my_arm": {"yaw": 0.2, "pitch": 0.1}},
))
invocation = registry.open(MemoryTransport(), limits=MacroLimits())
bundle = invocation.execute("arm.inspect")
# The caller must inspect evidence and choose its classification; execution
# alone does not automatically submit a SUCCESS report.
evidence = invocation.session.observations[-1]
report = invocation.submit_report("SUCCESS", evidence["observation_id"])
assert report["report_accepted"]
```

The concrete example succeeds on its in-memory adapter. Real callers must not
hard-code SUCCESS when observations can be unavailable or execution can fail.
Targets must contain one canonical node and finite named numeric values.
Unknown skills, extra selection arguments, incomplete/changed target writes and
unknown prerequisite state are rejected before dispatch. Use `allowed_skills`
on `open()` to restrict a task to an explicit registered subset. Each invocation
copies permissions; later registry/catalogue changes cannot enlarge that task.

## Connect an existing model

```python
from rosa_reliability.macro_agent import MacroROSA, InferenceLimits

# llm is your already-configured ChatOllama or authenticated ChatSiwc instance.
agent = MacroROSA(llm, invocation, backend="ollama",  # or "siwc"
                 inference_limits=InferenceLimits(calls=8, output_tokens=2048))
answer = agent.invoke("Use the inspection pose if permitted.")
accounting = agent.inference_budget.snapshot()
```

Use a NEW invocation for this example, not the already-terminal one above.
The five existing tools, common prompt and validated immediate termination are
retained. The authorized catalogue is included automatically. Ordinary/default
ROSA behavior is unchanged. A rejected report can be corrected within limits;
an accepted report needs no additional model acknowledgment. Text alone does
not count as accepted completion. The caller owns model/auth/transport cleanup.
Streaming/concurrent task callers are unsupported.

For a controlled reference use `registry.open(..., mode="primitives")`; identical
permissions, tools, reporting and guards apply, but selection does not execute
the bundle. This remains a repaired reference, not untouched upstream ROSA.

The agent reserves inference attempts before sending, requires usage metadata,
records unreturned calls as unknown-cost attempts and withholds length-truncated
or over-budget generations before tool parsing. Local per-call output options
preserve the supplied model's context/temperature/seed; no model replacement is
performed. Hosted output is an observed threshold, not a guaranteed provider cap.
Pass `batch_reserve` for cumulative campaign requests; fresh invocation limits
do not automatically impose a multi-task campaign limit.

## ROS 2 / Gazebo example

With ROS 2 Jazzy and the existing `ur_simulation_gz` installation:

```bash
source /opt/ros/jazzy/setup.bash
ROS_DOMAIN_ID=214 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
  uv run python -m rosa_reliability.ur5e_macro_demo --output /tmp/rosa-macro-demo-001
```

The output directory must not exist. This headless example starts its own
simulator with documented HOME positions, runs seven deterministic cases with
an independent read-only observer, records actor evidence and simulator cleanup,
and restores HOME outside invocation accounting. No experimental runner, LLM
account or credential is needed. It uses two named poses of ONE capability.
Gazebo/ROS installation and geometry/controllers are not changed. Mesh-collision
warnings and lack of path/collision validation prohibit physical-safety claims.

## Boundaries

The core reserves native/tool/correction/time allowances before dispatch; one
write is fixed. Transports must bound their I/O. The caller needs an external
watchdog for already-running callbacks/model calls; the Linux Gazebo CLI uses a
300-second external alarm plus cleanup. Cancellation is not proof of no robot
side effect, so uncertain writes are never replayed. Arbitrary untrusted Python
callbacks are not sandboxed by this package.

Evidence IDs are task-local, current relative to acquisitions/writes, and invalid
across tasks or after applicable writes. Physical freshness depends on adapter
acquisition, not only on an ID. Independent experiment scoring belongs outside
the module and must never silently repair model choices.

Public contract: [MACRO_MODULE_V1_SPEC.md](MACRO_MODULE_V1_SPEC.md).
M1 validates packaging and behavior, not a new live-model performance claim.
Genuinely distinct read-only/actuator capabilities require a documented M2
extension; do not disguise another pose as multi-capability support.
