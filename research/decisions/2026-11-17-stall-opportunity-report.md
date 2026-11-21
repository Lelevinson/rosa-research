# Stall-breaker opportunity: offline development recount

**Owner decision, 2026-11-17:** NO-GO accepted; park the stall breaker as future work. Keep this report, its protocol, script and per-episode recount. Do not design or run a narrowed variant this week.

2026-11-17. **Recommendation: NO-GO for a live shadow test of the combined first-hint/second-hide proposal before Saturday.** The exposure and cost screens pass, but the prewritten no-useful-call-suppression safety bar fails. The earlier replay already found two supported counterexamples, and the wider recount finds more possible suppressions. A shadow test does not itself hide calls, but it cannot cure this known defect in the proposed action. A separately specified hint-only experiment could be considered later; it is not established by this analysis and is not an approved alteration.

The [protocol](2026-11-17-stall-opportunity-protocol.md) was written and SHA-256 hashed **before this recount**: `447898aedc8d96571d96132b6e7334184953ceab5a9487f5e9df785ec35487fd`. Source proposal: the local purported full Project doc is a copy note; its available [overnight summary](</mnt/c/Users/user/Documents/ROSA-Claude-Context/Claude outputs/2026-11-16_PROMPT_CLAUDECODE_overnight.md>) states that first stalls get a ledger hint and the second stall on the same tool hides it for one request. The supplied task definition determines the trigger. [Script](2026-11-17-stall-recount.py), [per-episode data](2026-11-17-stall-episodes.jsonl), [machine-readable aggregates](2026-11-17-stall-summary.json).

## Results, full development episode denominators

| Source | Episodes | Episodes ≥1 stall | Stall calls | Supported episodes with ≥1 stall | Stall calls in supported episodes | Requests / tokens after first stall | Requests / tokens after second stall | Actual max-iteration endings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Pilot, all valid arms | 576 | 102 | 752 | 46 | 134 | 1,245 / 8,336,110 | 905 / 6,377,685 | 14 |
| Round 1, all arms | 320 | 35 | 312 | 19 | 61 | 513 / 3,807,241 | 413 / 3,352,996 | 5 |
| Round 2, both arms | 352 | 91 | 724 | 44 | 95 | 1,165 / 7,308,001 | 885 / 5,779,856 | 15 |
| **All above** | **1,248** | **228** | **1,788** | **109** | **290** | **2,923 / 19,451,352** | **2,203 / 15,510,537** | **34** |

Requests/tokens start strictly *after* the request containing the first/second stall in that episode. The two columns overlap; neither number is predicted savings. The second stall here can be on a different tool; the safety check below instead uses the second stall **on each same tool**, as the proposed hide requires. There were 152 episodes with a second overall stall. Result equality ignores arguments as specified: 1,692 calls had a repeated tool/result; 1,348 also had equal arguments. Empty/not-found criterion fired on 784 calls, overlapping repeats. All values are logged counts, not claims that later work was unnecessary. Eighteen tool calls lacked a recorded result and could not be classified (all pilot); no selected trace was unparseable and no post-trigger request lacked token usage. Counting is a lower-bound approximation when outputs are absent; changing graph values, nondeterminism and equal results for different arguments complicate interpretation.

| Model | Episodes | Episodes with stall | Stall calls | Supported episodes with stall | Requests after first | Actual cap endings |
|---|---:|---:|---:|---:|---:|---:|
| bonsai-2:4b | 312 | 111 | 1,386 | 52 | 1,977 | 33 |
| gpt-oss:20b | 312 | 27 | 40 | 18 | 120 | 0 |
| lfm3:1.7b | 312 | 67 | 314 | 24 | 669 | 0 |
| qwen3.5:9b | 312 | 23 | 48 | 15 | 157 | 1 |

