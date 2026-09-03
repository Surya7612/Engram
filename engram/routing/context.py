from __future__ import annotations

from dataclasses import dataclass, field


TTL_KEYWORDS = {"ttl", "session", "token", "expiry", "expiration", "cache", "redis", "invalidation"}
AUTH_KEYWORDS = {"auth", "authentication", "login", "password", "oauth", "jwt"}
INCIDENT_KEYWORDS = {"incident", "outage", "on-call", "pager", "error rate", "timeout", "down"}
DOCS_KEYWORDS = {"typo", "copy", "readme", "docs", "comment", "changelog", "wording"}


@dataclass
class ContextPolicy:
    mode: str
    task_class: str
    include_graph: bool = True
    include_vectors: bool = True
    include_incidents: bool = True
    include_prs: bool = True
    include_adrs: bool = True
    include_dependencies: bool = True
    expand_dependencies: bool = False
    top_k: int = 6
    vector_filter_service: bool = True
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "task_class": self.task_class,
            "include_graph": self.include_graph,
            "include_vectors": self.include_vectors,
            "include_incidents": self.include_incidents,
            "include_prs": self.include_prs,
            "include_adrs": self.include_adrs,
            "include_dependencies": self.include_dependencies,
            "expand_dependencies": self.expand_dependencies,
            "top_k": self.top_k,
            "vector_filter_service": self.vector_filter_service,
            "reasons": self.reasons,
        }


class ContextRouter:
    """Deterministic V1.5 context router. ML policies come later (V3)."""

    def route(self, task: str, mode: str = "adaptive") -> ContextPolicy:
        requested = (mode or "adaptive").lower()
        if requested != "adaptive":
            return self._fixed_mode(task, requested)
        return self._adaptive(task)

    def _task_class(self, task: str) -> str:
        t = task.lower()
        if any(k in t for k in DOCS_KEYWORDS):
            return "docs"
        if any(k in t for k in INCIDENT_KEYWORDS):
            return "incident"
        if any(k in t for k in TTL_KEYWORDS) or any(k in t for k in AUTH_KEYWORDS):
            return "risk_sensitive"
        return "generic"

    def _adaptive(self, task: str) -> ContextPolicy:
        task_class = self._task_class(task)
        if task_class == "docs":
            return ContextPolicy(
                mode="adaptive",
                task_class=task_class,
                include_graph=True,
                include_vectors=True,
                include_incidents=False,
                include_prs=False,
                include_adrs=False,
                include_dependencies=False,
                top_k=3,
                reasons=["Low-risk docs/copy change: keep context narrow."],
            )
        if task_class == "incident":
            return ContextPolicy(
                mode="adaptive",
                task_class=task_class,
                include_incidents=True,
                include_prs=True,
                include_adrs=False,
                include_dependencies=True,
                expand_dependencies=True,
                top_k=8,
                reasons=["Incident-time query: prioritize related failures and recent changes."],
            )
        if task_class == "risk_sensitive":
            return ContextPolicy(
                mode="adaptive",
                task_class=task_class,
                include_incidents=True,
                include_prs=True,
                include_adrs=True,
                include_dependencies=True,
                expand_dependencies=True,
                top_k=8,
                reasons=["Auth/TTL/cache change: include incidents, ADRs, PRs, and one-hop dep artifacts."],
            )
        return ContextPolicy(
            mode="adaptive",
            task_class=task_class,
            top_k=6,
            reasons=["Generic engineering task: hybrid graph + vector retrieval."],
        )

    def _fixed_mode(self, task: str, mode: str) -> ContextPolicy:
        task_class = self._task_class(task)
        if mode == "vector":
            return ContextPolicy(
                mode="vector",
                task_class=task_class,
                include_graph=False,
                include_vectors=True,
                include_incidents=False,
                include_prs=False,
                include_adrs=False,
                include_dependencies=False,
                top_k=8,
                reasons=["Fixed baseline: vector search only."],
            )
        if mode == "graph":
            return ContextPolicy(
                mode="graph",
                task_class=task_class,
                include_graph=True,
                include_vectors=False,
                top_k=0,
                reasons=["Fixed baseline: graph neighborhood only."],
            )
        if mode == "huge":
            return ContextPolicy(
                mode="huge",
                task_class=task_class,
                include_graph=True,
                include_vectors=True,
                top_k=20,
                vector_filter_service=False,
                reasons=["Fixed baseline: dump graph neighborhood plus unfiltered vector hits."],
            )
        return ContextPolicy(
            mode="hybrid",
            task_class=task_class,
            reasons=["Fixed baseline: graph neighborhood + service-filtered vectors."],
        )
