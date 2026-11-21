# Demo plan: Levinson's method M + Martin's bounded macro on UR5e Gazebo (PLAN ONLY)

Written 2026-11-22 (Taipei) by Session B (Claude, AI). **Zero model calls. Nothing built.** Branch `member/martin-merge`.
Team decision (relayed by Martin): (1) a **demo** of the merged method on Martin's UR5e Gazebo setup; (2) on the lab, Levinson's method first, with "his + mine" as an extra arm only if time allows. Demo first.
**A demo is not evidence.** It has no scoring, no held-out tasks, and its runs are never pooled with M4, G1, D, F1, parity or any of Levinson's results.
Labels: **(F)** read in code/docs at the cited place; **(R)** reported, not re-run; **(H)** my inference.

## 1. Scenario: three short demo tasks

All in the **healthy** UR5e world (no fault injection), start pose `ur5e.home`. The registry is the frozen M4 one (`rosa-evaluation/experiments/macro_m4/design.py`, `registry()`): `ur5e.home`, `ur5e.stage_left` (pan -0.14, wrist_3 0.20), `ur5e.park_right` (pan 0.16, wrist_3 -0.12), `ur5e.inspect_readiness` (F).

| # | Task text (draft, fixed before any live run) | His part shown | My part shown | Expected tool path |
|---|---|---|---|---|
| D1 | "Which node publishes /joint_states, and what are the current shoulder_pan_joint and wrist_3_joint positions? Answer as a JSON object." | short menu, structured finish, name fix (node name) | none | `ros2_topic_info` → `ros2_topic_echo` → `final_answer` |
| D2 | "Check that the arm is ready to move. If it is ready, move it to park_right. Report readiness and the final shoulder_pan_joint position as a JSON object." | finish tool, errors-as-text | read-only inspection skill, then the movement skill (read → one write → fresh verify) | `run_skill(ur5e.inspect_readiness)` → `run_skill(ur5e.park_right)` → `final_answer` |
| D3 | "Move the arm to stage_left, then confirm with a fresh joint sample. Report the final wrist_3_joint position as a JSON object." | menu read after the action, finish tool | movement skill | `run_skill(ur5e.stage_left)` → (optional `ros2_topic_echo /joint_states`) → `final_answer` |

Why readiness in D2 goes through my inspection skill and not his menu (F): controller activation is read from the service `/controller_manager/list_controllers` (`M:src/rosa_reliability/ros_readiness.py:16-36`). His menu has no service caller: unrestricted `ros2_service_call` is excluded on purpose (`L:research/decisions/2026-11-17-menu-coverage-and-rule.md:24-25`). His rule allows "a narrowly constrained adapter ... with explicit fallback" (`:25`); my read-only `InspectionSkill` (max 0 writes, `capabilities.py:63-69`) is exactly that kind of thing. We say so on the slide.

Reliability choices: healthy world only; each task needs at most 2 macro calls and 4 model requests; scripted reset to `ur5e.home` between tasks with a reset check (the Gazebo D wrapper already has `reset_check`, `rosa-evaluation` `member/martin-gazebo`).

## 2. Architecture (demo only)

```
user task ─▶ demo loop (one model, tool calling)
              ├─ his short menu: the 12 stock ROSA read tools (ros2_* + roslog_list + read_log)
              ├─ run_skill(skill_id)  ◀── my macro, ONE action tool
              │     each call: registry.open(..., mode='macro', allowed_skills=[skill_id]).execute(skill_id)
              │     = fresh bounded invocation: read → at most one write → fresh verify (inspection: verify only)
              └─ final_answer(answer: object)  ◀── the ONE terminal (his)
                    └─ name fix applied to the submitted answer, raw answer kept beside it
errors: any validation error or tool exception (including my rejection JSON) is returned to the model as text
```

