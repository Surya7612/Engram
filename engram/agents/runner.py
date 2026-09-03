from typing import TypedDict

from langgraph.graph import END, StateGraph

from engram.agents import backend, manager, reviewer
from engram.agents.constraints import constraints_from_packet, constraints_from_priors
from engram.agents.org import constrain_roles, required_roles
from engram.agents.sandbox import ReadOnlySandbox, Sandbox
from engram.config import Settings
from engram.learning.store import OutcomeStore
from engram.models.schemas import (
    AgentRunRequest,
    AgentRunResult,
    CandidateChange,
    ManagerProposal,
    PreflightPacket,
    PreflightRequest,
    ReviewReport,
)
from engram.routing.risk import blast_radius_from_packet, finalize_risk


class AgentState(TypedDict, total=False):
    request: AgentRunRequest
    packet: PreflightPacket
    manager: ManagerProposal | None
    instantiated: list[str]
    added_roles: list[str]
    dropped_roles: list[str]
    manager_overridden: bool
    constraints: list[str]
    priors: list[dict]
    sandbox: Sandbox
    candidate: CandidateChange | None
    review: ReviewReport | None
    result: AgentRunResult


class AgentRouter:
    """Manager proposes; Engram constrains; Backend sandboxes; Reviewer is read-only."""

    def __init__(self, engine):
        self._engine = engine
        self._settings: Settings = engine.settings
        self._graph = self._build()

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        state: AgentState = {"request": request}
        result = self._graph.invoke(state)
        packet_result = result.get("result")
        if not packet_result:
            raise RuntimeError("Agent router did not produce a result")
        return packet_result

    def _build(self):
        graph = StateGraph(AgentState)

        def preflight_node(state: AgentState) -> AgentState:
            req = state["request"]
            packet = self._engine.preflight(
                PreflightRequest(service=req.service, task=req.task, mode=req.mode)
            )
            return {"packet": packet}

        def manager_node(state: AgentState) -> AgentState:
            packet = state["packet"]
            task_class = (packet.retrieval.get("policy") or {}).get("task_class") or "generic"
            required = required_roles(
                packet.policy_outcome,
                task_class,
                blast_radius_from_packet(packet),
            )
            priors = OutcomeStore(self._settings.local_data_dir / "outcomes.jsonl").similar(
                packet.service.name,
                packet.task,
            )
            constraints = constraints_from_packet(packet) + constraints_from_priors(priors)
            proposal = None
            proposed_roles = [role for role in required if role != "manager"]
            if "manager" in required:
                proposal = manager.propose(self._settings, packet, constraints)
                proposed_roles = proposal.proposed_roles or ["backend"]
            instantiated, added, dropped, overridden = constrain_roles(proposed_roles, required)
            if proposal is None:
                overridden = False
                added, dropped = [], []
            return {
                "manager": proposal,
                "instantiated": instantiated,
                "added_roles": added,
                "dropped_roles": dropped,
                "manager_overridden": overridden,
                "constraints": constraints,
                "priors": priors,
            }

        def backend_node(state: AgentState) -> AgentState:
            if "backend" not in state["instantiated"]:
                return {"candidate": None}
            packet = state["packet"]
            req = state["request"]
            github_repo = req.repo or packet.service.github_repo
            try:
                sandbox = Sandbox.create(
                    self._settings.data_dir,
                    self._settings.local_data_dir,
                    packet.service.id,
                    github_repo=github_repo,
                    token=req.token or self._settings.github_token,
                )
            except (ValueError, RuntimeError) as exc:
                return {
                    "candidate": CandidateChange(
                        sandbox_id="none",
                        notes=str(exc),
                        applied_to_origin=False,
                        source_repo=github_repo,
                    )
                }
            candidate = backend.implement(self._settings, packet, state["constraints"], sandbox)
            return {"sandbox": sandbox, "candidate": candidate}

        def reviewer_node(state: AgentState) -> AgentState:
            if "reviewer" not in state["instantiated"]:
                return {"review": None}
            sandbox = state.get("sandbox")
            if sandbox is None:
                return {
                    "review": ReviewReport(
                        summary="No sandbox candidate to review.",
                        findings=[],
                    )
                }
            report = reviewer.review(
                self._settings,
                state["packet"],
                state["constraints"],
                ReadOnlySandbox(sandbox),
            )
            return {"review": report}

        def assemble_node(state: AgentState) -> AgentState:
            packet = state["packet"]
            proposal = state.get("manager")
            review = state.get("review")
            candidate = state.get("candidate")
            decision = finalize_risk(packet, candidate, review)
            notes = [
                "Candidate exists in a git worktree branch. Origin main is unchanged. Nothing is merged.",
                "Governance gate is Engram risk policy. Reviewer cannot approve a merge.",
            ]
            if state.get("manager_overridden"):
                added = ", ".join(state.get("added_roles") or []) or "none"
                dropped = ", ".join(state.get("dropped_roles") or []) or "none"
                notes.append(f"Manager proposal overridden. Added: {added}. Dropped: {dropped}.")
            if decision.human_required:
                notes.append("Human approval required. Agents cannot clear a review/block gate.")
            priors = state.get("priors") or []
            if priors:
                notes.append(
                    "Similar prior outcomes were injected as constraints. Lookup only; not a learned policy."
                )
            result = AgentRunResult(
                task=packet.task,
                service=packet.service.name,
                risk_level=packet.risk_level,
                gate=decision.gate,
                instantiated=state.get("instantiated") or [],
                manager_proposed_roles=(proposal.proposed_roles if proposal else []),
                engram_required_roles=state.get("instantiated") or [],
                manager_overridden=bool(state.get("manager_overridden")),
                constraints=state.get("constraints") or [],
                manager=proposal,
                candidate=candidate,
                review=review,
                evidence=packet.evidence,
                notes=notes,
                human_required=decision.human_required,
                risk=decision.as_dict(),
                priors=priors,
            )
            outcome = OutcomeStore(self._settings.local_data_dir / "outcomes.jsonl").record(
                result,
                extra={
                    "task_class": (packet.retrieval.get("policy") or {}).get("task_class"),
                    "token_estimate": packet.retrieval.get("token_estimate"),
                    "prior_ids": [item.get("id") for item in priors],
                },
            )
            result.outcome_id = outcome["id"]
            result.human_decision = outcome["human_decision"]
            return {"result": result}

        graph.add_node("preflight", preflight_node)
        graph.add_node("manager", manager_node)
        graph.add_node("backend", backend_node)
        graph.add_node("reviewer", reviewer_node)
        graph.add_node("assemble", assemble_node)
        graph.set_entry_point("preflight")
        graph.add_edge("preflight", "manager")
        graph.add_edge("manager", "backend")
        graph.add_edge("backend", "reviewer")
        graph.add_edge("reviewer", "assemble")
        graph.add_edge("assemble", END)
        return graph.compile()
