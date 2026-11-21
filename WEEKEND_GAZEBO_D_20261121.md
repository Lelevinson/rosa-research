# Gazebo D (weekend 2026-11-21 to 23): research-side pointer

Branch `member/martin-gazebo` of Lelevinson/rosa-research, created from `8713f9b205033a25f8ed8d9549610e9ad0b8bfde`
(the `member/martin` tip). `member/martin` is not modified. No `rosa_auth` file and no credential is changed or added.

The study, its protocol, cases, wrapper and analysis live in **Lelevinson/rosa-evaluation**, branch
`member/martin-gazebo`:
- `artifacts/gazebo-d-20261121/D0_PROTOCOL.md` (approved 2026-11-21; approval record `D0_APPROVAL_2026-11-21.md`,
  amendment `D0_AMENDMENT_01_2026-11-21.md`), first approved at rosa-evaluation commit `34492e1`.
- Study-local wrapper `experiments/gazebo_d/runner.py`; analysis `tools/gazebo_d/analysis.py`.

## Which rosa-research code D runs

- D reuses the frozen M4 harness unchanged. M4 froze rosa-research sources at commit
  `c0c61a05c481669f201cbbb892b0bc9a3a642000` (hashes in rosa-evaluation `artifacts/macro-m4-20261027/freeze.json`).
- On 2026-11-21 every M4-frozen rosa-research file at `8713f9b` was checked byte-identical to those hashes
  (`src/rosa*`, `src/rosa_reliability/sim/*`, `uv.lock`, `pyproject.toml`). So D runs on this branch's code with
  M4's `verify()` passing. Files added after M4 (e.g. `src/rosa_backends/tool_contract_ollama.py`) are not used by D,
  except that Granite's parity adapter uses the same IBM sentence as its `NATIVE_GUIDANCE['granite3.3']` (see the
  parity branch note).
- Gazebo Harmonic, ROS 2 Jazzy, UR5e world `src/rosa_reliability/sim/arm.sdf`, run headless on the laptop.

Commit hashes of later gates are appended below at each push.

## Gate log
- 2026-11-21: branch created; D0 approved (rosa-evaluation `34492e1`), amendment 01 (rosa-evaluation `a5ea648`).
