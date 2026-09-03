import re

from engram.agents.llm import complete_json
from engram.agents.sandbox import ReadOnlySandbox
from engram.config import Settings
from engram.models.schemas import PreflightPacket, ReviewFinding, ReviewReport

_SYSTEM = """You are Engram's Reviewer. You are read-only. You do not implement, merge, or approve.
Judge the candidate against Engram constraints and evidence (ADRs, incidents, ownership).
Return JSON: {"summary": "...", "findings": [{"severity": "high|medium|low", "claim": "...", "evidence_ids": ["adr-12"]}]}
Never output an approval or merge decision."""


def review(
    settings: Settings,
    packet: PreflightPacket,
    constraints: list[str],
    sandbox: ReadOnlySandbox,
) -> ReviewReport:
    evidence = [{"id": e.artifact_id, "label": e.label, "snippet": e.snippet} for e in packet.evidence]
    payload = complete_json(
        settings,
        _SYSTEM,
        (
            f"Task: {packet.task}\n"
            f"Constraints:\n- "
            + "\n- ".join(constraints)
            + f"\n\nEvidence: {evidence}\n\nCandidate diff:\n{sandbox.unified_diff() or '(empty)'}"
        ),
    )
    if payload:
        findings = []
        for item in payload.get("findings") or []:
            if not isinstance(item, dict):
                continue
            claim = str(item.get("claim") or "").strip()
            if not claim:
                continue
            findings.append(
                ReviewFinding(
                    severity=str(item.get("severity") or "medium"),
                    claim=claim,
                    evidence_ids=[str(x) for x in (item.get("evidence_ids") or []) if x],
                )
            )
        return ReviewReport(
            summary=str(payload.get("summary") or "Reviewer completed a read-only pass."),
            findings=findings,
        )
    return _deterministic_review(packet, sandbox)


def _deterministic_review(packet: PreflightPacket, sandbox: ReadOnlySandbox) -> ReviewReport:
    diff = sandbox.unified_diff()
    findings: list[ReviewFinding] = []
    added = "\n".join(
        line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
    )
    adr12 = next((a for a in packet.related_adrs if a.get("id") == "adr-12"), None)
    ttl_match = re.search(r"SESSION_TTL_HOURS\s*=\s*(\d+)", added)
    if adr12 and ttl_match and int(ttl_match.group(1)) > 48:
        findings.append(
            ReviewFinding(
                severity="high",
                claim=(
                    f"Candidate sets session lifetime to {ttl_match.group(1)} hours, "
                    "above ADR-12 max of 48 hours."
                ),
                evidence_ids=["adr-12"],
            )
        )
    inc77 = next((i for i in packet.related_incidents if i.get("id") == "inc-77"), None)
    if inc77 and "SESSION_TTL_HOURS" in diff:
        findings.append(
            ReviewFinding(
                severity="medium",
                claim="INC-77: raising credential lifetime previously caused Redis eviction and login failures.",
                evidence_ids=["inc-77"],
            )
        )
    if not findings:
        return ReviewReport(summary="Read-only review found no deterministic policy conflicts in the sandbox diff.")
    return ReviewReport(
        summary="Read-only review found constraint conflicts. Engram gate is unchanged by this report.",
        findings=findings,
    )
