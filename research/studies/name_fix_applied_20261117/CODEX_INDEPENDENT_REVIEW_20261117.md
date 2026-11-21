# Independent review of the applied name-fix test

Reviewer: Codex, 2026-11-17. Scope: all eight changed full-run answers and eight deliberately selected unchanged full-run answers. This is a retrospective review of saved evidence, not a new model, GPU, or ROS run. It does not review held-out tasks.

## Verdict

I agree with Claude Code's substantive audit: all eight changed answers identify the entities required by the fixture, and each submitted object equals the fixture answer. Across the 15 changed names, no other field or value was added, dropped, moved to another entity, or changed. All eight sampled unchanged answers were preserved as recorded; two were already incorrect and appropriately remained incorrect under this name-only rule. The samples do not demonstrate that the rule is generally safe.

**Evidence wording correction:** [REPORT.md](REPORT.md) says each full name appears in a successful tool result. For seven of the eight changed episodes, none of the changed full names appears as a contiguous string in any non-final tool output. Instead, successful topic-info results report `Node name` and `Node namespace` in the same endpoint block; the full name is reconstructed by joining them. This evidence supports the identity and the relevant endpoint role, but the report's literal wording is too strong. In the other changed episode (bonsai, `nf_multi_1`, seed 1), a successful node-list result contains the three full names. The audit's [evidence_names](analyze_namefix.py) explicitly reconstructs node names from those fields.

## Method and provenance

- Read the original and accepted answers, name-fix handler events, and tool starts/ends in each selected `trace.jsonl`, not the generated audit checks. Compare against [namefix_tasks.json](namefix_tasks.json), [namefix_graph.json](namefix_graph.json), and relevant endpoint roles and parameter results. Compare complete JSON objects, including values and associations; object ordering is immaterial.
- The task file, graph, and rule SHA-256 hashes match [FREEZE.json](FREEZE.json). All 16 reviewed trace files match the `trace_hash` in [RESULTS_LOG.jsonl](RESULTS_LOG.jsonl). That checks consistency with the saved log, not an independently timestamped external signature. Current Git HEAD is `0244e10aacd78328959b9b100773abdec4956c26`; the freeze records `dc57e07290ab3a20cd89cf8f0638c201686ebc23` and says research evidence is Git-excluded.
- Direct comparison of all 64 full-run log rows finds eight changed answers, 15 recorded rewrite events and 56 unchanged answers. The logged strict counts are 54 to 62; the logged lenient counts are 62 to 62. These aggregate score counts were read from saved score fields, not independently rescored here.
- The eight unchanged examples were selected deliberately to cover an exact name, ambiguous-name tasks, a multi-key answer, an absent-name look-alike, and both logged incorrect answers; they are not a random sample.

## All eight changed answers

The paths below are relative to `research/_artifacts/runs/name_fix_applied_20261117/full_20261117T144620Z/`; each episode directory contains the original `trace.jsonl`.

| Task; model; seed | Episode directory | Independent finding |
|---|---|---|
| `nf_single_2`; lfm3; 1 | `lfm3_1.7b-namefix/000-nf_single_2-NAMEFIX-lfm3_1.7b-s1` | `yeoman` → `/nf/agate/yeoman`. Topic `/nf/chisel_t` identifies yeoman in namespace `/nf/agate` as the subscriber, matching truth. No other content. |
| `nf_single_1`; lfm3; 2 | `lfm3_1.7b-namefix/012-nf_single_1-NAMEFIX-lfm3_1.7b-s2` | `bobbin` → `/nf/lantern/bobbin`. Topic `/nf/kestrel_t` identifies bobbin in `/nf/lantern` as publisher. No other content. |
| `nf_multi_1`; qwen3.5; 2 | `qwen3.5_9b-namefix/001-nf_multi_1-NAMEFIX-qwen3.5_9b-s2` | Leading slashes added to the three node keys for xylem, mortar and zenith. Topic result identifies all three as subscribers; successful parameter requests return 13, 48 and 52 respectively. No value or association changed. |
| `nf_multi_1`; gpt-oss; 2 | `gpt-oss_20b-namefix/014-nf_multi_1-NAMEFIX-gpt-oss_20b-s2` | Bare keys `mortar`, `xylem`, `zenith` become `/nf/cipher/mortar`, `/nf/agate/xylem`, `/nf/lantern/zenith`. Subscriber and parameter results establish 48, 13, 52 respectively; associations preserved. |
| `nf_single_1`; bonsai-2; 1 | `bonsai-2_4b-namefix/002-nf_single_1-NAMEFIX-bonsai-2_4b-s1` | `bobbin` → `/nf/lantern/bobbin`, supported as the `/nf/kestrel_t` publisher. No other content. |
| `nf_multi_2`; bonsai-2; 2 | `bonsai-2_4b-namefix/003-nf_multi_2-NAMEFIX-bonsai-2_4b-s2` | `obsidian` → `/nf/cipher/obsidian` under `/nf/bolt_t`; `easel` → `/nf/agate/easel` under `/nf/ratchet_t`. Topic results show these publishers and jasper as subscriber to each. Both topic keys and pairings preserved. |
| `nf_multi_1`; bonsai-2; 1 | `bonsai-2_4b-namefix/007-nf_multi_1-NAMEFIX-bonsai-2_4b-s1` | The same three bare keys and values as the gpt-oss row become the same full names, with matching subscriber and parameter results; no value or association changed. |
| `nf_single_1`; bonsai-2; 2 | `bonsai-2_4b-namefix/012-nf_single_1-NAMEFIX-bonsai-2_4b-s2` | `bobbin` → `/nf/lantern/bobbin`, supported as the `/nf/kestrel_t` publisher. No other content. |

