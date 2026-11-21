# Lab merged arm: short note (stretch goal), 2026-11-22, Session B

(Martin's instruction for this file was cut off after "what the"; this note covers what the lab merged arm would need and when it makes sense. Correct me if you meant something else.)

**Order agreed by the team:** Levinson's method first on the lab; "his + mine" as an extra arm only if time allows.

**What the merged arm would need before any lab run**
1. **Levinson's private harness** (`run_pilot`, `harness`, `ablation_arms`, `fair_arms`, `answer_gate`, `scorer_v2` are not public). He prefers to run the flag-off identity check himself (his reply, L3).
2. **Scorer visibility (L4):** his scorer does not see a read inside the bundle. The bundle must record its internal read with source and time in the event sequence, and this must be shown to work on a public dev task first. A pose read cannot replace a required read of another value (e.g. a background parameter).
3. **Task fidelity:** the bundle must not skip a step a task asks for (e.g. two turns in order). So it must be callable once per required action and must never "skip" a commanded write because the end state looks right.
4. **The fair control is his tool with the state line ON.** Against it, the possible saving on his public dev rows is 20.7% pooled (qwen3.5:9b 23.6%), cautious 16.7%: **below our pre-registered 25% gate** (`../merge_martin_20261122/STEP0_CALCULATION.md`). On current evidence the arm is not justified.
5. A frozen protocol in his style (spec, freeze file, results log, clustered bootstrap), its own stratum, added only before his Stage 2 freeze and with his agreement.

**Rough effort if all of that is agreed:** 20-30 h (my estimate), most of it on his side (harness, scorer, held-out custody).

**Recommendation:** run the UR5e demo (`DEMO_PLAN.md`) and present the two methods as separate strata on the lab. Add the merged arm only if a reason appears that the bundle changes model behavior beyond the state line, for example in tasks with failed or cancelled moves, and only on public dev tasks first.
