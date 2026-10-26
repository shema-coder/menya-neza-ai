"""Read-only access to MENYA NEZA AI's processed NISR datasets."""

import csv
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]

PRODUCTION_FILE = (
    PROJECT_ROOT / "data" / "processed"
    / "nisr_sas_2025_crop_production_long.csv"
)
VALIDATION_FILE = (
    PROJECT_ROOT / "data" / "processed"
    / "nisr_sas_2025_crop_production_validation.csv"
)

DATA_SOURCE = "NISR Seasonal Agricultural Survey 2025"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required dataset not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _number(value: Any) -> float | None:
    """Parse a numeric source value without converting blanks to zero."""
    if value is None:
        return None

    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


@lru_cache(maxsize=1)
def load_production() -> tuple[dict[str, Any], ...]:
    """Load and cache processed crop-production records."""
    records = []

    for row in _read_csv(PRODUCTION_FILE):
        record = dict(row)
        record["year"] = _integer(row.get("year"))
        record["production_mt"] = _number(row.get("production_mt"))
        record["source_table"] = _integer(row.get("source_table"))
        record["source_page"] = _integer(row.get("source_page"))
        records.append(record)

    return tuple(records)


@lru_cache(maxsize=1)
def load_validation() -> tuple[dict[str, Any], ...]:
    """Load and cache national-versus-district validation records."""
    records = []

    numeric_fields = (
        "district_sum_mt",
        "published_national_mt",
        "difference_mt",
    )

    for row in _read_csv(VALIDATION_FILE):
        record = dict(row)
        record["year"] = _integer(row.get("year"))
        record["district_missing_count"] = _integer(
            row.get("district_missing_count")
        )
        record["source_table"] = _integer(row.get("source_table"))
        record["source_page"] = _integer(row.get("source_page"))

        for field in numeric_fields:
            record[field] = _number(row.get(field))

        records.append(record)

    return tuple(records)


def list_districts() -> list[str]:
    return sorted({
        str(row["district"])
        for row in load_production()
        if row.get("district")
    })


def list_seasons() -> list[dict[str, Any]]:
    found = {}

    for row in load_production():
        key = (row.get("year"), row.get("season"))
        found[key] = row.get("season_period")

    return [
        {
            "year": year,
            "season": season,
            "season_period": period,
        }
        for (year, season), period in sorted(
            found.items(),
            key=lambda item: (
                item[0][0] or 0,
                item[0][1] or "",
            ),
        )
    ]


def list_crops() -> list[str]:
    return sorted({
        str(row["crop"])
        for row in load_production()
        if row.get("crop")
    })


def _inspect_dataset(
    path: Path,
    required_columns: set[str],
) -> dict[str, Any]:
    """Check CSV availability, schema, row widths and record count."""
    result: dict[str, Any] = {
        "available": path.is_file(),
        "records": None,
        "schema_valid": False,
        "missing_columns": [],
        "duplicate_columns": [],
        "rows_with_extra_fields": 0,
        "rows_with_missing_fields": 0,
    }

    if not result["available"]:
        result["error"] = "Required dataset file is missing."
        return result

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(
                file,
                restkey="__extra_fields__",
                restval=None,
            )
            headers = reader.fieldnames or []
            header_names = {
                name for name in headers
                if name is not None
            }
            missing = sorted(required_columns - header_names)
            duplicates = sorted(
                name for name, count in Counter(headers).items()
                if name is not None and count > 1
            )

            records = 0
            extra_rows = 0
            short_rows = 0

            for row in reader:
                records += 1

                if row.get("__extra_fields__") is not None:
                    extra_rows += 1

                if any(
                    row.get(name) is None
                    for name in headers
                    if name is not None
                ):
                    short_rows += 1

        result.update({
            "records": records,
            "missing_columns": missing,
            "duplicate_columns": duplicates,
            "rows_with_extra_fields": extra_rows,
            "rows_with_missing_fields": short_rows,
        })

        valid_headers = bool(headers) and all(
            name is not None and bool(name.strip())
            for name in headers
        )
        schema_valid = (
            valid_headers
            and not missing
            and not duplicates
            and extra_rows == 0
            and short_rows == 0
            and records > 0
        )
        result["schema_valid"] = schema_valid

        errors = []
        if not headers:
            errors.append("CSV header row is missing or empty.")
        elif not valid_headers:
            errors.append("CSV contains an empty column name.")
        if missing:
            errors.append(
                "Required columns are missing: " + ", ".join(missing)
            )
        if duplicates:
            errors.append(
                "Duplicate column names: " + ", ".join(duplicates)
            )
        if extra_rows:
            errors.append(f"{extra_rows} row(s) contain extra fields.")
        if short_rows:
            errors.append(f"{short_rows} row(s) have missing fields.")
        if records == 0:
            errors.append("Dataset contains no data records.")

        if errors:
            result["error"] = " ".join(errors)

    except (OSError, csv.Error, UnicodeError, ValueError) as exc:
        result["error"] = f"Could not inspect dataset: {exc}"

    return result


