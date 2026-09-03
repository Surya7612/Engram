from typing import TypedDict
import os

from langgraph.graph import END, StateGraph

from engram.config import Settings, get_settings
from engram.eval.groundedness import answer_from_evidence
from engram.graph.store import open_graph_store
from engram.models.schemas import (
    AgentRunRequest,
    AgentRunResult,
    PolicyOutcome,
    PreflightPacket,
    PreflightRequest,
    QueryRequest,
    QueryResponse,
    RiskLevel,
    ServiceContext,
)
from engram.preflight.risk import assess_risk, build_summary
from engram.retrieval.hybrid import HybridRetriever
from engram.vector.store import EmbeddingClient, VectorStore


class PreflightState(TypedDict, total=False):
    request: PreflightRequest
    retrieval: dict
    risk_level: RiskLevel
    policy_outcome: PolicyOutcome
    reasoning: list[str]
    manual_checks: list[str]
    packet: PreflightPacket


class EngramEngine:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._configure_tracing()
        self.graph = open_graph_store(self.settings)
        self.embedder = EmbeddingClient(self.settings)
        self.vectors = VectorStore(self.settings, self.embedder)
        self.retriever = HybridRetriever(self.graph, self.vectors)
        self._preflight_graph = self._build_preflight_graph()

    def _configure_tracing(self) -> None:
        if not (self.settings.langchain_tracing_v2 and self.settings.langchain_api_key):
            return
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = self.settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = self.settings.langchain_project
        os.environ["LANGSMITH_API_KEY"] = self.settings.langchain_api_key
        os.environ["LANGSMITH_TRACING"] = "true"

    def close(self) -> None:
        self.graph.close()
        self.vectors.close()

    def health(self) -> dict:
        return {
            "neo4j": self.graph.ping(),
            "qdrant": self.vectors.ping(),
        }

    def preflight(self, request: PreflightRequest) -> PreflightPacket:
        state: PreflightState = {"request": request}
        result = self._preflight_graph.invoke(state)
        packet = result.get("packet")
        if not packet:
            raise RuntimeError("Preflight workflow did not produce a packet")
        return packet

    def query(self, request: QueryRequest) -> QueryResponse:
        service_hint = request.service or self._infer_service(request.question)
        retrieval = self.retriever.retrieve(
            task=request.question,
            service_name_or_id=service_hint or "Auth Service",
            mode=request.mode,
            top_k=request.top_k,
        )
        evidence = retrieval["evidence"]
        answer, answer_source = answer_from_evidence(self.settings, request.question, evidence)
        return QueryResponse(
            answer=answer,
            evidence=evidence,
            retrieval={
                "service": retrieval["service"],
                "vector_hit_count": len(retrieval["vector_hits"]),
                "relationship_paths": retrieval["relationship_paths"],
                "policy": retrieval.get("policy"),
                "token_estimate": retrieval.get("token_estimate"),
                "answer_source": answer_source,
            },
        )

    def run_agents(self, request: AgentRunRequest) -> AgentRunResult:
        from engram.agents.runner import AgentRouter

        return AgentRouter(self).run(request)

    def _infer_service(self, question: str) -> str | None:
        q = question.lower()
        if "auth" in q or "session" in q or "token" in q:
            return "Auth Service"
        if "redis" in q or "cache" in q:
            return "Redis Cache"
        return None

    def _build_preflight_graph(self):
        graph = StateGraph(PreflightState)

        def resolve_context(state: PreflightState) -> PreflightState:
            req = state["request"]
            retrieval = self.retriever.retrieve(
                task=req.task,
                service_name_or_id=req.service,
                mode=req.mode,
            )
            return {"retrieval": retrieval}

        def assess(state: PreflightState) -> PreflightState:
            retrieval = state["retrieval"]
            risk, policy, reasoning, manual_checks = assess_risk(
                task=state["request"].task,
                service=retrieval["service"],
                neighborhood=retrieval["neighborhood"],
            )
            return {
                "risk_level": risk,
                "policy_outcome": policy,
                "reasoning": reasoning,
                "manual_checks": manual_checks,
            }

        def assemble_packet(state: PreflightState) -> PreflightState:
            retrieval = state["retrieval"]
            service = retrieval["service"]
            neighborhood = retrieval["neighborhood"]
            risk = state["risk_level"]
            policy = state["policy_outcome"]
            reasoning = state["reasoning"]
            manual_checks = state["manual_checks"]

            service_ctx = ServiceContext(
                id=service["id"],
                name=service["name"],
                owner=service.get("owner", "unknown"),
                criticality=service.get("criticality", "medium"),
                description=service.get("description", ""),
                dependencies=[d for d in neighborhood.get("dependencies") or [] if d],
                dependents=[d for d in neighborhood.get("dependents") or [] if d],
                github_repo=service.get("github_repo"),
            )

            packet = PreflightPacket(
                service=service_ctx,
                task=state["request"].task,
                risk_level=risk,
                policy_outcome=policy,
                summary=build_summary(service, risk, policy, reasoning),
                reasoning=reasoning,
                evidence=retrieval["evidence"],
                related_incidents=neighborhood.get("incidents") or [],
                related_prs=neighborhood.get("pull_requests") or [],
                related_adrs=neighborhood.get("adrs") or [],
                manual_checks=manual_checks,
                confidence="moderate" if policy != PolicyOutcome.ALLOW else "high",
                retrieval={
                    "vector_hit_count": len(retrieval["vector_hits"]),
                    "relationship_paths": retrieval["relationship_paths"],
                    "embedding_backend": "openai" if self.embedder.uses_openai else "local-hash",
                    "policy": retrieval.get("policy"),
                    "token_estimate": retrieval.get("token_estimate"),
                },
            )
            return {"packet": packet}

        graph.add_node("resolve_context", resolve_context)
        graph.add_node("assess", assess)
        graph.add_node("assemble_packet", assemble_packet)
        graph.set_entry_point("resolve_context")
        graph.add_edge("resolve_context", "assess")
        graph.add_edge("assess", "assemble_packet")
        graph.add_edge("assemble_packet", END)
        return graph.compile()
