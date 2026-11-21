# ROSA bottleneck evidence gate — 10 November 2026

## Decision and evidence level

**NO-GO for a new algorithm today. Reject dynamic-graph call admission as the selected research direction on present evidence. Recommend one bounded diagnostic of source/obligation failures before selecting a method.** This does not establish that temporal failures never occur. Their prevalence, observable warning signal, and net advantage over ordinary retry/invalidation have not been established here.

Evidence level: **original saved-event audit plus installed-source verification**, with explicit missing corpora and historical validity limits. This is stronger than a report-only feasibility review, weaker than a fresh causal comparison. No new ROS operation, graph observer, model experiment, benchmark, algorithm, runtime modification, or commit was executed. Source inspection is not runtime validation.

The strongest demonstrated bottleneck is **loss of requested source/answer obligations**, both before acquisition and after evidence arrives. In the 36-episode baseline diagnostic, preserved strict judgments identify three wrong-source answers and five interpretation/omission failures. Ten native failures in five episodes instead concern namespace/identity construction, not demonstrated stale incarnations. Older graph experiments independently expose missing acquisitions and incorrect final rendering despite eventual acquisition. None supplies a demonstrated method advantage over the strongest ordinary control.

The mission document supplies the tasks and read-only boundary because the user's current request explicitly authorizes executing that mission. Recommendations in the independent audit, old packets, and Missions A–D remain evidence/hypotheses. Their historical implementation or execution instructions do not authorize work in this mission. Original attachments remain unchanged; their paths/hashes are in [inputs.json](inputs.json).

## 1. Provenance and scope

Current checkout: `/home/levinsonchen/project/rosa-research`; branch `research/clean-foundation-20261108`; HEAD `94af17866cb82f3ea3f09422ef5cbb99b14cc89c`. Initial Git status was `?? research/`, so this was a clean source foundation with pre-existing untracked research, not an entirely clean working tree. The old clean-baseline audit was read at `/home/levinsonchen/project/rosa-research-previous-20261108/research/architecture/clean-baseline-audit-2026-11-08.md`; its branch/location descriptions are historical. Current facts above were checked directly.

Current ROSA declares `jpl-rosa==1.0.10`; editable-install metadata points to this checkout. `src/rosa/rosa.py` accepts a LangChain `BaseChatModel`, creates `create_tool_calling_agent` and `AgentExecutor`, and returns final text through `invoke()` (lines 134–168, 256–276). `astream()` exposes async events. Installed `rosa_llm/langchain.py::ChatRosaLLM.bind_tools` (line 154) transports schemas/calls; it does not execute ROS tools. Installed metadata: rosa-llm 0.1.0, LangChain 0.3.30, langchain-core 0.3.86. **The inspected historical baseline/pilot workers use ChatOllama and recorded `qwen3.5:9b`, not evidence of live ChatRosaLLM performance.**

Current source SHA-256:

| File | SHA-256 |
|---|---|
| `src/rosa/rosa.py` | `21c35b1bdb14f6c8f6fd2f449943de7f1ba177fdce51ba0a6344b5ec9991e66b` |
| `src/rosa/tools/ros2.py` | `7f3769bc9711274fae844993f9bee7c5024e41ec2c28790db86f422fd8146e22` |
| `src/rosa/prompts.py` | `a2e43cc849bc8438ca05ba3b2d0ed5b9630219f2959b84d26921f8e4abee2e17` |

### Original trace inventory

Use these root abbreviations only within this report:

- **P** = `/home/levinsonchen/project/rosa-research-previous-20261108/research/_artifacts/`
- **G** = `/home/levinsonchen/project/rosa-research-archive/research/raw/`