def data_status() -> dict[str, Any]:
    """Report dataset availability and basic CSV schema readiness."""
    production_columns = {
        "year",
        "season",
        "district",
        "crop",
        "production_mt",
        "source_value_status",
        "source_table",
        "source_page",
    }
    validation_columns = {
        "year",
        "season",
        "crop",
        "district_sum_mt",
        "published_national_mt",
        "difference_mt",
        "validation_status",
        "source_table",
        "source_page",
    }

    production = _inspect_dataset(PRODUCTION_FILE, production_columns)
    validation = _inspect_dataset(VALIDATION_FILE, validation_columns)

    result = {
        "source": DATA_SOURCE,
        "production_dataset": production,
        "validation_dataset": validation,
    }
    result["ready"] = all(
        dataset["available"] and dataset["schema_valid"]
        for dataset in (production, validation)
    )

    return result


def filter_production(
    *,
    district: str | None = None,
    season: str | None = None,
    crop: str | None = None,
    year: int | None = None,
) -> list[dict[str, Any]]:
    records = load_production()

    return [
        dict(row)
        for row in records
        if (district is None or row.get("district") == district)
        and (season is None or row.get("season") == season)
        and (crop is None or row.get("crop") == crop)
        and (year is None or row.get("year") == year)
    ]


def production_summaries(
    *,
    season: str | None = None,
    crop: str | None = None,
    year: int | None = None,
) -> list[dict[str, Any]]:
    """Summarize each crop separately; never add different crops together."""
    groups: dict[tuple[int, str, str], list[dict[str, Any]]] = {}

    for row in load_production():
        key = (row["year"], row["season"], row["crop"])

        if year is not None and row["year"] != year:
            continue
        if season is not None and row["season"] != season:
            continue
        if crop is not None and row["crop"] != crop:
            continue

        groups.setdefault(key, []).append(dict(row))

    validation_lookup = {
        (row["year"], row["season"], row["crop"]): row
        for row in load_validation()
    }

    expected_districts = len(list_districts())
    results = []

    for key, rows in groups.items():
        record_year, record_season, record_crop = key
        reported_values = [
            row["production_mt"]
            for row in rows
            if row["production_mt"] is not None
        ]

        validation = validation_lookup.get(key, {})
        reported_count = len(reported_values)

        results.append({
            "year": record_year,
            "season": record_season,
            "season_period": rows[0].get("season_period"),
            "crop": record_crop,
            "district_records": len(rows),
            "expected_districts_in_dataset": expected_districts,
            "reported_records": reported_count,
            "missing_production_records": len(rows) - reported_count,
            "district_coverage_percent": round(
                reported_count / expected_districts * 100, 2
            ) if expected_districts else None,
            "reported_district_sum_mt": round(sum(reported_values), 3),
            "published_national_mt": validation.get(
                "published_national_mt"
            ),
            "district_sum_mt_from_validation": validation.get(
                "district_sum_mt"
            ),
            "district_sum_completeness": validation.get(
                "district_sum_completeness"
            ),
            "district_missing_count": validation.get(
                "district_missing_count"
            ),
            "difference_mt": validation.get("difference_mt"),
            "validation_status": validation.get("validation_status"),
            "source": DATA_SOURCE,
            "source_table": validation.get(
                "source_table", rows[0].get("source_table")
            ),
            "source_page": validation.get(
                "source_page", rows[0].get("source_page")
            ),
            "interpretation_note": (
                "Reported district sum is a subtotal of available records, "
                "not necessarily a complete national total. Use the "
                "validation fields to assess completeness."
            ),
        })

    return sorted(
        results,
        key=lambda item: (
            item["year"],
            item["season"],
            item["crop"],
        ),
    )


def data_quality(
    *,
    season: str | None = None,
    crop: str | None = None,
) -> dict[str, Any]:
    rows = [
        dict(row)
        for row in load_validation()
        if (season is None or row.get("season") == season)
        and (crop is None or row.get("crop") == crop)
    ]

    counts: dict[str, int] = {}
    for row in rows:
        status = row.get("validation_status") or "UNSPECIFIED"
        counts[status] = counts.get(status, 0) + 1

    return {
        "source": DATA_SOURCE,
        "records_returned": len(rows),
        "status_counts": counts,
        "records": rows,
        "note": (
            "Validation statuses are data-quality diagnostics. "
            "They are not official agricultural risk classifications."
        ),
    }


