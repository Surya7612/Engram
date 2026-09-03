from engram.preflight.risk import assess_risk


def test_auth_ttl_change_triggers_review():
    service = {"name": "Auth Service", "criticality": "high"}
    neighborhood = {
        "incidents": [
            {"id": "inc-480", "number": 480, "status": "investigating", "title": "Token refresh timeout"}
        ],
        "adrs": [
            {"id": "adr-12", "number": 12, "title": "Redis TTL strategy", "content": "max TTL 48 hours"}
        ],
        "dependencies": ["Redis Cache"],
    }
    task = "Increase auth session TTL from 24 hours to 7 days"

    risk, policy, reasoning, manual = assess_risk(task, service, neighborhood)

    assert risk.value in {"medium", "medium-high", "high"}
    assert policy.value in {"warn", "review", "block"}
    assert reasoning
    assert manual
