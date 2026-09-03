from engram.config import Settings
from engram.graph.local import LocalGraphStore
from engram.retrieval.hybrid import HybridRetriever
from engram.vector.store import EmbeddingClient, VectorStore


def test_adaptive_pulls_one_hop_dep_incidents(tmp_path):
    settings = Settings(
        store="local",
        local_data_dir=tmp_path,
        openai_api_key="",
        langchain_tracing_v2=False,
        langchain_api_key="",
    )
    graph = LocalGraphStore(settings)
    graph.clear()
    graph.upsert_service(
        {
            "id": "svc-auth",
            "name": "Auth Service",
            "owner": "Platform Team",
            "criticality": "high",
            "description": "Authentication",
        }
    )
    graph.upsert_service(
        {
            "id": "svc-redis",
            "name": "Redis Cache",
            "owner": "Platform Team",
            "criticality": "high",
            "description": "Cache",
        }
    )
    graph.link_dependency("svc-auth", "svc-redis")
    graph.upsert_incident(
        {
            "id": "inc-77",
            "number": 77,
            "title": "Redis eviction after lifetime increase",
            "status": "resolved",
            "summary": "Raising identity credential lifetime caused Redis to evict hot keys.",
            "service_ids": ["svc-redis"],
        }
    )

    vectors = VectorStore(settings, EmbeddingClient(settings))
    vectors.ensure_collection()
    retriever = HybridRetriever(graph, vectors)
    try:
        task = "Increase auth session TTL from 24 hours to 7 days"

        graph_ids = {item.artifact_id for item in retriever.retrieve(task, "Auth Service", mode="graph")["evidence"]}
        adaptive_ids = {
            item.artifact_id for item in retriever.retrieve(task, "Auth Service", mode="adaptive")["evidence"]
        }

        assert "inc-77" not in graph_ids
        assert "inc-77" in adaptive_ids
    finally:
        vectors.close()
        graph.close()
