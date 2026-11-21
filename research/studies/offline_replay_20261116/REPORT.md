# Offline replay of three proposed mechanisms (2026-11-16)

Written for: the project owner, reading Job 1 of the overnight prompt after sleeping. Offline only (no GPU, no model, no ROS, no held-out data, scorer v2.0 unchanged). Protocol and pass bars were written and hashed *before* anything was computed: [PROTOCOL.md](PROTOCOL.md) (sha256 `4056dc029318c174...`, [PROTOCOL.sha256](PROTOCOL.sha256)). Code: [episodes.py](episodes.py), [replay.py](replay.py), [aggregate.py](aggregate.py); per-episode output [results.json](results.json); tables [TABLES.md](TABLES.md).

| | |
|---|---|
| **Result** | Against the frozen bars: sweep completion, trigger after two consecutive calls **passes** (3.8% of requests, extra tokens far below saved tokens); sweep completion, trigger after one call in a small group **fails** (0.7%, extra tokens exceed saved); stall breaker **fails** (hiding a tool would remove a useful retry in 2 supported episodes); answer rewrite **passes** (0 supported answers changed or rejected; 3 unsupported answers would become supported). |
| **What it changes** | Sweep completion (two calls) and answer rewrite are worth a live test; the stall breaker's "hide the tool" step is not, because the stalls it detects are mostly the bare-name error just before the model fixes the name with the same tool. |
| **What it cannot show** | Anything about what the model does after the mechanism acts: every saving is a prediction from recorded traces. The 400 episodes are 80 cells run up to 5 times: 87% of the sweep saving sits in 5 cells (the service-provider task `v2` gives 79 of 93 saved requests), and all 3 rewritten answers are one cell (bonsai `h4` seed 1, three runs). |
| **Adoption-free?** | Yes by design: none of the three needs the model to learn a new tool or schema. Adoption is not a risk here; the open risk is that the model's later calls change after the system acts. |
| **Cost** | Sweep completion (two calls): 250 extra tool executions for 93 saved requests; estimated extra result tokens 17.6k vs 746k tokens of removed requests (sibling result sizes are estimated, see protocol). Stall breaker and answer rewrite: no extra tool executions. |

## What was replayed
400 recorded fixed-loop episodes: 80 pilot fixed-loop (arm C1), 80 round-1 control, 240 round-1 add-on arms (answer gate, list arguments, both); 343 supported (scorer v2.0), 2,430 requests, 9.62M tokens. Round-1 add-on arms are included because the proposals act on tool calls and results, which those arms share with the fixed loop; their own add-ons already changed some episodes (listed in the round-1 report). Per model rows below; the three mechanisms share an *episode ledger* (every full name seen in a successful result or the task text, its source and the read tools run on it), built by [episodes.py](episodes.py) with the same name rule as the answer gate.

Episodes 400 (supported 343); fixed-loop requests 2430, tokens 9619344

### Proposal 1, V1 (two consecutive calls)

| model | episodes | episodes with a trigger | triggers | median group size | median sweep size | requests after first trigger (sum) | predicted saved requests | % of requests | saved tokens | extra tokens | extra tool runs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all four models | 400 | 22 | 31 | 19 | 14 | 144 | 93 | 3.8 | 746353 | 17590 | 250 |
| lfm3:1.7b | 100 | 4 | 5 | 19 | 17 | 16 | 3 | 0.5 | 46811 | 4384 | 69 |
| qwen3.5:9b | 100 | 5 | 7 | 19 | 17 | 17 | 8 | 1.8 | 43706 | 5880 | 80 |
| gpt-oss:20b | 100 | 4 | 7 | 19 | 2 | 28 | 18 | 3.5 | 84240 | 3776 | 18 |
| bonsai-2:4b | 100 | 9 | 12 | 19 | 14 | 83 | 64 | 7.4 | 571596 | 3551 | 83 |

### Proposal 1, V2 (one call, group of 2 to 4 names)

