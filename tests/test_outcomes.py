import json

from engram.agents.summary import format_run
from engram.config import Settings
from engram.engine import EngramEngine
from engram.ingestion.seed import seed_from_sample
from engram.learning.store import OutcomeStore
from engram.models.schemas import AgentRunRequest


def test_run_records_outcome_and_resolve_does_not_merge(tmp_path):
    settings = Settings(
        store="local",
        local_data_dir=tmp_path,
        openai_api_key="",
        langchain_tracing_v2=False,
        langchain_api_key="",
    )
    seed_from_sample(settings)
    engine = EngramEngine(settings)
    try:
        result = engine.run_agents(
            AgentRunRequest(
                service="Auth Service",
                task="Increase auth session TTL from 24 hours to 7 days",
            )
        )
    finally:
        engine.close()

    assert result.outcome_id
    assert result.human_decision == "pending"
    violation_ids = [item["evidence_id"] for item in (result.risk or {}).get("violations") or []]
    assert violation_ids == ["adr-12"]

    store = OutcomeStore(tmp_path / "outcomes.jsonl")
    recorded = store.get(result.outcome_id)
    assert recorded is not None
    assert recorded["gate"] == "block"
    resolved = store.resolve(result.outcome_id, "rejected", "ADR-12 stands")
    assert resolved["human_decision"] == "rejected"
    assert resolved["merged"] is False
    stats = store.stats()
    assert stats["n"] == 1
    assert stats["block_rate"] == 1.0
    assert store.latest()["id"] == result.outcome_id
    assert result.priors == []


def _row(outcome_id: str, decision: str, **extra) -> dict:
    payload = {
        "id": outcome_id,
        "service": "Auth Service",
        "task": "Increase auth session TTL from 24 hours to 7 days",
        "human_decision": decision,
        "gate": "block",
        "human_note": extra.pop("human_note", ""),
    }
    payload.update(extra)
    return payload


def test_similar_ignores_pending(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    path.write_text(json.dumps(_row("aaa111", "pending")) + "\n", encoding="utf-8")
    store = OutcomeStore(path)
    assert store.similar("Auth Service", "Increase auth session TTL from 24 hours to 7 days") == []


def test_similar_returns_rejected_note(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    path.write_text(
        json.dumps(_row("bbb222", "rejected", human_note="ADR-12 stands")) + "\n",
        encoding="utf-8",
    )
    store = OutcomeStore(path)
    hits = store.similar("Auth Service", "Increase auth session TTL from 24 hours to 7 days")
    assert [hit["id"] for hit in hits] == ["bbb222"]
    assert hits[0]["human_note"] == "ADR-12 stands"


def test_rejected_outcome_surfaces_on_next_run(tmp_path):
    settings = Settings(
        store="local",
        local_data_dir=tmp_path,
        openai_api_key="",
        langchain_tracing_v2=False,
        langchain_api_key="",
    )
    seed_from_sample(settings)
    task = "Increase auth session TTL from 24 hours to 7 days"
    engine = EngramEngine(settings)
    try:
        first = engine.run_agents(AgentRunRequest(service="Auth Service", task=task))
        store = OutcomeStore(tmp_path / "outcomes.jsonl")
        store.resolve(first.outcome_id, "rejected", "ADR-12 stands")
        second = engine.run_agents(AgentRunRequest(service="Auth Service", task=task))
    finally:
        engine.close()

    assert first.priors == []
    assert [item["id"] for item in second.priors] == [first.outcome_id]
    assert second.priors[0]["human_decision"] == "rejected"
    assert any("ADR-12 stands" in line for line in second.constraints)
    recorded = OutcomeStore(tmp_path / "outcomes.jsonl").get(second.outcome_id)
    assert recorded["prior_ids"] == [first.outcome_id]
    text = format_run(second)
    assert f"prior: {first.outcome_id}  rejected  ADR-12 stands" in text
    assert second.gate.value == "block"
