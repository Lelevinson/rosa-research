# Codex: bounded, decision-changing next action — ROSA native-read scheduling

**Status:** Proposed narrow read-only research step, **not** permission to alter the ROSA environment or run model benchmarks. Read the companion technical report and the canonical context §§0, 12, 14 first.

## Decision to resolve

Do currently preserved original ROSA traces actually contain sufficiently frequent **multi-entity calls** to `ros2_node_info(nodes)`, `ros2_topic_info(topics)`, or `ros2_service_info(services)`, and do the per-item native executions consume material wall time? If not, do **not** implement an adaptive concurrency scheduler. The existence of list APIs and a serial Python for-loop is not by itself an efficiency result.

## Do this first, without running a new ROSA/LLM benchmark

1. Inspect Git HEAD/status, `AGENTS.md`, current ROSA source and installed package versions. Do not overwrite existing instructions, change branches destructively, push, or modify old evidence.
2. Locate actual durable original archives, especially `rosa-baseline-diagnostic-review-20261107.zip` and corresponding source/protocol/scorer. The supplied November 11 ZIP contains earlier reports and CPAW raw results, not those original baseline traces. Missing 64 `$ref` records are irretrievably missing; never reconstruct false events.
3. Verify archive SHA/manifest. Parse **only original event rows** into exact: `episode_id`, arm, tool_name, submitted list argument, width, native operation count, per-item starts/ends if present, reported tool output bytes, total episode time. Do not assign synthetic task/source semantics. Count denominators across all episodes including wrong/uncertain episodes and actual failed calls.
4. Write under a new durable, ignored `research/_artifacts/native_exec_preflight/<run_id>/`: original-read hashes, extraction script, `events.csv`, `incidence.json`, `REPORT.md`, manifest. Retain an independent backup; avoid `/tmp`.
5. Include evidence excerpts for at least three genuine eligible calls if present, and identify exactly which required event fields are not recorded. Do not silently estimate per-item durations from wrapper counts.

## Decision branches

- **No/rare multi-entity reads, or tiny critical-path share:** stop. No optimization implementation, no new generic diagnostic. Report cost opportunity absent for this sample.
- **Multi-entity reads material, but individual timing unobservable:** document missing instrumentation and request a *bounded native-only* timing design, using fixed literal observed input sets and the same read-only ROS fixture. No model call yet.
- **Material eligible reads and timing:** propose a tightly frozen native-only parity+cost test against serial, tuned fixed k=2/k=4, generic adaptive limiter, and persistent `rclpy` alternative. Same safe transport/arguments/timeouts, exact outputs and errors, no mutation. **Do not implement adaptive candidate solely because this gate passed**—the literature/simple-controls contrast still needs checking.

## Constraints

- Do not inject semantic task→endpoint/extraction mappings, handpicked benchmark answers or tool-equivalence labels.
- Do not change prompt behavior in one arm alone; replace the conflicting default one-at-a-time instruction in all optimized model arms before any eventual LLM test.
- Do not infer correctness from source-value equality or ROS graph presence. Full requested answer fields, correct source and omission remain scoring obligations.
- Keep original ROSA descriptive and truly optimized existing ROSA decisive. Do not compare only against the original serial/forbidden-batching prompt.
- No paid model calls; no mutators, motion tools, arbitrary `ros2_service_call`; don't trust tool names or return values as effect contracts without reviewing source.
- Every count is native ops + model requests/tokens + total episode time including policy overhead. Trace failure/uncertain outputs and do not relabel them.

## Required final return

One short **GO-TO-NATIVE-PARITY / STOP / INSUFFICIENT-LOGGING** decision with original trace denominators, three exact evidence excerpts or explicit absence, artifact hashes, strongest ordinary comparison and an honest explanation of whether the decision changes. Do not autonomously launch a 22-cell baseline rerun or a wider research mission.
