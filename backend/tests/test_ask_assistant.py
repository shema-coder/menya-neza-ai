from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def ask(question: str) -> dict:
    response = client.post(
        "/api/v1/ask",
        json={"question": question, "language": "en"},
    )
    assert response.status_code == 200
    return response.json()


def test_nst2_maize_targets_are_returned_with_caveat():
    result = ask("What are the NST2 maize production targets?")

    assert result["status"] == "answered"
    assert "665,701" in result["answer"]
    assert "874,337" in result["answer"]
    assert "2.26" in result["answer"]
    assert "2.74" in result["answer"]
    assert "not proof of target achievement" in result["answer"]


def test_nst2_beans_targets_are_returned():
    result = ask("What are the NST2 targets for beans?")

    assert result["status"] == "answered"
    assert "565,009" in result["answer"]
    assert "662,115" in result["answer"]
    assert "1.3" in result["answer"]
    assert "1.5" in result["answer"]


def test_huye_maize_season_b_record_has_source_evidence():
    result = ask("How much maize did Huye report in Season B 2025?")

    assert result["status"] == "answered"
    assert "1,112" in result["answer"]
    assert result["evidence"]
    evidence = result["evidence"][0]
    assert evidence["district"] == "Huye"
    assert evidence["crop"].casefold() == "maize"
    assert evidence["season"] == "B"
    assert evidence["year"] == 2025
    assert evidence["source_page"] == 62


def test_weather_question_is_not_answered_as_a_prediction():
    result = ask("Will it rain in Rwanda tomorrow?")

    assert result["status"] == "unsupported"
    assert "weather" in result["limitation"].casefold() or (
        "weather" in result["answer"].casefold()
    )


def test_live_price_question_is_not_fabricated():
    result = ask("What is the current price of maize?")

    assert result["status"] == "unsupported"
    assert "price" in result["answer"].casefold()


def test_empty_question_requests_a_question():
    result = ask("   ")

    assert result["status"] == "needs_question"
    assert result["evidence"] == []
