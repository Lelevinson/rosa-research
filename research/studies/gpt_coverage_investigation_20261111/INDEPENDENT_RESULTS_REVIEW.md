# Independent source-support review — GPT coverage investigation

2026-11-11, Asia/Taipei. Read-only adjudication of actual model-visible tool
observations, native receipts, final answers and oracle-before. This review ran
no inference or ROS operation and changed no driver/scorer. It is independent of
the automatic supported_screen. Source line numbers below refer to each raw
`trace.jsonl` under
`research/_artifacts/gpt_coverage_investigation_20261111/primary-v1/`.

## Initial scope: closed episodes00–03 only

At this review checkpoint, the explicitly reviewed cells are00-openai-x1-A,
01-ollama-d1_recovery-A,02-ollama-x1-A and03-openai-d1_recovery-A. No pending or
unreviewed cell is assigned a result. Final study inventory/cleanup is not yet
certified by this checkpoint; the pass judgments below remain conditional on
valid before/after reference observations at eventual closeout.

Oracle-before preserves two actual persistent inventories, both containing the
four fixture nodes (plus the evaluator node outside the requested namespaces).
Direct parameter dumps give false for each use_sim_time. Topic metadata gives
std_msgs/msg/String with one publisher/one subscriber on chatter, and
turtlesim/msg/Pose with one publisher on pose. The retired identity's direct
inspection returns1 with the actual missing-node error.

| Closed cell | Final fields | Acquisition and procedure | Independent judgment |
|---|---|---|---|
| 00-openai-x1-A | All four clocks false; both complete topic type/publisher objects | Discovered actual nodes/topics; obtained four actual parameter values and verbose info for both topics | Supported, pending study closeout |
| 01-ollama-d1_recovery-A | All10 scalar endpoint/topic fields correct | Stale identity checked once before recovery; actual source/listener clock values read | Supported, pending study closeout |
| 02-ollama-x1-A | All eight requested scalar fields correct | Four actual clock reads and both verbose topic reads; complete final JSON/narrative | Supported, pending study closeout |
| 03-openai-d1_recovery-A | All10 scalar endpoint/topic fields correct | Stale identity checked once before recovery; both endpoint values read | Supported, pending study closeout |

### 00-openai-x1-A

Lines10/12 contain actual topic/node discovery, including exactly the four
requested-namespace nodes. Lines29/31 provide complete chatter/pose metadata.
The four model-visible parameter receipts are lines33,35,37,39; their actual
arguments identify calculator, palette, listener and source, respectively, and
each contains `Boolean value is: False`. Line42 returns the complete JSON with
all four identities, false values and correct topic objects. Every final field
has an acquired source; this is not default-value agreement alone. There is no
extra final narrative to adjudicate and no wrong-source claim identified.

The ordinary A model issued no action prose in this cell, despite having no B
terse instruction. That is relevant descriptive evidence: action verbosity is
not fixed solely by the arm name. It is not yet an A/B treatment comparison.

### 01-ollama-d1_recovery-A

The first native action is the requested retired-node inspection. Its missing
outcome is preserved at line7 and delivered at line8, monotonic8007.714736035.
Actual discovery starts later at line12, monotonic8011.001608681. No concurrent
or earlier recovery operation bypasses the initial check, and no duplicate retired
check occurs. The source/listener identities and roles come from topic metadata
at line19, with one publisher and one subscriber.

The model first attempts node-info (line28), then explicitly recognizes that
node-info does not contain the clock values. It requests both parameter values;
actual false receipts arrive at lines37/39. Thus the final false claims are
supported despite the earlier unnecessary information path. A repeated topic
read at line46 adds evidence/cost, not a new requirement. Final line49 preserves
all requested JSON fields and gives an accurate absence/source summary. No
unsupported final factual assertion was identified.

### 02-ollama-x1-A

