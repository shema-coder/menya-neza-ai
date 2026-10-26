# Agricultural Supply & Price Intelligence

## Purpose

Extend MENYA NEZA AI with traceable agricultural market evidence while
preserving the existing NISR crop-production and Supply Origins features.

## Current implementation status

- Historical crop production: available through the existing SAS 2025 extract.
- District supply origins: available through the existing API and frontend.
- Verified market-price feed: not yet integrated.
- Current market stock or supplier inventory: not established by the current
  production dataset.
- Automated external price ingestion: not implemented.

## Source registry

Review `data/metadata/market_price_source_registry.csv` before integrating
a dataset. A registry entry is a research lead, not proof that the data is
licensed, downloadable, complete, current, or suitable for publication.

## Price concepts must remain distinct

1. Farm-gate selling price: a survey-reported price received by a farmer.
2. Wholesale price: a price observed at a wholesale market.
3. Retail price: a price observed at a retail market.
4. Producer Price Index: an index, not a direct commodity quote.
5. Market functionality: an assessment indicator, not a price.

Do not combine these measures without clear labels and a defensible method.

## Minimum observation fields before publication

- Commodity and verified commodity identity
- Observation value and currency
- Unit and quantity basis
- Price type (farm-gate, wholesale, or retail)
- Market/location and geographic reference where available
- Observation date or survey reference period
- Source organization and source record/document
- Collection or publication date, if known
- Data status, missingness, and validation notes
- Access and usage conditions

Do not infer a missing observation date, market, unit, or price type.

## Freshness and interpretation

Show the actual observation date. If it is unknown, say so. If the record
is old, label it historical; do not silently present it as today's price.
Missing prices are unknown, not zero. A price difference between locations
is not automatically a profitable trading opportunity: transport, quality,
transaction costs, and market access may differ.

Historical crop production is not current stock, retail supply, or proof
of price causation. A relationship between harvests and prices should be
described as an association unless a suitable analysis supports stronger
claims.

## NST2 and NISR alignment

Use NISR survey definitions and documented source values. For NST2 progress,
verify the official indicator, baseline, target, and reporting period before
calculating progress. Production volume, yield, farm-gate price, retail price,
and price indices are different measures and must not be substituted for
one another.

## Incremental implementation gates

1. Verify the candidate source variables, access permissions, definitions,
   and geographic/time coverage.
2. Obtain a documented dataset or approved feed.
3. Profile missing values, units, duplicates, dates, outliers, and coverage.
4. Implement a source-specific parser and tests before exposing prices.
5. Add an API and interface only after real observations pass validation.
6. Display provenance, observation date, price type, and limitations.

Until those gates are met, the application must clearly report that no
verified market-price feed is connected rather than inventing prices.

## SAS 2025 questionnaire verification

The official NISR Plot Questionnaire for the 2024/2025 SAS confirms:
- Q2.27 asks which market the crop was sold in.
- Q2.28 asks the selling price per kilogram in RWF/kg and instructs the
  enumerator to report the farm-gate price.

Official source:
https://microdata.statistics.gov.rw/index.php/catalog/124

Verification boundary: this confirms the questionnaire fields, not the
mapping to columns in the released microdata. Before calculating or publishing
prices, identify the corresponding variables for each season, inspect valid
and missing cases and extreme values, confirm market and crop identifiers,
review survey weights/design, and check microdata access and usage conditions.

Status remains RESEARCH_ONLY. No price observations or current prices have
been added to MENYA NEZA AI.