- **One terminal:** his `final_answer`. My `submit_report` and the report gate are **not exposed**. The macro still runs its internal read/verify through `session.tools_by_name` (`M:macro.py:15-41`, `capabilities.py:151-165`), so nothing in my code needs `submit_report` to be offered.
- **One action tool:** `run_skill(skill_id)`, a thin demo wrapper. It opens a **fresh invocation per call** through the public API (`CapabilityRegistry.open(..., allowed_skills=[skill_id])`, `capabilities.py:71-93`). This lets D2 do inspect then move without changing my "select once per invocation" rule (`workflow.py:86-98`). Episode cap: 2 `run_skill` calls. No change to any `rosa_reliability` file.
- **Wording frozen from each side:**
  - mine: the `select_skill` tool description and the macro-mode condition sentence, verbatim from M4 (`workflow.py:157-162`; `design.py` `query()` macro sentence). Not my five-tool prompt contract (it names tools the demo does not offer).
  - his: the `final_answer` schema and description verbatim (`L:research/studies/action_tool_s2_20261118/smoke_loop.py:37-38`), and his M system prompt ("pilot A1 prompt + C1 finish line", `L:research/studies/canonical_render_20261118/FREEZE_LIVE.json:76`) **if Levinson sends the text** (section 3).
- **Scoring:** none. We log the trace (requests, tool calls, macro events, raw and rewritten answer) for the slide only.

## 3. His components: what the demo needs and what is in his public branch

| Component | Needed for | In public branch 2b1c790? | Option | Recommendation |
|---|---|---|---|---|
| 12 menu tool **names** | menu | **Yes**: list in `menu-coverage-and-rule.md:24` | — | use as is |
| 12 menu tool **implementations** | menu | **Yes**: stock ROSA, `src/rosa/tools/ros2.py` (`ros2_node_list` :92 … `ros2_doctor` :346, `roslog_list` :366), `src/rosa/tools/log.py:22` (`read_log`) | his wrapper with bounds (`harness.DOMAIN_TOOLS`) is **missing** | **reimplement**: pick these 12 stock tools by name (labelled "demo menu, same names, stock implementations, not his bounded wrapper") |
| `final_answer` schema | terminal | **Yes**: `smoke_loop.py:37-38`, `run_action_study.py:47-48` | — | use verbatim |
| M system prompt (A1 + C1 finish line) | prompt | **No** (`run_pilot.prompt_for`, missing) | ask Levinson for **the two strings only** (no files) / reimplement | **ask Levinson** (smallest request; keeps his wording exact). Fallback: a short prompt written by us, labelled "not his wording" |
| Errors as text + strict pre-check | errors | **No** (`harness`, `ablation_arms` missing) | reimplement from his description: a failed call returns field, expected type, received value as a tool message (`METHOD_SUMMARY.md:10`; one-page `2026-11-17-steady-loop-teammate-one-page.md`, example) | **reimplement**, labelled; ~40 lines |
| Answer name fix | finish | **Partly**: `namefix_rule.py` is public, but it imports `answer_gate` (missing; `namefix_rule.py:14-17`) | ask for `answer_gate.py` (one small dev file) / reimplement `allowed_names`, `ABSOLUTE_NAME`, `RELATIVE_NAME`, `trailing_matches` from `name_fix_applied_20261117/LEDGER_DEFINITION.md` | **ask Levinson for `answer_gate.py`**; fallback reimplement, labelled, and test against `namefix_rule`'s own tests (`tests/test_namefix.py`) |
| Steady loop (executor) | loop | **No** (`harness`, `run_pilot`) | reimplement a plain tool-calling loop (model ↔ tools until `final_answer`, cap 8 requests) | **reimplement**, labelled "demo loop, not his frozen harness" |
| `scorer_v2`, `fair_arms`, `ablation_arms` (arms), judge | scoring, baselines | No | — | **not needed** (no scoring in a demo) |

**Simplest overall:** one message to Levinson asking for (a) the A1 prompt and C1 finish-line text and (b) `answer_gate.py`. Everything else is either public or a small, labelled reimplementation. If he declines, all of it can be reimplemented; the demo then says "M as described in his public docs, reimplemented", not "his M".

## 4. Model

