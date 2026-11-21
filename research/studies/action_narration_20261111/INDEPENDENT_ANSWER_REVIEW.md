# Independent answer-support review

2026-11-11. This is a manual, read-only adjudication of preserved model responses, model-visible tool messages, native read results and the independent `oracle-before.json` under `research/_artifacts/action_narration_20261111/primary-v1`. No model/ROS calls or scoring-program execution were performed for this review. The reviewer also authored the prior-art/design review, but did not implement or run the study. This is independent trace judgment, not a blinded external audit.

## Review scope and rule

Initial scope: the seven closed cells `00` through `06`, read while the block was still running. Remaining cells are unreviewed, not failures or successes. No aggregate result over twelve is implied. Review checks each requested field against actual successful, model-visible acquisition, then checks completeness, source/role identity, extra factual narrative, and the recovery-task instruction. Matching the independent snapshot alone cannot establish support.

The independent snapshot shows four application nodes: `/diag_turtle/palette`, `/diag_demo/{calculator,listener,source}`. Configured RGB is 37/83/129; all four `use_sim_time` values are false. Turtle pose is `turtlesim/msg/Pose` with one publisher. Demo chatter is `std_msgs/msg/String` with one publisher `/diag_demo/source` and one subscriber `/diag_demo/listener`. Turtle graph-interface publishers are color_sensor and pose; cmd_vel is a subscription. These are graph/configuration facts, not proof that application messages were received or physical motion succeeded. Snapshot timing/stability requires the final whole-block audit; this review does not silently assume an atomic graph snapshot.

| Closed cell | Independent supported-completion judgment | Evidence and limitations |
|---|---|---|
| `00-t1-B` | PASS | Node discovered via list then node info. Successful parameter gets explicitly acquire background_r=37, background_g=83, background_b=129 from palette; topic info acquires pose type and publisher count. All observations appear in the final invocation scratchpad. Final JSON contains all requested values, with no unsupported extra factual narrative. |
| `01-d1_recovery-A` | PASS | First native read actually attempts `/diag_demo/retired_source` and returns missing-node error once. Discovery and verbose chatter info establish endpoint identities/roles and counts. Successful gets for each full-name endpoint acquire use_sim_time=false. Final JSON and accompanying summary are supported, including absence under the current fixture. “Does not exist” is interpreted as current observed absence, not permanent nonexistence. |
| `02-t3-A` | PASS | Discovered palette node info directly distinguishes Publishers from Subscribers. Both application publishers and their types are included; cmd_vel appears only as subscribed. Final explanation correctly says parameter_events appears in both interface sections and is excluded. No claim of message delivery is made; the task asks for interfaces, so graph evidence is sufficient for that scope. |
| `03-t1-A` | PASS | Same field support pattern as 00: discovered node, actual three RGB parameter gets, actual pose topic info. Summary repeats supported facts only. |
| `04-x1-B` | FAIL | Final text only says both nodes have a use_sim_time parameter; no requested clocks/topics object or values is returned. Parameter lists for calculator/listener do not acquire clock values. Final backend metadata is `done_reason=length`, prompt_eval_count4079 + eval_count17 =4096. This is observed truncation, not evidence that terse policy alone caused a failure. |
| `05-x1-A` | FAIL | Four successful full-name clock gets and the two verbose topic observations reach the model, but final answer stops after introductory headings and omits all requested field values. Backend metadata is `done_reason=length`, prompt_eval_count4069 + eval_count27 =4096. Acquisition succeeded more fully than in04, yet final coverage failed. Shared provider/context behavior is a material confound; do not count low completion token/time as efficient success. |
| `06-d1_recovery-C` | FAIL despite oracle-matching JSON | Chatter type/counts/endpoints/roles are acquired and supported. Both final `use_sim_time:false` fields are unsupported: no parameter get occurs anywhere in this episode and node-info output contains no parameter values. The expressly requested stale-node check is also never attempted. The model instead attempts bare `source` and `listener` node info, gets two real identity errors, discovers full names, and successfully reads node info before guessing the clocks. Final ends normally (`done_reason=stop`, prompt3068 + output124), so this support failure is distinct from x1 truncation. |

## Disconfirming case: correct values without supporting acquisition

