import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MemoryTier2DatasetTests(unittest.TestCase):
    def test_exact_scenario_count_and_unique_ids(self):
        data = json.loads((ROOT / "data" / "memory_15.json").read_text(encoding="utf-8"))
        rows = data["scenarios"]
        self.assertEqual(data["scenario_count"], 15)
        self.assertEqual(len(rows), 15)
        self.assertEqual(len({row["scenario_id"] for row in rows}), 15)

    def test_category_balance_and_three_clean_controls(self):
        data = json.loads((ROOT / "data" / "memory_15.json").read_text(encoding="utf-8"))
        counts = {}
        for row in data["scenarios"]:
            counts[row["category"]] = counts.get(row["category"], 0) + 1
        self.assertEqual(counts, data["category_counts"])
        self.assertEqual(sum(row["expected_action"] == "ACT" for row in data["scenarios"]), 3)

    def test_every_case_has_conversation_and_evidence(self):
        data = json.loads((ROOT / "data" / "memory_15.json").read_text(encoding="utf-8"))
        for row in data["scenarios"]:
            self.assertIn(row["expected_action"], {"ACT", "ESCALATE"})
            self.assertTrue(row["conversation"])
            self.assertTrue(row["evidence"])


if __name__ == "__main__":
    unittest.main()
