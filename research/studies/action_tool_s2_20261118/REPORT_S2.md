# Action tool S2: S1 executor wired to real turtlesim, tests and tiny model smoke

2026-11-18, Asia/Taipei. Development only: turtlesim is a workbench (spec section 3), not a reported result; not registered in ROSA or any harness; no held-out files. Smoke protocol `PROTOCOL_SMOKE.md` (SHA-256 `b9a59b9d68e77d383148975b03a60860976497a2e82b764c7d2a9bc1ce418f8c`) was hashed before `smoke_loop.py` existed.

## What was built
- `turtlesim_backend.py`: `TurtlesimBackend`, the real `ActionBackend` for `/turtle1/rotate_absolute` (rclpy action client + the turtle's own `/turtle1/pose`), spun in a background thread; `TURTLESIM_POLICY` (one typed tool `rotate_to_heading(theta)`, theta in [-pi, pi], budget 3, execution deadline 15 s). It holds no decision logic: the S1 executor (`../action_tool_s1_20261118/action_executor.py`) is **unchanged**. A late acknowledgement is reconciled in `poll()` (goal id kept), a cancel is a request, status is mapped from the real result.
- `tests/test_turtlesim_backend.py`: 7 tests against a real `turtlesim_node` started per test (offscreen), ground truth read by a separate subscription. The S1 tests (19) still pass.
- The post-action-state switch stays a separate option, default off (`ExecutorOptions.attach_post_action_state`), used unchanged.

## Tests (measured, real ROS)
All 7 pass (27 s): NOT_READY when no simulator (nothing sent, budget untouched); rotation to 1.2 rad SUCCEEDED and the independent pose read is within 0.05 rad; out-of-range theta REJECTED with no goal sent and no motion; a 0.3 s deadline gives TIMEOUT with the cancel confirmed by the real server (turtle really stopped and short of the goal); budget enforced; switch off adds no line, switch on adds `State after action: heading ... rad, position (...)` equal to the real heading, and no line when no goal was sent; simulator killed mid-motion gives TIMEOUT with `motion_confirmed_stopped=False`, state UNKNOWN_LOCKED, and the next call LOCKED. Not tested: a refused goal (turtlesim never refuses), a late-but-arriving acknowledgement, error codes (turtlesim reports none), the separate long-lived supervisor process.

## Model smoke (qwen3.5:9b, 4 episodes, run with nohup, about 2 minutes)
Tasks A1 (rotate to 1.5) and A2 (rotate to 2.0 then -1.0), both arms, order shuffled; the tools were `rotate_to_heading`, a read-only `read_turtle_pose`, and `final_answer`.
| task | arm | requests | goals sent | model-visible state line | true final heading | answer | judge |
|---|---|---|---|---|---|---|---|
| A1 | OFF | 3 | 1 | no | 1.488 | 1.488 | success |
| A1 | ON | 3 | 1 | yes | 1.488 | 1.488 | success |
| A2 | OFF | 4 | 2 | no | -0.992 | -0.992 | success |
| A2 | ON | 3 | 2 | yes | -0.992 | -0.992 | success |
**Clean criteria (all met):** every episode ended with `final_answer` (no cap, no crash, longest 30 s); prompt and tool-schema hashes equal across arms per task; the state line appeared only in ON and only after a goal-sending call; all goals SUCCEEDED, executor state TERMINAL at the end, turtle still for 1 s; Ollama had no model loaded afterwards, no turtlesim process remained. The turtle stops about 0.01 rad short of the goal (1.488 for 1.5), inside the 0.1 tolerance of the judge.

## Interpretation (labelled)
- Wiring works end to end: a small model called the typed tool, the real server executed and reported, the guards held in the tests. Whether it holds on Nav2/TurtleBot3 (lifecycle readiness, stale TF, partial cancels, real error codes) is untested; turtlesim is the easiest case.
- The switch: with the line on, one episode (A2) used one request fewer (the model skipped `read_turtle_pose`); in A1 it still called `read_turtle_pose` although the line was present. Four episodes, one model, no repeats: this shows nothing about the switch's value, only that it reaches the model and changes nothing else. Tasks were designed by me, not blind to the method.
- Not done and not authorized here: more tasks or seeds, other models, the ground-truth reader as a reusable judge, Gazebo/TurtleBot3, integration into ROSA or the step-loop harness. A larger run needs its own frozen protocol and the owner's decision (action tasks in or out of the paper is still open before the Saturday freeze).

Files: `turtlesim_backend.py`, `tests/test_turtlesim_backend.py`, `PROTOCOL_SMOKE.md/.sha256`, `smoke_loop.py`, `SMOKE_RESULTS.jsonl` (with executor events and transcripts), `smoke.log`.
