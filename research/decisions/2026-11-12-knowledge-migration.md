# Decision: add an index layer without relocating studies

Date: 2026-11-12. Scope: research infrastructure migration; no new scientific decision or experiment.

**Problem:** the canonical context is cumulative and contains date-sensitive recommendations; evidence and scripts refer to current and sibling paths; older study files are outside this checkout. Existing research and AGENTS.md were untracked at migration start.

**Decision:** retain the canonical context and original study bytes and paths. Add a compact dated state, stable rules, evidence-aware index, literature navigation and manifest. Keep the canonical preflight intact and maintain the existing requirement to update it after significant findings. Historical reports and input snapshots remain historical, not current instructions. No copied summary replaces raw evidence. See [migration report](../_artifacts/knowledge_migration_20261112/MIGRATION_REPORT.md) for unresolved limits and [manifest](../_artifacts/knowledge_migration_20261112/MIGRATION_MANIFEST.md) for source mappings.

**Revisions:** a later state change replaces superseded active-summary text and adds a dated decision linked to its original evidence; it must not silently overwrite a historical decision or fabricate missing traces. This decision does not authorize experiments or make external Project Sources synchronized.
