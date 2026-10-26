# MENYA NEZA AI — Data Sources

## Purpose

This document records the verified data sources considered for
MENYA NEZA AI.

The project prioritizes official Rwanda data, especially data from
the National Institute of Statistics of Rwanda (NISR), together with
other reliable public sources where appropriate.

## Priority

### Primary

- NISR
- Official Rwanda government institutions
- Official administrative data

### Secondary

- Reputable public climate and weather sources
- Reputable disaster-related sources
- Reputable agriculture and food datasets
- Geographic and geospatial public datasets

## Data Selection Principles

A dataset should be evaluated for:

1. Reliability
2. Relevance
3. Geographic coverage
4. Time coverage
5. Frequency
6. Variables available
7. Accessibility
8. License or usage conditions
9. Data quality
10. Limitations

## Dataset Registry

All datasets used or considered by MENYA NEZA AI should be recorded
in:

`data/metadata/dataset_registry.csv`

### Dataset Status Definitions

The `status` column in `data/metadata/dataset_registry.csv` describes
how a dataset is currently used or what validation remains.

- `integrated_historical_baseline`: integrated into the application for
  historical analysis. This does not mean the data is live, every variable
  has been independently validated, or the dataset supports forecasting.
- `identified_needs_validation`: a source has been identified, but its
  data structure, methodology, coverage, access conditions, or suitability
  still needs to be checked before integration.

These labels describe project readiness, not a guarantee that the source
is accurate for every intended use. Dataset-specific limitations remain
binding. In particular, estimated gridded rainfall is not a direct station
observation, and historical survey results are not real-time measurements.

## Important Rule

MENYA NEZA AI must not present invented data as real Rwanda data.

Every important indicator displayed to users should be traceable to
a documented source.

## Domains

The initial data architecture covers:

- Agriculture
- Food
- Disasters

## Geographic Standardization

Where possible, datasets should be aligned using common Rwanda
administrative geographic references:

- Province
- District
- Sector

Coordinates and geographic boundaries may also be used where available.

## Time Standardization

Datasets may have different frequencies:

- Daily
- Weekly
- Monthly
- Seasonal
- Annual

The preprocessing pipeline must document how observations are
aggregated or aligned across different time scales.

## Data Limitations

Missing values, different geographic boundaries, changes in collection
methods, inconsistent time periods, measurement uncertainty, and other
quality issues must be documented before using a dataset for modelling.

## NISR SAS 2025 Crop Production: Validation Notes

Source: National Institute of Statistics of Rwanda (NISR),
Seasonal Agricultural Survey 2025, Table 26,
"2025 Season C — Crop production by crop type and district (MT)",
printed report page 62.

- The published national total for Season C vegetables is 67,626 MT.
- The sum of the 30 district values extracted from the table is 67,621 MT.
- The difference (district sum minus published national total) is -5 MT.
- All 30 district vegetable values are reported; this discrepancy is
  not explained by missing district values.
- Preserve the published national total and district observations as
  recorded in the source. Do not silently adjust individual values.
- Mark this discrepancy for review and retain the source table and page
  references for traceability.

### Missing Values and Category Relationships

A dash (`-`) in the source table is recorded as not reported, not as zero.
Its precise statistical meaning should be confirmed before analysis.

Some crop labels represent related categories, such as Beans, Bush bean,
and Climbing bean. Do not add parent and subcategory totals together
unless the source definitions confirm that doing so is appropriate.

### Validation Status

The extraction script compares district sums with published national
totals and flags missing district values or differences for review.
A successful extraction does not establish that every value is correct.
The dataset remains subject to source verification before it is used
for risk scoring, public warnings, or decision-making.

## Agricultural Supply & Price Intelligence

The registry at `data/metadata/market_price_source_registry.csv` records
candidate sources and their current review/integration status. A listed
source is not necessarily integrated, licensed for reuse, or a live feed.

NISR SAS production figures support historical production analysis. NISR
survey metadata also documents farmer-reported selling-price questions for
some survey rounds; these must be validated against the underlying data and
must not be treated as current retail or wholesale prices.

FAO GIEWS country briefs can provide dated retail-price context, but report
observations are not automatically a current price feed. WFP market-functionality
indicators are not commodity prices. NISR producer-price indices are indices,
not direct market quotes.

Before publication, record the price type, commodity, unit, currency,
location, observation/reference date, source, coverage, access conditions,
and limitations. Unknown values remain unknown. Historical production does
not establish current stocks or market availability.


### TangaBid Monthly Price Trends

MENYA NEZA AI includes a TangaBid-provided monthly price-trend export
for exploratory, source-traceable analysis.

- Canonical data: `data/raw/tangabid/tangabid_six_month_price_trends.csv`
- Automated audit: `scripts/audit_tangabid_prices.py`
- Audit output: `data/metadata/tangabid_price_trends_quality.json`
- API endpoint: `/api/v1/market-prices/trends`

The dataset contains source-reported monthly summaries. Currency,
collection methodology, exact price type, sample-count meaning, and
sampling consistency across months have not been independently verified.
October 2026 may be incomplete.

The application must not label these observations as official or live
prices, generate forecasts from them, or compare records with different
units. Dataset inclusion does not establish source endorsement or
independent validation. See the TangaBid section of the data-quality
report before using these observations for decisions.
