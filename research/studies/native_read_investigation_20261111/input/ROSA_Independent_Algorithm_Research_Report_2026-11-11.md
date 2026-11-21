# ROSA: Independent Investigation of Framework-Owned Native Tool Execution Policies

**11 November 2026 | Research/design deliverable, not a ROSA experiment | Presentation 2 December 2026**  
**Decision:** No established new algorithmic performance result; two conditional execution-layer mechanisms specified; one tightly bounded evidence question precedes any ROSA integration.

## Executive conclusion

The most defensible unexplored *place* to look is **below the tool-selection/LLM boundary**, after the model has already chosen a legal read-only operation and its literal arguments. Pinned/reviewed ROSA code shows that `ros2_node_info(nodes: List[str])`, `ros2_topic_info(topics: List[str])`, and `ros2_service_info(services: List[str])` expose list-valued interfaces but iterate their inputs with a fresh ROS CLI subprocess for each name. This is a real **source-level serialization pattern**, not yet a measured wall-time bottleneck or a new algorithm. A framework runtime could execute independent approved reads with a bounded width, preserve all individual observations, and select the width from measured contention rather than a model-authored plan. The strongest competitor is **a simple fixed-width read executor and an existing adaptive-concurrency controller**, not ROSA's current serial loop.

A second technically distinct mechanism chooses **when to pay the setup cost of a persistent ROS 2 read client instead of renting a CLI subprocess per operation**. It has a clean online decision rule related to classic ski-rental. The disconfirming case is decisive: if one persistent client is reused across many ROSA queries, the ordinary always-persistent design can dominate the adaptive one. It is not currently justified as the preferred research implementation.

**Research decision:** Prioritize a **bounded, source-preserving native-read scheduling comparison**, *conditional* on recovering evidence that multiple eligible entity reads occur often enough and that their critical path contributes materially to wall time. Do **not** build a broad new optimizer, use code-generated plans, re-run the old 22-cell baseline, or claim novelty. If the evidence cannot establish useful workload incidence, retain this as a documented systems improvement prospect, not the final algorithm. The strong ordinary control and unforced full-answer tests are mandatory before claiming anything beyond source-level feasibility.

For the student-facing summary: *Kandidat yang paling masuk akal sekarang bukan membuat model mengarang workflow. Model memilih operasi dan node seperti biasa; framework hanya menentukan bagaimana daftar operasi baca yang sudah dipilih dijalankan. Kita menemukan loop subprocess serial di source, **belum menemukan bukti** bahwa mengganti loop itu akan memberi keuntungan penting dibanding implementasi sederhana. Langkah berikutnya sangat kecil: cek apakah daftar multi-node benar-benar sering muncul dan berapa biaya native read-nya dari trace yang masih utuh.*

## 1. Evidence provenance, scope, and non-negotiable boundaries

### What I inspected versus what was reported

| Evidence | Level | What it establishes | What it does **not** establish |
|---|---|---|---|
| Attached canonical `ROSA_RESEARCH_CONTEXT_UPDATED_2026-11-10.md`, especially §§0, 12, 14, and supplied ZIP manifest | F for the document's statements, R for its historical measurements | Research rules; original batching prompt conflict; chronology; negative findings; explicit prohibition on unaudited next runs | Independent experimental replication |
| `ROSA_Bottleneck_Evidence_Gate_2026-11-10.md`, Missions A–D, focused November 10 investigations, original clean baseline source audit | R | 36 original baseline episodes reported; native failures; already explored alternatives; audit of some source and traces by earlier researchers | Raw traces/scorer independently replayed here |
| Downloaded/read `src/rosa/prompts.py`, `src/rosa/rosa.py`, `src/rosa/tools/ros2.py`, `src/rosa/tools/__init__.py` from available `Lelevinson/rosa-research` GitHub default branch | F for inspected remote source | Exact prompt restriction, tool signature/CLI loop, registration and invocation hooks | Identity with user's *current local* ROSA/WSL checkout; timing on ROS hardware |
| Bundled capability discovery code/report, CPAW source-review package and previous CPAW review | F for provided code and ZIP integrity; R for previous test/trace replay | No sufficiently informative semantic output contracts in default ROSA inventory; CPAW not a demonstrated general solution | A new ROSA/LLM experiment or independent replay of all CPAW computations |
| Academic primary sources below | L | Prior methods and their mechanisms | An ROSA-specific speedup |
| `offline_decision_examples.py`, four passing unittest checks and generated JSON | F for deterministic **toy arithmetic only** | Checkable action differences and counterexamples | Measured ROS/LLM calls, operational parameter estimates, correctness or end-to-end gains |

