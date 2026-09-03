from engram.models.schemas import ArtifactType, Evidence
from engram.routing.context import ContextPolicy, ContextRouter
from engram.vector.store import VectorStore


def estimate_tokens(evidence: list[Evidence]) -> int:
    text = " ".join(f"{item.label} {item.snippet}" for item in evidence)
    return max(1, len(text) // 4)


def _change_label(pr: dict) -> str:
    artifact_id = str(pr.get("id") or "")
    if "-c-" in artifact_id:
        return f"COMMIT-{artifact_id.rsplit('-c-', 1)[-1][:7]}"
    return f"PR-{pr.get('number')}"


class HybridRetriever:
    def __init__(self, graph, vectors: VectorStore):
        self._graph = graph
        self._vectors = vectors
        self._router = ContextRouter()

    def retrieve(
        self,
        task: str,
        service_name_or_id: str,
        mode: str = "adaptive",
        top_k: int | None = None,
    ) -> dict:
        service = self._graph.find_service(service_name_or_id)
        if not service:
            raise ValueError(f"Service not found: {service_name_or_id}")

        policy = self._router.route(task, mode=mode)
        if top_k is not None:
            policy.top_k = top_k

        neighborhood = (
            self._graph.service_neighborhood(service["id"]) if policy.include_graph else {"service": service}
        )
        neighborhood = self._filter_neighborhood(neighborhood, policy)
        neighborhood = self._expand_dependency_artifacts(neighborhood, policy)

        vector_hits: list[dict] = []
        if policy.include_vectors:
            service_id = service["id"] if policy.vector_filter_service else None
            vector_hits = self._vectors.search(task, top_k=max(policy.top_k, 1), service_id=service_id)

        paths = self._graph.relationship_paths(service["id"]) if policy.include_graph else []
        evidence = self._merge_evidence(neighborhood, vector_hits, paths, policy)

        return {
            "service": service,
            "neighborhood": neighborhood,
            "vector_hits": vector_hits,
            "relationship_paths": paths,
            "evidence": evidence,
            "policy": policy.as_dict(),
            "token_estimate": estimate_tokens(evidence),
        }

    def _filter_neighborhood(self, neighborhood: dict, policy: ContextPolicy) -> dict:
        filtered = dict(neighborhood)
        if not policy.include_incidents:
            filtered["incidents"] = []
        if not policy.include_prs:
            filtered["pull_requests"] = []
        if not policy.include_adrs:
            filtered["adrs"] = []
        if not policy.include_dependencies:
            filtered["dependencies"] = []
            filtered["dependents"] = []
            filtered["dependency_ids"] = []
        return filtered

    def _expand_dependency_artifacts(self, neighborhood: dict, policy: ContextPolicy) -> dict:
        if not policy.expand_dependencies or not policy.include_incidents:
            return neighborhood
        dep_ids = [dep_id for dep_id in (neighborhood.get("dependency_ids") or []) if dep_id]
        if not dep_ids:
            return neighborhood

        incidents = list(neighborhood.get("incidents") or [])
        seen = {inc.get("id") for inc in incidents if inc.get("id")}
        for dep_id in dep_ids:
            dep_nb = self._graph.service_neighborhood(dep_id)
            for inc in dep_nb.get("incidents") or []:
                inc_id = inc.get("id")
                if not inc_id or inc_id in seen:
                    continue
                incidents.append(inc)
                seen.add(inc_id)
        expanded = dict(neighborhood)
        expanded["incidents"] = incidents
        return expanded

    def _merge_evidence(
        self,
        neighborhood: dict,
        vector_hits: list[dict],
        paths: list[list[str]],
        policy: ContextPolicy,
    ) -> list[Evidence]:
        evidence: list[Evidence] = []
        seen: set[str] = set()

        def add(item: Evidence) -> None:
            if item.artifact_id in seen:
                return
            seen.add(item.artifact_id)
            evidence.append(item)

        service = neighborhood.get("service") or {}
        if service:
            add(
                Evidence(
                    artifact_type=ArtifactType.SERVICE,
                    artifact_id=service["id"],
                    label=service["name"],
                    snippet=service.get("description", ""),
                    relationship_path=[service["name"]],
                )
            )

        if policy.include_incidents:
            for inc in neighborhood.get("incidents") or []:
                if not inc.get("id"):
                    continue
                add(
                    Evidence(
                        artifact_type=ArtifactType.INCIDENT,
                        artifact_id=inc["id"],
                        label=f"INC-{inc['number']}",
                        snippet=inc.get("summary") or inc.get("title", ""),
                        relationship_path=[service.get("name", ""), f"INC-{inc['number']}"],
                    )
                )

        if policy.include_prs:
            for pr in neighborhood.get("pull_requests") or []:
                if not pr.get("id"):
                    continue
                label = _change_label(pr)
                add(
                    Evidence(
                        artifact_type=ArtifactType.PULL_REQUEST,
                        artifact_id=pr["id"],
                        label=label,
                        snippet=pr.get("summary") or pr.get("title", ""),
                        relationship_path=[service.get("name", ""), label],
                    )
                )

        if policy.include_adrs:
            for adr in neighborhood.get("adrs") or []:
                if not adr.get("id"):
                    continue
                add(
                    Evidence(
                        artifact_type=ArtifactType.ADR,
                        artifact_id=adr["id"],
                        label=f"ADR-{adr['number']}",
                        snippet=(adr.get("content") or adr.get("title", ""))[:280],
                        relationship_path=[service.get("name", ""), f"ADR-{adr['number']}"],
                    )
                )

        if policy.include_vectors:
            for hit in vector_hits:
                payload = hit.get("payload") or {}
                artifact_id = payload.get("artifact_id")
                if not artifact_id:
                    continue
                artifact_type_raw = payload.get("artifact_type", "service")
                try:
                    artifact_type = ArtifactType(artifact_type_raw)
                except ValueError:
                    continue
                add(
                    Evidence(
                        artifact_type=artifact_type,
                        artifact_id=artifact_id,
                        label=payload.get("label", artifact_id),
                        snippet=(payload.get("text") or "")[:280],
                        relationship_path=paths[0] if paths else [payload.get("label", artifact_id)],
                    )
                )

        return evidence
