"""Stage 1 freeze record: hashes everything the exam depends on into FREEZE.json, or verifies the record against the current files.

  uv run python research/studies/final_exam_draft_20261118/freeze_package_20261121/make_freeze.py write [OLLAMA_URL]    refuses to write if a listed file is not committed and clean
  uv run python research/studies/final_exam_draft_20261118/freeze_package_20261121/make_freeze.py verify               exit 1 and a list of mismatches if anything differs

It records the git revision, the SHA-256 of the specs, plan inputs, analysis script, custodian MANIFEST and bridge, arms, harness, runners, frozen scorer, queue code, dependency lock, the model digests
read from Ollama (they must equal MODEL_DIGESTS_DRAFT.json), the cell counts per tier, the master seed and the success criteria text. The exact cell list is NOT stored here: it is a deterministic function
of the spec, the queue code and the custodian queue index named by MANIFEST.json (its hash is in that file), and the queue writes it to the custodian run folder at run time. Nothing is read from the custodian
bundle by this script; only the tracked MANIFEST.json is hashed.
"""
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
S = "research/studies/"
FP = S + "final_exam_draft_20261118/freeze_package_20261121/"
EQ = S + "final_exam_draft_20261118/exam_queue/"
CU = S + "custodian_stage1_20261121/"
FILES = {
    "spec": [FP + "exam_spec_stage1.json", FP + "exam_spec_stage1_F.json", FP + "make_exam_spec.py", FP + "MODEL_DIGESTS_DRAFT.json", FP + "SUCCESS_AND_INVALIDATION_DRAFT.md",
             S + "final_exam_draft_20261118/PROTOCOL_DRAFT.md"],
    "analysis": [FP + "analyze_primary.py", FP + "analyze_primary.sha256", FP + "make_freeze.py", FP + "start_stage1_laptop.sh"],
    "custodian_interface": [CU + "MANIFEST.json", CU + "bridge.py", CU + "queue_bridge.py", CU + "external_runner.py", CU + "change_hook.py"],
    "arms_and_runners": [S + "exam_arms_20261121/exam_arms.py", S + "exam_arms_20261121/run_exam.py", S + "exam_arms_20261121/run_forge.py", S + "exam_arms_20261121/forge_episode.py",
                         S + "steady_loop_ablation_20261117/ablation_arms.py", S + "fairness_errors_as_text_20261117/fair_arms.py", S + "fairness_errors_as_text_20261117/run_fair.py",
                         S + "name_fix_applied_20261117/namefix_rule.py", S + "build_round1_20261115/answer_gate.py", S + "build_round2_20261116/run_round2.py",
                         S + "thinking_escalation_20261119/run_think.py", S + "forge_baseline_20261115/run_full.py"],
    "harness": [S + "small_model_harness_20261115/harness.py", S + "small_model_harness_20261115/run_pilot.py", S + "headroom_diagnostic_20261112/run_stage1.py",
                S + "headroom_diagnostic_20261112/vendor/menu_run_study.py"],
    "scorer": [S + "residual_failures_20261115/scorer_v2.py"],
    "queue": [EQ + n for n in ("queue_core.py", "systems.py", "health.py", "gpu_state.py", "monitor.py", "notify.py", "commit_results.py", "exam_tables.py", "monitor_stage1.py")],
    "dependencies": ["uv.lock", "pyproject.toml"],
}
SCORER_V2_SHA256 = "c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9"  # frozen since 2026-11-15
FORGE_PYTHON = Path.home() / ".local/share/rosa-exam/forge-env/bin/python"
TIERS_EXPECTED = {"exam_spec_stage1.json": {"tier1_M_vs_E1": 1824, "tier2_S0_MT": 1824, "tier3_ablations": 2736, "tier4_extra_models": 1368}, "exam_spec_stage1_F.json": {"tier2b_F": 912}}
MASTER_SEED = 20261122


