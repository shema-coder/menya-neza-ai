MENYA NEZA AI
From Data to Early Action
MENYA NEZA AI is a Rwanda-focused agricultural data intelligence prototype built to make important agricultural statistics easier to find, understand, and verify. It bridges the gap between valuable data and the people who need to use it by letting users ask questions naturally, explore district-level production, compare seasons, inspect market-price observations, and review data-quality limitations.
Important: This is an independently developed prototype for the NISR 2026 Big Data Hackathon. It is not an official NISR application and does not provide validated disaster predictions, live weather forecasts, or official emergency warnings.

Project links
- Live application: https://menya-neza-ai-frontend-nxsc.vercel.app/
- Demo video (YouTube): https://youtu.be/zblJ9MmKIsw
- Full public source repository: https://github.com/shema-coder/menya-neza-ai
- Backend health endpoint: https://menya-neza-ai-api.onrender.com/health
- Backend API documentation: https://menya-neza-ai-api.onrender.com/docs
The problem
Rwanda has valuable statistical information about agriculture, but a citizen may not know which report, table, or page contains the answer to a particular question. Finding the relevant figures and interpreting their time period, completeness, and limitations can take time.

MENYA NEZA AI makes the available evidence more accessible. Users can start with a question or explore the information through district, season, crop, market, and data-quality views.
What the application provides
Ask MENYA NEZA AI
Ask supported agricultural-data questions in English or Kinyarwanda without needing to know the report or table in advance. Responses are grounded in the datasets available to the application and can include supporting source records. When the evidence is unavailable or cannot support a claim, the system should explain the limitation rather than invent a figure.
Check My Area
Select a Rwandan district and agricultural season to inspect historical crop-production observations, reported values, and missing data for that selection.
Insights and Data Quality & Sources
Review dataset coverage, missing records, and project validation checks. These checks are diagnostics produced by this project; they are not official NISR classifications.
Seasonal Comparison
Compare reported crop-production figures across Seasons A, B, and C of the 2025 survey, where the available data supports the comparison.
Supply Origins
Explore and compare reported crop-production values for districts and selected seasons. A sum of reported district values is labelled as a subtotal and must not automatically be interpreted as the official national total.
Market Intelligence
Explore available price observations and source-provided monthly price summaries alongside historical production evidence. These sources are presented separately because they have different dates, coverage, and limitations. The application does not claim that a change in production caused a change in price.
Data sources and limitations
1. NISR Seasonal Agricultural Survey (SAS) 2025
- Source report: NISR Seasonal Agricultural Survey 2025 — Final Report (PDF)
- Used for historical crop-production records and project data-quality checks.
- Survey seasons are labelled as follows:
  - Season A: September 2024–February 2025
  - Season B: March–June 2025
  - Season C: July–September 2025
- The current extract contains 1,650 records across districts, crops, and seasons.
- Missing or dash-valued records are not automatically converted to zero. Some crop categories may overlap with component categories, so values should not be added together unless the source supports doing so.
- The data describes the survey period. It does not establish current crop stocks, current market availability, household food sufficiency, weather conditions, or future harvests.
2. Esoko Rwanda price observations
- Source: Esoko Rwanda
- The application uses a manually imported snapshot, not a live Esoko API connection or live scraping.
- The repository documentation records 908 source rows observed on 26–27 October 2026.
- The imported export does not contain all location and unit fields needed for complete comparisons. Missing fields remain unknown rather than being inferred.
- Observations are dated source records and should not be presented as guaranteed current prices.
3. TangaBid monthly price-trend summaries
- Dataset file: data/raw/tangabid/tangabid_six_month_price_trends.csv
- The application presents source-provided monthly summaries for April–October 2026; October may be incomplete.
- Currency, precise price type, collection methodology, and the meaning of source-reported sample counts have not been independently verified.
- These records are monthly summaries, not live quotations or forecasts. Markets, sellers, sampling methods, and units may not be comparable between records. Do not add or compare values across different units without a valid conversion and supporting methodology.
Responsible data use
MENYA NEZA AI is built around evidence, transparency, and honest uncertainty:
- Historical survey observations are clearly distinguished from current conditions.
- Missing values stay unknown and are not silently changed to zero.
- Source records and known limitations are shown where available.
- District subtotals are not automatically labelled national totals.
- Price summaries are not presented as verified live prices when their source limitations do not support that claim.
- The platform does not currently provide validated disaster-risk predictions, live weather data, or official alerts. For current emergencies, consult the relevant official authorities.
Technology
- Frontend: React and Vite
- Backend: Python and FastAPI
- API: JSON endpoints under /api/v1
- Testing: pytest for backend tests; Vite production build for frontend checks
- Hosting: Vercel frontend and Render backend
Run locally
Requirements
Install Python 3.12 or a compatible supported Python version, Node.js, and npm.
1. Install backend dependencies
From the repository root:
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
2. Start the backend
In one terminal, from the repository root:
.venv/bin/python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
The API health endpoint will be available at http://localhost:8000/health, and interactive API documentation at http://localhost:8000/docs.
3. Start the frontend
In a second terminal:
cd frontend
npm install
npm run dev
Open the local Vite URL shown in the terminal, normally http://localhost:5173. The Vite development configuration proxies /api requests to the local FastAPI service on port 8000.

For a separate frontend deployment, set the Vite environment variable VITE_API_BASE_URL to the backend base URL, for example https://menya-neza-ai-api.onrender.com. Configure the backend's MENYA_NEZA_CORS_ORIGINS environment variable with the exact allowed frontend origin(s).
Run checks
From the repository root:
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend run build
Main API routes
- GET /health — backend health and dataset status
- GET /api/v1/production — filtered historical production records
- GET /api/v1/production/summary — production summaries
- GET /api/v1/production/seasonal-comparison — seasonal comparison
- GET /api/v1/supply/origins — district production comparison
- GET /api/v1/data-quality — data-quality diagnostics
- GET /api/v1/intelligence/supply-price — production evidence and price-source status
- GET /api/v1/market-prices/esoko-observations — imported Esoko observations
- GET /api/v1/market-prices/trends — TangaBid source-provided monthly summaries
- POST /api/v1/ask — evidence-grounded question answering
See the live API documentation for parameters and response schemas.
Team
- Team lead: Shema Aime Pacifique
- Team member: Niyonkuru Pierre
AI-use and project responsibility
AI assistance was used during parts of development, debugging, and documentation. The project team remains responsible for reviewing the implementation, testing its behaviour, verifying data claims, and clearly communicating limitations.
Demo
Watch the walkthrough: MENYA NEZA AI — NISR 2026 Big Data Hackathon.
MENYA NEZA AI — From Data to Early Action.
