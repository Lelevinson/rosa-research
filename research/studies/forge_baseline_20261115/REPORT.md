# Forge released baseline: matched pilot comparison

2026-11-15, Asia/Taipei. **80/80 assigned episodes completed.** Four local models, 10 development tasks and two seeds per model. Synthetic ROS fixtures with real local Ollama inference. The two thinking-on smoke episodes are a separate record and never enter these totals. Frozen scores retain the changing-fixture validity defects described below; those affected failures must not be interpreted as model staleness.

## Setup and provenance

The owner authorized this full matrix after the smoke. [PROTOCOL_FULL.md](PROTOCOL_FULL.md) freezes the preflight, cells, costs and stop rules; [FULL_PLAN.json](FULL_PLAN.json) lists every cell. PyPI forge-guardrails 0.10.1 executes through its unmodified WorkflowRunner. The same 12 C1 read tools plus released respond are offered, with required_steps=[], no prerequisites, terminal respond, 40 calls including retries, release default validation/error/retry/replay behavior, TieredCompact(keep_recent=2), budget 65536. Forge and C1 exclude write tools from the model menu as a shared safety setting. No per-task route, answer map, repair policy, cache or C1 validator was added.

Exact C1 system messages are preserved separately, with only final_answer -> respond, as printed with the complete diff in [REPORT_THINKING_ON_SMOKE.md](REPORT_THINKING_ON_SMOKE.md). Their JSON-object wording is unchanged despite respond's string argument. Identical task text is followed by Forge's own messages/nudges. The isolated uv environment, read-only reuse of project ROSA/LangChain dependencies, versions and import paths remain as documented in SMOKE_PROVENANCE.json; project dependencies and production source were not modified.

Ollama: temperature .7, num_ctx 65536, num_predict 4096, assigned seed, explicit per-model think field. The installed pilot SDK serializes think:false for **all four models, including gpt-oss**. PILOT_TRANSPORT.json preserves offline SDK serialization of actual historical logical messages/schemas. Historical raw HTTP bodies were not retained; this is reconstructed wire evidence, not a claimed historical HTTP capture. The matched HTTP wrapper changes only options and the explicit think field, leaving inherited send, parsing and Forge logic unchanged. Every real request is retained and checked; first-response checks are in TRANSPORT_CHECKS_FULL.jsonl.

ROS domain 220, localhost only, unchanged Stage 3/E1h fixtures and scripted change/reset hook, pilot interpreter for fixture nodes, before/after oracle and cleanup checks. Scripted fixture writes are outside the agent and are identical to the pilot. 90-second HTTP timeout, 900-second episode timeout, 10-hour full-run cap. Per-session freeze.json, driver snapshot, plan, prompts/diff, source hashes, worker logs and raw traces live under research/_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/ and its separately frozen full_20261115T091338Z-resume1/ continuation.

Frozen scorer-v2.0 SHA-256 c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9 is shared by all arms. Historical A1/C1 traces were hash-verified and rescored offline; they were not rerun. A1 is the stock executor with the deconflicted A1 prompt, not unmodified-prompt ROSA. S0 has no pilot data. Source/control hashes and v2 scores are in FULL_COMPARATORS_SOURCE.json and COMPARATORS_V2.json.

Menu fairness limit: the original A1 trace offers the full stock menu, including write-tool schemas, while the unchanged native guard blocks writes before ROS. C1 and Forge offer only the 12 read tools plus their finish tool. Thus A1 is a historical descriptive comparator with a different menu; C1 is the relevant strong loop comparator with matched read-tool access. No new A1 run or retroactive menu modification was made.

## Results

All costs below include failed attempts. Native-operation counts cover agent command starts; fixture setup, oracle and scripted changes are logged separately. Token totals are reported input plus output. No thinking-on smoke row is included. Forge has usage for 641 of 643 requests: two recovered HTTP 500 parser errors omit usage, so its token totals exclude unknown work and are lower bounds. The raw errors are lfm3 u3 seed 1 L41 (unexpected XML EOF) and resumed gpt-oss e1h_amb_1 seed 2 L50 (invalid tool-call JSON). Neither episode was rerun. TOKEN_USAGE_COVERAGE.json confirms historical A1 472/472 and C1 486/486 requests have usage.