| Artifact | Original events audited | Integrity and missing evidence |
|---|---|---|
| P`rosa-baseline-diagnostic-review-20261107.zip` | All 36 `evidence/primary-v1/*/trace.jsonl`; eight separate model-only replay traces; seven oracle trace files indexed separately | 333 members; full CRC passed; 332 manifest member hashes matched. Original task protocol, independent snapshots, automatic audit, strict judgments and closeout amendment preserved. |
| P`rosa-paper-pilot-review-20261108.zip` | All 15 interrupted evaluation traces, nine continuation traces, six development traces | **467 actual ZIP entries**, 466 hashed members matched; full CRC passed. Do not substitute older report member counts. Evaluation has 78 model starts but only 77 completions; missing closing oracle. Continuation is separately bracketed and unbalanced across arms. |
| P`rosa-multistep-review-20261107-reconstructed.zip` | **Zero original episode traces** | 35 entries, CRC passed, 34 included-file hashes matched. Reconstruction manifest explicitly lists **64 missing primary trace paths and expected hashes**; saved source/results cannot recreate events. |
| G`rosa-round28-external-review.zip` | All 64 Round27 held-out episode JSONs and all 84 Round28 held-out episode JSONs inside this archive; 552 dispatches | 22,343 entries; archive hash calculated; selected original members/scorers hashed and read successfully. Full archive CRC/manifest reconciliation was **not** repeated for this large archive. |
| Strong tool-menu retrieval | Source/protocol/auditor found at previous checkout `research/menu_retrieval/`; **no original menu episode corpus found** | Search covered previous/archive checkouts and project ZIP central directories below 150 MB. This bounded search does not exclude a copy elsewhere. Reported 10/12 vs 7/12 is not a newly verified raw result. |

Archive SHA-256:

```text
baseline diagnostic 85b601b988288ad95cb46451909435c81407d29ae049a24e00e6146813b2b8d4
CodeAct pilot      c64a7c67c3d6973a7c1ef5339eb033ea98d69b20ebc7f5f11f2ad64933826fea
multistep rebuilt  fd1c28f0c507c9de271c67e1fb0fe6d03eeb89ca261abcb5986065ba50cbb0e4
Round28 archive    90825be5f296c5e32d98dec2a2862f65557d3bd5bf448e819804cf8aeded520c
```

Exact original member paths, lengths and hashes are in [inventory.json](inventory.json) and [older_manifest.json](older_manifest.json). [missing_multistep.json](missing_multistep.json) preserves the exact missing ranges. No malformed JSON lines occurred in the indexed trace corpora or selected older episode/scorer JSONs. Integrity matching proves preservation relative to the bundled manifest, not correctness of the experiment or authenticity against an external signed reference.

### Truth/scorer availability and limitations

Baseline ZIP has `review/protocol.json`, `review/audit.py`, `review/independent-judgments.json`, `evidence/primary-v1/automatic-audit.json`, and independent oracle snapshots. The auditor builds truth from direct parameter dumps, node/topic/service observations; truth is separate from model messages. Saved literal strict judgments are joined to every primary episode. Those 36 judgments initially say 28 true/8 false; the explicit closeout amendment makes `33-x1-C-r1` inventory completeness **indeterminate**, yielding conservative A 9/12, B 10/12, C 8/12 plus one indeterminate. No pure-JSON framing successes in that baseline block. Factual coverage and output framing are separate.

The after-36 node enumeration omitted demo nodes although direct reads still worked. That is **observed incomplete discovery**, not proof of physical node disappearance. No clean closing snapshot was reconstructed.

CodeAct ZIP has `research/paper_pilot/protocol.json`, `research/paper_pilot/audit.py`, separate original-before-only and continuation-audit records under `research/_artifacts/paper-pilot-analysis-20261108/`. Those saved scores are joined in `episodes.json`. Before-only field matches are not bracketed supported completion. Development is not held-out evidence. The nine continuation scores and the one completed program do not provide a matched strong B/C efficiency comparison.

Older task/scorer members and adjudication distinctions are enumerated in [older_evidence.md](older_evidence.md). Saved scores were parsed, their source inspected, and decisive original-event witnesses checked; historical auditors were **not executed** and every answer was not newly independently adjudicated. Round28 automatic and post-closure representation adjudication remain distinct. `strict_supported_answer` alone does not mean every requested fact was answered.

## 2. Call ledger and denominators

[analyze_traces.py](analyze_traces.py) and [audit_older.py](audit_older.py) are new offline analysis scripts. They import no ROSA runtime or experiment driver. They persist exact arguments, task/answer records, recorded tokens, original member/line references and observation times where available.

