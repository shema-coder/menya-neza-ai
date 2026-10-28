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

def test_kinyarwanda_live_price_question_requires_clarification():
    result = answer_question(
        "Igiciro cy'ibigori uyu munsi ni angahe?",
        language="rw",
    )

    assert result["status"] == "needs_clarification"
    assert result["evidence"] == []
    assert "Sinshobora" in result["answer"]
    assert "ibiciro biriho ubu" in result["limitation"]


def test_kinyarwanda_weather_question_is_unsupported():
    result = answer_question(
        "Imvura izagwa mu Rwanda ejo?",
        language="rw",
    )

    assert result["status"] == "unsupported"
    assert result["evidence"] == []
    assert "Sinshobora" in result["answer"]
    assert "iteganyagihe" in result["limitation"]

def test_follow_up_price_question_requires_location():
    conversation = [{
        "question": "How much maize did Huye report in Season B 2025?",
        "result": {
            "status": "answered",
            "evidence": [{
                "district": "Huye",
                "crop": "maize",
                "season": "B",
                "year": 2025,
                "production_mt": 1112,
            }],
        },
    }]

    result = answer_question(
        "What about the current price of maize?",
        language="en",
        conversation=conversation,
    )

    assert result["status"] == "needs_clarification"
    assert result["evidence"] == []
    assert "price" in result["answer"].casefold()


def test_follow_up_weather_question_does_not_reuse_production_answer():
    conversation = [{
        "question": "How much maize did Huye report in Season B 2025?",
        "result": {
            "status": "answered",
            "evidence": [{
                "district": "Huye",
                "crop": "maize",
                "season": "B",
                "year": 2025,
                "production_mt": 1112,
            }],
        },
    }]

    result = answer_question(
        "What about the weather tomorrow?",
        language="en",
        conversation=conversation,
    )

    assert result["status"] == "unsupported"
    assert result["evidence"] == []
    assert "weather" in result["answer"].casefold()


def test_kinyarwanda_follow_up_price_question_requires_location():
    conversation = [{
        "question": "Huye yatanze toni zingana iki z'ibigori mu gihembwe B cya 2025?",
        "result": {
            "status": "answered",
            "evidence": [{
                "district": "Huye",
                "crop": "maize",
                "season": "B",
                "year": 2025,
                "production_mt": 1112,
            }],
        },
    }]

    result = answer_question(
        "None se igiciro cy'ibigori cyo ku isoko ubu ni angahe?",
        language="rw",
        conversation=conversation,
    )

    assert result["status"] == "needs_clarification"
    assert result["evidence"] == []
    assert "ibiciro biriho ubu" in result["limitation"]
