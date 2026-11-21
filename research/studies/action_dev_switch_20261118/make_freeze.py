"""Writes FREEZE.json: hashes of every file that must not change after the first live request, plus model digests. Run once, before the smoke is used for the full run."""
import hashlib, json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import run_action_study as R  # noqa: E402
names = ["research/studies/action_dev_switch_20261118/" + n for n in ("PROTOCOL.md", "run_action_study.py", "judge.py", "tests/test_judge.py", "smoke_check.py", "analyze_action.py")]
names += ["research/studies/action_tool_s1_20261118/" + n for n in ("action_interface.py", "action_executor.py")]
names += ["research/studies/action_tool_s2_20261118/turtlesim_backend.py", "research/studies/action_tool_s2_20261118/tests/test_turtlesim_backend.py"]
d = R.digests()
(HERE / "FREEZE.json").write_text(json.dumps(dict(frozen_at=time.strftime("%Y-%m-%d %H:%M:%S %Z"), files={n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names},
                                                  model_digests={m: d.get(m) for m in R.MODELS}), indent=1))
print("FREEZE.json written")
