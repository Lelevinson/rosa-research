# Improved ROSA: guiding project vision

Recorded 2026-10-22 from the user's project clarification. This is a planning
record, not an experimental protocol or a claim of demonstrated improvement.

## Objective and deliverable

Improve the reliability and/or efficiency of the existing LLM-powered ROSA
framework through its software architecture. We are not developing or training
a new LLM. Prefer modular, reusable Python components that work with different
LLM backends.

An appropriate final deliverable is an improved ROSA implementation, a reusable
module or package, or a working experimental system with reproducible benchmarks
that demonstrate its benefits and limitations. A smaller, completed and tested
improvement is preferable to several unfinished research features.

## Candidate research directions

- Verification and reliability: check execution and task outcomes, recognize
  failure or uncertainty, and avoid unsupported success claims.
- Tool-calling optimization: acquire the required information and execute tools
  with fewer unnecessary native operations or inference calls.

These are possible directions, not obligations to build two large systems.
Choose one manageable question or a small combination based on evidence and the
scope of an undergraduate robotics project.

## Research objective and immediate candidate question

Investigate which changes to ROSA's tool execution, feedback and outcome
verification improve reliability and/or efficiency, by how much, at what cost,
and under which conditions. Investigate whether the tested local backend
benefits; do not assume framework changes eliminate differences in model
capability or generalize to all smaller models.

The immediate candidate question is: under fixed resource limits, do structured
validation feedback and automatic fresh outcome verification improve verified
task completion and reduce unsupported success claims beyond a consistent
interface, clear instructions and ordinary bounded retries?

Separate prerequisite engineering from the experiments that test this question.
The proposed comparison independently toggles structured feedback and automatic
verification, with all other safeguards and capabilities shared. This is a
research-design commitment to fair attribution, not a frozen live protocol or a
promise that either mechanism will help. A reproducible negative result can be
useful; novelty and generality require evidence and comparison with prior work.

## Algorithms are candidates, not commitments

JTVR is one proposed tool-selection method, not the project's identity. Preserve
the Stage 4 findings: original JTVR did not outperform strong amortized batching
on the tested acquisition workloads. The subsequent live selection screen did
not demonstrate useful end-to-end benefit from automatic batching over a
reference with the same batching capability; local reporting failures limit
what can be concluded about successful local workflows.

Keep full JTVR paused and batching optional. Verified episodic memory and more
sophisticated selection methods remain optional future extensions. Negative
findings are acceptable; use them to choose simpler or more useful approaches.

## Backend flexibility and fair attribution

Local Qwen3.5 9B through Ollama and the hosted OpenAI model through the existing
OAuth adapter remain valid evaluation backends. A paid API-key backend and model
training are not required deliverables.

Define the same sensible tool contract, validation rules, operation bounds and
verification requirements for both backends. Do not tune tool schemas merely
until one model passes. Report model-generated decisions separately from
automatic correction, additional verification or reporting performed by ROSA.
Credit recovered outcomes to the combined system.

## Current development order

1. Preserve existing experiments and document unresolved evaluation problems.
2. Complete a separate interface, recovery-tracing and operation-limit repair
   milestone. Use consistent retrieval/report structures and canonical IDs.
3. Validate the repairs prospectively with both backends, fresh cases and fair
   simpler controls. Keep individual intervention effects distinguishable.
4. Establish one deterministic bounded Gazebo skill with independent outcome
   verification before introducing an LLM into that simulated robot workflow.
5. Compare the same ROSA skills with both backends and a deterministic control.

This order takes priority over future work in the historical six-stage roadmap.
It does not reopen Stage 4 or make episodic memory a prerequisite for Gazebo.

## Evidence and repository boundaries

Reusable ROSA runtime changes belong in `rosa-research`. Benchmark protocols,
independent scorers, raw trial records, tracing audits and experiment reports
belong in `rosa-evaluation`. A dependency snapshot in an evidence archive does
not replace publishing the corresponding research implementation separately.

Preserve Baseline v1, frozen protocols, historical scores, source snapshots and
the Stage 4 audit exception. New engineering results need a distinct version and
prospective label. Evaluate reliability and efficiency separately: a useful
verification mechanism may add work, and a failed attempt's lower cost is not a
successful-task efficiency gain.

The user's clarification authorizes updating planning and recommendations. It
does not by itself authorize an immediate architectural rewrite or new model
experiments. No such implementation or experiment is recorded by this document.

Subsequent instruction on 2026-10-22 explicitly authorized completing the four
repair/validation/Gazebo/backend steps. That implementation is a separate
Reliability v1 milestone; the earlier clarification remains a historical record
of scope, not a restriction against the user's later authorization.
