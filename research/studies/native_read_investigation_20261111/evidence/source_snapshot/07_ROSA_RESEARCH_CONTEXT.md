# ROSA Special Project — Research Context and Decision Log

**Version:** 2026-11-10 (evening addendum, post-CPAW) | Canonical research state: evidence-first, no algorithm selected  
**Purpose:** Persistent context for future ChatGPT Project conversations and Codex collaboration. This document records **what the user wants, what was tried, what actually happened, and which assumptions must not be repeated**. It is not a declaration that an algorithm has been finalized.

> **Ringkasan singkat (untuk user, 10 November 2026):** Target tetap **kontribusi algoritmik baru atau incremental yang nyata untuk efisiensi tool-calling ROSA**, tanpa mengorbankan jawaban yang benar/lengkap. Model tetap memilih makna dan sumber yang memerlukan judgment; framework dapat mengoptimalkan langkah yang aman. **Belum ada algoritme terpilih atau keunggulan baru yang terukur.** Misi A–D mengevaluasi komposisi, generated tools, interface specialization, parameter recovery, dan evidence packing, tetapi semuanya mempunyai pembanding sederhana/prior art kuat. Audit bukti 10 November mengidentifikasi kesalahan sumber dan jawaban yang hilang, tetapi belum membuktikan bahwa perbaikan baru akan meningkatkan efisiensi. Jangan mengulang audit umum atau benchmark lama tanpa pertanyaan pembeda yang jelas. Baca *Section 0* dan *Section 12* sebelum merekomendasikan langkah baru.

---


## 0. CURRENT STATUS AND SELF-CHECK — READ FIRST (2026-11-10)

This section supersedes older **next-step recommendations**, not the historical measurements or constraints recorded below. The date of a proposal is not its evidence level.

**Objective:** A defensible framework-level algorithmic contribution—ideally genuinely new, but an original, justified increment over prior methods is also acceptable—for reducing unnecessary LLM decisions, native tool work, tokens, latency, or total cost **with complete supported answers**. Correctness and validation are conditions, not a separate replacement project. December 2, 2026 is the presentation deadline.

**Current research decision:** **No algorithm has been selected; no new baseline run or 22-cell diagnostic is authorized or underway.** The last Codex evidence-gate audit recommended a future diagnostic, but that is a proposal, not the team's approved next action. The user correctly challenged repeating baseline work. Before any new run, show exactly what unmeasured decision it resolves that preserved old evidence cannot, identify the strongest ordinary control, and limit the run accordingly. Do not interpret a NO-GO on one hypothesis as evidence that no algorithmic opportunity exists.

**Previously known but repeatedly under-emphasized baseline fact:** In the pinned ROSA source, the **default system prompt instructs the agent not to batch or make multiple tool calls** (`src/rosa/prompts.py`, around line 81). This is a **prompt prohibition, NOT a framework/API impossibility**: some ROSA ROS 2 info tools already accept lists (`src/rosa/tools/ros2.py`); installed LangChain can dispatch emitted independent actions. A fair strong baseline must **replace**, not merely append contradictory instructions to, that default; it must demonstrate that actual batching/grouping is enabled and used on applicable tasks. Historical arms labeled "strong prompt" or "batching-enabled" must NOT automatically be described as fully deconflicted/activated. Original ROSA with its default prompt is descriptive context, not the decisive optimized control. This was documented before 10 November and should never be presented to the user as a newly discovered limitation without that qualification.

**Latest evidence status (Codex `ROSA_Bottleneck_Evidence_Gate_2026-11-10.md`, report audited, not independently re-executed here):**

| Claim | Evidence level and proper interpretation |
|---|---|
| 36 primary baseline traces; conservative supported answers A 9/12, B 10/12, C 8/12 and one uncertain | Original saved event audit and frozen judgments reported by Codex; the strict answer judgments do not certify every field or perfect experimental closure. |
| 3/36 wrong-source answer judgments and 5/36 interpretation/omission judgments | Reported recorded failure categories, may overlap; **not** a measured improvement opportunity in model/tool calls. |
| 10 native failures in five baseline episodes due to node identity/namespace construction | Source-grounded actual errors; a public FQN-assembly helper or ordinary validation is the strongest simple fix, not evidence of graph staleness. |
| 14/264 exact repeated native baseline commands | Same-command repetitions, **not proven safely reusable** because observations may change. |
| No indexed episode positively attributes failure to stale node incarnation | Lack of demonstrated staleness **in the preserved sampled evidence**, not zero risk in ROS 2. No calibrated guard signal or gain. |
| Max observed delivered tool message below 4.4 KiB in the inspected baseline/pilot traces | No demonstrated overflow-driven recovery from that sample; don't promote adaptive packing on hypothetical cap failures. |
| 64 original structured-dependency traces disappeared from `/tmp` | Reconstructed ZIP does **not** restore them. Other archives were audited to varying degrees; no general completeness claim. |

**Repeatedly explored and not yet promoted:** JTVR; graph-aware and dependency controllers; semantic field/source maps (generalization-confounded); tool-menu retrieval (coverage losses); structured `$ref` planner (zero adopted references in recorded experiment, incomplete raw evidence); CodeAct subset (one complete program of nine); GLBE (same-path ordinary composite can tie); CCVT generated paths (compact parameterized helper can cover same registry); generated alias selection (schema cost and naming prior art); adaptive parameter-batch recovery (simple list/type/singleton alternatives); evidence packing (factorization and strong fixed layouts); dynamic-graph admission (unproven signal and prevalence). These are **scoped failures/gaps**, not proofs of impossibility. Do not rename or lightly repackage them and restart the same mission.

**Open question:** Is there a ROSA-specific or framework-level *observable predecision signal* and a real policy choice that a strong ordinary baseline cannot already make as well or better, with sufficient realistic task frequency to justify its overhead? If yes, describe it precisely and test the smallest discriminating contrast. If no, say so and decide openly whether to report a systems-integration result, narrow the research question, or explore a substantively different mechanism—with prior-art screening first.

**Post-CPAW status (2026-11-10 evening):** CPAW has been implemented and independently reviewed; archive as a bounded negative prototype, not as the primary algorithm. Martin’s bounded-macro work is a teammate’s separate fixed-catalogue method; reference it but do not silently promote it into our generalizable research direction. No new optimization candidate, Codex implementation, or benchmark has been authorized. See Section 14 for the updated decision and mandatory execution discipline.

