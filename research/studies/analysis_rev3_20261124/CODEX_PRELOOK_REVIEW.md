# Independent Stage 1 analysis review, November 24, 2026

**Hold the first result review.** This applies to the candidate wrapper with
Git blob 382d68369808ee89bb4bb2f57523777629289880. I read the code and ran
its 14 tests, which all passed. I ran four additional end-to-end checks using
the public dummy spec. All four checks passed inconsistent records through the
gate. I used synthetic files outside both Stage 1 runs.

On coherent synthetic inputs I confirmed the whole-plan cross-tier orphan
check, plan-derived pair counts, the pre-start cohort check, and the switch to
the applied queue module. The paired exclusion and worst-case assignments
match the owner decision for ordinary single-sided and double-sided skips.
[Owner decision](../../decisions/2026-11-23-stage1-quarantined-cells.md)

1. **Validate task and machine identity.** In separate synthetic copies,
   changing one compact row's task or its machine kept the gate open. Each
   command exited 0 and reported five primary pairs against six planned. The
   sensitivity still used six pairs. The frozen analyzer groups by the task
   field and filters by the machine field. Validate both fields before
   invoking it. A denominator mismatch must block the comparison.
2. **Validate the compact comparison fields against the accepted full row.**
   Flipping one synthetic compact supported flag without changing its full
   row passed the gate. The analyzer reported FINAL and counted five supported
   primary cells where the full rows recorded six. The gate currently retains
   only full row IDs, so it cannot detect this mismatch. Use the existing
   custody compaction and compatibility rules to validate the fields consumed
   by analysis. Keep the check command outcome-blind and put the outcome
   comparison behind the authorized complete-tier analysis gate.
3. **Resolve an individual quarantine that also has a completed row.** Adding
   one explicit individual quarantine to a synthetic completed cell left the
   gate open and excluded zero pairs. The skip builder removes finished cells
   before the validator checks for an overlap. Block a conflicting individual
   quarantine until adjudicated. Previously completed cells in a block group
   that was later quarantined can still be valid completed observations.

I made no changes to the candidate wrapper or the frozen Stage 1 software.
The checks establish behavior on the identified candidate bytes and synthetic
inputs. They provide no Stage 1 results.
