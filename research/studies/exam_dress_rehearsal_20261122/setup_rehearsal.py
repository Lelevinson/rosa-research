"""Create the rehearsal custody folder: dev pool (opaque ids), task index, rehearsal manifest, stand-in fixture runtime, spec. Run once; refuses to overwrite.
  uv run --no-sync python research/studies/exam_dress_rehearsal_20261122/setup_rehearsal.py
Pool entry format = the custodian's: {opaque id: {"environment": env, "task": <task dict with "request" and the scorer's fields>}}. Here the task dicts are the PUBLIC dev tasks."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
REPO = HERE.parents[2]
RUN = REPO / "research/_artifacts/runs/exam_dress_rehearsal_20261122"
CUSTODY = RUN / "custody"
BUNDLE = CUSTODY / "stage1_rehearsal"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

TASK_FILES = [("stage3", "headroom_diagnostic_20261112/stage3_tasks.json", ["u3", "p3", "h4", "v2"]),
              ("e1h", "small_model_harness_20261115/e1h_tasks.json", ["e1h_amb_1", "e1h_amb_2", "e1h_abs_1", "e1h_abs_2", "e1h_chg_1", "e1h_chg_2"]),
              ("namefix", "name_fix_applied_20261117/namefix_tasks.json", ["nf_single_1", "nf_single_2", "nf_multi_1", "nf_multi_2", "nf_amb_1", "nf_amb_2", "nf_exact", "nf_absent"])]


def main():
    if BUNDLE.exists():
        sys.exit("rehearsal custody already exists; refusing to overwrite")
    BUNDLE.mkdir(parents=True, mode=0o700)
    pool, idmap = {}, {}
    for env, path, wanted in TASK_FILES:
        tasks = {t["id"]: t for t in json.loads((STUDIES / path).read_text())}
        for dev_id in wanted:
            opaque = "h" + hashlib.sha256(("rehearsal-" + dev_id).encode()).hexdigest()[:32]
            pool[opaque] = {"environment": env, "task": tasks[dev_id]}
            idmap[opaque] = dev_id
    assert len(pool) == 18
    (BUNDLE / "pool.json").write_text(json.dumps(pool, indent=1))
    index = {k: v["environment"] for k, v in pool.items()}
    (BUNDLE / "task-index.json").write_text(json.dumps(index, indent=1))
    shutil.copy(HERE / "fixtures_dev.py", BUNDLE / "fixtures.py")
    for name in ("queue", "compact", "ros-home", "ros-logs"):
        (BUNDLE / name).mkdir(mode=0o700)
    manifest = dict(note="REHEARSAL manifest (public dev tasks); not the custodian manifest", task_count=len(pool), pool_sha256=sha(BUNDLE / "pool.json"),
                    queue_index_sha256=sha(BUNDLE / "task-index.json"),
                    scorer_sha256={"v2.0": sha(STUDIES / "residual_failures_20261115/scorer_v2.py")},
                    fixture_sha256={"stage1_read_hook": sha(STUDIES / "custodian_stage1_20261121/change_hook.py"), "runtime": sha(BUNDLE / "fixtures.py")})
    (RUN / "MANIFEST_rehearsal.json").write_text(json.dumps(manifest, indent=1))
    (HERE / "idmap.json").write_text(json.dumps(idmap, indent=1))
    frozen = json.loads((STUDIES / "final_exam_draft_20261118/freeze_package_20261121/exam_spec_stage1.json").read_text())
    tier1 = frozen["tiers"][0]
    spec = {k: frozen[k] for k in ("temperature", "models", "master_seed", "pools", "queue")}
    spec["name"] = "dress_rehearsal_stage1"
    spec["tiers"] = [dict(tier1, name="tier1_M_vs_E1", seeds=[1])]
    (HERE / "rehearsal_spec.json").write_text(json.dumps(spec, indent=1))
    print("created", BUNDLE, "tasks", len(pool), "tier", spec["tiers"][0])


main()