Lines10/12 discover all four nodes and both relevant topics. Line27 supplies
actual verbose topic types/publisher counts; line31's node-info does not supply
clock values. Parameter-list receipts at lines44,46,48,50 establish names only;
they are not credited as values. The model then performs four real value reads,
delivered at lines63,65,67,69, each false with the corresponding node identity
retained in arguments. A repeated calculator read at line76 is additional cost.

Final line79 contains complete JSON and reiterates all four values and topic
metadata correctly. The real-time versus simulated-time explanation follows the
observed use_sim_time configuration; its closing compatibility wording is limited
to consistent clock configuration, not certification of overall application
compatibility. No final wrong-source or unsupported acquired-value claim was
identified. This cell supplies a complete nontruncated response where the old4096
study failed, but provider/adapter changes prevent isolating context alone as the
causal difference from the historical cell.

### 03-openai-d1_recovery-A

The first native action is exactly one retired-node inspection. The missing
outcome appears at line7 and is delivered at line8, monotonic8114.437185626;
node/topic discovery starts later at line12, monotonic8119.595213145. Thus the
procedural dependency is actually respected, not merely accepted by start order.
Topic-info at line26 establishes chatter type, counts, actual endpoint names,
namespaces and roles. Lines35/37 deliver actual source/listener parameter values,
both false. Final line40 returns all requested JSON fields with supported values
and correct identities. No unsupported extra narrative exists. The prompt asks
that the stale check be performed; its prescribed final JSON does not require a
separate absence field, so this concise JSON is not marked incomplete for omitting
an unrequested narrative summary of the already performed check.

## What this checkpoint establishes

All four reviewed **A** cells have supported final requested fields. Both d1
cells also meet the exact initial-check procedure and observed ordering. These
facts do not establish B/V outcomes, a complete study success rate, a causal
model-weights explanation or a framework algorithmic improvement. Both providers
can obtain the needed semantic evidence in these A cells. Additional reads and
model decisions remain costs to report even when answers are supported.

## Second checkpoint: additionally reviewed closed04–08

These five additional cells were closed when inspected. Cell09 remains unreviewed
at this checkpoint. The original exact procedure is retained: the named stale
identity must be inspected first and its missing outcome must precede actual
endpoint recovery/discovery. A tool-call list with the stale call written first
is not proof that the dependent ordering was respected by concurrent execution.
No procedural requirement is waived to obtain a favorable efficiency result.

