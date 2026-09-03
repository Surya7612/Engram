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
        assert meta["capabilities"]["clone_run"] is False
        assert meta["capabilities"]["eval"] is False
        assert meta["capabilities"]["sample_risk_run"] is True
        assert meta["capabilities"]["accept_client_github_token"] is False

        denied_clone = client.post(
            "/run",
            json={
                "service": "Claude Cookbooks",
                "task": "Add a note",
                "repo": "anthropics/claude-cookbooks",
            },
        )
        assert denied_clone.status_code == 403

        denied_eval = client.post("/eval")
        assert denied_eval.status_code == 403

    get_settings.cache_clear()