The supplied evidence bundle is **curated, not a complete raw history**. It does not include the original full baseline diagnostic ZIP, CodeAct raw evaluation ZIP, complete R25–28 traces/scorers, or the standalone November 6 adapter-paper audit. Those may still exist in local persistent archives or elsewhere in the Project Library. **Sixty-four original structured-dependency run traces were lost from `/tmp`; no reconstruction restores those events.** This limits independent reconstruction and forbids causal claims about why the dependency model failed beyond preserved summaries. The GitHub default branch files examined here also cannot verify the active WSL commit; the purported local commit `94af...` was not present in the queried public GitHub repository. Reconfirm files/SHAs before a Codex implementation.

Established experimental numbers **reported by earlier Codex work**, not rerun here:

* Initial baseline: 36 episodes (12 × 3 arms); supported outcomes original 9/12, ordinary strong prompt 10/12, historically labeled batching arm 8/12 with 3 incorrect and 1 uncertain. The latter retained the **no-multiple-calls default** and did not prove activation of generic list batching. It is not the fair final control.
* 264 underlying native baseline commands, with **14 identical command repeats** (not known cache-safe), **10 native failures in five episodes** attributed to namespace/node FQN assembly (an ordinary validation-helper opportunity), **3 wrong-source answer judgments**, and **5 omission/interpretation judgments**; these categories may overlap and do not quantify execution acceleration.
* Maximum observed delivered message <4.4 KiB in inspected baseline/pilot traces; no demonstrated output-overflow recovery opportunity.
* R25–26 conditional 47→32 native reads and 46→32 LLM requests against a ROSA configuration, but against the matched simple graph-aware controller the complex R26 candidate was not better: 44 vs 42 reads, 66 vs 64 calls, **44 LLM calls each**. Earlier controllers used manual field→source→extraction mappings. R27 generalization coverage **6/14** vs original ROSA **14/14** reported, where coverage alone is not factual correctness.
* Structured `$ref`/`foreach` dependency syntax had zero observed model adoption, and mutually supported comparisons reported **77 versus 63** model requests (candidate vs stronger batching control), with original episode traces since lost. CodeAct subset: **one complete program / nine authored**, three partial, five rejected before reads; no completed matched strong-control comparison. Tool-menu retrieval dropped supported completion from strong 10/12 to 7/12 candidate on a different 12-task study.
* CPAW's earlier independently reviewed 12 small synthetic instances: candidate expected 4.008656, best fixed 3.943446, exact adaptive 3.921982; **0/47** default tools matched its strict authorization/tri-state contract. CPAW remains a bounded negative prototype, not our algorithm. Martin's bounded fixed catalogue is a teammate's application-authorized systems reference, not a general unknown-tool controller.

**Research constraints preserved:** No application/benchmark semantic answer maps; no hidden task-derived tool/source equivalence; no hallucinated output certificates; no automatic mutator execution; no trained/replaced LLM; unsupported/ambiguous decisions return to the LLM; keep unchanged task wording, information, model/params, permissions, and output obligations; include strong batching-enabled baseline; measure model calls, tokens, underlying ROS operations, cost and actual latency; preserve failures and full-answer evidence. Work on safe branches, preserve `AGENTS.md`, no paid model inference without authorization, save durable original traces outside `/tmp`.

## 2. ROSA architecture: exact entry point, not an imagined executor

The **inspected remote source** has:

```python
# src/rosa/tools/ros2.py — simplified representation of inspected code
@tool
def ros2_node_info(nodes: List[str]) -> dict:
    data = {}
    for node_name in nodes:
        success, output = execute_ros_command(f"ros2 node info {node_name}")
        data[node_name] = output if success else {"error": output}
    return data

# execute_ros_command calls subprocess.check_output(command, shell=True)
# ros2_topic_info(topics) and ros2_service_info(services) use the same pattern.
```

Thus a **single LangChain tool invocation is not necessarily a single native ROS operation**. A list of five nodes still launches five native commands serially. Other ROSA wrappers already have distinct behavior; `ros2_param_get(node_name, param_name)` invokes one CLI per call and `ros2_topic_echo(count)` performs repeated sampling with timing semantics. Do **not** infer that all calls are independent just because they are read-only: ROS graph and parameters may mutate, topic echos have time/sample semantics, and different outputs lack a global snapshot guarantee.

`src/rosa/prompts.py` instructs one tool at a time, `src/rosa/rosa.py` builds a LangChain `AgentExecutor`, and `src/rosa/tools/__init__.py` registers decorated callables. The existing prompt condition must be **replaced** for all optimized arms; appending a contradictory message is not an effective control. LangChain asynchronous gathering can execute already-emitted independent actions, but it does **not** make a synchronous ROSA list-wrapper's Python for-loop parallel. Both layers must be accounted for separately.

**Security qualification:** `shell=True` and interpolation of tool arguments raise command-injection concerns. A research executor should use reviewed `subprocess.run([...], shell=False, timeout=...)` or a typed ROS client, validating entity arguments. Apply this remediation to **every** compared executor to prevent attributing security refactoring or lower Python startup overhead to the new policy. Deny mutating commands and arbitrary generic ROS service invocation. ROS CLI may already use an optional ROS 2 daemon for graph discovery; don't assume each subprocess repeats an entire DDS discovery handshake.

