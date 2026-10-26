import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


class APIEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_identifies_project_and_api_docs(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["project"], "MENYA NEZA AI")
        self.assertEqual(body["documentation"], "/docs")

    def test_health_and_dataset_status(self):
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "healthy")

        status = self.client.get("/api/v1/data/status")
        self.assertEqual(status.status_code, 200)
        body = status.json()
        self.assertTrue(body["ready"])
        production = body["production_dataset"]
        validation = body["validation_dataset"]

        self.assertEqual(production["records"], 1650)
        self.assertEqual(validation["records"], 55)

        for dataset in (production, validation):
            with self.subTest(dataset=dataset):
                self.assertTrue(dataset["available"])
                self.assertTrue(dataset["schema_valid"])
                self.assertEqual(dataset["missing_columns"], [])
                self.assertGreater(dataset["records"], 0)

    def test_district_endpoint_returns_unique_options(self):
        response = self.client.get("/api/v1/districts")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], len(body["districts"]))
        self.assertEqual(len(body["districts"]), len(set(body["districts"])))
        self.assertIn("Huye", body["districts"])

    def test_production_filter_and_source_traceability(self):
        response = self.client.get(
            "/api/v1/production",
            params={
                "district": "huye",
                "season": "b",
                "crop": "maize",
                "year": 2025,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_matching_records"], 1)

        record = body["records"][0]
        self.assertEqual(record["district"], "Huye")
        self.assertEqual(record["season"], "B")
        self.assertEqual(record["crop"], "Maize")
        self.assertEqual(record["production_mt"], 1112.0)
        self.assertEqual(record["source"], "NISR SAS 2025")
        self.assertEqual(record["source_table"], 25)
        self.assertEqual(record["source_page"], 62)
        self.assertIn("not a live weather feed", body["note"])

    def test_production_pagination_reports_total_matches(self):
        first = self.client.get(
            "/api/v1/production",
            params={"limit": 1, "offset": 0},
        )
        second = self.client.get(
            "/api/v1/production",
            params={"limit": 1, "offset": 1},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["total_matching_records"], 1650)
        self.assertEqual(second.json()["total_matching_records"], 1650)
        self.assertEqual(len(first.json()["records"]), 1)
        self.assertEqual(len(second.json()["records"]), 1)
        self.assertNotEqual(
            first.json()["records"][0],
            second.json()["records"][0],
        )

    def test_unknown_district_returns_helpful_422(self):
        response = self.client.get(
            "/api/v1/production",
            params={"district": "NotARealDistrict"},
        )
        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertEqual(detail["provided"], "NotARealDistrict")
        self.assertIn("Huye", detail["available_options"])

    def test_unavailable_year_returns_422(self):
        response = self.client.get(
            "/api/v1/production",
            params={"year": 1900},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("available_years", response.json()["detail"])

    def test_invalid_pagination_limits_return_422(self):
        for params in ({"limit": 0}, {"limit": 1001}, {"offset": -1}):
            with self.subTest(params=params):
                response = self.client.get(
                    "/api/v1/production",
                    params=params,
                )
                self.assertEqual(response.status_code, 422)

    def test_summary_explains_validation_limits(self):
        response = self.client.get(
            "/api/v1/production/summary",
            params={"year": 2025},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(body["count"], 0)
        self.assertIn("must not automatically be treated as", body["note"])

        keys = [
            (row["year"], row["season"], row["crop"])
            for row in body["summaries"]
        ]
        self.assertEqual(len(keys), len(set(keys)))

    def test_data_quality_filter_preserves_consistent_counts(self):
        response = self.client.get(
            "/api/v1/data-quality",
            params={"season": "B", "crop": "Maize"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(body["records_returned"], 0)
        self.assertEqual(
            sum(body["status_counts"].values()),
            body["records_returned"],
        )

    def test_unknown_crop_returns_422(self):
        response = self.client.get(
            "/api/v1/production/summary",
            params={"crop": "ImaginaryCrop"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("available_options", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
