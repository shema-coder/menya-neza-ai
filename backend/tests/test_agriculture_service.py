import unittest
import tempfile
from pathlib import Path

from backend.app.services import agriculture


class AgricultureServiceTests(unittest.TestCase):
    def test_both_datasets_are_available(self):
        status = agriculture.data_status()
        self.assertTrue(status["production_dataset"]["available"])
        self.assertTrue(status["validation_dataset"]["available"])
        self.assertTrue(status["ready"])

    def test_inspect_dataset_rejects_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.csv"
            result = agriculture._inspect_dataset(path, {"year", "season"})

        self.assertFalse(result["available"])
        self.assertFalse(result["schema_valid"])
        self.assertIn("error", result)

    def test_inspect_dataset_reports_missing_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "partial.csv"
            path.write_text("year\n2025\n", encoding="utf-8")
            result = agriculture._inspect_dataset(
                path, {"year", "season"}
            )

        self.assertTrue(result["available"])
        self.assertEqual(result["records"], 1)
        self.assertFalse(result["schema_valid"])
        self.assertEqual(result["missing_columns"], ["season"])

    def test_inspect_dataset_rejects_empty_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.csv"
            path.write_text("year,season\n", encoding="utf-8")
            result = agriculture._inspect_dataset(
                path, {"year", "season"}
            )

        self.assertTrue(result["available"])
        self.assertEqual(result["records"], 0)
        self.assertFalse(result["schema_valid"])
        self.assertIn("error", result)

    def test_inspect_dataset_accepts_valid_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valid.csv"
            path.write_text(
                "year,season\n2025,A\n",
                encoding="utf-8",
            )
            result = agriculture._inspect_dataset(
                path, {"year", "season"}
            )

        self.assertTrue(result["available"])
        self.assertEqual(result["records"], 1)
        self.assertTrue(result["schema_valid"])
        self.assertEqual(result["missing_columns"], [])

    def test_inspect_dataset_rejects_duplicate_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.csv"
            path.write_text(
                "year,season,season\n2025,A,B\n",
                encoding="utf-8",
            )
            result = agriculture._inspect_dataset(
                path, {"year", "season"}
            )

        self.assertFalse(result["schema_valid"])
        self.assertEqual(result["duplicate_columns"], ["season"])
        self.assertIn("Duplicate column names", result["error"])

    def test_inspect_dataset_rejects_extra_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extra.csv"
            path.write_text(
                "year,season\n2025,A,unexpected\n",
                encoding="utf-8",
            )
            result = agriculture._inspect_dataset(
                path, {"year", "season"}
            )

        self.assertFalse(result["schema_valid"])
        self.assertEqual(result["rows_with_extra_fields"], 1)
        self.assertIn("extra fields", result["error"])

    def test_inspect_dataset_rejects_missing_row_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "short.csv"
            path.write_text(
                "year,season\n2025\n",
                encoding="utf-8",
            )
            result = agriculture._inspect_dataset(
                path, {"year", "season"}
            )

        self.assertFalse(result["schema_valid"])
        self.assertEqual(result["rows_with_missing_fields"], 1)
        self.assertIn("missing fields", result["error"])

    def test_production_records_have_expected_fields(self):
        records = agriculture.load_production()
        self.assertGreater(len(records), 0)

        required = {
            "year",
            "season",
            "district",
            "crop",
            "production_mt",
            "source_value_status",
            "source_table",
            "source_page",
        }
        self.assertTrue(required.issubset(records[0].keys()))

    def test_districts_are_unique(self):
        districts = agriculture.list_districts()
        self.assertEqual(len(districts), len(set(districts)))
        self.assertGreater(len(districts), 0)

    def test_seasons_and_crops_are_available(self):
        self.assertTrue(
            {"A", "B", "C"}.issubset(
                {item["season"] for item in agriculture.list_seasons()}
            )
        )
        self.assertIn("Maize", agriculture.list_crops())

    def test_filtering_returns_matching_records(self):
        records = agriculture.filter_production(
            district="Huye",
            season="B",
            crop="Maize",
            year=2025,
        )
        self.assertGreater(len(records), 0)

        for row in records:
            self.assertEqual(row["district"], "Huye")
            self.assertEqual(row["season"], "B")
            self.assertEqual(row["crop"], "Maize")
            self.assertEqual(row["year"], 2025)

    def test_blank_numeric_values_remain_missing(self):
        self.assertIsNone(agriculture._number(""))
        self.assertIsNone(agriculture._number(None))
        self.assertEqual(agriculture._number("5,216"), 5216.0)

    def test_summaries_keep_crops_separate(self):
        summaries = agriculture.production_summaries(year=2025)
        self.assertGreater(len(summaries), 0)

        keys = [
            (row["year"], row["season"], row["crop"])
            for row in summaries
        ]
        self.assertEqual(len(keys), len(set(keys)))

        for row in summaries:
            self.assertIn("published_national_mt", row)
            self.assertIn("validation_status", row)
            self.assertIn("interpretation_note", row)

    def test_data_quality_has_status_counts(self):
        quality = agriculture.data_quality()
        self.assertGreater(quality["records_returned"], 0)
        self.assertEqual(
            sum(quality["status_counts"].values()),
            quality["records_returned"],
        )


if __name__ == "__main__":
    unittest.main()