## 3. Autonomous investigation: four genuinely distinct opportunities, with attacks and revisions

### A. Model-authored dependency programs / runtime chains — **rejected as primary direction**

**Original thought:** On discovering nodes, automatically call dependent parameter reads without another model decision; reduces model-round trips, addresses stronger bottleneck than pure tool latency.

**Prior art / countercontrol:** ReWOO binds earlier results into planned references; LLMCompiler generates a tool DAG and dispatches ready calls; CodeAct supplies executable programs; an ordinary parameterized helper can loop over discovered names. Historical R25–28 and Missions A–D showed the helper/composite ties much of the purported novelty. Crucially, local model generated neither structured references in one study nor reliable code in the other.

**Revised decision:** A new model-independent executor cannot know which unknown service's semantic output should map to a user request without supplied plan/knowledge. Guessing adds wrong-source or omitted information risk. Building a typed fixed helper is worthwhile engineering but not a new research advantage here. **Do not revive under a different compiler name**. Retain code/program paths as strong comparison points if a future system can actually adopt them.

### B. Semantic relation cover, capability discovery and evidence optimization — **not prioritized**

**Original thought:** Query from both sides of a ROS node↔topic relation; choose a minimal mixture of graph reads, or infer tool equivalences from output descriptions to avoid redundant calls.

**Attack:** The November 10 graph-read studies already derived a plausible exact-cover advantage against one-directional and greedy graph plans, but the separate six-request workload check reported **no qualifying mixed cases**; ordinary directional/fixed helpers cover the observed requests. Empirical capability discovery had false positives when different sources happened to return similar values; default tool schemas did not define source-level semantic equivalence. Earlier semantic mappings degraded cross-app completeness. A graph view is not a robot-state certificate.

**Revised decision:** A mathematical graph-cover win on fabricated pair sets does not demonstrate a ROSA task distribution. No new benchmark selected; do not claim unscreened arbitrary API transfer. If truly new observed pair-list workload later emerges, the exact-cover approach deserves separate attention—but that is not today's chosen path.

### C. Framework-owned native execution width — **conditionally retained, highest priority**

**Observed API opportunity (F):** `ros2_node_info`, `ros2_topic_info`, `ros2_service_info` loop over native CLI subprocesses **serially after literal arguments are already fixed**. No extra language planning is necessary to dispatch them differently. Native operation count can remain exactly the same; model answers receive the same complete per-entity observations.

**First design:** Parallelize all reads in one list; compare ROSA's serial loop. **Rejected as a research claim**: this is ordinary concurrency, potentially harmful through contention, and R24 already covered static scheduling at the agent DAG level.

**Second design:** Choose concurrency `k∈{1,2,4}` based on passive runtime evidence and admitted operations. **Still not automatically novel**: adaptive concurrency (AIMD, congestion controllers, Netflix concurrency-limits, adaptive database query execution) is established. The only possibly defensible increment is *ROSA-specific execution-boundary integration with unchanged source-keyed result obligations and a policy that outperforms a best ordinary fixed/adaptive limiter*, across real varying load. If it does not, label the outcome systems integration.

**Hostile competitors:** (i) serial identical subprocess backend; (ii) best fixed k=2/k=4, chosen on development data and frozen; (iii) existing generic adaptive concurrency controller with identical telemetry and safety limits; (iv) bounded persistent typed ROS 2 executor if applicable. The strong reference prompt **must** be deconflicted. Evaluate source-stability and completeness before speed.

**Critical missing fact:** We have a *source-level* eligible class but no audit of **actual `n≥2` model-issued list-wrapper calls and their native critical-path durations** on surviving original traces. Even if many native reads exist in aggregate, most could be singleton reads or dominate neither latency nor decisions. **If that is true, there is no compelling efficiency hypothesis for this layer.**

### D. On-demand persistent ROS transport (rent-or-buy) — **conditionally specified, secondary**

**Observed API opportunity (F):** ROSA's inspected `execute_ros_command()` creates a process per read. A reusable `rclpy` read client could in principle avoid repeated process startup. Unlike C, this policy chooses backend lifetime and changes fixed initialization cost, not concurrent scheduling.

**First design:** Always create a persistent `rclpy` client. **Ordinary baseline**, very likely best when a long-running ROSA service reuses it; not a new algorithm.

**Second design:** Execute a few reads using CLI, create the persistent client only if the accumulated CLI premium justifies setup. Classic **ski rental**: a known online fixed-cost decision, not novel alone. This gives a genuine, checkable action difference if sessions vary in length and require cold client creation, but it also introduces setup at the worst time for long sessions.