**Immediate user-facing discipline:** Do not issue another generic Work/Codex research prompt, prescribe a 22-cell rerun, or announce a new algorithm based only on a report summary. Re-read this state, locate earlier closest work, state one evidence-backed discriminating question and why it was not already measured. If none exists, acknowledge the blockage rather than manufacturing motion. The user should receive a compact actionable answer, not be expected to audit every recommendation.

---

## 1. Non-negotiable research objective

**Project:** Undergraduate Special Project, NASA/JPL ROSA (Robot Operating System Agent).  
**Main goal:** Develop a defensible **algorithmic or methodological improvement to LLM-agent tool-calling efficiency** that is implemented and measured in real ROSA, with potential to inform a research paper.

The aspiration is a **reusable framework-level component or decision mechanism**, not a task-specific robot controller, a better LLM model, or a collection of benchmarks alone. A framework is code that organizes agent/model/tool interactions; research contribution comes from a justified method/decision rule and evidence, not merely adding a Python module.

Important user priorities:

- Improve the **tool-selection, information-acquisition, or tool-execution part of an agent loop**. Do not drift into tool documentation/discovery as the sole contribution, general model training, or another unrelated AI topic.
- Aim to **reduce unnecessary model/tool operations, tokens, latency, or total cost** without sacrificing the information requested, task correctness, or safety. Saving model calls by losing answers is failure.
- The **LLM remains involved** in semantic interpretation and ambiguous cases. The objective is to reduce unnecessary repeated model involvement, not to abolish model reasoning.
- Prefer a **framework-level transferable principle**, demonstrable in ROSA and plausibly portable to other frameworks (for example agents handling APIs or databases). Do **not** require universality across all frameworks.
- Existing papers can supply substantial parent mechanisms. Adaptation, combination, simplification, formalization, or an incremental improvement are acceptable, but the work should identify an actual addition/difference and test it honestly. Do not demand a revolutionary theory or treat novelty uncertainty as grounds to prohibit every experiment.
- The user is interested in whether **mathematical modeling** can make the method more principled (e.g., cost/risk/objective functions and decision policies). Mathematics is a **design avenue to investigate, not an established requirement**; mathematical notation alone adds no evidence or novelty.
- The project is **still exploratory**. Do not prematurely name a “final algorithm,” or pretend that a positive result is owed in the next Codex run.
- **Presentation deadline: 2026-12-02 (Taiwan time).** Treat the remaining schedule as a constraint without reusing a stale countdown. Prioritize a coherent research concept, defensible method, initial prototype/evidence, and an honest presentation. A publishable result by that date is an aspiration, not a guarantee.

## 2. User expectations and communication contract

The user is a CS undergraduate who understands programming and basic agent loops, but **is not personally following every ROSA/Codex implementation detail**. ChatGPT is the primary user-facing coordinator/researcher; **ChatGPT Work and Codex are also independent research collaborators**, not disposable prompt-completion workers. None is the automatic authority on scientific truth.

When responding to the user:

1. Start with: **what we are trying, what happened, and what to do next**. Use plain informal Indonesian. A concrete tool-call example is often clearer than a new research label.
2. Do not assume the user knows labels such as “baseline B,” “evidence gate,” “compiler,” or the meaning of an experiment. Explain the object before the acronym; omit jargon unless needed.
3. Be **critical and intellectually independent**. Neither echo user suggestions automatically nor defend old ChatGPT decisions for consistency. Explain substantive disagreement briefly and concretely.
4. The user has repeatedly complained about long, abstract, reassuring, overly agreeable responses, and endlessly producing Codex prompts rather than taking research-level responsibility. Avoid these patterns.
5. When the user offers a nontechnical intuition, treat it as a **research requirement or hypothesis to evaluate**, not as an algorithm already designed by the user.
6. Contrast **measured facts**, **Codex reports not independently verified**, **interpretations**, and **future proposals**. Do not present predictions as results.
7. Do **not** substitute serial prompt-writing for substantive research. When independent external work is justified, provide a **complete, independently executable assignment** with evidence requirements, literature search, iterative self-critique, stop conditions, and a deliverable. Do not ask the user to supervise an agent loop.
8. Keep the research process cumulative. Negative results may be informative, but repeatedly cycling **idea → coding → failure → arbitrary new paper** without improving the underlying hypothesis wastes time and tokens.
9. Do not overcorrect into endless feasibility audits: sometimes a bounded implementation/experiment is the right way to investigate uncertainty. Conversely, do not run a huge benchmark before checking the critical assumption.
10. The user should not have to repeatedly redirect the advisor to the original research goal. At every major decision, re-read **Section 0, Section 12**, the historical counterexamples and relevant primary evidence. Surface disconfirming information **before** proposing an experiment, not only after the user points it out.

## 3. Fundamental technical distinction: two kinds of tool knowledge

**Ordinary tool registry:** ROSA supplies generic tool names, descriptions, accepted arguments, and mechanisms to discover ROS nodes/topics/services. For example, a generic `ros2_service_call` invokes a service named by the agent. Different agent frameworks have different wrappers, but the idea is similar.

**Application-specific semantic map:** Previous research controllers stored entries equivalent to `requested information field → endpoint/service → extraction rule`, with schemas such as `map.frame_id`, `pose.y`, `manager.active`, etc. That is **much more than a tool list**: it pre-solves a substantial part of each application task.

**Hard constraint:** Do not require a handwritten per-task or per-application answer/source map inside the proposed **general** algorithm and then claim the method transfers to new applications. Ordinary interface adapters that connect to ROS/other frameworks are acceptable. Runtime metadata extracted from genuine tools/docs/observations is acceptable **if its collection cost, accuracy, and availability are accounted for**. Do not give the treatment semantic information that controls lack without an explicit fair accounting. A tool schema alone may not reveal the semantics of a custom service: that is a real limitation, not something to gloss over.

**Generalization question:** What is the minimum input a reusable policy needs? Which portions are supplied by the model, ordinary tool interface, runtime discovery, existing results, inferred dependencies, or learned experience? What happens for a previously unknown service or another framework?

## 4. Research roles and rigorous standards

### ChatGPT — research advisor

- Own research direction, technical mechanism choices, parent-paper comparison, experimental logic, and skeptical interpretation of Codex output.
- Consult prior Project conversations, research summaries, source code and ZIP evidence before declaring success, failure, or asking for major rewrites.
- If possible, directly inspect code, protocols, raw traces, and scorer. Report verification limits when evidence is unavailable.
- Explain to the user **why** one method is worth trying and why plausible alternatives are not presently prioritized. Do not cherry-pick two papers out of a larger known list.
- Avoid performative “final” declarations and invented grand terminology. No unconditional agreement.