- [calls.jsonl](calls.jsonl): every recorded model proposal in the baseline/pilot/replay corpora; recorded input schema type/required-field checks, matching tool completion, delivered output, output bytes, earlier textual identity support and its time. Type checks are not full semantic validation.
- [native_calls.jsonl](native_calls.jsonl): exact commands, return codes, stdout/stderr, timing and earlier identical command. This separates process failure from successful output.
- [episodes.json](episodes.json): request, answer, starts/completions, usage, saved judgment/score and missing boundaries. [programs.json](programs.json) retains program arguments/results and nested native counts.
- [older_calls.jsonl](older_calls.jsonl), [older_episodes.jsonl](older_episodes.jsonl): all 552 older dispatches and 148 episode records, including original graph observations and saved score provenance.
- [older_models.jsonl](older_models.jsonl) and [older_model_proposals.jsonl](older_model_proposals.jsonl): all426 recorded completions (Round27 181, Round28 245) and409 proposals (184,225), including32/56 compilation proposals. These are distinct from552 dispatches: ordinary controllers can dispatch without one model proposal per read. Later identical-dispatch matches are candidates, not proof of causal identity.

**Grounding caution:** textual appearance in an earlier delivered tool response is a screening indicator, not proof the model used it or that the entity is still current. The baseline has 165/185 explicit entity arguments with an earlier exact textual match; CodeAct evaluation has 37/37, continuation 17/19. These counts exclude identities internal to programs/batches; the native/program ledgers retain their evidence. No continuous event/incarnation log exists. Freshness remains unknown, even when earlier discovery succeeded.

| Corpus/block | Episodes | Model starts/completions | Model proposals | Native completions/errors | Native failures | Exact repeated commands / same stdout |
|---|---:|---:|---:|---:|---:|---:|
| Baseline primary |36|227/227|203|264|10|14 / 14|
| Baseline replay, historical contexts |8|12/12|6|0|0|0 / 0|
| CodeAct evaluation, interrupted |15|78/77|67|75|1|14 / 13|
| CodeAct continuation |9|38/38|33|40|2|9 / 9|
| CodeAct development |6|21/21|17|22|0|1 / 1|

All primary baseline and CodeAct evaluation proposals match a delivered tool completion in the saved events. These proposal counts differ from internal wrapper dispatch counts; one program proposal can execute several native reads. Oracle records are not model episodes. Baseline recorded input/output tokens total **1,585,055 / 27,132**; evaluation **534,601 / 6,993**; continuation **246,355 / 2,920**. Missing model completion usage cannot be inferred. No latency saving is derived from these token totals or native durations.

Baseline exact repeated commands are A 4/76, B 7/97, C 3/91, across 13/36 episodes. This differs from older reports' broader “candidate redundant read” counts, which also cover overlap across different sources and other opportunity definitions. Neither definition proves same-time equivalence. The ledger explicitly declines to label repeats as proven redundant.

### Distinct causes, multi-label where appropriate