**Critical unknowns:** Real setup, per-call steady-state overhead, whether ROSA lifetime is per task or shared across turns, per-tool typed API parity (including errors/status), node lifetime/namespace races, and persistent client thread safety. **Don't implement before resolving these**, especially because the old reports already inspected usable `rclpy` parameter clients and may have solved the transport problem with an ordinary client.

### E. Lower-risk failure remediation and passive observability — **systems integration only**

A generic FQN normalization/validation helper directly addresses 10 reported native failures in five episodes, unlike hypothetical staleness guards; this can reduce retries and improve answers. Strongest baseline is precisely that ordinary helper. A typed event ledger distinguishes attempted, observed, errored and missing values, but without application semantics it cannot certify full natural-language answers; fully identified omission detection requires an external scorer. **Implement as shared safety/control infrastructure, not new algorithm.**

## 4. Algorithm specification 1: conservative native-read width controller

**Working label:** Native-Read Width Admission (NRWA), a *research candidate*, not a novel named discovery. No new tool is exposed to the model; selection operates only inside explicitly reviewed read-only wrappers. The model still chooses task-relevant tool and exact nodes/topics/service names; the framework may execute *already-authorized* exact reads differently.

**Inputs:** public tool name; validated literal array of `n` entity names in original order; executor safety/timeout budget; previous passive per-tool execution latencies, timeouts and concurrent operations; current backend concurrency occupancy. **Not inputs:** text-answer requirements, hidden benchmark labels, application-specific source maps, user-question-derived guessed mappings, previous values as timeless certificates.

**State:** per tool family/backend and coarse workload regime: `(n, chosen k, individual native status, time, in-flight/queue time, timeout, completed keys)`; compact bounded historical statistics; policy choice and observed duration; no history-implied freshness. On newly registered tools without reviewed effect contracts, **no optimization**. Never equate a tool description with a trusted read-only proof.

**Output:** same logical result mapping from the original wrapper, one exact key per original input (including duplicate-key contract explicitly documented if changed), all successes/errors/partial results, original returned observations without semantic alterations; per-item provenance/timing logged separately. Preserve duplicates internally by stable `(position, name)` even when the public dict would collapse duplicate names. Do not report a whole successful batch if any member failed. No model-invisible retries. Writes, motion, generic `ros2_service_call` and `ros2_topic_echo` **not eligible**.

**Eligibility:** explicitly allowlisted `ros2_node_info`, `ros2_topic_info`, `ros2_service_info`; `n≥2`, valid literal names, identical credentials/namespace/ROS graph observability, no known ordering-sensitive read; bounded timeout, rate/CPU load and side-effect restrictions. If the source's actual observed completion semantics require strict temporal order, run `k=1`. If returned output can't be associated with a requested exact entity, return an explicit unresolved/error record; never guess the association.

**Policy (design, not measured):** Use `k∈K={1,2,4}`. Before adequate passive samples, choose the conservative shared default (possibly `1`; do not call it an optimization). With calibrated observations, for comparable `(tool, batch-size, load)` contexts select a width with lowest estimated *end-to-end native batch makespan* **subject to** failure rate and resource constraints. Include exploration/calibration expense; fix a development-only calibration schedule, then freeze it. A simple EWMA/empirical-quantile selector is an implementation baseline, not mathematically calibrated correctness. Compare against generic adaptive limiters with exactly the same observations. Do not invent confidence bounds based on insufficient samples.

Pseudo-code:

```text
execute_authorized_read_list(tool, names, context, history):
    validate exact tool allowlist, arguments, n, resource limits
    if not eligible: return original safe serialized read routine
    k = select_from_{1,2,4}_or_conservative_default(context, history)
    launch bounded queue of read-only exact native operations, max k in flight
    for every original position i:
        record terminal status, exact stdout/value or error, time and input identity
    if timeout or failure: do NOT fabricate missing values or auto-retry
    compose complete legacy-compatible per-name response, preserving statuses
    append measurements including dispatch, queue, policy and subprocess overhead
    return response to LLM; LLM remains answer/repair decision-maker
```

**Concrete conservative policy implementation:** Maintain separate, capped rolling windows of at most 30 fully observed batch durations for each `(tool_family, n_bucket, predecision_occupancy_bucket, k)`, with `n_bucket ∈ {2–3, 4–7, ≥8}` and occupancy buckets `{idle, busy}`. Record all attempts, including timeouts as censored losses (never drop them). If fewer than 10 comparable observations exist for **every** candidate width, choose the documented common safe default `k=1`; supervised, **charged** development-only calibration can fill those windows without using answer labels. Otherwise choose the `k` with the smallest observed 90th-percentile end-to-end native batch time, *only* among widths whose observed failure fraction does not exceed the predeclared common control limit and current process budget. Break ties toward smaller k; after two consecutive timeout/overload events force k=1 for the next admitted batch and log the fallback. Freeze `n_bucket`, sample count, percentile, overload rule and limits **before** held-out evaluation. These values are **engineering defaults needing calibration**, not derived optimal constants or statistical guarantees. The strongest ordinary adaptive-controller baseline must receive the same calibration opportunities, observations and safety cap. If it ties or wins, this is not evidence of a new algorithm.