def supply_origins(
    *,
    crop: str,
    season: str,
    year: int,
) -> dict[str, Any]:
    """Compare reported production across districts for one crop and season.

    Missing production values remain unranked. The reported subtotal is
    not assumed to represent current market availability.
    """
    rows = filter_production(crop=crop, season=season, year=year)
    expected_districts = len(list_districts())

    reported = [
        row for row in rows if row.get("production_mt") is not None
    ]
    missing = [
        row for row in rows if row.get("production_mt") is None
    ]

    reported.sort(
        key=lambda row: (
            -row["production_mt"],
            str(row.get("district") or ""),
        )
    )
    missing.sort(key=lambda row: str(row.get("district") or ""))

    districts = []
    for rank, row in enumerate(reported, start=1):
        districts.append({
            "rank": rank,
            "district": row.get("district"),
            "production_mt": row.get("production_mt"),
            "value_status": row.get("source_value_status"),
            "source": row.get("source"),
            "source_table": row.get("source_table"),
            "source_page": row.get("source_page"),
        })

    for row in missing:
        districts.append({
            "rank": None,
            "district": row.get("district"),
            "production_mt": None,
            "value_status": row.get("source_value_status") or "not_reported",
            "source": row.get("source"),
            "source_table": row.get("source_table"),
            "source_page": row.get("source_page"),
        })

    record_count = len(rows)
    reported_count = len(reported)
    missing_count = len(missing)

    return {
        "source": DATA_SOURCE,
        "filters": {
            "crop": crop,
            "season": season,
            "year": year,
            "season_period": (
                rows[0].get("season_period") if rows else None
            ),
        },
        "unit": "metric tonnes",
        "summary": {
            "district_records": record_count,
            "expected_districts_in_dataset": expected_districts,
            "reported_records": reported_count,
            "missing_production_records": missing_count,
            "district_coverage_percent": round(
                reported_count / expected_districts * 100, 2
            ) if expected_districts else None,
            "record_reporting_percent": round(
                reported_count / record_count * 100, 2
            ) if record_count else None,
            "reported_district_subtotal_mt": round(
                sum(row["production_mt"] for row in reported), 3
            ),
            "subtotal_is_complete": (
                record_count == expected_districts and missing_count == 0
            ),
        },
        "districts": districts,
        "interpretation_notes": [
            "Rankings include only districts with reported numeric values.",
            "Missing production is not treated as zero.",
            "Reported production describes the recorded season, not current "
            "stock, market availability, or a confirmed source for buyers.",
            "The reported district subtotal is not automatically a published "
            "national total.",
        ],
    }



def seasonal_comparison(
    *,
    year: int,
    crop: str | None = None,
) -> dict[str, Any]:
    """Compare one crop's reported production across seasons A, B and C."""
    summaries = production_summaries(year=year)

    seasons_order = ("A", "B", "C")
    crop_seasons: dict[str, set[str]] = {}

    for row in summaries:
        name = row.get("crop")
        season = row.get("season")
        if name and season:
            crop_seasons.setdefault(str(name), set()).add(str(season))

    available_crops = sorted(
        name for name, seasons in crop_seasons.items()
        if set(seasons_order).issubset(seasons)
    )

    result: dict[str, Any] = {
        "source": DATA_SOURCE,
        "year": year,
        "unit": "metric tonnes",
        "available_crops": available_crops,
        "selected_crop": crop,
        "eligible": crop is None or crop in available_crops,
        "seasons": [],
        "interpretation_notes": [
            "Each season is a distinct agricultural period, not a direct "
            "year-over-year trend.",
            "Reported district subtotals may be incomplete and are not "
            "automatically published national totals.",
            "Missing production values are not treated as zero.",
            "Historical production does not indicate current stock, market "
            "availability, or a live forecast.",
        ],
    }

    if crop is None or crop not in available_crops:
        return result

    summaries_by_season = {
        row["season"]: row
        for row in summaries
        if row.get("crop") == crop
    }

    for season in seasons_order:
        row = summaries_by_season.get(season)
        if row is None:
            continue

        result["seasons"].append({
            "season": season,
            "season_period": row.get("season_period"),
            "reported_district_subtotal_mt": row.get(
                "reported_district_sum_mt"
            ),
            "reported_districts": row.get("reported_records"),
            "expected_districts": row.get(
                "expected_districts_in_dataset"
            ),
            "missing_districts": row.get(
                "missing_production_records"
            ),
            "district_coverage_percent": row.get(
                "district_coverage_percent"
            ),
            "published_national_mt": row.get("published_national_mt"),
            "validation_status": row.get("validation_status"),
            "source_table": row.get("source_table"),
            "source_page": row.get("source_page"),
        })

    return result
