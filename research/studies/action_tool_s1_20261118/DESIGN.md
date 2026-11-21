# Guarded action tool, stage S1: executor core against a fake robot

2026-11-18. Prototype only. Spec: `Claude outputs/2026-11-17_GUARDED_ACTION_TOOL_SPEC.md` (v2; mirror copy in the owner's context folder). Not registered in ROSA or in any harness, not run against ROS, Gazebo, turtlesim or a model: framework integration and any live action run need the owner's separate authorization. Status of the paper-level decision (action tasks in or out) is still the group's, before the Saturday 21 November freeze.

## What S1 is
The part of the spec that does not need a robot: the typed-tool **interface**, the deployment **policy**, the **state machine** that checks, sends once, waits, cancels and locks, and the **text** the model sees. The robot side is behind an `ActionBackend` contract so the same logic later runs against turtlesim or Nav2 (Simple Commander) inside the spec's separate supervisor process.

## Files (read in this order)
| file | responsibility |
|---|---|
| `action_interface.py` | Interface first. Policy (`DeploymentPolicy`, `ActionSpec`, `FieldRange`), method switches (`ExecutorOptions`), states (`ExecutorState`, `Result`), the structured record (`ActionOutcome`), the model-facing text (`render_for_model`), the tool schema generated from the policy (`tool_schema`), and the backend contract (`ActionBackend`, `Clock`, `Ack`, `GoalStatus`). No motion logic. |
| `action_executor.py` | `ActionExecutor.execute()`: LOCKED check, argument checks, budget, readiness, send once, wait, cancel on timeout, lock when the motion state is unknown. `begin_episode()` is the reset contract. Never raises to the caller. |
| `fake_backend.py` | A scripted fake robot and a fake clock (sleep advances time instantly) for tests. |
| `tests/test_executor.py` | 19 deterministic tests (all pass; run command in the file header). |

## Flow of one call
`execute(tool, args)` -> if `UNKNOWN_LOCKED`: `LOCKED` -> check tool name and arguments (finite numbers in range, no unknown field, empty behavior tree): `REJECTED <check and field>` -> goal budget: `REJECTED` -> `backend.readiness()`: `NOT_READY <reason>` (no goal, budget unchanged) -> `backend.send_goal` once (`PENDING`): refused = `REJECTED`; no answer = ask the backend once about the goal id, track it if it exists, otherwise request a cancel and lock -> `ACTIVE`: poll until `SUCCEEDED` / `ABORTED <code>` / `CANCELED`, or until the execution deadline -> cancel, wait for settlement: confirmed = `TIMEOUT: cancel confirmed, robot stopped` (state TERMINAL), not confirmed = `TIMEOUT: cancel requested, motion state unknown` and `UNKNOWN_LOCKED`.

## The separate switch: post-action state attached to the result
`ExecutorOptions.attach_post_action_state`, default **False**, kept apart from the policy because the policy must be identical in every method while this switch may become a method component (spec section 11 calls it a candidate add-on needing its own control arm). When on, any call that sent a goal gets one extra line, `State after action: <backend.observe_state()>`. Tests show: default off never reads the state; on adds exactly that line; the switch changes only the text, never a decision (same result, state, sends and cancels with the switch on or off); a failing state read becomes `unavailable (...)` and does not break the result. **This line is the robot's own sensor report to the executor, not the evaluator's ground truth** (spec section 8 keeps ground truth out of the model's sight).

## Tested (fake robot only)
Bad arguments (out of range, NaN, infinite, missing, unknown field, string, boolean, non-empty behavior tree, unknown tool) are rejected with no goal sent and no budget used; four not-ready reasons and a raising readiness check send nothing and keep the budget; success, abort with code, server refusal; budget per episode; timeout with working cancel (stopped, not locked); timeout with failed cancel (locked, `LOCKED` on the next call, nothing sent, `begin_episode` blocked, never auto-unlocked); lost acknowledgement (never resent; reconciled when the goal exists; locked when it cannot be known); a backend that raises after sending locks instead of crashing; event log rows; the switch behaviours above; schema generated from the policy.

## Not done (next stages; each needs its own decision)
- The separate long-lived supervisor process and the "worker killed mid-motion" test (the core is in-process so the logic can move unchanged).
- Real backends: turtlesim `rotate_absolute` (workbench), Nav2 `navigate_to_pose` with Simple Commander readiness (lab computer, domain 219 vs 220).
- Ground-truth reader, reset of simulation and pose, stability interval, the success judge.
- Central write authorization for every other tool, per-system registration and the "same model-facing tool in all four systems" test, task design (Codex, blind to the method).
- The deployment policy file for a real robot (map bounds, deadlines): the numbers in the tests are placeholders, not a robot's limits.

## Limits of what the tests establish
They show the state machine does what this file says against a scripted fake with a controllable clock. They do not show that a real action server behaves like the fake (late acknowledgements, partial cancels, feedback), that the deadlines are right, or that a small model uses the tool well. Say "guarded", never "safe".
