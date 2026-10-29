MENYA NEZA AI
From Data to Early Action
MENYA NEZA AI is a Rwanda-focused, citizen-first agricultural data intelligence prototype. It helps people find, explore, and understand available agricultural evidence without needing to know the exact report, table, or page where information is published.

The project focuses on making historical crop-production statistics, selected market-price observations, and data-quality limitations easier to inspect. It is an independently developed prototype for the NISR 2026 Big Data Hackathon and is not an official NISR application.
Important limitation: The current prototype does not provide validated disaster-risk predictions, live weather forecasts, or official emergency warnings. Historical agricultural statistics and downloaded price snapshots must not be interpreted as live conditions or forecasts.

Project links
- Live application: https://menya-neza-ai-frontend-nxsc.vercel.app/
- Demonstration video: https://youtu.be/zblJ9MmKIsw
- Full public source repository: https://github.com/shema-coder/menya-neza-ai
- Backend health check: https://menya-neza-ai-api.onrender.com/health
- Interactive API documentation: https://menya-neza-ai-api.onrender.com/docs
- Official NISR SAS 2025 report: NISR Seasonal Agricultural Survey 2025 — Final Report (PDF)
The problem
Rwanda has valuable statistical information about agriculture, but a citizen may not know which report, table, or page contains the answer to a particular question. Finding the relevant figures and interpreting their time period, completeness, and limitations can take time.

MENYA NEZA AI aims to bridge this gap by letting people begin with a natural-language question or explore the available information through district, season, crop, market, and data-quality views.
Main features
Ask MENYA NEZA AI
Ask supported agricultural-data questions in English or Kinyarwanda. Users do not need to know a source report or table in advance. Responses can include supporting source records so users can inspect where an answer came from. When available evidence cannot support a claim, the system should communicate the limitation rather than invent a figure.
Check My Area
Select a Rwandan district and agricultural season to explore historical crop-production observations, reported values, and missing information for that selection.
Insights
Review the coverage and consistency of the current crop-production extract. The views help users understand where records are reported or missing. Coverage percentages describe data availability, not crop performance or disaster risk.
Seasonal Comparison
Compare reported crop-production figures across Seasons A, B, and C of the 2025 survey where the available data supports the comparison.
Supply Origins
Explore and compare reported crop-production values across districts and selected seasons. A sum of reported district values is labelled as a subtotal and must not automatically be interpreted as the official national total.
Market Intelligence
Inspect historical production evidence alongside available market-price observations and source-provided monthly price summaries. These sources have different dates, coverage, units, and limitations. The application does not claim that a change in production caused a change in price.
Data Quality & Sources
Review data-source information, missing values, validation checks, and known limitations. Project-generated validation checks are diagnostic tools; they are not official NISR classifications.
Data sources and methodology
1. NISR Seasonal Agricultural Survey 2025
Source report: NISR Seasonal Agricultural Survey 2025 — Final Report (PDF)

The report is used for historical crop-production records and project data-quality checks. The survey seasons are represented as follows:
- Season A: September 2024–February 2025
- Season B: March–June 2025
- Season C: July–September 2025
The current extract contains 1,650 records across districts, crops, and seasons. In the current application view, reporting completeness is shown as:
Season	Records with numeric values	Expected records	Reported coverage	Period
Season A	613	690	89%	September 2024–February 2025
Season B	630	690	91%	March–June 2025
Season C	170	270	63%	July–September 2025


These percentages show availability of numeric records in the extract. They do not measure crop performance, food security, or disaster risk.

Interpretation rules:
- Missing or dash-valued records are not automatically converted to zero.
- Some crop labels may be aggregates alongside their component categories. Do not add these categories together unless the source supports doing so.
- The data describes the survey period; it does not establish current crop stocks, current market availability, household food sufficiency, weather conditions, or future harvests.
- District subtotals may differ from published national totals. Any difference should be reviewed rather than silently reconciled.
2. Esoko Rwanda price observations
- Source website: Esoko Rwanda / e-Soko
- Repository file: data/processed/esoko_market_price_observations.csv
- Imported snapshot: 908 source rows observed on 26–27 October 2026.
The application uses a manually imported snapshot. It is not a live Esoko API connection or live scraping. The export does not include all the location and unit fields required for complete comparisons. Missing fields remain unknown rather than being inferred. Observations are dated source records and should not be presented as guaranteed current prices.
3. TangaBid monthly price-trend summaries
- Repository file: data/raw/tangabid/tangabid_six_month_price_trends.csv
The current application presents source-provided monthly summaries labelled April–October 2026. October may be incomplete because the dataset was inspected during October 2026. The repository filename contains “six_month”; use the actual records and their dates when interpreting the period, rather than relying on the filename alone.