`06-d1_recovery-C` is the decisive caution against declaring a win from automatic truth matching. The final booleans happen to equal the fixture configuration, but neither CLI outputs nor model-visible observations supplies them. A parameter-service name advertised by node info establishes an available interface, not that parameter's value. Treat two clock leaves as unsupported; do not infer a semantic contract or a valid default from the coincidence. The omitted stale identity check separately violates the task's explicit procedure. Actual errors in this episode are wrong namespace/FQN attempts, not observed stale incarnation.

## Truncation and attribution limit

Both closed x1 controls A and B produce length-terminated partial finals at total4096 tokens. This directly supports reporting a provider length limit affecting these attempts. It does not, by itself, prove the precise internal context-allocation mechanism or that narration suppression caused the failures. Preserve the original envelopes and runtime context inspection, record the unknowns, and do not repair/rerun these identities under the original protocol. The twelve-cell block can expose an exploratory systems signal on mutually complete supported tasks; it cannot support unrestricted answer-preservation claims if these failures remain.

## Whole-block extension after all twelve cell closeouts

The following extension completes the independent answer review for all twelve episodes. Every episode now has an `episode_end` and `answer.json`; whole-fixture closing snapshot/cleanup validation remains a separate responsibility. Initial judgments above are retained unchanged. The remaining five episodes were reviewed from complete responses, wrapper/native outputs and final-invocation tool scratchpads, rather than from automatic strict-value scores.

| Closed cell | Independent supported-completion judgment | Evidence and limitations |
|---|---|---|
| `07-x1-C` | FAIL | Final answer is empty. Only calculator and listener clock values are acquired; source and palette values are not. Node/topic inventory and verbose topic fields are available, but none is delivered in a final report. Multiple turns are length-terminated; final prompt4094 + output2=4096. This shares the truncation limitation of x1 A/B and is not a successful low-token episode. |
| `08-t1-C` | PASS | Actual node discovery, palette node info, parameter list, pose info and all three successful RGB gets reach the final scratchpad. Final fields and summary match acquired facts. The description “blue-ish” is an informal interpretation of configured RGB, not an additional sensor observation or claim that rendered pixels were measured. No configured/observed substitution is needed to support the requested fields. |
| `09-t3-C` | PASS | Node list discovers palette and node info supplies the two publisher interfaces and cmd_vel subscription with correct full names/types. JSON and summary preserve the roles and requested exclusions. Final wording describes graph interfaces; it does not prove sensor/message delivery. |
| `10-t3-B` | PASS | Same supported node-list/node-info acquisition and correct interface-role output as09. A narrated second action remains despite the instruction, which is an adoption/efficiency matter, not a factual-support defect. |
| `11-d1_recovery-B` | FAIL despite oracle-matching JSON | Like06, chatter info supports all topic/count/endpoint/role fields. Both clock booleans are unsupported: no parameter values are acquired. Requested retired_source check never happens. Bare `source`/`listener` node-info calls fail, followed by discovery/full-name node info and final guesses. Final ends normally, so this is independent of the x1 length limit. |

### Exact failure provenance

All paths below are relative to `research/_artifacts/action_narration_20261111/primary-v1/`; line numbers refer to physical JSONL lines in the original preserved trace. A model-start line contains the complete serialized model-visible history for that invocation.

- `04-x1-B/trace.jsonl:31`: length-terminated action response at3995+101=4096; `:32` and `:33` request parameter **lists**, not values. `:40` contains the final model-visible tool observations. `:41` is the incomplete length-terminated final at4079+17=4096; `:42` closes the episode with that answer.
- `05-x1-A/trace.jsonl:22`–`:25`: requests the four actual clock gets. `:46` contains the final full model-visible history, including those values and both topic observations. `:47` is the truncated headings-only final at4069+27=4096; `:48` closes the episode. This distinguishes successful acquisition from failed delivery.
- `06-d1_recovery-C/trace.jsonl:4`, `:10`, `:18`, `:24`: the complete sequence of tool starts is topic info, bare-name node info, node list, full-name node info. There is no parameter get or retired_source inspection. `:15` contains the bare-name errors; `:29` contains successful full-name node-info output without clock values. `:30` preserves all four tool observations delivered before final generation. `:31` asserts both unsupported false booleans and ends with normal stop; `:32` closes the episode. The support failure concerns both clock leaves even though their values match the oracle.
- `07-x1-C/trace.jsonl:31` and `:37`: length-terminated clock-get action turns. `:32` and `:38` request only calculator/listener values. `:42` contains the final history; `:43` is the empty length-terminated final at4094+2=4096; `:44` closes the episode.
- `11-d1_recovery-B/trace.jsonl:4`, `:10`, `:18`, `:24`: the same complete tool-start sequence as06, again without any clock-value read or retired_source inspection. `:15` contains bare-name errors; `:29` supplies full-name node info without clock values. `:30` is final model-visible history; `:31` asserts both unsupported false booleans with normal stop at3047+124; `:32` closes the episode.

