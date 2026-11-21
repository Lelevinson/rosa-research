# Freeze gap: files imported by M or the baselines that FREEZE.json does not hash (2026-11-21)

Recorded by Claude Code. Record only: **no re-freeze was done.** `FREEZE.json` (original sha256 `40b26b0f...`, revision 1 in `FREEZE_REV1.json`) hashes 43 files; the files below are imported at run time by the arms or runners it covers but have no entry. They must be added at the next Stage 1 re-freeze (the run is paused for teammates' ideas). SHA-256 are of the current bytes (identical in the working tree and on `origin/member/levinson` at `afa52fe`).

| Path | Why it matters | Current SHA-256 |
|---|---|---|
| `research/studies/headroom_diagnostic_20261112/run_stage3b.py` | A1 PROMPT: `prompt_messages_a1()` and the `NEUTRAL` line replacing 3 discovery messages | `79002d21d120fae41093c9e492a2b40f601487e96f5ea0fbc87f7fc91aba77b5` |
| `research/studies/headroom_diagnostic_20261112/run_stage3.py` | imported by run_stage3b (`build_model`, `TASKS`) | `ad2d18152b9fe7bea5e0d2d9203f0dffa55381ba5a550d7523da31f86a0e0211` |
| `research/studies/headroom_diagnostic_20261112/stage3_fixture.py` | imported by run_stage3b (fixture helpers) | `17026be69505643705191788d17c16869a8d7a079f64f438cca1b12bc5e857ad` |
| `research/studies/headroom_diagnostic_20261112/vendor/menu_policy.py` | imported by menu_run_study | `6265cb94c3fdf610a884c75c675a7b89dce7ad298e39dcdf2d2b6f6a8b69dd9f` |
| `research/studies/headroom_diagnostic_20261112/vendor/baseline_protocol.json` | read by run_stage1 (`BASELINE`) | `3c62da11a8ad5f9b2d0df189ba02fdfcedc5158a185833742815632cefc74b6d` |
| `research/studies/small_model_harness_20261115/pilot_score.py` | `last_json_object` used by harness final_answer parsing | `5d9de512a74b9e3ef39ab01bdce0c4724012327125c52ed53a06b95f205107da` |
| `research/studies/headroom_diagnostic_20261112/score_stage1.py` | scoring helpers imported by scorer_v2/pilot_score | `462b34cdfedcb842d668d9a43ecaccc7a23ca4746fb24aa2796ee60b636aeb5e` |
| `research/studies/headroom_diagnostic_20261112/vendor/baseline_audit.py` | imported by score_stage1/pilot_score | `7a0808afa816b85f56b0e2f8ab2d22c35e30c9c7f5926425c81ce0afef9513a9` |
| `research/studies/headroom_diagnostic_20261112/stage3_graph.json` | fixture graph, read at import by stage3_fixture | `0a2c345a60c56b96343e3bf0e6d05f3ebf5356d7c2da98a34c13ba9e57352678` |
| `research/studies/headroom_diagnostic_20261112/stage3_tasks.json` | task set, read at import (run_think.TASKS, stage3_fixture) | `b61f8be16f7211e34b821c758472d784fcfa7c4cbd9c8bc95fcc9891a7c6ec67` |
| `research/studies/small_model_harness_20261115/e1h_tasks.json` | task set, read at import by run_think | `5802e8987ce1805d5023fb58338e268eee60f92682854d2085a01a09eb230a85` |

Notes:
- The 14 M files that were missing from the public branch were untracked; the freeze hashed working-tree files, which is why it could cover them. `run_stage3b.py` holds the A1 prompt (`NEUTRAL`, `prompt_messages_a1()`) and is **not** hashed.
- `src/rosa/*` (stock ROSA prompt and tool code) is also not hashed individually; `pyproject.toml` and `uv.lock` are.
- The baseline adapters (F, MT) import further files (`forge_episode.py`, `run_forge.py` are hashed; Forge's own package is covered by `forge_environment`). I did not audit the baselines' complete import chain, only M's.
