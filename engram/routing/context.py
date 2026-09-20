from __future__ import annotations

from dataclasses import dataclass, field


TTL_KEYWORDS = {"ttl", "session", "token", "expiry", "expiration", "cache", "redis", "invalidation"}
AUTH_KEYWORDS = {"auth", "authentication", "login", "password", "oauth", "jwt"}
INCIDENT_KEYWORDS = {"incident", "outage", "on-call", "pager", "error rate", "timeout", "down"}
DOCS_KEYWORDS = {"typo", "copy", "readme", "docs", "comment", "changelog", "wording"}
PAYMENTS_KEYWORDS = {
    "payment",
    "payments",
    "settlement",
    "settlements",
    "payment-worker",
    "invoice",
    "billing",
    "fintech",
}
# Soft token budget for adaptive packs (approx chars/4). Huge mode ignores this.
DEFAULT_TOKEN_BUDGET = {
    "docs": 600,
    "incident": 2200,
    "risk_sensitive": 2400,
    "payments": 2400,
    "generic": 1600,
}


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
    token_budget: int | None = None
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
            "token_budget": self.token_budget,
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
        if any(k in t for k in PAYMENTS_KEYWORDS):
            return "payments"
        if any(k in t for k in INCIDENT_KEYWORDS):
            return "incident"
        if any(k in t for k in TTL_KEYWORDS) or any(k in t for k in AUTH_KEYWORDS):
            return "risk_sensitive"
        return "generic"

    def _with_budget(self, policy: ContextPolicy) -> ContextPolicy:
        if policy.token_budget is None and policy.mode in {"adaptive", "hybrid"}:
            policy.token_budget = DEFAULT_TOKEN_BUDGET.get(policy.task_class, 1600)
        return policy

    def _adaptive(self, task: str) -> ContextPolicy:
        task_class = self._task_class(task)
        if task_class == "docs":
            return self._with_budget(
                ContextPolicy(
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
            )
        if task_class == "incident":
            return self._with_budget(
                ContextPolicy(
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
            )
        if task_class == "payments":
            return self._with_budget(
                ContextPolicy(
                    mode="adaptive",
                    task_class=task_class,
                    include_incidents=True,
                    include_prs=True,
                    include_adrs=True,
                    include_dependencies=True,
                    expand_dependencies=True,
                    top_k=8,
                    reasons=[
                        "Payments/settlements change: include incidents, ADRs, PRs, and dependency artifacts."
                    ],
                )
            )
        if task_class == "risk_sensitive":
            return self._with_budget(
                ContextPolicy(
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
            )
        return self._with_budget(
            ContextPolicy(
                mode="adaptive",
                task_class=task_class,
                top_k=6,
                reasons=["Generic engineering task: hybrid graph + vector retrieval."],
            )
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
                token_budget=None,
                reasons=["Fixed baseline: dump graph neighborhood plus unfiltered vector hits."],
            )
        return self._with_budget(
            ContextPolicy(
                mode="hybrid",
                task_class=task_class,
                reasons=["Fixed baseline: graph neighborhood + service-filtered vectors."],
            )
        )