| Cause | Observed support | Attribution and unknowns |
|---|---|---|
| Repeated identical read |14/264 baseline native executions; 14/75 interrupted pilot; 9/40 continuation | Equal commands/output at different times. Valid same-time redundancy **unknown**. No causal model-turn savings established. |
| Avoidable intermediate decision | Baseline `00-x1-B-r0` reads node info after discovery before scalar clock parameters; pilot continuation d1 C uses 2 model completions vs A 4 | Counterfactual helper/batching opportunity, not an activated advantage over the strongest control. Generic batch tool unused in baseline C; old sequential system prompt persists in model contexts. |
| Invalid tool/argument |0/203 baseline proposals fail the limited recorded schema checks, yet 10/264 native reads fail; development has one detected schema error | Syntactic legality does not imply target validity. Five baseline episodes use `/diag_turtle` as a node or `source`/`listener` without namespace. |
| Stale graph identity | No failure positively attributed to it in these indexed blocks | Not a measured zero prevalence. No incarnation/event journal or controlled natural churn labels. Do not reclassify malformed names or deliberately absent sources as staleness. |
| Unsupported semantic source |3/36 baseline strict wrong-source answers; older absent localization/battery requests | Background RGB was answered from color sensor observations instead of configuration. No temporal policy resolves that semantic distinction. |
| Malformed/incomplete native response |0 successful-empty CLI stdout among the 264+75+40 native records above; static Python parameter callback exposes an empty-response case | Zero empty stdout is not proof all bodies are semantically valid. Complete decoding/coverage certification unavailable for every raw text response. No measured prevalence for empty parameter batches. |
| Oversized observation | Maximum matched serialized tool output: baseline 4,390 bytes; pilot evaluation 3,139; continuation 2,884 | No frozen size-limit breach established. Actual model inputs also include schemas/history. These byte counts do not prove payload caused omissions or justify adaptive packing. |
| Interpretation/omission |5/36 baseline strict judgments; explicit older source/acquisition/rendering witnesses below | Keep missing acquisition separate from evidence acquired but omitted or misattributed. Strong ordinary controls already solve the small feasible older slice. |
| Program repair/interface mismatch |Evaluation+continuation:9 program attempts;5 rejected before native reads,3 partial failures,1 complete | Observed adoption/DSL mismatch, not a temporal graph failure or proof interpreter execution is inherently ineffective. |

Baseline failures occur in B (6/97 native reads) and C (4/91); A has 0/76. The five affected episodes recover to supported answers under the archived judgments. Seven failed proposal turns contain those ten failed reads. **Ten native failures and seven exposed turns are opportunity ceilings for perfect removal of these particular erroneous proposals, not achieved savings.** A guard returning a refusal still causes a model turn; unique argument repair is already an ordinary/SCA-style control. Similarly 14 repeated baseline commands bound only exact-repeat removals under an additional safe-reuse assumption; other overlap is outside this bound. Do not add ceilings across overlapping interventions.

### Original-event witnesses

Baseline member paths below begin `evidence/primary-v1/` in the baseline archive. Line numbers are JSONL lines; hashes are in the inventory.

1. `06-t1-A-r0/trace.jsonl`: model proposals at lines 4,10,16,24 acquire node/topic information then `ros2_topic_echo` of the color sensor; no background parameter read. Final answer gives `[255,255,255]`; independent configured truth is `[37,83,129]`. This is **wrong source plus missing required acquisition**, not a tool transport failure. The analogous C episodes are `14-t1-C-r0` and `28-t1-C-r1`.
2. `07-d2-B-r0/trace.jsonl`: node-info acquisition at line10 exposes GetTypeDescription; final answer omits it and claims only one non-parameter-management service. Lines32 and38 repeat the same `use_sim_time` request. This episode has **omission/misclassification plus repeated read**; eliminating the repeated read would leave the wrong answer. Five d2 judgments in total flag this family under literal task semantics. A narrower “application service only” reading must be reported separately, not silently replace the frozen question.
3. `11-t2-B-r0/trace.jsonl`: line10 proposes `ros2_node_info(nodes=['/diag_turtle'])`; line30 repeats that invalid identity in parameter listing; line36 finally uses `/diag_turtle/palette`. Earlier node list already supplied the full name. `30-t2-B-r1` repeats the pattern. **Namespace mistaken for node identity**, not an observed disappearance.
4. `13-d1-C-r0/trace.jsonl`: line10 proposes `nodes=['source','listener']` after topic info; failures at lines13,15 are followed by discovery and qualified names at line24. `19-d1-C-r1` and `34-d1-B-r1` share the pattern. Endpoint name/namespace assembly or conservative unique repair is the exact ordinary competing remedy.
5. Older Round27 `0-r27h05_grid_shape_and_lifecycle-graph_dynamic.json`: requested child lifecycle label is never acquired although the graph advertises GetState. Older Round28 selective h04 compiles the child-state obligation correctly but never dispatches GetState. These are different layers of **missing acquisition**.
6. Older Round28 `0-r28h09_total_and_comparison-selective.json`: requested and compiled `sum_rgb` is eventually acquired, but final answer renders earlier `sum_rg:155`. This is **rendering/source-scope failure after acquisition**, not compiler failure or unavailable data.