| model | episodes | episodes with a trigger | triggers | median group size | median sweep size | requests after first trigger (sum) | predicted saved requests | % of requests | saved tokens | extra tokens | extra tool runs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all four models | 400 | 88 | 159 | 2 | 1 | 313 | 18 | 0.7 | 55551 | 82912 | 179 |
| lfm3:1.7b | 100 | 26 | 56 | 2 | 1 | 71 | 2 | 0.3 | 6850 | 19246 | 63 |
| qwen3.5:9b | 100 | 15 | 26 | 2 | 1 | 57 | 6 | 1.3 | 16344 | 17456 | 30 |
| gpt-oss:20b | 100 | 21 | 31 | 2 | 1 | 85 | 7 | 1.4 | 19207 | 17152 | 31 |
| bonsai-2:4b | 100 | 26 | 46 | 2 | 1 | 100 | 3 | 0.3 | 13150 | 29059 | 55 |

### Proposal 2, stall breaker

| model | episodes | stalls rule (a) | stalls (a') | stalls (b) | episodes with a stall (a or b) | supported episodes with a stall | requests after first stall | second stalls | hides that remove a useful call (all) | in supported episodes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all four models | 400 | 331 | 253 | 206 | 46 | 27 | 1103 | 36 | 5 | 2 |
| lfm3:1.7b | 100 | 57 | 24 | 47 | 9 | 4 | 362 | 14 | 4 | 1 |
| qwen3.5:9b | 100 | 3 | 3 | 0 | 3 | 3 | 15 | 0 | 0 | 0 |
| gpt-oss:20b | 100 | 14 | 10 | 5 | 10 | 6 | 53 | 1 | 1 | 1 |
| bonsai-2:4b | 100 | 257 | 216 | 154 | 24 | 14 | 673 | 21 | 0 | 0 |

### Proposal 3, answer rewrite

| model | answers | unchanged | rewritten | would reject | supported before, rewritten | supported after rewrite | unsupported -> supported | supported -> unsupported | supported answers that would be rejected | rejects with a ledger next step |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all four models | 386 | 377 | 3 | 6 | 0 | 3 | 3 | 0 | 0 | 6 of 6 |
| lfm3:1.7b | 97 | 93 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 4 of 4 |
| qwen3.5:9b | 100 | 100 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 of 0 |
| gpt-oss:20b | 96 | 96 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 of 0 |
| bonsai-2:4b | 93 | 88 | 3 | 2 | 0 | 3 | 3 | 0 | 0 | 2 of 2 |

### Concentration (the 400 episodes are 80 cells run up to 5 times each)

- p1_v1: saved requests 93 in 11 distinct cells; in supported episodes 73, in unsupported 20; top 5 cells = 81 (87%): bonsai-2:4b v2 s2=45, gpt-oss:20b v2 s2=17, bonsai-2:4b v2 s1=11, qwen3.5:9b h4 s2=4, qwen3.5:9b v2 s1=4
  by task: {'v2': 79, 'h4': 10, 'u3': 4, 'p3': 0, 'e1h_amb_2': 0, 'e1h_abs_1': 0, 'e1h_abs_2': 0, 'e1h_chg_2': 0, 'e1h_chg_1': 0, 'e1h_amb_1': 0}
- p1_v2: saved requests 18 in 8 distinct cells; in supported episodes 17, in unsupported 1; top 5 cells = 15 (83%): qwen3.5:9b e1h_amb_1 s2=6, gpt-oss:20b h4 s1=4, lfm3:1.7b e1h_amb_1 s2=2, bonsai-2:4b e1h_amb_2 s1=2, gpt-oss:20b e1h_amb_1 s1=1
  by task: {'e1h_amb_1': 10, 'h4': 6, 'e1h_amb_2': 2, 'p3': 0, 'e1h_abs_1': 0, 'e1h_abs_2': 0, 'e1h_chg_2': 0, 'e1h_chg_1': 0, 'v2': 0, 'u3': 0}
- proposal 3: rewritten episodes 3 come from 1 distinct cell(s): [('bonsai-2:4b', 'h4', 1)]; would-reject episodes come from 3 cells
- proposal 2: supported episodes where hiding removes a useful call: 2 episodes in cells [('gpt-oss:20b', 'h4', 2), ('lfm3:1.7b', 'h4', 2)]


## Reading the tables
**Proposal 1, sweep completion.**
- Two-calls trigger (V1): 31 triggers in 22 episodes; median sibling group 19 names (a node or service list), median sweep 14 names. Predicted 93 saved requests = 3.8% of all fixed-loop requests, 746k tokens of removed requests against 17.6k estimated extra tokens and 250 extra tool executions. **Meets the bar** (>= 3% and extra < saved). By model: bonsai 7.4%, gpt-oss 3.5%, qwen 1.8%, lfm3 0.5%; only two of four models clear 3% alone. Of the saved requests, 73 sit in supported and 20 in unsupported episodes. Concentration: 11 distinct cells, top 5 cells 87%, task `v2` (find the node that provides a service) 79 of 93: a one-by-one node scan that a sweep would complete in one request. Where the saving is real it is mostly on loop-prone episodes.
- One-call trigger (V2, groups of 2 to 4 names): 159 triggers in 88 episodes, median sweep 1 name, 18 saved requests (0.7%), 55.6k saved vs 82.9k extra tokens. **Fails the bar** on both parts: small groups rarely cover a later whole request, and the extra siblings cost more than they save.
- Caveat on both: saved requests assume the model stops and answers once the sweep result is in its context; a model that ignores the extra result would not save anything, and a model confused by a longer result could do worse (untested).

**Proposal 2, stall breaker.**
- 331 repeated tool+result calls under the literal rule (a) (253 when arguments must also match: (a'), because different entities can return the same text), 206 second-empty/not-found calls (b), 46 episodes with at least one stall (27 supported), 1,103 requests after the first stalls (bonsai alone 673, driven by loops), 36 second stalls.
- **Harm check fails the bar:** hiding the tool for the next request would remove a useful call in 5 of 36 second stalls, in 2 supported episodes (lfm3 `h4` seed 2 `031-h4-C1-lfm3_1.7b-s2`, gpt-oss `h4` seed 2 `008-h4-C1-gpt-oss_20b-s2`). In both the "stall" is bare names (`zephyr`, `dune`, `oasis`) failing with "Node not found", and the very next request is the same tool with the full name that works (lfm3 request 5 fails three times in one request, request 6 succeeds; gpt-oss requests 4 to 6 fail, 7 succeeds). Rule (b) counts parallel failing calls inside one request as several stalls, which is how the second stall arrives before the model can correct itself. This was applied as frozen, not patched. The first-stall ledger lookup ("did you mean /plant32/zephyr") could not be replayed and is the part that matches the real recovery pattern (hypothesis, untested).

**Proposal 3, answer rewrite.**
- 386 answers replayed; 377 unchanged, 3 rewritten, 6 would be rejected (all with "never seen" or ambiguous names; each reject has a ledger next step). **0 supported answers are rewritten or rejected, 0 supported become unsupported: meets the bar.** The 3 rewritten answers are unsupported originally (bare keys `dune`, `oasis`, `zephyr` in `gains`) and **become supported** after the rewrite; all three are the same cell (bonsai `h4` seed 1, pilot control, round-1 control, round-1 answer-gate arm). In the round-1 gate arm the model was shown "did you mean /plant32/dune" twice and did not fix the keys (hand-read 3 of the round-1 report); the rewrite would have done it for the model.
- The 6 would-reject answers come from 3 cells (service provider named `/plant32/cedar`, never seen); all were unsupported; the ledger offers listed-but-unread entities in 6 of 6 cases. Whether that next step leads the model to the right node is unknown (round-1: the gate rejected the same answer and the model kept searching until the iteration cap in one episode).
- Rewriting never invents a name; the unique-suffix condition is the one the owner specified.

## Limits and stop conditions
- Everything is predicted from traces, development tasks only, two seeds, four small models; no held-out data. Repeated cells inflate the 400 (see the concentration section of [TABLES.md](TABLES.md)).
- Group definition (a JSON list or one text section of one result) is my precise reading of "names that appear together in one earlier result", chosen in the protocol to keep name kinds consistent; the literal whole-result reading would pull in names of other kinds (topics with nodes) and was not computed.
- Sibling result sizes for names the model never queried are estimates (median size of that tool's recorded results divided by 4).
- No rule needed per-task knowledge or ground truth, so no rule was marked "not general as written". The scorer is used only to judge the rewritten answers afterwards.
- Nothing here selects a claim; passing a replay bar is a reason to test, not a result.