| Model | Arm | Recorded / assigned | Supported-complete | LLM requests | Reported input tokens | Reported output tokens | Reported total tokens | Native ops | Error episodes | Timeouts | Compactions |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lfm3:1.7b | A1 | 20/20 | 15 | 135 | 1028694 | 61733 | 1090427 | 129 | 2 | 0 | n/a |
| lfm3:1.7b | C1 | 20/20 | 17 | 105 | 408791 | 45905 | 454696 | 122 | 0 | 0 | n/a |
| lfm3:1.7b | Forge | 20/20 | 12 | 213 | 689761 | 46431 | 736192 | 244 | 1 | 0 | 0 |
| qwen3.5:9b | A1 | 20/20 | 19 | 86 | 554213 | 9523 | 563736 | 120 | 0 | 0 | n/a |
| qwen3.5:9b | C1 | 20/20 | 20 | 87 | 242071 | 9672 | 251743 | 120 | 0 | 0 | n/a |
| qwen3.5:9b | Forge | 20/20 | 18 | 102 | 299469 | 7725 | 307194 | 122 | 0 | 0 | 0 |
| gpt-oss:20b | A1 | 20/20 | 7 | 54 | 207182 | 10631 | 217813 | 34 | 11 | 0 | n/a |
| gpt-oss:20b | C1 | 20/20 | 20 | 105 | 203554 | 20020 | 223574 | 116 | 0 | 0 | n/a |
| gpt-oss:20b | Forge | 20/20 | 17 | 133 | 316953 | 19720 | 336673 | 121 | 0 | 0 | 0 |
| bonsai-2:4b | A1 | 20/20 | 6 | 197 | 1391619 | 17828 | 1409447 | 191 | 5 | 0 | n/a |
| bonsai-2:4b | C1 | 20/20 | 13 | 189 | 726761 | 19728 | 746489 | 198 | 0 | 0 | n/a |
| bonsai-2:4b | Forge | 20/20 | 8 | 195 | 818481 | 17149 | 835630 | 303 | 1 | 0 | 0 |

Descriptive totals over recorded cells: Forge 55/80 supported-complete, 643 requests, 2215689 tokens and 790 native operations. Historical C1: 70/80, 486 requests, 1676502 tokens and 556 native operations. Historical A1: 47/80, 472 requests, 3281423 tokens and 474 native operations. These are frozen-label observations with the validity qualifications below, not a causal or novelty verdict.

'Error episodes' counts recorded episode errors/worker errors (or original pilot aborts), including timeouts and budget exhaustion; it is not a claim that each is a Python process crash. See the per-attempt ledger for exact causes. Historical timeout classifications in original abort lists are preserved rather than inferred from an empty new-run error field. New Forge worker crashes: 0; iteration-limit errors: 2. If a backend failure provides no usage, token totals include only reported usage, not an estimate of unobserved generation.

## Same-cell comparison

[All 80 cell rows](SAME_CELL_COMPARISON.md), with raw sources and full costs in [SAME_CELL_COMPARISON.json](SAME_CELL_COMPARISON.json). The following discordances use only cells with a recorded Forge attempt:

| Model | Comparator | Both supported | Only Forge supported | Only comparator supported | Neither supported |
|---|---|---:|---:|---:|---:|
| lfm3:1.7b | A1 | 9 | 3 | 6 | 2 |
| lfm3:1.7b | C1 | 10 | 2 | 7 | 1 |
| qwen3.5:9b | A1 | 17 | 1 | 2 | 0 |
| qwen3.5:9b | C1 | 18 | 0 | 2 | 0 |
| gpt-oss:20b | A1 | 5 | 12 | 2 | 1 |
| gpt-oss:20b | C1 | 17 | 0 | 3 | 0 |
| bonsai-2:4b | A1 | 3 | 5 | 3 | 9 |
| bonsai-2:4b | C1 | 6 | 2 | 7 | 5 |

A hand-read disagreement in Forge's favor: matched thinking-off lfm3 p3 seed 2 (`lfm3_1.7b-stage3/005-p3-Forge-s2/trace.jsonl`) reads the two links at L25/L34 and the correct setpoint at L52, then submits the correct object at L62. Historical same-cell C1 is unsupported because its first-node assignment is wrong. This is a descriptive cell disagreement, not evidence that thinking is necessary or that Forge caused the improvement.

## Transport checks

| Model | First HTTP status | First live wire think | Matches reconstructed pilot | First response has no thinking |
|---|---|---|---|---|
| lfm3:1.7b | 200 | false | True | True |
| qwen3.5:9b | 200 | false | True | True |
| gpt-oss:20b | 200 | false | True | False |
| bonsai-2:4b | 200 | false | True | True |

Historical raw thinking was not saved. With reasoning=False the pilot's LangChain adapter does not retain returned thinking in additional_kwargs. Thus absence in historical message logs does not establish wire absence. Current raw responses are retained without removing thinking; the table reports what was actually observed. gpt-oss returns raw thinking despite the matched think:false field. PILOT_THINKING_VISIBILITY_CHECK.json demonstrates offline, with no model inference, that the pilot SDK drops a mock raw thinking payload while retaining the answer and token usage. This explains historical invisibility, but does not recover historical raw responses. No per-model think value was invented, no raw output was suppressed, and no thinking ablation was run.