| Closed cell | Final factual/source support | Strict procedural order | Overall judgment before closeout |
|---|---|---|---|
| 04-openai-d1_recovery-B | All10 fields correct; both clock values actually read | Fails: endpoint discovery overlaps initial stale check | Strict failure; factual coverage retained |
| 05-ollama-d1_recovery-B | All10 fields correct; both clock values actually read | Fails: endpoint discovery overlaps initial stale check | Strict failure; factual coverage retained |
| 06-ollama-x1-B | All8 fields correct and acquired | No stale procedure applies | Supported |
| 07-ollama-d1_recovery-V | All10 fields correct; both clock values actually read | Fails: endpoint discovery starts even before stale native start | Strict failure; factual coverage retained |
| 08-openai-d1_recovery-V | All10 fields correct and acquired | Passes: actual missing outcome precedes recovery | Supported |
+
+The leading plus signs in this table are formatting artifacts only if present;
+the entries are judgments on original traces, not amended experimental outputs.
+
+### 04-openai-d1_recovery-B: complete facts, ordering failure
+
+Line4 proposes stale node-info and actual chatter topic-info together. Native
+stale start is line7 (monotonic8161.314568533); topic-info starts at line8
+(8161.314818986). Topic-info even completes first at line9 (8161.774199964),
+before the stale missing outcome at line11 (8161.780909124; delivered line12).
+Thus the actual endpoint discovery did not wait for the requested conditional
+check. Exactly one stale read occurred, but its order is not sufficient.
+
+Topic-info receipt line10 establishes type/counts and endpoint identities/roles.
+Parameter receipts lines19/26 give the source/listener false values with their
+actual arguments preserved. Final line29 supplies all10 fields correctly. No
+unsupported value or final source claim was identified. This is a procedural
+failure, distinct from old B's unsupported clocks and omitted check.
+
+### 05-ollama-d1_recovery-B: complete facts, ordering failure
+
+Line4 again proposes the stale inspection and topic discovery in one response.
+Native starts at lines7/8 are8184.873666097/8184.873879282; the missing outcome
+does not arrive until line9 at8185.412471982 (delivered line10). The topic-info
+request already ran during that interval. Its slightly later completion at line11
+does not repair the early admission. Both calls are read-only, but the task's
+specified dependency is still violated.
+
+The complete topic receipt appears at line12 and is repeated later. Lines44/46
+deliver actual false clock values after explicit parameter reads; node-info at
+line35 is not credited as clock evidence. Final line56 is complete correct JSON.
+No unsupported final narrative exists. Counts/identities/values pass factual
+support; overall strict completion fails only the initial ordering requirement.
+
+### 06-ollama-x1-B: supported complete answer
+
+Actual node/topic discovery appears at lines10/12. The two verbose topic results
+are supplied at line27; node-info at line31 is not treated as value evidence.
+Four actual parameter receipts at lines44,46,48,50 give false for source,
+calculator,listener,palette respectively, with actual subjects retained in their
+arguments. Final line53 includes all four clock entries, both topic objects and
+an accurate summary of observed publisher identities. No source confusion,
+missing requested final field or unsupported final claim was identified.
+
+### 07-ollama-d1_recovery-V: verification does not enforce initial order
+
+Line4 places the stale node-info first in the proposed tool-call array and
+topic-info second, but actual native scheduling starts topic-info first at line7
+(8272.289011378), followed by stale node-info at line8 (8272.289490945). The
+missing outcome arrives at line9 (8272.728114104; delivered line10). Therefore
+this cell fails even the first-native-start screen, as well as the stricter
+outcome-before-discovery requirement. Call-array order is not execution order.
+
+The factual report is nevertheless supported: line12 supplies complete actual
+topic/endpoint metadata; lines30/32 supply both actual false parameter values.
+Final line35 preserves every requested field and its absence/source summary is
+accurate. The added generic verification instruction did not enforce this
+procedural obligation in the observed Qwen cell. Do not reclassify the failure
+as guessed values, a missing check, stale graph identity or lack of native tools.
+
+### 08-openai-d1_recovery-V: supported including procedure
+
+Line4 proposes only the stale inspection. Native outcome line7 is the actual
+return1/missing-node result at8315.818543152, delivered at line8 by8315.818684652.
+Only afterward does line11 propose node/topic discovery and topic-info; first
+native recovery starts at8320.651824238. Exactly one stale read occurred.
+
+Line21 supplies the full actual topic metadata; lines32/34 provide source/listener
+false values. Final line37 contains all10 requested fields with correct source
+identity and roles. No extra unsupported narrative exists. This is an observed
+ordinary fixed-prompt success, not evidence of a new framework algorithm or a
+statistical guarantee that V fixes ordering.
+
+## Updated interpretation at the second checkpoint
+
+All nine reviewed final answers have their requested factual values supported by
+actual acquisition. Three d1 cells nevertheless fail the unchanged initial-order
+procedure. Keeping these axes separate is essential: the old unsupported-clock
+failure is absent in the reviewed new cells, but full task compliance has not
+become automatic. The model/prompt/provider/context differences and single
+observations prevent attributing the change to a sole internal cause.
+
+No overall10-cell rate or final oracle/cleanup certification is asserted here.

## Final checkpoint: cell09 and full closeout verified

