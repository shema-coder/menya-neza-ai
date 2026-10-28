import builtins

from backend.app.services import ai_explainer


SAMPLE_RESULT = {
    "status": "answered",
    "answer": "Huye reported 1,112 metric tonnes of maize in Season B 2025.",
    "source": "NISR SAS 2025",
    "limitation": "Historical data, not a live estimate.",
    "evidence": [
        {
            "district": "Huye",
            "crop": "Maize",
            "season": "B",
            "year": 2025,
            "production_mt": 1112,
            "source_page": 62,
        }
    ],
}


def test_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = ai_explainer.generate_explanation(
        "How much maize did Huye report?", "en", SAMPLE_RESULT
    )

    assert result is None


def test_skips_unanswered_results(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    result = ai_explainer.generate_explanation(
        "Will there be a disaster?", "en",
        {"status": "no_data", "answer": "No verified data.", "evidence": []},
    )

    assert result is None


def test_returns_mocked_explanation(monkeypatch):
    monkeypatch.setenv("MENYA_NEZA_AI_EXPLANATIONS", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    class FakeResponse:
        output_text = "The figure describes historical maize production."

    class FakeResponses:
        def create(self, **kwargs):
            assert kwargs["model"] == "test-model"
            assert "verified_answer" in kwargs["input"]
            return FakeResponse()

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr(
        ai_explainer, "_create_client",
        lambda api_key: FakeClient(api_key=api_key, max_retries=0, timeout=12.0),
    )

    result = ai_explainer.generate_explanation(
        "Explain Huye's maize production.", "en", SAMPLE_RESULT
    )

    assert result == "The figure describes historical maize production."


def test_api_failure_falls_back_to_none(monkeypatch):
    monkeypatch.setenv("MENYA_NEZA_AI_EXPLANATIONS", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeResponses:
        def create(self, **kwargs):
            raise RuntimeError("Simulated API failure")

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr(
        ai_explainer, "_create_client",
        lambda api_key: FakeClient(api_key=api_key, max_retries=0, timeout=12.0),
    )

    result = ai_explainer.generate_explanation(
        "Explain the result.", "en", SAMPLE_RESULT
    )

    assert result is None



def _track_openai_imports(monkeypatch):
    attempted = []
    original_import = builtins.__import__

    def tracked_import(name, *args, **kwargs):
        if name == "openai" or name.startswith("openai."):
            attempted.append(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", tracked_import)
    return attempted


def test_disabled_explanations_do_not_import_openai(monkeypatch):
    monkeypatch.setenv("MENYA_NEZA_AI_EXPLANATIONS", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    attempted = _track_openai_imports(monkeypatch)

    result = ai_explainer.generate_explanation(
        "Explain this production record.", "en", SAMPLE_RESULT
    )

    assert result is None
    assert attempted == []


def test_unsupported_answer_does_not_import_openai(monkeypatch):
    monkeypatch.setenv("MENYA_NEZA_AI_EXPLANATIONS", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    attempted = _track_openai_imports(monkeypatch)

    result = ai_explainer.generate_explanation(
        "Will it rain tomorrow?",
        "en",
        {"status": "unsupported", "answer": "Not available", "evidence": []},
    )

    assert result is None
    assert attempted == []
