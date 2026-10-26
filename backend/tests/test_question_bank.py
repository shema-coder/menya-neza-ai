from backend.app.services.question_bank import (
    load_question_bank,
    lookup_question,
    question_bank_stats,
    search_questions,
)


def test_question_bank_contains_more_than_one_thousand_questions():
    stats = question_bank_stats()
    assert stats["total_questions"] > 1000
    assert stats["by_language"].get("en", 0) > 0
    assert stats["by_language"].get("rw", 0) > 0


def test_stored_question_returns_answer_and_source_evidence():
    entries = load_question_bank()
    assert entries

    entry = next(item for item in entries if item["language"] == "en")
    found = lookup_question(entry["question"], language="en")

    assert found is not None
    assert found["response"]["answer"]
    assert found["response"]["evidence"]
    assert found["response"]["source"] == "NISR Seasonal Agricultural Survey 2025"


def test_question_search_returns_detailed_answers():
    results = search_questions("maize", language="en", limit=5)
    assert results
    assert len(results) <= 5
    assert all(item.get("answer") for item in results)


def test_missing_data_is_not_stored_as_zero():
    entries = load_question_bank()
    missing_entries = [
        item for item in entries
        if item["response"]["evidence"]
        and item["response"]["evidence"][0].get("production_mt") is None
    ]

    for entry in missing_entries[:20]:
        assert "not reported" in entry["response"]["answer"].casefold() or (
            "missing value" in entry["response"]["answer"].casefold()
            or "ntibisobanura" in entry["response"]["answer"].casefold()
            or "nti" in entry["response"]["answer"].casefold()
        )
