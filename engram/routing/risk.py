from __future__ import annotations

import re
from dataclasses import dataclass, field

from engram.models.schemas import CandidateChange, PolicyOutcome, PreflightPacket, ReviewReport

KNOWN_ROLES = ("manager", "backend", "reviewer")
HIGH_PATH_MARKERS = ("auth", "payment", "redis")


@dataclass
class BlastRadius:
    criticality: str
    dependency_count: int
    high_path: bool
    open_incidents: int


@dataclass
class RiskDecision:
    gate: PolicyOutcome
    human_required: bool
    verification: str
    reasons: list[str] = field(default_factory=list)
    violations: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "gate": self.gate.value,
            "human_required": self.human_required,
            "verification": self.verification,
            "reasons": self.reasons,
            "violations": self.violations,
        }


def blast_radius_from_packet(packet: PreflightPacket) -> BlastRadius:
    name = f"{packet.service.name} {packet.service.id}".lower()
    open_incidents = [
        inc
        for inc in packet.related_incidents
        if (inc.get("status") or "").lower() in {"investigating", "open", "active"}
    ]
    return BlastRadius(
        criticality=(packet.service.criticality or "medium").lower(),
        dependency_count=len(packet.service.dependencies or []),
        high_path=any(marker in name for marker in HIGH_PATH_MARKERS),
        open_incidents=len(open_incidents),
    )


def organization_roles(
    policy: PolicyOutcome,
    task_class: str,
    blast: BlastRadius | None = None,
) -> list[str]:
    """Minimum agent org from blast radius + policy. Rules, not a learned router."""
    if task_class == "docs" or policy == PolicyOutcome.ALLOW:
        return ["backend"]
    if blast and blast.high_path:
        return ["manager", "backend", "reviewer"]
    if policy in {PolicyOutcome.REVIEW, PolicyOutcome.BLOCK}:
        return ["manager", "backend", "reviewer"]
    if policy == PolicyOutcome.WARN or (blast and (blast.dependency_count >= 2 or blast.open_incidents)):
        return ["backend", "reviewer"]
    return ["backend"]


def finalize_risk(
    packet: PreflightPacket,
    candidate: CandidateChange | None,
    review: ReviewReport | None,
) -> RiskDecision:
    """Final gate after a candidate exists. Policy violations block; reviewer cannot allow."""
    reasons: list[str] = [
        f"Preflight policy is {packet.policy_outcome.value} at risk {packet.risk_level.value}."
    ]
    violations = _constraint_violations(packet, candidate)
    gate = packet.policy_outcome

    if violations:
        gate = PolicyOutcome.BLOCK
        for item in violations:
            reasons.append(item["detail"])
    elif review and any(item.severity == "high" for item in review.findings):
        if gate == PolicyOutcome.ALLOW:
            gate = PolicyOutcome.REVIEW
            reasons.append("Independent reviewer reported high-severity findings; Engram escalated allow → review.")
        elif gate == PolicyOutcome.WARN:
            gate = PolicyOutcome.REVIEW
            reasons.append("Independent reviewer reported high-severity findings; Engram escalated warn → review.")

    blast = blast_radius_from_packet(packet)
    human_required = gate in {PolicyOutcome.REVIEW, PolicyOutcome.BLOCK} and (
        blast.high_path or blast.criticality == "high" or gate == PolicyOutcome.BLOCK
    )
    if human_required:
        reasons.append("Human approval required before merge. Agents cannot clear this gate.")

    verification = {
        PolicyOutcome.ALLOW: "none",
        PolicyOutcome.WARN: "reviewer",
        PolicyOutcome.REVIEW: "independent_review",
        PolicyOutcome.BLOCK: "human",
    }[gate]

    return RiskDecision(
        gate=gate,
        human_required=human_required,
        verification=verification,
        reasons=reasons,
        violations=violations,
    )


def _constraint_violations(packet: PreflightPacket, candidate: CandidateChange | None) -> list[dict]:
    hours = [
        value
        for value in (_candidate_ttl_hours(candidate), _requested_hours(packet.task))
        if value is not None
    ]
    if not hours:
        return []
    requested = max(hours)

    found: list[dict] = []
    for adr in packet.related_adrs:
        cap = _adr_hour_cap(adr)
        if cap is None or requested <= cap:
            continue
        adr_id = str(adr.get("id") or "")
        found.append(
            {
                "evidence_id": adr_id,
                "detail": (
                    f"Requested/candidate lifetime {requested} hours exceeds "
                    f"{adr.get('id')} cap of {cap} hours."
                ),
            }
        )
    return found


def _candidate_ttl_hours(candidate: CandidateChange | None) -> int | None:
    if not candidate or not candidate.diff:
        return None
    added = "\n".join(
        line[1:]
        for line in candidate.diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    match = re.search(r"SESSION_TTL_HOURS\s*=\s*(\d+)", added)
    return int(match.group(1)) if match else None


def _requested_hours(task: str) -> int | None:
    text = task.lower()
    days = re.search(r"(\d+)\s*days", text)
    if days:
        return int(days.group(1)) * 24
    hours = re.search(r"to\s+(\d+)\s*hours", text)
    if hours:
        return int(hours.group(1))
    return None


def _adr_hour_cap(adr: dict) -> int | None:
    text = f"{adr.get('title') or ''} {adr.get('content') or ''}"
    lowered = text.lower()
    if not any(marker in lowered for marker in ("ttl", "session", "cache", "redis")):
        return None
    match = re.search(r"(?:max ttl of|at most)\s+(\d+)\s+hours", text, re.I)
    if match:
        return int(match.group(1))
    match = re.search(r"max TTL\s+(\d+)\s+hours", text, re.I)
    if match:
        return int(match.group(1))
    return None
