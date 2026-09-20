from pathlib import Path

from engram.config import Settings
from engram.engine import EngramEngine
from engram.ingestion.seed import seed_from_sample
from engram.models.schemas import SituationRequest
from engram.situation.resolve import (
    explain_situation,
    extract_entities,
    infer_service_from_screen,
    load_situation_fixture,
    redact_screen_text,
)


def test_redact_strips_secrets():
    raw = "token=ghp_abcdefghijklmnopqrstuvwxyz12 sk-proj-ABCDEFGHIJKLMNO Bearer abcdefghijklmnop"
    cleaned = redact_screen_text(raw)
    assert "ghp_" not in cleaned
    assert "sk-proj" not in cleaned
    assert "Bearer abc" not in cleaned
    assert "[REDACTED]" in cleaned


def test_infer_payments_from_datadog_fixture():
    settings = Settings(
        store="local",
        openai_api_key="",
        langchain_tracing_v2=False,
        langchain_api_key="",
    )
    text = load_situation_fixture(settings, "payment-worker")
    assert infer_service_from_screen(text) == "Payments Service"
    entities = extract_entities(text)
    values = {item["value"].lower() for item in entities}
    assert any("settlements" in value or "/settlements" in value for value in values)
    assert any("payment-worker" in value for value in values)


def test_explain_situation_payment_worker(tmp_path):
    settings = Settings(
        store="local",
        local_data_dir=tmp_path,
        openai_api_key="",
        langchain_tracing_v2=False,
        langchain_api_key="",
    )
    seed_from_sample(settings)
    outcomes_before = (tmp_path / "outcomes.jsonl").exists()
    screen = load_situation_fixture(settings, "payment-worker")
    eng = EngramEngine(settings)
    try:
        result = explain_situation(
            eng,
            SituationRequest(
                screen_text=screen + "\nsecret=ghp_abcdefghijklmnopqrstuvwxyz12",
                question="What's happening here? What should I check first?",
            ),
        )
    finally:
        eng.close()

    assert result.ephemeral is True
    assert result.service == "Payments Service"
    assert "not stored" in result.note.lower()
    ids = {item.artifact_id for item in result.evidence}
    labels = " ".join(item.label for item in result.evidence).lower()
    snippets = " ".join(item.snippet for item in result.evidence).lower()
    blob = f"{result.answer} {labels} {snippets} {' '.join(ids)}".lower()
    assert "inc-1842" in blob or "1842" in blob
    assert "pr-8831" in blob or "8831" in blob or "adr-62" in blob or "62" in blob
    # Screen / secrets must not be persisted as outcomes or graph side channel.
    assert outcomes_before is False
    assert not (tmp_path / "outcomes.jsonl").exists()
    graph = (tmp_path / "graph.json").read_text(encoding="utf-8")
    assert "ghp_abcdefghijklmnopqrstuvwxyz12" not in graph
    assert "[REDACTED]" not in graph


def test_situation_api_try_payload_shape(tmp_path, monkeypatch):
    """Smoke: /try on-call panel payload matches POST /situation response shape."""
    from fastapi.testclient import TestClient

    from engram.config import get_settings

    settings = Settings(
        store="local",
        local_data_dir=tmp_path,
        public_mode=True,
        seed_on_boot=True,
        openai_api_key="",
        langchain_tracing_v2=False,
        langchain_api_key="",
    )
    get_settings.cache_clear()
    import engram.api.app as app_module

    monkeypatch.setattr(app_module, "get_settings", lambda: settings)

    screen = load_situation_fixture(settings, "payment-worker")
    with TestClient(app_module.app) as client:
        response = client.post(
            "/situation",
            json={
                "screen_text": screen,
                "question": "What's happening here? What should I check first?",
                "mode": "adaptive",
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ephemeral"] is True
        assert body["service"]
        assert isinstance(body["answer"], str) and body["answer"]
        assert isinstance(body["entities"], list)
        assert isinstance(body["evidence"], list)
        assert body["note"]
        if body["evidence"]:
            item = body["evidence"][0]
            assert "label" in item and "snippet" in item and "artifact_id" in item

    get_settings.cache_clear()
