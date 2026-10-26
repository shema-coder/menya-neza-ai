"""Audit the canonical TangaBid CSV and regenerate its quality report."""

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "tangabid"
SOURCE = DATA_DIR / "tangabid_six_month_price_trends.csv"
DUPLICATE = DATA_DIR / "tangabid_six_month_price_trends_1.csv"
OUTPUT = ROOT / "data" / "metadata" / "tangabid_price_trends_quality.json"

REQUIRED = {
    "month", "product", "unit", "location", "region",
    "avg_price", "min_price", "max_price", "sample_count",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    if not SOURCE.is_file():
        raise SystemExit(f"Canonical dataset not found: {SOURCE}")

    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise SystemExit("CSV is missing required columns.")
        rows = list(reader)

    months = Counter()
    unit_values = set()
    unit_counts = Counter()
    products = set()
    locations = set()
    regions = set()
    exact_region_labels = set()
    region_variants = defaultdict(set)
    seen = set()

    duplicate_keys = 0
    invalid_dates = 0
    invalid_prices = 0
    nonpositive_prices = 0
    invalid_price_ranges = 0
    invalid_sample_counts = 0
    empty_required_fields = 0

    for row in rows:
        if any(not (row.get(field) or "").strip() for field in REQUIRED):
            empty_required_fields += 1

        month_text = (row.get("month") or "").strip()
        try:
            parsed_month = date.fromisoformat(month_text)
            if parsed_month.day != 1:
                raise ValueError("Month must start on day 1.")
            months[parsed_month.isoformat()] += 1
        except ValueError:
            invalid_dates += 1

        for field, target in (
            ("product", products),
            ("location", locations),
            ("region", regions),
            ("unit", unit_values),
        ):
            value = (row.get(field) or "").strip()
            if value:
                target.add(value.casefold())

        region = (row.get("region") or "").strip()
        if region:
            exact_region_labels.add(region)
            region_variants[region.casefold()].add(region)

        unit = (row.get("unit") or "").strip()
        if unit:
            unit_counts[unit] += 1

        try:
            prices = [
                float(row[field])
                for field in ("min_price", "avg_price", "max_price")
            ]
            if not all(math.isfinite(value) for value in prices):
                invalid_prices += 1
            else:
                if any(value <= 0 for value in prices):
                    nonpositive_prices += 1
                if not prices[0] <= prices[1] <= prices[2]:
                    invalid_price_ranges += 1
        except (TypeError, ValueError):
            invalid_prices += 1

        try:
            count = int(row["sample_count"])
            if count < 1:
                invalid_sample_counts += 1
        except (TypeError, ValueError):
            invalid_sample_counts += 1

        key = tuple(
            (row.get(field) or "").strip().casefold()
            for field in ("month", "product", "unit", "location")
        )
        if key in seen:
            duplicate_keys += 1
        seen.add(key)

    source_hash = sha256(SOURCE)
    duplicate_exists = DUPLICATE.is_file()
    duplicate_hash = sha256(DUPLICATE) if duplicate_exists else None

    report = {
        "source": "TangaBid-provided monthly price-trend dataset",
        "file": str(SOURCE.relative_to(ROOT)),
        "sha256": source_hash,
        "record_count": len(rows),
        "month_counts": dict(sorted(months.items())),
        "unique_products": len(products),
        "unique_locations": len(locations),
        "unique_regions": len(regions),
        "exact_region_label_count": len(exact_region_labels),
        "region_label_variants": {
            key: sorted(values)
            for key, values in sorted(region_variants.items())
            if len(values) > 1
        },
        "units": dict(sorted(unit_counts.items(), key=lambda item: item[0].casefold())),
        "unique_units": len(unit_values),
        "duplicate_keys": duplicate_keys,
        "invalid_dates": invalid_dates,
        "invalid_prices": invalid_prices,
        "nonpositive_prices": nonpositive_prices,
        "invalid_price_ranges": invalid_price_ranges,
        "invalid_sample_counts": invalid_sample_counts,
        "empty_required_fields": empty_required_fields,
        "duplicate_export": {
            "exists": duplicate_exists,
            "sha256": duplicate_hash,
            "byte_identical_to_canonical": (
                source_hash == duplicate_hash if duplicate_exists else None
            ),
        },
        "coverage_start_month": min(months)[:7] if months else None,
        "coverage_end_month": max(months)[:7] if months else None,
        "calendar_month_count": len(months),
        "coverage_note": (
            "October 2026 may be incomplete. Currency, collection methodology, "
            "exact price type, sample-count meaning, and consistency of markets, "
            "sellers, and sampling across months remain unverified."
        ),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nReport written to: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
