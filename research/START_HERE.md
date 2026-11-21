# Research knowledge entrypoint

For any task, read applicable [agent instructions](../AGENTS.md) and [active state](ACTIVE_STATE.md). This is Level 1: do not automatically load the canonical history, rules, literature or studies. Use the smallest sufficient context and inspect indexes before opening large files.

## Level 2: task-specific context

- **Software:** relevant source, tests and coding conventions; use [codebase guide](../docs/START_HERE.md) when useful.
- **Historical investigation:** locate the particular study in [study index](STUDY_INDEX.md), then read its relevant decisions, report, protocol and original evidence as needed. Reports are not raw evidence.
- **Literature:** start with [taxonomy](literature/README.md) and [prior-art matrix](literature/PRIOR_ART_MATRIX.md), then inspect only the relevant original sources and paper notes.
- **Evaluation:** load [research rules](RESEARCH_RULES.md), the applicable protocol, comparators, implementation and evidence; a previous proposed run is not authorization.

## Level 3: research proposals, substantial decisions, implementations and experiments

Apply the complete mandatory preflight in [AGENTS.md](../AGENTS.md): read canonical [context](ROSA_RESEARCH_CONTEXT.md) §§0–4, 12 and 14, applicable later updates, latest relevant results and the closest negative study. Read the complete five-question gate in §12.2 and make the decision record in §14.2. Independently check the closest prior mechanisms, ordinary controls, primary literature and original evidence as necessary. Retrieve other sections when relevant; do not assume a summary exhausts the canonical requirements. A material unknown or contradiction is **BLOCKED / NOT YET JUSTIFIED**.

## Study lifecycle and storage

- Search the study index and nearest prior work before creating a workspace. Reuse an existing study when the question and provenance fit; otherwise, when the current request authorizes creating files, use `research/studies/<topic>_YYYYMMDD/` with a concise, unique topic and the actual start date. Retain existing historical names. Keep study-specific design, implementation, focused tests, protocols, analysis and reviews together; create only the files needed.
- Investigation, implementation, experiment execution, independent review and production integration have distinct authorization boundaries. A request may authorize several at once; one phase alone does not authorize another. Explicit authorization is required before integrating an algorithm into `src/rosa/`; framework tests belong in `tests/`, general developer guidance in `docs/`, and shared tracing/evaluation infrastructure in sibling `rosa-evaluation`.
- For an authorized run with substantial outputs, use `research/_artifacts/runs/<study-id>/<run-id>/`. Choose a unique run ID, for example `<purpose>_YYYYMMDDThhmmssZ` in UTC with a suffix on collision. Create it only when needed; never overwrite a prior run. Small evidence may stay in its study when justified. Record input and output locations, raw traces, metrics, failures, protocol and revisions, source revision and dirty changes, dependencies, environment, model settings, seeds, costs and hashes as applicable. Keep original inputs and frozen evidence immutable; link an authoritative copy rather than duplicating it. Exclude credentials and document any unavailable provenance.
- Record study-specific findings and decisions with that study; index status and evidence in `STUDY_INDEX.md`. Failed, historical, continued or revisited studies retain their IDs and locations. New work uses a separately identified revision or run; do not overwrite prior protocols, results or negative evidence. Consequential cross-study decisions belong in `decisions/` only when a study ledger cannot serve.
- An independent reviewer reads original evidence and the exact reviewed revision, records scope, findings, disagreements and limitations in an existing appropriate review record or a separate attributed review when needed, and does not overwrite the author's work. One designated writer integrates shared-index or state changes after review.
- Retain historical `results/`, `evidence/`, `artifacts/`, `backup/`, review ZIPs and frozen manifests at their existing paths where reproduction depends on them. Identical bytes do not establish that two files have the same provenance or are safe to delete. Do not delete evidence or backups without verified independent recoverability; a same-filesystem copy is not independent disaster recovery.
- Treat `_artifacts/ROSA_KNOWLEDGE_MIGRATION_REVIEW_20261112.zip` as private: its embedded preservation tar includes an environment-file name and a private-configuration path. This is a member-name finding, not a contents inspection. Do not redistribute it without an explicit privacy review.

[Decision records](decisions/README.md) and [migration report](_artifacts/knowledge_migration_20261112/MIGRATION_REPORT.md) preserve historical context. If local historical paths need resolution, consult `research/.local/WORKSPACE_MAP.md` if available; it is optional machine-specific context, never default. Coordinate shared-state edits and inspect diffs. Local files do not automatically update other AI project sources.

## Maintain knowledge only when warranted

- After a meaningful change to current research state, replace superseded text
  in [ACTIVE_STATE.md](ACTIVE_STATE.md), date the snapshot, and link evidence;
  do not append a journal.
- Update [STUDY_INDEX.md](STUDY_INDEX.md) when a study's status, location, or
  evidence changes. Keep results, code, protocols, and study-specific decisions
  in the relevant `studies/` bundle. Preserve frozen versions and failures.
- Record consequential cross-study decisions or revisions in `decisions/` only
  when the study ledger cannot serve; link rather than duplicate the ledger.
- Update `literature/` when a source is meaningfully investigated or prior-art
  understanding changes. Update the canonical context after significant research
  developments, retaining its history, negative results, and mandatory gates.
- Change `RESEARCH_RULES.md` only when stable requirements change, and
  `docs/START_HERE.md` when general architecture or developer guidance changes.
  Routine debugging, minor edits, and exploratory discussion need no automatic
  research-document update.

Claude Code and Codex use the same files. Assign one writer for shared state;
independent reviewers inspect original evidence and report disagreements without
silently overwriting the author's results. Ignored research files and untracked
instructions do not travel with a Git clone; transfer and verify an authorized
copy separately. Historical study paths and original source snapshots are
described in the [study index](STUDY_INDEX.md).

## Context maintenance

- **Size budgets (approximate):** `ACTIVE_STATE.md` under 40 lines, this file under 60, `STUDY_INDEX.md` one row per study, [`CONTEXT_DIGEST.md`](CONTEXT_DIGEST.md) under 80. Replace text; do not append journals. Move detail to the study bundle and link it.
- **Digest:** agents may read it instead of the 720-line canonical file for orientation only. It never replaces the mandatory preflight in `AGENTS.md`. Every digest section has a "last verified" date; refresh it only after re-checking the linked source.
- **Staleness check at the start of each study:** compare the newest study folder with the state files, e.g. `ls -dt research/studies/*/ | head -1` against `stat -c '%y %n' research/ACTIVE_STATE.md research/STUDY_INDEX.md research/CONTEXT_DIGEST.md`. If the folder is newer, update the files before relying on them.
- **One writer at a time** per shared file; update only after a material state change, not after routine edits.
- **External Project sources:** `rosa-context-sync` mirrors Markdown to a local Windows folder (log: `~/.local/state/rosa-context-sync/sync.log`). Uploading to Claude or ChatGPT Project sources is manual and not done by any script.