**No cross-entity snapshot guarantee:** Graph membership may change between reads. Parallelism alters observation time and can alter values; the claim is equivalence of *requested operations*, not bitwise equivalence of time-dependent observations. For correctness comparisons use stable frozen fixtures *and* moving-state stress fixtures that score provenance and partial/uncertain handling. The backend need not be `shell=True`; use the safe same wrapper in all test arms.

**Formal cost/accounting:** For observed operation batch `b` with choice `k`, define

\[
T_b(k)=T_{\mathrm{validate}}+T_{\mathrm{queue}}+T_{\mathrm{execute}}(k)+T_{\mathrm{serialize}}+T_{\mathrm{policy}}.
\]

Do not sum concurrent per-read service times to infer batch latency. End-to-end agent time also includes tool-to-model boundaries and model inference. A strong batching prompt can reduce those boundaries independently; **this scheduler normally changes zero model calls and zero native read count for a fixed, already-authorized batch**. A paper cannot truthfully claim fewer LLM decisions solely from NRWA. It is relevant to the locked objective through the **tool-execution latency/cost** branch only; this narrower scope is made explicit.

For a policy `π`, a prospective validity test is

\[
\operatorname*{minimize}_\pi \mathbb{E}[T_{\rm episode}]\quad
\text{subject to}~~Q_{\rm correct+complete}(\pi)\geq Q_{\rm best\ simple}-\epsilon,
~~\text{side-effect limits}, ~~\text{failures and timeout caps}.
\]

Estimate quality per paired, separately scored episode; don't pretend a finite sample can certify a hard population guarantee. For a framework claim, also report native CPU/process count, all LLM costs, and setup+calibration. **Novelty is not created by this equation.**

**Exact candidate/control contrast:** Suppose eight already-authorized `ros2_node_info` reads are submitted. A real-time load indicator and prior observed costs suggest an empirical safe width of 2 under backend contention. A fixed-width-4 executor launches four; NRWA chooses two. Under a different measured low-contention regime it might choose four while a fixed-width-2 executor chooses two. This is a *synthetic policy-action contrast* until load signals and their predictive value are demonstrated. A generic adaptive limiter may also choose correctly, eliminating algorithmic novelty. A counterexample is a stable low-load environment where fixed k=4 dominates because NRWA's monitoring and exploration impose overhead. A second is high graph churn where parallel reads have no coherent snapshot and all candidates must report uncertainty rather than fabricate consistency.

**Evidence needed to promote:** a positive occurrence count of list calls with `n≥2`, measurable batch service time significant versus agent time, load variation that defeats best fixed width, and quality-preserving wins against ordinary adaptive concurrency—not just serial. The current bundle supplies only the source-level entry point, not those empirical prerequisites.

## 5. Algorithm specification 2: online cold-start transport policy

**Working label:** Lease-vs-Client transport admission. Exact semantics must be established for a limited public read family (e.g. `GetParameters` for literal `(node, parameter)`); unknown/opaque service tools are not admitted.

Let `c` be measured marginal CLI read cost, `p` measured persistent-client marginal read cost, `S` one-time setup cost, **only under conditions where `c>p` and `S>0`**. With `n` reads in one cold lifetime:

\[
C_{\mathrm{CLI}}(n)=nc,\qquad C_{\mathrm{persist}}(n)=S+np.
\]

Define marginal premium `d=c-p`. An online threshold rents the CLI for `q=\lceil S/d\rceil` completed reads, then buys the persistent backend *before the next read* if any. Its cost is

\[
C_{\mathrm{online}}(n)=nc~~(n\leq q),\quad qc+S+(n-q)p~~(n>q).
\]

This is an **ordinary classical ski-rental-derived rule**, not a theorem that latency is competitive under stochastic setup, changing p/c, runtime races, or end-to-end ROSA time. For deterministic constants, subtract baseline `np`: the policy's excess cost over an always-available already-paid backend is at most `2S+d` when switching, versus offline premium `min(nd,S)`; if `S/d` is an integer (as in our toy), this becomes the familiar 2× premium bound. **It does not guarantee the total online latency beats both always-CLI and always-persistent on every n.**

**Illustrative, deliberately synthetic arithmetic** (`c=100`, `p=25`, `S=450` arbitrary toy time units, threshold 6):

| Exact reads in a *cold session* | Always CLI | Persistent from start | Online threshold | Clairvoyant min |
|--:|--:|--:|--:|--:|
| 2 | 200 | 500 | 200 | 200 |
| 6 | 600 | 600 | 600 | 600 |
| 7 | 700 | 625 | **1,075** | 625 |
| 20 | 2,000 | 950 | 1,400 | 950 |

