import tempfile
import unittest
from pathlib import Path

import pandas as pd

from backend.app.services import wfp_prices


def sample_record():
    return {
        "date": pd.Timestamp("2025-01-15"),
        "admin1": "Eastern Province",
        "admin2": "Gatsibo",
        "market": "Example Market",
        "market_id": 123,
        "latitude": -1.75,
        "longitude": 30.34,
        "category": "Cereals and Tubers",
        "commodity": "Maize",
        "commodity_id": 1,
        "unit": "KG",
        "priceflag": "actual",
        "pricetype": "Retail",
        "currency": "RWF",
        "price": 500.0,
        "usdprice": 0.38,
        "esa_source": "HDX",
        "esa_processed": pd.Timestamp("2026-04-07"),
    }


class WFPPriceInspectionTests(unittest.TestCase):
    def write_fixture(self, directory, records):
        path = Path(directory) / "fixture.parquet"
        pd.DataFrame(records).to_parquet(path, index=False)
        return (path,)

    def test_inspection_keeps_dataset_research_only(self):
        with tempfile.TemporaryDirectory() as directory:
            files = self.write_fixture(directory, [sample_record()])
            report = wfp_prices.inspect_dataset(files)

        self.assertEqual(report["record_count"], 1)
        self.assertEqual(report["status"], "RESEARCH_ONLY_NOT_INTEGRATED")
        self.assertFalse(report["publication_ready"])
        self.assertFalse(report["forecast_produced"])

    def test_unavailable_district_is_flagged_not_corrected(self):
        row = sample_record()
        row["admin2"] = "Administrative unit not available"

        with tempfile.TemporaryDirectory() as directory:
            files = self.write_fixture(directory, [row])
            report = wfp_prices.inspect_dataset(files)

        self.assertEqual(
            report["quality_checks"]["missing_or_unavailable_district_rows"],
            1,
        )

    def test_duplicate_candidate_keys_are_reported(self):
        row = sample_record()

        with tempfile.TemporaryDirectory() as directory:
            files = self.write_fixture(directory, [row, row.copy()])
            report = wfp_prices.inspect_dataset(files)

        self.assertEqual(
            report["quality_checks"]["duplicate_candidate_key_rows"],
            2,
        )

    def test_invalid_dates_and_prices_are_reported(self):
        row = sample_record()
        row["date"] = "not-a-date"
        row["price"] = "not-a-price"

        with tempfile.TemporaryDirectory() as directory:
            files = self.write_fixture(directory, [row])
            report = wfp_prices.inspect_dataset(files)

        self.assertEqual(report["quality_checks"]["invalid_dates"], 1)
        self.assertEqual(report["quality_checks"]["invalid_prices"], 1)

    def test_invalid_coordinates_are_reported(self):
        row = sample_record()
        row["latitude"] = 95
        row["longitude"] = -200

        with tempfile.TemporaryDirectory() as directory:
            report = wfp_prices.inspect_dataset(
                self.write_fixture(directory, [row])
            )

        checks = report["quality_checks"]
        self.assertEqual(checks["invalid_latitudes"], 1)
        self.assertEqual(checks["invalid_longitudes"], 1)

    def test_blank_required_text_is_reported(self):
        row = sample_record()
        row["market"] = "   "

        with tempfile.TemporaryDirectory() as directory:
            report = wfp_prices.inspect_dataset(
                self.write_fixture(directory, [row])
            )

        self.assertEqual(
            report["quality_checks"]["blank_required_values"]["market"],
            1,
        )

    def test_unrecognized_price_metadata_is_reported(self):
        row = sample_record()
        row["pricetype"] = "Auction"
        row["priceflag"] = "estimated"
        row["currency"] = "XYZ"
        row["unit"] = "crate"

        with tempfile.TemporaryDirectory() as directory:
            report = wfp_prices.inspect_dataset(
                self.write_fixture(directory, [row])
            )

        checks = report["quality_checks"]
        self.assertEqual(checks["unknown_price_types"], {"Auction": 1})
        self.assertEqual(checks["unknown_price_flags"], {"estimated": 1})
        self.assertEqual(checks["unknown_currencies"], {"XYZ": 1})
        self.assertEqual(checks["unknown_units"], {"crate": 1})

    def test_missing_required_column_is_rejected(self):
        row = sample_record()
        del row["pricetype"]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.parquet"
            pd.DataFrame([row]).to_parquet(path, index=False)

            with self.assertRaisesRegex(ValueError, "missing columns"):
                wfp_prices.inspect_dataset((path,))

    def test_missing_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.parquet"

            with self.assertRaises(FileNotFoundError):
                wfp_prices.inspect_dataset((missing,))


if __name__ == "__main__":
    unittest.main()