### ChatGPT Work — independent academic investigator

- Independently search and read **primary literature and prior mechanisms** before adopting a candidate; trace alternative terminology, older work, and the closest simple method.
- Develop and critique competing mechanisms without merely ratifying the current ChatGPT/Codex favorite. Record what source text was read and which claims remain inference.
- Treat research autonomy as a **traceable process and independently checkable deliverable**, not a duration claim or a report's use of the phrase "three cycles." Work can propose counterexamples and scientific direction, not just bibliography.

### Codex — code-grounded investigator and research engineer

- May inspect ROSA, literature, prototype code, perform controlled experiments, preserve artifacts, run tests, and self-critique.
- Must keep full traces (including failures), source versions, frozen task protocols, model configuration, baseline settings, verification scripts, and cost metrics.
- Its summary is a **claim**, not a substitute for external review. It must not silently adapt benchmarks, hide failures, hardcode answers, or inject privileged task contracts.
- Do not ask Codex to burn tokens on speculative repair loops or large audits when a smaller distinguishing test will answer the question.

### Roles and coordination rule

ChatGPT, Work and Codex may each originate, attack and refine an algorithm. Their outputs are **parallel peer evidence**, not a voting scheme. Keep independent discovery independent where useful, then cross-review actual differences. ChatGPT owns synthesis and user-facing clarity but must also do its own source/paper work. Only involve a researcher when the assigned task resolves a concrete open question; no forced three-party activity every round.

### Required experimental fairness

- Compare with **original ROSA** and a **strong simple control** (reasonable prompting, native batching/reuse as appropriate). Explain exactly what capabilities the simple control receives.
- Keep comparable tools, information, model, model settings, task wording, environment and execution budget. Record unavoidable differences.
- Separate development tasks from held-out evaluation. Do not tune on held-out outcomes without labeling subsequent evaluation exploratory.
- Evaluate **correctness/completeness first**, then LLM calls/tokens, actual underlying ROS operations, time, preprocessing/policy overhead, repeated discovery, error recovery and side effects. A framework-level optimizer cannot be justified solely by fewer wrapper calls.
- Distinguish expected, cached, attempted, observed, verified, failed, and missing information. Do not claim tool invocation proves real-world effect.
- An “uncertain” or interrupted episode is not automatically a failed task nor successful evidence.
- Do not claim cross-application portability from tests only on two prepared applications.
- If evidence is lost, say what can and cannot still be reconstructed.

## 5. Historical research storyboard (Research 1 → 2 → 3)

The complete original research chats may contain additional details. This is a *reconstructed consolidated history* from prior handoffs, retrieved summaries, project sources, and uploaded reviews—not a verbatim archival export of every chat. Consult source documents for exact method and scoring details.

### Stage A — Early literature, ROSA inspection and JTVR proposals (October 2026)

- Investigated NASA/JPL ROSA, its built-in ROS1/ROS2 tool wrappers and LangChain-style agent loop. Explored whether selecting/reusing information needed both to complete tasks and verify effects could reduce tool calls.
- Candidate **Bounded Joint Task–Verification Retrieval (JTVR)** proposed: evidence ledger, bounded dependency lookahead, combine task information with verification obligations, cost-aware tool retrieval. Parent ideas include Verified Tool Calls, causal filtering, retrieval and reuse. A detailed algorithm draft existed, **not proof of superiority**.
- Some early conversations were **proposal/concept-only**; later work proceeded through implementation and actual ROS 2 experiments. Do not confuse proposal examples with results.

### Stage B — Approximately Rounds 1–18: evidence acquisition experiments

- Explored cost-aware acquisition, tool dependencies, evidence caching/reuse, provider/source-aware recovery, parameter bindings, capability discovery, ROS state/event-based revalidation and JTVR-related variants.
- Some local measurements were favorable conditionally, but methods repeatedly matched ordinary caching/batching/first-use verification. No robust general new algorithm was established.
- Fundamental risk: components relied on field/source knowledge created for the experimental application. Complex search or math did not necessarily yield an improvement beyond strong controls.

### Stage C — Rounds 19–24: routing, compilation, execution policies

- R19 tool routing / reducing tool menus: routing cost and mistakes could outweigh benefit.
- R20–21 early delegation, hybrid deterministic/LLM continuation, grounded request compilation: stronger prompts or ordinary fallback matched or exceeded much of the improvement.
- R22 evidence invalidation/causal recovery: advanced causal behavior was not superior to a simple verify-before-retry control on those tests.
- R23 ROS 2 action feedback: action-status-aware simple control covered observed gains; extra feedback probes could add overhead.
- R24 concurrency / dependency graph priority / learned provider cost: standard ready-list/concurrency controls explained many savings; no established incremental algorithmic advantage.

### Stage D — Rounds 25–26: conditional gains but strong adapted control

- Graph-aware information controller integrated into LLM-driven ROSA, with predefined information fields, ROS graph binding, service/topic/parameter acquisition, validity checks, fallback and sometimes batching/concurrency.
- A historical 16-task mutually-correct comparison reported native reads **47 → 32**, LLM calls **46 → 32**, input tokens **177,890 → 30,911**, episode time **194.36 s → 45.86 s** versus a ROSA configuration. These were **conditional results**; they do not isolate a new general algorithm or remove adapter advantages.
- Against the stronger *simple graph-aware controller* on 22 feasible matched tasks, complex candidate D was **not better**: simple 42 data reads / 64 tool calls / 44 model calls versus candidate 44 / 66 / 44.

### Stage E — Rounds 27–28: cross-application failure, critical correction

- Nav2 MapServer/lifecycle application exposed significant errors: wrong semantic source, confusion between observed and configured values, omitted requested lifecycle fields.
- R27 requested-field coverage **6/14** for graph controllers versus **14/14** for original ROSA (coverage is **not** equivalent to fully correct facts). R28 selective candidate **6/8** versus better controls **8/8** on reported feasible cases.
- Source examination later confirmed `round25/application.py`, `round27/application.py` and `round28/method.py` contained manually prepared field/source/extraction mappings. The user repeatedly challenged this as unfair/generalization-limiting; the advisor had failed to flag it early enough.
- **Do not resurrect these adapters as the main algorithm.** Preserve their source/results as historical engineering and a cautionary baseline.

### Stage F — Research 3 reset, AutoTool feasibility and archive migration (November 2026)