Counterexample worth emphasizing: 10 separate two-read sessions plus 3 separate twenty-read sessions cost CLI **8,000**, per-session always-persistent **7,850**, threshold **6,200**, offline per-session oracle **4,850** (toy units); but one persistent client **shared across all sessions** costs only **2,450**, far better than the threshold policy. **Session lifecycle changes the conclusion.** Existing ROSA commonly lives beyond a single request, so do not build cold-start switching into the agent before verifying this important premise.

**Other concerns:** `rclpy` client setup may require a running executor/discovery and cleanup; CLI error strings differ from typed `ParameterValue`; per-call latency may be noisy; switching during a live ROS graph transition can return a different observed value. If a continuously warm observer is the ordinary application architecture, choose it and record a systems integration result rather than claiming online switching.

## 6. Prior-art firewall: strongest adjacent mechanisms

| Related primary source/method | Relevant established idea | Candidate delta and novelty verdict |
|---|---|---|
| NASA/JPL ROSA (Royce et al., 2024); inspected source | ROSA-LangChain tool integration, ROS 2 wrappers | Our evidence is a concrete serial execution pattern in *some* wrappers; not a claimed new general agent architecture. |
| Kim et al., **LLMCompiler**, ICML 2024; ReWOO 2023; Wang et al., **CodeAct**, ICML 2024 | Plan-dependent tool execution, concurrent scheduling, code programs | NRWA **does not** generate tool plans; it only schedules fixed bound inputs. The lack of plan generation is an engineering differentiation, not by itself a theoretical novelty advantage. |
| **LLM Tool Compiler**, 2024 | Runtime fusion/grouped tool execution | Any reduction claimed purely from collecting a list into one wrapper is prior art or standard batching. NRWA's question is internal execution-width selection at fixed op count. |
| Selinger et al., **System R access-path selection**, SIGMOD 1979; Avnur & Hellerstein, **Eddies**, SIGMOD 2000 | Cost-based/adaptive query operation choice and routing | General cost-based selection and adaptive execution are known. Our application setting alone is not originality. |
| Jacobson, congestion control 1988; Netflix **concurrency-limits** | Adaptive concurrency/congestion response | NRWA must beat a generic limit controller using identical observations or be declared systems integration. |
| Classical **ski rental**, e.g. Lotker et al., 2008 | Online rent-versus-buy with fixed switching cost | Transport policy is a direct adaptation, with no currently defensible novel decision rule; active pooled client is a strong simpler control. |
| ROS 2 docs: `GetParameters`/`AsyncParameterClient` and CLI daemon | Native typed read APIs, persistent daemon/cache | Transport setup and equivalence must be measured; subprocess count is not itself DDS rediscovery count. |
| Earlier R24, GLBE/CCVT, graph-selection reports, Martin bounded macros and CPAW | Static dependency scheduling, parameterized helpers, finite contracts | These already subsume many apparent novelties. Our only untested axis is post-bound native process scheduling/lifetime with fair comparable execution; no proven gain. |

**Screening conclusion:** Neither specified policy currently passes a credible *algorithmic novelty and measured advantage* threshold. Conditional limited engineering tests can still be useful research: they test an isolated bottleneck with honest controls and may reveal whether a nontrivial joint scheduling problem exists. The research should not rebrand well-known AIMD/bandits/ski-rental as invention.

## 7. Three genuine design/critique iterations and decision changes

1. **Try saving model decisions via automatic dependency execution.** This directly matches the appealing objective. **Challenge:** model syntax adoption and strong helper/composite comparator failed historically; unknown tool semantics not inferable from registry; semantic adapters lost coverage. **Revision:** stop privileging model-authored plans; examine post-model safe execution only.
2. **Try all-at-once native batching/parallelism.** Source reveals a real serial subprocess loop. **Challenge:** standard width-4 pool, static batching and persistent `rclpy` match much of it; native operations unchanged; potential contention and non-atomicity. **Revision:** specify adaptive read-width *only under* measurable load variation, with the generic adaptive limiter and full result obligations as hostile controls. No current evidence that such variation matters.
3. **Try optimizing transport setup across calls.** This is different from scheduling and has a formal online decision threshold. **Challenge:** setup amortization over a shared ROSA lifetime makes always-persistent overwhelmingly competitive; tool error/status parity unknown. **Revision:** demote to conditional technical alternative, don't implement a new transport chooser without lifespan/latency evidence.
4. **Revisit seemingly concrete correctness issues.** Ten FQN failures are real while staleness has no positive indexed case. **Challenge:** a normal FQN helper is a complete simple remedy, and fewer errors are not proof of algorithmic model-call efficiency. **Revision:** use shared FQN validation and provenance as baseline infrastructure; don't sell them as the contribution.

These are analyses and a runnable mathematical counterexample, **not iterations of local ROSA benchmarking**.

## 8. Exact actionable Codex protocol and stop branches

### Stage 0 — Reconcile provenance, **read-only**, no model invocation

