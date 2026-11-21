"""Tests of the frozen primary-comparison analysis: synthetic cases with known answers, and the PUBLIC DEVELOPMENT results (steady-loop ablation FULL arm against fairness E1, seed 1, 40 paired cells).
No held-out data, no ROS, no model. From the repository root:
  uv run python -m unittest discover -s research/studies/final_exam_draft_20261118/freeze_package_20261121/tests -v"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import analyze_primary as A  # noqa: E402

STUDIES = HERE.parents[2]
MODELS = A.CORE_MODELS


def make_rows(tasks, seeds, primary, baseline, supported_primary, supported_baseline, tokens_primary, tokens_baseline, machine=None, extra=None):
    """Rows of two systems over tasks x 4 models x seeds. The supported/token arguments are functions (task index, model, seed) -> value."""
    rows = []
    for t in range(tasks):
        for m in MODELS:
            for s in seeds:
                for system, sup, tok in ((primary, supported_primary, tokens_primary), (baseline, supported_baseline, tokens_baseline)):
                    row = dict(system=system, task=f"t{t:02d}", model=m, seed=s, pool="p", supported=bool(sup(t, m, s)), input_tokens=tok(t, m, s), output_tokens=0, ending="supported" if sup(t, m, s) else "unsupported")
                    row["_system"] = system
                    if machine:
                        row["machine"] = machine
                    if extra:
                        row.update(extra(system, t, m, s))
                    rows.append(row)
    return rows


def run(rows, primary="EX-M", baseline="E1", planned=0, draws=400, seed=7, models=None):
    return A.analyse(rows, primary, baseline, models or MODELS, draws, seed, planned)


class VerdictRuleTests(unittest.TestCase):
    def stat(self, lower, upper_ratio):
        return dict(difference_interval=(lower, 9.0), ratio_interval=(0.1, upper_ratio))

    def test_both_criteria_are_strict(self):
        self.assertTrue(A.verdict(self.stat(-4.99, 0.79))[0].startswith("PASS"))
        self.assertIn("(a)", A.verdict(self.stat(-5.0, 0.5))[0])        # lower bound must be ABOVE -5, equality fails
        self.assertIn("(b)", A.verdict(self.stat(0.0, 0.80))[0])        # upper bound must be BELOW 0.80, equality fails
        text = A.verdict(self.stat(-6.0, 0.9))[0]
        self.assertTrue(text.startswith("FAIL") and "(a)" in text and "(b)" in text)

    def test_not_evaluable_without_intervals(self):
        self.assertTrue(A.verdict(dict(difference_interval=None, ratio_interval=None))[0].startswith("NOT EVALUABLE"))


class SyntheticTests(unittest.TestCase):
    def test_equal_correctness_and_half_the_tokens_passes(self):
        rows = make_rows(30, [1, 2, 3], "EX-M", "E1", lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 500, lambda t, m, s: 1000)
        result = run(rows)["primary_comparison"]
        self.assertEqual(result["pairs"], 30 * 4 * 3)
        self.assertEqual(result["difference_points"], 0.0)
        self.assertAlmostEqual(result["token_ratio"], 0.5)
        self.assertEqual(result["difference_interval"], (0.0, 0.0))
        self.assertTrue(result["verdict"].startswith("PASS"))

    def test_known_difference_and_ratio_and_correctness_failure(self):
        lose = lambda t, m, s: 0 if t % 5 == 0 else 1  # M loses every fifth task: 20 of 100 cells
        rows = make_rows(20, [1, 2, 3, 4, 5], "EX-M", "E1", lose, lambda t, m, s: 1, lambda t, m, s: 800, lambda t, m, s: 1000)
        result = run(rows)["primary_comparison"]
        self.assertEqual(result["pairs"], 20 * 4 * 5)
        self.assertAlmostEqual(result["difference_points"], -20.0)
        self.assertAlmostEqual(result["token_ratio"], 0.8)
        self.assertIn("(a)", result["verdict"])
        self.assertIn("(b)", result["verdict"])  # ratio 0.8 with an interval around it cannot have its upper bound below 0.80 here

    def test_the_bootstrap_resamples_tasks_not_cells(self):
        # one task is always lost by M, the others never: an interval over tasks is wide, a cell-level interval would be much narrower
        rows = make_rows(10, [1, 2, 3], "EX-M", "E1", lambda t, m, s: 0 if t == 0 else 1, lambda t, m, s: 1, lambda t, m, s: 10, lambda t, m, s: 10)
        result = run(rows, draws=2000)["primary_comparison"]
        low, high = result["difference_interval"]
        self.assertAlmostEqual(result["difference_points"], -10.0)
        self.assertEqual(high, 0.0)          # a resample without the lost task
        self.assertLessEqual(low, -20.0)     # a resample with the lost task twice or more

    def test_extra_models_are_not_in_the_primary_and_unpaired_cells_are_counted(self):
        rows = make_rows(5, [1], "EX-M", "E1", lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 2)
        rows += [dict(r, model="llama3.1:8b") for r in rows[:2]]                      # an extra model: ignored
        rows.append(dict(rows[0], model="qwen3.5:9b", task="only_m", _system="EX-M", system="EX-M"))  # a cell with only the primary
        result = run(rows)
        self.assertEqual(result["primary_comparison"]["pairs"], 5 * 4)
        self.assertEqual(result["unpaired_cells"], 1)

    def test_status_is_interim_until_the_planned_pairs_are_reached(self):
        rows = make_rows(3, [1], "EX-M", "E1", lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 2)
        self.assertTrue(run(rows, planned=912)["status"].startswith("INTERIM"))
        self.assertEqual(run(rows, planned=12)["status"], "FINAL")

    def test_per_model_rows_and_capped_sensitivity(self):
        rows = make_rows(6, [1, 2], "EX-M", "E1", lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 10, lambda t, m, s: 20)
        rows[0]["ending"] = "iteration_cap"
        result = run(rows)
        self.assertEqual(set(result["per_model_secondary"]), set(MODELS))
        self.assertEqual(result["per_model_secondary"]["qwen3.5:9b"]["pairs"], 12)
        self.assertEqual(result["without_capped_secondary"]["removed_pairs"], 1)

    def test_determinism_and_seed_dependence(self):
        rows = make_rows(12, [1, 2], "EX-M", "E1", lambda t, m, s: (t + s) % 3 != 0, lambda t, m, s: (t + m.__len__()) % 4 != 0, lambda t, m, s: 100 + t, lambda t, m, s: 150 + 7 * s)
        first, again, other = run(rows, seed=1), run(rows, seed=1), run(rows, seed=2)
        self.assertEqual(first["primary_comparison"], again["primary_comparison"])
        self.assertNotEqual(first["primary_comparison"]["difference_interval"], other["primary_comparison"]["difference_interval"])

    def test_duplicate_cells_and_pooled_strata_are_refused(self):
        rows = make_rows(2, [1], "EX-M", "E1", lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 1)
        with self.assertRaises(SystemExit):
            run(rows + [dict(rows[0])])
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.jsonl", Path(tmp) / "b.jsonl"
            a.write_text(json.dumps(dict(rows[0], machine="laptop")) + "\n")
            b.write_text(json.dumps(dict(rows[1], machine="lab")) + "\n")
            with self.assertRaises(SystemExit):
                A.load_rows([a, b], "system", None)
            self.assertEqual(len(A.load_rows([a, b], "system", "lab")), 1)

    def test_infrastructure_flags_and_compromised_exam_withholds_the_verdict(self):
        rows = make_rows(10, [1, 2], "EX-M", "E1", lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 2)
        for r in rows[:30]:                                    # 30 of 160 rows = 18.75% infrastructure
            r["ending"] = "infrastructure"
        result = run(rows)
        self.assertTrue(result["invalidation"]["compromised"])
        self.assertTrue(result["primary_comparison"]["verdict"].startswith("WITHHELD"))
        light = make_rows(10, [1, 2], "EX-M", "E1", lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 2)
        for r in light[:10]:                                   # 10 of 160 = 6.25%: system flagged, exam not compromised
            r["ending"] = "infrastructure"
        flagged = run(light)["invalidation"]
        self.assertFalse(flagged["compromised"])
        self.assertTrue(any(v["flagged"] for v in flagged["per_system"].values()))

    def test_name_fix_scored_both_ways(self):
        def extra(system, t, m, s):
            return dict(supported_raw=(t % 2 == 0), name_fix_changed=(t % 2 == 1)) if system == "EX-M" else {}
        rows = make_rows(10, [1], "EX-M", "E1", lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 1, extra=extra)
        nf = run(rows)["name_fix_both_ways"]
        self.assertEqual(nf["rewritten"]["supported_primary"], 40)
        self.assertEqual(nf["raw"]["supported_primary"], 20)
        self.assertEqual(nf["flips_unsupported_to_supported"], 20)
        self.assertEqual(nf["flips_supported_to_unsupported"], 0)
        self.assertEqual(nf["rewritten_answers"], 20)
        plain = make_rows(3, [1], "EX-M", "E1", lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 1)
        self.assertTrue(run(plain)["name_fix_both_ways"].startswith("not available"))

    def test_markdown_and_json_outputs_are_written(self):
        rows = make_rows(6, [1, 2], "EX-M", "E1", lambda t, m, s: 1, lambda t, m, s: 1, lambda t, m, s: 10, lambda t, m, s: 20)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "rows.jsonl"
            source.write_text("\n".join(json.dumps({k: v for k, v in r.items() if k != "_system"}) for r in rows) + "\n")
            self.assertEqual(A.main(["--rows", str(source), "--out", str(Path(tmp) / "out"), "--draws", "200"]), 0)
            payload = json.loads((Path(tmp) / "out.json").read_text())
            self.assertEqual(payload["meta"]["script_sha256"], A.sha256(A.__file__))
            self.assertIn("Verdict", (Path(tmp) / "out.md").read_text())


class PublicDevelopmentResultsTest(unittest.TestCase):
    """Real development rows: ablation FULL (the method without the name fix) against fairness E1, seed 1, phase full: the same 40 cells (10 tasks x 4 models). Recounted independently."""
    FULL = STUDIES / "steady_loop_ablation_20261117/RESULTS_LOG.jsonl"
    E1 = STUDIES / "fairness_errors_as_text_20261117/RESULTS_LOG.jsonl"

    def rows(self, path, arm):
        out = []
        for line in path.read_text().splitlines():
            r = json.loads(line)
            if r.get("arm") == arm and r.get("phase") == "full" and r.get("seed") == 1:
                out.append(r)
        return out

    def test_dev_full_against_e1_matches_an_independent_recount(self):
        if not (self.FULL.exists() and self.E1.exists()):
            self.skipTest("development logs not present")
        full, e1 = self.rows(self.FULL, "FULL"), self.rows(self.E1, "E1")
        self.assertEqual((len(full), len(e1)), (40, 40))
        for r in full + e1:
            r["pool"] = "dev"
        rows = [dict(r, _system="FULL") for r in full] + [dict(r, _system="E1") for r in e1]
        result = A.analyse(rows, "FULL", "E1", MODELS, 2000, A.DEFAULT_BOOTSTRAP_SEED, 40)
        main = result["primary_comparison"]
        self.assertEqual((main["pairs"], main["tasks"]), (40, 10))
        self.assertEqual(result["status"], "FINAL")
        sup_full, sup_e1 = sum(r["supported_complete"] for r in full), sum(r["supported_complete"] for r in e1)
        tok = lambda rs: sum(r["input_tokens"] + r["output_tokens"] for r in rs)
        self.assertEqual((main["supported_primary"], main["supported_baseline"]), (sup_full, sup_e1))
        self.assertAlmostEqual(main["difference_points"], 100 * (sup_full - sup_e1) / 40)
        self.assertAlmostEqual(main["token_ratio"], tok(full) / tok(e1))
        self.assertLess(main["difference_interval"][0], main["difference_points"] + 1e-9)
        self.assertGreater(main["difference_interval"][1], main["difference_points"] - 1e-9)
        self.assertEqual(sorted(result["per_model_secondary"]), sorted(MODELS))


if __name__ == "__main__":
    unittest.main()
