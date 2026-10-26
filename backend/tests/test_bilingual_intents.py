from backend.app.services.ask import answer_question


def test_kinyarwanda_beans_comparison_is_recognized():
    result = answer_question(
        "Gereranya umusaruro w'ibishyimbo mu bihembwe bya 2025",
        language="rw",
    )

    # Incomplete data may legitimately prevent a complete comparison,
    # but the question should not fall through to generic clarification.
    assert result["status"] in {"answered", "no_data"}
    assert result["status"] != "needs_clarification"
    assert result["evidence"] or result["status"] == "no_data"


def test_kinyarwanda_data_quality_question_is_recognized():
    result = answer_question(
        "Ni izihe mbogamizi z'ubwiza bw'amakuru?",
        language="rw",
    )

    assert result["status"] == "answered"
    assert "amakuru" in result["answer"].casefold()
    assert result["evidence"]
