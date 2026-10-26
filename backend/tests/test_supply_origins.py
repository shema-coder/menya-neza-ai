import unittest

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import agriculture


class SupplyOriginsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_maize_season_b_2025_summary(self):
        result = agriculture.supply_origins(
            crop="Maize", season="B", year=2025
        )
        summary = result["summary"]

        self.assertEqual(summary["district_records"], 30)
        self.assertEqual(summary["reported_records"], 30)
        self.assertEqual(summary["missing_production_records"], 0)
        self.assertEqual(summary["district_coverage_percent"], 100.0)
        self.assertEqual(summary["reported_district_subtotal_mt"], 117710.0)
        self.assertTrue(summary["subtotal_is_complete"])

    def test_reported_districts_are_ranked_descending(self):
        result = agriculture.supply_origins(
            crop="Maize", season="B", year=2025
        )
        districts = result["districts"]
        values = [row["production_mt"] for row in districts]

        self.assertEqual(values, sorted(values, reverse=True))
        self.assertEqual(districts[0]["rank"], 1)
        self.assertEqual(districts[0]["district"], "Nyagatare")
        self.assertEqual(districts[0]["production_mt"], 39347.0)

    def test_source_traceability_and_caveats_are_present(self):
        result = agriculture.supply_origins(
            crop="Maize", season="B", year=2025
        )

        self.assertEqual(result["unit"], "metric tonnes")
        self.assertEqual(result["districts"][0]["source_table"], 25)
        self.assertEqual(result["districts"][0]["source_page"], 62)
        self.assertTrue(any(
            "current stock" in note
            for note in result["interpretation_notes"]
        ))

    def test_api_endpoint_returns_ranked_results(self):
        response = self.client.get(
            "/api/v1/supply/origins",
            params={"crop": "maize", "season": "b", "year": 2025},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["filters"]["crop"], "Maize")
        self.assertEqual(body["districts"][0]["district"], "Nyagatare")
        self.assertEqual(body["summary"]["reported_records"], 30)

    def test_unknown_crop_is_rejected(self):
        response = self.client.get(
            "/api/v1/supply/origins",
            params={
                "crop": "ImaginaryCrop",
                "season": "B",
                "year": 2025,
            },
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
