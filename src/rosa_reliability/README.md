# Optional ROSA reliability tools

This module supplies the same four custom LangChain tools to either backend:
`read_state`, `write_state`, `verify_outcome`, and `submit_report`. Use the actual
ROSA executor with `load_default_tools=False` to keep this explicit registry.
It does not modify upstream default tools or silently repair model arguments.

```python
from rosa import ROSA
from rosa_reliability import ExecutionSession, make_tools

session = ExecutionSession(
    transport, {"/robot": {"joint": 0.2}},
    structured_feedback=True, automatic_verification=True,
    operation_limit=10, seconds=180, write_limit=1,
)
agent = ROSA(2, llm, tools=make_tools(session), load_default_tools=False,
             streaming=False, accumulate_chat_history=False, max_iterations=8)
answer = agent.invoke("Read current state, request the target, verify, and report.")
records = session.snapshot()
```

The transport implements bounded `read(node, names)` and `write(node, values)`
methods. `validate_write(node, values)` can reject domain constraints before
native dispatch. Setting `requires_observation=True` additionally requires known
state before a write. The caller supplies an application-specific task prompt;
the example above is not a complete robot safety policy.

Read and report values share a node-keyed structure. Timeout means unavailable
evidence represented as null, not a fabricated numeric value. Reports require a
fresh explicit or orchestrator-initiated verification, canonical IDs and values
matching observations within the configured numeric tolerance. A report gate
rejects unsupported claims; it never replaces them with a fabricated model
answer. Original model arguments and all rejections remain in the event ledger.

Plain and JSON error representations carry the same facts and correction cap.
All native reads, writes, failed read reservations and automatic verification
consume a shared pre-dispatch operation budget. Model-request limits and a hard
wall-clock deadline are enforced by the evaluation runner, not this library's
native-operation budget alone.

Controlled stops derive from Exception so normal LangChain tool-error callbacks
close. Async cancellation waits for the bounded synchronous transport operation
and its callbacks to finish before propagating cancellation; it does not leave
an unobserved write running. Transport implementations must therefore enforce
their own finite I/O timeouts. Optional explicit OpenTelemetry spans close even
on BaseException paths and can be reconciled with raw operation records.

`ros_joint.JointTransport` and `sim/` demonstrate a fixed-base, one-joint Gazebo
fixture using ROS 2 Jazzy and Gazebo Harmonic. The application command range is
[-0.6, 0.6] radians; the simulated joint has wider mechanical limits. A separate
read-only subscriber observes actual joint state. This is a limited integration
fixture, not a full arm, grasping task, hardware driver or safety certification.

Validated environment: Python 3.12, existing research uv environment. Runtime
components live here; protocols, independent scoring, traces, raw trials and
the runnable Gazebo demo live in the sibling rosa-evaluation repository.
