from engram.models.schemas import (
    CandidateChange,
    PolicyOutcome,
    PreflightPacket,
    ReviewReport,
    RiskLevel,
    ServiceContext,
)
from engram.routing.risk import finalize_risk, organization_roles


def _packet(**kwargs) -> PreflightPacket:
    service = kwargs.get(
        "service",
        ServiceContext(
            id="svc-auth",
            name="Auth Service",
            owner="Platform Team",
            criticality="high",
            description="auth",
            dependencies=["Redis Cache"],
        ),
    )
    return PreflightPacket(
        service=service,
        task=kwargs.get("task", "Increase auth session TTL from 24 hours to 7 days"),
        risk_level=kwargs.get("risk_level", RiskLevel.MEDIUM_HIGH),
        policy_outcome=kwargs.get("policy_outcome", PolicyOutcome.REVIEW),
        summary="preflight",
        reasoning=[],
        evidence=[],
        related_incidents=kwargs.get("related_incidents") or [],
        related_prs=[],
        related_adrs=kwargs.get("related_adrs")
        or [
            {
                "id": "adr-12",
                "number": 12,
                "title": "Redis TTL strategy",
                "content": "Auth session keys in Redis must use a max TTL of 48 hours unless approved.",
            }
        ],
        manual_checks=[],
        confidence="moderate",
        retrieval={"policy": {"task_class": kwargs.get("task_class", "risk_sensitive")}},
    )


def test_ttl_over_adr_cap_blocks():
    packet = _packet()
    candidate = CandidateChange(
        sandbox_id="t",
        diff="--- a/session.py\n+++ b/session.py\n@@ -1 +1 @@\n-SESSION_TTL_HOURS = 24\n+SESSION_TTL_HOURS = 168\n",
    )
    decision = finalize_risk(packet, candidate, ReviewReport(summary="ok", findings=[]))
    assert decision.gate == PolicyOutcome.BLOCK
    assert decision.human_required is True
    assert decision.violations
    assert decision.violations[0]["evidence_id"] == "adr-12"


def test_task_intent_blocks_even_without_diff():
    packet = _packet()
    decision = finalize_risk(packet, None, None)
    assert decision.gate == PolicyOutcome.BLOCK
    assert any("adr-12" in item["evidence_id"] for item in decision.violations)


def test_docs_org_stays_backend_only():
    assert organization_roles(PolicyOutcome.ALLOW, "docs") == ["backend"]


def test_task_still_blocks_if_candidate_keeps_old_ttl():
    packet = _packet()
    candidate = CandidateChange(
        sandbox_id="t",
        diff=(
            "--- a/session.py\n+++ b/session.py\n@@ -1 +1 @@\n"
            "-SESSION_TTL_HOURS = 24\n"
            "+SESSION_TTL_HOURS = 24  # maybe 7 days later\n"
        ),
    )
    decision = finalize_risk(packet, candidate, None)
    assert decision.gate == PolicyOutcome.BLOCK
    assert decision.violations[0]["evidence_id"] == "adr-12"


def test_identity_lifetime_adr_does_not_cap_session_ttl():
    packet = _packet(
        related_adrs=[
            {
                "id": "adr-40",
                "number": 40,
                "title": "Q4 identity lifetime freeze",
                "content": "identity credential lifetime for customer logins stays at 48 hours for finance audit.",
            },
            {
                "id": "adr-12",
                "number": 12,
                "title": "Redis TTL strategy",
                "content": "Auth session keys in Redis must use a max TTL of 48 hours unless approved.",
            },
        ]
    )
    decision = finalize_risk(packet, None, None)
    ids = [item["evidence_id"] for item in decision.violations]
    assert ids == ["adr-12"]
