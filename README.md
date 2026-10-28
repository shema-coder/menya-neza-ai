# MENYA NEZA AI

## From Data to Early Action

MENYA NEZA AI is a citizen-first, data-driven early-warning platform
focused on Agriculture, Food, and Disasters in Rwanda.

The platform combines relevant data to identify unusual patterns,
explain why they matter, and communicate understandable early-warning
signals to citizens, farmers, government institutions, NGOs, researchers,
and planners.

## Core Relationship

DISASTER → AGRICULTURE → FOOD → PEOPLE

## Core Pipeline

DATA → DETECT → EXPLAIN → WARN → PREPARE → ACT

## Main Principle

60% Citizen Benefit + 40% Institutional Benefit

## Main Citizen Feature

CHECK MY AREA

Citizens should be able to select their district and understand:

- What is happening?
- Why is the system concerned?
- What changed compared with normal?
- How confident is the signal?
- What should I monitor or prepare for?

## Focus Areas

- Agriculture
- Food
- Disasters

## Responsible AI

MENYA NEZA AI provides data-driven early-warning signals.
It does not replace official government warnings, emergency authorities,
or professional decision-making.

## Project Status

Version 0.2.0 — working prototype.

The project includes a FastAPI backend, a React/Vite frontend,
historical NISR SAS 2025 crop-production data, source traceability,
data-quality diagnostics, and automated backend/API tests.

The current prototype does not provide validated disaster-risk
predictions, live weather, or official warnings.

Run backend tests from the repository root with:

`.venv/bin/python -m pytest backend/tests/ -v`

Build the frontend from the `frontend` directory with:

`npm run build`

## Esoko Rwanda market-price source

- Source: [Esoko Rwanda eSoko Price Trends](https://esoko.rw/price-trends).
- Imported snapshot: `data/processed/esoko_market_price_observations.csv` (908 source rows, observed 26–27 October 2026).
- API: `/api/v1/market-prices/esoko/status` and `/api/v1/market-prices/esoko-observations`.
- Ask AI uses exact product/market observations where matched; TangaBid monthly summaries remain separate. This is a manual snapshot, not live scraping.
- Important limitation: this export does not include unit, province, or district columns. Missing prices remain missing and are never converted to zero.