**Prewritten bar:** C1-type control episodes (pilot C1, round-1 C1, round-2 CONTROL) show 66/336 = **19.6%** with stalls (bar ≥10%); 857/2,588 = **33.1%** of requests occurred after their first stall (bar ≥5%). Both are exposure, not intervention benefit. Round-2 CONTROL is enriched: seed 1–2 contributes 80 episodes, 14 with a stall and 142/508 requests after; extra seeds contribute 96, 30 with a stall and 448/1,089 requests after. Thus repeated enriched tasks and bonsai loops substantially affect pooled estimates. The third bar requires zero supported episodes where the next request uses that tool and obtains a successful, nonempty result not previously returned by that tool. The automated screen found **9 supported episodes** with such an opportunity across the whole corpus (17 useful-next events across all episodes); C1-type alone has 4 supported episodes. This is an observable suppression risk, not proof each final answer would fail if hidden: a real model could choose a different action. It is enough to fail the frozen zero bar.

**Population and exclusions.** Pilot 576 primary episodes, round 1 320, round 2 352; excluded 32 pilot infrastructure/superseded rows, eight round-1 smoke rows, four round-2 smoke rows and 60 round-2 oracle-excluded rows. These are repeated tasks/seeds/arms, not independent tasks or representative deployment frequencies. Pilot support uses the frozen v2 rescore; later logs supply their recorded v2 support. Same-tool/result compares serialized logged result; the new recount includes matching recorded handler errors and therefore is not numerically identical to the earlier [400-episode replay](../studies/offline_replay_20261116/REPORT.md), which skipped harness errors. The earlier two human-read counterexamples remain valid negative evidence.

**Cap discrepancy:** this recount identifies 15 round-2 episodes with 40 model responses and `episode_end.answer` equal to `Agent stopped due to max iterations.` For example, `research/_artifacts/runs/build_round2_20261116/full_resume2_20261116T132848Z/bonsai-2_4b-stage3/006-v2-CONTROL-bonsai-2_4b-s8/trace.jsonl`. The [round-2 report](../studies/build_round2_20261116/REPORT.md) says zero cap hits; its [`analyze_round2.py`](../studies/build_round2_20261116/analyze_round2.py) checks for `iteration limit` in `row["aborts"]`, which misses the trace termination text in these examples. The 15 is a trace-based recount, not a silent revision of the frozen original report; examine all affected outputs before amending that report. Across this corpus all 34 observed ≥40-request cases also have the explicit max-iteration end text.

## Fairness test and held-out opportunity

The fairness test was identified by the owner as running. Only its incomplete notes/smoke were available when this report was produced; **E0/E1 are pending, with no partial numbers presented**. After the owner records the complete 160-episode result, apply this frozen rule to its finalized full rows with the same exclusions and add a dated supplemental report; do not overwrite these numbers or move the bars. The existing recount script currently covers the three completed sources and does not claim to have processed fairness. Do not interrupt or inspect GPU activity to force completion.

Held-out estimate uses only the aggregate [custodian design rationale](2026-11-17-test-design-rationale.md), not protected task definitions, oracle records or held-out trajectories:

| Pool | Plausible stall situations | Confidence |
|---|---|---|
| Graph v2 (24) and original graph (16) | Breadth/dependency traversal may lead to repeat tool/results or repeated not-found results during name search, especially if a model scans candidates. | Low for actual firing: structure does not determine model calls; shared generator limits diversity. |
| Turtlesim (24) | Repeated enumeration or lookup errors are possible; most tasks have a single targeted observation stage, leaving less structural reason for a long search. | Low: no held-out model trace and the observation-stage floor does not bound exploration. |
| Stale-value (12) | Repeated reads around a scheduled change are plausible; an unchanged result can be a legitimate freshness check and a changed value is not a repeat under rule (a). | Low for frequency; high that a repeated value alone cannot establish a useless read. |

These are hypotheses about categories, not a list or count of individual tasks predicted to stall. Task-level identities are unavailable under the custodian's blinding rule; a custodian may privately evaluate the frozen detector against authorized reference descriptions, but those descriptions contain no model behavior and cannot establish firing rates.
