# Decision record (context §14.2), 2026-11-12

Read first: AGENTS.md; START_HERE; ACTIVE_STATE; context §§0–4, 12, 14 and §§16–20; RESEARCH_RULES; the prior "Decision Optimization" investigation; the baseline, narration and GPT-coverage reports. Labels F/R/L/H/P per §12.1.

**Status: Stage 0 (offline) PROCEEDS. Stage 1 (new runs) is BLOCKED / NOT YET JUSTIFIED** until the user authorizes it and a Stage 1 protocol is frozen (missing: authorization; written postconditions for any unseen task; fixed interpreter subset for code mode; a checked ChatGPT-plan access path; a Stage 1 cap table reviewed against Stage 0 results).

1. **Observed opportunity (F for counts, R for support judgments).** 327 requests in 58 preserved traces. Baseline requests A 76, B 80, C 71 equal the earlier report; 264 native reads and 14 exact repeats reproduced from raw `ros_start` events. Whether the opportunity is real efficiency headroom is what Stage 0 measures; correctness faults are not used as the opportunity.
2. **Concrete mechanism.** None proposed. This is a diagnostic. Any later candidate must name the observable signal before a wasted call (listed in REPORT) and differ from the strongest ordinary control.
3. **Incremental novelty.** None claimed. Closest ordinary mechanisms: deconflicted prompt with native batching, list arguments, exact memoization, FQN assembly from verbose topic info, LLMCompiler/ReWOO/CodeAct style plans (context §12.3).
4. **Fair evaluation.** Stage 0 compares nothing new; it relabels old traces. Known confounds: three corpora differ in prompt (baseline conflicted, others deconflicted), context length (65,536 / 4,096 / 16K), tasks and model; supported-complete flags come from earlier studies; one primary labeler plus a 20% blind check; floors are derived bounds. All tasks are development evidence.
5. **Decision-changing action.** Stage 0 decides whether Stage 1 is worth running at all: if the excess is mostly removable by a deconflicted prompt and ordinary dedupe, Stage 1 should shrink to a deconflicted-control measurement before any plan-ahead or code-mode arm. Stop rule: no Stage 1 without user authorization.

---

# Stage 1 section (added 2026-11-12, before any Stage 1 inference)

Authorization used: the user's message in this session telling me to follow the instructions in `ROSA_stage1_addendum.md`. The addendum also says the user approved Stage 1 earlier in chat and allowed the ChatGPT-plan OAuth path; I cannot see that earlier message, so I rely only on the present instruction, which covers: Stage 1a and 1b exactly as written, nothing else (no plan-ahead arm, no code mode, no new algorithm). If the strong-model provider returns an access or throttling problem, I stop that part.
Disclosure: the strong model receives the task prompts, the stock ROSA tool schemas and observations from an isolated stock-node fixture. No credentials, private data or physical-robot data. Quota is the ChatGPT plan; no API key.

**Status: Stage 1a and 1b may proceed once `PROTOCOL_STAGE1.md` is frozen and the offline checks pass; otherwise BLOCKED.**

1. **Observed opportunity (F).** Stage 0: all three baseline arms keep "NEVER call multiple tools / Do not batch" (adoption 0–6% among opportunities) while deconflicted arms show 50–100% on tiny samples; baseline supported-episode excess 82–112% of floor. The wasted-request share is real in traces; whether it disappears when only the prompt changes has not been measured (never run in one session, same tasks).
2. **Mechanism.** None. The treatment is a prompt deconfliction done by a runtime override of the system-prompt list inside the study harness. `src/rosa/prompts.py` is not edited.
3. **Novelty.** None claimed. This is baseline repair (context §0): the strongest ordinary control for any later candidate. Literature named in the addendum (ROSA MetaTool arXiv 2609.13335; efficient tool-using agents survey; programmatic tool calling arXiv 2608.06370) is **unverified** here: taken from the addendum's search summaries, not read; not relied on.
4. **Fair evaluation.** 1a: same tasks, tools, model, settings, session and order randomisation for A_orig vs A0; only the batching text differs. Correctness scored first with the vendored baseline scorer. 1b: A0 only; width N varied; truth from a direct oracle read, written before runs.
5. **Decision-changing action.** 1a decides whether the prompt fix alone removes the serialised-request excess; 1b decides whether it still holds when the number of entities grows. Stop rules and caps are in `PROTOCOL_STAGE1.md`.

---

# Stage 2a section (added 2026-11-13, before any replay computation)

Authorization used: the user's message telling me to follow `ROSA_stage2a_replay_addendum.md`: **offline replay only** (no inference, API, fixture or repository edit; study-folder files only). Nothing here authorizes implementing the mechanism in ROSA or running it live.
**Status: Stage 2a proceeds as a narrowly scoped offline diagnostic with a frozen kill bar. Any live implementation or run is BLOCKED / NOT YET JUSTIFIED.**

1. **Observed opportunity (F, from Stage 1).** In the Qwen A0 traces the avoidable excess was serial batchable calls, repeats, noise and recovery, and requests that truly depended on an earlier result were few (`DEP not batchable`: 2 in d1 and 2 in t1, none in t2/x1). Whether a learned expansion removes any floor-stage request is what the replay measures; I expect the opportunity may be small (H), which is why the kill bar exists.
2. **Mechanism (P, not implemented).** After a read tool returns, run read-only follow-up calls whose arguments are bound from fields of that result, where a tool-pair estimate learned from other tasks says the follow-up usually comes next, and append their results to the same observation. No hand-written task or tool map.
3. **Closest prior mechanisms and the closest negative study.** AutoTool-family history-continuation (`studies/autotool_iteration_20261112/`): its H2 origin-path association is essentially the binding type used here, its conditional tables with ordinary backoff are the tool-pair estimate, and its static equivalent is the fixed-order/top-1 control. That study found 0 complete tool-plus-argument matches over 269 boundaries and no difference from equal-feature ordinary backoff, and blocked live admission. PASTE (speculative tool execution), LLMCompiler, ReWOO and CodeAct are the parent mechanisms (L; named in the earlier screen, not re-read here). Incremental delta tested here: argument construction from learned field bindings plus whole-result expansion (over-fetch) measured against a static top-1 rule, on held-out tasks. **Risk of repeating the AutoTool negative is real**; the static top-1 control and the kill bar are the guard, and a tie with the static rule is a rejection.
4. **Fair evaluation.** Leave-one-task-out over six tasks; evaluation on A0 traces of Qwen (Stage 1a) and Luna (Stage 1c); cost side counted (speculative units, precision, extra native operations, extra input tokens). Development tasks only; a replay on recorded traces is **not** a live run and cannot show answer support or latency.
5. **Decision-changing action.** The replay decides whether any live or implementation phase is worth authorizing. Stop rule: the frozen kill bar in `PROTOCOL_STAGE2A.md`.
