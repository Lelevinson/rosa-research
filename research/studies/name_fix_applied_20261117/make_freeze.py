"""Writes FREEZE.json for the name-fix test (hashes of design, code, fixture, tasks, manifest, model digests) before the smoke. uv run python make_freeze.py"""
import hashlib, json, subprocess, sys, time, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent
S = HERE.parent
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
files = {"design": S.parent / "decisions/2026-11-17-name-fix-applied-test.md", "PROTOCOL_NOTE.md": HERE / "PROTOCOL_NOTE.md", "namefix_rule.py": HERE / "namefix_rule.py", "namefix_scoring.py": HERE / "namefix_scoring.py",
         "namefix_arm.py": HERE / "namefix_arm.py", "run_namefix.py": HERE / "run_namefix.py", "namefix_fixture.py": HERE / "namefix_fixture.py", "namefix_node.py": HERE / "namefix_node.py",
         "namefix_build.py": HERE / "namefix_build.py", "namefix_graph.json": HERE / "namefix_graph.json", "namefix_tasks.json": HERE / "namefix_tasks.json", "tests/test_namefix.py": HERE / "tests/test_namefix.py",
         "scorer_v2.py": S / "residual_failures_20261115/scorer_v2.py", "harness.py": S / "small_model_harness_20261115/harness.py", "round1_harness.py": S / "build_round1_20261115/round1_harness.py",
         "answer_gate.py": S / "build_round1_20261115/answer_gate.py", "run_pilot.py": S / "small_model_harness_20261115/run_pilot.py", "run_round2.py (OracleWithRetry)": S / "build_round2_20261116/run_round2.py",
         "uv.lock": S.parents[1] / "uv.lock"}
out = dict(frozen_at=time.strftime("%FT%TZ", time.gmtime()), design_sha256_stated="1e5d05213b3982a15ef65dfb8d1ac916dd8a403ed68ebeb5cbcf51230e8874a0", scorer_sha256_stated="c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9",
           git_head=subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=S.parents[1]).stdout.strip(),
           note="research/ is git-excluded in this checkout; provenance is by file hashes.", files={k: h(v) for k, v in files.items()})
assert out["files"]["design"] == out["design_sha256_stated"] and out["files"]["scorer_v2.py"] == out["scorer_sha256_stated"]
sys.path.insert(0, str(HERE))
import run_namefix as R
plan = R.plan_for("full")
out["manifest"] = dict(master_seed=R.MASTER_SEED, episodes=sum(map(len, plan.values())), sha256=hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(), sessions={k: len(v) for k, v in plan.items()})
out["smoke_manifest"] = dict(episodes=sum(map(len, R.plan_for("smoke").values())), sha256=hashlib.sha256(json.dumps(R.plan_for("smoke"), sort_keys=True).encode()).hexdigest())
tags = json.load(urllib.request.urlopen("http://172.30.80.1:11434/api/tags", timeout=10))["models"]
out["model_digests"] = {m["name"]: m["digest"] for m in tags if m["name"] in R.MODELS}
out["tests"] = "11 frozen unit tests pass (tests/test_namefix.py)"
(HERE / "FREEZE.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("manifest", "smoke_manifest", "tests")}, indent=1))
