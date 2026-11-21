# Note for the thinking report: gpt-oss thinking levels per arm (2026-11-19, written before part A)

Owner's instruction: gpt-oss cannot turn thinking off (levels only); state the level per arm. **Wording (owner, 2026-11-19): "the level `false` maps to, not off, not recorded"**; the earlier "lowest level" wording is withdrawn. This note is the text the report must carry; it is separate from the frozen files so that no hash changes.

| arm | lfm3, qwen3.5, bonsai | gpt-oss |
|---|---|---|
| FULL | `reasoning=False` in the constructor, no per-request override: thinking **off** | `reasoning=False`: **not off**; the level to which Ollama maps `false` (not recorded in the trace; `additional_kwargs` is empty) |
| ESCALATE | FULL, but `reasoning=True` for the 2 requests after a trigger | FULL, but `reasoning="high"` for those 2 requests |
| ALWAYS (part B) | `reasoning=True` on every request | `reasoning="high"` on every request |

**Evidence and its limit.** The single probe of `think_probe.py` (n = 1 per setting): `false` 227 output tokens / 783 thinking characters, `low` 91 / 179, `medium` 297 / 1,079, `high` 725 / 3,161. In that probe `false` sat **between `low` and `medium`** (one request per setting). A multi-request probe is scheduled after part A. The saved FULL traces agree that gpt-oss thinks without being asked (a single-tool-call response cost 277 output tokens with empty content), and the smoke showed gpt-oss FULL outputs as large as its `high` outputs (FULL 501 / 256 / 210 / 142 / 259 tokens against `high` 352 / 283 / 237 / 338 on the same task). The multi-request probe (`gpt_oss_level_probe.py`) runs in the gap after part A; the report writes "the level that `think: false` maps to for gpt-oss (not off, not recorded)" and adds the probe's counts.

**What this means for the contrast.** For gpt-oss the ESCALATE-against-FULL contrast is `high` against that unspecified level on the escalated requests, a smaller change than off-against-on for the other three models; per-model rows are reported and gpt-oss is read separately. All Ollama output-token counts for gpt-oss (every arm, every earlier study) include hidden thinking; the thinking-token estimate of the protocol (output minus visible tokens) is the only handle on it.


## Probe result (2026-11-19, after part A; `gpt_oss_level_probe.py`, `gpt_oss_level_probe.json`, `.log`)
64 requests, 8 seeds per setting and prompt, dev settings (temperature 0.7, num_ctx 65536, num_predict 4096), settings interleaved seed by seed, 0 errors, 0 length cuts. Output tokens (`eval_count`, thinking included), median (min-max):
| setting | plain prompt | tool prompt (one schema) | thinking text returned | thinking characters, median (plain / tool) |
|---|---|---|---|---|
| `false` | **216** (180-281) | **53** (41-165) | 16 of 16 | 732 / 106 |
| `"low"` | 91 (86-127) | 34 (32-39) | 16 of 16 | 150 / 25 |
| `"medium"` | **214** (151-328) | **49** (41-167) | 16 of 16 | 718 / 88 |
| `"high"` | 462 (374-887) | 187 (107-482) | 16 of 16 | 1,850 / 691 |
**Reading (measured):** with `think: false`, gpt-oss produced thinking in every request, and its output tokens and thinking length are **indistinguishable from `"medium"`** (216 vs 214 and 53 vs 49 medians; ranks of `false` among the four settings by tokens per seed: third in 5 of 8 and second in 3 of 8 for the plain prompt, second in 5 and third in 3 for the tool prompt, i.e. always between `low` and `high`, never lowest) and clearly above `"low"` (about 2.4 times the tokens on the plain prompt, 1.6 times on the tool prompt). `"high"` is about twice `medium`. The raw API returns the thinking text for gpt-oss even when `false` is sent; the harness's `reasoning=False` does not store it. **Wording for every report: the level that `think: false` maps to for gpt-oss (not off, not recorded; in 64 requests its token counts matched `"medium"`, not `"low"`).** The mapping is an observation of the Ollama build used here (not verified in its source). So for gpt-oss the ESCALATE contrast (`high` on escalated requests) is `high` against a medium-like level, about twice the thinking, not off against on.
