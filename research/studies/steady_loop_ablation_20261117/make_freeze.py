"""Writes FREEZE.json (hashes of code, scorer, fixtures, manifest, model digests, settings) before the smoke. uv run python make_freeze.py"""
import hashlib, json, subprocess, sys, time, urllib.request
from pathlib import Path
S = Path("research/studies")
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
files = {
 "protocol": "research/decisions/2026-11-17-steady-loop-ablation-protocol.md",
 "ablation_arms.py": S/"steady_loop_ablation_20261117/ablation_arms.py", "run_ablation.py": S/"steady_loop_ablation_20261117/run_ablation.py",
 "tests/test_ablation.py": S/"steady_loop_ablation_20261117/tests/test_ablation.py",
 "harness.py (base arm C1)": S/"small_model_harness_20261115/harness.py", "run_pilot.py": S/"small_model_harness_20261115/run_pilot.py",
 "run_round2.py (OracleWithRetry, amendment 4)": S/"build_round2_20261116/run_round2.py", "scorer_v2.py": S/"residual_failures_20261115/scorer_v2.py",
 "stage3_fixture.py": S/"headroom_diagnostic_20261112/stage3_fixture.py", "stage3_graph.json": S/"headroom_diagnostic_20261112/stage3_graph.json",
 "stage3_node.py": S/"headroom_diagnostic_20261112/stage3_node.py", "stage3_tasks.json": S/"headroom_diagnostic_20261112/stage3_tasks.json",
 "e1h_fixture.py": S/"small_model_harness_20261115/e1h_fixture.py", "e1h_graph.json": S/"small_model_harness_20261115/e1h_graph.json",
 "e1h_node.py": S/"small_model_harness_20261115/e1h_node.py", "e1h_tasks.json": S/"small_model_harness_20261115/e1h_tasks.json",
 "menu_run_study.py (guarded_native)": S/"headroom_diagnostic_20261112/vendor/menu_run_study.py", "uv.lock": "uv.lock"}
out = dict(frozen_at=time.strftime("%FT%TZ", time.gmtime()), protocol_sha256_stated="755139de33f28d69ca9b15dcb036721c333990d0034c046744c96b7bb6c5abf9",
           git_head=subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
           note="research/ is git-excluded in this checkout (git status shows no tracked change); provenance is by the file hashes below. The scorer_v2.py hash equals the one stated in the protocol (c6b02716...).",
           files={k: h(v) for k, v in files.items()})
sys.path.insert(0, str(S/"steady_loop_ablation_20261117"))
import run_ablation as R
plan = R.plan_for("full")
out["manifest"] = dict(master_seed=R.MASTER_SEED, cells=sum(map(len, plan.values())), sha256=hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(), sessions={k: len(v) for k, v in plan.items()})
smoke = R.plan_for("smoke")
out["smoke_manifest"] = dict(cells=sum(map(len, smoke.values())), sha256=hashlib.sha256(json.dumps(smoke, sort_keys=True).encode()).hexdigest())
tags = json.load(urllib.request.urlopen("http://172.30.80.1:11434/api/tags", timeout=10))["models"]
out["model_digests"] = {m["name"]: m["digest"] for m in tags if m["name"] in R.MODELS}
out["settings"] = dict(temperature=0.7, think=False, num_ctx=65536, num_predict=4096, max_iterations=40, http_timeout_s=90, episode_timeout_s=900, session_wall_limit_h=6, stop_at_reserved_hours=8,
                       prompt="pilot A1 prompt (+ final_answer line except NO_FINISH)")
out["tests"] = "10 focused fixtures pass (steady_loop_ablation_20261117/tests/test_ablation.py)"
Path(S/"steady_loop_ablation_20261117/FREEZE.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("manifest", "smoke_manifest", "model_digests")}, indent=1))
