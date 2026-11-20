# Bounded workflow prototype (2026-10-22)

The guiding vision in PROJECT_VISION.md is unchanged: improve ROSA's reliability
and efficiency through reusable software, without training a model. This
prospective milestone follows the completed output-budget investigation; it
does not reopen Stage 4 or alter any frozen results.

The opt-in implementation lives in `src/rosa_reliability/terminal.py` and
`workflow.py`. The normal ROSA class, previous tools and previous experiments
keep their existing behavior. This prototype supports synchronous invoke only.

```python
from rosa_reliability.terminal import AcceptedReportROSA
from rosa_reliability.workflow import WorkflowSession, make_workflow_tools

# Supply a bounded transport with read(node, names), write(node, values), and
# the same validation/observation safeguards used by the reference condition.
# Catalogue contents must be explicitly authorized for this task/session.
session = WorkflowSession(
    transport,
    {'inspect_station': {'/arm': {'joint_a': 0.2, 'joint_b': -0.1}}},
    program_managed=True,  # False is the model-managed reference.
    operation_limit=10, tool_limit=16, validation_limit=3, seconds=180,
)
agent = AcceptedReportROSA(
    2, llm, terminal_session=session, tools=make_workflow_tools(session),
    load_default_tools=False, accumulate_chat_history=False, max_iterations=8,
)
result = agent.invoke(task_with_public_catalogue_and_execution_instructions)
```

The model must receive the public catalogue, goal, execution condition and
limits in its task instructions. It selects one permitted skill. In the
candidate, ROSA performs read / conditional write / fresh verification through
the SAME bounded primitives. Unknown evidence, rejected prerequisites and
unconfirmed outcomes escalate without automatic command replay. The model still
classifies and submits observed values. An accepted validated report terminates
without an extra inference; rejected reports remain correctable.

Use a fresh session per task, bounded native transports and an external wall
timeout for live experiments: the operation ledger prevents expired dispatches
but cannot itself interrupt an in-flight blocking transport or model request.
Provider-level token limits and a cumulative inference meter must also be
configured in a live runner. No credential handling or provider options are
changed here. Existing OAuth consent/cleanup and backend configurations remain
in force. The module does not establish collision avoidance or robot safety.

See the evaluation repo's `docs/WORKFLOW_V1_DEVELOPMENT_2026-10-22.md` for decision
ownership and scientific limits; `experiments/workflow_v1/pilot.py` for scripted
feasibility cases. Scripted tests do not establish gains for Qwen or Sol.