- **Primary: Sol** (gpt-6.1-sol, hosted, existing OAuth session; no new consent). It is the most reliable on the M4 families: M4 laptop 20/20 in both arms (R, own records; `artifacts/report-addenda-20261121/ADDENDUM_GAZEBO_D.md`). Uses my `rosa_auth`/`ChatSiwc` from the `member/martin` checkout; **nothing from `rosa_auth` is copied to this branch**.
- **Fallback: qwen3.5:9b** (local; on Levinson's model list too). Less reliable: M4 15/20 vs 14/20; 11-17 lab 27/36 → 28/36 known-goal (R). Serving: the G1/M4 demo settings (num_ctx 8192, temperature 0, seed 42, think off), labelled as **demo settings, not his exam settings** (his are temperature 0.7, num_ctx 65536, `PROTOCOL_DRAFT_v3:48`).
- Pick one model for the recorded demo; keep the other as a backup recording.

## 5. Where the code goes and how it runs

- Code: `research/demo_merged_20261122/` on `member/martin-merge` (new files only; his files untouched).
- Runtime: my existing WSL research environment (the one M4 used: ROS 2 Jazzy, Gazebo, `rosa_reliability` and `rosa_auth` from `rosa-research` `member/martin` 8713f9b). His public pieces are imported by path from this worktree at a pinned commit.
- Launch: detached WSL job with on-disk logs (the Gazebo D pattern), own `ROS_DOMAIN_ID` (232; Session A's D uses 231), one Gazebo instance, scripted reset.

## 6. Build list (checks after each step; estimates are mine)

Steps 1-6 are scripted (zero model calls, no GPU). Live steps 7-8 only after `STATUS.md` shows Session A's chain finished.

| # | Step | Check | Est. |
|---|---|---|---|
| 1 | Send Levinson the request in section 3 (two strings + `answer_gate.py`). **STOP POINT 1:** wait up to an agreed time, then use the fallbacks. | his answer or the fallback decision written here | 0.2 h + wait |
| 2 | Menu: build the 12 stock tools by name; dump names, descriptions and schemas to JSON with SHA-256. | names equal the list in `menu-coverage-and-rule.md:24`; no write tool present (`ros2_param_set`, `ros2_service_call` absent) | 1 h |
| 3 | Errors-as-text + pre-check wrapper, and the demo loop (fake chat model for tests). | unit tests: wrong type → text with field/expected/received; tool exception → text; loop ends only on `final_answer`; cap enforced | 2 h |
| 4 | Name fix: `namefix_rule.py` unchanged + `answer_gate` (his file or labelled reimplementation). | his `tests/test_namefix.py` passes (if it needs only these modules); a scripted case rewrites `joint_state_broadcaster` → full name only when exactly one match was seen | 1-1.5 h |
| 5 | `run_skill` wrapper over `CapabilityRegistry.open` (fresh invocation per call, cap 2). Rejections returned as text. | scripted tests against a fake transport: inspect (0 writes); move from home (1 write, verify); already at goal (0 writes); 3rd call refused; no `submit_report` offered | 1.5 h |
| 6 | Scripted end-to-end dry run of D1-D3: fake model with fixed tool calls, fake ROS transports. **0 model calls.** Freeze task texts, prompt and tool JSON (hash file). **STOP POINT 2:** Martin reads the frozen demo texts. | each task ends in `final_answer`; trace shows the expected path; hashes recorded | 1.5 h |
| 7 | **After Session A's chain** (check `STATUS.md`): bring up Gazebo once, run the reset check, run D1-D3 with **Sol**, one take each. | Gazebo ready; reset check passes before each task; each task ends with `final_answer`; arm pose matches the skill within tolerance (macro verify) | 1 h |
| 8 | If a take fails: fix only wiring (not wording), rerun; if Sol is unavailable, record with qwen3.5:9b. Keep every take, including failures. **STOP POINT 3:** Martin picks the take for the demo. | all takes logged with model, settings and hashes | 1 h |

Total: about **8-9 h** scripted, **2 h** live. The live part waits for the chain.

## 7. Honest limits to say in the demo
- It shows the two parts working together on 3 hand-picked tasks in a healthy world. It does not show that the combination is better than either part alone.
- His components are partly reimplemented from public docs (marked in section 3). If Levinson's strings and file arrive, those two parts are exact.
- Sol is hosted and not one of his small models. The macro's evidence (M4/G1/D) is for the catalogue design on these UR5e poses, not for the combination.
