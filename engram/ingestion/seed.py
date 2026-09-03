import json
from pathlib import Path

from engram.config import Settings
from engram.graph.store import open_graph_store
from engram.vector.store import EmbeddingClient, VectorStore


def load_sample_org(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_from_sample(settings: Settings) -> dict:
    graph = open_graph_store(settings)
    embedder = EmbeddingClient(settings)
    vectors = VectorStore(settings, embedder)

    org_path = settings.data_dir / "org.json"
    org = load_sample_org(org_path)

    try:
        graph.init_schema()
        graph.clear()
        vectors.reset_collection()

        for svc in org["services"]:
            graph.upsert_service(svc)
            vectors.upsert_artifact(
                point_id=svc["id"],
                text=f"{svc['name']}. {svc['description']}. Owner: {svc['owner']}. Criticality: {svc['criticality']}.",
                payload={
                    "artifact_type": "service",
                    "artifact_id": svc["id"],
                    "label": svc["name"],
                    "service_ids": [svc["id"]],
                },
            )

        for dep in org["dependencies"]:
            graph.link_dependency(dep["from"], dep["to"])

        for pr in org["pull_requests"]:
            graph.upsert_pr(pr)
            vectors.upsert_artifact(
                point_id=pr["id"],
                text=f"PR-{pr['number']} {pr['title']}. {pr['summary']}. Status: {pr['status']}.",
                payload={
                    "artifact_type": "pull_request",
                    "artifact_id": pr["id"],
                    "label": f"PR-{pr['number']}",
                    "service_ids": pr.get("service_ids", []),
                },
            )

        for inc in org["incidents"]:
            graph.upsert_incident(inc)
            vectors.upsert_artifact(
                point_id=inc["id"],
                text=f"INC-{inc['number']} {inc['title']}. {inc['summary']}. Status: {inc['status']}.",
                payload={
                    "artifact_type": "incident",
                    "artifact_id": inc["id"],
                    "label": f"INC-{inc['number']}",
                    "service_ids": inc.get("service_ids", []),
                },
            )

        for adr in org["adrs"]:
            graph.upsert_adr(adr)
            vectors.upsert_artifact(
                point_id=adr["id"],
                text=f"ADR-{adr['number']} {adr['title']}. {adr['content']}. Status: {adr['status']}.",
                payload={
                    "artifact_type": "adr",
                    "artifact_id": adr["id"],
                    "label": f"ADR-{adr['number']}",
                    "service_ids": adr.get("service_ids", []),
                },
            )
    finally:
        graph.close()
        vectors.close()

    return {
        "organization": org.get("organization"),
        "services": len(org["services"]),
        "pull_requests": len(org["pull_requests"]),
        "incidents": len(org["incidents"]),
        "adrs": len(org["adrs"]),
        "embedding_backend": "openai" if embedder.uses_openai else "local-hash",
        "store": settings.store,
    }
