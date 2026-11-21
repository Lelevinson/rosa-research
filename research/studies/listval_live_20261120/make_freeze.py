"""Writes FREEZE.json for the LISTVAL live test (hashes of protocol, plan, spec, runner, arm, fixture files, scorer, model digests, settings). Run from the repo root before the smoke:
  uv run python research/studies/listval_live_20261120/make_freeze.py"""
import hashlib, json, os, subprocess, sys, time, urllib.request
from pathlib import Path
S = Path("research/studies")
C = S / "listval_live_20261120"
T = S / "thinking_escalation_20261119"
Q = S / "final_exam_draft_20261118/exam_queue"
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
files = {"PROTOCOL.md": C/"PROTOCOL.md", "listval_arm.py": C/"listval_arm.py", "tests/test_listval_arm.py": C/"tests/test_listval_arm.py", "run_listval.py": C/"run_listval.py", "smoke_spec.json": C/"smoke_spec.json",
         "listval_spec.json": Q/"specs/listval_spec.json", "systems.py": Q/"systems.py", "queue_core.py": Q/"queue_core.py", "gpu_state.py": Q/"gpu_state.py", "health.py": Q/"health.py", "monitor.py": Q/"monitor.py",
         "think_arm.py": T/"think_arm.py", "run_think.py": T/"run_think.py", "run_lossmap.py": S/"loss_map_20261120/run_lossmap.py",
         "harness.py (arm C1)": S/"small_model_harness_20261115/harness.py", "run_pilot.py": S/"small_model_harness_20261115/run_pilot.py", "run_round2.py": S/"build_round2_20261116/run_round2.py",
         "scorer_v2.py": S/"residual_failures_20261115/scorer_v2.py", "run_stage1.py": S/"headroom_diagnostic_20261112/run_stage1.py", "menu_run_study.py": S/"headroom_diagnostic_20261112/vendor/menu_run_study.py",
         "ros2.py (rosa tools)": "src/rosa/tools/ros2.py", "namefix_rule.py": S/"name_fix_applied_20261117/namefix_rule.py",
         "stage3_fixture.py": S/"headroom_diagnostic_20261112/stage3_fixture.py", "stage3_graph.json": S/"headroom_diagnostic_20261112/stage3_graph.json", "stage3_node.py": S/"headroom_diagnostic_20261112/stage3_node.py", "stage3_tasks.json": S/"headroom_diagnostic_20261112/stage3_tasks.json",
         "e1h_fixture.py": S/"small_model_harness_20261115/e1h_fixture.py", "e1h_graph.json": S/"small_model_harness_20261115/e1h_graph.json", "e1h_node.py": S/"small_model_harness_20261115/e1h_node.py", "e1h_tasks.json": S/"small_model_harness_20261115/e1h_tasks.json",
         "namefix_fixture.py": S/"name_fix_applied_20261117/namefix_fixture.py", "namefix_graph.json": S/"name_fix_applied_20261117/namefix_graph.json", "namefix_node.py": S/"name_fix_applied_20261117/namefix_node.py", "namefix_tasks.json": S/"name_fix_applied_20261117/namefix_tasks.json",
         "uv.lock": "uv.lock"}
sys.path.insert(0, str(C))
import run_listval as R
plan = R.plan_for("listval")
digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
out = dict(frozen_at=time.strftime("%FT%TZ", time.gmtime()), label="live development test of one candidate (list results carry values)",
           protocol_sha256_stated=(C/"PROTOCOL.sha256").read_text().split()[0], git_head=subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
           git_dirty_tracked=subprocess.run(["git", "status", "--short", "-uno"], capture_output=True, text=True).stdout.strip().splitlines(),
           note="research/ is git-excluded in this checkout (new files need git add -f); provenance is by the file hashes below. scorer_v2.py must equal c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9.",
           files={k: h(v) for k, v in files.items()},
           manifest=dict(master_seed=R.MASTER_SEED, seeds=R.SEEDS, cells=sum(map(len, plan.values())), sha256=digest, sessions={k: len(v) for k, v in plan.items()}))
url = os.environ.get("ROSA_OLLAMA_URL", "http://172.30.80.1:11434")
tags = json.load(urllib.request.urlopen(url + "/api/tags", timeout=10))["models"]
out["ollama_url_class"] = "laptop default" if "ROSA_OLLAMA_URL" not in os.environ else "ROSA_OLLAMA_URL set"
out["ollama_version"] = json.load(urllib.request.urlopen(url + "/api/version", timeout=10))["version"]
out["model_digests"] = {m["name"]: m["digest"] for m in tags if m["name"] in R.T.MODELS}
out["settings"] = dict(temperature=0.7, think=False, num_ctx=65536, num_predict=4096, max_iterations=40, http_timeout_s=240, episode_timeout_s=1800, arms="FULL (switch off) / LISTVAL (switch on), cap 2000 characters")
out["commands"] = dict(smoke="bash exam_queue/start_exam_tmux.sh listval_smoke $PWD/research/studies/listval_live_20261120/smoke_spec.json all all:1",
                       measurement="bash exam_queue/start_exam_tmux.sh listval $PWD/research/studies/final_exam_draft_20261118/exam_queue/specs/listval_spec.json all all:1")
out["scorer_ok"] = out["files"]["scorer_v2.py"] == "c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9"
(C/"FREEZE.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("manifest", "model_digests", "scorer_ok", "ollama_version")}, indent=1))
assert out["scorer_ok"] and digest == json.loads((Q/"specs/listval_spec.json").read_text())["tiers"][0]["frozen_plan"]["manifest_sha256"], "spec plan hash differs from the plan"
