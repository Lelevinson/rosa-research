# Report gate for action tasks, generic form: offline sizing (frozen 2026-11-21, before the script)

Source: `Claude outputs/2026-11-21_CC_REPORT_GATE_SIZING.md` (the owner's message is the authorisation). Offline, CPU only, saved traces and result rows only; no build, no run, no push, no held-out file. Run with `PYTHONDONTWRITEBYTECODE=1`.

## Mechanism sized (not built)
After an action episode ends, the executor compares the model's final claim about the action outcome with the executor's own post-action receipt (a fresh state read by the guarded action tool). On disagreement the model gets one request with the receipt shown (or, variant, the answer is marked as contradicting the receipt). Only the executor's receipts are used, never task answers or the judge. Both variants are detected identically offline, so they are not separated.

## Population
The 128 full-phase episodes of `research/studies/action_dev_switch_20261118/RESULTS_LOG.jsonl` (`phase == "full"`; 8 authored turtlesim tasks x 4 models x seeds 1-2 x arms OFF/ON; 6 smoke rows excluded). Development tasks only.

## Definitions
- **Independent final state (truth):** the row's `true_heading`, `true_x`, `true_y`, `turtle_still` (read by a separate node; never shown to the model).
- **Claim (post-hoc reading, labelled):** the final answer object, read as the action judge v1.1 would: for `ending == "text"` the last JSON object of the text (`judge_v1_1.parse_text_answer`), for `final_answer` the structured `answer`; in both a sole-key `{"answer": {...}}` wrapper is unwrapped. The frozen v1.0 as-scored reading (no unwrap) is reported beside it. A claim exists if the object holds a numeric `heading`, `x` or `y`; those are the **claimed fields** (`background_r` is not a state field the receipt covers). No claim (text without an object, backend error, missing fields): the gate cannot fire.
- **Tolerance:** 0.1 (the judge's `TOLERANCE`; angular difference for heading, absolute for x and y).
- **Contradiction:** a claimed field differs from the truth by >= the tolerance. Subtypes: **A** "claims the target but did not succeed" (the claimed heading is within the tolerance of the task's `final_target`, the true heading is not); **B** other mismatch with the true state not at target; **C** the true state is at the target but the claim is elsewhere (the reverse).
- **Receipt:** the last `State after action: heading H rad, position (X, Y)` line in a `rotate_to_heading` tool row of the episode (the executor's own state read right after the last goal that was sent; present **only in arm ON**, where `attach_post_action_state` was on). In arm OFF the executor recorded no state value (the trace holds only goal status), so **no receipt exists: the gate is not estimable there**; OFF contradictions are counted as a labelled ceiling and do not enter the bars. A receipt is also missing if no goal was sent.
- **Gate fires:** a receipt exists, a claim exists, and some claimed field differs from the receipt by >= the tolerance (heading and, where claimed, x and y).
- **Caught:** contradiction, gate fires, and the receipt agrees with the truth within the tolerance on heading, x and y (the receipt showed the true state).
- **False fire:** the gate fires in an episode whose claim does not contradict the truth. **Ambiguous receipt:** a receipt that differs from the truth by >= the tolerance (counted separately; if it makes the gate fire on a correct claim it is also a false fire; if the claim contradicts the truth and the receipt is wrong too, it is not caught).
- **Upper bound of gain:** caught episodes whose true state is at the task target and still (a corrected claim = the receipt values would be accepted by judge v1.1 reading): "convertible". Caught episodes whose true state is not at target would become truthful failures, not successes.
- All measures are per model and per arm, and per task.

## Bars (frozen)
- **Size:** caught contradictions >= 4 episodes in >= 2 models (arm ON, primary reading). **Harm:** false fires = 0.
- Below size: report "too rare on dev" (decision: not in the freeze; future work).

## Output
`REPORT.md` (top box first), commit, sync, status-only ntfy, stop.