- A read-only parent-paper feasibility probe examined old traces and returned *insufficient evidence* for history-based continuation. An AutoTool-focused Codex mission stopped before implementation because an overly strict prompt required a convincing differentiator in advance. **No AutoTool end-to-end pilot was run in that mission**, so do not report “AutoTool failed experimentally.”
- User explicitly rejected both extremes: **inventing results via adapters**, and **blocking every uncertain experiment with another two-minute audit**.
- Old work was archived. Active path remains `/home/levinsonchen/project/rosa-research`; old worktree `/home/levinsonchen/project/rosa-research-archive`. Existing changes/commits and backup were preserved according to Codex migration reports. Do not rewrite history or alter archive casually.
- `rosa-llm` is a separate custom model-integration package for GPT/OpenAI and Ollama. Codex subsequently reported that the `0.2.0`-labeled integration commit source was older/identical to working `0.1.0`, so environment stayed `0.1.0`; do not assume version bump is necessary. No paid API inference without explicit permission.

### Stage G — Clean tool-menu retrieval experiment (November 7)

- On 12 tasks (reported supported completion): original ROSA **8/12**, strong simple full-menu prompt **10/12**, simple lexical retrieval **6/12**, retrieval candidate **7/12**.
- Smaller tool menus saved some prompt tokens but harmed ability to locate tools/facts. Candidate not promoted. No old semantic adapters in candidate.

### Stage H — Multi-step dependency experiment and evidence loss (November 7)

- Structured dependency mechanism tried to run tool calls from prior results, but the local model **never generated dependency references** (`$ref`, `$item`, `foreach`). Candidate cost more than the stronger batch control in mutually supported pairs: **77 vs 63 model calls**, **573,081 vs 450,795 input tokens**.
- **64 of 72 intended episodes** ran; eight unattempted due to time cap. Candidate underperformed; zero dependency adoption does **not prove** the underlying dependency idea intrinsically bad.
- Raw traces for that run lived only in `/tmp` and disappeared on device restart. A later reconstructed ZIP contained only available source, protocols, summary results and manifest, **not the 64 original traces**. Do not present the reconstruction as a full raw replay.

### Stage I — Baseline diagnostic (November 7)

- **36 primary episodes + 8 replays**. Results conservative: original ROSA **9/12** correct; ordinary strong prompt **10/12**; batching-enabled control **8 correct, 3 incorrect, 1 uncertain**.
- On the batching-enabled condition, 23 redundant CLI reads recorded in 6/12 episodes, but potential saved CLI-only duration on supported outputs reported **5.54 s**. This did not establish meaningful saved LLM decisions or a strong new algorithmic opportunity. It *did* show repeat reads and certain answer interpretation failures.
- No new algorithm built in this diagnostic. Raw traces were preserved in a persistent artifact ZIP.

### Stage J — CodeAct-style read-program pilot (November 7–8)

- Parent paper: **CodeAct (2024)**, LLM emits small code that uses tool outputs to choose subsequent calls. Codex implemented a **bounded read-only Python subset** over ordinary ROSA tools, not arbitrary execution nor handwritten semantic task mappings.
- The idea genuinely activated: e.g., discovery yielded three node names; one emitted program read the corresponding parameters in sequence without repeated LLM decisions. In one supported case candidate versus *original ROSA*: model calls **2 vs 4**, native ROS operations **4 vs 7**, time **26.23 vs 56.37 s**. **Only one example; not evidence of superiority over the strong control.**
- Among **nine model-authored programs**, **five rejected before reads, three partial, one completed**. Model often emitted syntax unsupported by the limited interpreter.
- Primary comparison was interrupted and lacked required closing state snapshots. Separate continuation had no valid same-task B-versus-candidate pairs; therefore **efficiency against the strongest simple control is inconclusive**. Do not promote CodeAct as validated or claim a new algorithm by integration alone.
- Current recommendation is **not locked**. Further work may compare candidate against controls, or pivot to a carefully differentiated framework-level policy, but *must not* reflexively launch another lengthy experiment or automatically patch every Python syntax error.

## 6. Literature: parent mechanisms, not a narrow paper filter

Research references already discussed include (non-exhaustive): **CoALA** (agent architecture and memory; conceptual vocabulary), **LangGraph** (graph orchestration), JTVR/Verified Tool Calls, **CMTF / GIST-CMTF**, **DTDR**, **AutoTool (AAAI 2026)**, a different **AutoTool (ICML 2026)**, **In-N-Out**, **DRAFT**, **Tool-REX**, **ToolScope**, **HyperAgent**, **CodeAct (2024)**, **LLMCompiler (2024)**, **ReWOO**, Sherlock, Lookahead-R, and 2026 agent-workflow/middleware/tool-making work.

**Selection rule:** Look for any useful mechanism in tool selection, tool execution, information gathering, planning, caching, adaptive scheduling, verification, model-decision avoidance, or framework architecture. Do not restrict by title containing “tools.” Newer 2025–2026 literature is important for novelty; older foundational papers are still valid as parents. Check actual methods/evaluation and required expert mapping, demonstrations, training, preprocessing, runtime metadata, and claims about unfamiliar applications.

**Do not claim every listed paper is fully code-verified.** The Project contains a separate literature audit `ROSA_Paper_Adapter_Generalization_Audit_2026-11-06.md`; read its verification status rather than inferring full verification from appearance in this inventory.

## 7. Research design possibilities — **NOT yet selected**

### Framework-level policy as a *historical design interest* (not a selected mechanism)

The user imagines a reusable **tool-execution decision component** inserted between an agent's model decision and execution of tools. The model can still decide intent and ambiguous semantics. The component might use observable tool schemas and results to decide when to run a safe, clearly determined next step without another model turn, and when to return control to the LLM.

This is **an exploration preference, not a proven contribution or a locked mechanism**. Similar principles already appear in existing agentic systems. The core open research issue is defining an *additional* decision rule or measured trade-off that ordinary scripting, LLM-written code, direct multi-tool calls, batching, reuse, or LLMCompiler do not already provide.

Possible questions:
- What decision should be made at runtime (execute, batch, reuse, ask the model, abstain)?
- What observable data makes autonomous continuation safe, without a per-application handwritten plan?
- How to combine cost and correctness risk; how to account for overhead and bad tool choices?
- How to identify cases where the method **should do nothing**?
- What should transfer when ROSA is replaced by another framework's tool registry/executor?

### Mathematical formulation (option to investigate, not proof)

A reasonable *starting abstraction* could be choosing a policy `π` that minimizes measured expected total cost under correctness/safety constraints, for example:

