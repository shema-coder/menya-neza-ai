from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_api_resolves_follow_up_using_previous_answer():
    first_response = client.post(
        "/api/v1/ask",
        json={
            "question": "How much maize did Huye report in Season B 2025?",
            "language": "en",
        },
    )
    assert first_response.status_code == 200
    first = first_response.json()
    assert first["status"] == "answered"

    follow_up_response = client.post(
        "/api/v1/ask",
        json={
            "question": "Was that higher than Season A?",
            "language": "en",
            "conversation": [
                {
                    "question": "How much maize did Huye report in Season B 2025?",
                    "result": first,
                }
            ],
        },
    )

    assert follow_up_response.status_code == 200
    result = follow_up_response.json()

    assert result["status"] == "answered"
    assert result["answer"].startswith("No.")
    assert "6,930" in result["answer"]
    assert len(result["evidence"]) == 2
    assert {row["season"] for row in result["evidence"]} == {"A", "B"}


def test_api_follow_up_retrieves_season_a_record():
    first_response = client.post(
        "/api/v1/ask",
        json={
            "question": "How much maize did Huye report in Season B 2025?",
            "language": "en",
        },
    )
    first = first_response.json()

    response = client.post(
        "/api/v1/ask",
        json={
            "question": "What about Season A?",
            "language": "en",
            "conversation": [
                {"question": "How much maize did Huye report in Season B 2025?",
                 "result": first}
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "answered"
    assert "8,042" in result["answer"]
    assert result["evidence"][0]["season"] == "A"
    assert result["evidence"][0]["source_page"] == 61