The currency, exact price type, collection methodology, and meaning of source-reported sample counts have not been independently verified. These records are monthly summaries, not live quotations or forecasts. Markets, sellers, sampling methods, and units may not be comparable between records. Do not add or compare values across different units without a valid conversion and supporting methodology. No original external TangaBid source URL is asserted here because one has not been independently verified for this file.
Responsible data use
MENYA NEZA AI is built around evidence, transparency, and honest uncertainty:
- Historical survey observations are distinguished from current conditions.
- Missing values stay unknown and are not silently changed to zero.
- Source records and known limitations are shown where available.
- District subtotals are not automatically labelled as national totals.
- Project-generated quality checks are not represented as official NISR classifications.
- Downloaded market-price snapshots and monthly summaries are not presented as verified live prices when their source limitations do not support that claim.
- The platform does not currently provide validated disaster-risk predictions, live weather data, or official alerts. For current emergencies, consult the relevant official authorities.
Technology
- Frontend: React and Vite
- Backend: Python and FastAPI
- API: JSON endpoints under /api/v1
- Testing: pytest for backend tests; Vite production build for frontend checks
- Hosting: Vercel frontend and Render backend
Run locally
Requirements
- Python 3.12 or another version supported by the project dependencies
- Node.js and npm
- Git
1. Clone the repository
git clone https://github.com/shema-coder/menya-neza-ai.git
cd menya-neza-ai
2. Set up the backend
From the repository root:
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
Start the backend in one terminal:
.venv/bin/python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
The local API health endpoint is http://localhost:8000/health, and interactive API documentation is available at http://localhost:8000/docs.
3. Set up the frontend
In a second terminal, from the repository root:
npm --prefix frontend install
npm --prefix frontend run dev
Open the local Vite URL shown in the terminal, normally http://localhost:5173. The local Vite configuration is set up to proxy API requests to the local FastAPI service.

For a separate frontend deployment, set the Vite environment variable VITE_API_BASE_URL to the backend base URL, for example:
VITE_API_BASE_URL=https://menya-neza-ai-api.onrender.com
Configure the backend environment variable MENYA_NEZA_CORS_ORIGINS with the exact allowed frontend origin or origins, separated by commas. Example:
MENYA_NEZA_CORS_ORIGINS=http://localhost:5173,https://menya-neza-ai-frontend-nxsc.vercel.app
Do not include a trailing slash in each origin.
Run checks
From the repository root:
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend run build
The backend test suite and frontend build should complete successfully before deployment. These commands verify the local code; also test the deployed application separately.
Main API routes
The API's interactive documentation at https://menya-neza-ai-api.onrender.com/docs is the reference for current request parameters and response schemas. Main routes include:
Method	Route	Purpose
GET	/health	Backend health and dataset status
GET	/api/v1/production	Filtered historical production records
GET	/api/v1/production/summary	Production summaries
GET	/api/v1/production/seasonal-comparison	Seasonal comparisons
GET	/api/v1/supply/origins	District production comparisons
GET	/api/v1/data-quality	Data-quality diagnostics
GET	/api/v1/intelligence/supply-price	Production evidence and price-source status
GET	/api/v1/market-prices/esoko-observations	Imported Esoko observations
GET	/api/v1/market-prices/trends	TangaBid source-provided monthly summaries
POST	/api/v1/ask	Evidence-grounded question answering


See the live API documentation for the complete route list, parameters, and response schemas.
Team
- Team lead: Shema Aime Pacifique
- Team member: Niyonkuru Pierre
AI use and project responsibility
AI tools were used as assistants during parts of development, debugging, and documentation. The team remains responsible for reviewing the implementation, testing its behaviour, verifying data claims, acknowledging sources, and clearly communicating limitations. Use of AI tools does not remove the team's responsibility for the submitted work.
Acknowledgements
We acknowledge the National Institute of Statistics of Rwanda (NISR) for its published Seasonal Agricultural Survey data and the external data providers identified above. Each source is used and described with its known coverage and limitations.
MENYA NEZA AI — From Data to Early Action.

Understand the data. Prepare for change. Built with respect for data quality and local knowledge.
