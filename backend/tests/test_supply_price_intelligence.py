import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


class SupplyPriceIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_combined_report_uses_existing_production_evidence(self):
        response = self.client.get(
            "/api/v1/intelligence/supply-price",
            params={
                "crop": "Maize",
                "season": "B",
                "year": 2025,
                "district": "Huye",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["filters"]["crop"], "Maize")
        self.assertEqual(body["selected_district_evidence"]["district"], "Huye")
        self.assertEqual(
            body["selected_district_evidence"]["production_mt"], 1112.0
        )
        self.assertEqual(body["source"], "NISR Seasonal Agricultural Survey 2025")
        self.assertIn("nst2_alignment", body)
        self.assertIn("market_price_intelligence", body)
        self.assertIn("price_movement_assessment", body)

    def test_no_unverified_price_forecast_is_generated(self):
        response = self.client.get(
            "/api/v1/intelligence/supply-price",
            params={"crop": "Maize", "season": "B", "year": 2025},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertFalse(
            body["market_price_intelligence"]["verified_price_feed_connected"]
        )
        self.assertFalse(
            body["price_movement_assessment"]["forecast_produced"]
        )
        self.assertEqual(
            body["price_movement_assessment"]["status"],
            "INSUFFICIENT_VERIFIED_PRICE_EVIDENCE",
        )

    def test_nst2_targets_are_references_not_claimed_achievements(self):
        response = self.client.get(
            "/api/v1/intelligence/supply-price",
            params={"crop": "Maize", "season": "B", "year": 2025},
        )
        self.assertEqual(response.status_code, 200)
        alignment = response.json()["nst2_alignment"]

        self.assertEqual(
            alignment["reference_indicators"]["production_mt"]["end_term_target"],
            874337,
        )
        self.assertEqual(
            alignment["target_comparison_status"],
            "NOT_COMPUTED_PERIOD_AND_DEFINITION_CHECK_REQUIRED",
        )

    def test_situation_summary_connects_evidence_and_limits(self):
        response = self.client.get(
            "/api/v1/intelligence/supply-price",
            params={
                "crop": "Maize",
                "season": "B",
                "year": 2025,
                "district": "Huye",
            },
        )
        self.assertEqual(response.status_code, 200)

        situation = response.json()["situation_summary"]

        self.assertEqual(
            situation["status"], "HISTORICAL_EVIDENCE_AVAILABLE"
        )
        self.assertEqual(
            situation["observed"]["selected_district_production_mt"],
            1112.0,
        )
        self.assertTrue(
            situation["connected_evidence"]["historical_nisr_production"]
        )
        self.assertFalse(
            situation["connected_evidence"]["verified_market_price_observations"]
        )
        self.assertFalse(
            situation["connected_evidence"]["validated_live_disaster_warnings"]
        )
        self.assertTrue(situation["unknowns"])
        self.assertTrue(situation["recommended_next_actions"])

    def test_unknown_crop_is_rejected(self):
        response = self.client.get(
            "/api/v1/intelligence/supply-price",
            params={"crop": "ImaginaryCrop", "season": "B", "year": 2025},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
