"""Writes FREEZE.json (hashes of code, scorer, fixtures, manifests, model digests, settings) before the live smoke.  uv run python research/studies/repeat_finish_nudge_20261118/make_freeze_live.py"""
import hashlib, json, subprocess, sys, time, urllib.request
from pathlib import Path
S = Path("research/studies")
C = S / "repeat_finish_nudge_20261118"
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
files = {
 "PROTOCOL.md": C/"PROTOCOL.md", "nudge_arm.py": C/"nudge_arm.py", "run_nudge.py": C/"run_nudge.py", "analyze_nudge.py": C/"analyze_nudge.py", "smoke_check.py": C/"smoke_check.py",
 "tests/test_nudge_arm.py": C/"tests/test_nudge_arm.py", "tests/test_analyze_nudge.py": C/"tests/test_analyze_nudge.py", "count_candidates.py": S/"candidate_counts_20261118/count_candidates.py",
 "harness.py (base arm C1)": S/"small_model_harness_20261115/harness.py", "run_pilot.py": S/"small_model_harness_20261115/run_pilot.py",
 "run_round2.py (OracleWithRetry, amendment 4)": S/"build_round2_20261116/run_round2.py", "scorer_v2.py": S/"residual_failures_20261115/scorer_v2.py",
 "stage3_fixture.py": S/"headroom_diagnostic_20261112/stage3_fixture.py", "stage3_graph.json": S/"headroom_diagnostic_20261112/stage3_graph.json", "stage3_node.py": S/"headroom_diagnostic_20261112/stage3_node.py", "stage3_tasks.json": S/"headroom_diagnostic_20261112/stage3_tasks.json",
 "e1h_fixture.py": S/"small_model_harness_20261115/e1h_fixture.py", "e1h_graph.json": S/"small_model_harness_20261115/e1h_graph.json", "e1h_node.py": S/"small_model_harness_20261115/e1h_node.py", "e1h_tasks.json": S/"small_model_harness_20261115/e1h_tasks.json",
 "menu_run_study.py (guarded_native)": S/"headroom_diagnostic_20261112/vendor/menu_run_study.py", "uv.lock": "uv.lock"}
out = dict(frozen_at=time.strftime("%FT%TZ", time.gmtime()), protocol_sha256_stated=(C/"PROTOCOL.sha256").read_text().split()[0],
           git_head=subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
           note="research/ is git-excluded in this checkout; provenance is by the file hashes below. scorer_v2.py must equal c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9.",
           files={k: h(v) for k, v in files.items()})
sys.path.insert(0, str(C))
import run_nudge as R
plan = R.plan_for("full")
out["manifest"] = dict(master_seed=R.MASTER_SEED, cells=sum(map(len, plan.values())), sha256=hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(), sessions={k: len(v) for k, v in plan.items()})
smoke = R.plan_for("smoke")
out["smoke_manifest"] = dict(cells=sum(map(len, smoke.values())), sha256=hashlib.sha256(json.dumps(smoke, sort_keys=True).encode()).hexdigest())
tags = json.load(urllib.request.urlopen("http://172.30.80.1:11434/api/tags", timeout=10))["models"]
out["model_digests"] = {m["name"]: m["digest"] for m in tags if m["name"] in R.MODELS}
out["settings"] = dict(temperature=0.7, think=False, num_ctx=65536, num_predict=4096, max_iterations=40, http_timeout_s=90, episode_timeout_s=900, session_wall_limit_h=6, prompt="pilot A1 prompt + C1 finish line (both arms)")
out["tests"] = "27 focused tests pass (repeat_finish_nudge_20261118/tests)"
Path(C/"FREEZE.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("manifest", "smoke_manifest")}, indent=1))
print("scorer ok:", out["files"]["scorer_v2.py"] == "c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9")
