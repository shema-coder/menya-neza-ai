import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .services import agriculture, intelligence, tangabid

app = FastAPI(
    title="MENYA NEZA AI",
    description=(
        "From Data to Early Action. "
        "Historical agricultural evidence and data-quality insights for Rwanda."
    ),
    version="0.2.0",
)



# MENYA NEZA DEPLOYMENT CORS
_default_cors_origins = (
    "http://localhost:5173,http://127.0.0.1:5173"
)
_allowed_cors_origins = [
    origin.strip()
    for origin in os.environ.get(
        "MENYA_NEZA_CORS_ORIGINS",
        _default_cors_origins,
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

@app.get("/")
def root() -> dict[str, Any]:
    return {
        "project": "MENYA NEZA AI",
        "tagline": "From Data to Early Action",
        "status": "running",
        "version": app.version,
        "documentation": "/docs",
        "api_prefix": "/api/v1",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "menya-neza-ai-backend",
        "datasets": agriculture.data_status(),
    }


@app.get("/api/v1/data/status")
def get_data_status() -> dict[str, Any]:
    return agriculture.data_status()


@app.get("/api/v1/intelligence/supply-price")
def get_supply_price_intelligence(
    crop: str,
    season: str,
    year: int = 2025,
    district: str | None = None,
) -> dict[str, Any]:
    """Combine production evidence, price-source status and NST2 relevance."""
    crop = _resolve_option(crop, agriculture.list_crops(), "crop")
    season = _resolve_option(
        season,
        sorted({item["season"] for item in agriculture.list_seasons()}),
        "season",
    )
    year = _resolve_year(year)
    district = _resolve_option(
        district, agriculture.list_districts(), "district"
    )

    return intelligence.supply_price_report(
        crop=crop,
        season=season,
        year=year,
        district=district,
    )


@app.get("/api/v1/market-prices/esoko/status")
def get_esoko_market_price_source_status():
    # Return metadata and limitations for the imported Esoko CSV snapshot.
    from .services import esoko_source

    return esoko_source.source_status()


@app.get("/api/v1/market-prices/esoko-observations")
def get_esoko_market_price_observations(
    product: str | None = None,
    location: str | None = None,
    price_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    # Search dated Esoko observations without mixing them into monthly summaries.
    from .services import esoko_source
    from fastapi import HTTPException

    try:
        return esoko_source.search_observations(
            product=product,
            location=location,
            price_type=price_type,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Esoko snapshot is unavailable.") from exc


@app.get("/api/v1/market-prices/trends")
def get_market_price_trends(
    product: str | None = None,
    month: str | None = None,
    region: str | None = None,
    location: str | None = None,
    unit: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Return source-provided monthly price summaries, not live prices."""
    try:
        return tangabid.price_trends(
            product=product,
            month=month,
            region=region,
            location=location,
            unit=unit,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Market-price dataset is not available.",
        ) from exc


def _resolve_option(
    value: str | None,
    options: list[str],
    field_name: str,
) -> str | None:
    if value is None:
        return None

    lookup = {option.casefold(): option for option in options}
    resolved = lookup.get(value.strip().casefold())

    if resolved is None:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Unknown {field_name}.",
                "provided": value,
                "available_options": options,
            },
        )

    return resolved


def _resolve_year(year: int | None) -> int | None:
    if year is None:
        return None

    years = sorted({
        item["year"]
        for item in agriculture.list_seasons()
        if item["year"] is not None
    })

    if year not in years:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Year is not available in the loaded dataset.",
                "provided": year,
                "available_years": years,
            },
        )

    return year


@app.get("/api/v1/districts")
def get_districts() -> dict[str, Any]:
    districts = agriculture.list_districts()
    return {"count": len(districts), "districts": districts}


@app.get("/api/v1/seasons")
def get_seasons() -> dict[str, Any]:
    seasons = agriculture.list_seasons()
    return {"count": len(seasons), "seasons": seasons}


@app.get("/api/v1/crops")
def get_crops() -> dict[str, Any]:
    crops = agriculture.list_crops()
    return {"count": len(crops), "crops": crops}


@app.get("/api/v1/production")
def get_production(
    district: str | None = None,
    season: str | None = None,
    crop: str | None = None,
    year: int | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    district = _resolve_option(
        district, agriculture.list_districts(), "district"
    )
    season = _resolve_option(
        season,
        sorted({item["season"] for item in agriculture.list_seasons()}),
        "season",
    )
    crop = _resolve_option(crop, agriculture.list_crops(), "crop")
    year = _resolve_year(year)

    records = agriculture.filter_production(
        district=district,
        season=season,
        crop=crop,
        year=year,
    )

    return {
        "source": "NISR Seasonal Agricultural Survey 2025",
        "filters": {
            "district": district,
            "season": season,
            "crop": crop,
            "year": year,
        },
        "total_matching_records": len(records),
        "limit": limit,
        "offset": offset,
        "records": records[offset:offset + limit],
        "note": (
            "Historical survey data, not a live weather feed or an "
            "official agricultural warning."
        ),
    }


@app.get("/api/v1/production/summary")
def get_production_summary(
    season: str | None = None,
    crop: str | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    season = _resolve_option(
        season,
        sorted({item["season"] for item in agriculture.list_seasons()}),
        "season",
    )
    crop = _resolve_option(crop, agriculture.list_crops(), "crop")
    year = _resolve_year(year)

    summaries = agriculture.production_summaries(
        season=season,
        crop=crop,
        year=year,
    )

    return {
        "source": "NISR Seasonal Agricultural Survey 2025",
        "filters": {"season": season, "crop": crop, "year": year},
        "count": len(summaries),
        "summaries": summaries,
        "note": (
            "Each crop is summarized separately. Reported district sums "
            "may be incomplete and must not automatically be treated as "
            "national totals."
        ),
    }


@app.get("/api/v1/data-quality")
def get_data_quality(
    season: str | None = None,
    crop: str | None = None,
) -> dict[str, Any]:
    season = _resolve_option(
        season,
        sorted({item["season"] for item in agriculture.list_seasons()}),
        "season",
    )
    crop = _resolve_option(crop, agriculture.list_crops(), "crop")

    return agriculture.data_quality(season=season, crop=crop)


@app.get("/api/v1/supply/origins")
def get_supply_origins(
    crop: str,
    season: str,
    year: int,
) -> dict[str, Any]:
    """Explore historical crop-production origins by district."""
    crop = _resolve_option(crop, agriculture.list_crops(), "crop")
    season = _resolve_option(
        season,
        sorted({item["season"] for item in agriculture.list_seasons()}),
        "season",
    )
    year = _resolve_year(year)

    return agriculture.supply_origins(
        crop=crop,
        season=season,
        year=year,
    )



@app.get("/api/v1/production/seasonal-comparison")
def get_seasonal_comparison(
    crop: str | None = None,
    year: int = 2025,
) -> dict[str, Any]:
    """Compare a crop's reported production across all three 2025 seasons."""
    year = _resolve_year(year)
    crop = _resolve_option(crop, agriculture.list_crops(), "crop")

    result = agriculture.seasonal_comparison(year=year, crop=crop)

    if crop is not None and not result["eligible"]:
        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "This crop is not represented in all three seasons "
                    "in the loaded dataset."
                ),
                "provided": crop,
                "available_options": result["available_crops"],
            },
        )

    return result


@app.post("/api/v1/ask")
def ask_menya_neza(payload: dict[str, Any]) -> dict[str, Any]:
    """Answer a supported question using loaded agricultural evidence."""
    from .services.ask import answer_question

    question = payload.get("question", "")
    language = payload.get("language", "en")

    if not isinstance(question, str):
        raise HTTPException(
            status_code=422,
            detail="'question' must be a string.",
        )
    if len(question) > 500:
        raise HTTPException(
            status_code=422,
            detail="'question' must be 500 characters or fewer.",
        )

    conversation = payload.get("conversation", [])
    if conversation is None:
        conversation = []
    if not isinstance(conversation, list):
        raise HTTPException(
            status_code=422,
            detail="'conversation' must be a list.",
        )

    # Keep only a small recent history; allow only the fields we need.
    safe_history = []
    for turn in conversation[-6:]:
        if not isinstance(turn, dict):
            continue
        prior_question = turn.get("question", "")
        prior_result = turn.get("result", {})
        if not isinstance(prior_question, str):
            continue
        if not isinstance(prior_result, dict):
            continue

        safe_evidence = []
        prior_evidence = prior_result.get("evidence", [])
        if isinstance(prior_evidence, list):
            allowed_fields = {
                "district", "crop", "season", "year", "season_period",
                "production_mt", "source", "source_table", "source_page",
                "source_value_status", "value_status",
            }
            for item in prior_evidence[:3]:
                if isinstance(item, dict):
                    safe_evidence.append({
                        key: value
                        for key, value in item.items()
                        if key in allowed_fields
                    })

        safe_history.append({
            "question": prior_question[:500],
            "result": {
                "status": str(prior_result.get("status", ""))[:40],
                "evidence": safe_evidence,
            },
        })

    result = answer_question(question, language, conversation=safe_history)

    from .services.ai_explainer import generate_explanation

    explanation = generate_explanation(question, language, result)
    if explanation:
        result["ai_explanation"] = explanation

    return result


# ASK_KNOWLEDGE_BANK_ENDPOINTS
@app.get("/api/v1/ask/knowledge/status")
def ask_knowledge_status() -> dict[str, Any]:
    """Return the size and language coverage of the stored Q&A bank."""
    from .services.question_bank import question_bank_stats
    return question_bank_stats()


@app.get("/api/v1/ask/knowledge/questions")
def search_ask_knowledge(
    q: str = "",
    language: str = "en",
    limit: int = 20,
) -> dict[str, Any]:
    """Search stored questions and return their detailed answers and evidence."""
    from .services.question_bank import search_questions, question_bank_stats

    code = language.casefold().strip()
    if code not in {"en", "rw", "kin", "kinyarwanda", "eng", "english"}:
        raise HTTPException(
            status_code=422,
            detail="language must be English (en) or Kinyarwanda (rw).",
        )

    safe_limit = max(1, min(limit, 100))
    questions = search_questions(q, language=code, limit=safe_limit)
    return {
        "query": q,
        "language": code,
        "limit": safe_limit,
        "total_questions_in_bank": question_bank_stats()["total_questions"],
        "returned": len(questions),
        "questions": questions,
    }
