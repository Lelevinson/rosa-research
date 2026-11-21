"""Stage 1 draft spec: cell counts, per-tier models, system ids resolve. No ROS, no Ollama, no custodian file (76 synthetic task ids)."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "freeze_package_20261121"))
import make_exam_spec as M  # noqa: E402
import queue_core as Q  # noqa: E402
import systems  # noqa: E402


class Stage1SpecTests(unittest.TestCase):
    def test_counts_match_the_approved_design(self):
        per_tier, total = M.counts()
        self.assertEqual(per_tier, {"tier1_M_vs_E1": 2 * 76 * 4 * 3, "tier2_S0_F_MT": 3 * 76 * 4 * 3, "tier3_ablations": 3 * 76 * 4 * 3, "tier4_extra_models": 2 * 76 * 3 * 3})
        self.assertEqual(total, 7296 + 1368)  # 8 systems x 76 x 4 x 3 core (S0, F, MT, EX-M, E1, 3 ablations), 2 systems x 76 x 3 x 3 extras

    def test_extra_models_only_in_the_last_tier_and_only_m_and_e1(self):
        spec = M.build_spec()
        spec["pools"] = {M.POOL: {"tasks": {f"t{i}": "stage3" for i in range(5)}}}
        cells = Q.build_cells(spec)
        extra = [c for c in cells if c["model"] in M.EXTRA_MODELS]
        self.assertTrue(extra)
        self.assertEqual({c["tier"] for c in extra}, {"tier4_extra_models"})
        self.assertEqual({c["system"] for c in extra}, {"EX-M", "E1"})
        self.assertFalse(any(c["model"] in M.EXTRA_MODELS for c in cells if c["tier"] != "tier4_extra_models"))

    def test_every_system_is_registered_and_has_a_runner(self):
        spec = M.build_spec()
        used = {s for t in spec["tiers"] for s in t["systems"]}
        self.assertTrue(used <= set(systems.SYSTEMS), used - set(systems.SYSTEMS))
        self.assertEqual({s for s in used if systems.SYSTEMS[s][0] is None}, set())  # F and MT have adapters since 2026-11-21

    def test_final_specs_split_f_and_keep_the_approved_cells(self):
        main, forge = M.build_final_specs()
        self.assertEqual([t["name"] for t in main["tiers"]], ["tier1_M_vs_E1", "tier2_S0_MT", "tier3_ablations", "tier4_extra_models"])
        self.assertEqual([t["systems"] for t in main["tiers"]], [["EX-M", "E1"], ["S0", "MT"], ["EX-NO_MENU", "EX-NO_FINISH", "EX-NO_ERRORTEXT"], ["EX-M", "E1"]])
        self.assertEqual([t["systems"] for t in forge["tiers"]], [["F"]])
        self.assertNotIn("F", {s for t in main["tiers"] for s in t["systems"]})
        counts = []
        for spec in (main, forge):
            spec["pools"] = {M.POOL: {"tasks": {f"t{i:02d}": "stage3" for i in range(76)}}}
            counts.append(len(Q.build_cells(spec)))
        self.assertEqual(counts, [1824 + 1824 + 2736 + 1368, 912])
        self.assertEqual(sum(counts), 8664)
        self.assertEqual(main["master_seed"], forge["master_seed"])

    def test_seeds_are_fixed_and_cell_ids_are_unique(self):
        spec = M.build_spec()
        self.assertEqual({tuple(t["seeds"]) for t in spec["tiers"]}, {(1, 2, 3)})
        spec["pools"] = {M.POOL: {"tasks": {f"t{i}": "stage3" for i in range(3)}}}
        ids = [c["id"] for c in Q.build_cells(spec)]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
