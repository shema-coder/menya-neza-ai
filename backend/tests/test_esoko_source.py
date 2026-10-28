from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.services import esoko_source


def test_esoko_snapshot_has_expected_coverage():
    status = esoko_source.source_status()
    assert status["available"] is True
    assert status["records"] == 908
    assert status["distinct_products"] == 101
    assert status["distinct_markets"] == 25
    assert status["snapshot_observation_start"].startswith("2026-10-26")
    assert status["snapshot_observation_end"].startswith("2026-10-27")
    assert status["missing_values"]["farmgate_price_rwf"] == 2
    assert status["missing_values"]["unit"] == 908
    assert status["missing_values"]["province"] == 908
    assert status["missing_values"]["district"] == 908


def test_api_search_filters_esoko_observations():
    result = esoko_source.search_observations(
        product="Ibigori", location="Nyabugogo", price_type="retail"
    )
    assert result["source"] == "Esoko Rwanda eSoko Price Trends"
    assert result["live_feed"] is False
    assert result["total_matching_records"] >= 1
    assert result["records"][0]["market"] == "Nyabugogo"
    assert result["records"][0]["selected_price_type"] == "retail"
    assert result["records"][0]["selected_price_rwf"] == 600


def test_ask_answers_retail_price_with_source_timestamp_and_unit_caveat():
    result = esoko_source.answer_question(
        "What is the retail price of Ibigori at Nyabugogo?", "en"
    )
    assert result is not None
    assert result["status"] == "answered"
    assert result["price_observation"]["retail_price_rwf"] == 600
    assert result["price_observation"]["observed_date"] == "2026-10-26"
    assert result["price_observation"]["unit_status"] == "NOT_PROVIDED_IN_EXPORT"
    assert result["price_observation"]["live_price_verified"] is False
    assert "does not report the product unit" in result["answer"]


def test_akawunga_alias_uses_actual_esoko_variant_and_keeps_all_price_tiers():
    result = esoko_source.answer_question(
        "Akawunga kabura angahe i Nyabugogo?", "rw"
    )
    assert result is not None
    assert result["status"] == "answered"
    assert result["evidence"][0]["product_name"] == "Ifu - Ibigori - Mugurusu"
    assert result["price_observation"]["farmgate_price_rwf"] == 900
    assert result["price_observation"]["wholesale_price_rwf"] == 1100
    assert result["price_observation"]["retail_price_rwf"] == 1200
    assert result["price_observation"]["unit"] is None
    assert "si igiciro cy'ako kanya" in result["answer"]


def test_missing_farmgate_value_is_not_converted_to_zero():
    result = esoko_source.answer_question(
        "What is the farmgate price of Konkombure at Nyagatare?", "en"
    )
    assert result is not None
    assert result["status"] == "no_data"
    assert "does not mean zero" in result["answer"]
    assert result["evidence"][0]["requested_price_type"] == "farmgate"


def test_non_price_questions_are_not_intercepted():
    assert esoko_source.answer_question(
        "How much maize did Nyagatare report during Season B 2025?"
    ) is None


def test_api_endpoint_is_registered_and_returns_esoko_metadata():
    if not (Path(__file__).resolve().parents[1] / "app/main.py").is_file():
        pytest.skip("API route integration test requires the full project checkout")

    from backend.app.main import app

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/market-prices/esoko-observations",
            params={"product": "Ibigori", "location": "Nyabugogo", "price_type": "retail"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["source_url"] == "https://esoko.rw/price-trends"
    assert data["records"]
    assert data["records"][0]["selected_price_rwf"] == 600