Every old node name above has exactly one whole-segment suffix match among the fixture's node FQNs. That is a property of this fixture, not evidence that a suffix will be unique in other environments.

## Eight unchanged answers

Each trace has identical original and accepted JSON objects and an empty name-fix event list.

| Task; model; seed | Episode directory | Finding |
|---|---|---|
| `nf_single_1`; qwen3.5; 1 | `qwen3.5_9b-namefix/002-nf_single_1-NAMEFIX-qwen3.5_9b-s1` | Full `/nf/lantern/bobbin` is the evidenced publisher and matches truth; leave intact. |
| `nf_multi_1`; lfm3; 2 | `lfm3_1.7b-namefix/001-nf_multi_1-NAMEFIX-lfm3_1.7b-s2` | Three exact full-name keys and gains 13, 48, 52 match truth and successful tool results; leave intact. |
| `nf_multi_2`; bonsai-2; 1 | `bonsai-2_4b-namefix/011-nf_multi_2-NAMEFIX-bonsai-2_4b-s1` | `{"test":"value"}` is wrong and lacks the required `upstream` object despite available topic evidence. There is no name to repair; preserving it is consistent with this rule, not a correct answer. |
| `nf_amb_1`; gpt-oss; 1 | `gpt-oss_20b-namefix/011-nf_amb_1-NAMEFIX-gpt-oss_20b-s1` | Exact `/nf/dynamo/eclipse`, limit 901, supported by list and parameter results; the look-alike is `/nf/ivory/eclipse`. Leave intact. |
| `nf_amb_2`; qwen3.5; 1 | `qwen3.5_9b-namefix/009-nf_amb_2-NAMEFIX-qwen3.5_9b-s1` | Exact `/nf/dynamo/nozzle`, gain 71, supported by publisher and parameter results; `/nf/ivory/nozzle` is the subscriber. Leave intact. |
| `nf_exact`; lfm3; 1 | `lfm3_1.7b-namefix/004-nf_exact-NAMEFIX-lfm3_1.7b-s1` | Requested exact `/nf/lantern/talon`, gain 61, agrees with the parameter result. Leave intact. |
| `nf_absent`; qwen3.5; 1 | `qwen3.5_9b-namefix/014-nf_absent-NAMEFIX-qwen3.5_9b-s1` | `/flint/umbra`, `running: false` matches truth; the filtered list finds `/nf/flint/umbra` but an exact node-info lookup fails. Retaining the requested exact name avoids a wrong suffix substitution. |
| `nf_absent`; bonsai-2; 2 | `bonsai-2_4b-namefix/004-nf_absent-NAMEFIX-bonsai-2_4b-s2` | `/nf/flint/umbra`, `running: true`, rate 855 describes the observed look-alike but answers the wrong question. The rule leaves the already observed full name intact; it neither causes nor corrects the model's identity error. |

## Limits

The original scores in these episodes classify all rewritten originals as strict-unsupported and lenient-supported; no originally strict-supported answer was rewritten. Thus the harm rate conditional on rewriting a strict-supported answer has denominator zero. None of these unchanged examples exercises a live ambiguous-short-name rejection, unseen-name rejection, or collision. The review establishes what happened in these saved cases, not how often the rule helps or harms on other tasks, deployments, or models. No live ROS, GPU, or model inference was used.
