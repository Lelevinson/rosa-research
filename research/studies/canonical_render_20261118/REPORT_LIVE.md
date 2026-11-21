# Canonical result rendering: live report (FULL vs RENDER)

2026-11-18, Asia/Taipei. Frozen protocol [PROTOCOL_LIVE.md](PROTOCOL_LIVE.md) (SHA-256 `1ca28d2bd007f460e8244f25a7f9f6c35eff2c165995550d93bc0dcb838604f2`), frozen analysis `analyze_live.py` (reading rule applied by code), renderer frozen (`FREEZE_RENDERER.json`). Run: 288 episodes (18 tasks x 4 models x seeds 1-2 x 2 arms), started 11:12, ended 14:27; 0 infrastructure-failed cells; smoke (6 episodes) not in any total. Raw: `research/_artifacts/runs/canonical_render_20261118/full_20261118T031216Z`; rows: `RESULTS_LOG_LIVE.jsonl` (294 lines = 288 + 6 smoke); numbers: `results_live.json`. Development evidence only (synthetic fixtures, 4 small models, 2 seeds), not held-out, not a method result.

## Measured (144 episodes per arm)
| | FULL | RENDER |
|---|---|---|
| supported-complete | 127 | 125 |
| model requests | 781 | 792 |
| input+output tokens | 3,715,499 | 3,235,116 |
| capped / no-answer endings | 3 | 3 |
| failed calls (any reason) | 104 | 97 |
| not-found calls naming an entity | 64 | 40 |
| slashless fires, split-only | 23 | 0 |
| slashless fires, other | 5 | 1 |

By stratum (supported / requests / tokens / not-found entity calls / split-only fires, FULL -> RENDER):
- S1 (h4, u3, v2; 24 eps): 22 -> 19; 227 -> 257; 949,714 -> 1,506,692; 27 -> 9; 7 -> 0.
- S2 (8 name-fix tasks; 64 eps): 56 -> 57; 290 -> 253; 2,076,539 -> 806,067; 23 -> 5; 16 -> 0.
- S3 (p3 + 6 e1h tasks; 56 eps): 49 -> 49; 264 -> 282; 689,246 -> 922,357; 14 -> 26; 0 -> 0.

By model (supported / requests / tokens, FULL -> RENDER): bonsai 24 -> 24, 285 -> 323, 2.21M -> 1.64M; gpt-oss 35 -> 35, 179 -> 151, 388k -> 297k; lfm3 33 -> 30, 178 -> 186, 735k -> 943k; qwen3.5 35 -> 36, 139 -> 132, 384k -> 352k. Supported difference RENDER minus FULL by model: 0, 0, -3, +1.
Paired cells: supported in both 121, FULL only 6, RENDER only 4, neither 13. Request distance from a fire to the next successful call on that name: FULL n=22, median 2; RENDER n=1.

## Frozen reading rule applied
Split-only fires in S1+S2: 23 -> 0 (-100%). Other fires in S1+S2: 5 -> 1 (-80%). The rule requires the other fires **not** to fall by 30% or more (internal control), so **mechanism signal M = not seen**. Harm flags: none (supported -2 cells; requests +1.4%; tokens -12.9%; capped +0; only one model, lfm3, at -3 cells). **Class B: "no evidence of a benefit in these cells".**

## Interpretation (labelled)
- The raw counts point one way for the targeted event: slashless not-found fires on split-only names went from 23 to 0, and not-found entity calls fell 64 -> 40. But the control the protocol set did not hold: fires on names already seen whole also fell (5 -> 1). Both counts are small, so I cannot say whether that is chance or an effect of the consistent layout; the frozen rule is not adjusted for it.
- Supported answers did not change beyond noise (127 vs 125; the detectable difference at this size is about 13 cells). Request and token totals do not show a reliable change either: the token total is dominated by a few long bonsai/lfm3 loops (S2 -61%, S1 +59%, S3 +34%, in opposite directions), and the offline estimate of the direct size cost of rendering was only +0.14%. I do not read the -12.9% tokens as a benefit.
- S3 (where no fire occurred in either arm) shows more failed and not-found calls in RENDER (46 vs 30; 26 vs 14). I have not looked at the traces for a cause; it may be noise, and it is the stratum a harm check was meant to watch.
- Status of the idea: not yet justified as a method component. Whatever the name-error effect is, it did not turn into measurable support, request or token gains here, and held-out tasks may not create split-name situations (custodian aggregate: 0 of 76 need short-name resolution).

## Limits and notes
- 18 tasks, 4 models, 2 seeds, synthetic fixtures; trajectories diverge from request 1-2, so paired cells are descriptive.
- Fires were computed on the raw results of each episode (as frozen), so RENDER fires are not hidden by the rendering.
- Known carried defect: `e1h_chg_*` hook misses node names written without a leading slash; cells stay in the denominators.
- No change to prompt, schema, renderer, scorer or scenario after the first live request.
- Step 4 (Nav2/TurtleBot3 generality check with the frozen renderer) not started; generality remains undemonstrated.
