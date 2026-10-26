# MENYA NEZA AI — Data Quality Report

## 1. Purpose

This report records data completeness and reconciliation checks
performed on crop production values transcribed from the NISR
Seasonal Agricultural Survey (SAS) 2025 report.

These are data-quality checks, not agricultural risk predictions
or official disaster warnings.

## 2. Source and Coverage

- Source institution: National Institute of Statistics of Rwanda (NISR)
- Source: Seasonal Agricultural Survey 2025
- Table: 26 — 2025 Season C crop production by crop type and district
- Printed report page: 62
- Season C period: July–September 2025
- Geographic coverage: 30 Rwanda districts
- Unit: Metric tonnes (MT)
- Processed district-level production records: 1,650 across Seasons A, B, and C

## 3. Season C Completeness

| Crop | Missing district values | Completeness |
|---|---:|---|
| Sweet potatoes | 0 | Complete |
| Irish potatoes | 4 | Partial |
| Beans | 8 | Partial |
| Bush bean | 9 | Partial |
| Climbing bean | 25 | Partial |
| Peas | 13 | Partial |
| Soya beans | 16 | Partial |
| Groundnut | 25 | Partial |
| Vegetables | 0 | Complete |

A dash in the source table is recorded as a blank production value.
It must not automatically be interpreted as zero. Its statistical
meaning should be confirmed from the source documentation.

## 4. District-to-National Reconciliation

| Crop | District sum (MT) | Published national total (MT) | Difference (MT) |
|---|---:|---:|---:|
| Sweet potatoes | 41,288 | 41,289 | -1 |
| Vegetables | 67,621 | 67,626 | -5 |

Difference is calculated as district sum minus published national total.

Both comparisons include all 30 reported district values, but their
differences require review. Preserve the original observations and
published national totals. Do not silently modify values to force a match.

For the seven crop categories with missing district observations,
district-to-national differences are not calculated because the
district sums are incomplete.

## 5. Data Integrity Rules

1. Preserve source values and record their source table and page.
2. Do not replace missing values with zero without verified justification.
3. Do not combine parent and subcategory totals unless source definitions
   establish that the categories do not overlap.
4. Do not calculate a complete district total from partial observations
   without clearly labelling it as partial.
5. Keep published national totals separate from district-level records
   used for geographic analysis.
6. Investigate discrepancies before relying on the affected values.

## 6. Implications for MENYA NEZA AI

Crop production data can help describe agricultural patterns, but
production statistics alone do not establish that a flood, drought,
food shortage, or other disaster will occur.

Any future risk indicator must use relevant evidence, documented
baselines, an explicit analysis period, and appropriate validation.
Incomplete or unverified data must be disclosed to users.

Warnings must communicate signals and uncertainty rather than claim
that a disaster will definitely happen.

## 7. Follow-up Actions

- Verify the meaning of dash entries in the original SAS documentation.
- Review the two national-total discrepancies against the source report.
- Preserve and document missing observations.
- Confirm relationships between parent crop categories and their
  subcategories before aggregating them.
- Validate any future indicators against suitable historical evidence
  before displaying them as warnings.


## 8. TangaBid Monthly Price-Trend Dataset

### Source and Coverage

- Source description: TangaBid-provided monthly price-trend dataset.
- Canonical file: `data/raw/tangabid/tangabid_six_month_price_trends.csv`
- Audit report: `data/metadata/tangabid_price_trends_quality.json`
- Records: 6,765.
- Coverage: April–October 2026, across seven calendar months.
- Products: 122.
- Locations: 47.
- Case-insensitive region labels: 26.
- Units: Kg, Bottle, Litre, Piece, and Sack.

The October 2026 observations may be incomplete because the dataset
was inspected on 22 October 2026.

### Structural Validation

The audit found no duplicate month/product/unit/location keys,
invalid dates, invalid or nonpositive prices, invalid min/average/max
relationships, invalid sample counts, or empty required fields.

The duplicate export is byte-identical to the canonical CSV. The audit
report records the canonical file's SHA-256 digest for reproducibility.

One region-label inconsistency was identified: `KICUKIRO` and
`Kicukiro`. They are equivalent under case-insensitive comparison, but
the source labels should be preserved until normalization rules are
documented.

### Limitations and Permitted Use

The source currency, collection methodology, exact price type, and
meaning of sample counts have not been independently verified.
Consistency of markets, sellers, and sampling methods across months is
also unverified. Apparent month-to-month price changes may therefore
reflect differences in the sampled records as well as price changes.

These observations must not be described as official, live, or forecast
prices. Different units must not be compared or combined. Do not infer
national market conditions from the dataset without assessing its
geographic and sampling coverage.

Before using these observations to support public decisions, verify
the currency, price type, collection dates, locations, sample-count
definition, and comparability across months with the data provider.
