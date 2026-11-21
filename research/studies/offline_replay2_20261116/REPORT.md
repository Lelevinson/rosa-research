# Offline replay 2: name lookup, no-progress cutoff, parallel calls (2026-11-17)

| | |
|---|---|
| **Result** | Name lookup as written (fires after a successful read with no other name in it): 484 firings in 281 of 400 episodes, **0 requests saved**, bar not met. Its optional start block predicts 280 of 2,430 requests saved (11.5%) for 71k tokens added vs 907k saved, bar met on paper only. No-progress cutoff: **no K is eligible** (supported episodes cut: 17 / 7 / 5 for K = 3 / 4 / 5). List arm: **no more parallel calls per request** (0.928 vs 0.923). |
| **What it changes** | The dead-end trigger as written fires on ordinary value reads (322 of 484 firings are `ros2_param_get`), not on dead ends, so it saves nothing. The start block is the only candidate worth a live test, and only for the part that resolves a task word into a full name. A cutoff cannot be offered at K = 3 to 5 without cutting episodes that ended supported. The list arm's -71 requests are not a parallelism effect. |
| **What it cannot show** | What a model does after any of these fires; recorded data only. Job 1 line counts are lower bounds (551 of 3,700 tool runs had no recorded output). The start block's "covered" requests assume the model skips list calls and failed bare-name calls once it has the block; this is untested. Job 3's "explains" reading is true by construction (see section 3). |
| **System acts or model must adopt** | Lookup: the system acts (appends lines to a tool result). Start block: the system adds text, the model must use it. Cutoff: the system restricts the tools. List arm: the model must adopt (and did not). |
| **Cost** | CPU only, `nice -n 19`, about 15 minutes in total; no GPU, no Ollama, no ROS; round 2's files were only read. |

Protocol (frozen and hashed before any number): [PROTOCOL.md](PROTOCOL.md), `PROTOCOL.sha256`. Scripts: `job1_lookup.py`, `job2_cutoff.py`, `job3_parallel.py` (+ `common.py`); numbers: `results_job1.json`, `results_job2.json`, `results_job3.json`. Data: the 400 recorded fixed-loop episodes (pilot C1 80, round 1 control 80, round 1 gate/list/both arms 240), parsed with `offline_replay_20261116/episodes.py`; "control-type" below means the 160 C1 episodes.

## 1. Name-keyed lookup

**Dead-end trigger (as written).** 484 firings (one per episode and entity) in 281 of 400 episodes; 192 of them in the 160 control-type episodes. By tool: `ros2_param_get` 322, `ros2_param_list` 124, `ros2_service_info` 38, `ros2_node_info` 0, `ros2_topic_info` 0. Per model: bonsai 127, lfm3 127, qwen3.5 121, gpt-oss 109.

| | all 400 | control-type 160 |
|---|---:|---:|
| firings (episodes with one) | 484 (281) | 192 |
| tool runs (cap 20 each) / not computable | 3,700 / 551 | |
| firings that found at least one line / lines added | 381 / 400 | |
| tokens added (mean per firing, counted for the remaining requests) | 12.9k (26.7) | |
| later requests fully covered by the added lines | **0** | 0 |
| predicted requests saved (share of 2,430) | **0 (0%)** | 0 |
| harm firings (look-alike named in the added lines) | **0** | 0 |

Bar (saving at least 3% of requests and tokens added below tokens saved): **not met** (0%).
- **Why zero.** Nothing is wrong with the arithmetic: no later request in the 400 episodes consists only of reads that the lookup had already run (checked with the name test removed too: 0). The trigger is mis-specified for its purpose: a successful `param_get` returns a bare value with no other name, so it counts as a "dead end" every time. The real dead ends (a not-found or empty result) are excluded by the rule "successful result" and were not tested; I did not change the rule after seeing this.
- Not computable runs are mostly bonsai (476) and gpt-oss (75): they read `topic_info`/`service_info` of entities no episode ever read, so no recorded output exists. These could only add lines, so the true saving could be higher than 0; with 0 covered requests among the 3,149 computable runs I do not expect a large change, but that is a judgement, not a measurement.
- **Overlap with sweep completion's V1 triggers (episode level):** 43 of the 484 firings are in 17 of the 22 episodes that have a V1 trigger. They address different situations (V1 needs two reads from one list).
- **Harm: 0.** Every added line names only e (the rule keeps only lines that contain e), and none of the 400 lines names a look-alike of e. No case to list.
- Per model: bonsai 127 firings / 84 lines, gpt-oss 109 / 81, lfm3 127 / 120, qwen3.5 121 / 115. The saving is 0 for every model and task, so there is no task share to report.

**Optional start block (evaluated separately; "not general as written" for the "not listed" part, see the protocol).** A block mapping task words to full names and kinds, built from the three list results of each environment, added before request 1.

| | all 400 | control-type 160 |
|---|---:|---:|
| predicted requests saved (share) | **280 (11.5%)** | 121 (12.2%) |
| predicted tokens saved / tokens added | 906,507 / 71,133 | 358,693 / 29,247 |
| largest task's share of the saving | v2, 34% | |

