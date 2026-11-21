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

`rosa-llm`/`ChatRosaLLM` provides reusable ChatGPT OAuth and Ollama access through ROSA's `llm` interface. It is infrastructure, not a research contribution or JTVR.

Before changing model setup, consult the historical workflow guide and dated handoff identified below for integration paths, pinned version, Python/Jazzy requirements, legacy defaults and provider-setting limits; verify current integration details.

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
- Always communicate in English in agent responses, technical discussions, code reviews, and research reports, unless the user explicitly requests another language.
- End substantial coding or research tasks with a concise English explanation covering:
  1. What changed and why.
  2. Important code locations, with exact file paths and function names.
  3. How execution flows through those files.
  4. What was actually tested, the results, and what those results establish.
  5. Remaining uncertainty and limitations.

## Mandatory research context and preflight

Before any new ROSA research proposal, substantial research decision, algorithm implementation, or experiment, read Sections 0–4, 12 and 14 of the canonical [research context and decision log](research/ROSA_RESEARCH_CONTEXT.md), relevant later updates, the latest relevant results, and the closest negative experiment. Apply all gates, including all five questions in Section 12.2 and the decision record in Section 14.2. Retrieve other relevant sections and evidence as needed; the entire document need not be loaded. Preserve all applicable requirements and historical evidence.

Record the observed opportunity and its evidence, candidate/control action difference, closest prior mechanisms, fair evaluation and costs, and the smallest decision-changing next action with its stop rule. If a material prerequisite is unknown or contradicted, mark it `BLOCKED / NOT YET JUSTIFIED` and do not start major implementation or model benchmarking. A narrowly scoped diagnostic may proceed only when it can reverse a concrete decision, under a frozen protocol and small resource cap, with the necessary authorization. A description in the context is not authorization to run or implement it. Follow the user's current task scope and higher-priority instructions.

Update the canonical record after significant findings while retaining earlier evidence, and do not assume a local edit updates a ChatGPT Project source. These instructions require a preflight; they do not automatically verify the reasoning.

The historical `research/README.md` and `research/internal/NEXT_STEPS.md` are absent from this checkout. Use the [research entrypoint](research/START_HERE.md) and study index to locate their preserved copies. If local paths need resolution, consult the optional `research/.local/WORKSPACE_MAP.md`. Treat the copies as historical guidance and verify current integration and package details.

## Research knowledge navigation and agent coordination

- Default: read applicable instructions here, [research/START_HERE.md](research/START_HERE.md), and [research/ACTIVE_STATE.md](research/ACTIVE_STATE.md). Load the smallest additional context needed for the actual task.
- Search indexes before opening large files. Select relevant sections, source, tests, protocols and evidence; do not indiscriminately load research directories, archives or historical trees. Use `research/.local/WORKSPACE_MAP.md` only when local path resolution or historical discovery requires it, if available.
- For new research, apply the mandatory preflight above. Check closest prior failures, original literature, strong ordinary baselines, and a concrete incremental difference before proposing an algorithm. Distinguish verified evidence, reported findings, hypotheses and proposals; independently review important claims.
- Preserve raw evidence, reproducibility, failures and provenance. Update active notes only for material changes and link dated decisions. Coordinate a single writer for shared research state; inspect Git status and diffs, including untracked files. Local files do not synchronize external AI project sources.
- Treat investigation, prototype implementation, experiment execution, independent review and framework integration as distinct phases. The current user request must authorize each phase it covers; an authorization may cover multiple phases, but do not infer permission for another phase. Framework integration requires explicit authorization.
- For study reuse, new study and run locations, evidence ownership, reviewer handoff and status changes, follow the existing [research entrypoint](research/START_HERE.md). Preserve legacy evidence and its original paths and manifests.
- Claude Project context mirror: after finishing all edits to mirrored Markdown (`research/` core files, `literature/`, `decisions/`, `studies/` reports, `docs/START_HERE.md`), run `rosa-context-sync` once, not after each save. Skip it if no mirrored file changed. Report any sync error instead of claiming the mirror is current. Never copy raw evidence, archives, secrets or excluded files into the mirror.

## Shared team research context (`Lelevinson/rosa-contexts`)

`rosa-research` remains the authoritative source for this member's research.
The public `rosa-contexts` repository is a read-only published mirror for
teammates. Its `main` branch owns the shared protocol; each member owns only
their `member/<name>` branch. Never edit another member's branch or treat their
reported results as independently verified.

### Before substantial research work

- Read this repository's [research entrypoint](research/START_HERE.md),
  [active state](research/ACTIVE_STATE.md), and relevant decisions and study
  reports first.
- Fetch `rosa-contexts` references and inspect available `member/*` branches.
  Read the member entrypoint, active state, and synchronization manifest with
  `git show`; do not check out another member's branch over this working tree.
- Check for active overlap and prior negative results. Tell the user when a
  teammate is pursuing the same question or reports conflicting evidence.
- Treat a teammate's report as reported evidence until its sources and original
  evidence have been independently checked. Reading a branch does not prohibit
  independent replication.

### During research and after meaningful progress

- Keep local research files authoritative. Preserve existing research gates,
  provenance, negative results, and authorization boundaries.
- After a meaningful change in findings, decisions, failures, or active status,
  update the appropriate local research documents and cite the source revision
  and evidence. Do not duplicate a narrative solely for the shared repository.
- Publish only after meaningful context changes. In the `rosa-contexts` clone,
  switch to `member/levinson`, merge protocol updates from `origin/main`, run
  the manifest-based sync helper in preview mode, inspect its proposed diff,
  then apply it. Review the public diff and secret scan before committing and
  pushing. The helper never commits or pushes for you.
- The detailed commands and deletion, conflict, and privacy rules are in the
  shared repository's `PROTOCOL.md`.

### Operational safeguards

- Do not publish credentials, personal data, local machine maps, raw traces,
  archives, or other private artifacts. Redactions change only the published
  copy; local source files remain untouched.
- Do not merge research conclusions across members or modify teammate branches.
- Do not claim a sync or push succeeded until the remote branch head is checked.
- Do not make routine coding tasks wait for a full teammate-context review, and
  do not run an experiment merely to refresh the shared context.
