from engram.agents.llm import complete_json
from engram.config import Settings
from engram.models.schemas import ManagerProposal, PreflightPacket

_SYSTEM = """You are Engram's Manager agent. Propose a short plan and which of these roles should run: backend, reviewer.
You do not approve merges. You do not override ADRs, incidents, ownership, or policy.
Return JSON: {"proposed_roles": ["backend"], "steps": ["..."], "rationale": "..."}
Only use roles backend and reviewer. Do not invent other personas."""


def propose(
    settings: Settings,
    packet: PreflightPacket,
    constraints: list[str] | None = None,
) -> ManagerProposal:
    constraint_block = ""
    if constraints:
        constraint_block = "Constraints:\n- " + "\n- ".join(constraints[:12]) + "\n"
    payload = complete_json(
        settings,
        _SYSTEM,
        (
            f"Task: {packet.task}\n"
            f"Service: {packet.service.name} (owner {packet.service.owner}, "
            f"criticality {packet.service.criticality})\n"
            f"Engram policy: {packet.policy_outcome.value}; risk {packet.risk_level.value}\n"
            f"{constraint_block}"
            f"Evidence labels: {', '.join(e.label for e in packet.evidence[:8])}\n"
        ),
    )
    if payload:
        roles = [r for r in payload.get("proposed_roles") or [] if isinstance(r, str)]
        steps = [s for s in payload.get("steps") or [] if isinstance(s, str)]
        return ManagerProposal(
            proposed_roles=roles or ["backend"],
            steps=steps,
            rationale=str(payload.get("rationale") or ""),
        )
    return ManagerProposal(
        proposed_roles=["backend"],
        steps=["Have backend implement the requested change."],
        rationale="Naive fallback: manager proposed backend-only execution.",
    )
