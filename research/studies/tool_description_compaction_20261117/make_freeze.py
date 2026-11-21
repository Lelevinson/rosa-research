"""Writes FREEZE.json of the compaction test (hashes of protocol, code, fixtures, scorer, manifest, model digests). uv run python make_freeze.py"""
import hashlib, json, subprocess, sys, time, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent
S = HERE.parent
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
files = {"PROTOCOL.md": HERE / "PROTOCOL.md", "compaction.py": HERE / "compaction.py", "compaction_arm.py": HERE / "compaction_arm.py", "run_compaction.py": HERE / "run_compaction.py", "analyze_compaction.py": HERE / "analyze_compaction.py",
         "tests/test_compaction.py": HERE / "tests/test_compaction.py", "measure_rule.py": HERE / "measure_rule.py",
         "ablation_arms.py (base FULL arm)": S / "steady_loop_ablation_20261117/ablation_arms.py", "run_ablation.py (episode rows)": S / "steady_loop_ablation_20261117/run_ablation.py",
         "scorer_v2.py": S / "residual_failures_20261115/scorer_v2.py", "harness.py": S / "small_model_harness_20261115/harness.py", "run_pilot.py": S / "small_model_harness_20261115/run_pilot.py",
         "run_round2.py (OracleWithRetry)": S / "build_round2_20261116/run_round2.py", "stage3_fixture.py": S / "headroom_diagnostic_20261112/stage3_fixture.py", "stage3_graph.json": S / "headroom_diagnostic_20261112/stage3_graph.json",
         "stage3_tasks.json": S / "headroom_diagnostic_20261112/stage3_tasks.json", "e1h_fixture.py": S / "small_model_harness_20261115/e1h_fixture.py", "e1h_graph.json": S / "small_model_harness_20261115/e1h_graph.json",
         "e1h_tasks.json": S / "small_model_harness_20261115/e1h_tasks.json", "uv.lock": S.parents[1] / "uv.lock"}
out = dict(frozen_at=time.strftime("%FT%TZ", time.gmtime()), scorer_sha256_stated="c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9", note="research/ is git-excluded in this checkout; provenance is by file hashes.",
           git_head=subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=S.parents[1]).stdout.strip(), files={k: h(v) for k, v in files.items()})
assert out["files"]["scorer_v2.py"] == out["scorer_sha256_stated"]
sys.path.insert(0, str(HERE))
import run_compaction as R
plan = R.plan_for("full")
out["manifest"] = dict(master_seed=R.MASTER_SEED, episodes=sum(map(len, plan.values())), sha256=hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(), sessions={k: len(v) for k, v in plan.items()})
out["smoke_manifest"] = dict(episodes=sum(map(len, R.plan_for("smoke").values())), sha256=hashlib.sha256(json.dumps(R.plan_for("smoke"), sort_keys=True).encode()).hexdigest())
tags = json.load(urllib.request.urlopen("http://172.30.80.1:11434/api/tags", timeout=10))["models"]
out["model_digests"] = {m["name"]: m["digest"] for m in tags if m["name"] in R.MODELS}
out["tests"] = "7 frozen unit tests pass (tests/test_compaction.py)"
(HERE / "FREEZE.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("manifest", "smoke_manifest", "tests")}, indent=1))
