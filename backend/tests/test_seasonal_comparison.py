import unittest

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import agriculture


class SeasonalComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_eligible_crop_list_contains_only_three_season_crops(self):
        result = agriculture.seasonal_comparison(year=2025)

        self.assertTrue(result["available_crops"])
        self.assertIn("Beans", result["available_crops"])
        self.assertIn("Irish potatoes", result["available_crops"])
        self.assertEqual(result["seasons"], [])

    def test_irish_potatoes_returns_seasons_in_order(self):
        result = agriculture.seasonal_comparison(
            year=2025, crop="Irish potatoes"
        )

        self.assertTrue(result["eligible"])
        self.assertEqual(
            [row["season"] for row in result["seasons"]],
            ["A", "B", "C"],
        )
        self.assertTrue(all(
            "district_coverage_percent" in row
            for row in result["seasons"]
        ))
        self.assertTrue(all(
            "source_table" in row and "source_page" in row
            for row in result["seasons"]
        ))

    def test_api_lists_eligible_crops(self):
        response = self.client.get(
            "/api/v1/production/seasonal-comparison",
            params={"year": 2025},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("Beans", body["available_crops"])
        self.assertEqual(body["unit"], "metric tonnes")

    def test_api_returns_three_seasons_for_eligible_crop(self):
        response = self.client.get(
            "/api/v1/production/seasonal-comparison",
            params={"crop": "Irish potatoes", "year": 2025},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["season"] for row in response.json()["seasons"]],
            ["A", "B", "C"],
        )

    def test_api_rejects_crop_not_available_in_all_seasons(self):
        response = self.client.get(
            "/api/v1/production/seasonal-comparison",
            params={"crop": "Maize", "year": 2025},
        )

        self.assertEqual(response.status_code, 422)

    def test_notes_explain_comparison_limitations(self):
        result = agriculture.seasonal_comparison(
            year=2025, crop="Beans"
        )

        notes = " ".join(result["interpretation_notes"]).lower()
        self.assertIn("not a direct", notes)
        self.assertIn("current stock", notes)


if __name__ == "__main__":
    unittest.main()