The supplied oracle and preserved runtime configuration are not model-visible evidence for a field. An advertised `/get_parameters` service in node info is not an observed `use_sim_time` value. Absence of a read is established over each complete four-tool-start recovery trace, not inferred solely from the final message.

### Supported-quality decision

| Task | A | B | C |
|---|---|---|---|
| t1 | PASS | PASS | PASS |
| t3 | PASS | PASS | PASS |
| d1_recovery | PASS | FAIL: unsupported clocks and omitted stale check | FAIL: unsupported clocks and omitted stale check |
| x1 | FAIL: length-limited incomplete final | FAIL: length-limited incomplete final | FAIL: length-limited empty final |
| Total supported completion | **3/4** | **2/4** | **2/4** |

**B does not meet the frozen no-loss condition. C fails independently of length termination.** Both match A only on the two Turtlesim tasks; neither has a supported mutually complete demo recovery pair with A. Therefore an apparent cost reduction on recovery cannot count as successful efficiency, and cross-application quality-preserving savings are not established. This is exploratory single-seed evidence, not statistical proof that terse instructions always harm quality.

No final false-source selection was established in these reviewed answers: published/subscribed roles are correct, RGB is acquired from configured parameters, and recovery endpoint identities are ultimately correct. The recovery defect is missing acquisition followed by unsupported values, plus omitted procedure. Intermediate bare-name read failures are node-identity/FQN mistakes. Do not relabel them as stale graph incarnation, false-source attribution, or successful clock evidence reuse.

The parent reports a preserved `/api/ps` observation of context_length4096 and matching checkpoint digest at `research/_artifacts/action_narration_20261111/runtime-model-context.json`. The observed length endings/token sums are directly trace-verified above; runtime-context interpretation should cite the separately preserved provider response. No mid-block correction or replacement result is justified by this review. Keep all twelve attempts and stop promotion under the existing protocol.

## Final closure exception: protocol incomplete

The completed episode reviews above do **not** establish successful protocol closure. Direct inspection of the saved final artifacts confirms:

- `oracle-after-12.json` enumerates all four expected nodes after the last episode.
- The later `oracle-after.json` node-list command returns0 with empty stdout. Its twelve direct node-info/parameter-dump/topic-info reads all return0, and its explicit retired_source check returns the expected missing-node error. Thus the final enumeration is invalid as a complete-node-set certificate; successful direct reads must not be used to manufacture the missing inventory.
- `setup.jsonl` records the study assertion failure after episode11, then four owned fixture processes exiting0 and daemon stop returning0. All twelve workers closed before the exception, but the full study did not satisfy its frozen snapshot assertion.

The A3/4, B2/4, C2/4 numbers above are **manual source-supported episode judgments conditional on the preserved direct reference observations and the successful after12 inventory**, not an unqualified protocol-valid accuracy estimate. The failed final enumeration prevents certifying full-set stability for x1; its result is additionally indeterminate on that oracle-closure dimension. All three x1 answers already fail complete delivery, so this uncertainty does not rescue them as successes. The two recovery answers in B/C still contain unsupported clock claims and omit the required stale check independently of the closure issue.

Keep the failed frozen scorer output and original scorer source. A separate, explicitly postexecution diagnostic extraction may compare direct observed values, but must not be called frozen scoring, reconstruct the inventory, or certify x1 completeness. No new snapshot or replacement run should be pooled under primary-v1. Scientific conclusion: no quality-preserving improvement is established; the failed closure further limits causal/accuracy claims rather than changing the original success rule.
