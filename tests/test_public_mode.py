from fastapi.testclient import TestClient

from engram.config import Settings, get_settings


def test_public_mode_meta_and_guards(tmp_path, monkeypatch):
    settings = Settings(
        store="local",
        local_data_dir=tmp_path,
        public_mode=True,
        seed_on_boot=True,
        openai_api_key="",
        langchain_tracing_v2=False,
        langchain_api_key="",
        github_token="",
    )
    get_settings.cache_clear()

    import engram.api.app as app_module

    monkeypatch.setattr(app_module, "get_settings", lambda: settings)

    with TestClient(app_module.app) as client:
        meta = client.get("/meta").json()
        assert meta["public_mode"] is True
        assert meta["seeded"] is True
        assert meta["capabilities"]["clone_run"] is False
        assert meta["capabilities"]["eval"] is False
        assert meta["capabilities"]["sample_risk_run"] is True
        assert meta["capabilities"]["situation"] is True
        assert meta["capabilities"]["accept_client_github_token"] is False
        assert meta["github_token_configured"] is False
        assert client.get("/live").json()["status"] == "live"

        denied_clone = client.post(
            "/run",
            json={
                "service": "Claude Cookbooks",
                "task": "Add a note",
                "repo": "anthropics/claude-cookbooks",
            },
        )
        assert denied_clone.status_code == 403

        monkeypatch.setattr(app_module, "ingest_github", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("ingestion reached")))
        assert meta["capabilities"]["github_ingest"] is False
        assert meta["capabilities"]["outcome_resolve"] is False
        for service in ("Auth Service", "svc-auth", "other"):
            assert client.post("/ingest/github", json={"repo": "private/repo", "service": service, "token": "browser-secret"}).status_code == 403
        assert client.post("/ingest/sample").status_code == 403
        assert client.get("/outcomes").status_code == 403
        assert client.post("/outcomes/anything/resolve", json={"decision": "approved", "note": "malicious instruction"}).status_code == 403
        monkeypatch.setitem(app_module._boot, "seeded", False)
        assert client.post("/query", json={"question": "hello"}).status_code == 503
        monkeypatch.setitem(app_module._boot, "seeded", True)
        denied_eval = client.post("/eval")
        assert denied_eval.status_code == 403

    get_settings.cache_clear()


def test_ingest_github_reuses_engine_qdrant(tmp_path, monkeypatch):
    """Regression: opening a second local Qdrant client during ingest used to 500."""
    settings = Settings(
        store="local",
        local_data_dir=tmp_path,
        public_mode=False,
        seed_on_boot=True,
        openai_api_key="",
        langchain_tracing_v2=False,
        langchain_api_key="",
        github_token="",
    )
    get_settings.cache_clear()

    import engram.api.app as app_module

    monkeypatch.setattr(app_module, "get_settings", lambda: settings)

    pulls = [
        {
            "number": 3,
            "title": "Wire context router",
            "state": "closed",
            "body": "V1.5",
        }
    ]

    def fake_ingest(settings_arg, **kwargs):
        assert kwargs.get("graph") is not None
        assert kwargs.get("vectors") is not None
        from engram.ingestion.github import ingest_github as real_ingest

        return real_ingest(
            settings_arg,
            repo=kwargs["repo"],
            service=kwargs.get("service"),
            limit=kwargs.get("limit", 30),
            token=kwargs.get("token"),
            pulls=pulls,
            graph=kwargs["graph"],
            vectors=kwargs["vectors"],
        )

    monkeypatch.setattr(app_module, "ingest_github", fake_ingest)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/ingest/github",
            json={"repo": "acme/demo", "limit": 10},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["pull_requests"] == 1
        assert body["service"]

    get_settings.cache_clear()


def test_public_runner_ignores_graph_repo_and_persisted_priors(tmp_path, monkeypatch):
    from engram.engine import EngramEngine
    from engram.ingestion.seed import seed_from_sample
    from engram.agents.sandbox import Sandbox
    from engram.learning.store import OutcomeStore
    from engram.models.schemas import AgentRunRequest

    settings = Settings(store="local", local_data_dir=tmp_path, public_mode=True,
                        github_token="server-secret", openai_api_key="",
                        langchain_tracing_v2=False, langchain_api_key="")
    seed_from_sample(settings)
    engine = EngramEngine(settings)
    original_preflight = engine.preflight
    original_create = Sandbox.create
    calls = []

    def poisoned_preflight(request):
        packet = original_preflight(request)
        packet.service.github_repo = "private/repo"
        return packet

    def guarded_create(*args, **kwargs):
        calls.append(kwargs)
        assert kwargs["github_repo"] is None
        assert kwargs["token"] is None
        return original_create(*args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("Public run accessed persistent outcome memory")

    monkeypatch.setattr(engine, "preflight", poisoned_preflight)
    monkeypatch.setattr(Sandbox, "create", guarded_create)
    monkeypatch.setattr(OutcomeStore, "similar", forbidden)
    monkeypatch.setattr(OutcomeStore, "record", forbidden)
    try:
        result = engine.run_agents(AgentRunRequest(service="Auth Service", task="Increase auth session TTL to 7 days", repo="attacker/repo", token="client-secret"))
        assert calls
        assert result.candidate.source_repo == "fixture:auth-service"
        assert result.priors == []
        assert not result.outcome_id
        assert not (tmp_path / "outcomes.jsonl").exists()
    finally:
        engine.close()