FULL_AUDIT.json independently checks cell uniqueness, raw trace hashes, every wire option/think field, initial system messages, costs, token-usage coverage, loaded context, agent writes, fixture changes/resets, and oracle/cleanup records. It also verifies all 52 installed Forge Python files against the wheel RECORD and verifies that the thinking-on smoke report and ledger remain unchanged.

## Hand-read Forge failures

Hand-read original matched Forge traces. Paths below are relative to
`research/_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/`.
Line numbers refer to the immutable JSONL traces, not a reconstructed transcript.
Control outcomes use the same task/model/seed under frozen scorer v2.

1. **lfm3 h4 seed 1: correct acquired facts, malformed final keys; C1 succeeds.**
   `lfm3_1.7b-stage3/002-h4-Forge-s1/trace.jsonl`: L38 gives anvil's three
   input topics; L51 names their publishers. Gains are actually read at
   L69 (zephyr 74), L78 (dune 65), and L87 (oasis 89). L96 reads an
   additional unrequested anvil gain. At L101 `respond.message` puts leading
   spaces in the oasis/anvil keys and includes the extra anvil field, followed
   by a promise to recompute. Forge returns that message at L103; the promise
   causes no further iteration after a successful terminal call. Support
   passes, exactness fails. Same-cell C1 is supported in 9 requests; Forge
   uses 11. The observed failure is final content, not a failed ROS read.

2. **lfm3 absent-target seed 2: decoy mistaken for requested node; C1 succeeds.**
   `lfm3_1.7b-e1h/013-e1h_abs_1-Forge-s2/trace.jsonl`: the exact requested
   `/ember/mistral` lookup fails at L11. An unanchored listing at L17–20
   returns the different `/e1h/ember/mistral`. Forge then reads that decoy
   (L26–29) and its limit 279 (L44–47), and at L52 submits `running:true`
   for the decoy plus an unrequested limit. The exact requested node is
   absent. Same-cell C1 is supported; Forge's six-request answer is wrong.
   A successful native read of a similarly named node did not establish the
   requested entity's presence.

3. **lfm3 ambiguous-node seed 2: repeated successful reads until the cap;
   C1 succeeds.** `lfm3_1.7b-e1h/014-e1h_amb_1-Forge-s2/trace.jsonl`:
   L40 and L49 deliver the two nodes' modes; L58 and L67 deliver both limits.
   The facts needed to select the fast node and its limit have arrived.
   From L73 through L361, calls alternate the same two `limit` reads instead
   of submitting a terminal answer. L366–367 record MaxIterationsError at
   40 requests, with no final answer. These are successful repeated reads,
   not an unavailable ROS source. The same-cell C1 control is supported.
   This illustrates a failure in this run; it does not establish that a
   particular countermeasure would preserve correctness or reduce total cost.

4. **Qwen service-provider seed 1: type acquired, provider guessed; C1 succeeds.**
   `qwen3.5_9b-stage3/023-v2-Forge-s1/trace.jsonl`: L8–11 obtains only
   `/plant32/cedar_reset`'s type. L17–20 lists node names, including both
   quill and the true provider wharf; it does not associate a node with the
   service. No `node_info` is called. At L25 `respond` names quill, which is
   wrong; the correct node is wharf. Forge uses three requests and returns
   an exactness failure, while same-cell C1 is supported. The frozen support
   screen's empty missing-evidence list is not proof the provider relation
   was read: listing the name passes its textual occurrence check, whereas
   the exact-answer check rejects the wrong relation. Scoring was not changed.

5. **gpt-oss h4 seed 2: facts present, malformed outer answer JSON; C1
   succeeds.** `gpt-oss_20b-stage3/045-h4-Forge-s2/trace.jsonl`: L101,
   L110 and L119 deliver gains 74, 65 and 89. L124 submits a string containing
   the correct node, publisher mapping and gains, but it ends with a stray
   quote after the gains object and lacks the outer closing brace. L126
   returns the same malformed string. The frozen last-JSON-object extractor
   selects the valid inner gains object, so the scored object lacks node,
   publishers and the enclosing gains key. This is a serialization/scoring
   interaction with factually correct content in the raw message, not a
   missing native read. Same-cell C1 is supported; Forge uses 14 requests.
   No JSON repair, label override or scorer revision was applied.


## Orchestration recovery and fixture validity