Per model (requests saved, share): bonsai 149 (17.2%), gpt-oss 70 (13.7%), lfm3 54 (8.9%), qwen3.5 7 (1.6%). Per task: v2 96, e1h_chg_2 67, e1h_amb_1 40, e1h_amb_2 30, e1h_abs_2 19, e1h_abs_1 14, h4 8, u3 6 (p-tasks 0). The frozen bar is met (at least 3%, tokens added below tokens saved, no task above 60%).
- **What the 280 are.** 200 of the 281 covered requests are list calls whose pattern contains a task word that the block maps (the model searching for a full name), 79 are failed calls on a bare task word the block maps or marks "not listed", 1 mixes both. So the saving is "the model need not search for the full name of a word from the task". It assumes the model takes the block instead of searching; I did not test that, and the strongest effect is on the smaller models (qwen3.5 barely uses these searches).
- **Limit:** in the e1h tasks with look-alike names the block lists two matches for one word (for example `/e1h/basalt/sorrel` and `/e1h/cobalt/sorrel`); it does not choose, so the model still has to disambiguate, and I did not compute a harm count for the start block (showing both is by design). The "not listed" lines use words that later appear as a failed bare name in the recorded episode, which is knowledge from the future, so that part is **not general as written**. Re-counted without it (checked after the first run, same data): **no covered request depended on it** (280 of 2,430 either way; the 79 failed calls are all on words the block maps), so the prediction and the bar verdict are unchanged. The start-block draft drops that part.

## 2. No-progress cutoff

Rule: after K consecutive requests that add no new name, no new first-time call result and no changed repeat result, only the finish tool is offered. Exact effect on the recorded episodes (nothing before the offer changes; the offered request is kept for the finish call; removed = recorded requests after it).

| K | episodes cut | requests removed (share of 2,430) | tokens removed (share) | **supported episodes cut** | eligible (bar 0) |
|---|---:|---:|---:|---:|---|
| 3 | 28 | 371 (15.3%) | 2,785,123 (29.0%) | **17** | no |
| 4 | 18 | 292 (12.0%) | 2,415,131 (25.1%) | **7** | no |
| 5 | 11 | 191 (7.9%) | 1,231,728 (12.8%) | **5** | no |

- Control-type episodes only: K = 3 cuts 13 (8 supported), K = 4 cuts 8 (3 supported), K = 5 cuts 3 (1 supported), removing 168 / 128 / 72 requests.
- Per model, episodes cut / supported cut: bonsai 22 / 14 (K = 3), 14 / 6 (K = 4), 10 / 4 (K = 5); lfm3 5 / 2, 4 / 1, 1 / 1; gpt-oss 1 / 1, 0, 0; qwen3.5 0 in every K. The cost is almost all bonsai (a model that loops), which also means the cuts that matter are the ones where it later still reached a supported answer.
- The five supported episodes cut at K = 5 are listed in `results_job2.json` (`K5.supported_cut_cases`): bonsai v2 and h4 (three), lfm3 v2 (one, offered at request 9, 9 requests removed). The answer after a cutoff is unknown, so these are cost effects only; the harm bound is what the bar is about. No K passes.

## 3. Parallel calls in the list arm

Native tool calls per request (calls of the response excluding `final_answer`; the final-answer request has 0, so means are below 1):

| arm | requests | calls | mean calls per request | requests with 2+ calls | distribution 0 / 1 / 2 / 3+ |
|---|---:|---:|---:|---:|---|
| control (C1) | 505 | 466 | 0.923 | 6.1% | 78 / 396 / 24 / 7 |
| list arguments (C1+LA) | 432 | 401 | 0.928 | 8.3% | 78 / 318 / 27 / 9 |
| list + gate (C1+AG+LA) | 466 | 419 | 0.899 | 6.4% | 88 / 348 / 21 / 9 |

Per model, mean calls per request control vs list arm: bonsai 0.940 vs 1.007 (+0.067), qwen3.5 0.854 vs 0.857 (+0.003), lfm3 1.034 vs 0.991 (-0.043), gpt-oss 0.835 vs 0.791 (-0.044). Counting one call per list item gives 1.099 vs 1.141.
- **Question 1, does the list arm show more parallel calls per request? No.** Frozen reading (pooled at least +0.10 and higher in 3 of 4 models): pooled +0.005, higher in 2 of 4. The share of requests with two or more calls rises slightly (6.1% to 8.3%), driven by 3 more two-call requests and 2 more with three or more; too small to call a pattern.
- **Question 2, can it explain the -71? The frozen counterfactual says "yes" (97% recovered), but the reason is not parallelism.** The list arm made 401 calls against the control's 466 (65 fewer) at the same calls per request, so it needed about 435 requests instead of 505. The difference is **fewer calls overall, not more calls per request**. The same holds without the list type: the 76 list-arm episodes with no list call used 399 requests and 367 calls against the control's 505 and 466. The four episodes with a list call used 33 requests and 34 calls. So the data agree with round 1's reading that the saving does not come from the list type and say additionally that it does not come from batching. The cause (sampling noise, or the schema change altering when the model stops) is still untested.
- Data note: this count gives 505 vs 432 requests (a difference of 73) from the parsed traces, round 1's REPORT gives -71 from its results log; I did not reconcile the two (probably episodes that stop on an error or a crashed backend are counted differently).

## Limits (all jobs)
Recorded episodes only; models, seeds and tasks are the pilot's and round 1's, two seeds per cell, and the arms with the gate or list type are included in jobs 1 and 2 as the first replay did. No novelty or significance claim; nothing here is evidence about any live behaviour. No held-out data, scorer v2.0 and round 2's files untouched.