`minimize E[C_model + C_tool + C_policy + C_latency]` with terms normalized to comparable units, subject to `P(correct and complete) >= P(strong_simple_baseline) - ε` and safe-operation constraints.

This is a **generic objective, not novel mathematics**. It requires honest estimation and evaluation; combining time, tokens and calls naïvely can double-count costs. Formalism is only useful if it leads to a real implementable policy (such as a threshold/decision criterion) whose behavior and robustness can be compared against simple alternatives. Do not force sophisticated MDP/POMDP/RL methods or invented probability estimates just to make a paper look mathematical.

### Constraints and no-go patterns

- No hardcoded information-to-source map per user task/application; ordinary generic tool integration is allowed.
- No pretending a simple tool-loop wrapper or cached response is an original contribution without a meaningful different policy.
- No assuming the model will emit valid Python, `$ref` or other syntax without checking actual adoption.
- No treating code-generated tools as safe merely because the LLM proposes them; side-effectful ROS services need explicit guards/authorization.
- No optimizing one metric while task correctness collapses; don't conflate new prompt/tool instructions with a measured mechanism advantage.
- No endless “choose paper → prototype → fail → next paper” campaigns without an explicit cross-round learning update.

## 8. Repository, reproducibility and artifact rules

**Active main work:** `/home/levinsonchen/project/rosa-research`  
**Historical archive:** `/home/levinsonchen/project/rosa-research-archive`  
**Special package:** separate `rosa-llm` integration (GPT/OpenAI + Ollama). Working pinned package reported `0.1.0` after version/source check; recheck environment before asserting current state.  
**Other prior scratch:** `rosa-method-lab` historically used for method exploration, not necessarily current active workspace.

The repository already has an **existing `AGENTS.md` with shared development conventions**, such as readability, Git safety, real evidence, and `uv` dependency management. **Do not overwrite it with this history file**; reference this context from the existing AGENTS.md if useful.

- Keep original ROSA baseline and archived experiments intact. Work on appropriate research branches and inspect Git status before edits. No push/merge/force reset without explicit user authorization.
- Keep academic code and research source generally in English; explain results in Indonesian.
- Use local models (historically Qwen over Ollama) unless the user explicitly permits paid APIs.
- Preserve complete raw traces/protocols/candidate source/metric computation for each substantial run; compare to real ROSA and strong simple controls with equal information.
- **Do not store the only experimental evidence in `/tmp`**. Save durable raw evidence and review ZIPs under an ignored directory such as `research/_artifacts/`, and retain a second persistent backup. Two copies on one physical host are useful but not independent disaster recovery.
- Use `.gitignore` for bulky generated evidence, not as a substitute for archiving historical tracked files or Git commits. Track compact source, protocols, and human-readable reports in Git as appropriate.
- Every Codex ZIP must distinguish fully verified traces from missing/partial evidence; include hashes and manifest without leaking secrets.

## 9. Known evidence locations (historical / currently uploaded to ChatGPT)

Files may have newer versions in the active repo. Do not assume the following exact names/paths still exist on a particular local computer without checking:

- `Pasted text(7).txt` — Research 3 original handoff summarizing R1–28, goals and process failures.
- `Pasted text(8).txt` — bounded read-only audit of older ROSA methods.
- `Review Riset ROSA.txt` — archived JTVR research and methodological scrutiny (multiple versions exist).
- `ROSA_RECOVERY_REVIEW.zip` — selected Round 25–28 evidence, source and reports.
- `rosa-parent-feasibility-evidence.zip` and `rosa-autotool-focused-pilot-20261106.zip` — **read-only** AutoTool feasibility evidence, not new successful AutoTool experiments.
- `ROSA_Paper_Adapter_Generalization_Audit_2026-11-06.md` — literature/adapter survey; distinguishes verified and unverified sources.
- `rosa-clean-restart-review-20261107.zip` — clean menu-retrieval run and Git migration evidence.
- `baseline-findings-review.md` — historical multi-step evidence review, with missing raw evidence disclosed.
- `rosa-baseline-diagnostic-review-20261107.zip` — complete diagnostic raw traces and replays.
- `rosa-paper-pilot-review-20261108.zip` — CodeAct-based prototype/evaluation and raw evidence.
- Within repo, previous studies under `research/`, including `research/baseline_diagnostic/`, `research/paper_pilot/`, `research/multistep/`, and `research/_artifacts/` (ignored evidence).

Important: ZIP reports and Codex summaries are **not automatically independent replications**. An advisor must distinguish reading the author's report, checking source, replaying scorer, and actually rerunning ROS/model experiments.

## 10. What to do in a **new research chat** (updated 2026-11-10)

1. Read **Sections 0, 1–4, 5, 8, 11–12** of this file first, then the *latest available evidence-gate report*. This avoids treating an older proposal or an ignored negative result as today's recommendation.
2. In at most a few paragraphs, state **our goal; what is proven, reported, unverified and missing; and the next decision whose outcome could change our actions**. Do not greet the user with another invented algorithm name.
3. Before advising a new research mission or run, fill the **five-question self-gate in Section 12.2** privately, cite source paths and the closest prior mechanism, and verify that a strong ordinary baseline does not already answer the question.
4. If the gate fails, explicitly state the blocker and choose a **smaller decisive verification**, a different substantiated mechanism, or an honest scoped systems result. Do **not** automatically queue another broad diagnostic or another agent task.
5. If the gate passes, deliver **one integrated plan** with a meaningful pass/fail rule, no hidden task-specific semantics, artifact preservation, and an honest deadline trade-off. The three research collaborators should not wait for the user to tell them to self-critique or consult papers.

No experiment, implementation, repo edit or external task is authorized solely because this document describes a possible next step.

## 11. Updating this living document

Treat this as the **canonical narrative**, not an immutable set of instructions. After meaningful progress, update it rather than creating another disconnected chat-specific handoff.

1. Change **Version** at the top, and update the *current status* in the summary / relevant sections.
2. Add an entry to the **Change log (Section 13)** with date, what was decided, evidence path(s), outcome, and remaining doubt. Separate **fact**, **interpretation**, and **proposal**.
3. Keep invalidated older approaches and evidence in the historical narrative; do not erase negative outcomes.
4. Record any change of research goal or hard constraint explicitly. Do not silently replace an earlier decision.
5. If adding a paper, mark whether abstract, full paper, code, and cross-application evaluation were actually inspected.
6. If changing code, record repo branch/commit and whether this is source-only, tested in simulation, or tested in real ROSA/ROS 2.
7. Update the copy uploaded to **ChatGPT Project sources** whenever its contents change. A local Git edit does **not** automatically update an uploaded Project file. In the repo, keep the original `AGENTS.md` and link this context document from it; do not overwrite shared guidelines.
8. Avoid versions of this file diverging across the Project and repo; designate one current copy and replace the older uploaded copy when updating.