Older denominators: Round27 9/260 native-wrapper failures = eight deliberately absent AMCL pose reads plus one GetParameters `{}` request without names. Round28 10/292 = seven deliberately absent pose reads plus three unapproved `battery_charge` guesses. Prior graph endpoint membership is 184/192 and 188/208 endpoint-bearing calls; exact repeated dispatch arguments 11/260 and 9/292. Neither wrapper `allowed=true` nor backend `ok=false` alone certifies a DDS request or physical postcondition.

Older saved adjudicated full feasible completion is Round28 original 8/8, strong prompt compiler 8/8, old graph 7/8, selective 6/8, no-gate 8/8, no-coverage 8/8, async 3/8. These adapted experiments cannot establish transfer to ordinary ROSA without their application field projections. They strongly challenge another answer-field compiler or selective gate as the solution.

## 3. Installed ROS semantics: dynamic-graph hypothesis

Exact installed paths, versions, line references, source hashes and primary-source links are in [api_literature.md](api_literature.md). Installed rclpy is 7.1.12; rclcpp 28.1.22. The decisive facts are:

| Source/API fact | Implication |
|---|---|
| rclpy `Node.get_node_names_and_namespaces()` returns names/namespace pairs; publisher endpoint info exposes endpoint GIDs | FQN assembly fixes the observed bare-name mistake. Neither a name nor an endpoint GID is a universal node-incarnation/parameter-version token. |
| Installed rclcpp offers graph events/waits; installed public rclpy Node does not expose those methods | Do not design a Python guard assuming the C++ methods exist on Python Node. A bridge/listener is additional engineering/setup. |
| RMW graph queries report discovery **as seen by the associated node**; C++ Event stores a Boolean | Cached discovery is not a globally current snapshot; events may coalesce and do not supply an ordered entity journal. No measured delivery-lag distribution was collected. |
| Parameter updates publish separate events; default QoS is RELIABLE, VOLATILE, KEEP_LAST depth1000 | Topology can remain unchanged while values change; late joiners do not automatically recover history. Silence supplies no completeness/freshness certificate. |
| Parameter events carry FQN, time and parameter changes, without incarnation or sequence certificate | Namespace filtering and observer scope matter. Receipt time and source timestamp do not close every race or identify restart continuity. |
| Installed scalar `ros2 param get` already waits for the node and parameter services through NodeStrategy | Another membership preflight duplicates some existing work and still races with the read. A persistent in-process observer changes architecture/setup costs; give it to controls equally. |
| Installed rclpy parameter service clears all returned values on an undeclared/uninitialized requested name, while interface expects correlated values | Empty transport-success on a nonempty request means insufficient coverage. This provider behavior is not malformed wire transport, and its prevalence here is unknown. Ordinary typed length checks and bounded recovery are required controls. |

Source audit finds no cheaper public check that certifies all of name presence, incarnation continuity and value stability. It does not prove such a specialized signal can never exist. A preflight can reject *known contradictory* proposals; it cannot certify arbitrary proposals from event silence. Reads also have a check/use race. Correctness needs explicit observation-time semantics and honest missing/ambiguous results.

| Ordinary control | Cost/information | Residual limitation |
|---|---|---|
| No preflight + one bounded retry | Read, then recovery only on failure | Pays first invalid read; often competitive at low failure frequency |
| Always refresh | Additional graph query before each guarded read | Still no atomicity/value/incarnation certificate |
| Name membership | Use already-paid graph metadata or another query | Observer scope/lag; presence does not ensure requested service/parameter |
| TTL | Timestamp plus fixed lifetime | Heuristic freshness |
| Ordinary graph-event invalidation | Listener setup and callback/refresh work | No silence guarantee; no parameter-value stability |
| Parameter-event invalidation | Subscription/filter/processing plus refresh | Late-join and completeness limits; distinct from graph events |

All must get the same observations, native API access, batching, timeouts, retry rights and result envelope. Charge cold listener/setup, extra native checks, false refusals, model turns/tokens and recovery. A screening inequality is `stale_frequency × avoidable_failure_cost > guard_cost + false_refusal_cost`; none of these terms has been measured here for the proposed guard. Native-read seconds cannot substitute for model-turn savings.

