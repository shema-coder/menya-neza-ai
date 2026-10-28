from backend.app.services.ask import answer_question


def test_named_district_comparison_uses_requested_seasons():
    result = answer_question(
        "Compare Huye maize production between Season A and Season B in 2025.",
        language="en",
    )
    assert result["status"] == "answered"
    assert len(result["evidence"]) == 2
    assert result["comparison"]["previous_season"] == "A"
    assert result["comparison"]["comparison_season"] == "B"
    assert result["comparison"]["difference_mt"] == 6930


def test_district_count_returns_a_count_not_a_tonnage_total():
    result = answer_question(
        "How many districts reported maize in Season B 2025?",
        language="en",
    )
    assert result["status"] == "answered"
    assert "30 of 30 districts" in result["answer"]
    assert "117,710" not in result["answer"]
    assert result["evidence"][0]["reported_records"] == 30


def test_kinyarwanda_follow_up_switches_to_season_a():
    question = "Huye yatanze toni zingana iki z'ibigori mu gihembwe B cya 2025?"
    previous = answer_question(question, language="rw")
    assert previous["status"] == "answered"

    result = answer_question(
        "None se igihembo A?",
        language="rw",
        conversation=[{"question": question, "result": previous}],
    )
    assert result["status"] == "answered"
    assert result["question_context"]["season"] == "A"
    assert result["evidence"][0]["season"] == "A"
    assert result["evidence"][0]["production_mt"] == 8042


def test_kinyarwanda_comparison_uses_kinyarwanda_crop_name():
    result = answer_question(
        "Gereranya umusaruro w'ibigori wa Huye mu gihembwe A n'icya B muri 2025.",
        language="rw",
    )
    assert result["status"] == "answered"
    assert len(result["evidence"]) == 2
    assert "ibigori" in result["answer"]
    assert "Maize" not in result["answer"]
    assert "Bho toni" not in result["answer"]
    assert "w' ibigori" not in result["answer"]
    assert result["comparison"]["absolute_difference_mt"] == 6930

def test_overall_two_season_comparison_returns_both_seasons():
    result = answer_question(
        "Compare maize production between Season A and Season B in 2025.",
        language="en",
    )

    assert result["status"] == "answered"
    assert len(result["evidence"]) == 2
    assert result["comparison"]["previous_season"] == "A"
    assert result["comparison"]["comparison_season"] == "B"
    assert "not verified national totals" in result["answer"]


def test_flood_forecast_question_is_explicitly_unsupported():
    result = answer_question(
        "Is flooding expected in Kigali tomorrow?",
        language="en",
    )

    assert result["status"] == "unsupported"
    assert result["evidence"] == []
    assert "disaster warnings" in result["answer"].casefold()

def test_kinyarwanda_reliability_question_returns_quality_findings():
    result = answer_question("Ese amakuru y'ubuhinzi yizewe?", language="rw")
    assert result["status"] == "answered"
    assert result["evidence"][0]["records_returned"] == 55
    assert "inyandiko 55" in result["answer"]


def test_kinyarwanda_incomplete_data_question_returns_quality_findings():
    result = answer_question(
        "Ni ibihe bibazo biri mu makuru atuzuye?", language="rw"
    )
    assert result["status"] == "answered"
    assert result["evidence"][0]["records_returned"] == 55
    assert "Igenzura" in result["answer"]


def test_kinyarwanda_unknown_year_is_localized():
    result = answer_question(
        "Huye yatanze toni zingana iki z'ibigori mu gihembwe B cya 2030?",
        language="rw",
    )
    assert result["status"] == "unsupported"
    assert "2030" in result["answer"]
    assert "loaded dataset" not in result["answer"].casefold()
    assert "Nta makuru" in result["answer"]


def test_kinyarwanda_comparison_uses_localized_coverage():
    result = answer_question(
        "Gereranya umusaruro w'ibigori hagati y'igihembwe A "
        "n'igihembwe B muri 2025.",
        language="rw",
    )
    assert result["status"] == "answered"
    assert "30 of 30 districts" not in result["answer"]
    assert "uturere 30 kuri 30" in result["answer"]
    assert result["comparison"]["absolute_difference_mt"] == 363538


def test_kinyarwanda_akawunga_nyabugogo_returns_latest_monthly_price():
    result = answer_question(
        "Akawunga kabura angahe i Nyabugogo?", language="rw"
    )

    assert result["status"] == "answered"
    evidence = result["evidence"][0]
    assert evidence["product"] == "Maize Flour"
    assert evidence["location"] == "Nyabugogo"
    assert evidence["region"] == "NYARUGENGE"
    assert evidence["month"] == "2026-10-01"
    assert evidence["avg_price"] == 900
    assert evidence["sample_count"] == 2
    assert evidence["currency"] is None
    assert evidence["live_price_verified"] is False
    assert "si igiciro cyagenzuwe cyo uyu munsi" in result["answer"]


def test_english_market_question_can_select_a_specific_month():
    result = answer_question(
        "How much was maize flour in Nyabugogo in May 2026?",
        language="en",
    )

    assert result["status"] == "answered"
    evidence = result["evidence"][0]
    assert evidence["month"] == "2026-05-01"
    assert evidence["avg_price"] > 854
    assert evidence["avg_price"] < 855
    assert evidence["sample_count"] == 11


def test_live_price_question_discloses_monthly_data_limitation():
    result = answer_question(
        "What is the current price of maize flour in Nyabugogo today?",
        language="en",
    )

    assert result["status"] == "answered"
    assert result["evidence"][0]["month"] == "2026-10-01"
    assert result["price_observation"]["live_price_verified"] is False
    assert "do not have a verified live price" in result["answer"]
    assert "not a verified live quote" in result["answer"]


def test_market_price_question_requires_a_location():
    result = answer_question(
        "What is the current price of maize flour?", language="en"
    )

    assert result["status"] == "needs_clarification"
    assert result["evidence"] == []
    assert "Which market or location" in result["answer"]


def test_market_price_question_is_answered_through_public_api():
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/v1/ask",
        json={
            "question": "Akawunga kabura angahe i Nyabugogo?",
            "language": "rw",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["evidence"][0]["product"] == "Maize Flour"
    assert body["evidence"][0]["month"] == "2026-10-01"


def test_flood_related_price_forecast_remains_unsupported():
    result = answer_question(
        "Will the price rise because flooding is expected in Nyabugogo?",
        language="en",
    )

    assert result["status"] == "unsupported"
    assert result["evidence"] == []
