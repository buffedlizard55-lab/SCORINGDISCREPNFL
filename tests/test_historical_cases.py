import json
import re
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HistoricalCaseDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads((ROOT / "data" / "historical-cases.json").read_text(encoding="utf-8"))
        cls.cases = cls.payload["cases"]

    def test_dataset_has_unique_case_ids_and_explicit_scope(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("curated", self.payload["coverage_status"])
        self.assertIn("not a count", self.payload["scope_note"])

    def test_case_fields_dates_and_deltas_are_consistent(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertRegex(case["game"]["date"], r"^\d{4}-\d{2}-\d{2}$")
                date.fromisoformat(case["game"]["date"])
                self.assertIn(case["evidence_grade"], {"A", "B", "C"})
                self.assertTrue(case["players"])
                for player in case["players"]:
                    self.assertTrue(player["changes"])
                    for change in player["changes"]:
                        self.assertIsInstance(change["initial"], (int, float))
                        self.assertIsInstance(change["corrected"], (int, float))
                        self.assertEqual(change["corrected"] - change["initial"], change["delta"])
                        self.assertTrue(change["initial_basis"])
                        self.assertTrue(change["final_basis"])

    def test_report_lag_matches_dates_when_both_are_known(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                if case["reported_on"] is None:
                    self.assertIsNone(case["elapsed_days_to_report"])
                    continue
                reported = date.fromisoformat(case["reported_on"])
                game_day = date.fromisoformat(case["game"]["date"])
                self.assertEqual((reported - game_day).days, case["elapsed_days_to_report"])
                self.assertTrue(case["reported_on_basis"])

    def test_market_and_score_outcomes_are_explicit_and_separate(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                impact = case["actual_market_impact"]
                score = case["score_effect"]
                self.assertIn("sportsbook_line_verified", impact)
                self.assertIn("sportsbook_settlement_change", impact)
                for field in ("official_score_changed", "winner_changed", "point_total_or_margin_changed"):
                    self.assertIsInstance(score[field], bool)
                if not impact["sportsbook_line_verified"]:
                    self.assertNotEqual(impact["sportsbook_settlement_change"], "verified")

    def test_all_manual_review_links_are_https(self):
        for case in self.cases:
            urls = [case["game"]["url"], *(source["url"] for source in case["sources"])]
            for url in urls:
                with self.subTest(case=case["id"], url=url):
                    self.assertTrue(url.startswith("https://"))
                    self.assertFalse(re.search(r"\s", url))

    def test_reported_downstream_effects_are_separate_from_sportsbook_outcomes(self):
        payload = json.loads((ROOT / "data" / "reported-downstream-effects.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["effects"])
        for effect in payload["effects"]:
            with self.subTest(effect=effect["id"]):
                self.assertIn("fantasy", effect["classification"])
                self.assertIn("not a sportsbook", effect["sportsbook_impact"])
                self.assertTrue(effect["verification_limit"])
                self.assertTrue(effect["source"]["url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