In `/home/levinsonchen/project/rosa-research`:

1. Inspect `git status`, HEAD, pinned installed ROSA/`rosa-llm` source, `AGENTS.md`, and source paths `src/rosa/prompts.py`, `src/rosa/tools/ros2.py`, `src/rosa/rosa.py`, `src/rosa/tools/__init__.py`. Report source SHAs and whether the three list wrappers still loop over one subprocess each; no git reset/push, no version assumption (working `rosa-llm` reported 0.1.0). Read existing research notes first. No editing at this stage.
2. Locate surviving original **baseline diagnostic** and **CodeAct** durable evidence packages. Verify manifests, distinguish events from summaries; don't pretend recovered data for 64 lost dependency episodes. Extract **only**, without modifying prior experiment labels, from raw existing calls: count `N_total_episodes`, `N_list_wrapper_calls`, `N_calls_with_list_length≥2`, size histogram, per-item native start/end and time if logged, share of read-critical path per episode, error/missing distributions. Attribute inability to reconstruct per-item timing to logger availability; don't invent it.
3. Write `research/native_exec_preflight/READ_ONLY_INVENTORY.md` with exact numerator/denominator and 3 redacted representative event excerpts; `evidence_manifest.json` with source and hash. Do not collect a new 22-cell benchmark or regenerate old tasks. This resolves a new **post-bound list-wrapper incidence** question not isolated in previous model-call/graph studies.

**Stage 0 decision:** If no genuine `n≥2` events occur, or per-item native runtime is tiny relative to end-to-end episode cost, **halt NRWA as a main algorithm; no integration**, and state remaining questions honestly. If there are material eligible lists but timestamps are absent, authorize only a bounded **native-only timing microbenchmark** before asking the model again, with calibration/setup included. Do not mistake a nonzero fraction for useful speedup.

### Stage 1 — Controlled semantic- and safety-parity harness (only if Stage 0 positive)

Prepare read-only wrappers with exact model-visible schema and exact native operation count; validate `(tool,name)` inputs in all arms; no `shell=True`; same graph namespace/permissions/timeouts. Test (a) ordinary serial subprocess, (b) static 2, (c) static 4, (d) candidate width admission with specified passive telemetry, (e) a standard generic adaptive limiter with same telemetry and warmup budget, and (f) a warm persistent `rclpy` observer when semantically equivalent. In a disposable, stable ROS 2 fixture, compare exact per-entity answer mapping/status and all missing/error cases. Follow with controlled graph churn, shutdown, node name changes, partial failure and timeout to characterize non-snapshot semantics. Use same request and relevant ROS state snapshots; do not issue action/write commands.

Charge process creation, queueing, waiting, serialization, policy lookup, startup, calibration, warmups and all actual native requests. Freeze preconditions and budgets **before** comparing. Include at least two fixed load regimes with reversals and one mixed held-out regime; no use of future load labels at decision time. The **toy model** in the companion script is only a specification witness, not suitable as evaluation evidence.

**Stage 1 decision:** If best fixed/static/persistent or generic adaptive limiter ties or beats on correctness-adjusted total latency, stop proposing novel scheduler. Retain basic safe parallel reads if useful as an ordinary integration result. Do not tune post hoc on held-out workload.

### Stage 2 — Small unforced real-ROSA paired test (only after parity and measurable incremental contrast)

Compare original ROSA for descriptive context, **deconflicted** strong ROSA with actually used batching and equivalent tool permissions, ordinary best fixed/adaptive native execution, and NRWA. Use *the same* local model, tokenizer, seeds where available, temperature, ROS 2 fixture, language, task set, timeout, native operation limits and evaluator. Do not call paid models without explicit permission. Confirm from raw trace that the agent actually called admitted list wrappers; never insert synthetic lists that magically solve the language task while claiming full-agent generalization. Keep development/held-out tasks distinct, report failures/uncertain separately, and add at least one **new, non-handmapped ROS tool family** held out if claiming portability. Otherwise state narrow ROSA-core-API transfer only.

Independent full-answer scorer must check **every requested field and its correct source (observed versus configured, namespace, timestamp, requested lifecycle state, list cardinality, etc.)**, and distinguish missing, unknown, succeeded and stale. Record per-task: correctness+coverage first; then LLM calls/input/output tokens, unique native operations/attempts/errors, wrapper calls, end-to-end latency, CPU/process cost, setup/policy/calibration and distributions/paired confidence intervals. An interrupted run is uncertain, not automatically failure.

**Go/stop rule:** no claim of algorithmic contribution unless it differs in actions **and** quality-preserving measured cost from the best ordinary adaptive controller, with full-coverage held-out evidence. The size of a meaningful effect should be preregistered from Stage 0's upper bound and measurement noise; don't invent a percentage threshold now. If negative, report a narrow measured systems tradeoff and the previous historical failures honestly. Do not start another novel name/paper search to hide a negative result.

