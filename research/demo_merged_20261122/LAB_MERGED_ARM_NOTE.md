# Lab merged arm: short note, 2026-11-22 (updated, Session B)

**Team decision:** a demo of the merged method first. On the lab, Levinson runs his method first (1-2 days from Monday). Then the merged method is run for **real numbers**. The integration is built once, lab-ready.

**The 20.7% figure is an estimate, not a result.** It is the possible saving in model requests against his tool with the state line returned (arm ON), from his saved public dev rows: 42 of 203 requests pooled, qwen3.5:9b 13 of 55 (23.6%), cautious 16.7% (`../merge_martin_20261122/STEP0_CALCULATION.md`). It assumes the macro removes every post-move pose read at no cost. Only a run can settle it. The earlier recommendation against the arm is withdrawn.

**What the lab arm needs (and what the demo code already provides)**

| Need | Status |
|---|---|
| Scorer can see reads inside the bundle (L4) | **Built into the demo code.** Every transport call the macro makes is logged with source, actor, skill, global sequence number, parent tool-call sequence number, monotonic and wall times, arguments, result or error, and the macro's operation id (`merged_demo/skill_tool.py`, tests `test_skill_tool.py`). Still to prove on a public dev task with his scorer (his side). |
| A pose read must not replace a required read of a different value (e.g. a background parameter) | Reads inside the bundle are logged as `internal_read` with their own source; the model-visible menu reads stay separate. The scorer rule is his. |
| No skipped task steps | Each `run_skill` call is a fresh bounded invocation. The macro still skips a write when the fresh read is already within tolerance; this is **logged** (`write_skipped: already_within_tolerance`). A task that must see a movement even at target cannot be expressed with the macro, so such tasks are flagged, not silently scored. Movements per task are configurable (`max_writes`, default 1) for multi-step tasks, and a failed or unconfirmed write is never replayed across calls. |
| His private harness, prompt strings, `answer_gate.py` | Requested (`REQUEST_TO_LEVINSON.md`). Until they arrive the demo uses labelled substitutes ("M as described in his public docs, reimplemented"). |
| A parameterized skill for turtle-style tasks | **New variant, not built here.** The demo registers the UR5e catalogue (named poses). A `rotate_verified(theta)`-style skill is a different object: no M4/G1/D evidence is claimed for it. |
| Frozen protocol in his style, own stratum, before his Stage 2 freeze, his agreement | Open. |

**Order:** demo first; lab arm after his own runs, if time allows (stretch goal). Never pooled with his results or with M4/G1/D.