### 09-openai-x1-B
+
+Line8 supplies all four actual node identities. Line15 discovers the topic names.
+Line32 supplies verbose pose/chatter receipts with the correct types and publisher
+counts. Four actual false clock values are delivered at lines34,36,38,40 for
+source,listener,calculator,palette respectively; actual argument identity is
+preserved. Final line43 contains all8 requested scalar fields and no unsupported
+extra narrative. This is a supported complete answer, not default-value agreement.
+
+### Independent reference and teardown checks
+
+All seven snapshots are present: before, after02/04/06/08/10, and final. Each
+contains both predeclared persistent graph observations. All14 observed sets
+contain exactly the four fixture nodes within the two requested namespaces;
+the evaluator/daemon identities outside those namespaces are not extra requested
+nodes. Every snapshot's direct node-info, parameter-dump and topic-info stdout
+matches the before snapshot byte-for-byte. All direct acquisition return codes
+are0, except each explicit retired-node inspection, which returns1 with the actual
+missing-node message. No unavailable field was filled from a guessed truth value.
+
+The original CLI enumeration is still empty in oracle-after-08 and oracle-after.
+Those negative observations remain preserved. They do not invalidate this study's
+predeclared independent persistent-observer criterion, which was introduced
+before scored execution rather than selected after these outcomes. Do not erase
+the disagreement or claim that every ROS enumeration interface was complete.
+
+setup.jsonl line27 records study_closed with10 attempted/10 scheduled cells.
+Lines28–31 record all four owned fixture processes exiting0; line32 records the
+oracle graph close; line33 records daemon stop0. Every episode has one episode_end,
+no model_error, and no observed length termination. These closure facts are
+independently inspected saved evidence, not inferred from driver returncode alone.
+
+### Final counts and interpretation
+
+| Arm/provider scope | Complete supported factual answers | Exact procedure plus complete support |
+|---|---:|---:|
+| OpenAI A |2/2|2/2|
+| OpenAI B |2/2|1/2|
+| OpenAI V |1/1|1/1|
+| Ollama A |2/2|2/2|
+| Ollama B |2/2|1/2|
+| Ollama V |1/1|0/1|
+| All10 scored cells |**10/10**|**7/10**|
+
+All92 requested final scalar fields are correct and supported by actual
+acquisition in these10 observations (four x1 cells×8 plus six d1 cells×10).
+The three strict failures are exactly04-openai-d1_recovery-B,
+05-ollama-d1_recovery-B and07-ollama-d1_recovery-V, solely because endpoint
+discovery did not wait for the initial stale-check outcome. No final wrong-source
+claim or unsupported value was identified. An automatic first-start-only screen
+can over-credit04/05; manual native-interval review is the stricter final judgment.
+
+The old missing-clock-read failure is not reproduced by these new factual
+trajectories. The broader full-task/no-loss condition still fails for B, since
+each provider's A supports d1 including order while its B violates order. Luna's
+fixed ordinary V cell respects that order and acquires all facts in this sample;
+Qwen's V does not. This is not a statistical claim, a proof of model superiority,
+or validation of a framework algorithm. Historical-to-new differences include
+context capacity, adapter/provider configuration and ordinary model trajectories;
+model weights or context alone are not isolated causes.
+
+This final checkpoint supersedes the earlier pending-closeout limits for this
+new primary block only. The original November11 experiment's incomplete closure
+and unsupported-clock failures retain their historical status unchanged.

### Structural counterfactual, separately labeled
+
+In all three ordering-failure cells04/05/07, line4's assistant call array places
+the stale node-info call before topic-info. Serial dispatch in that proposal order
+would impose first-completion-before-second-start for the recorded initial batch,
+without a task semantic map or additional model selection turn. This was not run
+and does not repair the measured cells or establish a new latency/output result.
+The concurrent observed results and strict failures remain unchanged. A future
+candidate must confront this ordinary host control and an equally informed
+declared-dependency executor while preserving fair concurrency capabilities.
