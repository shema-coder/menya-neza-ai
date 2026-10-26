from backend.app.services.ask import answer_question


def test_follow_up_answers_was_that_higher_directly():
    first = answer_question(
        "How much maize did Huye report in Season B 2025?",
        "en",
    )

    follow_up = answer_question(
        "Was that higher than Season A?",
        "en",
        conversation=[
            {"question": "How much maize did Huye report in Season B 2025?",
             "result": first}
        ],
    )

    assert first["status"] == "answered"
    assert follow_up["status"] == "answered"
    assert follow_up["answer"].startswith("No.")
    assert "6,930" in follow_up["answer"]
    assert "Season B" in follow_up["answer"]
    assert "Season A" in follow_up["answer"]

    records = follow_up["evidence"]
    assert len(records) == 2
    assert {row["season"] for row in records} == {"A", "B"}
    assert {row["production_mt"] for row in records} == {8042.0, 1112.0}
    assert all(row.get("source_page") for row in records)


def test_follow_up_what_about_season_a_retrieves_new_record():
    first = answer_question(
        "How much maize did Huye report in Season B 2025?",
        "en",
    )

    follow_up = answer_question(
        "What about Season A?",
        "en",
        conversation=[
            {"question": "How much maize did Huye report in Season B 2025?",
             "result": first}
        ],
    )

    assert follow_up["status"] == "answered"
    assert "8,042" in follow_up["answer"]
    assert follow_up["evidence"][0]["season"] == "A"
    assert follow_up["evidence"][0]["source_page"] == 61