## 12. Research governance, prior-art firewall and anti-loop rules (added 2026-11-10)

These are **operational decision gates**, not guarantees of originality or model correctness. Apply them before **every** substantial new recommendation, algorithm design, Codex/Work mission or evaluation. Prefer small, high-information tasks to long reports whose outputs cannot change the decision.

### 12.1 Fact, candidate and conclusion labels

Every technical claim should be one of:

- **F — verified primary evidence:** exact code/version/line or original event/scorer inspected by this researcher, with scope and counterevidence.
- **R — independently reported evidence:** another agent's source-/trace-based findings, not locally re-executed; specify what was and was not verified.
- **L — literature mechanism:** a cited primary paper and inspected portion; do not generalize a paper's result to ROSA without data.
- **H — hypothesis/inference:** mechanism or suspected bottleneck, with the observations that would refute it.
- **P — proposed action:** not an achieved result or user authorization.

A long report, fast or slow completion, manuscript-style citations, or an agent's claimed autonomous iterations **does not establish** experimental validation, deep coverage, or independent replication. Where important, request the verifiable research trail (queries/papers inspected, mechanism comparison, dead ends, code/trace references); never infer it from elapsed minutes alone.

### 12.2 Mandatory five-question gate (self-audit before recommending)

1. **Novelty/closest ordinary mechanism:** What exact decision is new or meaningfully altered? Identify the nearest **paper method** and best simple implementation, including prior terms/synonyms. Does the candidate do anything observably different with the **same information and capabilities**? A paper with overlapping components does not force rejection; articulate the incremental delta and its value. Do not relabel ordinary batching, a fixed composite, type binding, caching, schema naming or result packing as new without this test.
2. **Observed need and honest denominators:** What original traces/source support the bottleneck (not merely API possibility)? What evidence is missing or irretrievable? What is the realistic opportunity bound and how does it connect **directly to efficiency**, not just answer correctness? List alternative causes and disconfirming cases.
3. **Concrete policy and measurable discriminator:** State model/framework inputs, decision, state, outputs, failure mode and at least one trace in which candidate and strongest ordinary control **choose different actions**. Define what is counted: total model requests/tokens, underlying ROS operations, end-to-end time, setup/serialization, complete answer support. If the policies are identical on all cases, there is no algorithmic differentiator yet.
4. **Fair control and no hidden oracle:** Confirm actual default/strong prompts and that the strong arm is genuinely capable of batching, reuse, concurrent or parameterized tools where applicable; same verified APIs, metadata, retry rights, resource caps and actual outputs. No manual application answer map, privileged scorer data, changed task obligations, or after-the-fact weaker control. Score complete source-supported answers before costs.
5. **Nonrepeating next action:** Why is this action **not an old R1–28/baseline/CodeAct/Missions A–D repeat**? What minimal missing evidence does it collect, which future decision will change if positive versus negative, what is the stopping rule, and where will durable traces go? If no answer, **do not commission another broad research or benchmark loop**.

A recommendation that cannot pass this gate should be labeled **not yet justified**, not filled in with motivational prose. An experiment may still be justified solely to discriminate a pivotal unknown—but then it must be narrow, frozen and honestly labeled diagnostic.

### 12.3 Prior-art adjacency map (screen at mechanism level before designing)

| Mechanism family already encountered | Mandatory closest controls / literature to revisit | Status here |
|---|---|---|
| Plan/result dependencies, intermediate execution, fusion | Ordinary native batch, same-path fixed composite, LLMCompiler, ReWOO, LLM-Tool Compiler, CodeAct | Generic savings from one fewer model boundary are not novel alone. |
| Graph-aware/runtime relation traversal | Public ROS typed graph API, normal parameterized workflow helper, fair same-metadata registry | Cross-family path feasibility is not broad generalization or policy superiority. |
| Tool-menu retrieval, generated functions, interface names | Complete compact dispatcher, fixed naming/alias policy, PA-Tool, DocsChisel, ToolScope, State-Path Menu | Schema/adoption gains require measured token/adoption trade-off and fair complete controls. |
| Error checking, constraint repair, stale state | FQN assembly, ordinary validation/retry, standard event invalidation/refresh, SCA, Gecko | Staleness not evidenced in preserved baseline; no atomicity guarantee from graph presence. |
| Adaptive batch repair | Native ListParameters/GetParameterTypes/GetParameters, singleton fallback, group testing, same retry budgets | No source-grounded policy superiority yet. |
| Evidence delivery, compression and answer grounding | Fixed compact table/mixed serializer, factorized query results, TAP4LLM, complete evidence receipts | Reversible formatting alone is known; relation to answer quality/input tokens must be measured. |
| Task-to-source/answer obligation compiler | Strong prompt and full-answer independent scorer; manual semantic maps prohibited in policy | Historical generalization and coverage failures; no hidden task oracle. |

This map is **not an exhaustive world literature review**. Any new candidate triggers synonym searches, backward/forward related work, examination of the closest method's actual mechanism, and a recorded delta **before** code. If a closely related paper emerges after a recommendation, update this map and openly revisit the earlier claim; don't restart from zero or pretend the relationship was unknowable.

### 12.4 Autonomy and collaborator handoff

- All three entities (ChatGPT, Work, Codex) should independently search, generate, attack and refine when the question warrants it. No hierarchy of who is "more autonomous"; role specialization is for efficiency, not epistemic privilege.
- A well-scoped independent mission must include: objective and known negative history, source corpus, primary literature, >=1 simple hostile comparator, concrete mechanism/counterexamples, *multiple actual analysis passes*, a decision/rejection rule, deliverable and stop condition. It should continue exploring distinct candidates within its authorized scope after one rejection, but must not hide uncertainty or invent new algorithm labels to imply progress.
- Prefer **parallel independent designs** when two different skill sets genuinely inform a decision; prefer **one code audit** when only repository/trace facts are missing; prefer no extra agent when answer is already established. Later cross-review should confront disagreements with shared facts rather than select by vote.
- ChatGPT must itself check critical prior art and source evidence rather than delegating all thinking. Never imply that a user must spend time reading every paragraph to catch a preventable contradiction; offer a concise evidence-backed recommendation and one explicit next step.

