"""Evidence-first agricultural supply and price intelligence.

This service combines existing SAS production evidence with market-source
readiness and NST2 reference context. It does not invent prices or forecasts.
"""

import csv
from pathlib import Path
from typing import Any

from . import agriculture


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PRICE_REGISTRY = (
    PROJECT_ROOT / "data" / "metadata" / "market_price_source_registry.csv"
)

SOURCE = "NISR Seasonal Agricultural Survey 2025"

# These are reference values, not proof of NST2 achievement.
# Do not calculate progress until the official reporting periods, indicator
# definitions, and units have been verified against the complete source.
NST2_REFERENCES: dict[str, dict[str, Any]] = {
    "Maize": {
        "reference_crop_label": "Maize",
        "production_mt": {
            "baseline": 508492,
            "mid_term_target": 665701,
            "end_term_target": 874337,
            "unit": "metric tonnes",
        },
        "productivity_mt_per_ha": {
            "baseline": 1.7,
            "mid_term_target": 2.26,
            "end_term_target": 2.74,
            "unit": "metric tonnes per hectare",
        },
    },
    "Beans": {
        "reference_crop_label": "Beans",
        "production_mt": {
            "baseline": 441406,
            "mid_term_target": 565009,
            "end_term_target": 662115,
            "unit": "metric tonnes",
        },
        "productivity_mt_per_ha": {
            "baseline": 0.6,
            "mid_term_target": 1.3,
            "end_term_target": 1.5,
            "unit": "metric tonnes per hectare",
        },
    },
    "Rice": {
        "reference_crop_label": "Rice",
        "production_mt": {
            "baseline": 133628,
            "mid_term_target": 240073,
            "end_term_target": 293178,
            "unit": "metric tonnes",
        },
        "productivity_mt_per_ha": {
            "baseline": 4.0,
            "mid_term_target": 4.8,
            "end_term_target": 5.4,
            "unit": "metric tonnes per hectare",
        },
    },
    "Irish potatoes": {
        "reference_crop_label": "Irish potatoes",
        "production_mt": {
            "baseline": 781032,
            "mid_term_target": 1144425,
            "end_term_target": 1498545,
            "unit": "metric tonnes",
        },
        "productivity_mt_per_ha": {
            "baseline": 8.2,
            "mid_term_target": 11.4,
            "end_term_target": 14.7,
            "unit": "metric tonnes per hectare",
        },
    },
    "Wheat": {
        "reference_crop_label": "Wheat",
        "production_mt": {
            "baseline": 16656,
            "mid_term_target": 22169,
            "end_term_target": 26825,
            "unit": "metric tonnes",
        },
        "productivity_mt_per_ha": {
            "baseline": 1.2,
            "mid_term_target": 1.38,
            "end_term_target": 1.48,
            "unit": "metric tonnes per hectare",
        },
    },
    "Soybean": {
        "reference_crop_label": "Soybean",
        "production_mt": {
            "baseline": 29059,
            "mid_term_target": 53019,
            "end_term_target": 64152,
            "unit": "metric tonnes",
        },
        "productivity_mt_per_ha": {
            "baseline": 0.4,
            "mid_term_target": 1.1,
            "end_term_target": 1.4,
            "unit": "metric tonnes per hectare",
        },
    },
    "Cassava": {
        "reference_crop_label": "Cassava",
        "production_mt": {
            "baseline": 1345379,
            "mid_term_target": 1567734,
            "end_term_target": 1653924,
            "unit": "metric tonnes",
        },
        "productivity_mt_per_ha": {
            "baseline": 13.5,
            "mid_term_target": 16.5,
            "end_term_target": 17.9,
            "unit": "metric tonnes per hectare",
        },
    },
    "Cooking banana": {
        "reference_crop_label": "Cooking banana",
        "production_mt": {
            "baseline": 1049838,
            "mid_term_target": 1274919,
            "end_term_target": 1424973,
            "unit": "metric tonnes",
        },
        "productivity_mt_per_ha": {
            "baseline": 14.2,
            "mid_term_target": 17.9,
            "end_term_target": 19.7,
            "unit": "metric tonnes per hectare",
        },
    },
}


