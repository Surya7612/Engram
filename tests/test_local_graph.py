from engram.config import Settings
from engram.graph.local import LocalGraphStore


def test_local_graph_finds_auth_service(tmp_path):
    settings = Settings(store="local", local_data_dir=tmp_path)
    graph = LocalGraphStore(settings)
    graph.clear()
    graph.upsert_service(
        {
            "id": "svc-auth",
            "name": "Auth Service",
            "owner": "Platform Team",
            "criticality": "high",
            "description": "Handles authentication",
        }
    )
    graph.link_dependency("svc-auth", "svc-auth")
    found = graph.find_service("Auth")
    assert found is not None
    assert found["id"] == "svc-auth"
    neighborhood = graph.service_neighborhood("svc-auth")
    assert neighborhood["service"]["name"] == "Auth Service"
    assert "svc-auth" in neighborhood["dependency_ids"]
