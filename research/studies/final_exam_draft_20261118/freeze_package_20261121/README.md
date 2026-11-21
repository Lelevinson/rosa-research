# Stage 1 freeze package (DRAFT, 2026-11-21; nothing here is hashed or frozen)

| file | what it is |
|---|---|
| `make_exam_spec.py` | generator of the exam spec and cell counts (`write`, `counts`); no custodian file opened |
| `exam_spec_stage1_DRAFT.json` | generated spec: 4 tiers in the owner's laptop order, seeds 1-3, master seed 20261122 (draft value), pool from the custodian's file named by `ROSA_HELDOUT_V2_TASKS` |
| `MODEL_DIGESTS_DRAFT.json` | full digests of the 4 core and 3 extra models from the laptop Ollama (the 4 core digests equal those of `steady_loop_ablation_20261117/FREEZE.json`); the lab's copies are compared at the lab pre-run gate |
| `analyze_primary.py`, `analyze_primary.sha256`, `tests/`, `dev_check/` | **frozen analysis of the primary comparison** (supported-complete difference M minus E1, token ratio over all assigned episodes, task-clustered bootstrap 95% intervals with a fixed seed, the pass/fail rule of section 9c: lower bound above -5 points and upper bound below 0.80, per-model rows, the name fix scored both ways, the infrastructure-share invalidation check, strata never pooled). Its hash is recorded before any held-out result exists; 14 tests, including a recount on the public dev results (`dev_check/`, an exercise of the script, not evidence) |
| `FORGE_ENV.md` | persistent Forge interpreter path, pinned packages and check |
| `SUCCESS_AND_INVALIDATION_DRAFT.md` | the criteria and invalidation text of draft section 9c items 4 and 8 |

Expected cells with 76 tasks: tier 1 1,824; tier 2 (S0, F, MT) 2,736; tier 3 2,736; tier 4 1,368; total 8,664 (7,296 core + 1,368 extras). **Revision 2026-11-21 evening:** MT was added to tier 2 on the owner's instruction, which raises the core total of draft section 9c item 3 from 6,384 to 7,296 episodes (+912, about 9 laptop hours at dev speed; planning figure). F now has a queue adapter (`exam_arms_20261121/run_forge.py`, Forge in its isolated interpreter) and MT is the MetaTool mechanism ported from the released source; see the [baseline adapters report](../../exam_prep_20261121/REPORT_BASELINE_ADAPTERS.md).

**Still needed before hashing (not done here):** the custodian's manifest and held-out v2 task file (Codex), the hold-out adapter that lets `run_exam.py` score held-out ids (today it knows development tasks only), the final master seed, the git revision of the code, the freeze file listing file hashes (as the dev studies' `make_freeze.py` do), and the owner's confirmation of the text. Cell order inside a tier follows the queue's generic rule (seed, task shuffle, model, system shuffle in the pair); the dev studies' per-(model, environment) fixture-session grouping is **not** used and whether the exam needs it is open.

To hash after approval (a command, not run): `sha256sum exam_spec_stage1_DRAFT.json MODEL_DIGESTS_DRAFT.json SUCCESS_AND_INVALIDATION_DRAFT.md`.
