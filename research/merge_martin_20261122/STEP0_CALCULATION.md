# Step 0 calculation, in detail (answer to Levinson's questions), 2026-11-21, Session B

Status: **plan level only.** Levinson chose to keep the two studies separate for now. The merged arm is not built. Nothing here is a result for a merged method.
Data: his public dev rows, `research/studies/action_dev_switch_20261118/RESULTS_LOG.jsonl` (his snapshot 2b1c790; study frozen 2026-11-18 19:33 CST, protocol SHA-256 `5f899cbe…050b`; reported evidence, not rerun by us). 128 `full` rows (64 per arm). Script: `step0/size_bundle.py`; output `step0/step0_results.json`. All counts below were recomputed from the rows.

## 1. What the 25% and the ~21% count

**Unit counted:** model requests (`requests`: one per model response, including the final answer and rejected tries).
**Tool version compared against:** the dev study's own runner and tool (`run_action_study.py`): `rotate_to_heading` through the `ActionExecutor` with `TURTLESIM_POLICY`.
- **Arm OFF** = `ExecutorOptions.attach_post_action_state = False`. The result is only `SUCCEEDED/REJECTED/...`. This equals the `XM` default in `action_arms.py` (post-action state OFF). **The 25% and 21% are computed on OFF.**
- **Arm ON** = same tool, plus the line `State after action: heading <h> rad, position (<x>, <y>)` after any call that sent a goal (`PROTOCOL.md:7`). In my pre-registration ON was a sensitivity check only.
- `XM`, `XS0`, `XE1` were **not** run in the dev study. The numbers are not from those arms.

**Removable request** = one model request that is a `read_turtle_pose` call made **after a goal was sent** (the log's `verification_calls`). The macro would return the verified pose, so that request would not be needed. Rule: `removable = min(verification_calls, requests - 1)`. In the data this never clipped, and no episode has more than one such read. So removable = the number of episodes with a post-goal pose read.
- **Optimistic U** = all those reads. **Cautious R** = the same without the R2 episodes (R2 asks for the turtle's position; its read is the answer's source).
- **Not removable:** rotate calls (including rejected S3 tries), `get_parameter` (R1's parameter read), `divide`, `final_answer`, the first request.

### Arm OFF (the gate): 64 episodes, 216 requests (3.38 per episode)
| Episode type | Episodes | Requests | Removable pose reads | U |
|---|---:|---:|---:|---:|
| single (S1-S3) | 24 | 76 | 22 | 28.9% |
| act-then-read (R1, R2) | 16 | 50 | 10 | 20.0% |
| two-step (M1-M3) | 24 | 90 | 22 | 24.4% |
| **all** | **64** | **216** | **54** | **25.0%** |

Per task: S1 33%, S2 33%, S3 21%, R1 7% (2 of 28), R2 36% (8 of 22), M1 27%, M2 27%, M3 20%.
Cautious R (without R2): 46 of 216 = **21.3%** pooled; qwen3.5:9b 12 of 56 = **21.4%** (its U is 14 of 56 = 25.0%).
Two-step tasks: each episode has one final read, not one per turn. So the saving counted there is one read per episode. It holds only if the bundle can be called more than once (it then verifies after each turn). The bundle cannot save more reads than the control makes.

## 2. "About 1.7 model calls per attempt" versus his 3.38 / 3.17

- **His numbers are right.** OFF: 216 requests / 64 episodes = **3.375**. ON: 203 / 64 = **3.172**. Each is one arm's requests divided by that arm's episodes.
- **Mine (MERGE_PLAN section 0 item 5) was wrong.** I wrote "~1.7 requests per episode (216 and 203 requests over 64 episodes per arm)". 216 / 128 = 1.69: I divided one arm's requests by **both arms' episodes**. The "64 per arm" in my own sentence shows the slip. The verification rates in the same sentence (0.84 and 0.66 reads per episode = 54/64 and 42/64) were correct.
- **Effect:** my text called the saving "bounded by" those reads and the closing steps, and "small". The real denominator is 3.4 requests, not 1.7, so the reads are 25% of requests (OFF), not about 50%. The step 0 figures above do not use the wrong number: they divide by the real request counts.
- A dated **correction note** is appended to MERGE_PLAN.md. The original text is kept.

## 3. His point: the turtle tool already returns the state after a move

He is right, and it is the key issue. That is **arm ON**. With the state line already in the result:
- Pose reads after a goal are still made in **42 of 64** ON episodes (OFF: 54 of 64). The drop is 12 reads, 9 of them bonsai's. In R2 the read is made 8 of 8 times in both arms, although the line already carries the position.
- If ON is the control, the possible saving is the reads that remain: **42 of 203 = 20.7%** pooled (qwen3.5:9b 13 of 55 = **23.6%**). Cautious (without R2): **34 of 203 = 16.7%** pooled; qwen 11 of 55 = **20.0%**.
- **Both are below T = 25%.** My pre-registered rule applied to ON would give **NO-GO**. I chose OFF as the primary control because it is the `XM` default. I do not change the earlier decision, but ON is the fairer comparison if his tool is run with the state line.
- **What the bundle adds beyond ON:** by content, nothing the model does not already get after a move. The bundle also reads the pose before writing (more native operations, no model request saved) and skips the write if the robot is already at the goal (these tasks start at heading 0, so this does not change the request count). The only possible extra effect is an explicit "goal reached" verdict that might stop the model's redundant read. **That is untested (H).** The ON data point the other way: the state was shown and the model still read in 42 of 64 episodes.
- **How much of the estimate remains:** against ON the optimistic bound falls from 25.0% to 20.7%, and the cautious one from 21.3% to 16.7%. A realistic saving is below the cautious figure.

## 4. Recommendation (plan level)
Keep the studies separate (option C), as Levinson prefers. The possible saving against his own state-returning tool is under the threshold, and his noise floor (about 21% at 64 per arm) is as large as the saving. Revisit only if his turtle tool is run with the state line and there is a reason to think a goal-reached verdict would change the model's reads.