def sha(path):
    return hashlib.sha256((REPO / path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def listed():
    return [path for group in FILES.values() for path in group]


def dirty_files():
    """Listed files that are untracked, modified or staged-but-uncommitted."""
    status = git("status", "--porcelain", "--", *listed())
    return [line for line in status.splitlines() if line.strip()]


def model_digests(url):
    tags = json.load(urllib.request.urlopen(url.rstrip("/") + "/api/tags", timeout=15))
    have = {m["name"]: m["digest"] for m in tags["models"]}
    wanted = json.loads((REPO / FP / "MODEL_DIGESTS_DRAFT.json").read_text())["digests"]
    missing = [m for m in wanted if m not in have]
    if missing:
        raise SystemExit(f"models missing from Ollama: {missing}")
    changed = {m: (wanted[m][:12], have[m][:12]) for m in wanted if have[m] != wanted[m]}
    if changed:
        raise SystemExit(f"model digests differ from MODEL_DIGESTS_DRAFT.json: {changed}")
    version = json.load(urllib.request.urlopen(url.rstrip("/") + "/api/version", timeout=15))["version"]
    return {m: have[m] for m in wanted}, version


def forge_environment():
    if not FORGE_PYTHON.exists():
        raise SystemExit(f"Forge interpreter missing: {FORGE_PYTHON}")
    freeze = subprocess.check_output(["uv", "pip", "freeze", "--python", str(FORGE_PYTHON)], text=True)
    return dict(python=str(FORGE_PYTHON), pip_freeze_sha256=hashlib.sha256(freeze.encode()).hexdigest(), forge_guardrails="forge-guardrails==0.10.1" in freeze)


def write(url):
    if dirty_files():
        raise SystemExit("refusing to freeze: listed files not committed/clean:\n" + "\n".join(dirty_files()))
    for path in listed():
        if not (REPO / path).exists():
            raise SystemExit(f"listed file missing: {path}")
    if sha(S + "residual_failures_20261115/scorer_v2.py") != SCORER_V2_SHA256:
        raise SystemExit("scorer v2.0 hash differs from the frozen value")
    for name, tiers in TIERS_EXPECTED.items():
        spec = json.loads((REPO / FP / name).read_text())
        if spec["master_seed"] != MASTER_SEED or {t["name"] for t in spec["tiers"]} != set(tiers):
            raise SystemExit(f"{name}: master seed or tiers differ from the approved design")
    digests, version = model_digests(url)
    record = dict(
        frozen_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds"),
        stage="Stage 1 (held-out v2 question tasks)", status="FROZEN: laptop queue started under this record",
        git_head=git("rev-parse", "HEAD"), git_branch=git("rev-parse", "--abbrev-ref", "HEAD"),
        master_seed=MASTER_SEED, seeds_per_cell=[1, 2, 3], temperature=0.7,
        cells_per_tier=TIERS_EXPECTED, cells_total_main=sum(TIERS_EXPECTED["exam_spec_stage1.json"].values()), cells_total_F=912,
        tier_order=["tier1_M_vs_E1", "tier2_S0_MT", "tier3_ablations", "tier4_extra_models", "(F: exam_spec_stage1_F.json, refused until a held-out F adapter exists)"],
        primary_criteria="supported(M) - supported(E1): lower 95% bound above -5 points AND token ratio M/E1: upper 95% bound below 0.80 (task-clustered bootstrap, held-out v2, 4 core models, 3 seeds); text in SUCCESS_AND_INVALIDATION_DRAFT.md",
        laptop_rule="the laptop runs the full Stage 1 queue to completion regardless of the lab (owner, 2026-11-21 15:41); the laptop is its own stratum and is never pooled with the lab",
        lab_rule="lab stratum: pre-run gate on Monday (container restart with --init and integrity check, transient-failure check, Forge env copy); no protocol change",
        plan_derivation="cell list = queue_core.build_cells(spec) over the custodian queue index named in MANIFEST.json (queue_index_sha256); written by the queue to the custodian run folder; not stored here",
        sha256={path: sha(path) for path in listed()},
        scorer_v2_sha256=SCORER_V2_SHA256, model_digests=digests, ollama_version=version, forge_environment=forge_environment(),
    )
    (HERE / "FREEZE.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print("FREEZE.json written; git head", record["git_head"], "; sha256 of FREEZE.json:", hashlib.sha256((HERE / "FREEZE.json").read_bytes()).hexdigest())


def verify(url=None):
    record = json.loads((HERE / "FREEZE.json").read_text())
    problems = [f"{path}: hash differs or file missing" for path, digest in record["sha256"].items() if not (REPO / path).exists() or sha(path) != digest]
    if sha(S + "residual_failures_20261115/scorer_v2.py") != record["scorer_v2_sha256"]:
        problems.append("scorer v2.0 differs")
    if url:
        try:
            digests, _ = model_digests(url)
            problems += [f"model {m} digest differs" for m in record["model_digests"] if digests.get(m) != record["model_digests"][m]]
        except SystemExit as error:
            problems.append(str(error))
    print("VERIFIED: all frozen files and digests match" if not problems else "\n".join(problems))
    return 0 if not problems else 1


if __name__ == "__main__":
    url = sys.argv[2] if len(sys.argv) > 2 else "http://172.30.80.1:11434"
    command = sys.argv[1] if len(sys.argv) > 1 else "verify"
    sys.exit(write(url) or 0 if command == "write" else verify(url))
