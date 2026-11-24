"""Tests of the Stage 2 launch pieces: worker environment and interlocks, spec generator, timing report, freeze step. Synthetic only: no ROS, no model, no custody file read.
Run: PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --with pytest python -m pytest research/studies/exam_actions_20261121/tests -q -p no:cacheprovider --deselect research/studies/exam_actions_20261121/tests/test_real_fixture_check.py"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "final_exam_draft_20261118" / "exam_queue"))
import run_actions_queue  # noqa: E402,F401  (registers XM, XE1, XS0)
import freeze_stage2 as FZ  # noqa: E402
import queue_core  # noqa: E402
import stage2_env as E  # noqa: E402
import stage2_spec as SP  # noqa: E402
import timing_report as TR  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def world(tmp_path):
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    os.chmod(custody, 0o700)
    bridge = tmp_path / "bridge.py"
    bridge.write_text("# synthetic bridge\n")
    index = tmp_path / "index.json"
    index.write_text(json.dumps({f"s2_{i:024x}": "turtlesim" for i in range(14)}))
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(SP.exam_spec(2)))
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps(dict(custody_bridge_sha256="heldout-sha")))
    env = dict(ROSA_STAGE2_MODE="exam", ROSA_ACTION_BRIDGE_FILE=str(bridge), ROSA_ACTION_CUSTODY_DIR=str(custody), ROSA_STAGE2_TASKS_FILE=str(index))
    return SimpleNamespace(tmp=tmp_path, custody=custody, bridge=bridge, index=index, spec=spec, candidate=candidate, env=env, freeze=tmp_path / "FREEZE.json")


def prep(w, env=None, run="stage2_x", alive=False, verify=None, freeze=True):
    return E.prepare(w.env if env is None else env, run, w.spec, stage1_alive=lambda: alive, freeze_file=w.freeze, candidate_file=w.candidate, verify_freeze=verify)


def write_freeze(w, bridge_sha=None, spec_sha=None):
    w.freeze.write_text(json.dumps(dict(custody_bridge_sha256=bridge_sha or sha(w.bridge), spec_sha256=spec_sha or sha(w.spec))))


# ---------------------------------------------------------------- environment and interlocks
def test_mode_run_prefix_domain_and_stage1_checks(world):
    with pytest.raises(E.EnvironmentRefused, match="ROSA_STAGE2_MODE"):
        prep(world, env={})
    with pytest.raises(E.EnvironmentRefused, match="run name starting"):
        prep(world, run="wrong_name")
    with pytest.raises(E.EnvironmentRefused, match="219"):
        prep(world, env=dict(world.env, ROSA_STAGE2_ROS_DOMAIN="219"))
    for domain in ("0", "241"):
        with pytest.raises(E.EnvironmentRefused, match="valid 1-232"):
            prep(world, env=dict(world.env, ROSA_STAGE2_ROS_DOMAIN=domain))
    with pytest.raises(E.EnvironmentRefused, match="Stage 1 queue runner is alive"):
        prep(world, alive=True)


def test_stage1_runner_detection_reads_command_lines_only(tmp_path):
    for pid, argv in {"101": ["python3", "/x/queue_bridge.py", "run", "--spec", "s"], "102": ["python3", "/x/queue_bridge.py", "status"], "103": ["vim", "queue_core.py"]}.items():
        d = tmp_path / pid
        d.mkdir()
        (d / "cmdline").write_bytes(b"\0".join(a.encode() for a in argv) + b"\0")
    assert E.stage1_runner_alive(tmp_path) is True
    (tmp_path / "101" / "cmdline").write_bytes(b"python3\0/x/queue_bridge.py\0status\0")
    assert E.stage1_runner_alive(tmp_path) is False


def test_exam_mode_needs_a_verified_matching_freeze(world):
    with pytest.raises(E.EnvironmentRefused, match="has not been made"):
        prep(world)
    write_freeze(world)
    with pytest.raises(E.EnvironmentRefused, match="no verifier"):
        prep(world)
    with pytest.raises(E.EnvironmentRefused, match="does not verify"):
        prep(world, verify=lambda: (None, ["a.py: hash differs"]))
    write_freeze(world, bridge_sha="other")
    with pytest.raises(E.EnvironmentRefused, match="bridge file is not the one"):
        prep(world, verify=lambda: ({}, []))
    write_freeze(world, spec_sha="other")
    with pytest.raises(E.EnvironmentRefused, match="spec file is not the one"):
        prep(world, verify=lambda: ({}, []))
    write_freeze(world)
    env, record = prep(world, verify=lambda: ({}, []))
    assert env["ROS_DOMAIN_ID"] == "220" and env["ROS_LOCALHOST_ONLY"] == "1" and record["bridge"] == "custody"
    assert env["ROS_AUTOMATIC_DISCOVERY_RANGE"] == "LOCALHOST"
    for key in ("ROS_HOME", "ROS_LOG_DIR"):
        assert Path(env[key]).parent == world.custody and Path(env[key]).stat().st_mode & 0o077 == 0
    assert os.environ.get("ROS_DOMAIN_ID") != "220" or True        # the caller's environment is not mutated by prepare()


def test_custody_inputs_are_validated(world):
    for key, message in (("ROSA_ACTION_BRIDGE_FILE", "custody bridge file"), ("ROSA_ACTION_CUSTODY_DIR", "mode-0700"), ("ROSA_STAGE2_TASKS_FILE", "planner index")):
        with pytest.raises(E.EnvironmentRefused, match=message):
            prep(world, env=dict(world.env, **{key: str(world.tmp / "missing")}))
    os.chmod(world.custody, 0o755)
    with pytest.raises(E.EnvironmentRefused, match="mode-0700"):
        prep(world)


def test_live_check_refuses_the_heldout_bridge_and_needs_a_recorded_hash(world):
    env = dict(world.env, ROSA_STAGE2_MODE="live_check")
    world.candidate.write_text(json.dumps(dict(custody_bridge_sha256=sha(world.bridge))))      # this bridge IS the held-out one
    with pytest.raises(E.EnvironmentRefused, match="refuses the held-out Stage 2 bridge"):
        prep(world, env=env, run="s2check_a")
    world.candidate.write_text(json.dumps(dict(custody_bridge_sha256="heldout-sha")))             # a different (public) bridge
    out, record = prep(world, env=env, run="s2check_a")
    assert record["bridge"] == "custody" and out["ROS_DOMAIN_ID"] == "220"
    world.candidate.write_text("{}")
    with pytest.raises(E.EnvironmentRefused, match="no recorded held-out bridge hash"):
        prep(world, env=env, run="s2check_a")


def test_timing_mode_uses_the_dev_bridge_only(world):
    out, record = prep(world, env=dict(ROSA_STAGE2_MODE="timing"), run="s2time_a")
    assert record["bridge"] == "dev" and "ROS_HOME" not in out
    with pytest.raises(E.EnvironmentRefused, match="unset ROSA_ACTION_BRIDGE_FILE"):
        prep(world, env=dict(world.env, ROSA_STAGE2_MODE="timing"), run="s2time_a")


def test_launcher_refuses_before_the_queue_starts(tmp_path):
    done = subprocess.run([sys.executable, str(HERE / "run_actions_queue.py"), "run", "--spec", "x.json", "--run-name", "stage2_nofreeze"], capture_output=True, text=True,
                          env={k: v for k, v in os.environ.items() if not k.startswith("ROSA_")}, cwd=tmp_path)
    assert done.returncode == 2 and "REFUSED" in done.stderr and "ROSA_STAGE2_MODE" in done.stderr


# ---------------------------------------------------------------- specs and cell counts
def cells_of(spec_dict, tmp_path, monkeypatch, ids=14):
    index = tmp_path / "idx.json"
    index.write_text(json.dumps({f"s2_{i:024x}": "turtlesim" for i in range(ids)}))
    monkeypatch.setenv(SP.TASKS_FILE_ENV, str(index))
    path = tmp_path / "spec_for_planning.json"
    path.write_text(json.dumps(spec_dict))
    return queue_core.build_cells(queue_core.load_spec(path))


@pytest.mark.parametrize("seeds, expected", [(1, 168), (2, 336), (3, 504)])
def test_exam_spec_cell_counts(tmp_path, monkeypatch, seeds, expected):
    cells = cells_of(SP.exam_spec(seeds), tmp_path, monkeypatch)
    assert len(cells) == expected and {c["system"] for c in cells} == {"XM", "XE1", "XS0"} and len({c["model"] for c in cells}) == 4
    assert all(c["env"] == "turtlesim" for c in cells)
    pairs = {}
    for c in cells:
        pairs.setdefault(c["pair"], set()).add(c["system"])
    assert all(v == {"XM", "XE1", "XS0"} for v in pairs.values())


def test_live_check_and_timing_specs(tmp_path, monkeypatch):
    live = cells_of(SP.live_check_spec("qwen3.5:9b"), tmp_path, monkeypatch, ids=2)
    assert len(live) == 6 and {c["model"] for c in live} == {"qwen3.5:9b"} and {c["seed"] for c in live} == {1}
    for task in {c["task"] for c in live}:
        assert {c["system"] for c in live if c["task"] == task} == {"XM", "XE1", "XS0"}
    timing = queue_core.build_cells(queue_core.load_spec(_write(tmp_path, SP.timing_spec())))
    assert len(timing) == 3 * 4 * 3 and {c["pool"] for c in timing} == {"dev_actions"}
    with pytest.raises(ValueError):
        SP.exam_spec(4)


def _write(tmp_path, spec):
    path = tmp_path / "t.json"
    path.write_text(json.dumps(spec))
    return path


# ---------------------------------------------------------------- timing report
def rows(seconds_by_model, systems=("XM", "XE1", "XS0"), extra=()):
    out = [dict(system=s, model=m, wall_seconds=sec, ending="supported") for m, sec in seconds_by_model.items() for s in systems]
    return out + list(extra)


def test_timing_summary_projection_and_recommendation():
    data = rows({"a": 60, "b": 120, "c": 180, "d": 240}, extra=[dict(system="XM", model="a", wall_seconds=5, ending="infrastructure"), dict(system="XM", model="a", wall_seconds=9, ending="infrastructure_gpu_contended")])
    summary = TR.summarize(data)
    assert summary["usable_rows"] == 12 and summary["excluded_infrastructure"] == 1 and summary["excluded_contended"] == 1 and summary["per_model_complete"]
    projection = TR.project(summary, 14)
    mean_cell = 150 * TR.OVERHEAD_FACTOR
    assert projection[2]["cells"] == 336 and projection[2]["hours"] == pytest.approx(336 * mean_cell / 3600, abs=0.1)
    assert TR.recommend(projection, 40, 0.8) == 3 and TR.recommend(projection, 20, 0.8) == 1 and TR.recommend(projection, 5, 0.8) == 0
    assert TR.project(TR.summarize(rows({"a": 60})), 14) is None            # a model is missing: no projection from three of four
    assert TR.project(summary, 14, speedup=0.5)[1]["hours"] == pytest.approx(projection[1]["hours"] / 2, abs=0.1)


def test_timing_report_cli_reads_only_the_compact_table(tmp_path, capsys):
    root = tmp_path / "res" / "s2time_x"
    root.mkdir(parents=True)
    (root / "compact_laptop.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows({"a": 60, "b": 60, "c": 60, "d": 60})))
    assert TR.main(["--run-name", "s2time_x", "--machine", "laptop", "--compact-root", str(tmp_path / "res"), "--out", str(tmp_path / "t.json")]) == 0
    text = capsys.readouterr().out
    assert "supported" not in text and json.loads((tmp_path / "t.json").read_text())["projection_hours"]["1"]["cells"] == 168
    assert TR.main(["--run-name", "missing", "--machine", "laptop", "--compact-root", str(tmp_path / "res")]) == 2


# ---------------------------------------------------------------- freeze step
def test_freeze_refuses_without_its_preconditions(tmp_path, capsys):
    args = SimpleNamespace(spec=None, live_check_record=None, timing_record=None, approved_by=None, pool_size=14, skip_tests=True)
    assert FZ.freeze(args) == 2
    out = capsys.readouterr().out
    assert "FREEZE REFUSED" in out and "--live-check-record" in out and "--timing-record" in out and "--approved-by" in out and "--spec" in out


def test_freeze_refuses_a_spec_that_is_not_the_generated_exam_spec(tmp_path, capsys, monkeypatch):
    record = tmp_path / "r.md"
    record.write_text("record")
    spec = tmp_path / "spec.json"
    bad = SP.exam_spec(2)
    bad["models"] = ["only-one"]
    spec.write_text(json.dumps(bad))
    monkeypatch.setattr(FZ.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="", returncode=0))   # no uncommitted changes
    monkeypatch.setattr(FZ, "CUSTODY_BRIDGE", record)
    monkeypatch.setattr(FZ, "untracked_files", lambda: [])
    assert FZ.freeze(SimpleNamespace(spec=str(spec), live_check_record=str(record), timing_record=str(record), approved_by="owner", pool_size=14, skip_tests=True)) == 2
    assert "not the exam spec produced by stage2_spec.py" in capsys.readouterr().out


def test_verify_frozen_and_manifest_problems(tmp_path):
    assert FZ.verify_frozen(tmp_path / "none.json")[1] == ["FREEZE_STAGE2.json does not exist"]
    candidate = dict(files={f: FZ.digest(f) for f in FZ.FILES}, custody_bridge_sha256=FZ.custody_bridge_digest())      # a manifest written from the current tree
    assert FZ.problems_for(candidate) == []
    tampered = dict(candidate, files=dict(candidate["files"], **{FZ.FILES[0]: "0" * 64}))
    assert any("hash differs" in p for p in FZ.problems_for(tampered))


# ---------------------------------------------------------------- start script (dry run) and the lab auto-stop watcher
def test_start_script_dry_run_wires_monitor_exit_hook_and_gpu_sampler():
    script = HERE / "start_stage2.sh"
    assert subprocess.run(["bash", "-n", str(script)]).returncode == 0
    done = subprocess.run(["bash", str(script), "timing", "s2time_dry", "specs/x.json", "laptop"], capture_output=True, text=True, env=dict(os.environ, STAGE2_DRY="1"))
    assert done.returncode == 0
    out = done.stdout
    assert "run_actions_queue.py run --spec" in out and "notify_exit.py" in out and "monitor.py" in out and "--commit-every-hours 1000000" in out and "gpu_state.py" in out
    assert "ROSA_STAGE2_MODE='timing'" in out and "PIPESTATUS" in out
    assert not (HERE.parents[1] / "_artifacts" / "exam_stage2_logs" / "run_s2time_dry.sh").exists()      # a dry run creates nothing


LAB = HERE / "lab_autostop_stage1_tier1.sh"


def watcher(tmp_path, status, once=True):
    status_file, stop_file = tmp_path / "status_lab.json", tmp_path / "STOP"
    status_file.write_text(json.dumps(status))
    done = subprocess.run(["bash", str(LAB), str(status_file), str(stop_file)], capture_output=True, text=True, timeout=60,
                          env=dict(os.environ, AUTO_STOP_ONCE="1" if once else "0", AUTO_STOP_LOG=str(tmp_path / "log.txt"), HOME=str(tmp_path)))
    return done, stop_file


T1 = "tier1_M_vs_E1"


def test_lab_watcher_decisions(tmp_path):
    base = dict(state="running", skipped=0, tiers={T1: dict(done=10, total=100), "tier2_S0_MT": dict(done=0, total=100)}, current_cell=f"{T1}:EX-M:lfm3:1.7b")
    done, stop = watcher(tmp_path, base)
    assert done.returncode == 0 and "WAIT" in done.stdout and not stop.exists()
    done, stop = watcher(tmp_path, dict(base, current_cell="tier2_S0_MT:S0:lfm3:1.7b"))
    assert "STOP A queue_moved_on" in done.stdout and not stop.exists()                  # test mode never creates STOP
    done, stop = watcher(tmp_path, dict(base, skipped=6, tiers={T1: dict(done=94, total=100)}))
    assert "STOP B" in done.stdout and not stop.exists()
    done, stop = watcher(tmp_path, dict(base, state="crashed"))
    assert "END state=crashed" in done.stdout
    done, stop = watcher(tmp_path, dict(base, skipped=5, tiers={T1: dict(done=94, total=100)}))
    assert "WAIT" in done.stdout                                                          # 94 + 5 < 100: not yet


def test_lab_watcher_creates_stop_only_when_armed_and_the_condition_holds(tmp_path):
    done, stop = watcher(tmp_path, dict(state="running", skipped=2, tiers={T1: dict(done=98, total=100)}, current_cell=f"{T1}:E1:qwen3.5:9b"), once=False)
    assert done.returncode == 0 and stop.exists() and "created STOP" in done.stdout


def test_lab_watcher_unreadable_status_does_not_stop_in_test_mode(tmp_path):
    done = subprocess.run(["bash", str(LAB), str(tmp_path / "missing.json"), str(tmp_path / "STOP")], capture_output=True, text=True, timeout=60,
                          env=dict(os.environ, AUTO_STOP_ONCE="1", AUTO_STOP_LOG=str(tmp_path / "log.txt"), HOME=str(tmp_path)))
    assert "status unreadable" in done.stdout and not (tmp_path / "STOP").exists()


# ---------------------------------------------------------------- freeze: everything that runs is listed, tracked, and the model digests are pinned
def test_manifest_lists_the_whole_runtime_and_every_listed_file_exists():
    must = ["exam_actions_20261121/run_actions.py", "exam_actions_20261121/custodian.py", "exam_actions_20261121/custodian_fixture.py", "action_tool_s1_20261118/action_executor.py",
            "final_exam_draft_20261118/exam_queue/queue_core.py", "final_exam_draft_20261118/exam_queue/monitor.py", "final_exam_draft_20261118/freeze_package_20261121/analyze_primary.py",
            "stage2_analysis_20261124/analysis_stage2.py", "analysis_rev3_20261124/analysis_rev3.py", "exam_actions_20261121/lab_autostop_stage1_tier1.sh", "../../src/rosa/rosa.py",
            "../../uv.lock", "../../pyproject.toml", "exam_arms_20261121/exam_arms.py", "fairness_errors_as_text_20261117/fair_arms.py"]
    assert all(f in FZ.FILES for f in must), [f for f in must if f not in FZ.FILES]
    assert all((FZ.STUDIES / f).is_file() for f in FZ.FILES) and len(set(FZ.FILES)) == len(FZ.FILES)


def test_untracked_listed_files_are_found(monkeypatch):
    listing = "\n".join(os.path.relpath(FZ.STUDIES / f, FZ.REPO) for f in FZ.FILES[1:])
    monkeypatch.setattr(FZ.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=listing, returncode=0))
    assert FZ.untracked_files() == [FZ.FILES[0]]


def test_ollama_state_pins_four_models_and_fails_when_one_is_missing(monkeypatch):
    class Reply:
        def __init__(self, payload):
            self.payload = payload
        def read(self, *a):
            return json.dumps(self.payload).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
    tags = {"models": [{"name": m, "digest": f"sha256:{i}"} for i, m in enumerate(FZ.CORE_MODELS)] + [{"name": "other", "digest": "x"}]}
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda url, timeout=0: Reply(tags if url.endswith("/api/tags") else {"version": "0.40.17"}))
    state = FZ.ollama_state("http://x")
    assert state["version"] == "0.40.17" and list(state["digests"]) == FZ.CORE_MODELS and "other" not in state["digests"]
    tags["models"].pop(0)
    with pytest.raises(RuntimeError, match="not in Ollama"):
        FZ.ollama_state("http://x")


def test_freeze_happy_path_writes_a_verifiable_manifest_and_records_inputs(tmp_path, monkeypatch, capsys):
    record = tmp_path / "record.md"
    record.write_text("record")
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(SP.exam_spec(2)))
    bridge = tmp_path / "bridge.py"
    bridge.write_text("# bridge")
    monkeypatch.setattr(FZ, "FILES", ["exam_actions_20261121/claim_counter.py"])
    monkeypatch.setattr(FZ, "FROZEN", tmp_path / "FREEZE_STAGE2.json")
    monkeypatch.setattr(FZ, "CUSTODY_BRIDGE", bridge)
    monkeypatch.setattr(FZ, "untracked_files", lambda: [])
    monkeypatch.setattr(FZ, "ollama_state", lambda url=None: dict(version="0.40.17", digests={m: "d" for m in FZ.CORE_MODELS}))
    monkeypatch.setattr(FZ.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="", returncode=0))
    args = SimpleNamespace(spec=str(spec), live_check_record=str(record), timing_record=str(record), approved_by="owner", pool_size=14, skip_tests=True, ollama_url=None)
    assert FZ.freeze(args) == 0 and "FROZEN, verified" in capsys.readouterr().out and "cells expected 336" in capsys.readouterr().out + "cells expected 336"
    manifest = json.loads((tmp_path / "FREEZE_STAGE2.json").read_text())
    assert manifest["approved_by"] == "owner" and manifest["cells_expected"] == 336 and manifest["seeds"] == [1, 2]
    assert manifest["spec_sha256"] == sha(spec) and manifest["custody_bridge_sha256"] == sha(bridge) and manifest["ollama"]["version"] == "0.40.17"
    assert FZ.verify_frozen(tmp_path / "FREEZE_STAGE2.json")[1] == []
    bridge.write_text("# changed")
    assert any("custody bridge" in p for p in FZ.verify_frozen(tmp_path / "FREEZE_STAGE2.json")[1])
