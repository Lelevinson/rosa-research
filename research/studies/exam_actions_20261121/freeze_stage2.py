"""Hash manifest of the Stage 2 code (CANDIDATE until the owner approves the Stage 2 protocol; this script does not freeze anything by itself).
  python3 freeze_stage2.py write    writes FREEZE_STAGE2_CANDIDATE.json (sha256 of every listed file + the git head)
  python3 freeze_stage2.py freeze --spec S --live-check-record R --timing-record T --approved-by NAME   the freeze step (see `freeze`)
  python3 freeze_stage2.py verify-frozen [--check-ollama]   exit 0 only if FREEZE_STAGE2.json verifies (and, with the flag, the running Ollama version and core-model digests equal the frozen ones)
  python3 freeze_stage2.py verify   exit 0 only if every file still has its recorded hash; exit 2 otherwise (prints the differences)
Listed: the judge chain (task bank, v1.1, v1.2, exam wrapper, claim counter, Stage 2 judge), the runner and its wiring, the guarded action tool and turtlesim backend, the graph check helper, the
Stage 2 protocol draft and the tests. The custodian bridge file is NOT listed here (it lives in custody); its sha256 is recorded in the run's start record by the custodian."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
REPO = HERE.parents[2]
MANIFEST = HERE / "FREEZE_STAGE2_CANDIDATE.json"
FILES = [
    "action_dev_switch_20261118/judge.py", "action_dev_switch_20261118/judge_v1_1.py", "action_dev_switch_20261118/judge_v1_2.py",
    "exam_actions_20261121/judge_exam.py", "exam_actions_20261121/claim_counter.py", "exam_actions_20261121/judge_stage2.py", "exam_actions_20261121/action_bridge.py",
    "exam_actions_20261121/action_trace.py", "exam_actions_20261121/custodian.py", "exam_actions_20261121/custodian_fixture.py", "exam_actions_20261121/action_arms.py", "exam_actions_20261121/action_systems.py", "exam_actions_20261121/run_actions.py",
    "exam_actions_20261121/run_actions_queue.py", "exam_actions_20261121/stage2_env.py", "exam_actions_20261121/stage2_spec.py", "exam_actions_20261121/timing_report.py", "stage23_plan_20261123/graph_settle.py", "action_tool_s1_20261118/action_executor.py", "action_tool_s1_20261118/action_interface.py",
    "action_tool_s2_20261118/turtlesim_backend.py", "stage2_protocol_20261124/PROTOCOL_STAGE2_DRAFT.md", "stage2_protocol_20261124/RUNBOOK_TIMING_LIVE_CHECK_FREEZE.md", "exam_actions_20261121/start_stage2.sh",
    "exam_actions_20261121/tests/test_exam_actions.py", "exam_actions_20261121/tests/test_stage2_pieces.py", "exam_actions_20261121/tests/test_real_fixture_check.py", "exam_actions_20261121/tests/test_custody_path.py", "exam_actions_20261121/tests/test_stage2_launch.py",
    "stage23_plan_20261123/tests/test_graph_settle.py",
]


# Everything else that RUNS in a Stage 2 episode or in its analysis (found with an import-closure listing on 2026-11-24, plus the lazy imports that listing misses): the arms and the Stage 1
# harness they build on, the queue and its monitor, the frozen analyzer and analysis revision 3, the lab watcher, the ROSA baseline source (src/rosa, never edited) and the dependency lock.
FILES += [
    "action_tool_s2_20261118/tests/test_turtlesim_backend.py",
    "build_round1_20261115/answer_gate.py", "exam_arms_20261121/exam_arms.py", "fairness_errors_as_text_20261117/fair_arms.py", "name_fix_applied_20261117/namefix_rule.py",
    "residual_failures_20261115/scorer_v2.py", "small_model_harness_20261115/harness.py", "small_model_harness_20261115/pilot_score.py", "small_model_harness_20261115/run_pilot.py",
    "steady_loop_ablation_20261117/ablation_arms.py", "s0_dev_20261116/run_s0.py",
    "headroom_diagnostic_20261112/run_stage1.py", "headroom_diagnostic_20261112/run_stage3.py", "headroom_diagnostic_20261112/run_stage3b.py", "headroom_diagnostic_20261112/score_stage1.py",
    "headroom_diagnostic_20261112/stage3_fixture.py", "headroom_diagnostic_20261112/vendor/baseline_audit.py", "headroom_diagnostic_20261112/vendor/menu_policy.py",
    "headroom_diagnostic_20261112/vendor/menu_run_study.py",
    "final_exam_draft_20261118/exam_queue/queue_core.py", "final_exam_draft_20261118/exam_queue/systems.py", "final_exam_draft_20261118/exam_queue/health.py",
    "final_exam_draft_20261118/exam_queue/gpu_state.py", "final_exam_draft_20261118/exam_queue/notify.py", "final_exam_draft_20261118/exam_queue/notify_exit.py",
    "final_exam_draft_20261118/exam_queue/monitor.py", "final_exam_draft_20261118/exam_queue/commit_results.py",
    "final_exam_draft_20261118/freeze_package_20261121/analyze_primary.py",
    "analysis_rev3_20261124/analysis_rev3.py", "analysis_rev3_20261124/tests/test_analysis_rev3.py",
    "stage2_analysis_20261124/analysis_stage2.py", "stage2_analysis_20261124/tests/test_analysis_stage2.py",
    "exam_actions_20261121/lab_autostop_stage1_tier1.sh", "../../pyproject.toml", "../../uv.lock",
]
FILES += sorted(str(p.relative_to(STUDIES.parent.parent / "src")).join(["../../src/", ""]) for p in (STUDIES.parent.parent / "src" / "rosa").rglob("*.py"))   # the ROSA baseline source

CUSTODY_BRIDGE = REPO / "<CUSTODY_PATH>"   # custody file: only its sha256 is recorded, never its content


def custody_bridge_digest():
    return hashlib.sha256(CUSTODY_BRIDGE.read_bytes()).hexdigest() if CUSTODY_BRIDGE.exists() else None


def digest(relative):
    return hashlib.sha256((STUDIES / relative).read_bytes()).hexdigest()


FROZEN = HERE / "FREEZE_STAGE2.json"


def untracked_files():
    """Listed files that git does not track (an ignored or new file would hash fine but could not be reproduced from the repository)."""
    tracked = set(subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True).stdout.split("\n"))
    return [f for f in FILES if os.path.relpath(STUDIES / f, REPO) not in tracked]


CORE_MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]


def ollama_state(url=None):
    """Ollama version and the digests of the four core models, read from the running server (CPU only: /api/version and /api/tags). Raises if a core model is missing."""
    import urllib.request
    url = url or os.environ.get("ROSA_OLLAMA_URL", "http://172.30.80.1:11434")
    get = lambda path: json.load(urllib.request.urlopen(url + path, timeout=15))
    digests = {m["name"]: m["digest"] for m in get("/api/tags")["models"]}
    missing = [m for m in CORE_MODELS if m not in digests]
    if missing:
        raise RuntimeError(f"core model(s) not in Ollama: {missing}")
    return dict(version=get("/api/version")["version"], digests={m: digests[m] for m in CORE_MODELS})


def problems_for(manifest):
    recorded = manifest["files"]
    problems = [f"{f}: {'missing from manifest' if f not in recorded else 'hash differs'}" for f in FILES if f not in recorded or digest(f) != recorded[f]]
    problems += [f"{f}: listed in manifest but not in FILES" for f in recorded if f not in FILES]
    if manifest.get("custody_bridge_sha256") != custody_bridge_digest():
        problems.append("custody bridge file hash differs from the manifest (or the file is absent on this machine)")
    return problems


def verify_frozen(path=None):
    """(manifest, problems) for FREEZE_STAGE2.json. Used by the launcher in exam mode."""
    path = Path(path or FROZEN)
    if not path.exists():
        return None, ["FREEZE_STAGE2.json does not exist"]
    manifest = json.loads(path.read_text())
    return manifest, problems_for(manifest)


def freeze(args):
    """The freeze step, after the live check, the timing episodes and the owner's approval of the protocol. Refuses unless every precondition holds; then writes FREEZE_STAGE2.json and verifies it.
      python3 freeze_stage2.py freeze --spec specs/exam_spec_stage2.json --live-check-record PATH --timing-record PATH --approved-by NAME [--pool-size 14] [--skip-tests]"""
    refusals = []
    for label, path in (("--live-check-record", args.live_check_record), ("--timing-record", args.timing_record), ("--spec", args.spec)):
        if not path or not Path(path).is_file() or Path(path).stat().st_size == 0:
            refusals.append(f"{label} must name an existing non-empty file")
    if not args.approved_by:
        refusals.append("--approved-by NAME (the owner's approval of the protocol) is required")
    if not CUSTODY_BRIDGE.exists():
        refusals.append("the custody bridge file is not present on this machine")
    untracked = untracked_files()
    if untracked:
        refusals.append("listed files are not tracked by git (a hash of an untracked file is not reproducible): " + ", ".join(untracked[:5]))
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *[str(STUDIES / f) for f in FILES]], cwd=REPO, capture_output=True, text=True).stdout.strip()
    if dirty:
        refusals.append("listed files have uncommitted changes (commit first, so the hashed bytes are the committed bytes):\n" + dirty)
    if not refusals:
        spec = json.loads(Path(args.spec).read_text())
        import stage2_spec
        expected = stage2_spec.exam_spec(len(spec["tiers"][0]["seeds"]))
        if {k: spec.get(k) for k in expected if not k.startswith("_")} != {k: v for k, v in expected.items() if not k.startswith("_")}:
            refusals.append("the spec is not the exam spec produced by stage2_spec.py")
    if not refusals and not args.skip_tests:
        run = subprocess.run(["uv", "run", "--with", "pytest", "python", "-m", "pytest", str(HERE / "tests"), "-q", "-p", "no:cacheprovider", "--deselect", str(HERE / "tests/test_real_fixture_check.py")],
                             cwd=REPO, capture_output=True, text=True, env=dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1"))
        if run.returncode != 0:
            refusals.append("unit tests failed:\n" + run.stdout[-800:])
    if refusals:
        print("FREEZE REFUSED:\n- " + "\n- ".join(refusals))
        return 2
    try:
        ollama = ollama_state(args.ollama_url)
    except Exception as failure:  # noqa: BLE001
        print(f"FREEZE REFUSED:\n- the Ollama version and model digests cannot be pinned ({failure!r}); pass --ollama-url or start Ollama")
        return 2
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    cells = args.pool_size * 3 * 4 * len(spec["tiers"][0]["seeds"])
    manifest = dict(status="FROZEN", frozen_at=time.strftime("%FT%T%z"), ollama=ollama, git_head=head, approved_by=args.approved_by, files={f: digest(f) for f in FILES}, custody_bridge_sha256=custody_bridge_digest(),
                    spec_sha256=hashlib.sha256(Path(args.spec).read_bytes()).hexdigest(), seeds=spec["tiers"][0]["seeds"], pool_size_assumed=args.pool_size, cells_expected=cells,
                    live_check_record_sha256=hashlib.sha256(Path(args.live_check_record).read_bytes()).hexdigest(), timing_record_sha256=hashlib.sha256(Path(args.timing_record).read_bytes()).hexdigest(),
                    bank_digest_note="the bank digest is pinned by the custodian (<CUSTODY_FILE>) and checked by the worker")
    FROZEN.write_text(json.dumps(manifest, indent=1) + "\n")
    _, problems = verify_frozen()
    print("FROZEN, verified" if not problems else "FROZEN FILE WRITTEN BUT DOES NOT VERIFY:\n" + "\n".join(problems), f"| cells expected {cells}")
    return 0 if not problems else 2


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if command == "write":
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
        MANIFEST.write_text(json.dumps(dict(status="CANDIDATE, not frozen: needs owner approval of the Stage 2 protocol", git_head_when_written=head, files={f: digest(f) for f in FILES}, custody_bridge_sha256=custody_bridge_digest(), bank_digest_note="the bank digest is pinned by the custodian (<CUSTODY_FILE>) and checked by the worker"), indent=1) + "\n")
        print(f"wrote {MANIFEST.name}: {len(FILES)} files")
        return 0
    if command == "freeze":
        import argparse
        parser = argparse.ArgumentParser(prog="freeze_stage2.py freeze")
        parser.add_argument("--spec")
        parser.add_argument("--live-check-record")
        parser.add_argument("--timing-record")
        parser.add_argument("--approved-by")
        parser.add_argument("--pool-size", type=int, default=14)
        parser.add_argument("--skip-tests", action="store_true")
        parser.add_argument("--ollama-url")
        return freeze(parser.parse_args(sys.argv[2:]))
    if command == "verify-frozen":
        manifest, problems = verify_frozen()
        if manifest and "--check-ollama" in sys.argv:
            try:
                live = ollama_state()
                if live != manifest.get("ollama"):
                    problems.append("the running Ollama version or core-model digests differ from the freeze")
            except Exception as failure:  # noqa: BLE001
                problems.append(f"Ollama could not be read for the digest check: {failure!r}")
        print("VERIFIED (frozen)" if manifest and not problems else "\n".join(problems))
        return 0 if manifest and not problems else 2
    manifest = json.loads(MANIFEST.read_text())
    problems = problems_for(manifest)
    print("VERIFIED" if not problems else "\n".join(problems))
    return 0 if not problems else 2


if __name__ == "__main__":
    sys.exit(main())
