import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import tangabid


class TangaBidPriceTrendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_endpoint_returns_source_and_caveats(self):
        response = self.client.get(
            "/api/v1/market-prices/trends",
            params={"limit": 2},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["source"], tangabid.SOURCE_NAME)
        self.assertIsNone(body["currency"])
        self.assertFalse(body["forecast_produced"])
        self.assertEqual(len(body["records"]), 2)
        self.assertTrue(body["limitations"])

    def test_coverage_summary_describes_full_dataset(self):
        response = self.client.get("/api/v1/market-prices/trends")
        self.assertEqual(response.status_code, 200)

        coverage = response.json()["coverage"]
        self.assertEqual(coverage["record_count"], 6765)
        self.assertEqual(coverage["start_month"], "2026-04")
        self.assertEqual(coverage["end_month"], "2026-10")
        self.assertEqual(coverage["calendar_month_count"], 7)
        self.assertEqual(coverage["product_count"], 122)
        self.assertEqual(coverage["location_count"], 47)
        self.assertEqual(sum(coverage["records_by_month"].values()), 6765)

    def test_non_finite_prices_are_rejected(self):
        original = dict(tangabid.load_records()[0])
        for invalid_price in ("NaN", "inf", "-inf"):
            with self.subTest(price=invalid_price):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "invalid_prices.csv"
                    row = dict(original)
                    row["avg_price"] = invalid_price

                    with path.open("w", encoding="utf-8", newline="") as handle:
                        writer = csv.DictWriter(handle, fieldnames=row.keys())
                        writer.writeheader()
                        writer.writerow(row)

                    with patch.object(tangabid, "PRICE_FILE", path):
                        tangabid.load_records.cache_clear()
                        try:
                            with self.assertRaisesRegex(
                                ValueError, "Prices must be finite numbers"
                            ):
                                tangabid.load_records()
                        finally:
                            tangabid.load_records.cache_clear()

    def test_product_month_and_unit_filters(self):
        response = self.client.get(
            "/api/v1/market-prices/trends",
            params={
                "product": "Maize",
                "month": "2026-09-01",
                "unit": "Kg",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(body["total_matching_records"], 0)
        for row in body["records"]:
            self.assertEqual(row["product"].casefold(), "maize")
            self.assertEqual(row["month"], "2026-09-01")
            self.assertEqual(row["unit"].casefold(), "kg")
            self.assertGreaterEqual(row["sample_count"], 1)

    def test_region_filter_is_case_insensitive(self):
        response = self.client.get(
            "/api/v1/market-prices/trends",
            params={"region": "kicukiro"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.json()["total_matching_records"], 0)
        self.assertTrue(all(
            row["region"].casefold() == "kicukiro"
            for row in response.json()["records"]
        ))

    def test_location_filter_and_pagination(self):
        response = self.client.get(
            "/api/v1/market-prices/trends",
            params={"location": "Mulindi", "limit": 1, "offset": 0},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(body["total_matching_records"], 0)
        self.assertEqual(len(body["records"]), 1)
        self.assertEqual(body["records"][0]["location"].casefold(), "mulindi")

    def test_invalid_month_returns_422(self):
        response = self.client.get(
            "/api/v1/market-prices/trends",
            params={"month": "October 2026"},
        )
        self.assertEqual(response.status_code, 422)

    def test_invalid_pagination_returns_422(self):
        for params in ({"limit": 0}, {"limit": 1001}, {"offset": -1}):
            with self.subTest(params=params):
                response = self.client.get(
                    "/api/v1/market-prices/trends",
                    params=params,
                )
                self.assertEqual(response.status_code, 422)

    def test_missing_dataset_returns_503(self):
        with patch.object(
            tangabid, "PRICE_FILE",
            tangabid.PROJECT_ROOT / "data" / "missing-price-file.csv",
        ):
            tangabid.load_records.cache_clear()
            try:
                response = self.client.get("/api/v1/market-prices/trends")
                self.assertEqual(response.status_code, 503)
            finally:
                tangabid.load_records.cache_clear()

    def test_duplicate_export_is_not_added_to_canonical_dataset(self):
        rows = tangabid.load_records()
        self.assertEqual(len(rows), 6765)
        self.assertEqual(
            tangabid.PRICE_FILE.name,
            "tangabid_six_month_price_trends.csv",
        )
        self.assertNotIn("_1.csv", str(tangabid.PRICE_FILE))

    def test_source_records_keep_their_reported_units(self):
        response = self.client.get(
            "/api/v1/market-prices/trends",
            params={"product": "Maize"},
        )
        self.assertEqual(response.status_code, 200)
        rows = response.json()["records"]
        self.assertTrue(rows)
        self.assertTrue(all(row["unit"] for row in rows))
        self.assertTrue(all(row["sample_count"] >= 1 for row in rows))


    def test_available_filter_options_cover_the_full_dataset(self):
        response = self.client.get("/api/v1/market-prices/trends")
        self.assertEqual(response.status_code, 200)

        body = response.json()
        options = body["available_options"]

        self.assertEqual(body["total_matching_records"], 6765)
        self.assertIn("Maize", options["products"])
        self.assertIn("2026-10-01", options["months"])
        self.assertIn("Kg", options["units"])
        self.assertTrue(options["regions"])
        self.assertTrue(options["locations"])

    def test_region_options_deduplicate_case_variants(self):
        response = self.client.get("/api/v1/market-prices/trends")
        self.assertEqual(response.status_code, 200)

        regions = response.json()["available_options"]["regions"]
        normalized_regions = [region.casefold() for region in regions]

        self.assertEqual(len(normalized_regions), len(set(normalized_regions)))

    def test_filter_options_remain_available_when_records_are_filtered(self):
        response = self.client.get(
            "/api/v1/market-prices/trends",
            params={"product": "Maize", "limit": 1},
        )
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(len(body["records"]), 1)
        self.assertGreater(body["total_matching_records"], 1)
        self.assertIn("RICE - luck Kema", body["available_options"]["products"])


if __name__ == "__main__":
    unittest.main()
