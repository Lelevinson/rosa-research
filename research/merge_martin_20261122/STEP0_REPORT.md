# Step 0 report: GO / NO-GO on the possible saving (2026-11-21, Session B)

Rule, threshold (T = 25%) and definitions: [STEP0_GATE_PREREG.md](STEP0_GATE_PREREG.md), committed **before** measuring (c63a509, SHA-256 f7306c40…be61).
Script: `step0/size_bundle.py` (stdlib, read-only). Output: `step0/step0_results.json`. Data: his public dev rows (`action_dev_switch_20261118/RESULTS_LOG.jsonl`, reported evidence, not rerun).
This concerns the **new parameterized variant `rotate_verified(theta)`**. No M4/G1/D evidence is claimed for it. Zero model calls.

## Result: **GO, exactly at the threshold**
| Control rows (arm OFF, full phase) | Episodes | Requests | Removable pose-read requests | U |
|---|---:|---:|---:|---:|
| qwen3.5:9b | 16 | 56 | 14 | **25.0%** |
| all four models pooled | 64 | 216 | 54 | **25.0%** |
| Conservative R (R2 reads not counted) | qwen 16 / pooled 64 | 56 / 216 | 12 / 46 | 21.4% / 21.3% |
Per model U: bonsai 26.5%, gpt-oss 23.6%, lfm3 25.0%, qwen3.5 25.0%. Per task (pooled): S1 33%, S2 33%, R2 36%, M1 27%, M2 27%, S3 21%, M3 20%, R1 7%. Sensitivity (arm ON): qwen 23.6%, pooled 20.7%. No infrastructure rows excluded.

By the frozen rule (U ≥ 25% for qwen and pooled) the decision is **GO**. I did not change the rule or the data selection.

## What this does and does not say (honest reading)
- **It is an upper bound.** It assumes the bundle removes every post-goal pose read, at no extra cost, and that the model then does not read the pose anyway. His own report notes models read the pose even when it is shown (R2).
- **The conservative figure is below T** (21%), and the ON arm is lower (21-24%). So GO is marginal. The honest expectation is a saving **below 25%**.
- **The saving is concentrated in the rotate-then-check tasks** (S1, S2, S3, R2, M1-M3). R1 has almost none. M1-M3 only count if the bundle can be called more than once (decision D-M3).
- **A signal run cannot confirm a saving this small.** His own noise floor is about 21% at 64 episodes per arm; the planned run has 16 per arm per model (about 42% for one model, about 24% for three). A signal run can only show whether a large saving appears, whether adoption works, and whether success and safety hold.
- Mixed in the pre-registered design: no claim from this step. It only says a signal run is not pointless.

## Step 2, in-tree part only (no private modules)
His S1 executor tests, run unchanged from the merge worktree (Python 3.14.3, pytest 9.1.1): **19 passed**, equal to his reported count.
Not run: the turtlesim backend tests (need ROS), `test_exam_actions`/`test_exam_arms`/`test_queue` (need his missing modules).

## Still open
- **L3** (who runs the identity check) and **L4** (can his judge count a pose read inside the bundle) were left as unresolved placeholders in the instruction. L3 blocks steps 2-3 (the part that needs his private modules). **L4 blocks step 6.**
- Next in scope without them: step 3 recorder script (for him to run), step 4 protocol, then **STOP POINT 3**: Martin and Levinson read the protocol.
