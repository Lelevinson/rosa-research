# ROSA codebase guide

ROSA connects a language model to robot and system tools through LangChain.
Start with the project [setup](../README.md), then inspect the code for your task.

- `src/rosa/rosa.py`: `ROSA` constructs the tool-calling agent and executor;
  `invoke()` runs a query and `astream()` streams agent events.
- `src/rosa/prompts.py`: default robot system prompts.
- `src/rosa/tools/__init__.py`: `ROSATools` assembles registered tools.
- `src/rosa/tools/ros2.py`, `ros1.py`, `system.py`, `calculation.py`, and
  `log.py`: framework tool implementations.
- `tests/test_rosa/`: production agent, prompt, and tool tests. Use the test
  command in the project README; tests alone do not establish robot success.
- `research/studies/`: study-specific designs, prototypes, protocols, tests,
  and reports, including historical work. Study code is not automatically
  registered as production ROSA components.
  Shared tracing and evaluation infrastructure belongs in `rosa-evaluation`.

For research, begin at [research/START_HERE.md](../research/START_HERE.md).
The [study index](../research/STUDY_INDEX.md) links each study's execution
instructions, evidence, conclusions, and limits. Run a study only when its
protocol and current authorization permit it. The research tree is local-only
and must be supplied separately to a fresh Git checkout.