### 12.5 Decision ledger and resource/accounting rules

- Classify each direction as **exploring**, **conditionally retained**, **rejected for this scope**, **systems integration only**, or **empirically supported**. Record the specific falsifying evidence and whether a different environment might reopen it. A NO-GO does not prove global impossibility.
- Avoid open-ended research prompts after repeated negative audits. Two parallel missions or a large test suite need **distinct information value**; if they would likely reiterate existing evidence, stop.
- Every stage should produce a small, durable **decision ledger**: *what changed since the last stage? why did we change course? what is newly known vs already known? what would overturn this decision?* Keep the historical failures in the same canonical file.
- Track source-revision and experiment state separately. New Markdown reports and offline parsers do not count as new ROS/model experiments. Preserve original traces/protocol/ground truth in persistent `research/_artifacts/` or another deliberate repository-relative destination, with manifest and backup; never rely on `/tmp` alone.
- Correctness/coverage, research novelty and efficiency are **three distinct questions**. A better error message is not automatically fewer model calls. A lower wrapper count is not automatically fewer native ROS reads. A lower cost on the original weak prompt is not evidence of a win over a genuinely activated strong control.
- For the 2 December presentation, prioritize a truthful executable test of one justified claim over another unvalidated ambitious controller; do not turn the deadline into a reason to label an ordinary method "novel".

### 12.6 Known advisor/process errors acknowledged and corrective rule

| Error in previous guidance | Correction that must occur *before* the next recommendation |
|---|---|
| Proposed GLBE/CCVT/alias/packing advances before giving their best simple competitors full parity | Identify same-path parameterized helpers, fixed mixed layouts and paper overlaps before deciding that an idea is an algorithmic contribution. |
| Raised the prompt-level batching prohibition as though it were new late in the conversation | Baseline/architecture audit is required at the **start**; distinguish prompt restriction from tool/runtime capability and read earlier reports. |
| Repeatedly pivoted into generic feasibility reports and a proposed 22-cell diagnostic despite prior ROSA baselines | Before authorizing a run, write the distinct decision it resolves and check old raw/source evidence; otherwise do not run. |
| Sometimes treated a literature appearance as a veto, then looked for a new algorithm name | Investigate the *exact incremental delta* and when it helps; originality can be meaningful recombination/adaptation, not only invention ex nihilo. |
| Proposed next steps that sounded definitive although evidence/autorization was missing | Label hypothesis, design, experiment, independent verification and user authorization separately; don't claim success or a selected algorithm prematurely. |
| Allowed the user's repeated objections to serve as quality control | Perform these checks autonomously; inform the user only of remaining real decisions, and correct mistakes proactively. |

**Next-state handoff as of 2026-11-10:** No new algorithm or broad benchmark approved. The evidence-gate audit has narrowed historical facts; the next algorithmic move must pass the gate above, not be another unbounded baseline-failure search. If a genuinely unmeasured action contrast can be articulated, pursue the smallest frozen experiment; if not, state the remaining research decision honestly rather than circling.

## 13. Change log

- **2026-11-10 (evening, post-CPAW):** Independently audited `CPAW_REVIEW_PACKAGE.zip` and review document `CPAW_Independent_Review_and_Research_Lessons_2026-11-10.md`: 21 tests, 720 synthetic trace audits, expected 4.009 CPAW vs 3.943 best fixed vs 3.922 exact adaptive in 12 small unrestricted instances; none of 47 default ROSA tools satisfies CPAW’s *strict proposed contract*; no end-to-end ROSA/LLM evidence; archive CPAW and reuse testing infrastructure only. Separately inspected `member/martin` bounded-macro code/docs: explicit application-authorized fixed skill catalogue; teammate approach remains a reference, not our selected optimization. User observed repeated process failure: the advisor recommended directions before applying the existing Section 12 research gate. Section 14 records the operational correction, without replacing prior constraints.

- **2026-11-08:** Consolidated Research 1–3 into a single handoff; recorded R1–28 limitations, manual semantic adapter discovery, post-reset negative experiments, CodeAct pilot as inconclusive, the proposed framework-level research interest, optional mathematical modeling, and the December 2 presentation deadline. **No new algorithm selected or experiments performed by producing this document.**

- **2026-11-09:** Independent Missions A/B investigated novelty and ROSA source: composed/compiled JSON tools are technically feasible, but a complete compact parameterized helper is a decisive countercontrol. Missions C/D explored multiple candidates and found no defensible new algorithmic advantage; Work conditionally proposed evidence packing, Codex favored ordinary bounded integration. Neither mission implemented or ran experiments. Evidence: `ROSA_Mission_A_Research_Report_2026-11-09.md`, `ROSA_Mission_B_Code_Grounded_Investigation_2026-11-09.md`, `ROSA_Mission_C_Autonomous_Algorithm_Development_2026-11-09(1).md`, `ROSA_Mission_D_Autonomous_Algorithm_Development_2026-11-09.md`.
- **2026-11-10:** Codex `ROSA_Bottleneck_Evidence_Gate_2026-11-10.md` reported offline audit of surviving original traces, installed ROSA/ROS 2 APIs, and primary literature. It found recorded source/answer-coverage failures but no positively evidenced stale-incarnation failures; no new ROS/model inference. User challenged repetitive baseline audits and delayed recognition of prompt-level batching prohibition. This update records self-audit/novelty/anti-loop gates, corrects terminology, explicitly declines to authorize a proposed 22-cell rerun, and retains the unchanged research objective. Updating this Markdown is not a Project-source replacement or code/runtime modification by itself.


## 14. POST-CPAW STATE AND ENFORCEMENT (2026-11-10 evening) — ADDITIVE, NOT A REPLACEMENT

**Why this section exists:** Section 12 already contained a comprehensive, mandatory five-question gate, yet the advisor did not consistently apply it (e.g., CPAW contract feasibility discovered too late, Martin proposed as the next experiment despite known catalogue limits). Writing another checklist alone is insufficient. This addendum creates an observable *decision procedure* to ensure earlier constraints are checked before work is commissioned. It does not change, narrow or supersede the objective or constraints in Sections 0–12.

### 14.1 Current decisions — distinct statuses

