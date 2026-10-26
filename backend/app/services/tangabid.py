"""Read-only access to the TangaBid-provided monthly price-trend export.

Currency and collection methodology have not yet been independently verified.
These observations must not be described as official or live prices.
"""

import csv
import math
from collections import Counter
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PRICE_FILE = (
    PROJECT_ROOT / "data" / "raw" / "tangabid"
    / "tangabid_six_month_price_trends.csv"
)

SOURCE_NAME = "TangaBid-provided monthly price-trend dataset"
LIMITATIONS = [
    "Source collection methodology and currency have not been independently verified.",
    "Monthly aggregates are not live quotes and do not establish future prices.",
    "October 2026 may be incomplete because the export was inspected on 22 October 2026.",
    "Sample counts indicate the count reported by the source; their methodology needs confirmation.",
    "Consistency of markets, sellers, and sampling methods across months has not been verified; apparent changes may reflect changes in the sampled records.",
    "Different units must not be compared or combined.",
]


@lru_cache(maxsize=1)
def load_records() -> tuple[dict[str, Any], ...]:
    """Load and validate the canonical CSV only; never load the duplicate copy."""
    if not PRICE_FILE.is_file():
        raise FileNotFoundError(f"Price dataset not found: {PRICE_FILE}")

    required = {
        "month", "product", "unit", "location", "region",
        "avg_price", "min_price", "max_price", "sample_count",
    }
    records = []
    seen = set()

    with PRICE_FILE.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("Price dataset is missing required columns.")

        for line_number, row in enumerate(reader, start=2):
            try:
                month = date.fromisoformat(row["month"].strip())
                if month.day != 1:
                    raise ValueError("Month must use the first day of the month.")

                product = row["product"].strip()
                unit = row["unit"].strip()
                location = row["location"].strip()
                region = row["region"].strip()
                avg_price = float(row["avg_price"])
                min_price = float(row["min_price"])
                max_price = float(row["max_price"])
                sample_count = int(row["sample_count"])

                if not all((product, unit, location, region)):
                    raise ValueError("Product, unit, location, and region are required.")
                prices = (avg_price, min_price, max_price)
                if not all(math.isfinite(value) for value in prices):
                    raise ValueError("Prices must be finite numbers.")
                if not all(value > 0 for value in prices):
                    raise ValueError("Prices must be positive.")
                if min_price > avg_price or avg_price > max_price:
                    raise ValueError("Expected min_price <= avg_price <= max_price.")
                if sample_count < 1:
                    raise ValueError("sample_count must be at least 1.")

            except (TypeError, ValueError, AttributeError) as exc:
                raise ValueError(
                    f"Invalid price record on CSV line {line_number}: {exc}"
                ) from exc

            key = (
                month.isoformat(), product.casefold(), unit.casefold(),
                location.casefold(),
            )
            if key in seen:
                raise ValueError(
                    f"Duplicate price record on CSV line {line_number}."
                )
            seen.add(key)

            records.append({
                "month": month.isoformat(),
                "product": product,
                "unit": unit,
                "location": location,
                "region": region,
                "avg_price": avg_price,
                "min_price": min_price,
                "max_price": max_price,
                "sample_count": sample_count,
            })

    return tuple(records)


def price_trends(
    product: str | None = None,
    month: str | None = None,
    region: str | None = None,
    location: str | None = None,
    unit: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Filter source records without combining units or calculating forecasts."""
    if month is not None:
        try:
            parsed_month = date.fromisoformat(month)
            if parsed_month.day != 1 or parsed_month.isoformat() != month:
                raise ValueError
        except ValueError as exc:
            raise ValueError("month must use YYYY-MM-01 format.") from exc

    all_records = list(load_records())

    # Build dropdown options from the complete dataset, not the filtered page.
    # Deduplicate case-insensitively while retaining an original source label.
    def unique_values(field: str) -> list[str]:
        seen: set[str] = set()
        values: list[str] = []
        for row in all_records:
            value = str(row[field])
            normalized = value.casefold()
            if normalized not in seen:
                seen.add(normalized)
                values.append(value)
        return sorted(values, key=str.casefold)

    available_options = {
        "products": unique_values("product"),
        "months": unique_values("month"),
        "regions": unique_values("region"),
        "locations": unique_values("location"),
        "units": unique_values("unit"),
    }

    records_by_month = dict(sorted(
        Counter(row["month"] for row in all_records).items()
    ))
    unit_record_counts = dict(sorted(
        Counter(row["unit"] for row in all_records).items(),
        key=lambda item: item[0].casefold(),
    ))
    coverage = {
        "record_count": len(all_records),
        "start_month": min(records_by_month)[:7] if records_by_month else None,
        "end_month": max(records_by_month)[:7] if records_by_month else None,
        "calendar_month_count": len(records_by_month),
        "records_by_month": records_by_month,
        "product_count": len(available_options["products"]),
        "location_count": len(available_options["locations"]),
        "region_count": len(available_options["regions"]),
        "unit_record_counts": unit_record_counts,
    }

    records = all_records

    filters = {
        "product": product,
        "month": month,
        "region": region,
        "location": location,
        "unit": unit,
    }

    for field, requested in filters.items():
        if requested is None:
            continue
        requested = requested.strip()
        records = [
            row for row in records
            if str(row[field]).casefold() == requested.casefold()
        ]

    # Keep source records distinct; never aggregate unlike units.
    records.sort(
        key=lambda row: (
            row["month"], row["product"].casefold(),
            row["region"].casefold(), row["location"].casefold(),
            row["unit"].casefold(),
        )
    )

    return {
        "source": SOURCE_NAME,
        "source_file": "data/raw/tangabid/tangabid_six_month_price_trends.csv",
        "currency": None,
        "currency_status": "NOT_INDEPENDENTLY_VERIFIED",
        "price_type": "Source-reported monthly price summary; exact market/price type unverified",
        "filters": filters,
        "available_options": available_options,
        "coverage": coverage,
        "total_matching_records": len(records),
        "limit": limit,
        "offset": offset,
        "records": records[offset:offset + limit],
        "limitations": LIMITATIONS,
        "forecast_produced": False,
        "note": (
            "These are source-provided monthly summaries, not live prices or forecasts. "
            "Confirm currency, collection methodology, price type, and sample-count "
            "meaning before relying on them for decisions."
        ),
    }
