"""Synthetic tests of analysis_stage2 (no custody data, no ROS, no model). Run from the repository root:
  PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --with pytest python -m pytest research/studies/stage2_analysis_20261124/tests -q -p no:cacheprovider"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import analysis_stage2 as S  # noqa: E402

R, Q = S.R, S.Q
SALT = "s2-test-salt"
MODELS = ["m1", "m2"]
SPEC = {"name": "synthetic_stage2", "master_seed": 3, "temperature": 0.7, "models": MODELS, "pools": {"p": {"tasks": {f"t{i}": "turtlesim" for i in range(1, 5)}}},
        "tiers": [{"name": "stage2", "systems": ["XM", "XE1", "XS0"], "pools": ["p"], "seeds": [1]}]}
OPAQUE = R.opaque_factory(SALT)
A = R.load_analyzer()


def plan_of(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(SPEC))
    return Q.my_cells(Q.build_cells(Q.load_spec(path)), "lab", Q.parse_machines("lab:1")), path


def rows_for(cell, supported, ending, claim=None):
    tokens = 50 if cell["system"] == "XM" else 100
    override = ending if ending in ("unscored", "unresolved_motion") else None
    full = dict(cell_id=cell["id"], tier=cell["tier"], system=cell["system"], model=cell["model"], supported_complete=supported, llm_requests=3, input_tokens=tokens, output_tokens=tokens,
                aborts=[], answer="in_custody", ending_override=override, exposure=dict(claim_audit=claim))
    compact = dict(cell=OPAQUE(cell["id"]), pair=OPAQUE(cell["pair"]), task=OPAQUE(cell["pool"] + cell["task"]), pool=cell["pool"], tier=cell["tier"], system=cell["system"], model=cell["model"],
                   seed=cell["seed"], machine="lab", supported=supported, ending=ending, requests=3, input_tokens=tokens, output_tokens=tokens, wall_seconds=1.0)
    return full, compact


def snapshot(tmp_path, outcome=lambda cell: (cell["system"] != "XS0", None), skipped=(), ledger=()):
    plan, _ = plan_of(tmp_path)
    full_rows, compact = [], []
    for cell in plan:
        if cell["id"] in skipped:
            continue
        supported, ending_override = outcome(cell)
        ending = ending_override or ("supported" if supported else "unsupported")
        claim = dict(applicable=True, claimed_arrival=True, arrived=supported, claimed_but_not_arrived=not supported) if ending not in ("unscored",) else None
        f, c = rows_for(cell, supported and ending == "supported", ending, claim)
        full_rows.append(f)
        compact.append(c)
    return dict(plan=plan, machine="lab", salt=SALT, spec_sha256="x", full_ids=[r["cell_id"] for r in full_rows], full_rows=full_rows, compact=compact, ledger=list(ledger),
                quarantined_cells=set(skipped), quarantined_groups=set(), accepted_duplicates=set(), adjudicated=set(), prestart_ids=None, input_sha256={})


def report(snap, outcomes=True):
    return S.stage2_report(snap, "stage2", A, MODELS, 100, 1, outcomes)


def test_three_comparisons_with_sensitivity_only_when_m_is_primary(tmp_path):
    out = report(snapshot(tmp_path))
    assert out["status"] == "analysed" and set(out["comparisons"]) == {"XM_vs_XE1", "XM_vs_XS0", "XE1_vs_XS0"}
    primary = out["comparisons"]["XM_vs_XE1"]["results"]
    assert primary["primary_denominator"] == 8 and primary["primary"]["primary_comparison"]["difference_points"] == pytest.approx(0.0)
    assert "sensitivity" in primary and "sensitivity" in out["comparisons"]["XM_vs_XS0"]["results"]
    assert "sensitivity" not in out["comparisons"]["XE1_vs_XS0"]["results"]
    assert out["comparisons"]["XM_vs_XS0"]["results"]["primary"]["primary_comparison"]["difference_points"] == pytest.approx(100.0)


def test_unscored_is_counted_as_failure_and_excluded_in_the_secondary(tmp_path):
    victim = {}
    def outcome(cell):
        if cell["system"] == "XM" and cell["model"] == "m1" and cell["task"] == "t1" and not victim:
            victim["id"] = cell["id"]
            return False, "unscored"
        return cell["system"] != "XS0", None
    out = report(snapshot(tmp_path, outcome))
    block = out["comparisons"]["XM_vs_XE1"]
    primary = block["results"]["primary"]["primary_comparison"]
    assert primary["pairs"] == 8 and primary["supported_primary"] == 7 and primary["supported_baseline"] == 8          # counted as failure
    secondary = block["without_unscored_pairs_secondary"]
    assert secondary["pairs_removed"] == 1 and secondary["analysis"]["primary_comparison"]["pairs"] == 7
    assert out["validity"]["per_system"]["XM"]["class_c_unscored"] == 1 and out["validity"]["per_system"]["XM"]["stop_for_owner"] is True       # 1 of 8 cells = 12.5% > 3%
    assert out["validity"]["per_system"]["XE1"]["stop_for_owner"] is False


def test_validity_thresholds_and_compromise(tmp_path):
    out = report(snapshot(tmp_path, lambda cell: (False, "unscored") if cell["task"] == "t1" else (True, None)))        # 2 of 8 cells per system unscored (25%)
    assert all(v["flagged"] and v["stop_for_owner"] for v in out["validity"]["per_system"].values()) and out["validity"]["compromised"] is True
    clean = report(snapshot(tmp_path))
    assert not clean["validity"]["compromised"] and not any(v["flagged"] for v in clean["validity"]["per_system"].values())


def test_new_ending_classes_appear_in_the_table(tmp_path):
    out = report(snapshot(tmp_path, lambda cell: (False, "unresolved_motion") if cell["system"] == "XS0" and cell["model"] == "m2" else (True, None)))
    endings = {(r["system"], r["model"], r["ending"]): r["cells"] for r in out["ending_classes"]}
    assert endings[("XS0", "m2", "unresolved_motion")] == 4 and endings[("XM", "m1", "supported")] == 4


def test_claim_counter_2x2_per_system_and_model(tmp_path):
    out = report(snapshot(tmp_path, lambda cell: (cell["system"] != "XS0", None)))
    table = {(r["system"], r["model"]): r for r in out["claim_counter"]}
    assert table[("XS0", "m1")]["claimed__not_arrived"] == 4 and table[("XS0", "m1")]["claimed_but_not_arrived"] == 4
    assert table[("XM", "m1")]["claimed__arrived"] == 4 and table[("XM", "m1")]["claimed_but_not_arrived"] == 0


def test_quarantine_rule_is_applied_per_comparison(tmp_path):
    plan, _ = plan_of(tmp_path)
    pair = next(iter({c["pair"]: c for c in plan}.values()))
    cell = next(c for c in plan if c["pair"] == pair["pair"] and c["system"] == "XS0")
    out = report(snapshot(tmp_path, skipped={cell["id"]}))
    assert out["comparisons"]["XM_vs_XE1"]["report"]["pairs_excluded"] == 0                                      # this pair is intact for M against E1
    assert out["comparisons"]["XM_vs_XS0"]["report"]["pairs_excluded"] == 1 and out["comparisons"]["XM_vs_XS0"]["results"]["primary_denominator"] == 7
    causes = out["comparisons"]["XM_vs_XS0"]["report"]["skipped_by_system_model_cause"]
    assert causes and causes[0]["system"] == "XS0" and causes[0]["cells"] == 1


def test_integrity_problem_blocks_everything(tmp_path):
    snap = snapshot(tmp_path)
    snap["compact"][0] = dict(snap["compact"][0], machine="laptop")
    assert report(snap)["status"] == "integrity_problem"


def test_check_is_outcome_blind_and_analyze_needs_approval(tmp_path, capsys):
    plan, spec_path = plan_of(tmp_path)
    snap = snapshot(tmp_path)
    artifacts, compact = tmp_path / "art", tmp_path / "cmp"
    (artifacts / "run").mkdir(parents=True)
    (compact / "run").mkdir(parents=True)
    (artifacts / "run" / "RESULTS_LOG_lab.jsonl").write_text("".join(json.dumps(r) + "\n" for r in snap["full_rows"]))
    (compact / "run" / "compact_lab.jsonl").write_text("".join(json.dumps(r) + "\n" for r in snap["compact"]))
    common = ["--spec", str(spec_path), "--run-name", "run", "--machine", "lab", "--machines", "lab:1", "--artifacts", str(artifacts), "--compact", str(compact), "--salt", SALT, "--models", *MODELS]
    assert S.main(["check", *common]) == 0
    text = capsys.readouterr().out
    assert "difference" not in text and "token_ratio" not in text and "claim" not in text and '"supported' not in text
    assert S.main(["analyze", *common, "--out", str(tmp_path / "o")]) == 2 and not (tmp_path / "o.json").exists()
    assert S.main(["analyze", *common, "--out", str(tmp_path / "o"), "--result-look-approved", "--draws", "100"]) == 0
    saved = json.loads((tmp_path / "o.json").read_text())
    assert saved["status"] == "analysed" and saved["comparisons"]["XM_vs_XE1"]["results"]["primary_denominator"] == 8
