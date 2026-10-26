from backend.app.services.ask import answer_question


def test_natural_kinyarwanda_data_quality_question():
    result = answer_question(
        "Ni ibihe bibazo biri mu bwiza bw'amakuru y'umusaruro?",
        language="rw",
    )

    assert result["status"] == "answered"
    evidence = result["evidence"][0]
    assert evidence["records_returned"] == 55
    assert evidence["status_counts"] == {
        "SMALL_DIFFERENCE_REVIEW": 21,
        "INCOMPLETE_DISTRICT_DATA": 29,
        "MATCH": 4,
        "LARGE_DIFFERENCE_REVIEW": 1,
    }
