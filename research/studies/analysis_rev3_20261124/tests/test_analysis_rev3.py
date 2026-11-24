"""Synthetic tests of analysis_rev3 (no held-out data, no ROS, no model). Run from the repository root:
  PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --with pytest python -m pytest research/studies/analysis_rev3_20261124/tests -q -p no:cacheprovider"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "final_exam_draft_20261118" / "exam_queue"))
import analysis_rev3 as R  # noqa: E402
import queue_core as Q  # noqa: E402

SALT = "test-salt"
MODELS = ["m1", "m2"]
SPEC = {"name": "synthetic", "master_seed": 7, "temperature": 0.7, "models": MODELS,
        "pools": {"p": {"tasks": {f"t{i}": "env" for i in range(1, 5)}}},
        "tiers": [{"name": "tier1", "systems": ["EX-M", "E1"], "pools": ["p"], "seeds": [1, 2]}, {"name": "tier2", "systems": ["S0", "MT"], "pools": ["p"], "seeds": [1]}]}
OPAQUE = R.opaque_factory(SALT)
A = R.load_analyzer()


def plan_of(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(SPEC))
    return Q.my_cells(Q.build_cells(Q.load_spec(path)), "laptop", Q.parse_machines("laptop:1")), path


def compact_row(cell, supported, tokens=100):
    return dict(cell=OPAQUE(cell["id"]), pair=OPAQUE(cell["pair"]), task=OPAQUE(cell["pool"] + cell["task"]), pool=cell["pool"], tier=cell["tier"], system=cell["system"], model=cell["model"],
                seed=cell["seed"], machine="laptop", supported=supported, ending="supported" if supported else "unsupported", requests=3, input_tokens=tokens, output_tokens=tokens, wall_seconds=1.0)


def full_row(cell, supported, tokens):
    return dict(cell_id=cell["id"], supported_complete=supported, llm_requests=3, input_tokens=tokens, output_tokens=tokens, aborts=[], answer={"a": 1})


def snapshot(tmp_path, skipped=(), groups=(), pending=(), m_wins=lambda cell: True, e1_wins=lambda cell: False, ledger=(), prestart=None, only_tiers=("tier1", "tier2")):
    plan, _ = plan_of(tmp_path)
    full, compact, full_rows = [], [], []
    for cell in plan:
        if cell["id"] in skipped or cell["id"] in pending or cell["tier"] not in only_tiers:
            continue
        if f"{cell['model']}|{cell['env']}|{cell['tier']}" in groups:
            continue
        wins = m_wins(cell) if cell["system"] == "EX-M" else e1_wins(cell) if cell["system"] == "E1" else True
        full.append(cell["id"])
        tokens = 50 if cell["system"] == "EX-M" else 100
        full_rows.append(full_row(cell, wins, tokens))
        compact.append(compact_row(cell, wins, tokens=tokens))
    return dict(plan=plan, machine="laptop", salt=SALT, spec_sha256="x", full_ids=full, full_rows=full_rows, adjudicated=set(), compact=compact, ledger=list(ledger), quarantined_cells=set(skipped), quarantined_groups=set(groups),
                accepted_duplicates=set(), prestart_ids=prestart, input_sha256={})


def pair_cells(plan, tier="tier1"):
    pairs = {}
    for c in plan:
        if c["tier"] == tier:
            pairs.setdefault(c["pair"], {})[c["system"]] = c
    return pairs


def run(snap, expected=0, draws=200):
    report = R.assess(snap, "tier1", "EX-M", "E1", MODELS, expected)
    results = R.compute(snap, report, A, "EX-M", "E1", MODELS, draws, 1, Q) if report["status"] == "analysable" else None
    return report, results


def test_clean_tier_has_plan_derived_denominator_and_sensitivity_equals_primary(tmp_path):
    report, results = run(snapshot(tmp_path))
    assert report["status"] == "analysable" and report["planned_pairs"] == 16 and report["pairs_excluded"] == 0
    primary, sensitivity = results["all"]["primary"]["primary_comparison"], results["all"]["sensitivity"]
    assert primary["pairs"] == 16 and results["all"]["primary"]["status"] == "FINAL"
    assert primary["difference_points"] == pytest.approx(100.0) == pytest.approx(sensitivity["difference_points"])
    assert primary["token_ratio"] == pytest.approx(0.5)


def test_skipped_m_cell_pair_is_excluded_and_sensitivity_is_worst_case(tmp_path):
    plan, _ = plan_of(tmp_path)
    pairs = pair_cells(plan)
    pair = next(iter(pairs.values()))
    snap = snapshot(tmp_path, skipped={pair["EX-M"]["id"]}, m_wins=lambda c: True, e1_wins=lambda c: False)
    report, results = run(snap)
    assert report["pairs_excluded"] == 1 and report["primary_denominator"] == 15
    assert results["all"]["primary"]["status"] == "FINAL" and results["all"]["primary"]["primary_comparison"]["pairs"] == 15
    s = results["all"]["sensitivity"]
    assert s["pairs"] == 16 and s["supported_primary"] == 15 and s["supported_baseline"] == 0        # the skipped M cell counts as failure


def test_skipped_baseline_cell_counts_as_success_in_sensitivity(tmp_path):
    plan, _ = plan_of(tmp_path)
    pair = next(iter(pair_cells(plan).values()))
    report, results = run(snapshot(tmp_path, skipped={pair["E1"]["id"]}))
    s = results["all"]["sensitivity"]
    assert report["pairs_excluded"] == 1 and s["supported_primary"] == 16 and s["supported_baseline"] == 1   # the observed M success is kept


def test_both_cells_skipped_counts_one_pair_and_m_fails_e1_succeeds(tmp_path):
    plan, _ = plan_of(tmp_path)
    pair = next(iter(pair_cells(plan).values()))
    report, results = run(snapshot(tmp_path, skipped={pair["EX-M"]["id"], pair["E1"]["id"]}))
    s = results["all"]["sensitivity"]
    assert report["pairs_excluded"] == 1 and report["primary_denominator"] == 15
    assert s["supported_primary"] == 15 and s["supported_baseline"] == 1


def test_block_group_quarantine_is_skipped_and_reported_with_its_cause(tmp_path):
    report, results = run(snapshot(tmp_path, groups={"m2|env|tier1"}))
    assert report["status"] == "analysable" and report["pairs_excluded"] == 8 and report["primary_denominator"] == 8
    assert {r["cause"] for r in report["skipped_by_system_model_cause"]} == {"block_group_quarantine"}
    assert {(r["system"], r["model"], r["cells"]) for r in report["skipped_by_system_model_cause"]} == {("EX-M", "m2", 8), ("E1", "m2", 8)}


def test_skipped_cells_reported_per_system_model_cause(tmp_path):
    plan, _ = plan_of(tmp_path)
    cells = [next(iter(v.values())) for v in list(pair_cells(plan).values())[:2]]
    ids = [c["id"] for c in cells]
    ledger = [dict(event="interrupted", cell_id=ids[0], requests_seen=2), dict(event="failed_after_requests", cell_id=ids[0], requests_seen=1), dict(event="quarantined", cell_id=ids[0], reason="x"),
              dict(event="quarantined", cell_id=ids[1], reason="failure count reached the quarantine limit")]
    report, _ = run(snapshot(tmp_path, skipped=set(ids), ledger=ledger))
    causes = {r["cause"] for r in report["skipped_by_system_model_cause"]}
    assert causes == {"two_attempts_reached_model(failed_after_requests+interrupted)", "failure_count_limit"}
    assert sum(r["cells"] for r in report["skipped_by_system_model_cause"]) == 2


def test_cross_tier_orphan_blocks_every_tier(tmp_path):
    snap = snapshot(tmp_path)
    orphan = next(c for c in snap["plan"] if c["tier"] == "tier2")
    snap["full_ids"].remove(orphan["id"])                          # a PLANNED tier-2 cell whose full row is missing, compact row present
    report = R.assess(snap, "tier1", "EX-M", "E1", MODELS, 0)
    assert report["status"] == "integrity_problem" and any("without a full row" in p for p in report["problems"])


def test_full_row_without_compact_and_field_mismatch_and_repeats(tmp_path):
    snap = snapshot(tmp_path)
    snap["compact"].pop()
    assert any("without a compact row" in p for p in R.validate(snap))
    snap = snapshot(tmp_path)
    snap["compact"][0] = dict(snap["compact"][0], pair="deadbeef0000")
    assert any("disagree with the plan" in p for p in R.validate(snap))
    snap = snapshot(tmp_path)
    snap["compact"].append(snap["compact"][3])
    assert any("repeated" in p for p in R.validate(snap))
    snap = snapshot(tmp_path)
    snap["full_ids"].append("p|ghost|EX-M|m1|1")
    assert any("outside the plan" in p for p in R.validate(snap))


def test_pending_cell_blocks_the_look_and_a_missing_pair_does_not_shrink_the_denominator(tmp_path):
    plan, _ = plan_of(tmp_path)
    pair = next(iter(pair_cells(plan).values()))
    report = R.assess(snapshot(tmp_path, pending={pair["EX-M"]["id"], pair["E1"]["id"]}), "tier1", "EX-M", "E1", MODELS, 0)
    assert report["status"] == "not_analysable_pending_cells" and report["planned_pairs"] == 16


def test_prestart_cohort_is_never_skipped_silently(tmp_path):
    plan, _ = plan_of(tmp_path)
    pair = next(iter(pair_cells(plan).values()))
    ids = [pair["EX-M"]["id"], pair["E1"]["id"]]
    with pytest.raises(R.IntegrityError, match="missing"):
        R.assess(snapshot(tmp_path), "tier1", "EX-M", "E1", MODELS, 2)
    with pytest.raises(R.IntegrityError, match="expected 2"):
        R.assess(snapshot(tmp_path, prestart=ids[:1]), "tier1", "EX-M", "E1", MODELS, 2)
    with pytest.raises(R.IntegrityError, match="not planned, finished"):
        R.assess(snapshot(tmp_path, prestart=["p|ghost|EX-M|m1|1", ids[1]]), "tier1", "EX-M", "E1", MODELS, 2)
    with pytest.raises(R.IntegrityError, match="is 0"):
        R.assess(snapshot(tmp_path, prestart=ids), "tier1", "EX-M", "E1", MODELS, 0)
    report, results = run(snapshot(tmp_path, prestart=ids), expected=2)
    assert set(results) == {"all", "without_prestart"} and report["prestart_pairs"] == 1
    assert results["all"]["primary"]["primary_comparison"]["pairs"] == 16 and results["without_prestart"]["primary"]["primary_comparison"]["pairs"] == 15
    assert results["without_prestart"]["primary_denominator"] == 15


def test_prestart_pair_that_is_also_skipped_is_not_double_counted(tmp_path):
    plan, _ = plan_of(tmp_path)
    pair = next(iter(pair_cells(plan).values()))
    ids = [pair["EX-M"]["id"], pair["E1"]["id"]]
    snap = snapshot(tmp_path, prestart=ids)
    other = list(pair_cells(plan).values())[1]
    snap2 = snapshot(tmp_path, prestart=ids, skipped={other["E1"]["id"]})
    _, results = run(snap2, expected=2)
    assert results["all"]["primary_denominator"] == 15 and results["without_prestart"]["primary_denominator"] == 14 and snap is not None


def test_machines_are_never_pooled_and_files_are_read_once(tmp_path):
    with pytest.raises(R.IntegrityError, match="never pooled"):
        R.load_snapshot(Q, tmp_path / "spec.json", "run", "all", "all:1")
    plan, spec_path = plan_of(tmp_path)
    artifacts, compact = tmp_path / "art", tmp_path / "cmp"
    (artifacts / "run").mkdir(parents=True)
    (compact / "run").mkdir(parents=True)
    snap = snapshot(tmp_path)
    (artifacts / "run" / "RESULTS_LOG_laptop.jsonl").write_text("".join(json.dumps(r) + "\n" for r in snap["full_rows"]))
    (compact / "run" / "compact_laptop.jsonl").write_text("".join(json.dumps(r) + "\n" for r in snap["compact"]))
    loaded = R.load_snapshot(Q, spec_path, "run", "laptop", "laptop:1", artifacts, compact, SALT)
    assert R.validate(loaded) == [] and set(loaded["input_sha256"]) == {"full", "compact"} and loaded["quarantined_cells"] == set()
    (compact / "run" / "compact_laptop.jsonl").write_text('{"cell": "a"}\n{torn')
    with pytest.raises(R.IntegrityError, match="not valid JSON"):
        R.load_snapshot(Q, spec_path, "run", "laptop", "laptop:1", artifacts, compact, SALT)


def test_check_output_has_no_outcome_fields_and_analyze_needs_the_approval_flag(tmp_path, capsys):
    plan, spec_path = plan_of(tmp_path)
    artifacts, compact = tmp_path / "art", tmp_path / "cmp"
    (artifacts / "run").mkdir(parents=True)
    (compact / "run").mkdir(parents=True)
    snap = snapshot(tmp_path)
    (artifacts / "run" / "RESULTS_LOG_laptop.jsonl").write_text("".join(json.dumps(r) + "\n" for r in snap["full_rows"]))
    (compact / "run" / "compact_laptop.jsonl").write_text("".join(json.dumps(r) + "\n" for r in snap["compact"]))
    common = ["--spec", str(spec_path), "--run-name", "run", "--machine", "laptop", "--machines", "laptop:1", "--tier", "tier1", "--primary", "EX-M", "--baseline", "E1", "--prestart-expected", "0",
              "--artifacts", str(artifacts), "--compact", str(compact), "--salt", SALT, "--models", *MODELS]
    assert R.main(["check", *common]) == 0
    text = capsys.readouterr().out
    assert "supported" not in text and "difference" not in text and "token" not in text
    assert R.main(["analyze", *common, "--out", str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out.json").exists()
    assert R.main(["analyze", *common, "--out", str(tmp_path / "out"), "--result-look-approved", "--draws", "100"]) == 0
    saved = json.loads((tmp_path / "out.json").read_text())
    assert saved["results"]["all"]["primary_denominator"] == 16 and saved["report"]["input_sha256"].keys() == {"full", "compact"}


# ---- the four synthetic checks of the Codex pre-look review (CODEX_PRELOOK_REVIEW.md, 2026-11-24): each one passed the candidate gate and must now block
def test_codex_1a_compact_task_identity_mismatch_blocks(tmp_path):
    snap = snapshot(tmp_path)
    snap["compact"][2] = dict(snap["compact"][2], task="0123456789ab")
    report = R.assess(snap, "tier1", "EX-M", "E1", MODELS, 0)
    assert report["status"] == "integrity_problem" and any("disagree with the plan" in p for p in report["problems"])


def test_codex_1b_compact_machine_mismatch_blocks(tmp_path):
    snap = snapshot(tmp_path)
    snap["compact"][2] = dict(snap["compact"][2], machine="lab")
    report = R.assess(snap, "tier1", "EX-M", "E1", MODELS, 0)
    assert report["status"] == "integrity_problem" and any("disagree with the plan" in p for p in report["problems"])


def test_codex_2_flipped_compact_supported_flag_blocks_the_comparison_but_check_stays_outcome_blind(tmp_path):
    snap = snapshot(tmp_path)
    index = next(i for i, r in enumerate(snap["compact"]) if r["system"] == "EX-M")
    snap["compact"][index] = dict(snap["compact"][index], supported=False, ending="unsupported")      # the full row still says supported
    report = R.assess(snap, "tier1", "EX-M", "E1", MODELS, 0)
    assert report["status"] == "analysable"                                                            # `check` does not compare outcomes
    with pytest.raises(R.IntegrityError, match="disagree with their accepted full row"):
        R.compute(snap, report, A, "EX-M", "E1", MODELS, 100, 1, Q)
    snap["compact"][index] = dict(snap["compact"][index], supported=True, ending="supported", input_tokens=999)   # a token field, same check
    with pytest.raises(R.IntegrityError, match="disagree"):
        R.compute(snap, R.assess(snap, "tier1", "EX-M", "E1", MODELS, 0), A, "EX-M", "E1", MODELS, 100, 1, Q)


def test_codex_3_individual_quarantine_of_a_completed_cell_blocks_until_adjudicated(tmp_path):
    snap = snapshot(tmp_path)
    victim = next(c for c in snap["plan"] if c["tier"] == "tier1" and c["system"] == "EX-M")["id"]
    snap["quarantined_cells"] = {victim}
    report = R.assess(snap, "tier1", "EX-M", "E1", MODELS, 0)
    assert report["status"] == "integrity_problem" and any("adjudicate" in p for p in report["problems"])
    snap["adjudicated"] = {victim}                                  # the owner decided the finished row stands
    report = R.assess(snap, "tier1", "EX-M", "E1", MODELS, 0)
    assert report["status"] == "analysable" and report["pairs_excluded"] == 0 and report["listed_in_quarantine_but_finished"] == [victim]


def test_finished_cells_inside_a_later_quarantined_group_are_not_a_conflict(tmp_path):
    snap = snapshot(tmp_path)
    snap["quarantined_groups"] = {"m1|env|tier1"}                   # cells already finished stay valid observations
    report = R.assess(snap, "tier1", "EX-M", "E1", MODELS, 0)
    assert report["status"] == "analysable" and report["pairs_excluded"] == 0


def test_denominator_guard_blocks_when_the_analyzer_pairs_fewer_than_the_plan(tmp_path):
    snap = snapshot(tmp_path)
    report = R.assess(snap, "tier1", "EX-M", "E1", MODELS, 0)
    class ShortAnalyzer:
        MARGIN_POINTS = A.MARGIN_POINTS
        bootstrap = staticmethod(A.bootstrap)
        @staticmethod
        def analyse(rows, *args):
            return A.analyse(rows[2:], *args)
    with pytest.raises(R.IntegrityError, match="plan gives"):
        R.compute(snap, report, ShortAnalyzer, "EX-M", "E1", MODELS, 100, 1, Q)
