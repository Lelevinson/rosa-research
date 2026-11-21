# `member/martin` (research repository `origin`), read 2026-11-21

Reported evidence, read from the branch tree with `git show`; nothing run. Head `8713f9b` (2026-11-20 18:33:42 +0800), author martin, 6 commits on top of `18a5f2f` (our fork's 2026-10-20 base; `member/martin` does not contain our research branch, steady loop, scorer or studies). 73 files, +6,452 lines (mostly `src/rosa_reliability/`, `src/rosa_auth/`, `src/rosa_backends/`, `tests/`, `docs/`).

## Problem targeted
Reliability and efficiency of ROSA through reusable software, no model training (`PROJECT_VISION.md`, 2026-10-22): do structured validation feedback and automatic fresh outcome verification improve verified task completion and reduce unsupported success claims beyond clear instructions and ordinary bounded retries (stated as the candidate question, "not a promise that either mechanism will help"). Robot target: a UR5e arm in Gazebo (`src/rosa_reliability/sim/`, `ur5e_macro_demo.py`, `gazebo_demo.py`, a one-joint fixture).

## Mechanism (from `docs/MACRO_MODULE_V1_SPEC.md`, `docs/MACRO_CAPABILITIES_V2_README.md`, `src/rosa_reliability/README.md`)
- **Inputs:** a catalogue of application-registered skills: `StateSkill(skill_id, targets={node: {joint: value}})` (a named numeric pose, one write at most) and `InspectionSkill(skill_id, subject, checks=...)` (read-only readiness check). Targets are bound and validated by application code at registration; the model supplies only a `skill_id`.
- **Tools the model sees:** the same five tools in both modes (`select_skill`, `read_state`, `write_state`, `verify_outcome`, `submit_report`, per the spec's "exact five-tool registry"); in macro mode `select_skill` starts a Python routine: read, conditional write, fresh verification; in comparison ("primitive") mode the model drives the primitives itself.
- **Trigger and output:** the model selects one skill; Python performs bundled read / conditional write / verify; the model still classifies SUCCESS / FAILURE / UNKNOWN and cites the latest observation ID in `submit_report`. A report gate rejects reports not supported by a fresh verification and canonical IDs; an accepted report ends the run without another inference. Uncertain dispatch is never replayed; a write needs known state.
- **Budgets and guards:** `MacroLimits` (native operations, tool attempts, corrections, time), at most one write per invocation, `validate_write` hook, evidence invalidation after writes, permission and reservation accounting (`ExecutionSession`, `EvidenceSession`).
- **Other parts:** remembered ChatGPT OAuth with rotating credentials (`src/rosa_auth/`, `docs/REMEMBERED_CHATGPT_AUTH.md`); `rosa_backends/` (Ollama and hosted back ends, observation cache); an opt-in `native-schema-v1` Ollama profile adding model-native tool-format guidance and persistent schemas for `llama3.1` and `granite3.3` only; Windows/WSL helper scripts.

## Code location, build and test state
`src/rosa_reliability/` (`bounded_macro.py`, `capabilities.py`, `completion.py`, `execution.py`, `evidence.py`, `workflow.py`, `terminal.py`, `macro_agent.py`, demos); tests in `tests/` (`test_bounded_macro.py`, `test_capabilities.py`, `test_macro_agent.py`, `test_reliability.py`, `test_evidence.py`, `test_siwc*.py`, ...). Built; scripted and deterministic tests exist. The spec says scripted checks "do not establish fresh live Qwen/Sol performance" and that M1 stopped before live studies.

## Reported results (as reported; not rerun by us)
The branch tree contains **no results files, run counts or tables**. The docs say: M1 validated scripted/Gazebo transports and rejection paths; M2/M3 harnesses and independent scoring live in the sibling repository `rosa-evaluation` (`experiments/macro_capabilities_v2`), which we did not read; the 2026-11-20 commit message states the native-schema profile was "used by the 2026-11-17 Llama/Granite native-schema Gazebo rerun". The earlier Stage 4 note in `PROJECT_VISION.md` reports that original JTVR "did not outperform strong amortized batching" and that a live selection screen "did not demonstrate useful end-to-end benefit". No tasks, models, seeds or episode counts for a live comparison are stated in the tree. `README.md` states results from this branch "must be labeled as a modified ROSA fork".

## Rules check against our contract ([PAPER_GOAL_CONTRACT.md](../PAPER_GOAL_CONTRACT.md))
- Per-task / per-application maps: **a hand-registered application catalogue is part of the design** (named skills with fixed target poses or checks; "application authorizes the catalogue"). Whether this is an "adapter" in the sense of the contract's taboo is the owner's decision.
- Training-free / plug-and-play: yes (no training; opt-in module; modified ROSA fork, so not drop-in on original ROSA).
- Read-only / guarded: guarded, not read-only (one write per invocation, validation hook, budgets, no replay after uncertain dispatch).
- Strong-baseline comparison: the design has a same-tools primitive mode; no comparison with original ROSA, our steady loop, or published baselines (MetaTool, Forge) is in the tree.
- Held-out data: none seen in the tree; no exam or held-out material is referenced.
- Scope: action tasks on a simulated arm (UR5e), not our inspection tasks or TurtleBot3/Nav2.

## Closest of our own studies and the concrete difference (descriptive, no novelty claim)
- [Guarded action tool S1](../studies/action_tool_s1_20261118/DESIGN.md) and [S2 turtlesim](../studies/action_tool_s2_20261118/REPORT_S2.md), and the [turtlesim dev action study](../studies/action_dev_switch_20261118/REPORT.md): ours are an executor-level guard plus an independently read final state on turtlesim with free-form tool use; his is a named-skill catalogue with Python-run read/write/verify bundles and a report gate on UR5e.
- [Finish gate check](../decisions/2026-11-17-finish-gate-check.md) (we did not add a gate) vs his accepted-report gate (rejects reports without a fresh verification).
- Differences in base: his branch is on the 2026-10-20 fork; ours has the 12-tool steady loop, scorer v2.0, frozen protocols.

## Loss-map class and size
Our [loss map](../studies/loss_map_20261120/REPORT.md) classes (format, repeat, name_guess, serial batchable, unsupported conclusions) come from **inspection** tasks on the 12-tool menu. His mechanism acts on action tasks (write, verify, report). **Not estimable** from our saved traces without running anything. Our turtlesim action traces (128 episodes) would be the nearest data, but they were not analysed for this.

## Relevance to Sunday's exam
None found: no exam, queue, lab or task-pool material, and the native-schema profile rejects our four model families.