- **CPAW:** `rejected for the main algorithm / retained as bounded evidence and test infrastructure`. It is NOT a general ROSA improvement; simulated task certificates do not certify natural-language answer completeness. Its DP, exact baselines, synthetic audit and eligibility inspector can be reused with stated assumptions. Do not rerun CPAW parameter tuning or build semantic adapters just to produce positive results.
- **Martin bounded macros:** `teammate reference / systems integration`. The application-authorized fixed catalogue enables execution reuse but does not by itself transfer to arbitrary newly registered ROSA tools. Do not characterize this as our independent research contribution or auto-schedule extensive Martin benchmarks. Small read-only code comparisons are permissible if they settle a clearly identified open research question.
- **Main research direction:** unchanged: `framework-level algorithmic or meaningfully incremental optimization of LLM-agent tool-calling efficiency in NASA/JPL ROSA`, preserving source-supported correctness and full answer coverage. We have **no selected main algorithm**.
- **No automatic pivot:** A new approach is not selected simply because the preceding candidate failed, or because a teammate reported reduced model calls.

### 14.2 Mandatory preflight before recommending any new experiment or Codex mission

**Owner: ChatGPT (research advisor), not the user.** Read Sections 0–4 and 12, the most recent results and closest negative experiment. Apply all existing requirements, not just a newly abbreviated five-point list. Before asking anyone to implement/run, produce a brief internal or written decision record containing:

1. **The real observed opportunity:** original trace or actual ROSA tool/API behavior, exact denominator and cost. Don't derive an efficiency opportunity solely from correctness faults.
2. **A concrete general mechanism:** framework-observable inputs, state, output and action difference vs the strongest simple control. No application-specific semantic catalogue, benchmark-provided oracle, automatically trusted tool equivalence, or unjustified typed-contract assumption. Check unchanged ROSA registry and real authorization/fallback *before* implementation.
3. **Specific incremental novelty:** exact parent papers and ordinary controls; an observable different choice in a plausible case, plus a counterexample; don't require completely unprecedented theory but don't rename prior art.
4. **Fair and complete evaluation:** deconflicted ROSA prompt (original prompt forbids batching; strong control must actually enable it), same model/info/capabilities/permissions; correctness and complete answer first; count native ROS calls, tokens, LLM calls, latency, overhead, calibration and setup. Prospective held-out tasks/tools and reproducible artifacts.
5. **Decision-changing minimum task:** why existing R1–28, JTVR, CodeAct, Missions A–D, capability discovery, CPAW, and teammate reference cannot already answer it; smallest next action; positive/negative branch and stopping rule; estimated scope vs Dec 2 deadline.

**Fail-closed rule:** If a material requirement is unknown or contradicted, label it `BLOCKED / NOT YET JUSTIFIED`, name the exact missing fact, and do not command major implementation or model benchmarking. A narrowly justified diagnostic is allowed *only* if its result would reverse a concrete decision, with a frozen protocol and small resource cap. Do not create a new general literature review or GO/NO-GO cycle as a substitute.

**Public recommendation discipline:** When presenting a next action to the user, include one concise line stating what evidence supports it and the crucial limitation. If a prior recommendation was invalid, correct it explicitly rather than silently pivoting. The user does not act as the quality-control filter.

### 14.3 Current next action and deadline posture

- **Do not start a Martin test campaign, CPAW integration, new benchmark, or new algorithm implementation now.** None currently clears Section 12.2 + Section 14.2.
- The research task next in sequence is to formulate and independently challenge a **specific ROSA-observable, no-handmapped policy decision that a genuinely strong existing controller handles differently**, using preserved source/traces and exact closest prior mechanisms. This is a design task, **not permission for an open-ended audit**. If no such decision can be defended from existing evidence and literature, stop proposing code and prepare a scoped, truthful systems-result/negative-evidence presentation rather than claiming novelty.
- **Deadline:** 2026-12-02. Keep a viable final presentation track in parallel; distinguish documented engineering improvement from unproven algorithmic novelty. No research result is guaranteed.
- After any significant new finding, update this canonical record append-only (retain earlier negative evidence) and synchronize the repo copy with ChatGPT Project Sources. The repo's existing `AGENTS.md` is not to be overwritten: add a brief pointer to this file and Section 14 if authorized, while keeping all existing shared development instructions.

### 14.4 Practical enforcement for tools and collaborators

Codex/Work must treat the canonical context as input to each new research mission, with a structured preflight and a halt at a failed prerequisite; an assistant's confident narrative is not authorization or evidence. A generated Markdown document, a passing synthetic unit-test suite, and a strong result versus ROSA's original weak batching prompt are **not** sufficient milestones. Do not ask the user to repeatedly restate these constraints.

**Verification limit:** Neither this file nor `AGENTS.md` mathematically prevents faulty reasoning. They make violations easier to identify and stop before costly implementation. Actual source checking and critical comparison remain the advisor's responsibility.


## 15. Repository integration and local evidence pointers (2026-11-10)

The text through Section 14 was imported from `ROSA_RESEARCH_CONTEXT_UPDATED_2026-11-10.md` without alteration. The source file's SHA-256 is `0c9500b5090f4a281f154b34c081028ecba54e802e1489e10bb442b51bea834d`. This section records existing local evidence that supplements the imported narrative; it does not authorize research execution.

- [Capability discovery report](capability_discovery/REPORT.md): the local study retains its observer as an opt-in diagnostic, not authority to substitute tools. It reports 5 false supports among 7 initially supported extension pairs and 0 informative output schemas among the 47 inspected default tools. Finite agreement did not establish semantic equivalence; the study dispatched no native ROS operations. Consult the report for denominators and limitations.
- [LLM decision optimization investigation](design/ROSA_LLM_Decision_Optimization_Investigation_2026-11-10.md): a saved-evidence investigation rejected prototyping guarded decision reuse on the available evidence. Exact-context reuse is ordinary memoization; a useful cross-context guard lacked support and a demonstrated advantage over the stated strong controls. This is a scoped decision, not proof that all decision reuse is impossible.
- [CPAW local prototype report](cpaw_prototype/REPORT.md): preserve the protocols, negative and corrected results, and artifacts. Its reported 0/47 eligibility concerns the strict proposed contract for the inspected default registry, not every extension or real task; synthetic certificates do not establish natural-language answer completeness. Section 14 remains the current decision.
- [Bottleneck evidence gate](diagnostics/ROSA_Bottleneck_Evidence_Gate_2026-11-10.md): use the report and underlying surviving evidence for its stated scope; missing original traces remain missing. The proposed 22-cell diagnostic is not an approved next action.

These links identify existing local reports; this integration did not independently rerun their studies or verify every underlying claim. Keep the original reports and history intact, and append later findings with their provenance and limits.
