# Esoko Rwanda Market-Price Source

- **Source:** Esoko Rwanda eSoko Price Trends
- **URL:** https://esoko.rw/price-trends
- **Import type:** Manually exported CSV snapshot, not a live API integration.
- **Raw export:** `data/raw/esoko/esoko_price_trends_export.csv`
- **Normalized observations:** `data/processed/esoko_market_price_observations.csv`
- **Price fields:** farmgate, wholesale and retail. Dashes/blanks are missing values, never zero.
- **Currency:** RWF is supported by published descriptions of Esoko data, but it is not a column in this particular export.
- **Units:** The supplied CSV has no per-product unit column. Do not label these observations as per kg, litre, piece, etc. unless units are independently joined from a verified source.
- **Geography:** The exported Province and District columns are blank for all 908 source rows. `Markets` is the only supplied location field.
- **Snapshot dates:** observations run from 26 October 2026 through 27 October 2026 (timezone offset +02:00 retained).
- **Source quality:** 908 source rows; 101 distinct product labels; 25 distinct market labels; two missing farmgate values; two pairs of exact duplicate rows. The source rows are retained in the normalized file for traceability.
- **Interpretation:** latest observation in the file is not a guaranteed live price. This integration does not scrape the site and does not automatically refresh. Download a new export and replace the source data through the same guarded process to refresh.
- **API:** `GET /api/v1/market-prices/esoko/status` and `GET /api/v1/market-prices/esoko-observations`.
- **Ask AI:** when a product and market map to a specific observation, the assistant can report the observed price tiers and timestamp with unit/source caveats. If product/market matching is ambiguous, it should ask for clarification or fall back to the existing TangaBid monthly service.

## Provenance note

Published research describes Esoko as a Rwanda market-price source, with prices reported in Rwandan francs and price observations for food items often recorded per kilogram or litre. That does **not** establish the unit for each row in this specific CSV, so the integration explicitly leaves unit blank. References include:

- Esoko Price Trends: https://esoko.rw/price-trends
- ScienceDirect, *Cost and affordability of recommended diets in Rwanda using [near] real-time market data*: https://www.sciencedirect.com/science/article/abs/pii/S0306919226000527
- eSoko/Rwanda Food Price Monitor context: https://ssa.foodsecurityportal.org/node/1833/
