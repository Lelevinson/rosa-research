# ROSA Research Development Guidelines

This repository supports collaborative undergraduate research on NASA/JPL ROSA.
Students develop separate improvements on separate Git branches.
Prioritize readable, maintainable, scientifically rigorous code over architectural sophistication.
Write for students who did not write the original code.

## Scope and collaboration

- Inspect the current branch, working tree, relevant code, and applicable instructions before editing.
- Explain the intended change before changing files. Keep edits within the requested task.
- Respect teammates' branches and existing work. Do not overwrite unrelated changes or perform destructive Git operations without explicit authorization.
- Do not change the original ROSA baseline checkout. Make research changes in the research branch and preserve a reproducible baseline comparison.
- Keep shared instructions independent of any student's algorithm. Do not impose one branch's research design on other branches.
- Do not push or merge unless the user explicitly requests it.

## Readable Python

- Prefer simple, explicit Python with descriptive variable, function, and class names.
- Use ordinary conditionals for simple decisions. Keep important algorithmic decision rules visible and easy to locate.
- Avoid unnecessary patterns, factories, wrappers, inheritance, and indirection.
- Give each module one understandable responsibility. Group closely related logic when this improves readability.
- Avoid excessive file fragmentation. Preserve correctness and necessary modularity when choosing file boundaries.
- Explain non-obvious assumptions and reasons in comments. Do not merely restate the code.
- Handle relevant validation and errors explicitly. Do not hide failed operations behind apparent success.

## Understandable algorithms

- Separate algorithmic decisions from ROSA integration, evaluation, and error handling when this clarifies responsibilities.
- Document the objective, mathematical definitions, assumptions, and decision rules near the implementation or in one linked research document.
- Make decisions traceable from inputs through intermediate values to the selected action.
- Distinguish established methods, new hypotheses, and engineering choices. Do not present a simple heuristic as a novel contribution without evidence.

## Scientific practice

- Verify relevant prior art and citations against original sources. Mark unverified claims and uncertain novelty explicitly.
- State the hypothesis, controls, metrics, and success criteria before running a study.
- Design meaningful experiments alongside focused tests. Unit tests alone do not establish algorithm quality or robot task success.
- Compare against a reproducible baseline under matched conditions. Document unavoidable differences and their effects on interpretation.
- Record code revisions, dependencies, commands, model settings, ROS configuration, inputs, and seeds when applicable.
- Distinguish simulations, controlled fixtures, and live ROSA/LLM/ROS 2 runs. Limit conclusions to what the experiment actually measures.
- Preserve negative findings and failures. A requested tool call or a trace entry does not prove successful execution.
- Do not change scenarios or evaluation criteria to improve reported performance. Document legitimate protocol revisions and report their results separately.
- Prefer hypothesis-driven experiments over repeated speculative patches. Inspect actual errors and outputs before assigning a cause.

## Dependencies and artifacts

- Use `uv` for project dependencies and execution. Record dependency changes in `pyproject.toml` and the corresponding `uv.lock`.
- Keep virtual environments, secrets, temporary files, and large experiment traces out of Git.
- Retain compact results and enough metadata to reproduce findings. Document how to obtain any required external artifacts.
- Keep shared tracing and evaluation infrastructure in the sibling `rosa-evaluation` project. Keep branch-specific experiment drivers with their research code.

## LLM infrastructure

`rosa-llm`/`ChatRosaLLM` provides reusable ChatGPT OAuth and Ollama access through
ROSA's `llm` interface. It is infrastructure, not a research contribution or JTVR.
Before changing model setup, read the [workflow guide](research/README.md#use-rosa-llm-in-the-research-drivers)
and [dated handoff](research/internal/NEXT_STEPS.md) for integration paths, pinned
version, Python/Jazzy requirements, legacy defaults and provider-setting limits.
ROSA Research owns instrumentation, evidence scoring and experimental methodology.

## Documentation and navigation

- Maintain one concise, beginner-friendly codebase guide, preferably `docs/START_HERE.md`.
- Explain the main execution flow, important files and functions, and each file's responsibility.
- Identify algorithm implementations and explain their interactions with LangChain and ROS 2.
- Show how to run an experiment, inspect its outputs, and interpret its results and limitations.
- Update the guide when relevant behavior or navigation changes. Link existing research documents instead of duplicating them.
- Ensure Git tracks the guide. If an ignore rule excludes it, adjust only the relevant rule when adding the guide.

## Teaching and communication

- Act as a tutor and reviewer during learning tasks. Evaluate the user's reasoning honestly and identify errors, gaps, and uncertainty.
- Start unfamiliar concepts with a simple concrete example before terminology, mathematics, or code.
- Prefer a small hint or pseudocode before a complete solution. Provide complete code when requested or when the user is stuck.
- Distinguish Python syntax, framework behavior, database concepts, HTTP concepts, and business logic when relevant.
- Explain newly introduced terminal commands, subcommands, flags, and abbreviations, including how to read the full command.
- In reviews, explain current behavior and why a defect matters before suggesting a focused correction. Separate bugs from optional improvements.
- Consider security, validation, error handling, performance, and maintainability when relevant to the change.
- Keep source code and academic research documents in English.
- End substantial coding or research tasks with a conversational Indonesian explanation covering:
  1. What changed and why.
  2. Important code locations, with exact file paths and function names.
  3. How execution flows through those files.
  4. What was actually tested, the results, and what those results establish.
  5. Remaining uncertainty and limitations.


## Mandatory research context and preflight

Before any new ROSA research proposal, algorithm implementation, or experiment, read the canonical [research context and decision log](research/ROSA_RESEARCH_CONTEXT.md). Apply Sections 0, 12, and 14 as preflight decision gates, including the full five-question gate in Section 12.2 and the decision record in Section 14.2. Read Sections 0–4, the latest relevant results, and the closest negative experiment as Section 14 requires. Preserve all other applicable requirements and historical evidence.

Record the observed opportunity and its evidence, candidate/control action difference, closest prior mechanisms, fair evaluation and costs, and the smallest decision-changing next action with its stop rule. If a material prerequisite is unknown or contradicted, mark it `BLOCKED / NOT YET JUSTIFIED` and do not start major implementation or model benchmarking. A narrowly scoped diagnostic may proceed only when it can reverse a concrete decision, under a frozen protocol and small resource cap, with the necessary authorization. A description in the context is not authorization to run or implement it. Follow the user's current task scope and higher-priority instructions.

Update the canonical record after significant findings while retaining earlier evidence, and do not assume a local edit updates a ChatGPT Project source. These instructions require a preflight; they do not automatically verify the reasoning.

The historical `research/README.md` and `research/internal/NEXT_STEPS.md` links
in the LLM infrastructure guidance above are absent from this checkout. Their
preserved copies are in `/home/levinsonchen/project/rosa-research-previous-20261108/`
at those same relative paths. Consult them as historical guidance and verify
current integration and package details before relying on them.
