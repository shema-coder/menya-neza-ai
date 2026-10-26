from backend.app.services.ask import answer_question


def test_natural_kinyarwanda_huye_maize_question():
    result = answer_question(
        "Huye yatanze toni zingana iki z'ibigori mu gihembwe B cya 2025?",
        language="rw",
    )

    assert result["status"] == "answered"
    assert "1,112" in result["answer"]
    assert "Huye" in result["answer"]
    assert "gihembwe B cya 2025" in result["answer"]
    assert "Huye reported" not in result["answer"]
    assert result["evidence"][0]["production_mt"] == 1112
    assert result["evidence"][0]["source_page"] == 62


def test_stored_style_kinyarwanda_question_still_works():
    result = answer_question(
        "Umusaruro w' ibigori mu karere ka Huye mu gihembwe B cya 2025 wari ungana iki?",
        language="rw",
    )

    assert result["status"] == "answered"
    assert result["evidence"][0]["production_mt"] == 1112
    assert "1,112" in result["answer"]
