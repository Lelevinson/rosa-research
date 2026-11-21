# Finish-tool split: report

Run 2026-11-18 08:04-10:59 Asia/Taipei, 240 of 240 episodes, 0 zero-request (infrastructure) cells, frozen protocol [PROTOCOL.md](PROTOCOL.md) (SHA-256 `309308b6...`), analysis `analyze_split.py`, numbers in `results.json`. Development evidence only; patterns, not detections (see the power note below).

## Measured (supported-complete, scorer v2.0; per model out of 20)
| arm | all /80 | bonsai | lfm3 | qwen3.5 | gpt-oss | requests | input+output tokens | endings: finish call / text / none |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| FULL | 69 | 15 | 16 | 20 | 18 | 486 | 1,842,684 | 74 / 4 / 2 |
| TOOL_ONLY | 69 | 15 | 16 | 20 | 18 | 491 | 1,812,758 | 60 / 16 / 4 |
| LINE_JSON | 62 | 8 | 16 | 18 | 20 | 603 | 2,492,104 | 0 / 74 / 6 |

Paired against FULL (cells where only one arm is supported): TOOL_ONLY 6 vs 6 (63 both, 5 neither); LINE_JSON FULL-only 11, LINE_JSON-only 4 (58 both, 7 neither). Bonsai requests 182 / 177 / 289. Tool use in TOOL_ONLY: gpt-oss called `final_answer` in 6 of 20 episodes (12 text endings) and was still 18/20; qwen3.5 20 of 20. LINE_JSON never saw the tool (0 `tool_not_offered`).
Frozen reading rule: d_tool = FULL - TOOL_ONLY = 0, d_line = FULL - LINE_JSON = 7, **case 1: "the tool is sufficient and the prompt-only route loses cells"**.

## Interpretation (labelled)
- The whole LINE_JSON deficit is bonsai (15 -> 8 cells, +59% requests, 5 no-answer endings); lfm3 equal, qwen3.5 -2, gpt-oss +2. The case-1 label is therefore a bonsai pattern, not a four-model one.
- A gap of 7 of 80 is below the roughly 10 of 80 that the power note says can be detected, and 7 is one above the protocol's own "separated" threshold of 6; read it as a pattern. It is in the direction and size of the earlier NO_FINISH gap (-7 of 40) but that arm removed tool and line together and used other seeds.
- TOOL_ONLY equalling FULL says the finish tool does not need the prompt line to keep supported answers in these cells; it does not say the tool causes the gain, and gpt-oss shows the tool can be mostly unused with no loss.
- LINE_JSON costs +24% requests and +35% tokens against FULL, mostly bonsai.
Limits: 10 dev tasks, 4 models, 2 seeds, one run; trajectories diverge from request 1-2; no Codex audit of differing answers was run.

## Limit noted 2026-11-19 (the text above is left unchanged)
`LINE_JSON` differs from `FULL` and `TOOL_ONLY` in two bundled ways: the structured ending (no `final_answer` tool; the episode ends on the first response without a tool call) **and** the invalid-answer retry (`FULL` and `TOOL_ONLY` keep the harness's one retry for an invalid `final_answer`; `LINE_JSON` has none, see PROTOCOL.md row `LINE_JSON`: "no retry"). The measured gap (supported 69 / 69 / 62, the net gap all bonsai) therefore cannot be assigned to the structured ending alone or to the missing retry alone. See `../final_exam_draft_20261118/PROTOCOL_DRAFT.md` section 7 flag (vi).