## 4. Primary research and incremental-delta challenge

The supplied research identifiers resolve to matching primary records; method text was checked, with scope stated below. None is evidence that its result transfers to ROSA.

| Primary work | Relevant mechanism | Remaining claim burden |
|---|---|---|
| [SCA, Lee & Barke, arXiv2610.25552v1](https://arxiv.org/html/2610.25552v1), method and limitations | Documentation/execution-history constraints; first-order checking; conservative unique MaxSMT argument repair | History-qualified checking and repair are prior art. Hidden-state/missed-call limitations identify an observability problem, not an automatic novelty opening. A ROS signal must add useful information and beat ordinary invalidation. |
| [Gecko, ICML2026 primary record](https://proceedings.mlr.press/v306/zhang26cv.html), [full author v2](https://arxiv.org/html/2602.19218v2) | Schema/semantic validation and simulated stateful feedback/refinement | Generic preflight/repair is established. Simulation is not independent live-graph evidence; helper-model costs differ. |
| [Structured Uncertainty guided Clarification, ACL2026](https://aclanthology.org/2026.findings-acl.2028.pdf), method | Structured tool/parameter beliefs and EVPI/cost-based questions | Generic risk/cost balancing is insufficient novelty; clarifying intent differs from sensing hidden environment state. |
| [When2Tool, arXiv2605.09252v3](https://arxiv.org/html/2605.09252v3), method | Hidden-state probe and prefill intervention for call necessity | Requires model access/training unlike a framework guard. Model prior knowledge cannot replace requested live evidence. |
| [Proof-of-Use, EMNLP2026](https://aclanthology.org/2026.emnlp-main.1664.pdf), method | Evidence IDs, usefulness/citation alignment, RL rewards | Lineage labels and answer grounding alone do not establish a new method; temporal validity is a different unproved increment. |
| [Agent-C, arXiv2512.23738](https://arxiv.org/abs/2512.23738), abstract/record only | Temporal action-order constraints enforced during generation | “Temporal” naming does not distinguish a contribution; action ordering is distinct from physical freshness. No full implementation comparison claimed. |

The ordinary fixed-composite objection also survives direct source/event scrutiny: known node lists can be passed to existing list tools, independent selections can share one model response, and a fixed discovery/read helper can remove the same intermediate boundary as a general composer. Installed LangChain async dispatch already uses `asyncio.gather` (`agents/agent.py:1543` onward). Current ROSA's system prompt explicitly prohibits batching (`prompts.py:81–90`), including in historical strong-prompt traces. Correcting that contradiction is a **baseline repair**, not a research contribution.

Current CLI runner also uses `shell=True`, returns exception strings, and can put failure text under normal entity-list keys (`tools/ros2.py:25–88`). These are relevant contract/validation limitations; no exploit or unsafe execution was attempted. A shared typed, bounded backend would be infrastructure, and cannot be reserved for the candidate to manufacture an efficiency win.

## 5. Adversarial ranking and gate

Ranking combines original-event opportunity, separation from strong ordinary controls, feasibility by 2 December, and independently measurable transfer. It is a priority ranking for diagnosis, **not** a candidate promotion list.

| Rank / target | Demonstrated opportunity | Mechanism delta / transfer / deadline judgment |
|---|---|---|
|1. Requested-source and answer-obligation retention |3 wrong-source +5 interpretation/omission baseline answers; distinct older acquisition/rendering witnesses | Most useful next measurement. Framework-only safe remedy not established; do not introduce a manual field map. Diagnose across both stock situations before engineering. |
|2. Qualified identity construction / recovery |10 failed native reads in5/36 baseline episodes; two continuation target mistakes | Concrete and inexpensive systems fix; exact competitor is FQN assembly from public name/namespace plus conservative ordinary validation/retry. SCA already pressures novelty. |
|3. Intermediate decisions and repeat reads |Recorded repeats; one successful dependent program | Ordinary batching/reuse/fixed helper can explain opportunity; unsupported tasks cannot earn efficiency credit. No new policy survives strong-control comparison. |
|4. DSL/interface adoption |8 failed/partial program attempts out of9 evaluation+continuation invocations | Strong evidence against using that interface as-is, not justification for another automatic composer. Narrower ordinary tools remain the comparator. |
|5. Temporal admission |Changing graphs are possible; preserved failures do not demonstrate this cause | Required signal and prevalence missing, setup/preflight may dominate. Reject promotion; retain only a small stress falsification check. |
|6. Adaptive packing / opaque batch recovery |No measured size-caused failure or poisoned-batch prevalence here | Fixed output envelope, typed correlation and ordinary bounded recovery are strong controls. Source possibility alone is insufficient. |

**No algorithmic decision rule is specified**, because no bottleneck passes all gates. This is the mission's explicit no-go branch. The exact strongest comparator for the top target is corrected ordinary ROSA: remove conflicting sequential advice, preserve source identity and all requested obligations in ordinary guidance, use existing list batching/available concurrency and bounded retry, and score all answers independently. For older adapted claims it is the saved prompt-compiler/no-gate control with equivalent typed tools and projections, not original defaults. A new field compiler that reproduces those mappings would violate the project boundary.

## 6. Single next measurement: frozen source-to-answer diagnostic

**Design only; requires separate authorization and has not been implemented or run.** Measure where a requested fact first becomes lost on the corrected strong ordinary ROSA baseline. Primary output is a request → actual delivered evidence → final-answer ledger, not another optimization score.

Use two stock situations: namespaced Turtlesim and `demo_nodes_cpp` talker/listener/add-two-ints. Six frozen read-only questions per situation, one fixed seed/model/provider configuration, one repetition: **12 unperturbed stable episodes**. These are constructed diagnostic requests, not sampled production traffic. Freeze model/provider settings and independent source obligations before execution. The evaluator may use source maps to score; the runtime policy/model must never receive those answer keys/maps. A question whose truth cannot be independently established stops that cell as invalid.

Proposed frozen question texts (each asks for a JSON object, with unavailable fields explicitly marked):

| Cell | Literal request before the common JSON instruction |
|---|---|
| T1 | In /gate_turtle, discover the running simulator node and report its configured background_r, background_g and background_b values. |
| T2 | In /gate_turtle, discover the color sensor topic and report one observed RGB message, identifying the topic and message type. |
| T3 | Discover every running node in /gate_turtle and report use_sim_time for each fully qualified node name. |
| T4 | Discover the pose topic in /gate_turtle and report its full name, type, publisher count and subscriber count. |
| T5 | Discover the simulator node in /gate_turtle and list all its advertised service servers with types, including standard services. |
| T6 | Report the configured background RGB, the pose topic's publisher count, and all node names in /gate_turtle; keep the sources distinct. |
| D1 | Discover every running node in /gate_demo and report use_sim_time for each fully qualified node name. |
| D2 | Discover the chatter topic in /gate_demo and report full name, type, publisher count and subscriber count. |
| D3 | For the chatter topic in /gate_demo, report every publisher and subscriber node with its namespace and endpoint role. |
| D4 | Discover the arithmetic server in /gate_demo and list all its advertised service servers with types, including standard services. |
| D5 | Discover every node in /gate_demo and list its parameter names without inferring values. |
| D6 | Report all node names in /gate_demo, the chatter topic's publisher count, and the arithmetic server's use_sim_time; identify each source. |

Common instruction: `Return one JSON object containing every requested fact and its source identity. Mark unavailable facts explicitly. Do not substitute a different quantity.` These fixtures use fixed namespaces but require discovering node identities; no question-to-endpoint map is supplied to the runtime. T1 and T2 intentionally separate configured background from sensed color. D4 deliberately includes standard services to remove the historical wording ambiguity. These texts are a prospective proposal, not retroactively frozen inputs to the old evidence.

Separately, add **five explicitly injected stress cells per situation**, fixed before execution: stable discovery→read, actual removal between discovery/read (include same-name restart in this cell's second observation), stale cached lookup, nonempty parameter request containing an undeclared name, and a normal non-target query. Ten stress cells test observation and failure classification; they do **not** estimate natural stale-call prevalence. Restart/parameter manipulation would be confined to disposable simulator fixtures and needs that later authorization. No robot motion is needed.

Instrumentation must preserve model starts and ends, exact schemas/proposals/args, actual delivered outputs, native transport/decoding/coverage, discovery observer/domain/FQN/time, endpoint GIDs where available, separate parameter events, orchestrator-controlled fixture truth times, answer text, and independent frozen scores. Distinguish (a) no adequate evidence acquired, (b) adequate evidence delivered but omitted/misattributed, (c) identity genuinely changed after grounding, and (d) unknown. Record partial refusals as partial answers, and separate JSON framing. Test event lag by recording times, not by assuming it away.

Do not launch a broad control matrix yet. First record no-preflight/one-retry baseline plus the observable warning signals in **shadow mode**: signals cannot alter calls. Offline, evaluate whether name membership, TTL, graph invalidation or parameter invalidation even distinguishes the labelled failures under the same observations. Charge acquisition/setup when it would require new work; retrospective knowledge of hidden fixture state is not a deployable guard. Only a subsequent frozen paired study can demonstrate saved turns or latency.

Predeclared stop conditions:

1. No interim tuning, replacement episodes, changed questions, or new algorithm. Maximum22 cells; at most one recovery attempt per failed read; common caps16 model requests,32 native attempts and180 seconds per episode, including recovery. Budget exhaustion is an incomplete attempt, not an exclusion. Abort on instrumentation mismatch or fixture truth loss and retain the invalid cell. Freeze exact model/provider settings and fixture seed before separately authorized execution.
2. If all natural errors are already explained by ordinary FQN handling, source guidance, output handling or retry, stop algorithm promotion. If no actual stale proposal occurs naturally, temporal admission remains unselected regardless of stress success.
3. If source/obligation loss occurs fewer than twice across the12 unperturbed cells, report insufficient recurrence. If confined to one application or one ambiguous question, do not claim transfer. This small sample is a screening gate, not a prevalence estimate or significance test.
4. Before any later prototype, require one explicit observable decision where a proposed rule differs from—and plausibly improves on—the best ordinary control without hidden truth or semantic maps. If no such witness exists, choose systems-only improvement. A perfect retrospective repair count is not this witness.
5. Any later paired efficiency claim must preserve full factual/source-supported completion and exact requested scope on every feasible paired cell, account for all attempts and cold overhead, and exceed a frozen minimum benefit (suggested screening target: at least one actual model request saved on two supported paired tasks, across both situations, with no increase in total native work). Freeze held-out inputs and criteria before implementation. A tie with the fixed/helper/event/retry control, any unsupported answer, or net cost increase rejects promotion.

The 22-cell plan is the smallest credible bounded screen proposed here: twelve natural questions separate source/acquisition/rendering across two situations; ten stress cells probe API observability separately. It is not a powered benchmark or a currently authorized experiment.

## 7. Completed actions and preservation

Completed: read both attached documents and relevant project/clean-baseline/design context; located originals; parsed all baseline/pilot traces and two older held-out blocks; inspected frozen scorer source and saved truth/judgments; checked archive integrity within the stated bounds; inspected installed ROSA/LangChain/model adapter and Jazzy APIs; checked primary method texts; challenged each proposed avenue against ordinary controls; produced this report, scripts and ledgers.

All new files are under `research/diagnostics/`. Existing source, tests, configuration, research and input archives were not edited. [preservation_before.json](preservation_before.json) inventories pre-existing checkout files; [preservation_after.json](preservation_after.json) records the final comparison and Git/HEAD check. Archive reads were read-only; no historical scorer/driver execution, environment sync, installation, ROS process, inference, commit, push, merge, reset, branch switch or cleanup occurred. Newly generated analysis files are untracked, not committed.

Reproduce the offline evidence indexes from the repository root:

```bash
python3 research/diagnostics/bottleneck_gate_20261110/analyze_traces.py
python3 research/diagnostics/bottleneck_gate_20261110/audit_older.py
```

`python3` runs the named analysis script. These commands read the absolute archive paths recorded above and overwrite only their diagnostic outputs. They do not rerun experiments. The scripts and archive member hashes make this audit inspectable; missing event histories and unexecuted causal comparisons remain missing.
