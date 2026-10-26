"""Read-only validation of historical WFP/HDX Rwanda food-price data.

This service is for research and data-quality inspection only.
It does not publish current prices, correct locations, or generate forecasts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


SOURCE_ID = "WFP_HDX_RWA_FOOD_PRICES"
SOURCE_NAME = "Electric Sheep Africa; upstream WFP via HDX"

CACHE_DIR = Path.home() / ".cache" / "menya-neza-wfp-inspection"
FILES = (CACHE_DIR / "train.parquet", CACHE_DIR / "test.parquet")

REQUIRED_COLUMNS = {
    "date", "admin1", "admin2", "market", "market_id",
    "latitude", "longitude", "category", "commodity",
    "commodity_id", "unit", "priceflag", "pricetype",
    "currency", "price", "usdprice", "esa_source",
    "esa_processed",
}

LIMITATIONS = [
    "Historical observations only; this is not a live price feed.",
    "The latest observed date in the inspected extract is 2026-03-15.",
    "Market collection methodology and upstream licensing require verification.",
    "Retail and wholesale observations are distinct and must not be combined.",
    "Source price flags are preserved; aggregate observations are not treated as individual actual observations.",
    "Units must remain distinct; prices per KG, L, Unit, and Sack are not directly comparable.",
    "Some district labels are unavailable, and some market-geography combinations require investigation.",
    "No forecasts or corrected geographic labels are produced.",
]


def _read_source_files(
    files: tuple[Path, ...] | None = None,
) -> pd.DataFrame:
    """Read the inspected Parquet files without changing source values."""
    paths = files or FILES
    frames = []

    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"WFP inspection file not found: {path}")

        frame = pd.read_parquet(path)

        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(
                f"WFP file {path.name} is missing columns: {sorted(missing)}"
            )

        frame = frame.copy()
        frame["_inspection_file"] = path.name
        frames.append(frame)

    if not frames:
        raise ValueError("No WFP Parquet files were supplied.")

    return pd.concat(frames, ignore_index=True)


def inspect_dataset(
    files: tuple[Path, ...] | None = None,
) -> dict[str, Any]:
    """Return structural and quality findings without correcting observations."""
    frame = _read_source_files(files)

    parsed_dates = pd.to_datetime(frame["date"], errors="coerce")
    prices = pd.to_numeric(frame["price"], errors="coerce")
    latitudes = pd.to_numeric(frame["latitude"], errors="coerce")
    longitudes = pd.to_numeric(frame["longitude"], errors="coerce")

    text_columns = [
        "admin1", "admin2", "market", "category", "commodity",
        "unit", "priceflag", "pricetype", "currency", "esa_source",
    ]
    blank_required_values = {
        column: int(
            frame[column].astype("string").fillna("").str.strip().eq("").sum()
        )
        for column in text_columns
    }

    def unknown_value_counts(column, known_values):
        values = frame[column].astype("string").str.strip()
        normalized = values.str.casefold()
        mask = values.notna() & values.ne("") & ~normalized.isin(known_values)
        return {
            str(value): int(count)
            for value, count in frame.loc[mask, column]
            .value_counts(dropna=False).items()
        }

    candidate_key = [
        "date", "market_id", "commodity_id",
        "unit", "priceflag", "pricetype",
    ]

    missing_district = (
        frame["admin2"].astype("string").str.strip().str.casefold()
        .isin({
            "",
            "administrative unit not available",
            "not available",
            "unknown",
        })
    )

    duplicate_keys = int(frame.duplicated(candidate_key, keep=False).sum())

    market_geo = (
        frame[["market", "market_id", "admin1", "admin2"]]
        .drop_duplicates()
        .groupby("market_id", dropna=False)
        .size()
    )

    # These are known review leads from the initial data audit, not
    # automatic corrections or definitive proof of incorrect coordinates.
    geography_review_markets = {
        "kimironko",
        "muhanga",
        "gisenyi",
    }
    geography_review_mask = (
        frame["market"].astype("string").str.strip().str.casefold()
        .isin(geography_review_markets)
    )
    geography_review_rows = int(geography_review_mask.sum())
    geography_review_market_counts = {
        str(market): int(count)
        for market, count in (
            frame.loc[geography_review_mask, "market"]
            .value_counts()
            .items()
        )
    }

    dates = parsed_dates.dropna()

    return {
        "source_id": SOURCE_ID,
        "source": SOURCE_NAME,
        "status": "RESEARCH_ONLY_NOT_INTEGRATED",
        "publication_ready": False,
        "file_names": [path.name for path in (files or FILES)],
        "record_count": int(len(frame)),
        "columns": list(frame.columns.drop("_inspection_file")),
        "date_range": {
            "first": dates.min().date().isoformat() if not dates.empty else None,
            "last": dates.max().date().isoformat() if not dates.empty else None,
        },
        "quality_checks": {
            "missing_required_values": {
                column: int(frame[column].isna().sum())
                for column in sorted(REQUIRED_COLUMNS)
            },
            "invalid_dates": int(parsed_dates.isna().sum()),
            "blank_required_values": blank_required_values,
            "invalid_prices": int(prices.isna().sum()),
            "nonpositive_prices": int((prices <= 0).sum()),
            "invalid_latitudes": int(
                (latitudes.isna() | ~latitudes.between(-90, 90)).sum()
            ),
            "invalid_longitudes": int(
                (longitudes.isna() | ~longitudes.between(-180, 180)).sum()
            ),
            "unknown_price_types": unknown_value_counts(
                "pricetype", {"retail", "wholesale"}
            ),
            "unknown_price_flags": unknown_value_counts(
                "priceflag", {"actual", "actual,aggregate", "aggregate"}
            ),
            "unknown_currencies": unknown_value_counts(
                "currency", {"rwf"}
            ),
            "unknown_units": unknown_value_counts(
                "unit", {"kg", "l", "unit", "sack"}
            ),
            "duplicate_candidate_key_rows": duplicate_keys,
            "missing_or_unavailable_district_rows": int(missing_district.sum()),
            "records_in_markets_flagged_for_geography_review": (
                geography_review_rows
            ),
            "geography_review_rows_by_market_name": (
                geography_review_market_counts
            ),
            "market_ids_with_multiple_market_admin_combinations": int(
                (market_geo > 1).sum()
            ),
        },
        "price_types": {
            str(key): int(value)
            for key, value in frame["pricetype"].value_counts(
                dropna=False
            ).items()
        },
        "price_flags": {
            str(key): int(value)
            for key, value in frame["priceflag"].value_counts(
                dropna=False
            ).items()
        },
        "units": {
            str(key): int(value)
            for key, value in frame["unit"].value_counts(
                dropna=False
            ).items()
        },
        "currencies": {
            str(key): int(value)
            for key, value in frame["currency"].value_counts(
                dropna=False
            ).items()
        },
        "forecast_produced": False,
        "limitations": LIMITATIONS,
        "note": (
            "This report describes the inspected historical extract. "
            "Quality flags identify records for review; they do not establish "
            "that a source record is false or authorize a geographic correction."
        ),
    }
