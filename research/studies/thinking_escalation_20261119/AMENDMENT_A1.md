# Amendment A1 to the thinking-escalation protocol (dated 2026-11-19, before any full-run episode)

Owner's instruction of 2026-11-19 (GPU schedule is the owner's; the owner gives the go). The frozen [PROTOCOL.md](PROTOCOL.md) (revision R1, SHA-256 `0e9fbdf6dc499a61aa1ec1285a8824d240cfd54de26f8b514697cb7e8a9d49a5`) is **unchanged**; this amendment changes only how the 240 planned episodes are split over time and sessions. Nothing has been run beyond the 12-episode smoke (clean, 122 checks; one session re-run because of an oracle first-read flake before any episode). No scoring rule, trigger, window, level, bar or class changes.

## What changes
- **Part A (first run): FULL against FULL+ESCALATE**, 10 dev tasks x 4 models x seeds 1-2 x 2 arms = **160 episodes**. One fixture session per (model, environment) as frozen (8 sessions); **the two arms and both seeds of a session are shuffled together** (master seed 20261125, shuffle key now includes the part name, so the shuffles and the manifest differ from the original 3-arm plan).
- **Part B (later, only after the owner's separate go): FULL+ALWAYS**, same 10 tasks x 4 models x seeds 1-2 = **80 episodes**, in **separate sessions** (one per model and environment, seeds shuffled together). It is a ceiling and cost reference, not a candidate.
- Everything else of the protocol (arms' definitions, trigger classes, window of 2, levels True / "high" for gpt-oss, settings including the 240 s HTTP and 1,800 s episode limits, measurements, reading rule, power note) is unchanged.

## Consequences for reading (stated before the run)
1. **The class of the candidate (A-D, section 5) is decided inside part A only**: `ESCALATE` against `FULL`, same sessions, same time window, same Ollama state: concurrent controls as in every earlier study. Part A can be reported before part B exists; the report then says "C0 headroom not evaluated".
2. **ALWAYS runs in different sessions, later**. Anything compared with `ALWAYS` (the C0 headroom reading `ALWAYS - FULL >= 4 cells`, tokens and wall time of `ALWAYS`) is a **cross-session comparison**: different fixture restarts, model load state, possibly different thermal and background conditions on the laptop, a different day. The same loop scored 35, 36, 32 and 32 of 40 in different sessions (dev noise, about 4 cells of 40), so differences of that size between `ALWAYS` and `FULL` cannot be separated from session effects. The report must state the session difference next to every number that uses `ALWAYS`, and `ALWAYS` figures are descriptive (no class).
3. Wall-time and token comparisons between `ESCALATE` and `FULL` stay concurrent; those with `ALWAYS` do not.
4. The smoke covered all three arms with the unchanged arm code; it is not repeated for the split.

## Code changes made for the amendment (GPU not used)
`run_think.py`: new phases `partA` (arms FULL, ESCALATE) and `partB` (arm ALWAYS) in `plan_for`; smoke unchanged (its manifest hash is identical to the frozen one). `analyze_think.py`: phase `full` reads `partA` and `partB` rows; when no `ALWAYS` rows exist, C0 and the ALWAYS difference are `null` and the class is still computed. `tests/test_analyze_think.py`: one added test (20 tests pass). `make_freeze.py`: records the part A and part B manifests; the earlier freeze is kept as `FREEZE_BEFORE_A1.json`. New hashes: `FREEZE.json` and `AMENDMENT_A1.sha256`.