def _read_price_registry() -> list[dict[str, str]]:
    """Read source leads without treating them as integrated price data."""
    if not PRICE_REGISTRY.is_file():
        return []

    with PRICE_REGISTRY.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        return [
            dict(row)
            for row in csv.DictReader(file)
            if row.get("source_id")
        ]


def _public_registry_summary() -> list[dict[str, Any]]:
    """Expose useful provenance while keeping registry status explicit."""
    fields = (
        "source_id",
        "organization",
        "dataset_or_product",
        "measure_type",
        "unit_or_measure",
        "time_character",
        "integration_status",
        "source_url",
        "limitations",
    )

    return [
        {field: row.get(field, "") for field in fields}
        for row in _read_price_registry()
    ]


def supply_price_report(
    *,
    crop: str,
    season: str,
    year: int,
    district: str | None = None,
) -> dict[str, Any]:
    """Return one traceable report without inventing prices or forecasts."""
    summaries = agriculture.production_summaries(
        crop=crop,
        season=season,
        year=year,
    )
    summary = summaries[0] if summaries else None

    origin_report = agriculture.supply_origins(
        crop=crop,
        season=season,
        year=year,
    )

    district_record = None
    if district is not None:
        matches = agriculture.filter_production(
            crop=crop,
            season=season,
            year=year,
            district=district,
        )
        if matches:
            row = matches[0]
            district_record = {
                "district": row.get("district"),
                "production_mt": row.get("production_mt"),
                "value_status": row.get("source_value_status"),
                "source": row.get("source", SOURCE),
                "source_table": row.get("source_table"),
                "source_page": row.get("source_page"),
                "interpretation": (
                    "Historical survey production for the selected district "
                    "and season. It is not a measure of current stock or "
                    "market availability."
                ),
            }
        else:
            district_record = {
                "district": district,
                "production_mt": None,
                "value_status": "NO_MATCHING_RECORD",
                "source": SOURCE,
                "source_table": None,
                "source_page": None,
                "interpretation": (
                    "No matching district observation was found. "
                    "This must not be interpreted as zero production."
                ),
            }

    registry = _public_registry_summary()
    nst2_reference = NST2_REFERENCES.get(crop)

    production_available = summary is not None
    reported_count = (
        summary.get("reported_records", 0) if summary else 0
    )
    missing_count = (
        summary.get("missing_production_records", 0) if summary else 0
    )

    selected_production = (district_record or {}).get("production_mt")

    situation_summary = {
        "status": (
            "HISTORICAL_EVIDENCE_AVAILABLE"
            if production_available
            else "INSUFFICIENT_MATCHING_EVIDENCE"
        ),
        "scope": {
            "district": district,
            "crop": crop,
            "season": season,
            "year": year,
            "season_period": summary.get("season_period") if summary else None,
        },
        "observed": {
            "selected_district_production_mt": selected_production,
            "reported_district_records": reported_count,
            "missing_production_records": missing_count,
            "district_coverage_percent": (
                summary.get("district_coverage_percent") if summary else None
            ),
            "validation_status": (
                summary.get("validation_status") if summary else None
            ),
        },
        "connected_evidence": {
            "historical_nisr_production": production_available,
            "historical_supply_origins": bool(
                origin_report.get("districts")
            ),
            "verified_market_price_observations": False,
            "validated_live_disaster_warnings": False,
        },
        "unknowns": [
            "Current food stocks and local food availability are not established by historical production.",
            "No verified market-price observations are connected to this report.",
            "This report does not provide validated live weather or disaster warnings.",
        ],
        "recommended_next_actions": [
            "Review source validation and missing-district coverage before comparing seasonal totals.",
            "Check a verified, dated local market-price source before drawing conclusions about current prices.",
            "Consult official weather and disaster authorities for current alerts.",
        ],
        "interpretation": (
            "This summary connects available historical evidence and its limits. "
            "It does not establish current food availability, cause-and-effect "
            "between production and prices, or current disaster risk."
        ),
    }

    return {
        "source": SOURCE,
        "situation_summary": situation_summary,
        "filters": {
            "crop": crop,
            "season": season,
            "year": year,
            "district": district,
            "season_period": (
                summary.get("season_period") if summary else None
            ),
        },
        "production_evidence": {
            "available": production_available,
            "summary": summary,
            "district_coverage_percent": (
                summary.get("district_coverage_percent")
                if summary else None
            ),
            "reported_records": reported_count,
            "missing_production_records": missing_count,
            "supply_origins": {
                "summary": origin_report.get("summary", {}),
                "leading_reported_districts": [
                    row
                    for row in origin_report.get("districts", [])
                    if row.get("production_mt") is not None
                ][:5],
            },
            "interpretation": (
                "Reported seasonal production is historical evidence. "
                "It does not establish current stocks, current market "
                "availability, or the quantity available for purchase."
            ),
        },
        "selected_district_evidence": district_record,
        "evidence_assessment": {
            "status": (
                "HISTORICAL_PRODUCTION_AVAILABLE"
                if production_available
                else "NO_MATCHING_PRODUCTION_SUMMARY"
            ),
            "reported_district_records": reported_count,
            "missing_production_records": missing_count,
            "validation_status": (
                summary.get("validation_status") if summary else None
            ),
            "caution": (
                "Assess district coverage and source validation before "
                "interpreting the reported subtotal as representative."
            ),
        },
        "market_price_intelligence": {
            "verified_price_feed_connected": False,
            "observations_available": False,
            "status": "NO_VERIFIED_PRICE_OBSERVATIONS_CONNECTED",
            "price_observations": [],
            "source_registry": registry,
            "message": (
                "No verified market-price observations are connected. "
                "Registry entries are research leads, not price data. "
                "No current price is available from this report."
            ),
            "required_before_price_publication": [
                "Verified crop identity",
                "Actual price observation and currency",
                "Unit and quantity basis",
                "Price type: farm-gate, wholesale, or retail",
                "Market or geographic location",
                "Observation date or survey reference period",
                "Source provenance and access permission",
                "Missingness, outlier, and coverage checks",
            ],
        },
        "nst2_alignment": {
            "reference_indicators": nst2_reference or {},
            "reference_available_for_exact_crop_label": (
                nst2_reference is not None
            ),
            "target_comparison_status": (
                "NOT_COMPUTED_PERIOD_AND_DEFINITION_CHECK_REQUIRED"
            ),
            "note": (
                "Reference values are not achievements or calculated "
                "progress. Verify the official NST2 indicator definitions, "
                "crop labels, units, baseline, and reporting periods before "
                "making a formal comparison. No target is inferred for an "
                "unmatched crop label."
            ),
        },
        "price_movement_assessment": {
            "status": "INSUFFICIENT_VERIFIED_PRICE_EVIDENCE",
            "forecast_produced": False,
            "observed_price_change": None,
            "estimated_price_change": None,
            "causal_conclusion": None,
            "message": (
                "Price movement cannot be assessed without verified, "
                "dated price observations. Production data alone cannot "
                "establish that prices will rise or fall."
            ),
            "factors_to_investigate": [
                "Recent harvest and production evidence",
                "Verified market prices over comparable dates",
                "Transport and transaction costs",
                "Demand and cross-border trade",
                "Weather, crop disease, and supply disruptions",
                "Market functionality and access",
            ],
        },
        "recommended_next_actions": [
            "Review production coverage and validation for the selected crop.",
            "Verify and obtain authorized source price observations.",
            "Check crop definitions, units, locations, and reference dates.",
            "Compare only compatible observations and report uncertainty.",
            "Verify NST2 indicator definitions before calculating progress.",
        ],
    }