After 53 recorded cells, a parent-driver check stopped the matrix following a safely rejected malformed read in gpt-oss e1h_amb_2 seed 1. Forge had already recovered and returned a supported answer. The native guard blocked the malformed command; no unsafe native operation executed. Only the parent orchestration was corrected to log rejections without aborting independent later cells. The remaining 27 cells resumed in their original order with fresh fixture/oracle checks under the original 10-hour cap. RESUME_ORCHESTRATION_AUDIT.json proves that episode, client, tool dispatch, prompt and scoring definitions did not change. No completed model cell was rerun or excluded. All owned nodes from the interrupted session were cleaned up, but its post-oracle was not performed; that gap remains in the original evidence.

FIXTURE_EVENT_AUDIT.json separately audits the changing-task traces for all three arms. The unchanged EpisodeHook watches an exact absolute ROS command. In gpt-oss Forge e1h_chg_1 seed 2 (`gpt-oss_20b-e1h/050-e1h_chg_1-Forge-s2/trace.jsonl`), valid relative-name reads at L9–10 and L27–28 observe level 30 both times; the scripted change to 45 never fires. L36 reports final_level=30, which matches its last native read, but the frozen scorer expects 45 and marks failure. This is a fixture scheduling validity issue, not evidence of a stale cached value. The same missed-trigger pattern also exists in historical A1 gpt-oss e1h_chg_2 seed 2 and A1 bonsai e1h_chg_1 seed 2; the audit checks the strong C1 controls too. Frozen scores and assigned denominators are retained unchanged. No corrected success count, post-hoc exclusion, hook repair or replacement run is substituted for those data.

| Arm | Audited changing cells | Trigger fired | Valid relative read but trigger missed | Other missing triggers |
|---|---:|---:|---:|---:|
| A1 | 16 | 14 | 2 | 0 |
| C1 | 16 | 16 | 0 | 0 |
| Forge | 16 | 15 | 1 | 0 |

## What this comparison can and cannot show

The comparison measures complete supported answers and costs on exactly the pilot development cells, using a common scorer and preserved failure denominators. It does not establish novelty, cross-application generalization, statistical significance, equivalence or universal superiority. Controls are historical, not concurrent; two seeds, shared fixture structure, model/runtime variability and nonidentical finish-tool schemas remain limitations. The pilot SDK streams internally whereas the released Forge send path buffers a response; wire serialization and timeout semantics are therefore not identical even with matched sampling and nominal timeout. Bonsai and Qwen share a model family. A higher success count alone does not establish lower cost. Native reads and observed tool outputs, rather than a requested call alone, support the scoring.

## Open questions (not acted on)

Thinking-on Forge solved the smoke p3 cell where historical thinking-off C1 failed. The owner suggests a separate thinking-on versus thinking-off test later. That observation confounds reasoning setting, session and stochastic generation; it is not causal evidence for either thinking or Forge. The authorized matched matrix also contains a thinking-off success on p3 seed 2, so the smoke alone does not establish a thinking benefit. No separate thinking test, prompt tuning or mechanism change was performed.

## Code and data flow

prepare_full.py extracts valid historical C1 cells and reconstructs the pilot SDK transport without inference. run_full.py:MatchedTransport injects the explicit think field while PilotOptionsClient changes options only. episode runs released WorkflowRunner on the ordinary tool callables, logs requests/results/compaction, and manages the unchanged E1h episode hook. session owns fixture/oracle/context/cleanup; append_result scores and appends every attempt to RESULTS_MATCHED.jsonl. report_full.py rescored the controls, joins identical model/environment/task/seed cells, and generates this report. ATTEMPTS_FULL.jsonl preserves starts; RESULTS_MATCHED.jsonl preserves outcomes and trace hashes. The original smoke reports, logs, source and failed setup sessions remain separate and unchanged.

Executed command from the repository root (historical paths retained; not an instruction to overwrite this completed run):

```bash
UV_CACHE_DIR=/tmp/rosa-forge-uv-cache \
ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 \
ROS_HOME=/tmp/rosa-forge-ros-home ROS_LOG_DIR=/tmp/rosa-forge-ros-logs \
uv run --no-project --python /tmp/rosa-forge-env-20261115/bin/python \
  python research/studies/forge_baseline_20261115/run_full.py full \
  research/_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z
```

The continuation used the same environment and command with mode `resume` and output suffix `-resume1`. `uv run` executes with uv; `--no-project` avoids syncing the project environment, and `--python` selects the isolated interpreter. The ROS variables select the disposable domain, localhost discovery and temporary log locations. A new reproduction needs fresh output and ledger locations; the driver refuses to rerun already-recorded cells in full mode.