### Stage 3 — Before 2 December presentation

Deliver reproducible commit/source diff on a research branch, frozen experiment protocol, readable raw event JSONL, exact scorer code/judgments, quality-before-speed results table, failed/partial traces, SHA-256 manifest, reproducibility README and backup. Keep bulky artifacts in `research/_artifacts/` plus a second durable backup, not `/tmp`; never overwrite prior archive or `AGENTS.md`. Update canonical context *append-only* with fact/reported/interpretation/proposal labels. Present an **algorithmic result only if the strongest comparator gap remains**; otherwise present source-grounded engineering, constrained negative research, and openly unresolved generalization.

## 9. Precise research decision and highest-information next question

**Not selected as final algorithm.** NRWA is a bounded **conditionally retained technical hypothesis**, not a result, and rent-or-buy a secondary theoretical candidate with a strong counterexample. The source establishes a serial read loop; the evidence does not establish workload frequency, runtime bottleneck, or novelty relative to best adaptive control. The next allowable action is narrow: **recover count and per-item latency of already-observed list-valued reads from surviving archived baseline traces**. This is not a generic baseline rerun and requires no LLM. Positive evidence triggers only a matched native-only speed/parity comparison; negative or missing critical evidence blocks major implementation. The exact status is deliberately more cautious than the existence of runnable math code might suggest.

## 10. Primary source bibliography and exact audit pointers

**Original research papers and software mechanisms (primary):**

1. NASA/JPL ROSA / robot-agent paper (Royce et al., 2024), https://arxiv.org/abs/2410.06472 ; inspected implementation `src/rosa/tools/ros2.py`, `src/rosa/prompts.py`, `src/rosa/rosa.py`, `src/rosa/tools/__init__.py` in user's accessible GitHub default branch. Version identity with local pinned checkout not guaranteed.
2. Kim et al., *An LLM Compiler for Parallel Function Calling*, ICML 2024, https://proceedings.mlr.press/v235/kim24y.html .
3. Wang et al., *Executable Code Actions Elicit Better LLM Agents*, ICML 2024 (CodeAct), https://proceedings.mlr.press/v235/wang24h.html .
4. Xu et al., *ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models*, 2023, https://arxiv.org/abs/2305.18323 .
5. *LLM Tool Compiler*, runtime tool-fusion work, https://arxiv.org/abs/2405.17438 .
6. Selinger et al., *Access Path Selection in a Relational Database Management System*, SIGMOD 1979, https://doi.org/10.1145/582095.582099 .
7. Avnur and Hellerstein, *Eddies: Continuously Adaptive Query Processing*, SIGMOD 2000, https://dsf.berkeley.edu/cs286/papers/eddies-sigmod2000.pdf .
8. Jacobson, *Congestion Avoidance and Control*, SIGCOMM 1988, https://dl.acm.org/doi/10.1145/52324.52356 . Netflix concurrency-limits source, https://github.com/Netflix/concurrency-limits (existing adaptive-concurrency baseline, not a new paper).
9. Lotker, Patt-Shamir, Rawitz, *Rent, Lease or Buy: Randomized Algorithms for Multislope Ski Rental*, Information Processing Letters 2008, https://doi.org/10.1016/j.ipl.2008.07.009 . Standard single-slope threshold arguments are older and classical.
10. ROS 2 `rcl_interfaces/srv/GetParameters` and ROS 2 CLI daemon documentation, https://docs.ros.org/en/rolling/p/rcl_interfaces/srv/GetParameters.html ; https://docs.ros.org/en/rolling/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Nodes/Understanding-ROS2-Nodes.html . Local ROS distribution must be checked before using Rolling behavior as historical evidence.

**Supplied review artifacts:** `00_CORE/ROSA_RESEARCH_CONTEXT_UPDATED_2026-11-10.md` §§0,12,14; `01_PRIMARY_ADJUDICATION/ROSA_Bottleneck_Evidence_Gate_2026-11-10.md`; `clean-baseline-audit-2026-11-08.md`; `ROSA_Mission_A..D`; `ROSA_Focused_Algorithm_Discovery_2026-11-10(1).md`; `ROSA_Mixed_Graph_Read_Admission_2026-11-10.md`; `02_FAILURE_AUDITS_AND_SPECS/CPAW_Independent_Review_and_Research_Lessons_2026-11-10.md`, `REPORT.md` and `03_REPRODUCIBLE_EVIDENCE/CPAW_REVIEW_PACKAGE.zip`. Precise included-file hashes are in the supplied `README_EVIDENCE_INDEX.md` and `MANIFEST.json`.

**Independent verification here:** exact downloaded remote source inspection, bundled documents/negative reports, syntactic source comparison, ZIP integrity check, 4 pure-Python offline tests. **Not performed:** ROSA local tool execution, new ROS 2 experiments, any paid LLM requests, causal replay of the unavailable original raw histories, or empirical scoring of natural-language answers.
